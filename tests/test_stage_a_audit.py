"""Read-only audit regressions: evidence, lost records and ambiguous sources."""
import copy
from email import policy
from email.message import EmailMessage
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from scripts.audit_stage_a import audit_data, audit_sources, build_report, compare_saved_source, digest
from scripts.audit_source_snapshots import extract_original, read_heading_date
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
        cls.report = build_report(ROOT / "data", ROOT / "research-sources/medjugorje_original_sources_seven.zip")

    def test_current_snapshot_has_no_integrity_violations(self):
        self.assertEqual(self.report["violations"], [])

    def test_all_seven_original_snapshots_match_without_proving_category_coverage(self):
        sources = self.report["sources"]
        self.assertEqual(sources["status"], "SEVEN_ALL_SNAPSHOTS_MATCH_JSON_PENDING_CATEGORY_REVIEW")
        self.assertEqual(len(sources["sources"]), 7)
        self.assertEqual(sources["source_records_compared"], sum(s["records"] for s in self.report["summary"]["languages"].values()))
        self.assertEqual(sources["source_missing_count"], 0)
        self.assertEqual(sources["record_difference_count"], 0)
        self.assertEqual(sources["heading_date_issue_count"], 0)
        self.assertEqual(sources["unclassified_source_block_count"], 0)
        self.assertEqual(sources["non_message_navigation_count"], 286)
        self.assertEqual(sources["json_records_absent_from_saved_sources"], 0)
        self.assertEqual(set(sources["missing_required"]), {"en/annual", "en/special", "hr/annual", "hr/special"})
        self.assertEqual(set().union(*(set(s["source_ids"]) for s in sources["sources"])),
                         {r["id"] for r in self.report["inventory"]})
        self.assertTrue(all(s["supplied_manifest_sha_and_size_and_count_match"] for s in sources["sources"]))

    def test_heading_date_reader_does_not_guess_unknown_names_or_invalid_calendar_dates(self):
        self.assertEqual(read_heading_date("Medjugorje Message, August 12, 2014 - Ivan", "en"), "2014-08-12")
        self.assertEqual(read_heading_date("Vēstījums, 2005.g. 2. Aprīlis", "lv"), "2005-04-02")
        self.assertIsNone(read_heading_date("Message, February 30, 2014", "en"))
        self.assertIsNone(read_heading_date("Message, UnknownMonth 12, 2014", "en"))

    def test_proposals_cite_exact_original_zip_members_and_keep_editorial_review_pending(self):
        source_path = ROOT / "research-sources/medjugorje_original_sources_seven.zip"
        self.assertEqual(self.report["sources"]["proposals_confirmed_in_original_all"], len(self.report["proposals"]))
        with zipfile.ZipFile(source_path) as archive:
            for proposal in self.report["proposals"]:
                self.assertEqual(proposal["review_status"], "original_all_snapshot_confirmed_pending_category_and_editorial_review")
                self.assertFalse(proposal["applied"])
                for evidence in proposal["evidence"]:
                    snapshot = evidence["original_snapshot"]
                    self.assertEqual(snapshot["archive_sha256"], digest(source_path.read_bytes()))
                    self.assertEqual(snapshot["source_sha256"], digest(archive.read(snapshot["zip_member"])))
                    self.assertEqual(snapshot["quote_sha256"], digest(evidence["quote"].encode()))
                    self.assertIsInstance(snapshot["heading_position"], int)

    def test_independent_reader_ignores_navigation_and_preserves_context_and_inline_text(self):
        html = ('<a href="https://www.medjugorje.ws/en/messages/111111s/">Navigation</a>'
                '<div class="messages">' + html_record(text='<span class="bq">“</span>A<b>B</b><br>C<span class="eq">”</span><!-- not content -->')
                .replace('<div class="mmm-footer">', '<div class="poselstvi">Editorial context</div><div class="mmm-footer">')
                + '</div>')
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.mht"
            save_mhtml(path, html, "https://www.medjugorje.ws/en/messages/all")
            rows, positions, location = extract_original(path.read_bytes(), "en")
            save_mhtml(path, html.replace('</div><div class="mmm-footer">', '</div><p>Unexpected body</p><div class="mmm-footer">'), "https://www.medjugorje.ws/en/messages/all")
            _, with_unknown, _ = extract_original(path.read_bytes(), "en")
            self.assertEqual(with_unknown["060908s"]["unclassified_source_blocks"][0]["excerpt"], "Unexpected body")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "AB\nC")
        self.assertEqual(rows[0]["segments"][-1], {"kind": "context", "text": "Editorial context"})
        self.assertEqual(positions["060908s"]["heading_position"], 0)

    def test_independent_reader_keeps_reused_urls_and_refuses_duplicate_canonical_ids(self):
        def wrapper(day):
            return '<div class="messages">' + html_record(day=day) + '</div>'
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.mht"
            save_mhtml(path, wrapper("2006-09-08") + wrapper("2006-09-09"), "https://www.medjugorje.ws/en/messages/all")
            rows, _, _ = extract_original(path.read_bytes(), "en")
            self.assertEqual([r["id"] for r in rows], ["060908s", "060909s"])
            self.assertEqual(rows[0]["source_url"], rows[1]["source_url"])
            save_mhtml(path, wrapper("2006-09-08") * 2, "https://www.medjugorje.ws/en/messages/all")
            with self.assertRaisesRegex(ValueError, "Duplicate original canonical ID"):
                extract_original(path.read_bytes(), "en")

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
