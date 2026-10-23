#!/usr/bin/env python3
"""Import complete saved /messages/all pages, including Chrome MHTML files.

This command is offline. It preserves original wording, editorial notes,
source URLs and date/link anomalies. It never declares content verified.
"""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
from email import policy
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, UnicodeDammit

TYPES = {"m": "monthly", "w": "weekly", "s": "special", "a": "annual"}
LANGS = ("ru", "be", "uk")
PATH = re.compile(r"^/(ru|be|uk)/messages/(\d{6}[a-z][a-z0-9_-]*)/?$", re.I)
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})_")
VISIONARIES = {
    "mirjana": r"mirjan|мирьян|мір.?ян",
    "ivanka": r"ivank|иванк|іванк",
    "jakov": r"jakov|яков|якаў|якуб|яків",
    "marija": r"marija|мария павлов|марія павлов|марыя паўлов",
    "ivan": r"ivan dragi|иван драг|іван драг",
}


def load_html(path):
    raw = Path(path).read_bytes()
    if not raw:
        raise ValueError("Empty source file")
    location = None
    if Path(path).suffix.lower() in (".mht", ".mhtml"):
        mime = BytesParser(policy=policy.default).parsebytes(raw)
        candidates = []
        for part in mime.walk():
            if part.is_multipart() or part.get_content_type() != "text/html":
                continue
            data = part.get_payload(decode=True)
            url = part.get("Content-Location")
            if data:
                priority = bool(url and re.search(r"medjugorje\.ws/(ru|be|uk)/messages/all/?$", url))
                candidates.append((int(priority), len(data), data, url))
        if not candidates:
            raise ValueError("No HTML part in MHTML")
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        raw, location = candidates[0][2:]
    try:
        return raw.decode("utf-8-sig"), location
    except UnicodeDecodeError:
        return UnicodeDammit(raw, is_html=True).unicode_markup, location


def block_text(tag):
    copy = BeautifulSoup(str(tag), "html.parser")
    for x in copy.select("script,style,noscript,span.bq,span.eq"):
        x.decompose()
    for x in copy.select("br"):
        x.replace_with("\n")
    root = copy.find(tag.name)
    value = root.get_text("", strip=False) if root else ""
    value = re.sub(r"[ \t\r\f\v]+", " ", value.replace("\xa0", " ").replace("\u200b", ""))
    value = "\n".join(line.strip() for line in value.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def get_visionary(title, category):
    for key, pattern in VISIONARIES.items():
        if re.search(pattern, title, flags=re.I):
            return key
    return "marija" if category == "monthly" else None


def parse_page(html, lang):
    soup = BeautifulSoup(html, "html.parser")
    titles = soup.select("h2.poselstvi-datum")
    if not titles:
        raise ValueError("No message headings; wrong file or changed source markup")
    messages, anomalies, slugs = [], [], Counter()
    for pos, title_tag in enumerate(titles):
        link = title_tag.select_one("a[href]")
        url = link.get("href", "") if link else ""
        p = urlparse(url)
        match = PATH.fullmatch(p.path)
        if not match or p.hostname not in ("www.medjugorje.ws", "medjugorje.ws") or match[1] != lang:
            anomalies.append({"position": pos, "reason": "invalid_message_link", "url": url})
            continue
        source_id = match[2].lower()
        slugs[source_id] += 1
        head = title_tag.find_parent("div", class_="mm-head")
        checkbox = head.select_one('input[type="checkbox"]') if head else None
        checked = DATE.match(checkbox.get("value", "")) if checkbox else None
        if not checked:
            anomalies.append({"position": pos, "reason": "missing_source_date", "source_id": source_id})
            continue
        d = checked[1]
        try:
            year, month, day = [int(x) for x in d.split("-")]
            date(year, month, day)
        except ValueError:
            anomalies.append({"position": pos, "reason": "invalid_source_date", "date": d})
            continue
        key = f"{year % 100:02d}{month:02d}{day:02d}" + source_id[6:]
        if key != source_id:
            anomalies.append({"position": pos, "reason": "source_url_date_mismatch",
                              "source_id": source_id, "derived_id": key,
                              "date": d, "url": url})
        category = TYPES.get(source_id[6], "other")
        title = title_tag.get_text(" ", strip=True)
        segments = []
        for sibling in head.next_siblings:
            if not getattr(sibling, "name", None):
                continue
            classes = sibling.get("class") or []
            if "mm-head" in classes or "mmm-footer" in classes or "messages" in classes:
                break
            if "poselstvi-mary" in classes or "poselstvi" in classes:
                text = block_text(sibling)
                if text:
                    segments.append({
                        "kind": "message" if "poselstvi-mary" in classes else "context",
                        "text": text
                    })
        message = "\n\n".join(s["text"] for s in segments if s["kind"] == "message")
        if not message:
            notes = " ".join(s["text"] for s in segments if s["kind"] == "context")
            status = ("no_message_announced" if re.search(
                r"не было .*послан|не было передано|няма .*паслан|не було .*послан",
                notes, flags=re.I) else "missing_message_text")
            anomalies.append({"position": pos, "reason": status, "id": key, "date": d})
        else:
            status = "contains_message"
        messages.append({
            "id": key, "source_id": source_id, "date": d, "type": category,
            "visionary": get_visionary(title, category), "language": lang,
            "title": title, "text": message, "segments": segments,
            "status": status, "source_url": url, "source_position": pos,
            "text_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest()
        })
    if len({x["id"] for x in messages}) != len(messages):
        anomalies.append({"reason": "duplicate_derived_id"})
    for slug, count in slugs.items():
        if count > 1:
            anomalies.append({"reason": "duplicate_source_url",
                              "source_id": slug, "occurrences": count})
    messages.sort(key=lambda m: (m["date"], m["id"]), reverse=True)
    report = {
        "status": "UNVERIFIED_RESEARCH_IMPORT", "language": lang,
        "archive_headings": len(titles), "records": len(messages),
        "distinct_ids": len({m["id"] for m in messages}),
        "distinct_source_urls": len(slugs),
        "records_with_text": sum(bool(m["text"]) for m in messages),
        "records_without_text": sum(not bool(m["text"]) for m in messages),
        "type_counts": dict(sorted(Counter(m["type"] for m in messages).items())),
        "date_first": min((m["date"] for m in messages), default=None),
        "date_last": max((m["date"] for m in messages), default=None),
        "latest_monthly": max((m["date"] for m in messages
                              if m["type"] == "monthly" and m["text"]), default=None),
        "anomalies": anomalies
    }
    return messages, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--language", choices=LANGS, default="ru")
    parser.add_argument("--output", type=Path, default=Path("research-output/offline"))
    args = parser.parse_args()
    html, location = load_html(args.source)
    if not html:
        raise ValueError("HTML could not be decoded")
    messages, report = parse_page(html, args.language)
    report.update({
        "saved_html_location": location,
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "generated_at": datetime.now(timezone.utc).isoformat()
    })
    args.output.mkdir(parents=True, exist_ok=True)
    def save(name, value):
        (args.output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save(f"{args.language}.json", {"language": args.language, "verified": False,
                                   "messages": messages})
    save("report.json", report)
    print(json.dumps({
        "records": report["records"], "with_text": report["records_with_text"],
        "without_text": report["records_without_text"],
        "anomalies": len(report["anomalies"]),
        "type_counts": report["type_counts"]
    }, ensure_ascii=False, indent=2))
    return 0 if messages else 2


if __name__ == "__main__":
    raise SystemExit(main())
