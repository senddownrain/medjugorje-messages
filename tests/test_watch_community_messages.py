import unittest
from scripts.watch_community_messages import parse_feed, is_message_candidate

ORIGIN={"ru":"https://svetmariji.ru/","uk":"https://svitlomariji.com.ua/",
        "sk":"https://svetlomariino.sk/","lv":"https://medjugorje.lv/",
        "en":"https://thelightofmary.com/"}

def item(title,lang,category="",url=None):
    return {"title":title,"categories":[category] if category else [],
            "url":url or ORIGIN[lang]+"2026/10/example/"}

class CommunityWatcherTests(unittest.TestCase):
    def test_rss_parser(self):
        data=b"""<rss><channel><item><title>Test</title><link>https://example.com/a</link>
        <pubDate>Fri, 23 Oct 2026 10:15:00 +0000</pubDate>
        <category>Messages</category></item></channel></rss>"""
        rows=parse_feed(data)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["categories"],["Messages"])
        self.assertEqual(rows[0]["published"],"2026-10-23T10:15:00+00:00")

    def test_accept_strict_message_titles(self):
        cases={
            "ru":"Послание Богородицы, Царицы Мира, 25 октября 2026",
            "uk":"Послання Богородиці, Цариці миру, 25 жовтня 2026",
            "sk":"Posolstvo Panny Márie, Kráľovnej pokoja, 25. októbra 2026",
            "lv":"Dievmātes, Miera Karalienes, vēstījums Marijai 2026. gada 25. oktobrī",
            "en":"Message from the Queen of Peace, October 25, 2026",
        }
        for lang,title in cases.items():
            with self.subTest(lang=lang):
                self.assertTrue(is_message_candidate(lang,item(title,lang),ORIGIN[lang]))

    def test_excludes_daily_posts_and_reflections(self):
        self.assertFalse(is_message_candidate("ru",item("23.10.2026","ru","В школе Богородицы"),ORIGIN["ru"]))
        self.assertFalse(is_message_candidate("uk",item("Нехай цей час буде часом молитви за мир","uk","Роздуми"),ORIGIN["uk"]))
        self.assertFalse(is_message_candidate("sk",item("Posolstvo Panny Márie, 25.10","sk","Úvahy"),ORIGIN["sk"]))
        self.assertFalse(is_message_candidate("en",item("Prayer for Peace","en","Meditations"),ORIGIN["en"]))

    def test_refuses_external_url(self):
        self.assertFalse(is_message_candidate("ru",item("Послание Богородицы", "ru",
                          url="https://example.com/article"),ORIGIN["ru"]))

    def test_relevant_ukrainian_archive_path(self):
        row=item("25 жовтня 2026 року","uk",
                 url=ORIGIN["uk"]+"poslannya-bogoroditsi/misyachni-poslannya/2026/new-message/")
        self.assertTrue(is_message_candidate("uk",row,ORIGIN["uk"]))

    def test_empty_feed_is_not_no_updates(self):
        with self.assertRaises(ValueError):
            parse_feed(b"<rss><channel></channel></rss>")

if __name__ == "__main__":
    unittest.main()
