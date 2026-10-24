#!/usr/bin/env python3
"""Strict append-only gate for proposed seven-language archives.

Requires explicit old/new directories. Reads JSON only; never writes either
directory and never approves or deploys texts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

LANGUAGES = ("ru", "be", "uk", "hr", "en", "sk", "lv")


class AppendOnlyError(ValueError):
    pass


def reject(message):
    raise AppendOnlyError(message)


def load_archives(folder):
    data = {}
    for lang in LANGUAGES:
        file = folder / (lang + ".json")
        value = json.loads(file.read_text(encoding="utf-8"))
        if value.get("language") != lang or not isinstance(value.get("messages"), list):
            reject("Invalid language archive: " + lang)
        data[lang] = value
    index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    if not isinstance(index.get("messages"), list):
        reject("Invalid union index")
    return data, index


def keyed(rows, label):
    values = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            reject(label + " has missing ID")
        key = row["id"]
        if key in values:
            reject(label + " duplicate ID: " + key)
        values[key] = row
    return values


def gate(baseline, proposed):
    before_lang, before_index = load_archives(baseline)
    after_lang, after_index = load_archives(proposed)
    old_index = keyed(before_index["messages"], "baseline index")
    new_index = keyed(after_index["messages"], "proposed index")
    if set(old_index) - set(new_index):
        reject("Index deletes existing canonical IDs")
    if after_index.get("unique_records") != len(new_index):
        reject("Proposed index count mismatch")
    added_language_records = {}
    additions_by_language = {}
    for lang in LANGUAGES:
        old_rows = keyed(before_lang[lang]["messages"], lang + " baseline")
        new_rows = keyed(after_lang[lang]["messages"], lang + " proposed")
        if set(old_rows) - set(new_rows):
            reject(lang + " removes existing translations")
        for key, original in old_rows.items():
            if new_rows[key] != original:
                reject(lang + " changes an existing translation (even punctuation/metadata): " + key)
        additions = set(new_rows) - set(old_rows)
        additions_by_language[lang] = len(additions)
        added_language_records[lang] = additions
        for key in additions:
            m = new_rows[key]
            row = new_index.get(key)
            if row is None or not row.get("translations", {}).get(lang, {}).get("present"):
                reject(lang + " addition lacks explicit index presence: " + key)
            if m.get("language") != lang or m.get("date") != row.get("date") or m.get("type") != row.get("type"):
                reject(lang + " addition has incompatible language, date or type: " + key)
            digest = hashlib.sha256(m.get("text", "").encode("utf-8")).hexdigest()
            if m.get("text_sha256") != digest:
                reject(lang + " addition has invalid text checksum: " + key)
            index_digest = row["translations"][lang].get("text_sha256")
            if index_digest != digest:
                reject(lang + " index has incompatible text checksum: " + key)
            if row["translations"][lang].get("has_text") != bool(m.get("text")):
                reject(lang + " index has incompatible text presence: " + key)
    for key, original in old_index.items():
        next_row = new_index[key]
        if {k: v for k, v in original.items() if k != "translations"} != {
                k: v for k, v in next_row.items() if k != "translations"}:
            reject("Existing canonical metadata/attribution changed: " + key)
        previous_translations = original.get("translations", {})
        current_translations = next_row.get("translations", {})
        for lang in LANGUAGES:
            old = previous_translations.get(lang, {"present": False, "has_text": False})
            new = current_translations.get(lang)
            if new is None:
                reject("Translation metadata missing: " + lang + " / " + key)
            if old == new:
                continue
            if old.get("present") or not new.get("present"):
                reject("Existing translation metadata mutated: " + lang + " / " + key)
            if key not in added_language_records[lang]:
                reject("Translation presence changed without appended text: " + lang + " / " + key)
    for key, row in new_index.items():
        if key not in old_index and not any(key in added_language_records[l] for l in LANGUAGES):
            reject("New index-only ID without any appended translation: " + key)
        for lang in LANGUAGES:
            item = row.get("translations", {}).get(lang)
            if item is None:
                reject("Incomplete seven-language index: " + lang + " / " + key)
            in_archive = key in keyed(after_lang[lang]["messages"], lang + " proposed")
            if bool(item.get("present")) != in_archive:
                reject("Index and language archive disagree: " + lang + " / " + key)
    return {"status": "APPEND_ONLY_PASS", "new_canonical_ids": len(new_index) - len(old_index),
            "new_translations": additions_by_language, "can_merge": False, "can_publish": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = gate(args.baseline, args.candidate)
    except (AppendOnlyError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc),
                          "can_merge": False, "can_publish": False}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
