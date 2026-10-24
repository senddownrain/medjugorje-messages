"""Production loopback Chromium measurements. Emulation, never physical Android."""
import argparse
import gzip
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import shutil
import threading
import time
from playwright.sync_api import sync_playwright, expect

p = argparse.ArgumentParser()
p.add_argument('--dist', type=Path, default=Path('dist'))
p.add_argument('--output', type=Path, required=True)
p.add_argument('--base', default='/medjugorje-messages/')
p.add_argument('--port', type=int, default=5182)
p.add_argument('--samples', type=int, default=3)
args = p.parse_args()

class Link:
    """Shared paced response link covers page, Worker and SW fetches alike."""
    def __init__(self):
        self.lock = threading.Lock()
        self.latency = 0
        self.bandwidth = 1_250_000
        self.next_at = 0
        self.sent = 0

    def configure(self, latency, bandwidth):
        with self.lock:
            self.latency = latency / 1000
            self.bandwidth = bandwidth
            self.next_at = time.monotonic()

    def send(self, stream, body):
        for start in range(0, len(body), 16384):
            chunk = body[start:start+16384]
            with self.lock:
                deadline = max(self.next_at, time.monotonic()) + len(chunk)/self.bandwidth
                self.next_at = deadline
            time.sleep(max(0, deadline-time.monotonic()))
            try:
                stream.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                return
            with self.lock:
                self.sent += len(chunk)

    def bytes(self):
        with self.lock:
            return self.sent

link = Link()

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        return str(args.dist.resolve() / path.split('?', 1)[0].removeprefix(args.base))

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_GET(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            path = path / 'index.html'
        time.sleep(link.latency)
        if path.is_file() and 'gzip' in self.headers.get('Accept-Encoding', ''):
            body = gzip.compress(path.read_bytes(), mtime=0)
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(str(path)))
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            link.send(self.wfile, body)
        else:
            super().do_GET()

    def log_message(self, *_):
        pass

