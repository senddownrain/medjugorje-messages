"""Snapshot coverage, grouping, preservation and failure-mode regressions."""
from email import policy
from email.message import EmailMessage
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

from scripts.historical_baseline import write_historical_baseline
from scripts.audit_source_snapshots import extract_original, sha256
from scripts.audit_thematic_snapshots import SOURCE_SHA256, inspect_category_links, verify_thematic_zip

ROOT = Path(__file__).resolve().parents[1]
THEMATIC = ROOT / "research-sources/medjugorje_thematic_en_hr_sources_audit_2026-10-23.zip"
ORIGINAL = ROOT / "research-sources/medjugorje_original_sources_seven.zip"


def mhtml(html, origin):
    mime = EmailMessage(policy=policy.default)
    mime.make_related()
    part = EmailMessage(policy=policy.default)
    part.set_content(html, subtype="html")
    part["Content-Location"] = origin
    mime.attach(part)
    return mime.as_bytes()


class ThematicSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.historical_temp = TemporaryDirectory()
        cls.addClassCleanup(cls.historical_temp.cleanup)
        cls.historical = write_historical_baseline(ROOT / "data", Path(cls.historical_temp.name))
        cls.report, cls.memberships = verify_thematic_zip(THEMATIC, cls.historical)

    def test_every_record_and_group_in_the_four_snapshots_is_reconciled(self):
        self.assertEqual(self.report["status"], "VERIFIED_SOURCE_SNAPSHOT_COVERAGE")
        self.assertEqual(self.report["violations"], [])
        self.assertEqual(self.report["total_thematic_entries"], 476)
        self.assertEqual(self.report["distinct_thematic_ids"], 258)
        expected = {"en/annual": (79, {"ivanka": 17, "jakov": 29, "mirjana": 33}),
                    "hr/annual": (79, {"ivanka": 17, "jakov": 29, "mirjana": 33}),
                    "en/special": (179, {"ivan": 1, "marija": 1, "mirjana": 177}),
                    "hr/special": (139, {"mirjana": 139})}
        for key, (count, groups) in expected.items():
            page = self.report["source_pages"][key]
            self.assertEqual((page["message_count"], page["group_counts"]), (count, groups))
            self.assertEqual(page["absent_from_category"], [])
            self.assertEqual(page["unexpected_from_category"], [])
            self.assertEqual(page["explicit_pagination_links"], [])
            self.assertEqual(page["group_view_urls_without_inline_group"], [])
            self.assertEqual(set(page["source_ids"]), set().union(*(set(g["ids"]) for g in page["groups"].values())))

    def test_receipt_hashes_match_the_owners_comment_and_all_four_raw_members(self):
        self.assertEqual(sha256(THEMATIC.read_bytes()), "e300ebe4af0c0b2c619d7de7daca61c9aba8ccb50475e09de06b3b450e613654")
        with zipfile.ZipFile(THEMATIC) as archive:
            for key, page in self.report["source_pages"].items():
                self.assertEqual(page["mhtml_sha256"], SOURCE_SHA256[key])
                self.assertEqual(page["mhtml_sha256"], sha256(archive.read(page["zip_member"])))
                self.assertTrue(page["reference_comment_and_supplied_report_match"])

    def test_four_union_exceptions_keep_ids_languages_and_original_anomalous_slugs(self):
        outside = {r["id"]: r for r in self.report["union_ids_outside_both_languages"]}
        self.assertEqual(set(outside), {"110625a", "160625a", "140812s", "050402s"})
        self.assertEqual(outside["110625a"]["languages_present"], ["lv"])
        self.assertEqual(outside["160625a"]["languages_present"], ["ru", "lv"])
        self.assertEqual(outside["140812s"]["languages_present"], ["uk"])
        self.assertEqual(outside["050402s"]["languages_present"], ["lv"])
        self.assertEqual(outside["160625a"]["original_sources"]["ru"]["source_id"], "120625a")
        self.assertEqual(outside["140812s"]["original_sources"]["uk"]["source_id"], "140802s")
        union = {r["id"] for r in json.loads((ROOT / "data/index.json").read_text())["messages"]}
        self.assertTrue(set(outside) <= union)

    def test_forty_english_only_special_entries_are_language_coverage_gaps(self):
        cross = self.report["cross_language"]["special"]
        self.assertEqual(cross["common"], 139)
        self.assertEqual(cross["hr_only"], [])
        self.assertEqual(len(cross["en_only"]), 40)
        self.assertEqual({a: len(ids) for a, ids in cross["en_only_by_group"].items()},
                         {"special.ivan": 1, "special.marija": 1, "special.mirjana": 38})
        hr = {r["id"] for r in json.loads((ROOT / "data/hr.json").read_text())["messages"]}
        self.assertTrue(set(cross["en_only"]).isdisjoint(hr))

    def test_original_independent_script_reproduces_all_three_supplied_reports(self):
        with TemporaryDirectory() as tmp, zipfile.ZipFile(THEMATIC) as archive:
            folder = Path(tmp)
            for entry in archive.infolist():
                target = folder / entry.filename
                self.assertTrue(target.resolve().is_relative_to(folder.resolve()))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
            out = folder / "reproduced"
            env = {**os.environ, "MHT_DATA_DIR": str(self.historical), "MHT_AUDIT_OUT": str(out)}
            result = subprocess.run([sys.executable, str(folder / "reconcile_thematic.py")], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("thematic_report.json", "thematic_entries.csv", "thematic_violations.csv"):
                self.assertEqual((out / name).read_bytes(), archive.read(name))

    def test_changed_text_and_missing_language_record_cannot_pass_snapshot_verification(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for lang in ("en", "hr", "index"):
                (folder / f"{lang}.json").write_bytes((ROOT / "data" / f"{lang}.json").read_bytes())
            doc = json.loads((folder / "en.json").read_text())
            for row in doc["messages"]:
                if row["id"] == "060908s":
                    row["text"] += "changed"
            doc["messages"] = [r for r in doc["messages"] if r["id"] != "050302s"]
            (folder / "en.json").write_text(json.dumps(doc))
            result, _ = verify_thematic_zip(THEMATIC, folder)
        self.assertEqual(result["status"], "THEMATIC_SOURCE_REVIEW_REQUIRED")
        self.assertTrue(any(v["reason"] == "source-missing" and v["id"] == "050302s" for v in result["violations"]))
        self.assertTrue(any(v["reason"] == "thematic_all_record_difference" and v["id"] == "060908s" for v in result["violations"]))

    def test_group_is_read_from_the_source_anchor_even_on_an_exceptional_annual_date(self):
        html = ('<div class="messages"><a name="annual.ivanka"></a><div class="nadpis">'
                '<h2><a href="https://www.medjugorje.ws/en/messages/annual.ivanka/">Annual messages to Ivanka</a></h2></div>'
                '<div class="mm-head"><input type="checkbox" value="1985-05-07_messages">'
                '<h2 class="poselstvi-datum"><a href="https://www.medjugorje.ws/en/messages/850507a/">May 7, 1985</a></h2></div>'
                '<div class="poselstvi-mary">Source fixture</div></div>')
        origin = "https://www.medjugorje.ws/en/messages/annual/"
        rows, positions, _ = extract_original(mhtml(html, origin), "en", "annual")
        self.assertEqual(rows[0]["type"], "annual")
        self.assertEqual(positions["850507a"]["thematic_group"]["anchor"], "annual.ivanka")
        with self.assertRaisesRegex(ValueError, "no preceding source group anchor"):
            extract_original(mhtml(html.replace('<a name="annual.ivanka"></a>', ''), origin), "en", "annual")

    def test_pagination_and_uncovered_group_views_require_more_source_review(self):
        origin = "https://www.medjugorje.ws/en/messages/annual/"
        html = ('<a href="/en/messages/annual.ivanka/">Inline group</a>'
                '<a href="/en/messages/annual.other/">Missing group</a><a rel="next" href="?page=2">Next</a>')
        result = inspect_category_links(mhtml(html, origin), origin, {"annual.ivanka"})
        self.assertEqual(result["explicit_pagination_links"], [origin + "?page=2"])
        self.assertEqual(result["group_view_urls_without_inline_group"], ["https://www.medjugorje.ws/en/messages/annual.other/"])

    def test_unavailable_zip_cannot_be_reported_as_verified(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            result = subprocess.run([sys.executable, "-m", "scripts.audit_stage_a", "--source-zip", str(ORIGINAL),
                "--thematic-zip", str(Path(tmp) / "missing.zip"), "--out", str(out)], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Thematic ZIP is unavailable", result.stderr)
            self.assertNotIn("VERIFIED_SOURCE_SNAPSHOT_COVERAGE", result.stdout)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
