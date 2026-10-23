"""Exercise the built application over loopback only; no deployment or PWA claim."""
import argparse
import hashlib
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
parser.add_argument('--output', type=Path, default=ROOT / 'reports/stage-c')
parser.add_argument('--port', type=int, default=5176)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
shots = args.output / 'screenshots'
shots.mkdir(exist_ok=True)
model = json.loads((ROOT / 'derived/search-metadata.json').read_text())
rows = sorted(model['messages'], key=lambda r: (r['date'], r['id']), reverse=True)
archives = {l: json.loads((ROOT / f'data/{l}.json').read_text()) for l in ('ru','be','uk','hr','en','sk','lv')}
checks, screenshots, matrix, errors, workers = [], [], [], [], []
url = f'http://127.0.0.1:{args.port}/medjugorje-messages/'

def shot(page, name, full=False):
    page.screenshot(path=str(shots / f'{name}.png'), full_page=full, animations='disabled')
    screenshots.append(f'screenshots/{name}.png')

def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')

def ready(page, count=None):
    expect(page.locator('#search-results')).to_have_attribute('aria-busy', 'false')
    expect(page.locator('#retry-search')).to_have_count(0)
    if count is not None:
        expect(page.locator('#result-total')).to_have_text(str(count))

def settings(page, ui=None, language=None, appearance=None):
    page.locator('#language-button').click()
    if ui: page.locator('#ui-language').select_option(ui)
    if language: page.locator('#reading-language').select_option(language)
    if appearance: page.locator('#appearance').select_option(appearance)
    page.locator('#close-settings').click()
    expect(page.locator('.v-dialog')).not_to_be_visible()