server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{args.port}' + args.base
results = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        for name, latency, bandwidth, cpu, sample in [(name, latency, bandwidth, cpu, sample) for name,latency,bandwidth,cpu in [('normal-mobile',80,1_250_000,4),('slow-mobile',150,200_000,6)] for sample in range(1,args.samples+1)]:
            link.configure(latency, bandwidth)
            context = browser.new_context(viewport={'width':390, 'height':844}, service_workers='allow')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            cdp = context.new_cdp_session(page)
            cdp.send('Network.enable')
            cdp.send('Emulation.setCPUThrottlingRate', {'rate':cpu})
            for run in ['cold', 'repeat']:
                transfer_start = link.bytes()
                transferred = []
                def received(event):
                    transferred.append(event.get('encodedDataLength', 0))
                cdp.on('Network.loadingFinished', received)
                page.goto(url, wait_until='domcontentloaded', timeout=120000)
                expect(page.locator('.message-text').first).to_be_visible(timeout=120000)
                latest = page.evaluate('performance.now()')
                startup_body_bytes = link.bytes() - transfer_start
                interactive = page.evaluate("""async () => {const before=document.documentElement.dataset.theme;
                    document.querySelector('#theme-button').click(); await new Promise(requestAnimationFrame);
                    if(before===document.documentElement.dataset.theme) throw new Error('Click had no effect');
                    return performance.now();}""")
                page.wait_for_function("document.documentElement.dataset.theme === 'dark' || document.documentElement.dataset.theme === 'light'")
                before_search = sum(transferred)
                first_resources = page.evaluate("performance.getEntriesByType('resource').map(r=>({name:r.name,bytes:r.transferSize,encoded:r.encodedBodySize,type:r.initiatorType}))")
                page_transfer = page.evaluate("performance.getEntriesByType('navigation')[0].transferSize + performance.getEntriesByType('resource').reduce((n,r)=>n+r.transferSize,0)")
                page.locator('#query').click()
                expect(page.locator('#search-results')).to_have_attribute('aria-busy', 'false', timeout=120000)
                page.locator('#query').fill('\"Дорогие дети\"')
                expect(page.locator('#search-results')).to_have_attribute('aria-busy','false', timeout=120000)
                page.wait_for_function('Number(document.querySelector("#result-total").textContent)>0')
                search_at = page.evaluate('performance.now()')
                expect(page.locator('#retry-search')).to_have_count(0)
                page.wait_for_function('Boolean(navigator.serviceWorker.controller)', timeout=120000)
                page.locator('#language-button').click()
                language_start = page.evaluate('performance.now()')
                page.locator('#reading-language').select_option('en')
                expect(page.locator('#search-results')).to_have_attribute('aria-busy','false', timeout=120000)
                language_ms = page.evaluate('performance.now()') - language_start
                page.locator('#close-settings').click()
                page.wait_for_timeout(600)
                workers = []
                session = browser.new_browser_cdp_session()
                for target in session.send('Target.getTargets')['targetInfos']:
                    if target['type'] == 'worker' and '/assets/worker-' in target['url']:
                        workers.append(target)
                heaps = []
                replies = []
                session.on('Target.receivedMessageFromTarget', lambda e: replies.append(json.loads(e['message'])))
                for target in workers:
                    attached = session.send('Target.attachToTarget', {'targetId':target['targetId'], 'flatten':False})['sessionId']
                    session.send('Target.sendMessageToTarget', {'sessionId':attached,
                        'message':json.dumps({'id':42, 'method':'Runtime.getHeapUsage'})})
                    deadline = time.monotonic()+5
                    while not any(r.get('id') == 42 for r in replies) and time.monotonic() < deadline:
                        page.wait_for_timeout(50)
                    reply = next((r for r in replies if r.get('id') == 42), {})
                    heaps.append({'url':target['url'], **reply.get('result', {}), 'error':reply.get('error')})
                    replies.clear()
                    session.send('Target.detachFromTarget', {'sessionId':attached})
                heap = heaps
                results.append({'profile':name, 'sample':sample, 'run':run, 'latest_ms':round(latest,1),
                    'interaction_ms':round(interactive,1), 'search_ready_ms':round(search_at,1), 'language_switch_with_search_ms':round(language_ms,1),
                    'first_screen_server_body_bytes':startup_body_bytes, 'all_server_body_bytes':link.bytes()-transfer_start,
                    'first_screen_cdp_transferred_bytes':before_search, 'all_transferred_bytes':sum(transferred),
                    'initial_page_transfer_bytes':page_transfer, 'first_resources':first_resources, 'worker_heap':heap, 'page_errors':errors[:]})
                cdp.remove_listener('Network.loadingFinished', received)
                page.evaluate("localStorage.setItem('medjugorje-language','ru')")
                page.goto('about:blank')
            context.set_offline(True)
            page.goto(url, wait_until='domcontentloaded')
            expect(page.locator('.message-text').first).to_be_visible(timeout=30000)
            results.append({'profile':name, 'sample':sample, 'run':'offline', 'latest_ms':round(page.evaluate('performance.now()'),1)})
            context.close()
        report = {'browser':browser.version, 'physical_android_tested':False,
            'method':'Three independent contexts per profile; cold then repeat and offline in each. Loopback gzip HTTP; shared server link paces all response bodies including Worker/SW with per-response latency and aggregate throughput. Server counts sent compressed bodies (excludes HTTP headers/TLS). Page CPU uses CDP; Worker/SW CPU not throttled. Times from navigation start; search triggered after first screen and RU phrase typed to build index; language EN tested next; each navigation starts in RU; then language changes to EN with the RU query retained, building an honest no-match EN index; times include automation observation latency; Server bytes include background SW installation up to the observation; page CDP/ResourceTiming are diagnostic and can omit SW traffic. Repeat includes installed SW. No inference about physical phone.',
            'profiles':{'normal-mobile':{'response_latency_ms':80,'down_bytes_s':1250000,'page_cpu':4}, 'slow-mobile':{'response_latency_ms':150,'down_bytes_s':200000,'page_cpu':6}},
            'results':results}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        browser.close()
finally:
    server.shutdown()
