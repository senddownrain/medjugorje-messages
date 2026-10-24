#!/usr/bin/env python3
"""Offline, read-only audit. Writes reports only; never repairs archive data."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from scripts.import_mhtml import LANGS, TYPES, load_html, parse_page
from scripts.audit_source_snapshots import attach_source_evidence
from scripts.audit_thematic_snapshots import attach_thematic_evidence


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


# These are reviewable evidence selections, not a general-purpose name classifier.
EVIDENCE = (
    ("060908s", "en", "title", "to Ivan", "ivan"),
    ("140812s", "uk", "title", "- Ivan", "ivan"),
    ("050402s", "lv", "title", "Mirjamai", "mirjana"),
    ("850114w", "hr", "title", "preko Vicke", "vicka"),
    ("850114w", "en", "context", "Message conveyed by Vicka", "vicka"),
    ("850114w", "ru", "context", "переданное через Вицку", "vicka"),
    ("850114w", "sk", "context", "prostredníctvom Vicky", "vicka"),
    ("850114w", "lv", "context", "caur vizionāri Vicku", "vicka"),
    ("840814w", "hr", "context", "Ivan je molio", "ivan"),
    ("840814w", "en", "context", "Ivan was praying at home", "ivan"),
    ("840814w", "ru", "context", "Визионер Иван", "ivan"),
    ("841008w", "en", "context", "Jakov was sick and received this message", "jakov"),
    ("841008w", "sk", "context", "Jakov bol chorý a doma dostal posolstvo", "jakov"),
    ("850625w", "lv", "context", "caur Mariju Pavloviču", "marija"),
    ("850625w", "en", "context", "in response to the question of Marija Pavlović", "marija"),
    ("840430w", "en", "context", "Our Lady replied", "marija"),
    ("840430w", "hr", "context", "Vidjelica Marija pitala je Gospu", "marija"),
    ("850405w", "hr", "title", "preko Ivanke", "ivanka"),
    ("850405w", "en", "context", "Message given through Ivanka", "ivanka"),
    ("850507a", "en", "title", "to Ivanka", "ivanka"),
    ("980912a", "en", "title", "to Jakov", "jakov"),
    ("100101s", "en", "title", "to Marija", "marija"),
)


def audit_data(folder):
    folder = Path(folder)
    index_doc = read(folder / "index.json")
    index = index_doc["messages"]
    archives = {lang: read(folder / f"{lang}.json") for lang in LANGS}
    anomalies, violations, gaps, inventory, proposals = [], [], [], [], []
    by_id = {r["id"]: r for r in index}
    if len(by_id) != len(index) or index_doc["unique_records"] != len(index):
        violations.append({"reason": "invalid_index_count_or_duplicate_id"})
    language_maps = {}
    hashes = {p.name: digest(p.read_bytes()) for p in [folder / "index.json", *[folder / f"{l}.json" for l in LANGS]]}
    for lang, doc in archives.items():
        rows = doc["messages"]
        mapping = {r["id"]: r for r in rows}
        language_maps[lang] = mapping
        if len(mapping) != len(rows) or doc.get("language") != lang:
            violations.append({"reason": "duplicate_id_or_invalid_language", "language": lang})
        urls = defaultdict(list)
        for row in rows:
            key = row["id"]
            base = {"language": lang, "id": key, "source_url": row["source_url"]}
            root = by_id.get(key)
            meta = root.get("translations", {}).get(lang, {}) if root else {}
            checks = {
                "indexed": root is not None,
                "language": row.get("language") == lang,
                "date": root is not None and root["date"] == row["date"],
                "type": root is not None and root["type"] == row["type"],
                "text_sha256": digest(row["text"].encode()) == row["text_sha256"],
                "segments": "\n\n".join(s["text"] for s in row["segments"] if s["kind"] == "message") == row["text"],
            }
            for field in ("title", "status", "source_url", "source_id", "text_sha256"):
                checks["index_" + field] = meta.get(field) == row.get(field)
            checks["index_present"] = meta.get("present") is True
            checks["index_has_text"] = meta.get("has_text") == bool(row["text"])
            for field, passed in checks.items():
                if not passed:
                    violations.append({**base, "reason": "integrity_mismatch", "field": field})
            urls[row["source_url"]].append(key)
            parsed = urlparse(row["source_url"])
            if (parsed.hostname not in ("medjugorje.ws", "www.medjugorje.ws") or
                    parsed.path.rstrip("/") != f"/{lang}/messages/{row['source_id']}"):
                anomalies.append({**base, "reason": "invalid_source_url"})
            expected_id = row["date"][2:].replace("-", "") + row["source_id"][6:]
            if expected_id != key or TYPES.get(row["source_id"][6:7]) != row["type"]:
                violations.append({**base, "reason": "canonical_id_or_type_mismatch"})
            if key != row["source_id"]:
                anomalies.append({**base, "reason": "source_url_date_mismatch", "source_id": row["source_id"], "date": row["date"]})
            if not row["text"]:
                anomalies.append({**base, "reason": "record_without_message_text", "stored_status": row["status"]})
            if root and row.get("visionary") != root.get("visionary"):
                anomalies.append({**base, "reason": "language_index_visionary_difference", "language_value": row.get("visionary"), "index_value": root.get("visionary")})
        for url, keys in urls.items():
            if len(keys) > 1:
                anomalies.append({"reason": "duplicate_source_url", "language": lang, "source_url": url, "ids": keys})
        for root in index:
            present = root["id"] in mapping
            if root.get("translations", {}).get(lang, {}).get("present") != present:
                violations.append({"reason": "presence_mismatch", "id": root["id"], "language": lang})
            if not present:
                gaps.append({"reason": "translation-not-present", "id": root["id"], "language": lang,
                             "meaning": "Нет записи в языковом JSON; отсутствие в исходнике пока не установлено."})
    evidence = defaultdict(list)
    for key, lang, field, needle, person in EVIDENCE:
        row = language_maps[lang].get(key)
        if not row:
            continue
        values = [(row["title"], "title")] if field == "title" else [
            (s["text"], f"segments/{n}/text") for n, s in enumerate(row["segments"]) if s["kind"] == field]
        found = [(value, pointer) for value, pointer in values if needle in value]
        if not found:
            violations.append({"reason": "expected_evidence_missing", "id": key, "language": lang, "field": field})
        for value, pointer in found:
            evidence[key].append({"visionary": person, "language": lang, "field": field, "quote": value,
                                  "source_url": row["source_url"], "source_id": row["source_id"],
                                  "json_pointer": f"/messages/{archives[lang]['messages'].index(row)}/{pointer}",
                                  "artifact": f"data/{lang}.json", "artifact_sha256": hashes[f"{lang}.json"]})
    for root in index:
        key = root["id"]
        try:
            date.fromisoformat(root["date"])
        except ValueError:
            violations.append({"reason": "invalid_calendar_date", "id": key, "date": root["date"]})
        ev = evidence[key]
        people = {e["visionary"] for e in ev}
        if len(people) == 1 and root.get("visionary") not in people:
            proposals.append({"id": key, "date": root["date"], "field": "visionary", "before": root.get("visionary"),
                              "proposed": next(iter(people)), "confidence": "explicit_imported_source_evidence",
                              "review_status": "pending_original_mhtml_and_editorial_review", "evidence": ev,
                              "applied": False})
        inventory.append({"id": key, "date": root["date"], "type": root["type"], "visionary": root.get("visionary"),
                          "series": None, "series_review_status": "not_verified_against_source_sections",
                          "languages_present": [l for l in LANGS if key in language_maps[l]],
                          "languages_with_text": [l for l in LANGS if key in language_maps[l] and language_maps[l][key]["text"]],
                          "source_metadata": {l: {f: language_maps[l][key].get(f) for f in
                              ("title", "source_url", "source_id", "date", "type", "visionary", "status", "source_position", "text_sha256")}
                              for l in LANGS if key in language_maps[l]},
                          "evidence": ev})
    summary = {
        "status": "INCOMPLETE_SOURCE_AUDIT", "unique_records": len(index),
        "integrity_violations": len(violations), "type_counts": dict(Counter(r["type"] for r in index)),
        "visionary_counts": dict(Counter(r.get("visionary") or "unattributed" for r in index)),
        "languages": {l: {"records": len(d["messages"]), "with_text": sum(bool(r["text"]) for r in d["messages"]),
                          "without_text": sum(not r["text"] for r in d["messages"]),
                          "translation_not_present": len(index) - len(d["messages"]),
                          "first_date": min(r["date"] for r in d["messages"]), "last_date": max(r["date"] for r in d["messages"])} for l, d in archives.items()},
        "anomaly_counts": dict(Counter(r["reason"] for r in anomalies)),
        "proposal_count": len(proposals), "file_sha256": hashes,
        "unattributed_weekly_ids": [r["id"] for r in index if r["type"] == "weekly" and r.get("visionary") is None],
    }
    return {"summary": summary, "inventory": inventory, "anomalies": anomalies, "violations": violations,
            "translation_not_present": gaps, "proposals": proposals}


def compare_saved_source(path, expected_url, language, category, records):
    """Compare actual dated message headings, never navigation link occurrences.

    Fail closed if a category page is a link-only landing page. Its section pages
    must be supplied separately before completeness can be assessed.
    """
    html, location = load_html(path)
    result = {"path": str(path), "source_sha256": digest(Path(path).read_bytes()),
              "expected_url": expected_url, "content_location": location, "language": language,
              "category": category, "status": "NOT_CHECKED", "issues": []}
    if not location or location.rstrip("/") != expected_url.rstrip("/"):
        result["status"] = "SOURCE_IDENTITY_NOT_CONFIRMED"
        return result
    try:
        parsed, report = parse_page(html, language)
    except ValueError as error:
        result.update(status="SOURCE_CONTENT_NOT_COMPARABLE", error=str(error))
        return result
    result["parser_anomalies"] = report["anomalies"]
    result["source_records"] = len(parsed)
    result["source_ids"] = sorted(r["id"] for r in parsed)
    if not parsed:
        result["status"] = "SOURCE_CONTENT_NOT_COMPARABLE"
        return result
    soup = BeautifulSoup(html, "html.parser")
    # Keep section labels verbatim as evidence. No guessed person/series mapping.
    section, headings = None, []
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        if "poselstvi-datum" in (tag.get("class") or []):
            a = tag.find("a", href=True)
            headings.append({"title": tag.get_text(" ", strip=True), "source_url": a["href"] if a else None, "section": section})
        else:
            section = tag.get_text(" ", strip=True)
    result["source_headings"] = headings
    saved = {r["id"]: r for r in parsed}
    target = {r["id"]: r for r in records}
    fields = ("date", "type", "source_id", "source_url", "title", "text", "segments", "text_sha256")
    for row in parsed:
        current = target.get(row["id"])
        if current is None:
            result["issues"].append({"reason": "source-missing", "id": row["id"], "source_url": row["source_url"],
                                     "meaning": "Запись есть в сохранённом источнике, но отсутствует в языковом JSON."})
        else:
            changed = [f for f in fields if row[f] != current[f]]
            if changed:
                result["issues"].append({"reason": "saved_source_record_difference", "id": row["id"], "fields": changed})
    # Reverse set comparison only valid for a whole-language /all snapshot.
    # A category snapshot may be one section/page of a paginated archive.
    if category == "all":
        result["json_ids_not_in_saved_source"] = sorted(set(target) - set(saved))
    result["status"] = "COMPARED_REQUIRES_COVERAGE_REVIEW"
    return result


def audit_sources(manifest_path, folder):
    if manifest_path is None:
        return {"status": "NOT_PROVIDED", "sources": [], "missing_required": [f"{l}/all" for l in LANGS] + [f"{l}/{c}" for l in ("en", "hr") for c in ("annual", "special")]}
    manifest_path = Path(manifest_path)
    manifest = read(manifest_path)
    sources = []
    for spec in manifest["sources"]:
        lang, cat = spec["language"], spec["category"]
        if lang not in LANGS or cat not in ("all", "annual", "special"):
            raise ValueError("Unsupported source language/category")
        parsed_url = urlparse(spec["url"])
        if (parsed_url.hostname not in ("medjugorje.ws", "www.medjugorje.ws") or
                not re.fullmatch(rf"/{lang}/messages/{cat}(?:/[^?#]*)?", parsed_url.path)):
            raise ValueError("Source URL does not match its language/category")
        sources.append(compare_saved_source(manifest_path.parent / spec["path"], spec["url"], lang, cat, read(Path(folder) / f"{lang}.json")["messages"]))
    provided = {f"{s['language']}/{s['category']}" for s in sources if s["status"] == "COMPARED_REQUIRES_COVERAGE_REVIEW"}
    required = {f"{l}/all" for l in LANGS} | {f"{l}/{c}" for l in ("en", "hr") for c in ("annual", "special")}
    return {"status": "REQUIRES_MANUAL_SECTION_AND_PAGINATION_REVIEW", "sources": sources, "missing_required": sorted(required - provided)}


def write_reports(report, out):
    out.mkdir(parents=True, exist_ok=True)
    for name, value in report.items():
        (out / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "proposals.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, lineterminator="\n", fieldnames=("id", "date", "field", "before", "proposed", "confidence", "review_status", "applied", "evidence", "source_group_evidence"))
        writer.writeheader()
        for row in report["proposals"]:
            writer.writerow({**row, "before": json.dumps(row["before"]), "evidence": json.dumps(row["evidence"], ensure_ascii=False),
                             "source_group_evidence": json.dumps(row.get("source_group_evidence", []), ensure_ascii=False)})


def build_report(folder, source_zip=None, manifest=None, thematic_zip=None):
    report = audit_data(folder)
    if source_zip:
        report = attach_source_evidence(report, source_zip, folder)
        return attach_thematic_evidence(report, thematic_zip, folder) if thematic_zip else report
    if thematic_zip:
        raise ValueError("Thematic coverage requires the original seven-source ZIP too")
    report["sources"] = audit_sources(manifest, folder)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    source_args = parser.add_mutually_exclusive_group()
    source_args.add_argument("--sources", type=Path, help="Local JSON manifest of saved source MHTML files")
    source_args.add_argument("--source-zip", type=Path, help="Original seven-source ZIP, verified independently")
    parser.add_argument("--thematic-zip", type=Path, help="Four original thematic snapshots plus reference audit")
    parser.add_argument("--out", type=Path, default=Path("reports/stage-a"))
    args = parser.parse_args()
    # Prevent an accidental report destination from touching original inputs.
    out = args.out.resolve()
    protected = args.data.resolve()
    if out == protected or protected in out.parents or out in protected.parents:
        parser.error("Output must be separate from the input data directory")
    if args.sources:
        manifest = read(args.sources)
        inputs = [args.sources, *[args.sources.parent / s["path"] for s in manifest["sources"]]]
        if any(out == p.resolve() or out in p.resolve().parents for p in inputs):
            parser.error("Output must not contain source inputs or their manifest")
    if args.source_zip and (out == args.source_zip.resolve() or out in args.source_zip.resolve().parents):
        parser.error("Output must not contain the source ZIP")
    if args.thematic_zip and (not args.source_zip or out == args.thematic_zip.resolve() or out in args.thematic_zip.resolve().parents):
        parser.error("Thematic ZIP requires --source-zip and must be outside the output directory")
    if args.thematic_zip and not args.thematic_zip.is_file():
        parser.error("Thematic ZIP is unavailable; source snapshot coverage was not verified")
    report = build_report(args.data, args.source_zip, args.sources, args.thematic_zip)
    write_reports(report, out)
    print(json.dumps({k: v for k, v in report["summary"].items() if k not in
                      ("file_sha256", "unattributed_weekly_ids")}, ensure_ascii=False, indent=2))
    if report["summary"]["status"] == "VERIFIED_SOURCE_SNAPSHOT_COVERAGE":
        return 0  # Technical snapshot coverage only; editorial approval is independent.
    if report["summary"]["status"] == "SOURCE_REVIEW_REQUIRED":
        return 1
    # Exit 2 means source audit pending; it must never be mistaken for completion.
    return 1 if report["violations"] or report["sources"]["status"] in (
        "SAVED_SOURCE_DIFFERENCES_REQUIRE_REVIEW", "SOURCE_BLOCKS_REQUIRE_REVIEW") else 2


if __name__ == "__main__":
    raise SystemExit(main())
