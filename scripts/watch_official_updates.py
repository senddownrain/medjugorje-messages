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

def fetch_dates():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    robots_response = session.get("https://www.medjugorje.hr/robots.txt", timeout=15)
    if robots_response.status_code in (401, 403, 429):
        raise PermissionError("robots.txt HTTP " + str(robots_response.status_code))
    if robots_response.status_code not in (200, 404):
        raise ConnectionError("robots.txt HTTP " + str(robots_response.status_code))
    robot = RobotFileParser()
    robot.parse(robots_response.text.splitlines() if robots_response.status_code == 200 else [])
    if not robot.can_fetch(USER_AGENT, URL):
        raise PermissionError("robots.txt disallows messages archive")
    response = session.get(URL, timeout=25)
    if response.status_code in (401, 403, 429):
        raise PermissionError("archive HTTP " + str(response.status_code))
    response.raise_for_status()
    if "html" not in response.headers.get("content-type", "").lower():
        raise ValueError("Unexpected source content type")
    return extract_dates(response.text)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=Path, default=Path("data/index.json"))
    p.add_argument("--output", type=Path, default=Path("research-output/official-watch.json"))
    args = p.parse_args()
    report = {"source": URL, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        dates = fetch_dates()
        report.update(compare(dates, json.loads(args.index.read_text(encoding="utf-8"))))
    except Exception as exc:
        report.update({"status": "blocked_or_failed", "error": str(exc), "new_dates": None,
                       "translations_checked": False})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 2 if report["status"] == "blocked_or_failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())
