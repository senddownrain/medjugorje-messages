#!/usr/bin/env python3
"""Check for NEW DATES in the official English archive, not seven translations."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

URL = "https://www.medjugorje.hr/en/our-lady-messages-archive"
USER_AGENT = "MedjugorjeMessagesWatch/0.1 (https://github.com/senddownrain/medjugorje-messages)"
DATE_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$")
LANGS = ("ru", "be", "uk", "hr", "en", "sk", "lv")

def extract_dates(html):
    soup = BeautifulSoup(html, "html.parser")
    dates = set()
    for tag in soup.select("h2"):
        title = " ".join(tag.get_text(" ", strip=True).split())
        if DATE_RE.fullmatch(title):
            dates.add(datetime.strptime(title, "%B %d, %Y").date().isoformat())
    if not dates:
        raise ValueError("Official archive has no recognizable date headings")
    return sorted(dates, reverse=True)

def compare(official_dates, index):
    records = index.get("messages")
    if not isinstance(records, list) or not records:
        raise ValueError("Missing stored message index")
    if any(not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row.get("date", ""))) for row in records):
        raise ValueError("Invalid stored dates")
    newest_local = max(row["date"] for row in records)
    new_dates = [date for date in official_dates if date > newest_local]
    return {
        "status": "new_dates_detected" if new_dates else "no_newer_dates",
        "latest_official": official_dates[0], "latest_local": newest_local,
        "new_dates": new_dates, "translations_checked": False,
        "language_counts_in_local_index": {
            lang: sum(bool(row.get("translations", {}).get(lang, {}).get("present")) for row in records)
            for lang in LANGS
        }
    }

def extract_observations(html, *, errors=None):
    soup = BeautifulSoup(html, "html.parser")
    for unsafe in soup.select('script, style, noscript'):
        unsafe.decompose()
    groups = {}
    for heading in soup.select('h2'):
        title = " ".join(heading.get_text(" ", strip=True).split())
        if not DATE_RE.fullmatch(title):
            continue
        try:
            date = datetime.strptime(title, "%B %d, %Y").date().isoformat()
        except ValueError:
            if errors is None:
                raise
            errors.append({"heading":title,"code":"invalid_official_message_date"})
            continue
        body = []
        for sibling in heading.next_siblings:
            if getattr(sibling, 'name', None) == 'h2':
                break
            text = sibling.get_text("\n", strip=True) if hasattr(sibling, 'get_text') else str(sibling).strip()
            if text:
                body.append(text)
        groups.setdefault(date, []).append("\n".join(body))
    if not groups:
        raise ValueError("Official archive has no recognizable date headings")
    return [{'date':date, 'sections':sections} for date, sections in sorted(groups.items(), reverse=True)]

def fetch_archive(*, raw=False):
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    robots_response = session.get("https://www.medjugorje.hr/robots.txt", timeout=15, allow_redirects=False)
    if robots_response.status_code in (401, 403, 429):
        raise PermissionError("robots.txt HTTP " + str(robots_response.status_code))
    if robots_response.status_code not in (200, 404):
        raise ConnectionError("robots.txt HTTP " + str(robots_response.status_code))
    robot = RobotFileParser()
    robot.parse(robots_response.text.splitlines() if robots_response.status_code == 200 else [])
    if not robot.can_fetch(USER_AGENT, URL):
        raise PermissionError("robots.txt disallows messages archive")
    response = session.get(URL, timeout=25, allow_redirects=False)
    if response.status_code in (401, 403, 429):
        raise PermissionError("archive HTTP " + str(response.status_code))
    if 300 <= response.status_code < 400:
        raise ValueError("Unapproved source redirect; review documented URL")
    response.raise_for_status()
    if "html" not in response.headers.get("content-type", "").lower():
        raise ValueError("Unexpected source content type")
    return response.content if raw else response.text

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=Path, default=Path("data/index.json"))
    p.add_argument("--output", type=Path, default=Path("research-output/official-watch.json"))
    args = p.parse_args()
    report = {"source": URL, "source_role": "primary", "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        html = fetch_archive()
        dates = extract_dates(html)
        report["observations"] = extract_observations(html)
        report.update(compare(dates, json.loads(args.index.read_text(encoding="utf-8"))))
    except Exception as exc:
        report.update({"status": "blocked_or_failed", "error": str(exc), "new_dates": None,
                       "translations_checked": False})
    report["state"] = "ERROR" if report["status"] == "blocked_or_failed" else "OK"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 2 if report["status"] == "blocked_or_failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())
