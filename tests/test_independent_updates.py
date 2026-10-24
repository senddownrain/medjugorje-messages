"""Offline safety tests for independent seven-language update staging and append-only gates."""
import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.check_append_only_updates import AppendOnlyError, gate
from scripts.update_candidate_gate import GateError, validate_manifest, validate_registry

LANGS = ("ru", "be", "uk", "hr", "en", "sk", "lv")
DATE = "2026-09-25"
CANONICAL = "2026-09-25-monthly"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def blank_translation():
    return {"present": False, "has_text": False}


def message(lang, key=CANONICAL, text="Original message"):
    return {
        "id": key, "date": DATE, "language": lang, "type": "monthly",
        "title": "25 September", "visionary": None, "text": text,
        "text_sha256": digest(text), "source_id": "saved-" + lang,
        "source_url": "https://example.org/messages/" + key, "status": "unverified"
    }


def present(m):
    return {
        "present": True, "has_text": bool(m["text"]), "title": m["title"],
        "text_sha256": m["text_sha256"], "source_id": m["source_id"],
        "source_url": m["source_url"], "status": m["status"]
    }


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "bundle"
        (self.bundle / "snapshots").mkdir(parents=True)
        (self.bundle / "snapshots" / "original.txt").write_bytes(b"Source bytes: Hello")
        self.registry = json.loads(Path("research/update_source_registry.json").read_text(encoding="utf-8"))
        self.candidate = {
            "language": "en", "canonical_id": CANONICAL,
            "message_date": DATE, "published_at": "2026-09-26T12:00:00+00:00",
            "source_url": "https://www.medjugorje.hr/en/our-lady-messages-archive",
            "source_kind": "manual_snapshot", "source_id": "official-section-25",
            "snapshot_path": "snapshots/original.txt",
            "snapshot_sha256": hashlib.sha256(b"Source bytes: Hello").hexdigest(),
            "proposed_text": "Hello", "proposed_text_sha256": digest("Hello"),
            "editorial_status": "needs_review", "verified": False,
            "approved": False, "attribution_status": "unconfirmed"
        }

    def validate(self, candidate=None):
        dump(self.bundle / "manifest.json", {
            "schema_version": 1, "status": "NEEDS_REVIEW",
            "candidates": [candidate or self.candidate]
        })
        return validate_manifest(self.bundle, self.registry)

    def test_registry_seven_independent_languages(self):
        validate_registry(self.registry)
        self.assertEqual(set(self.registry["languages"]), set(LANGS))
        self.assertEqual(self.registry["languages"]["be"]["watch_sources"], [])
        self.assertEqual(self.registry["languages"]["hr"]["watch_sources"], [])

    def test_offline_manifest_valid_but_never_approved(self):
        report = self.validate()
        self.assertEqual(report["status"], "REVIEW_ONLY")
        self.assertFalse(report["can_import"])
        self.assertFalse(report["can_publish"])

    def test_changed_original_source_bytes_blocked(self):
        self.validate()
        (self.bundle / "snapshots" / "original.txt").write_bytes(b"tampered")
        with self.assertRaisesRegex(GateError, "original bytes"):
            self.validate()

    def test_changed_proposed_text_blocked(self):
        candidate = {**self.candidate, "proposed_text": "Changed punctuation!"}
        with self.assertRaisesRegex(GateError, "text SHA-256 mismatch"):
            self.validate(candidate)

    def test_traversal_is_blocked(self):
        candidate = {**self.candidate, "snapshot_path": "snapshots/../../secrets.txt"}
        with self.assertRaisesRegex(GateError, "traversal"):
            self.validate(candidate)

    def test_http_or_fake_source_is_blocked(self):
        candidate = {**self.candidate, "source_url": "http://example.org/msg"}
        with self.assertRaises(GateError):
            self.validate(candidate)

    def test_missing_timezone_is_blocked(self):
        candidate = {**self.candidate, "published_at": "2026-09-26T12:00:00"}
        with self.assertRaisesRegex(GateError, "timezone"):
            self.validate(candidate)

    def test_unknown_date_must_be_explained(self):
        candidate = {**self.candidate, "message_date": None}
        with self.assertRaisesRegex(GateError, "explain missing message date"):
            self.validate(candidate)

    def test_unknown_date_may_remain_unknown_if_explicit(self):
        candidate = {**self.candidate, "message_date": None, "date_uncertainty": "Not proven"}
        self.assertEqual(self.validate(candidate)["total"], 1)

    def test_rss_metadata_cannot_claim_to_be_full_text(self):
        candidate = {**self.candidate, "source_kind": "community_rss"}
        with self.assertRaisesRegex(GateError, "RSS metadata"):
            self.validate(candidate)

    def test_staging_can_never_self_approve(self):
        for changes in ({"approved": True}, {"verified": True},
                        {"editorial_status": "verified"}, {"attribution_status": "verified"}):
            with self.subTest(changes=changes), self.assertRaises(GateError):
                self.validate({**self.candidate, **changes})

    def test_duplicate_same_source_language_blocked(self):
        dump(self.bundle / "manifest.json", {
            "schema_version": 1, "status": "NEEDS_REVIEW",
            "candidates": [self.candidate, deepcopy(self.candidate)]
        })
        with self.assertRaisesRegex(GateError, "duplicate language/source"):
            validate_manifest(self.bundle, self.registry)

    def test_duplicate_canonical_id_language_blocked(self):
        other = {**self.candidate, "source_id": "other-section"}
        dump(self.bundle / "manifest.json", {
            "schema_version": 1, "status": "NEEDS_REVIEW",
            "candidates": [self.candidate, other]
        })
        with self.assertRaisesRegex(GateError, "duplicate language/canonical_id"):
            validate_manifest(self.bundle, self.registry)

    def test_publication_date_independent_from_message_date(self):
        candidate = {**self.candidate, "message_date": "2026-10-01",
                     "published_at": "2026-10-23T17:03:00Z"}
        self.assertEqual(self.validate(candidate)["total"], 1)


class AppendOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.before, self.after = root / "before", root / "after"
        english = message("en")
        old_index = {
            "verified": False, "unique_records": 1, "messages": [{
                "id": CANONICAL, "date": DATE, "type": "monthly", "visionary": None,
                "translations": {lang: present(english) if lang == "en" else blank_translation()
                                 for lang in LANGS}
            }]
        }
        for folder in (self.before, self.after):
            dump(folder / "index.json", old_index)
            for lang in LANGS:
                dump(folder / (lang + ".json"), {"language": lang, "verified": False,
                     "messages": [english] if lang == "en" else []})

    def load(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def add_translation(self):
        ru = message("ru", text="Новый русский перевод")
        path = self.after / "ru.json"
        archive = self.load(path)
        archive["messages"].append(ru)
        dump(path, archive)
        index = self.load(self.after / "index.json")
        index["messages"][0]["translations"]["ru"] = present(ru)
        dump(self.after / "index.json", index)
        return ru

    def test_existing_data_self_comparison_is_safe(self):
        result = gate(self.before, self.after)
        self.assertEqual(result["new_canonical_ids"], 0)
        self.assertFalse(result["can_merge"])

    def test_appends_new_language_independently(self):
        self.add_translation()
        self.assertEqual(gate(self.before, self.after)["new_translations"]["ru"], 1)

    def test_blocks_change_to_existing_translation_even_with_recomputed_hash(self):
        english_path = self.after / "en.json"
        archive = self.load(english_path)
        archive["messages"][0]["text"] += "!"
        archive["messages"][0]["text_sha256"] = digest(archive["messages"][0]["text"])
        dump(english_path, archive)
        with self.assertRaisesRegex(AppendOnlyError, "changes an existing translation"):
            gate(self.before, self.after)

    def test_blocks_existing_metadata_changes(self):
        index_path = self.after / "index.json"
        index = self.load(index_path)
        index["messages"][0]["visionary"] = "Invented name"
        dump(index_path, index)
        with self.assertRaisesRegex(AppendOnlyError, "canonical metadata"):
            gate(self.before, self.after)

    def test_blocks_removal(self):
        path = self.after / "en.json"
        archive = self.load(path)
        archive["messages"] = []
        dump(path, archive)
        with self.assertRaisesRegex(AppendOnlyError, "removes existing translations"):
            gate(self.before, self.after)

    def test_blocks_fabricated_append_hash(self):
        self.add_translation()
        path = self.after / "ru.json"
        archive = self.load(path)
        archive["messages"][0]["text_sha256"] = "0" * 64
        dump(path, archive)
        with self.assertRaisesRegex(AppendOnlyError, "invalid text checksum"):
            gate(self.before, self.after)

    def test_blocks_index_claim_without_language_record(self):
        index_path = self.after / "index.json"
        index = self.load(index_path)
        index["messages"][0]["translations"]["ru"] = {"present": True,
             "has_text": True, "text_sha256": "0" * 64}
        dump(index_path, index)
        with self.assertRaises(AppendOnlyError):
            gate(self.before, self.after)

    def test_blocks_duplicate_language_id(self):
        path = self.after / "en.json"
        archive = self.load(path)
        archive["messages"].append(deepcopy(archive["messages"][0]))
        dump(path, archive)
        with self.assertRaisesRegex(AppendOnlyError, "duplicate ID"):
            gate(self.before, self.after)

    def test_blocks_phantom_index_entry(self):
        index_path = self.after / "index.json"
        index = self.load(index_path)
        invented = deepcopy(index["messages"][0])
        invented["id"] = "2026-10-25-monthly"
        index["messages"].append(invented)
        index["unique_records"] = 2
        dump(index_path, index)
        with self.assertRaises(AppendOnlyError):
            gate(self.before, self.after)


if __name__ == "__main__":
    unittest.main()
