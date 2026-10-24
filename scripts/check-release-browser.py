"""Production release checks on localhost or the anonymous public Pages URL."""
import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import threading
import tempfile
import time
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--url')
p.add_argument('--expected-sha')
p.add_argument('--output', type=Path, default=ROOT/'work/release-browser')
args = p.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
shots = args.output/'screenshots'; shots.mkdir(exist_ok=True)
languages = ['ru','be','uk','hr','en','sk','lv']
phrases = dict(zip(languages, ['Дорогие дети','Дарагія дзеці','Дорогі діти','Draga djeco','Dear children','Drahé deti','Dārgie bērni']))
archives = {l:json.loads((ROOT/f'data/{l}.json').read_text()) for l in languages}
model = json.loads((ROOT/'derived/search-metadata.json').read_text())
rows = sorted(model['messages'], key=lambda r:(r['date'],r['id']), reverse=True)
matrix, checks, errors = [], [], []
server = None
if args.url:
    url = args.url
else:
    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            return str(ROOT/'dist'/path.split('?',1)[0].removeprefix('/medjugorje-messages/'))
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/medjugorje-messages/'

def read_url(path):
    with urlopen(Request(url+path, headers={'Cache-Control':'no-cache'}), timeout=30) as response:
        assert response.status == 200
        return response.read()

if args.expected_sha:
    for attempt in range(60):
        try:
            published = json.loads(read_url('release.json?check='+str(time.time_ns())))
            if published['sha'] == args.expected_sha: break
        except Exception:
            if attempt == 59: raise
        time.sleep(3)
    else: raise AssertionError('Public release SHA has not reached the requested commit')
else:
    published = json.loads(read_url('release.json'))
manifest = json.loads(read_url('data/latest.json'))
assert set(manifest['latest']) == set(languages)
for language in languages:
    raw = read_url('data/'+manifest['latest'][language]['archive'])
    assert hashlib.sha256(raw).hexdigest() == hashlib.sha256((ROOT/f'data/{language}.json').read_bytes()).hexdigest()
checks.append('PASS HTTP 200; public release SHA (when requested); all seven served archives byte-identical to source JSON')

