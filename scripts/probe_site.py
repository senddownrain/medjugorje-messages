#!/usr/bin/env python3
"""Check whether GitHub Actions can read the site's own public update index.

DIAGNOSTIC ONLY: no downloads of full texts, no circumvention, no publishing.
If access is blocked, the report is BLOCKED, never 'no new messages'.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

ORIGINS = ("https://www.medjugorje.ws", "https://text.medjugorje.ws")
MESSAGE_ID = re.compile(r"^\d{6}[a-z][a-z0-9_-]*$", re.I)
USER_AGENT = "MedjugorjeArchiveResearch/0.2 (contact: https://github.com/senddownrain/medjugorje-messages)"


def parse_listing(html: str, lang: str, origin: str):
    soup = BeautifulSoup(html, "html.parser")
    ids = set()
    for a in soup.select("a[href]"):
        url = urlparse(urljoin(origin, a["href"]))
        p = url.path.rstrip("/").split("/")
        if len(p) == 4 and p[0] == "" and p[1] == lang and p[2] == "messages" and MESSAGE_ID.fullmatch(p[3]):
            if url.netloc in ("www.medjugorje.ws", "text.medjugorje.ws"):
                ids.add(p[3].lower())
    return sorted(ids)


def probe_origin(origin, session):
    robots_url = origin + "/robots.txt"
    try:
        robots = session.get(robots_url, timeout=15)
        if robots.status_code in (401, 403, 429):
            return {"origin": origin, "state": "blocked", "at": "robots.txt", "http_status": robots.status_code}
        if robots.status_code not in (200, 404):
            return {"origin": origin, "state": "unavailable", "at": "robots.txt", "http_status": robots.status_code}
        policy = RobotFileParser()
        policy.parse(robots.text.splitlines() if robots.status_code == 200 else [])
        target = origin + "/en/messages/list"
        if not policy.can_fetch(USER_AGENT, target):
            return {"origin": origin, "state": "blocked", "at": "robots_policy"}
        resp = session.get(target, timeout=25)
        if resp.status_code in (401, 403, 429):
            return {"origin": origin, "state": "blocked", "at": "message_listing", "http_status": resp.status_code}
        if resp.status_code != 200:
            return {"origin": origin, "state": "unavailable", "at": "message_listing", "http_status": resp.status_code}
        if "html" not in resp.headers.get("content-type", "").lower():
            return {"origin": origin, "state": "unexpected_content_type"}
        ids = parse_listing(resp.text, "en", origin)
        if not ids:
            return {"origin": origin, "state": "unparseable", "message": "No message links in page"}
        return {"origin": origin, "state": "accessible", "ids_found": len(ids), "latest_ids": ids[-5:]}
    except requests.RequestException as exc:
        return {"origin": origin, "state": "unavailable", "exception_type": type(exc).__name__}


def run(path: Path):
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    report = {
        "type": "diagnostic_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "probes": [probe_origin(origin, session) for origin in ORIGINS]
    }
    report["source_status"] = (
        "access_available" if any(p["state"] == "accessible" for p in report["probes"])
        else "blocked_or_unavailable"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run(Path("research-output/access-probe.json"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
