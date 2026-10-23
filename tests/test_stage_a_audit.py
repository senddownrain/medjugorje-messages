"""Read-only audit regressions: evidence, lost records and ambiguous sources."""
import copy
from email import policy
from email.message import EmailMessage
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.audit_stage_a import audit_data, audit_sources, compare_saved_source, digest
from scripts.import_mhtml import parse_page

ROOT = Path(__file__).resolve().parents[1]


def html_record(day="2006-09-08", slug="060908s", title="Apparition to Ivan", text="Saved test text"):
    return (f'<h3>Special messages to Ivan</h3><div class="mm-head">'
            f'<input type="checkbox" value="{day}_messages">'
            f'<h2 class="poselstvi-datum"><a href="https://www.medjugorje.ws/en/messages/{slug}/">'
            f'{title}</a></h2></div><div class="poselstvi-mary">{text}</div><div class="mmm-footer"></div>')


def save_mhtml(path, html, location):
    mime = EmailMessage(policy=policy.default)
    mime.make_related()
    part = EmailMessage(policy=policy.default)
    part.set_content(html, subtype="html")
    part["Content-Location"] = location
    mime.attach(part)
    path.write_bytes(mime.as_bytes())


class StageAAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit_data(ROOT / "data")

    def test_current_snapshot_has_no_integrity_violations(self):
        self.assertEqual(self.report["violations"], [])

    def test_audit_leaves_all_input_bytes_unchanged(self):
        paths = sorted((ROOT / "data").glob("*.json"))
        before = {p.name: p.read_bytes() for p in paths}
        audit_data(ROOT / "data")
        self.assertEqual(before, {p.name: p.read_bytes() for p in paths})

    def test_committed_data_reports_match_current_evidence(self):
        for name, value in self.report.items():
            with self.subTest(report=name):
                stored = json.loads((ROOT / "reports/stage-a" / f"{name}.json").read_text())
                self.assertEqual(stored, value)

    def test_every_record_in_inventory_and_every_absent_translation_listed(self):
        index = json.loads((ROOT / "data/index.json").read_text())["messages"]
        self.assertEqual({r["id"] for r in index}, {r["id"] for r in self.report["inventory"]})
        expected = {(r["id"], lang) for r in index for lang, meta in r["translations"].items() if not meta["present"]}
        self.assertEqual(expected, {(r["id"], r["language"]) for r in self.report["translation_not_present"]})

    def test_eight_proposals_have_exact_local_evidence_and_are_not_applied(self):
        self.assertEqual({r["id"]: r["proposed"] for r in self.report["proposals"]},
                         {"060908s": "ivan", "140812s": "ivan", "050402s": "mirjana", "850114w": "vicka",
                          "840814w": "ivan", "841008w": "jakov", "850625w": "marija", "840430w": "marija"})
        for proposal in self.report["proposals"]:
            self.assertFalse(proposal["applied"])
            self.assertIsNone(proposal["before"])
            for evidence in proposal["evidence"]:
                self.assertEqual(digest((ROOT / evidence["artifact"]).read_bytes()), evidence["artifact_sha256"])
                value = json.loads((ROOT / evidence["artifact"]).read_text())
                for part in evidence["json_pointer"].strip("/").split("/"):
                    value = value[int(part)] if isinstance(value, list) else value[part]
                self.assertEqual(value, evidence["quote"])
        vicka = next(r for r in self.report["proposals"] if r["proposed"] == "vicka")
        self.assertEqual({e["language"] for e in vicka["evidence"]}, {"hr", "en", "ru", "sk", "lv"})

    def test_unknown_weekly_records_are_not_generally_assigned(self):
        ids = self.report["summary"]["unattributed_weekly_ids"]
        self.assertEqual(len(ids), 159)  # Frozen baseline, not a future archive-size constraint.
        proposed = {r["id"] for r in self.report["proposals"]}
        self.assertEqual(proposed.intersection(ids), {"850114w", "840814w", "841008w", "850625w", "840430w"})
        self.assertNotIn("840823w", proposed)  # Reporting a statement alone does not prove recipient.
        self.assertNotIn("840531w", proposed)  # No message given; mention of a future message is insufficient.
        self.assertTrue(all(r["series"] is None for r in self.report["inventory"]))

    def test_originals_not_supplied_does_not_mean_source_missing(self):
        result = audit_sources(None, ROOT / "data")
        self.assertEqual(result["status"], "NOT_PROVIDED")
        self.assertEqual(len(result["missing_required"]), 11)
        self.assertEqual(result["sources"], [])
        self.assertNotIn("source-missing", self.report["summary"]["anomaly_counts"])

    def test_annual_exceptions_and_known_weekly_recipient_keep_original_type(self):
        rows = {r["id"]: r for r in self.report["inventory"]}
        self.assertEqual((rows["850507a"]["type"], rows["850507a"]["visionary"]), ("annual", "ivanka"))
        self.assertEqual((rows["980912a"]["type"], rows["980912a"]["visionary"]), ("annual", "jakov"))
        self.assertEqual((rows["850405w"]["type"], rows["850405w"]["visionary"]), ("weekly", "ivanka"))

    def test_saved_source_missing_record_diff_and_section_provenance(self):
        html = html_record()
        records, _ = parse_page(html, "en")
        url = "https://www.medjugorje.ws/en/messages/special/"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.mhtml"
            save_mhtml(path, html, url)
            missing = compare_saved_source(path, url, "en", "special", [])
            self.assertEqual(missing["issues"][0]["reason"], "source-missing")
            self.assertEqual(missing["source_headings"][0]["section"], "Special messages to Ivan")
            changed = copy.deepcopy(records)
            changed[0]["text"] = "Different text"
            changed[0]["title"] = "Different title"
            result = compare_saved_source(path, url, "en", "special", changed)
            self.assertEqual(set(result["issues"][0]["fields"]), {"text", "title"})
            self.assertEqual(changed[0]["text"], "Different text")
            self.assertNotIn("json_ids_not_in_saved_source", result)

    def test_landing_page_and_wrong_snapshot_do_not_prove_absence(self):
        url = "https://www.medjugorje.ws/en/messages/annual/"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.mhtml"
            save_mhtml(path, '<a href="/en/messages/annual/mirjana/">Mirjana</a>', url)
            result = compare_saved_source(path, url, "en", "annual", [])
            self.assertEqual(result["status"], "SOURCE_CONTENT_NOT_COMPARABLE")
            self.assertEqual(result["issues"], [])
            result = compare_saved_source(path, url.replace("annual", "special"), "en", "special", [])
            self.assertEqual(result["status"], "SOURCE_IDENTITY_NOT_CONFIRMED")
            # Headings with unparseable metadata are not a successfully empty archive.
            save_mhtml(path, html_record().replace('value="2006-09-08_messages"', 'value="invalid"'), url)
            result = compare_saved_source(path, url, "en", "annual", [])
            self.assertEqual(result["status"], "SOURCE_CONTENT_NOT_COMPARABLE")
            self.assertTrue(result["parser_anomalies"])

    def test_duplicate_original_url_retains_both_canonical_ids(self):
        html = html_record("2006-09-08", "060908s") + html_record("2006-09-09", "060908s")
        url = "https://www.medjugorje.ws/en/messages/all/"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.mhtml"
            save_mhtml(path, html, url)
            result = compare_saved_source(path, url, "en", "all", [])
            self.assertEqual(result["source_ids"], ["060908s", "060909s"])
            self.assertIn("duplicate_source_url", {r["reason"] for r in result["parser_anomalies"]})

    def test_mutated_source_metadata_and_lost_record_are_detected(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for path in (ROOT / "data").glob("*.json"):
                (folder / path.name).write_bytes(path.read_bytes())
            doc = json.loads((folder / "en.json").read_text())
            removed = doc["messages"].pop()
            doc["messages"][0]["source_url"] = "https://example.invalid/"
            doc["messages"][0]["text"] += "changed"
            (folder / "en.json").write_text(json.dumps(doc))
            result = audit_data(folder)
            reasons = {r["reason"] for r in result["violations"]}
            self.assertIn("integrity_mismatch", reasons)
            self.assertTrue(any(r["reason"] == "presence_mismatch" and r["id"] == removed["id"] for r in result["violations"]))


if __name__ == "__main__":
    unittest.main()
