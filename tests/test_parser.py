import unittest
from scripts.sync_messages import (
    date_for_slug, parse_archive, slug_for_url, visionary_for_title
)

class ParserTests(unittest.TestCase):
    def test_date(self):
        self.assertEqual(date_for_slug("840301w"), "1984-03-01")
        self.assertEqual(date_for_slug("260925m"), "2026-09-25")

    def test_normalized_links(self):
        self.assertEqual(
            slug_for_url("/ru/messages/260925m/", "ru"),
            "260925m"
        )
        self.assertIsNone(
            slug_for_url("https://example.org/ru/messages/260925m/", "ru"),
        )

    def test_same_day_distinct_types(self):
        html = """<h2><a href="/ru/messages/261225a/">Послание Якову</a></h2>
        <p>Дорогие дети! Первое послание здесь.</p>
        <h2><a href="/ru/messages/261225m/">Ежемесячное послание</a></h2>
        <p>Дорогие дети! Второе послание здесь.</p>"""
        rows, links, issues = parse_archive(
            html, "ru", "https://www.medjugorje.ws/ru/messages/all"
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(links), {"261225a", "261225m"})
        self.assertEqual(rows["261225m"]["type"], "monthly")
        self.assertEqual(rows["261225a"]["visionary"], "jakov")
        self.assertEqual(rows["261225m"]["visionary"], "marija")
        self.assertEqual(issues, [])

    def test_belarusian(self):
        html = ('<h2><a href="/be/messages/260925m/">Пасланне</a></h2>'
                '<p>Дарагія дзеці! Маліцеся за мір.</p>')
        rows, _, _ = parse_archive(
            html, "be", "https://www.medjugorje.ws/be/messages/all"
        )
        self.assertEqual(rows["260925m"]["language"], "be")

    def test_visionary_unknown_is_not_invented(self):
        self.assertIsNone(visionary_for_title("Послание 25 декабря", "annual"))

if __name__ == "__main__":
    unittest.main()
