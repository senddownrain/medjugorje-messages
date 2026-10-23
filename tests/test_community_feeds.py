import unittest
from scripts.probe_community_feeds import summarize_rss

class FeedTests(unittest.TestCase):
    def test_rss(self):
        raw = b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title>
        <item><title>Monthly message</title><link>https://example.test/message</link>
        <pubDate>Thu, 25 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>'''
        posts, number = summarize_rss(raw)
        self.assertEqual(number, 1)
        self.assertEqual(posts[0]["title"], "Monthly message")

    def test_empty_feed(self):
        posts, number = summarize_rss(b'<rss><channel><title>Empty</title></channel></rss>')
        self.assertEqual(posts, [])
        self.assertEqual(number, 0)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            summarize_rss(b'<html><body>Not an rss feed</body></html>')

if __name__ == "__main__":
    unittest.main()
