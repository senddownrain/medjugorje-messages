#!/usr/bin/env python3
"""Merge RU/BE/UK saved HTML or MHTML archives into offline research JSON and CSV."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.import_mhtml import load_html, parse_page, LANGS

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def write_csv(path, fields, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        w.writerows(data)

def combine_sources(sources, output):
    if set(sources) != set(LANGS):
        raise ValueError("Missing required RU/BE/UK files")
    langs, reports = {}, {}
    for lang in LANGS:
        html, url = load_html(sources[lang])
        if url and f"/{lang}/messages/all" not in url:
            raise ValueError(f"Wrong source language: {lang}: {url}")
        messages, report = parse_page(html, lang)
        if not messages or len({m["id"] for m in messages}) != len(messages):
            raise ValueError(f"Missing or duplicate canonical IDs in {lang}")
        langs[lang] = {m["id"]: m for m in messages}
        reports[lang] = report
        write_json(output / "data" / (lang + ".json"),
                   {"language": lang, "verified": False, "messages": messages})
        write_json(output / "reports" / (lang + "_report.json"), report)

    index, issues, combos = [], [], Counter()
    for lang, report in reports.items():
        for a in report["anomalies"]:
            issues.append({
                "language": lang, "reason": a.get("reason", ""),
                "id": a.get("id") or a.get("derived_id") or a.get("source_id") or "",
                "date": a.get("date") or "",
                "details": json.dumps(a, ensure_ascii=False)
            })
    for id in set().union(*(set(t) for t in langs.values())):
        v = {lang: langs[lang].get(id) for lang in LANGS}
        known = [rec for rec in v.values() if rec]
        if len({rec["date"] for rec in known}) != 1 or len({rec["type"] for rec in known}) != 1:
            raise ValueError(f"Conflicting message metadata: {id}")
        visionaries = {rec["visionary"] for rec in known if rec["visionary"]}
        if len(visionaries) > 1:
            issues.append({"language": "all", "reason": "visionary_disagreement",
                           "id": id, "date": known[0]["date"], "details": str(sorted(visionaries))})
        combos[tuple(lang for lang in LANGS if v[lang])] += 1
        index.append({
            "id": id, "date": known[0]["date"], "type": known[0]["type"],
            "visionary": next(iter(visionaries)) if len(visionaries) == 1 else None,
            "translations": {
                lang: ({
                    "present": True, "has_text": bool(rec["text"]),
                    "source_url": rec["source_url"], "source_id": rec["source_id"],
                    "title": rec["title"], "status": rec["status"],
                    "text_sha256": rec["text_sha256"]
                } if rec else {"present": False, "has_text": False})
                for lang, rec in v.items()
            }
        })
    index.sort(key=lambda rec: (rec["date"], rec["id"]), reverse=True)
    write_json(output / "data/index.json",
               {"verified": False, "unique_records": len(index), "messages": index})
    fields = ["id", "date", "type", "visionary"] + [
        lang + suffix for lang in LANGS for suffix in ("_present", "_text", "_url")
    ]
    csv_index, absent, by_year = [], [], Counter()
    for row in index:
        rec = {k: row.get(k) or "" for k in ("id", "date", "type", "visionary")}
        available = [lang for lang in LANGS if row["translations"][lang]["present"]]
        for lang in LANGS:
            t = row["translations"][lang]
            rec[lang + "_present"] = int(t["present"])
            rec[lang + "_text"] = int(t["has_text"])
            rec[lang + "_url"] = t.get("source_url", "")
            if t["present"]:
                by_year[(row["date"][:4], lang, "records")] += 1
                by_year[(row["date"][:4], lang, "text")] += int(t["has_text"])
            else:
                absent.append({
                    "id": row["id"], "date": row["date"], "type": row["type"],
                    "absent_language": lang, "present_languages": ",".join(available)
                })
        csv_index.append(rec)
    write_csv(output / "reports/index.csv", fields, csv_index)
    write_csv(output / "reports/absent_in_saved_language_archive.csv",
              ["id", "date", "type", "absent_language", "present_languages"], absent)
    write_csv(output / "reports/by_year.csv",
              ["year", "language", "records", "with_text"],
              [{"year": year, "language": lang,
                "records": by_year[(year, lang, "records")],
                "with_text": by_year[(year, lang, "text")]}
               for year in sorted({x["date"][:4] for x in index}) for lang in LANGS])
    write_json(output / "reports/issues.json", issues)
    write_csv(output / "reports/issues.csv",
              ["language", "reason", "id", "date", "details"], issues)
    summary = {
        "status": "UNVERIFIED_SAVED_SNAPSHOT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "unique_records": len(index), "all_three": combos[LANGS],
        "languages": {lang: {
            "records": rep["records"], "with_text": rep["records_with_text"],
            "without_text": rep["records_without_text"],
            "first": rep["date_first"], "last": rep["date_last"]
        } for lang, rep in reports.items()},
        "issues_count": len(issues), "verified": False
    }
    write_json(output / "reports/summary.json", summary)
    return summary

def main():
    p = argparse.ArgumentParser()
    for lang in LANGS:
        p.add_argument("--" + lang, type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("research-output/combined"))
    args = p.parse_args()
    print(json.dumps(combine_sources({lang: getattr(args, lang) for lang in LANGS},
                                     args.output), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
