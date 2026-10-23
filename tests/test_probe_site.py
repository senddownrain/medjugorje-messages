import unittest
from scripts.probe_site import parse_listing

class ProbeTests(unittest.TestCase):
    def test_parse_unique_message_ids_without_year_links(self):
        html = """<a href="/en/messages/260925m/">Sep 25</a>
        <a href="/en/messages/260925m/">Same message</a>
        <a href="https://www.medjugorje.ws/en/messages/260318a/">Annual</a>
        <a href="/en/messages/2026/">Year</a><a href="https://elsewhere.test/en/messages/260825m/">External</a>"""
        self.assertEqual(parse_listing(html, "en", "https://www.medjugorje.ws"),
                         ["260318a", "260925m"])
    def test_cannot_mix_languages(self):
        html = '<a href="/ru/messages/260925m/">Russian</a>'
        self.assertEqual(parse_listing(html, "en", "https://www.medjugorje.ws"), [])
if __name__ == "__main__":
    unittest.main()