with tempfile.TemporaryDirectory() as temp:
    with (Path(temp) / 'preview.log').open('w+') as log:
        server = subprocess.Popen(['node','node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port',str(args.port),'--strictPort'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+25
            while True:
                if server.poll() is not None:
                    log.seek(0); raise RuntimeError(log.read())
                try:
                    with urlopen(url, timeout=1) as response:
                        if response.status == 200: break
                except OSError:
                    if time.monotonic()>deadline: raise
                    time.sleep(.1)
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
                for width in (320,390):
                    for language in archives:
                        context=browser.new_context(viewport={'width':width,'height':844},service_workers='block')
                        context.add_init_script(f"localStorage.setItem('medjugorje-language','{language}');localStorage.setItem('medjugorje-interface-language','{language}');localStorage.setItem('medjugorje-theme','light');")
                        page=context.new_page(); page.on('pageerror', lambda e:errors.append(str(e)))
                        page.on('worker',lambda w:workers.append(w.url))
                        page.goto(url)
                        latest=next(r for r in rows if r['availability'][language]=='with_text')
                        expect(page.locator('.reading')).to_have_attribute('data-message-id',latest['id'])
                        original=next(r for r in archives[language]['messages'] if r['id']==latest['id'])
                        assert '\n\n'.join(page.locator('.message-text').all_text_contents())==original['text']
                        expect(page.locator('html')).to_have_attribute('lang',language)
                        assert page.locator('.top-actions button').count()==2
                        assert not page.locator('nav').count()
                        for theme in ('light','dark'):
                            if theme=='dark': page.locator('#theme-button').click()
                            expect(page.locator('html')).to_have_attribute('data-theme',theme)
                            no_overflow(page)
                            if width==390 or language=='ru': shot(page,f'home-{language}-{width}-{theme}')
                            matrix.append({'width':width,'ui_language':language,'reading_language':language,'theme':theme,'latest_id':latest['id'],'status':'PASS'})
                        page.locator('#query').click(); ready(page,len(archives[language]['messages']))
                        page.locator('#filter-toggle').click(); no_overflow(page)
                        # Native long series labels cannot grow controls outside the viewport.
                        page.locator('#series').select_option('mirjana_second_day'); ready(page)
                        no_overflow(page)
                        context.close()
                checks.append('28 real UI combinations: 320/390px × 7 UI/reading languages × both themes; latest available text, two header controls, long filter labels, no horizontal overflow')
                context=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
                context.add_init_script("for(const [key,value] of Object.entries({'medjugorje-language':'en','medjugorje-interface-language':'ru','medjugorje-theme':'light'})){if(!localStorage.getItem(key))localStorage.setItem(key,value);}window.workerMessages=[];const send=Worker.prototype.postMessage;Worker.prototype.postMessage=function(data,...args){window.workerMessages.push(data);return send.call(this,data,...args);};")
                page=context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
                startup=[]
                page.on('request',lambda request:startup.append(request.url) if '/data/' in request.url else None)
                page.goto(url); expect(page.locator('.reading')).to_be_visible()
                assert sorted(path.rsplit('/',1)[-1] for path in startup)==sorted([f'{l}.json' for l in archives]+['index.json'])
                data_requests_before=len(startup)
                page.locator('#language-button').click(); shot(page,'language-sheet-390')
                page.locator('#ui-language').focus()
                page.keyboard.press('Tab'); expect(page.locator('#reading-language')).to_be_focused()
                page.keyboard.press('Shift+Tab'); expect(page.locator('#ui-language')).to_be_focused()
                page.locator('#ui-language').select_option('en')
                assert page.locator('#reading-language').input_value()=='en'
                page.keyboard.press('Escape'); expect(page.locator('.v-dialog')).not_to_be_visible()
                expect(page.locator('#language-button')).to_be_focused()
                settings(page, appearance='auto')
                page.emulate_media(color_scheme='dark'); expect(page.locator('html')).to_have_attribute('data-theme','dark')
                page.locator('#theme-button').click(); expect(page.locator('html')).to_have_attribute('data-theme','light')
                page.emulate_media(color_scheme='light')
                checks.append('Independent UI/reading languages, bottom sheet Escape/focus restoration, system-theme updates and immediate sun/moon override')
                page.locator('#query').focus(); ready(page,894)
                page.locator('#filter-toggle').click()
                for person in ('marija','mirjana','ivanka','jakov','ivan','vicka','unattributed'):
                    count=sum((r['visionary']['value'] or 'unattributed')==person and r['availability']['en']!='translation_not_present' for r in rows)
                    page.locator('#visionary').select_option(person); ready(page,count)
                page.locator('#visionary').select_option('ivan'); ready(page,2)
                page.locator('#include-missing').check(); ready(page,3)
                assert page.locator('.pending-label').count()==3
                shot(page,'filters-ivan-390',True)
                page.locator('[data-id="140812s"]').click()
                expect(page.locator('.reading')).to_have_attribute('data-message-id','140812s')
                assert page.locator('.message-text').count()==0
                assert '140812s' in page.url and page.locator('.other-languages button').count()>0
                assert 'approval' in page.locator('.reading .pending-label').inner_text().lower()
                shot(page,'missing-translation-390',True)
                # Refresh preserves canonical ID, missing translation and back snapshot.
                page.reload(); expect(page.locator('.reading')).to_have_attribute('data-message-id','140812s')
                assert page.locator('.message-text').count()==0
                page.locator('.reader-back').click(); ready(page,3)
                assert page.locator('#visionary').input_value()=='ivan' and page.locator('#include-missing').is_checked()
                data_requests_before=len(startup) # the deliberate refresh above legitimately loaded all eight files again
                checks.append('All six recipients + unknown; present translations by default; include-missing preserves 899-ID model; pending and missing canonical deep link survive refresh and Back')
                page.locator('#reset-search').click(); ready(page,894)
                page.locator('#search-mode').select_option('phrase')
                page.locator('#query').fill('dear children'); ready(page)
                assert page.locator('.card-snippet mark').count()>0
                page.locator('#query').fill('<img onerror=window.injected=1>'); ready(page,0)
                assert page.locator('#search-results img').count()==0 and page.evaluate('window.injected===undefined')
                page.locator('#reset-search').click(); ready(page,894)
                # Combinations use the actual module worker and date range is inclusive.
                page.locator('#year').select_option('2020')
                page.locator('#message-type').select_option('monthly')
                page.locator('#date-from').fill('2020-02-01'); page.locator('#date-to').fill('2020-03-31'); ready(page,2)
                page.locator('#exact-date').fill('2020-03-25'); ready(page,1)
                page.locator('#exact-date').fill('')
                page.locator('#date-from').fill('2021-01-01')
                expect(page.locator('#retry-search')).to_be_visible()
                page.locator('#date-from').fill('2020-02-01'); ready(page,2)
                checks.append('Words/phrases, escaped malicious input, safe highlights, filter-only year/type/exact date/inclusive range, invalid-range error and recovery')
                # Preserve the entire state and a long paged list across reader/back/forward.
                page.locator('#reset-search').click(); ready(page,894)
                page.locator('#query').fill('peace'); ready(page)
                page.locator('#filter-toggle').click()
                page.locator('#show-more').click()
                target=page.locator('.result-card').nth(43)
                target.scroll_into_view_if_needed()
                before=page.evaluate('scrollY'); target_id=target.get_attribute('data-id')
                count=page.locator('#result-total').inner_text()
                target.press('Enter'); expect(page.locator('.reading')).to_have_attribute('data-message-id',target_id)
                page.go_back(); ready(page,int(count))
                expect(page.locator('#query')).to_have_value('peace')
                assert page.locator('.result-card').count()==70
                page.wait_for_function('(y)=>Math.abs(scrollY-y)<3',arg=before)
                expect(page.locator(f'[data-id="{target_id}"]')).to_be_focused()
                page.go_forward(); expect(page.locator('.reading')).to_have_attribute('data-message-id',target_id)
                page.locator('.reader-back').click(); ready(page,int(count))
                page.wait_for_function('(y)=>Math.abs(scrollY-y)<3',arg=before)
                checks.append('Keyboard Enter opens full reading; browser Back/Forward and in-app Back restore query, filters, language, 70-row pagination, exact scroll and focused result')
                # Rapid input + language switch: final state must win over old work.
                page.locator('#query').fill('veryoldquery')
                page.locator('#query').fill('dear children')
                page.locator('#language-button').click()
                page.locator('#reading-language').select_option('uk')
                page.locator('#reading-language').select_option('en')
                page.locator('#reading-language').select_option('lv')
                page.locator('#close-settings').click()
                expect(page.locator('.v-dialog')).not_to_be_visible()
                page.locator('#query').fill('"Dargie berni"'); ready(page)
                assert int(page.locator('#result-total').inner_text())>0
                assert page.locator('#language-button').inner_text()=='LV'
                assert page.locator('.card-snippet mark').count()>0
                sent=page.evaluate('window.workerMessages')
                assert any(m.get('method')=='searchIds' and m['args'][0]=='lv' for m in sent)
                assert any(m.get('method')=='loadLanguage' for m in sent)
                assert len(startup)==data_requests_before, startup
                shot(page,'results-lv-390')
                checks.append('Real module Worker RPC in production UI, rapid queries/language switches settle on latest LV results and safe diacritic highlights')
                # Shrinking the viewport models the space available above a software keyboard.
                page.set_viewport_size({'width':390,'height':430}); page.locator('#query').focus()
                assert page.locator('#query').bounding_box()['y']>=0
                page.locator('#query').fill('neexistujucislovo'); ready(page,0)
                page.locator('#query').press('Enter'); expect(page.locator('#query')).not_to_be_focused()
                no_overflow(page); shot(page,'keyboard-space-empty-390')
                page.set_viewport_size({'width':390,'height':844})
                checks.append('Keyboard Tab/Enter/Escape and 430px reduced viewport; empty results stay usable (physical Android software keyboard NOT TESTED)')
                # Simulate worker asset failure, then retry the actual Worker successfully.
                await_worker='**/assets/worker-*.js'
                page.route(await_worker,lambda route:route.abort())
                page.reload(); page.locator('#query').click()
                expect(page.locator('#retry-search')).to_be_visible(timeout=15000)
                shot(page,'worker-error-390')
                page.unroute(await_worker); page.locator('#retry-search').click(); ready(page)
                assert page.locator('#query').input_value()=='neexistujucislovo'
                checks.append('Worker loading failure gives explicit retry; retry recovers without losing query')
                # Legacy compatibility and direct missing translation (no history state).
                page.goto(url+'#archive'); ready(page,628)
                page.goto(url+'#message/140812s'); expect(page.locator('.reading')).to_have_attribute('data-message-id','140812s')
                assert page.locator('#language-button').inner_text()=='LV'
                settings(page,language='en'); assert page.locator('.message-text').count()==0
                page.locator('.other-languages button').first.click(); expect(page.locator('.message-text').first).to_be_visible()
                assert page.url.endswith('#message/140812s')
                checks.append('Legacy #archive opens unified search; direct #message/<id> works without state; missing translation is never substituted; manual language choice retains ID')
                page.goto(url+'#message/230225m'); settings(page,language='uk')
                expect(page.locator('.context-text')).not_to_have_count(0)
                assert page.locator('.message-text').count()==0
                expect(page.locator('.empty-text')).to_be_visible()
                shot(page,'context-only-390',True)
                checks.append('Context-only UK 230225m shows an empty-message notice and separately labeled original context, without promoting quoted text')
                page.route('**/data/ru.json',lambda route:route.fulfill(status=500,body='failure'))
                page.reload(); expect(page.locator('[role="alert"]')).to_be_visible()
                page.unroute('**/data/ru.json'); page.locator('.plain-button').click(); expect(page.locator('.reading')).to_be_visible()
                checks.append('Original required-archive loading error/retry works; eager index+7 language policy unchanged')
                assert not errors,errors
                assert workers and all('/assets/worker-' in w for w in workers)
                context.close()
                report={'status':'PASS','browser':browser.version,'base_pr':18,'checks':checks,'matrix':matrix,'screenshots':screenshots,'page_errors':errors,
                    'physical_android':'NOT TESTED','physical_software_keyboard':'NOT TESTED','pwa_install_offline':'NOT TESTED','private_preview_deployment':'NOT RUN',
                    'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'data').glob('*.json'))},
                    'scope':'Built production application over loopback; service workers blocked to isolate UI. Does not validate install/offline/real Android keyboard.'}
                (args.output/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(json.dumps({'status':'PASS','checks':checks,'matrix_cases':len(matrix),'screenshots':len(screenshots)},ensure_ascii=False,indent=2))
                browser.close()
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=5)
