import unittest
from scripts.import_mhtml import LANGS, PATH, parse_page

class ExtendedMhtmlLanguages(unittest.TestCase):
    def test_all_seven_languages_have_paths(self):
        self.assertEqual(set(LANGS), {"ru","be","uk","hr","en","sk","lv"})
        for lang in LANGS:
            with self.subTest(lang=lang):
                self.assertIsNotNone(PATH.fullmatch(f"/{lang}/messages/260925m/"))

    def test_parses_four_added_languages(self):
        for lang in ("hr","en","sk","lv"):
            with self.subTest(lang=lang):
                html=(
                    f'<div class="mm-head"><input type="checkbox" value="2026-09-25_33221100_messages">'
                    f'<h2 class="poselstvi-datum"><a href="https://www.medjugorje.ws/{lang}/messages/260925m/">'
                    f'September 25, 2026</a></h2></div>'
                    f'<div class="poselstvi-mary">Peace to all of you.</div>'
                    f'<div class="mmm-footer"></div>'
                )
                rows,report=parse_page(html,lang)
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]["id"],"260925m")
                self.assertEqual(rows[0]["language"],lang)
                self.assertEqual(rows[0]["text"],"Peace to all of you.")
                self.assertEqual(report["records_without_text"],0)

if __name__ == "__main__":
    unittest.main()
