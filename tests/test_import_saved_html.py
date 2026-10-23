import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_saved_html import import_saved_html


class SavedHtmlImportTests(unittest.TestCase):
    def test_imports_messages_and_reports_missing_languages(self):
        html = """<!doctype html><html><head><meta charset="utf-8"></head><body>
        <h2><a href="/ru/messages/260925m/">Ежемесячное послание</a></h2>
        <p>Дорогие дети! Молитесь о мире.</p>
        <h2><a href="/ru/messages/261225a/">Ежегодное послание Якову</a></h2>
        <p>Дорогие дети! Пусть молитва будет вашей радостью.</p>
        </body></html>"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = root / "ru.html"
            saved.write_text(html, encoding="utf-8")
            report = import_saved_html({"ru": saved}, root / "data")
            self.assertEqual(report["languages"]["ru"]["unique_messages"], 2)
            self.assertEqual(report["languages"]["ru"]["missing_ids"], [])
            self.assertEqual(report["languages"]["be"]["status"], "not_provided")
            data = json.loads((root / "data" / "ru.json").read_text(encoding="utf-8"))
            self.assertFalse(data["verified"])
            self.assertEqual(len(data["messages"]), 2)
            index = json.loads((root / "data" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["unique_messages"], 2)

    def test_invalid_empty_file_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = root / "ru.html"
            saved.write_text("", encoding="utf-8")
            report = import_saved_html({"ru": saved}, root / "data")
            self.assertEqual(report["languages"]["ru"]["status"], "failed")
            self.assertTrue(report["warnings"])

    def test_not_counting_unsupported_links_as_text(self):
        html = """<h2><a href="/be/messages/260925m/">Пасланне</a></h2>
        <p>Дарагія дзеці! Маліцеся за мір.</p>
        <p><a href="/be/messages/261025m/">Next month</a></p>"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = root / "be.html"
            saved.write_text(html, encoding="utf-8")
            report = import_saved_html({"be": saved}, root / "data")
            self.assertEqual(report["languages"]["be"]["unique_messages"], 1)
            self.assertEqual(report["languages"]["be"]["missing_ids"], ["261025m"])
            self.assertTrue(report["warnings"])

if __name__ == "__main__":
    unittest.main()
