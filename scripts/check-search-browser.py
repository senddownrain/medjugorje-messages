"""Local-only Chromium E2E and optional measured CPU throttling; never publishes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--benchmark', action='store_true')
parser.add_argument('--output', type=Path, default=ROOT / 'reports/stage-b/search-browser.json')
parser.add_argument('--port', type=int, default=5174)
args = parser.parse_args()
url = f'http://127.0.0.1:{args.port}/medjugorje-messages/tests/search/harness.html'
checks, profiles = [], []
model=json.loads((ROOT/'derived/search-metadata.json').read_text())
unknown=sum(not r['visionary']['value'] for r in model['messages'])
with tempfile.TemporaryDirectory() as tmp:
    with (Path(tmp) / 'vite.log').open('w+') as log:
        server = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(args.port), '--strictPort'],
                                  cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while True:
                if server.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(log.read())
                try:
                    with urlopen(url, timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            with sync_playwright() as p:
                executable = shutil.which('chromium')
                browser = p.chromium.launch(executable_path=executable, args=['--no-sandbox', '--enable-precise-memory-info'])
                context = browser.new_context(viewport={'width': 390, 'height': 844})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url)
                page.wait_for_function('Boolean(window.searchHarness)', timeout=30000)
                expect(page.locator('#total')).to_have_text(str(len(model['messages'])))
                checks.append('All current canonical IDs available through the Vue adapter')
                assert page.locator('#safe-highlight img').count() == 0
                assert page.evaluate('window.injected === undefined')
                assert page.locator('#safe-highlight mark').all_text_contents() == ['C\u030car', 'Āmen', 'img']
                checks.append('Vue highlight renders HTML as text with exact combining-character offsets')
                requests = []
                page.wait_for_load_state('networkidle')
                capture_request = lambda request: requests.append(request.url)
                page.on('request', capture_request)
                phrases = {'ru': 'Дорогие дети', 'be': 'Дарагія дзеці', 'uk': 'Дорогі діти', 'hr': 'Draga djeco',
                           'en': 'Dear children', 'sk': 'Drahé deti', 'lv': 'Dārgie bērni'}
                for language, phrase in phrases.items():
                    page.locator('#language').select_option(language)
                    page.locator('#query').fill('"' + phrase + '"')
                    page.wait_for_function('Number(document.querySelector("#total").textContent)>0')
                checks.append('Actual input/select events search all seven languages without network requests')
                page.evaluate("""() => { const a=window.searchHarness.adapter;
                    a.update({query:'', filters:{visionary:'ivan'}, scrollTop:390}); a.select('140812s'); }""")
                page.locator('#language').select_option('en')
                expect(page.locator('#total')).to_have_text('3')
                selected = json.loads(page.locator('#selection').inner_text())
                assert selected == {'id': '140812s', 'availability': 'translation_not_present', 'pending': True, 'text': None}
                assert page.evaluate('window.searchHarness.adapter.snapshot().scrollTop') == 390
                assert page.locator('li[data-pending="true"]').count() == 3
                page.evaluate("window.searchHarness.adapter.update({filters:{visionary:'unattributed'}})")
                expect(page.locator('#total')).to_have_text(str(unknown))
                checks.append('Pending recipients, current unknowns, missing translation and selection/scroll survive language changes')
                assert not requests, requests
                page.remove_listener('request', capture_request)
                worker_result = page.evaluate('window.searchHarness.workerCheck()')
                assert worker_result['main_thread_timer_ticks'] > 0
                checks.append('Real module Worker returns independent concurrent results while main-thread timer remains active')
                assert not errors, errors
                if args.benchmark:
                    cdp = context.new_cdp_session(page)
                    for rate in (1, 6):
                        cdp.send('Emulation.setCPUThrottlingRate', {'rate': rate})
                        measured = []
                        for language in phrases:
                            page.evaluate('window.searchHarness.catalog.clearIndexes()')
                            cdp.send('HeapProfiler.collectGarbage')
                            before = page.evaluate('performance.memory.usedJSHeapSize')
                            result = page.evaluate('(language) => window.searchHarness.benchmark(language, 50)', language)
                            cdp.send('HeapProfiler.collectGarbage')
                            result['retained_heap_delta_bytes'] = page.evaluate('performance.memory.usedJSHeapSize') - before
                            measured.append(result)
                        profiles.append({'cpu_throttle_rate': rate, 'results': measured})
                    cdp.send('Emulation.setCPUThrottlingRate', {'rate': 1})
                report = {'browser': browser.version, 'checks': checks, 'worker': worker_result, 'page_errors': errors, 'search_network_requests': requests,
                          'profiles': profiles, 'physical_android_tested': False,
                          'methodology': 'Local Vite test harness only; Chromium 390px, real CDP CPU rate 1 and 6, 5 warmups + 50 samples/case. GC heap deltas exclude already loaded corpus/metadata. CPU throttle is not a physical Android result.'}
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                print(json.dumps({'checks': checks, 'profiles': len(profiles), 'output': str(args.output)}, ensure_ascii=False, indent=2))
                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
