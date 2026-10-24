#!/usr/bin/env python3
"""Offline editorial evidence gate for independent language updates.

Reads an explicitly supplied review bundle. NEVER fetches remote content,
changes data/, approves texts, opens PRs, or publishes anything.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit

LANGUAGES = ("ru", "be", "uk", "hr", "en", "sk", "lv")
HEX256 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[^\s\x00-\x1f]{1,255}$")


class GateError(ValueError):
    """A candidate fails a review-only provenance or integrity gate."""


def fail(message):
    raise GateError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def iso_date(value, field, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str):
        fail(field + " must be an ISO date")
    try:
        if date.fromisoformat(value).isoformat() != value:
            fail(field + " must be YYYY-MM-DD")
    except ValueError:
        fail(field + " must be a real YYYY-MM-DD date")


def iso_instant(value, field, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str):
        fail(field + " must be a timezone-aware ISO timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            fail(field + " must include timezone")
    except ValueError:
        fail(field + " must be a valid ISO timestamp")


def https_origin(value):
    if not isinstance(value, str):
        fail("source_url must be a HTTPS URL")
    try:
        uri = urlsplit(value)
        port = uri.port
    except ValueError:
        fail("Malformed source_url")
    if (uri.scheme != "https" or not uri.hostname or uri.username or uri.password
            or uri.fragment or uri.hostname in ("localhost", "127.0.0.1")
            or port not in (None, 443)):
        fail("source_url must be public HTTPS without userinfo, fragment or custom port")
    return uri.hostname.lower()


def safe_snapshot(bundle, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        fail("Snapshot path must use simple POSIX relative segments")
    path = PurePosixPath(relative)
    if (path.is_absolute() or len(path.parts) < 2 or path.parts[0] != "snapshots"
            or any(p in ("", ".", "..") for p in relative.split("/"))):
        fail("Snapshot path must be under snapshots/, without traversal")
    root = bundle.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root / "snapshots") or not candidate.is_file():
        fail("Missing or unsafe snapshot: " + relative)
    if any(p.is_symlink() for p in [root / "snapshots", root / relative]):
        fail("Symlink snapshots are forbidden")
    return candidate.read_bytes()


def validate_registry(registry):
    if registry.get("schema_version") != 1:
        fail("Unsupported source-registry schema")
    languages = registry.get("languages")
    if not isinstance(languages, dict) or set(languages) != set(LANGUAGES):
        fail("Registry must explicitly cover exactly seven languages")
    for lang in LANGUAGES:
        row = languages[lang]
        if not isinstance(row.get("watch_sources"), list) or "text_source" not in row:
            fail("Incomplete registry: " + lang)
        for source in row["watch_sources"]:
            https_origin(source.get("url"))
            if source.get("scope") not in ("metadata_only", "date_and_visible_english_sections"):
                fail("Source scope has not been approved: " + lang)
        if row["text_source"].get("status") not in ("unconfirmed", "manual_source_review_required"):
            fail("Registry must not claim automatic text import approval: " + lang)


def validate_manifest(bundle, registry):
    validate_registry(registry)
    manifest_path = bundle / "manifest.json"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or document.get("status") != "NEEDS_REVIEW":
        fail("Manifest must explicitly be schema 1 / NEEDS_REVIEW")
    candidates = document.get("candidates")
    if not isinstance(candidates, list):
        fail("candidates must be a list")
    seen_source, seen_translation = set(), set()
    languages = {lang: 0 for lang in LANGUAGES}
    for index, item in enumerate(candidates):
        label = "candidate " + str(index)
        if not isinstance(item, dict) or item.get("language") not in LANGUAGES:
            fail(label + ": unsupported language")
        lang = item["language"]
        if item.get("editorial_status") != "needs_review" or item.get("verified") is not False:
            fail(label + ": candidate must be explicitly unverified and pending review")
        if item.get("source_kind") != "manual_snapshot":
            fail(label + ": RSS metadata alone cannot be imported as full text")
        origin = https_origin(item.get("source_url"))
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not IDENTIFIER.fullmatch(source_id):
            fail(label + ": missing stable source_id")
        source_key = (lang, origin, source_id)
        if source_key in seen_source:
            fail(label + ": duplicate language/source identity")
        seen_source.add(source_key)
        canonical_id = item.get("canonical_id")
        if canonical_id is not None:
            if not isinstance(canonical_id, str) or not IDENTIFIER.fullmatch(canonical_id):
                fail(label + ": invalid canonical_id")
            key = (lang, canonical_id)
            if key in seen_translation:
                fail(label + ": duplicate language/canonical_id")
            seen_translation.add(key)
        iso_date(item.get("message_date"), label + ".message_date", nullable=True)
        iso_instant(item.get("published_at"), label + ".published_at", nullable=True)
        if item.get("message_date") is None and not item.get("date_uncertainty"):
            fail(label + ": explain missing message date")
        if item.get("published_at") is None and not item.get("publication_uncertainty"):
            fail(label + ": explain missing source publication date")
        # Preserve independent language publication times: never infer these
        # from a message's date or from other translations.
        snapshot_hash = item.get("snapshot_sha256")
        text_hash = item.get("proposed_text_sha256")
        if not isinstance(snapshot_hash, str) or not HEX256.fullmatch(snapshot_hash):
            fail(label + ": invalid raw snapshot SHA-256")
        if not isinstance(text_hash, str) or not HEX256.fullmatch(text_hash):
            fail(label + ": invalid proposed text SHA-256")
        original = safe_snapshot(bundle, item.get("snapshot_path"))
        if sha256(original) != snapshot_hash:
            fail(label + ": saved original bytes do not match snapshot SHA-256")
        proposed = item.get("proposed_text")
        if not isinstance(proposed, str) or not proposed.strip():
            fail(label + ": proposed_text must be nonempty; never invent absent texts")
        if sha256(proposed.encode("utf-8")) != text_hash:
            fail(label + ": proposed text SHA-256 mismatch")
        if item.get("attribution_status") != "unconfirmed":
            fail(label + ": visionary/type attribution must be reviewed manually")
        if item.get("approved") is not False:
            fail(label + ": a staging candidate cannot approve itself")
        languages[lang] += 1
    return {"status": "REVIEW_ONLY", "source_registry_valid": True,
            "total": len(candidates), "languages": languages,
            "can_import": False, "can_publish": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path,
                        help="Existing folder containing manifest.json and snapshots/")
    parser.add_argument("--registry", type=Path,
                        default=Path("research/update_source_registry.json"))
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    try:
        report = validate_manifest(args.bundle, registry)
    except (GateError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc),
                          "can_import": False, "can_publish": False}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
