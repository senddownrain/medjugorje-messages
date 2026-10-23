import unittest
from email import policy
from email.message import EmailMessage
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.import_mhtml import load_html, parse_page


def record(date, source_id, text, title="Послание"):
    return (
        f'<div class="mm-head"><input type="checkbox" '
        f'value="{date}_33221100_messages" />'
        f'<h2 class="poselstvi-datum"><a href="https://www.medjugorje.ws/ru/messages/{source_id}/">'
        f'{title}</a></h2></div>'
        f'<div class="poselstvi-mary"><span class="bq">"</span><span class="d">Д</span>'
        f'{text}<span class="eq">"</span></div><div class="mmm-footer"></div>'
    )


class MhtmlImporterTests(unittest.TestCase):
    def test_message_blocks_and_title(self):
        html = record("2026-09-25", "260925m", "орогие дети! Молитесь о мире.")
        rows, report = parse_page(html, "ru")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "Дорогие дети! Молитесь о мире.")
        self.assertEqual(rows[0]["type"], "monthly")
        self.assertEqual(rows[0]["visionary"], "marija")
        self.assertEqual(report["records_without_text"], 0)

    def test_duplicate_source_url_keeps_both_records(self):
        html = (record("2011-12-25", "121125m", "орогие дети! Первое послание.")
                + record("2012-11-25", "121125m", "орогие дети! Второе послание."))
        rows, report = parse_page(html, "ru")
        self.assertEqual({r["id"] for r in rows}, {"111225m", "121125m"})
        self.assertEqual(report["distinct_source_urls"], 1)
        self.assertIn("source_url_date_mismatch", [x["reason"] for x in report["anomalies"]])

    def test_multiple_messages_and_intervening_context(self):
        html = record("2011-01-02", "110102s", "орогие дети! Первый текст.")
        html = html.replace(
            '<div class="mmm-footer"></div>',
            '<div class="poselstvi">Пояснение редактора.</div>'
            '<div class="poselstvi-mary"><span class="bq">"</span>Второе послание'
            '<span class="eq">"</span></div><div class="mmm-footer"></div>'
        )
        rows, _ = parse_page(html, "ru")
        self.assertEqual(rows[0]["text"], "Дорогие дети! Первый текст.\n\nВторое послание")
        self.assertEqual([s["kind"] for s in rows[0]["segments"]],
                         ["message", "context", "message"])

    def test_missing_quote_is_explicit(self):
        html = record("2010-12-25", "101225m", "орогие дети!").replace(
            '<div class="poselstvi-mary"><span class="bq">"</span><span class="d">Д</span>'
            'орогие дети!<span class="eq">"</span></div>', ""
        )
        rows, report = parse_page(html, "ru")
        self.assertEqual(rows[0]["status"], "missing_message_text")
        self.assertEqual(report["records_without_text"], 1)

    def test_mhtml_selects_main_page_not_embedded_tracking_html(self):
        m = EmailMessage(policy=policy.default)
        m.make_related()
        a = EmailMessage(policy=policy.default)
        a.set_content('<h2>Real archive</h2>', subtype='html')
        a['Content-Location'] = 'https://www.medjugorje.ws/ru/messages/all'
        m.attach(a)
        b = EmailMessage(policy=policy.default)
        b.set_content('<h2>Tracking frame</h2>', subtype='html')
        m.attach(b)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'page.mht'
            path.write_bytes(m.as_bytes())
            result, source = load_html(path)
        self.assertIn('Real archive', result)
        self.assertIn('/ru/messages/all', source)

if __name__ == "__main__":
    unittest.main()
