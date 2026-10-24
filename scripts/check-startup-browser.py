"""Production PWA QA over trustworthy localhost. Not an Android/HTTPS deployment test."""
import argparse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, default=ROOT/'reports/stage-d/pwa.json')
args = p.parse_args()
checks = []
with tempfile.TemporaryDirectory() as temp:
    site = Path(temp)/'site'
    shutil.copytree(ROOT/'dist', site)
    requests = []

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            return str(site / path.split('?',1)[0].removeprefix('/medjugorje-messages/'))

        def do_GET(self):
            requests.append(self.path)
            super().do_GET()

        def end_headers(self):
            # Fixtures edit bytes at the same URL within one second; bypass HTTP
            # mtime/304 caching so this checks SW validation rather than fixture staleness.
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/medjugorje-messages/'
    manifest = json.loads((site/'data/latest.json').read_text())
    latest_path = '/medjugorje-messages/data/' + manifest['latest']['ru']['file']
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
            context = browser.new_context(viewport={'width':320,'height':844})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url)
            expect(page.locator('.reading')).to_have_attribute('data-message-id', manifest['latest']['ru']['id'])
            page.wait_for_function('Boolean(navigator.serviceWorker.controller)')
            page.wait_for_function("""async path => Boolean(await (await caches.open('message-immutable-data-v1')).match(path))""", arg=latest_path)
            home_requests = requests[:]
            assert not any('/metadata.json' in r or r.endswith(('/ru.json','/en.json','/be.json','/uk.json','/hr.json','/sk.json','/lv.json')) for r in home_requests), home_requests
            assert not any('/worker-' in r or '/controller-' in r or '/catalog-' in r for r in home_requests), home_requests
            assert not page.workers
            checks.append('PASS cold home: only manifest + selected latest, no archive/metadata/search code/Worker')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            context.set_offline(True)
            page.reload()
            expect(page.locator('.reading')).to_have_attribute('data-message-id', manifest['latest']['ru']['id'])
            expect(page.locator('body')).to_contain_text('Нет интернета')
            page.locator('#language-button').click()
            page.locator('#reading-language').select_option('lv')
            page.locator('#close-settings').click()
            expect(page.locator('[role="alert"]')).to_be_visible()
            assert not page.locator('.message-text').count(), 'Never fall back to another language'
            checks.append('PASS offline shell/latest; uncached language explicit error, no fallback')
            context.set_offline(False)
            lv_file = site/'data'/manifest['latest']['lv']['file']
            lv_original = lv_file.read_text()
            lv_file.write_text('<html>Temporary upstream error, HTTP 200</html>')
            page.locator('.plain-button').click()
            expect(page.locator('[role="alert"]')).to_be_visible()
            page.wait_for_timeout(200)
            assert not page.evaluate("async path => Boolean(await (await caches.open('message-immutable-data-v1')).match(path))", '/medjugorje-messages/data/'+manifest['latest']['lv']['file'])
            lv_file.write_text(lv_original)
            page.locator('.plain-button').click()
            checks.append('PASS malformed HTTP-200 data is not cached; retry succeeds after source repair')
            expect(page.locator('.reading')).to_have_attribute('data-message-id', manifest['latest']['lv']['id'])
            page.locator('#open-search').click()
            expect(page.locator('#search-results')).to_have_attribute('aria-busy','false')
            expect(page.locator('#retry-search')).to_have_count(0)
            page.locator('#query').fill('"Dārgie bērni"')
            expect(page.locator('#search-results')).to_have_attribute('aria-busy','false')
            total = page.locator('#result-total').inner_text()
            assert int(total) > 0
            requests_before = requests[:]
            page.locator('.result-card').first.click()
            expect(page.locator('.reading')).to_be_visible()
            page.go_back()
            expect(page.locator('#result-total')).to_have_text(total)
            page.go_forward()
            expect(page.locator('.reading')).to_be_visible()
            assert requests_before == requests
            context.set_offline(True)
            page.reload()
            expect(page.locator('.reading')).to_be_visible()
            page.locator('.reader-back').click()
            page.locator('#open-search').click()
            expect(page.locator('#search-results')).to_have_attribute('aria-busy','false')
            expect(page.locator('#retry-search')).to_have_count(0)
            checks.append('PASS loaded language, archive, dynamic code and search available offline; Back/Forward no resource refetch')
            context.set_offline(False)
            # A deploy that lacks a required shell resource must fail installation, preserving
            # the currently active SW and saved data. This is a synthetic deployment fixture.
            old_sw = (site/'sw.js').read_text()
            broken = old_sw.replace('index.html', 'required-missing-shell.html') + '\n// failed-install-fixture\n'
            (site/'sw.js').write_text(broken)
            page.evaluate("navigator.serviceWorker.getRegistration().then(async r => { await r.update(); window.fixtureWorker=r.installing; })")
            page.wait_for_function('window.fixtureWorker && window.fixtureWorker.state === "redundant"')
            assert page.evaluate('navigator.serviceWorker.controller.state') == 'activated'
            page.goto(url)
            expect(page.locator('.reading')).to_be_visible()
            checks.append('PASS failed new SW installation preserves active shell and previous data')
            (site/'sw.js').write_text(old_sw + '\n// successful-update-fixture\n')
            page.evaluate('navigator.serviceWorker.getRegistration().then(r => r.update())')
            expect(page.get_by_text('Доступна новая версия — обновить', exact=True)).to_be_visible(timeout=30000)
            # applyUpdate first saves history (possibly changing the hash). That
            # same-document navigation is not the reload after SW activation.
            # Wait for a new document before interacting with its settings.
            page.evaluate('window.__startupUpdateDocument = true')
            page.get_by_text('Доступна новая версия — обновить', exact=True).click()
            page.wait_for_function('window.__startupUpdateDocument !== true')
            expect(page.locator('.reading')).to_be_visible()
            page.wait_for_function('navigator.serviceWorker.getRegistration().then(r => !r.waiting)')
            checks.append('PASS SW waits for explicit update, activates/reloads, keeps saved data')
            page.locator('#language-button').click()
            page.locator('#reading-language').select_option('ru')
            page.locator('#close-settings').click()
            expect(page.locator('.reading')).to_have_attribute('data-message-id', manifest['latest']['ru']['id'])
            # New data version, same source content. No message is fabricated or approved.
            new_version = 'f'*24
            shutil.copytree(site/'data'/manifest['data_version'], site/'data'/new_version)
            new_manifest = json.loads(json.dumps(manifest).replace(manifest['data_version'], new_version))
            for path in (site/'data'/new_version).glob('latest-*.json'):
                record = json.loads(path.read_text()); record['data_version']=new_version
                path.write_text(json.dumps(record))
            (site/'data/latest.json').write_text(json.dumps(new_manifest))
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.get_by_text('Доступна новая версия — обновить', exact=True)).to_be_visible()
            page.evaluate('window.__startupUpdateDocument = true')
            page.get_by_text('Доступна новая версия — обновить', exact=True).click()
            page.wait_for_function('window.__startupUpdateDocument !== true')
            expect(page.locator('.reading')).to_be_visible()
            page.wait_for_function("""async version => {
                const r=await (await caches.open('message-manifest-schema-1')).match('./data/latest.json');
                return r && (await r.json()).data_version===version;
            }""", arg=new_version)
            context.set_offline(True); page.reload()
            expect(page.locator('.reading')).to_be_visible()
            page.locator('#language-button').click()
            page.locator('#reading-language').select_option('lv')
            page.locator('#close-settings').click()
            expect(page.locator('.reading')).to_have_attribute('data-message-id', manifest['latest']['lv']['id'])
            checks.append('PASS data-only update on foreground/confirmation; old loaded LV remains offline through whole-snapshot fallback')
            assert not errors, errors
            report = {'status':'PASS','browser':browser.version,'checks':checks,'home_requests':home_requests,
                'physical_android':'NOT TESTED','real_https_auth':'NOT TESTED',
                'scope':'Built production app; localhost SW; synthetic failed/successful deployments preserve original message texts.'}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(report,ensure_ascii=False,indent=2))
            browser.close()
    finally:
        server.shutdown()
