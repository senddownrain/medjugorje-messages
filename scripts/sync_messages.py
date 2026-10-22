#!/usr/bin/env python3
"""Stage-one research importer for medjugorje.ws messages (RU, BE, UK).

Collect original published texts; do not translate, publish, or infer absent data.
Only a manually triggered GitHub Action runs this initial importer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

ORIGIN = "https://www.medjugorje.ws"
LANGUAGES = ("ru", "be", "uk")
CATEGORIES = {"m": "monthly", "w": "weekly", "a": "annual", "o": "special"}
SOURCES = ("all", "list", "monthly/", "weekly/", "annual/", "special/")
HEADERS_TO_STOP = {"h1", "h2"}
SKIP_ANCESTORS = {"script", "style", "nav", "footer", "form", "select", "option", "noscript", "svg"}
END_MARKERS = (
    "to compare medjugorje messages", "printer friendly version",
    "для сравнения с другой", "для параўнання", "для порівняння"
)
ID_RE = re.compile(r"^(\d{6}[a-z][a-z0-9_-]*)$", re.I)


def slug_for_url(href: str, lang: str, base: str = ORIGIN) -> str | None:
    url = urlparse(urljoin(base, href))
    if url.hostname not in ("www.medjugorje.ws", "medjugorje.ws"):
        return None
    match = re.fullmatch(rf"/{lang}/messages/([^/]+)/?", url.path)
    if not match:
        return None
    slug = match.group(1).lower()
    return slug if ID_RE.fullmatch(slug) else None


def date_for_slug(slug: str) -> str:
    yy, mm, dd = int(slug[:2]), int(slug[2:4]), int(slug[4:6])
    return date((1900 if yy >= 84 else 2000) + yy, mm, dd).isoformat()


def visionary_for_title(title: str, kind: str) -> str | None:
    t = title.lower()
    patterns = {
        "mirjana": r"mirjan|мирьян|мір.?ян|марыян",
        "ivanka": r"ivank|иванк|іванк",
        "jakov": r"jakov|яков|якаў|якуб|яків",
        "marija": r"marija|мария павлов|марія павлов|марыя паўлов",
        "ivan": r"ivan dragi|иван драг|іван драг",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, t):
            return name
    # Monthly messages are attributed to Marija in the site's classification.
    return "marija" if kind == "monthly" else None


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u200b", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_body(heading: Tag) -> str:
    """Take text after a linked H2, up to the next H2, excluding page furniture."""
    parts = []
    for node in heading.next_elements:
        if isinstance(node, Tag):
            if node is not heading and node.name in HEADERS_TO_STOP:
                break
            if node.name in ("p", "blockquote", "div", "br", "li"):
                parts.append("\n")
            continue
        if not isinstance(node, NavigableString) or heading in node.parents:
            continue
        if any(isinstance(p, Tag) and p.name in SKIP_ANCESTORS for p in node.parents):
            continue
        s = str(node)
        if any(marker in s.lower() for marker in END_MARKERS):
            break
        parts.append(s)
    return normalize_text("".join(parts))


def parse_archive(html: str, lang: str, page_url: str):
    soup = BeautifulSoup(html, "html.parser")
    discovered = {
        slug for a in soup.select("a[href]")
        if (slug := slug_for_url(a["href"], lang, page_url))
    }
    records = {}
    problems = []
    for h in soup.find_all("h2"):
        slug = next((
            slug for a in h.select("a[href]")
            if (slug := slug_for_url(a["href"], lang, page_url))
        ), None)
        if slug is None:
            continue
        title = h.get_text(" ", strip=True)
        body = extract_body(h)
        if not 10 <= len(body) <= 30000:
            problems.append(f"{slug}: suspicious length {len(body)} in {page_url}")
            continue
        try:
            date_string = date_for_slug(slug)
        except ValueError:
            problems.append(f"{slug}: invalid date in {page_url}")
            continue
        kind = CATEGORIES.get(slug[6], "other")
        rec = {
            "id": slug, "date": date_string, "type": kind,
            "visionary": visionary_for_title(title, kind),
            "language": lang, "title": title, "text": body,
            "source_url": f"{ORIGIN}/{lang}/messages/{slug}/",
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()
        }
        if slug in records and rec["sha256"] != records[slug]["sha256"]:
            problems.append(f"{slug}: duplicate differing content in {page_url}")
        else:
            records[slug] = rec
    return records, discovered, problems


class PoliteFetcher:
    def __init__(self, delay: float = 1.5):
        self.delay = max(delay, 1.0)
        self.last = 0.0
        self.session = requests.Session()
        self.user_agent = "MedjugorjeMessagesArchiveResearch/0.1 (GitHub: senddownrain/medjugorje-messages)"
        self.session.headers["User-Agent"] = self.user_agent
        self.robots = RobotFileParser()
        robots_url = ORIGIN + "/robots.txt"
        response = self.session.get(robots_url, timeout=30)
        if response.status_code in (401, 403):
            raise RuntimeError("Site denies access to robots.txt; manual permission required")
        if response.status_code not in (200, 404):
            raise RuntimeError(f"Unknown robots.txt status: {response.status_code}")
        self.robots.parse(response.text.splitlines() if response.status_code == 200 else [])

    def get(self, url: str) -> str:
        if not self.robots.can_fetch(self.user_agent, url):
            raise PermissionError(f"robots.txt disallows: {url}")
        for attempt in range(3):
            elapsed = time.monotonic() - self.last
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self.last = time.monotonic()
            try:
                response = self.session.get(url, timeout=45)
                if response.status_code in (401, 403):
                    raise PermissionError(f"Site denies access: {url}: {response.status_code}")
                if response.status_code == 429:
                    raise RuntimeError(f"Rate-limited: {url}; stop, do not bypass")
                response.raise_for_status()
                if "html" not in response.headers.get("Content-Type", "text/html"):
                    raise ValueError(f"Unexpected content type: {url}")
                if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                    response.encoding = response.apparent_encoding
                return response.text
            except (requests.RequestException, ValueError) as exc:
                if attempt == 2:
                    raise RuntimeError(f"Could not read {url}: {exc}") from exc
                time.sleep(3 * 2**attempt)
        raise AssertionError("unreachable")


def write_json(path: Path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("research-output"))
    p.add_argument("--delay", type=float, default=1.5)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    report = {
        "status": "UNVERIFIED_RESEARCH_IMPORT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "languages": {}, "warnings": []
    }
    datasets = {}
    errors = []
    try:
        fetcher = PoliteFetcher(args.delay)
    except Exception as exc:
        write_json(args.output / "report.json", {**report, "fatal_error": str(exc)})
        print(f"Research blocked: {exc}")
        return 2

    for lang in LANGUAGES:
        found = {}
        expected = set()
        lang_warnings = []
        pages_ok = []
        for source in SOURCES:
            url = f"{ORIGIN}/{lang}/messages/{source}"
            try:
                html = fetcher.get(url)
                batch, discovered, problems = parse_archive(html, lang, url)
                pages_ok.append(url)
                expected.update(discovered)
                lang_warnings.extend(problems)
                for slug, record in batch.items():
                    if slug in found and found[slug]["sha256"] != record["sha256"]:
                        lang_warnings.append(f"{slug}: conflict between source sections")
                    else:
                        found.setdefault(slug, record)
                print(f"{lang} {source}: parsed={len(batch)} links={len(discovered)}")
            except (PermissionError, RuntimeError) as exc:
                errors.append(str(exc))
                lang_warnings.append(str(exc))
                print(f"{lang} {source}: {exc}")
                if isinstance(exc, PermissionError) or "Rate-limited" in str(exc):
                    break
        missing = sorted(expected - found.keys())
        report["languages"][lang] = {
            "sections_fetched": pages_ok,
            "unique_messages": len(found), "linked_ids": len(expected),
            "missing_ids": missing, "warnings": lang_warnings,
            "first_date": min((x["date"] for x in found.values()), default=None),
            "latest_monthly": max(
                (x["date"] for x in found.values() if x["type"] == "monthly"), default=None
            )
        }
        if not found or missing or lang_warnings:
            report["warnings"].append(f"{lang}: needs manual validation")
        datasets[lang] = found
        write_json(args.output / f"{lang}.json", {
            "language": lang, "verified": False,
            "messages": sorted(found.values(), key=lambda x: (x["date"], x["id"]), reverse=True)
        })

    ids = {}
    for lang, entries in datasets.items():
        for slug, msg in entries.items():
            item = ids.setdefault(slug, {
                "id": slug, "date": msg["date"], "type": msg["type"],
                "visionary": msg["visionary"], "languages": []
            })
            item["languages"].append(lang)
            if item["visionary"] is None and msg["visionary"]:
                item["visionary"] = msg["visionary"]
    write_json(args.output / "index.json", {
        "verified": False, "unique_messages": len(ids),
        "messages": sorted(ids.values(), key=lambda x: (x["date"], x["id"]), reverse=True)
    })
    write_json(args.output / "report.json", report)
    print(json.dumps({
        "unique_ids": len(ids),
        "per_language": {k: report["languages"][k]["unique_messages"] for k in LANGUAGES},
        "warnings": report["warnings"],
    }, ensure_ascii=False, indent=2))
    # Findings can still be downloaded as an artifact if diagnostics flag gaps.
    return 2 if errors or report["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
