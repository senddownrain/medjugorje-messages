#!/usr/bin/env python3
"""Import saved, user-authorized HTML archive pages without network requests.

Usage:
  python scripts/import_saved_html.py --ru saved/ru.html --be saved/be.html \
    --uk saved/uk.html --output research-output/offline

The output is RESEARCH ONLY and always marked verified=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import UnicodeDammit

from scripts.sync_messages import LANGUAGES, parse_archive, write_json


def read_html(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Archive not found: {path}")
    raw = path.read_bytes()
    if not raw:
        raise ValueError(f"Empty HTML file: {path}")
    decoded = UnicodeDammit(raw, is_html=True).unicode_markup
    if not decoded:
        raise ValueError(f"Could not decode: {path}")
    return decoded


def import_saved_html(files: dict[str, Path], output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "UNVERIFIED_RESEARCH_IMPORT",
        "method": "provided_local_html",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "languages": {},
        "warnings": [],
    }
    all_records = {}
    for lang in LANGUAGES:
        if lang not in files:
            report["languages"][lang] = {
                "status": "not_provided",
                "unique_messages": 0,
                "missing_ids": [],
                "warnings": ["No saved HTML page was supplied for this language"],
            }
            report["warnings"].append(f"{lang}: no source file provided")
            continue
        source_path = files[lang]
        source_url = f"https://www.medjugorje.ws/{lang}/messages/all"
        try:
            html = read_html(source_path)
            records, expected_ids, problems = parse_archive(html, lang, source_url)
            missing = sorted(expected_ids - records.keys())
            # Source may have been saved from the wrong page or encoding corrupted.
            if not records:
                problems.append("No usable text records detected")
            if missing:
                problems.append(f"{len(missing)} linked messages lack extracted text")
            lang_report = {
                "status": "needs_review" if problems else "parsed_unverified",
                "source_file": source_path.name,
                "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "unique_messages": len(records),
                "linked_ids": len(expected_ids),
                "missing_ids": missing,
                "warnings": problems,
                "first_date": min((r["date"] for r in records.values()), default=None),
                "latest_date": max((r["date"] for r in records.values()), default=None),
            }
            report["languages"][lang] = lang_report
            if problems:
                report["warnings"].append(f"{lang}: extraction gaps or errors")
            all_records[lang] = records
            write_json(output / f"{lang}.json", {
                "language": lang, "verified": False,
                "messages": sorted(records.values(), key=lambda x: (x["date"], x["id"]), reverse=True),
            })
        except (OSError, ValueError) as exc:
            report["languages"][lang] = {
                "status": "failed",
                "source_file": source_path.name,
                "unique_messages": 0,
                "missing_ids": [],
                "warnings": [str(exc)],
            }
            report["warnings"].append(f"{lang}: file cannot be imported")

    index = {}
    for lang, records in all_records.items():
        for message_id, record in records.items():
            row = index.setdefault(message_id, {
                "id": message_id,
                "date": record["date"],
                "type": record["type"],
                "visionary": record["visionary"],
                "languages": [],
            })
            if row["date"] != record["date"] or row["type"] != record["type"]:
                report["warnings"].append(f"{message_id}: cross-language metadata disagreement")
            row["languages"].append(lang)
            if row["visionary"] is None and record["visionary"]:
                row["visionary"] = record["visionary"]

    write_json(output / "index.json", {
        "verified": False, "unique_messages": len(index),
        "messages": sorted(index.values(), key=lambda r: (r["date"], r["id"]), reverse=True),
    })
    write_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for lang in LANGUAGES:
        parser.add_argument(f"--{lang}", type=Path)
    parser.add_argument("--output", type=Path, default=Path("research-output/offline"))
    args = parser.parse_args()
    files = {lang: getattr(args, lang) for lang in LANGUAGES if getattr(args, lang)}
    if not files:
        parser.error("Supply at least one source file: --ru, --be, or --uk.")
    report = import_saved_html(files, args.output)
    print(json.dumps({
        "status": report["status"],
        "counts": {
            lang: data["unique_messages"]
            for lang, data in report["languages"].items()
        },
        "warnings": report["warnings"],
    }, ensure_ascii=False, indent=2))
    return 2 if report["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
