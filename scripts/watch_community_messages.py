#!/usr/bin/env python3
"""Conservative RSS watcher for published message translation CANDIDATES.

Five sites agreed with the project community. Reads RSS metadata only.
Does not harvest, edit, translate or publish texts. An Issue means review needed.
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

import requests
from scripts.probe_community_feeds import SITES, USER_AGENT

# Exclude commentary whose titles merely quote a message.
TITLE_PATTERNS = {
    "ru": re.compile(r"^(?:послани[ея]\s+(?:богородиц\w*|цариц\w*|девы марии)|ежегодное послание)\b", re.I),
    "uk": re.compile(r"^(?:послання\s+(?:богородиц\w*|цариц\w*|діви марії)|щорічне послання)\b", re.I),
    "sk": re.compile(r"^(?:posolstvo\s+(?:panny márie|kráľovnej pokoja)|výročné (?:posolstvo|zjavenie))\b", re.I),
    "lv": re.compile(r"^(?:dievmātes.*?\bvēstījums|vēstījums marijai pavlovičai|ikmēneša vēstījums)\b", re.I),
    "en": re.compile(r"^(?:message from the queen of peace|our lady.s message|annual message of our lady|monthly message from)\b", re.I)
}
STRONGLY_RELEVANT_PATHS = {
    "ru": ("/poslaniya-bogorodicy/", "/poslaniya-czariczy-mira/"),
    "uk": ("/poslannya-bogoroditsi/", "/poslannya-czariczi-miru/"),
    "sk": ("/posolstva-kralovnej-pokoja/",),
    "lv": (),
    "en": ("/messages/",)
}
NON_MESSAGE_CATEGORIES = {
    "ru": ("в школе богородицы", "размышления", "новости"),
    "uk": ("у школі богородиці", "роздуми", "новини"),
    "sk": ("v škole panny márie", "úvahy", "aktuality"),
    "lv": ("pārdomas", "aktuāli"),
    "en": ("meditations", "news")
}

def parse_feed(content):
    root = ET.fromstring(content)
    if root.tag.rsplit("}", 1)[-1].lower() != "rss":
        raise ValueError("Expected an RSS 2.0 feed")
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel missing")
    posts = []
    for item in channel.findall("item"):
        def value(tag):
            x = item.find(tag)
            return (x.text or "").strip() if x is not None else ""
        title, link, published = value("title"), value("link"), value("pubDate")
        if not (title and link and published):
            continue
        try:
            dt = parsedate_to_datetime(published)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        posts.append({"title":title, "url":link, "published":dt.astimezone(timezone.utc).isoformat(),
                      "categories":[(x.text or "").strip() for x in item.findall("category")],
                      "guid":value("guid"), "summary":value("description")})
    if not posts:
        raise ValueError("No usable RSS entries; cannot infer no updates")
    return posts

def is_message_candidate(lang, item, origin):
    uri = urlparse(item["url"])
    if uri.scheme != "https" or uri.hostname != urlparse(origin).hostname:
        return False
    lower_title = item["title"].casefold()
    cats = [x.casefold() for x in item["categories"]]
    if any(blocked in cat for cat in cats for blocked in NON_MESSAGE_CATEGORIES[lang]):
        return False
    # A strongly relevant permalink or an explicitly labelled message title.
    path = uri.path.casefold()
    return bool(TITLE_PATTERNS[lang].search(lower_title)) or any(
        segment in path for segment in STRONGLY_RELEVANT_PATHS[lang]
    )

def load_feed(session, origin):
    target = origin + "feed/"
    robots = session.get(origin + "robots.txt", timeout=15, allow_redirects=False)
    if robots.status_code in (401,403,429):
        raise PermissionError(f"robots HTTP {robots.status_code}")
    if robots.status_code not in (200,404):
        raise ConnectionError(f"robots HTTP {robots.status_code}")
    rules = RobotFileParser()
    rules.parse(robots.text.splitlines() if robots.status_code == 200 else [])
    if not rules.can_fetch(USER_AGENT,target):
        raise PermissionError("robots policy forbids feed")
    response = session.get(target,timeout=25, allow_redirects=False)
    if response.status_code in (401,403,429):
        raise PermissionError(f"feed HTTP {response.status_code}")
    if 300 <= response.status_code < 400:
        raise ValueError("Unapproved source redirect; review documented URL")
    response.raise_for_status()
    return parse_feed(response.content)

def inspect_all(since):
    result = {"checked_at_utc":datetime.now(timezone.utc).isoformat(),
              "since_utc":since.isoformat(),"status":"ok",
              "note":"POTENTIAL TRANSLATIONS ONLY — not automatically verified or published",
              "sites":{},"candidates":[]}
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for lang, origin in SITES.items():
        try:
            posts = load_feed(session,origin)
            candidates = [dict(language=lang, notify_new=datetime.fromisoformat(p['published']) >= since, **p) for p in posts
                          if is_message_candidate(lang,p,origin)]
            result["sites"][lang] = {"state":"accessible","items":len(posts),
                                     "candidate_count":len(candidates)}
            result["candidates"].extend(candidates)
        except (requests.RequestException, ConnectionError, ValueError, PermissionError, ET.ParseError) as error:
            result["sites"][lang] = {"state":"failed","error_type":type(error).__name__,
                                     "detail":str(error)[:180]}
            result["status"]="incomplete"
    result["candidates"].sort(key=lambda x:(x["published"],x["language"]),reverse=True)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since",default="2026-10-23T00:00:00+00:00")
    parser.add_argument("--output",type=Path,default=Path("research-output/community-watch.json"))
    args = parser.parse_args()
    since=datetime.fromisoformat(args.since.replace("Z","+00:00"))
    if since.tzinfo is None:
        parser.error("Date needs a timezone")
    report=inspect_all(since.astimezone(timezone.utc))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"sites":report["sites"],
                      "candidates":report["candidates"]},ensure_ascii=False,indent=2))
    return 2 if report["status"] != "ok" else 0

if __name__ == "__main__":
    raise SystemExit(main())