def fits(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'

def ready(page):
    expect(page.locator('#search-results')).to_have_attribute('aria-busy','false',timeout=30000)
    expect(page.locator('#retry-search')).to_have_count(0)

def choose(page, language, ui=None):
    page.locator('#language-button').click()
    page.locator('#reading-language').select_option(language)
    if ui: page.locator('#ui-language').select_option(ui)
    page.locator('#close-settings').click()
    expect(page.locator('.language-sheet.v-overlay--active')).to_have_count(0)

def close_filters(page, method='button'):
    expect(page.locator('.filter-sheet.v-overlay--active')).to_be_visible()
    if method == 'back': page.go_back()
    elif method == 'escape': page.keyboard.press('Escape')
    else: page.locator('#close-filters').click()
    expect(page.locator('.filter-sheet.v-overlay--active')).to_have_count(0)
    expect(page.locator('#filter-toggle')).to_have_attribute('aria-expanded','false')

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
        for width in [320,390]:
            context = browser.new_context(viewport={'width':width,'height':844},is_mobile=True,has_touch=True)
            page = context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
            for language in languages:
                if language == 'ru': page.goto(url)
                else: choose(page,language,language)
                latest = manifest['latest'][language]['id']
                expect(page.locator('.reading')).to_have_attribute('data-message-id',latest,timeout=30000)
                record = next(r for r in archives[language]['messages'] if r['id']==latest)
                assert '\n\n'.join(page.locator('.message-text').all_text_contents()) == record['text']
                for theme in ['light','dark']:
                    if page.locator('html').get_attribute('data-theme') != theme: page.locator('#theme-button').click()
                    fits(page)
                    matrix.append({'width':width,'language':language,'theme':theme,'status':'PASS'})
                    if language == 'ru': page.screenshot(path=str(shots/f'home-{width}-{theme}.png'),animations='disabled')
                page.locator('#open-search').click(); ready(page)
                assert int(page.locator('#result-total').inner_text())==len(archives[language]['messages'])
                page.locator('#query').fill('"'+phrases[language]+'"'); ready(page)
                expect(page.locator('.result-card').first).to_be_visible()
                assert page.locator('.card-snippet mark').count()>0
                assert page.locator('#search-results').evaluate("el=>!el.closest('[role=dialog]')")
                bar=page.locator('.search-bar').bounding_box()
                assert abs(bar['y']+bar['height']-844) < 40
                fits(page)
                page.locator('#close-search').click()
                expect(page.locator('.reading')).to_be_visible()
            context.close()
        checks.append('PASS 28 mobile viewport/language/theme cases; exact latest texts; search highlights and independent seven languages; results in page above bottom bar')

        context = browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        page=context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url); expect(page.locator('.reading')).to_be_visible()
        choose(page,'en','en')
        page.locator('#open-search').click(); ready(page)
        page.locator('#query').fill('peace'); ready(page)
        page.screenshot(path=str(shots/'search-390-light.png'),animations='disabled')
        page.locator('#filter-toggle').click()
        expect(page.locator('#search-filters')).to_be_visible()
        assert page.locator('#search-filters select').evaluate_all('(nodes)=>nodes.map(n=>n.id)')==['visionary','message-type','year','month']
        page.locator('#visionary').select_option('marija')
        page.locator('#year').select_option('2020'); ready(page)
        total=page.locator('#result-total').inner_text(); assert int(total)>0
        page.screenshot(path=str(shots/'filters-390-light.png'),animations='disabled')
        expect(page.locator('#search-filters')).to_be_visible()
        close_filters(page,'back'); ready(page)
        expect(page.locator('#result-total')).to_have_text(total)
        expect(page.locator('.filter-dot')).to_be_visible()
        page.locator('#filter-toggle').click()
        assert page.locator('#year').input_value()=='2020'
        close_filters(page,'escape'); ready(page)
        page.locator('.result-card').first.click(); expect(page.locator('.reading')).to_be_visible()
        page.go_back(); ready(page)
        assert page.locator('#query').input_value()=='peace'
        expect(page.locator('#result-total')).to_have_text(total)
        page.locator('#filter-toggle').click(); page.locator('#reset-search').click(); ready(page)
        assert page.locator('#query').input_value()=='peace'
        assert all(page.locator('#'+key).input_value()=='' for key in ['visionary','message-type','year','month'])
        close_filters(page)
        page.locator('#show-more').click()
        target=page.locator('.result-card').nth(43); target.scroll_into_view_if_needed()
        before=page.evaluate('scrollY'); identifier=target.get_attribute('data-id')
        target.press('Enter'); expect(page.locator('.reading')).to_have_attribute('data-message-id',identifier)
        page.go_back(); ready(page)
        assert page.locator('.result-card').count()==70
        page.wait_for_function('(y)=>Math.abs(scrollY-y)<3',arg=before)
        expect(page.locator(f'[data-id="{identifier}"]')).to_be_focused()
        page.go_forward(); expect(page.locator('.reading')).to_have_attribute('data-message-id',identifier)
        page.locator('.reader-back').click(); ready(page)
        page.wait_for_function('(y)=>Math.abs(scrollY-y)<3',arg=before)
        checks.append('PASS four independent filters, native Back/Escape closes sheet while retaining results and filters; reset preserves query; reader Back/Forward restores 70 cards, scroll and focus')
        page.locator('#query').fill('<img onerror=window.injected=1>'); ready(page)
        expect(page.locator('#result-total')).to_have_text('0')
        assert page.locator('#search-results img').count()==0 and page.evaluate('window.injected===undefined')
        for width in [320,390]:
            page.set_viewport_size({'width':width,'height':430})
            page.locator('#query').focus(); fits(page)
            bar=page.locator('.search-bar').bounding_box()
            assert 0 <= bar['y'] and bar['y']+bar['height']<=430
            page.locator('#query').press('Enter'); expect(page.locator('#query')).not_to_be_focused()
            page.locator('#theme-button').click()
            page.screenshot(path=str(shots/f'search-{width}-reduced.png'),animations='disabled')
        page.set_viewport_size({'width':390,'height':844})
        page.goto(url+'#message/140812s')
        expect(page.locator('.reading')).to_have_attribute('data-message-id','140812s')
        assert page.locator('.message-text').count()==0
        expect(page.locator('.reading .pending-label')).to_be_visible()
        page.reload(); expect(page.locator('.reading')).to_be_visible()
        assert page.locator('.message-text').count()==0
        checks.append('PASS XSS-safe empty results, reduced viewport 320/390 × 430, search submit dismisses focus; direct message refresh and explicit missing translation/pending attribution')
        context.close()

        profile = tempfile.TemporaryDirectory()
        context=pw.chromium.launch_persistent_context(profile.name,executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'],viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        page=context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
        requests=[]; page.on('request',lambda r:requests.append(r.url))
        response=page.goto(url)
        assert response.status==200 and (not args.url or page.url.startswith('https://'))
        expect(page.locator('.reading')).to_be_visible()
        page.wait_for_function('Boolean(navigator.serviceWorker.controller)',timeout=30000)
        scope=page.evaluate('navigator.serviceWorker.getRegistration().then(r=>r.scope)')
        assert scope==url
        assert not page.workers
        assert not any('/metadata.json' in r or r.endswith(tuple('/'+l+'.json' for l in languages)) for r in requests)
        cdp=context.new_cdp_session(page)
        app_manifest=cdp.send('Page.getAppManifest')
        assert not app_manifest['errors'], app_manifest
        installability=cdp.send('Page.getInstallabilityErrors')
        assert not installability['installabilityErrors'],installability
        for language in languages:
            if language!='ru': choose(page,language,language)
            expect(page.locator('.reading')).to_have_attribute('data-message-id',manifest['latest'][language]['id'])
            page.locator('#open-search').click(); ready(page)
            page.locator('#query').fill('"'+phrases[language]+'"'); ready(page)
            expect(page.locator('.result-card').first).to_be_visible()
            page.wait_for_function('async path=>Boolean(await (await caches.open("message-immutable-data-v1")).match(path))',arg=url+'data/'+manifest['latest'][language]['file'])
            context.set_offline(True)
            page.reload(); ready(page)
            expect(page.locator('.result-card').first).to_be_visible()
            page.locator('.result-card').first.click(); expect(page.locator('.reading')).to_be_visible()
            page.reload(); expect(page.locator('.reading')).to_be_visible()
            page.locator('#language-button').click()
            page.locator('#reading-language').select_option(language)
            page.locator('#close-settings').click()
            page.locator('.brand').click(); expect(page.locator('.reading')).to_have_attribute('data-message-id',manifest['latest'][language]['id'])
            context.set_offline(False)
        page.screenshot(path=str(shots/'offline-ready-390.png'),animations='disabled')
        checks.append('PASS anonymous HTTPS (public mode), SW scope, Chromium installability; lazy startup; all seven cached languages/search/archive/message reload work offline')
        assert not errors, errors
        report={'status':'PASS','url':url,'release':published,'browser':browser.version,'matrix':matrix,'checks':checks,'page_errors':errors,
                'installability':installability,'service_worker_scope':scope,
                'physical_android':'NOT TESTED','physical_keyboard':'NOT TESTED','os_pwa_install':'NOT TESTED',
                'cache_update':'Separate test: check-startup-browser.py, synthetic failed/successful shell and data updates',
                'screenshots':[str(f.relative_to(args.output)) for f in sorted(shots.glob('*.png'))]}
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        context.close(); profile.cleanup()
        browser.close()
finally:
    if server: server.shutdown()
