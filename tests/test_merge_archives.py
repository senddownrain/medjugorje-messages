import json
import tempfile
import unittest
from pathlib import Path

from scripts.merge_archives import combine_sources


def page(lang, id, day, body):
    return (f'<div class="mm-head"><input type="checkbox" value="{day}_test"/>'
            f'<h2 class="poselstvi-datum"><a href="https://www.medjugorje.ws/{lang}/messages/{id}/">'
            'Послание</a></h2></div>'
            f'<div class="poselstvi-mary">{body}</div><div class="mmm-footer"></div>')

class MergeTests(unittest.TestCase):
    def test_union_with_missing_historical_translation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            html = {
                "ru": page("ru", "260925m", "2026-09-25", "Дорогие дети! Мир вам.")
                    + page("ru", "840301w", "1984-03-01", "Историческое послание."),
                "be": page("be", "260925m", "2026-09-25", "Дарагія дзеці! Мір вам."),
                "uk": page("uk", "260925m", "2026-09-25", "Дорогі діти! Мир вам."),
            }
            inputs = {}
            for lang, value in html.items():
                file = root / (lang + ".html")
                file.write_text(value, encoding="utf-8")
                inputs[lang] = file
            report = combine_sources(inputs, root / "out")
            self.assertEqual(report["unique_records"], 2)
            self.assertEqual(report["all_three"], 1)
            index = json.loads((root / "out/data/index.json").read_text(encoding="utf-8"))
            self.assertFalse(index["verified"])
            self.assertTrue(index["messages"][0]["translations"]["uk"]["has_text"])
            self.assertFalse(index["messages"][1]["translations"]["be"]["present"])
            self.assertTrue((root / "out/reports/index.csv").is_file())

    def test_refuses_incomplete_input(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "Missing required"):
                combine_sources({"ru": Path(temp) / "ru.html"}, Path(temp) / "out")

if __name__ == "__main__":
    unittest.main()
