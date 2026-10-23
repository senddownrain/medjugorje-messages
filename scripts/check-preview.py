"""Browser QA against a locally built private preview; never uploads message data.

Optional dependency: pip install playwright. Use an installed Chromium executable.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:4174/')
parser.add_argument('--chromium', default='/usr/bin/chromium')
parser.add_argument('--output', default='/tmp/medjugorje-preview')
args = parser.parse_args()
assert args.url.startswith(('http://127.0.0.1:', 'http://localhost:')), 'Local QA only'
root = Path(__file__).resolve().parent.parent
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)
languages = {'ru':'Русский','be':'Беларуская','uk':'Українська','hr':'Hrvatski',
             'en':'English','sk':'Slovenčina','lv':'Latviešu'}
archives = {code:json.loads((root/'data'/f'{code}.json').read_text())['messages'] for code in languages}
index = json.loads((root/'data/index.json').read_text())['messages']
brands = ['Царица Мира','Каралева Супакою','Цариця Миру','Kraljica Mira','Queen of Peace','Kráľovná pokoja','Miera Karaliene']
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
    for width in (320, 390):
        context = browser.new_context(viewport={'width':width,'height':844}, device_scale_factor=1, is_mobile=True, has_touch=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(args.url)
        expect(page.locator('.message-text').first).to_be_visible()
        def fits():
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}'
        def select(n, title):
            page.locator('.settings-dialog .v-select').nth(n).click()
            page.get_by_role('option', name=title, exact=True).click()
        def settings():
            page.locator('.settings-button').click()
            expect(page.locator('.settings-dialog')).to_be_visible()
        def close():
            page.locator('.settings-dialog .v-card-actions button').click()
            expect(page.locator('.settings-dialog')).not_to_be_visible()
        # Change all seven UI languages using actual settings, leaving message language RU.
        settings()
        for (code, title), brand in zip(languages.items(), brands):
            select(0, title)
            expect(page.locator('.brand-copy strong')).to_have_text(brand)
            assert page.evaluate("localStorage.getItem('medjugorje-language')") in (None, 'ru')
            assert page.locator('.language-shortcut').inner_text() == 'RU'
            fits()
        select(0, 'Русский')
        # Change message language independently; compare displayed paragraphs to source JSON.
        for code, title in languages.items():
            select(1, title)
            close()
            latest = sorted((r for r in index if r['type']=='monthly' and r['translations'].get(code,{}).get('has_text')), key=lambda r:(r['date'],r['id']), reverse=True)[0]
            record = next(r for r in archives[code] if r['id']==latest['id'])
            expected = [s['text'] for s in record.get('segments',[]) if s['kind']=='message'] or [record['text']]
            expect(page.locator('.message-text')).to_have_text(expected)
            expect(page.locator('html')).to_have_attribute('lang','ru')
            fits()
            settings()
        select(1,'Русский')
        select(2,'Светлая')
        close()
        fits()
        page.screenshot(path=str(output/f'{width}-light.png'), full_page=True)
        page.locator('.main-nav button').nth(1).click()
        def count(expected):
            expect(page.locator('.result-count strong')).to_have_text(str(expected))
        def reset():
            page.locator('.result-count button').click()
        rows = [r for r in index if r['translations']['ru']['present']]
        count(len(rows))
        page.locator('.filters select').nth(0).select_option('2020')
        count(sum(r['date'].startswith('2020') for r in rows))
        reset()
        page.locator('.filters select').nth(1).select_option('monthly')
        count(sum(r['type']=='monthly' for r in rows))
        page.locator('.filters select').nth(2).select_option('marija')
        count(sum(r['type']=='monthly' and r.get('visionary')=='marija' for r in rows))
        reset()
        date=rows[0]['date']
        page.locator('input[type=date]').fill(date)
        count(sum(r['date']==date for r in rows))
        reset()
        query='молитв'
        page.locator('input[type=search]').fill(query)
        count(sum(query in ((r.get('text','') or '')+' '+(r.get('title','') or '')).lower() for r in archives['ru']))
        page.locator('input[type=search]').fill('zzzzz_no_such_message')
        count(0)
        reset()
        page.locator('.more-button').click()
        expect(page.locator('.result-item')).to_have_count(70)
        page.locator('.result-item').first.click()
        expect(page.locator('.reading')).to_be_visible()
        page.locator('.return-link').click()
        fits()
        settings()
        select(2,'Тёмная')
        close()
        expect(page.locator('html')).to_have_attribute('data-theme','dark')
        fits()
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(output/f'{width}-dark.png'), full_page=False)
        page.reload()
        expect(page.locator('html')).to_have_attribute('data-theme','dark')
        assert page.evaluate("localStorage.getItem('medjugorje-language')")=='ru'
        # Loopback SW check does not establish Android installation or hosted auth behavior.
        page.evaluate('navigator.serviceWorker.ready.then(() => true)')
        page.wait_for_function('navigator.serviceWorker.controller !== null')
        context.set_offline(True)
        page.reload()
        expect(page.locator('.result-count strong')).to_have_text(str(len(rows)))
        page.locator('.main-nav button').first.click()
        expect(page.locator('.message-text').first).to_be_visible()
        context.set_offline(False)
        assert not errors, errors
        checks.append({'width':width,'ui_languages':7,'message_languages':7,'filters':'PASS','themes':'PASS','overflow':'PASS','local_offline_reload':'PASS','page_errors':errors})
        context.close()
    browser.close()
(output/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False,indent=2))
