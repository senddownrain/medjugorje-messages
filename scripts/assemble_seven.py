#!/usr/bin/env python3
"""Merge seven language JSONs, reusing old RU/BE/UK data without rewriting them.

Run AFTER importing four new MHTML source files, with input JSONs in data/.
Writes candidate index and diagnostics to a separate output folder.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

LANGUAGES = ("ru", "be", "uk", "hr", "en", "sk", "lv")
ORIGINAL = ("ru", "be", "uk")
EXTRA = ("hr", "en", "sk", "lv")

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def assemble(folder, out):
    original_index = read_json(folder / "index.json")
    if original_index.get("unique_records") != len(original_index.get("messages", [])):
        raise ValueError("Original index has an invalid count")
    old = {r["id"]: r for r in original_index["messages"]}
    if len(old) != len(original_index["messages"]):
        raise ValueError("Original index contains duplicate IDs")
    # Deep copy — do not change any original translation metadata.
    joined = json.loads(json.dumps(old, ensure_ascii=False))
    anomalies, counts = [], {}
    for lang in LANGUAGES:
        file = folder / (lang + ".json")
        dataset = read_json(file)
        if dataset.get("language") != lang or not isinstance(dataset.get("messages"), list):
            raise ValueError("Invalid language JSON: " + str(file))
        entries = dataset["messages"]
        counts[lang] = {"records": len(entries), "with_text": sum(bool(m["text"]) for m in entries)}
        found = set()
        for msg in entries:
            msg_id = msg["id"]
            if msg_id in found:
                raise ValueError("Duplicate canonical ID: " + lang + " / " + msg_id)
            found.add(msg_id)
            if msg.get("language") != lang:
                raise ValueError("Language mismatch: " + msg_id)
            digest = hashlib.sha256(msg.get("text", "").encode("utf-8")).hexdigest()
            if msg.get("text_sha256") != digest:
                raise ValueError("Text SHA mismatch: " + lang + " / " + msg_id)
            current = joined.setdefault(msg_id, {
                "id":msg_id, "date":msg["date"], "type":msg["type"],
                "visionary":msg.get("visionary"), "translations":{}
            })
            if current["date"] != msg["date"] or current["type"] != msg["type"]:
                raise ValueError("Date/type mismatch: " + lang + " / " + msg_id)
            existing = current["translations"].get(lang)
            if lang in ORIGINAL:
                if not existing or existing.get("present") is not True:
                    raise ValueError("Original index missing original text: " + lang + " / " + msg_id)
                if existing.get("text_sha256") != digest:
                    raise ValueError("Original data changed: " + lang + " / " + msg_id)
                if existing.get("source_url") != msg.get("source_url"):
                    raise ValueError("Original source URL changed: " + lang + " / " + msg_id)
                if bool(msg["text"]) != existing.get("has_text"):
                    raise ValueError("Original content flag changed: " + lang + " / " + msg_id)
            else:
                if existing and existing.get("present"):
                    raise ValueError("Target index already has a translation: " + lang + " / " + msg_id)
                current["translations"][lang] = {
                    "present": True, "has_text": bool(msg["text"]),
                    "title": msg["title"], "status":msg["status"],
                    "source_url": msg["source_url"], "source_id":msg["source_id"],
                    "text_sha256":digest
                }
                if not current.get("visionary") and msg.get("visionary"):
                    current["visionary"] = msg["visionary"]
            if not msg.get("text"):
                anomalies.append({"language":lang,"id":msg_id,"reason":"missing_message_text"})
        # Check that no old translation disappeared.
        if lang in ORIGINAL:
            indexed = {r["id"] for r in original_index["messages"]
                       if r["translations"].get(lang, {}).get("present")}
            if found != indexed:
                raise ValueError("Original language has records added/removed: " + lang)
    for msg in joined.values():
        for lang in LANGUAGES:
            msg["translations"].setdefault(lang, {"present":False, "has_text":False})
    for msg_id, previous in old.items():
        new = joined[msg_id]
        for lang in ORIGINAL:
            if new["translations"][lang] != previous["translations"][lang]:
                raise ValueError("Original translation metadata not preserved: " + msg_id + " / " + lang)
    ordered = sorted(joined.values(),key=lambda r:(r["date"], r["id"]),reverse=True)
    new_index = {"verified":False,"unique_records":len(ordered),"messages":ordered}
    summary = {
        "status":"UNVERIFIED_RESEARCH_ARCHIVE",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "original_unique_records":len(old), "union_unique_records":len(ordered),
        "new_unique_records":len(ordered)-len(old), "languages":counts,
        "all_seven_with_text":sum(all(r["translations"][lang]["has_text"] for lang in LANGUAGES)
                                  for r in ordered),
        "original_ru_be_uk_preserved":True,
        "missing_text_records":len(anomalies)
    }
    write_json(out / "index.json",new_index)
    write_json(out / "summary.json",summary)
    write_json(out / "issues.json",anomalies)
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",type=Path,default=Path("data"))
    parser.add_argument("--out",type=Path,default=Path("research-output/seven-language-candidate"))
    args = parser.parse_args()
    print(json.dumps(assemble(args.data,args.out),ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
