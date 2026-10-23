#!/usr/bin/env python3
"""Read-only RSS access diagnostic for community-approved language sites.

No feeds are saved in the Git repository, no texts are published.
Never interpret HTTP errors as "no new translations".
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests

SITES = {
    "lv": "https://medjugorje.lv/",
    "sk": "https://svetlomariino.sk/",
    "uk": "https://svitlomariji.com.ua/",
    "ru": "https://svetmariji.ru/",
    "en": "https://thelightofmary.com/",
}
USER_AGENT = "MedjugorjeCommunityFeedProbe/0.1 (https://github.com/senddownrain/medjugorje-messages)"

def summarize_rss(data: bytes):
    root = ET.fromstring(data)
    name = root.tag.rsplit("}", 1)[-1].lower()
    if name == "rss":
        channel = root.find("channel")
        if channel is None:
            raise ValueError("RSS has no channel")
        posts = channel.findall("item")
        def get(el, field):
            found = el.find(field)
            return (found.text or "").strip() if found is not None else ""
        return [{"title": get(p, "title"), "link": get(p, "link"),
                 "published": get(p, "pubDate"),
                 "categories": [(c.text or "").strip() for c in p.findall("category")]}
                for p in posts[:5]], len(posts)
    if name == "feed":
        atom = "{http://www.w3.org/2005/Atom}"
        posts = root.findall(atom + "entry")
        return [{
            "title": (p.findtext(atom + "title") or "").strip(),
            "link": next((a.get("href", "") for a in p.findall(atom + "link")
                          if a.get("rel", "alternate") == "alternate"), ""),
            "published": (p.findtext(atom + "updated") or "").strip(),
            "categories": [(c.get("term") or "").strip() for c in p.findall(atom + "category")]
        } for p in posts[:5]], len(posts)
    raise ValueError("Not an RSS/Atom feed")


def inspect_site(lang, origin, session):
    feed_url = origin + "feed/"
    result = {"language": lang, "feed_url": feed_url, "state": "unknown"}
    try:
        robots = session.get(origin + "robots.txt", timeout=15)
        if robots.status_code in (401, 403, 429):
            return {**result, "state": "blocked", "at": "robots", "status": robots.status_code}
        if robots.status_code not in (200, 404):
            return {**result, "state": "unavailable", "at": "robots", "status": robots.status_code}
        rp = RobotFileParser()
        rp.parse(robots.text.splitlines() if robots.status_code == 200 else [])
        if not rp.can_fetch(USER_AGENT, feed_url):
            return {**result, "state": "blocked", "at": "robots_policy"}
        response = session.get(feed_url, timeout=25)
        if response.status_code in (401, 403, 429):
            return {**result, "state": "blocked", "at": "feed", "status": response.status_code}
        if response.status_code != 200:
            return {**result, "state": "unavailable", "at": "feed", "status": response.status_code}
        try:
            sample, count = summarize_rss(response.content)
        except (ET.ParseError, ValueError) as exc:
            return {**result, "state": "not_parseable", "error": str(exc)[:200]}
        if not sample:
            return {**result, "state": "empty_feed"}
        return {**result, "state": "accessible", "items": count, "sample": sample}
    except requests.RequestException as exc:
        return {**result, "state": "unavailable", "error_type": type(exc).__name__}

def run():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return {"checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "diagnostic_only",
            "sites": [inspect_site(lang, url, session) for lang, url in SITES.items()]}

if __name__ == "__main__":
    output = run()
    path = Path("research-output/community-feed-probe.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
