"""Read-only regressions for visionary/series provenance; never alter message texts."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("ru", "be", "uk", "hr", "en", "sk", "lv")

def read(name):
    return json.loads((ROOT / "data" / (name + ".json")).read_text(encoding="utf-8"))

class VisionaryAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = read("index")["messages"]
        cls.by_id = {r["id"]:r for r in cls.index}
        cls.archives = {l: {r["id"]:r for r in read(l)["messages"]} for l in LANGS}

    def test_all_translation_checksums_and_index_relations(self):
        self.assertEqual(len(self.by_id), len(self.index))
        for lang, records in self.archives.items():
            for key,record in records.items():
                with self.subTest(language=lang, id=key):
                    self.assertIn(key,self.by_id)
                    root=self.by_id[key]
                    self.assertEqual(root["date"],record["date"])
                    self.assertEqual(root["type"],record["type"])
                    meta=root["translations"][lang]
                    self.assertTrue(meta["present"])
                    self.assertEqual(meta["has_text"],bool(record["text"]))
                    digest=hashlib.sha256(record["text"].encode("utf8")).hexdigest()
                    self.assertEqual(record["text_sha256"],digest)
                    self.assertEqual(meta["text_sha256"],digest)
                    assembled="\n\n".join(s["text"] for s in record["segments"] if s["kind"] == "message")
                    self.assertEqual(assembled,record["text"])
            for root in self.index:
                self.assertEqual(bool(root["translations"][lang]["present"]),root["id"] in records)

    def test_ivan_special_2006_carries_explicit_english_evidence(self):
        row=self.by_id["060908s"]
        text=self.archives["en"]["060908s"]["title"]
        self.assertIn("to Ivan",text)
        self.assertIsNone(row["visionary"])
        self.assertEqual(row["type"],"special")

    def test_ivan_special_2014_source_url_mismatch_is_preserved(self):
        row=self.by_id["140812s"]
        source=self.archives["uk"]["140812s"]
        self.assertIn("Ivan",source["title"])
        self.assertEqual(source["source_id"],"140802s")
        self.assertEqual(row["date"],"2014-08-12")
        self.assertIsNone(row["visionary"])

    def test_mirjana_2005_explicit_latvian_title(self):
        self.assertIn("Mirjamai",self.archives["lv"]["050402s"]["title"])
        self.assertIsNone(self.by_id["050402s"]["visionary"])

    def test_unattributed_weekly_is_parish_series_not_force_assigned(self):
        weekly=[r for r in self.index if r["type"]=="weekly"]
        self.assertGreater(len(weekly),0)
        self.assertTrue(any(r["visionary"] is None for r in weekly))
        self.assertTrue(all(r["type"] == "weekly" for r in weekly))

if __name__=="__main__":
    unittest.main()
