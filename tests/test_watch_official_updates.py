import unittest
from scripts.watch_official_updates import compare, extract_dates

class WatcherTests(unittest.TestCase):
    def test_parse_dates(self):
        self.assertEqual(extract_dates("<h2>September 25, 2026</h2><h2>August 25, 2026</h2>"),
                         ["2026-09-25", "2026-08-25"])
    def test_detect_date(self):
        index = {"messages": [{"date": "2026-09-25", "translations": {"ru": {"present": True}}}]}
        found = compare(["2026-10-25", "2026-09-25"], index)
        self.assertEqual(found["new_dates"], ["2026-10-25"])
        self.assertFalse(found["translations_checked"])
        self.assertEqual(found["language_counts_in_local_index"]["lv"], 0)
    def test_no_newer_date(self):
        self.assertEqual(compare(["2026-09-25"], {"messages": [{"date": "2026-09-25"}]})["status"],
                         "no_newer_dates")
    def test_error_not_no_updates(self):
        with self.assertRaises(ValueError):
            extract_dates("<h2>Temporarily unavailable</h2>")
if __name__ == "__main__":
    unittest.main()
