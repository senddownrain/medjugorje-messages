"""Phased UX checks of the built app, loopback only; no deploy or PWA claims."""
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

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--phase', choices=['filters','languages','reader','regression'], default='regression')
parser.add_argument('--output',type=Path,default=ROOT/'reports/stage-c-polish')
parser.add_argument('--port',type=int,default=5176)
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
shots=args.output/'screenshots';shots.mkdir(exist_ok=True)
model=json.loads((ROOT/'derived/search-metadata.json').read_text())
rows=sorted(model['messages'],key=lambda r:(r['date'],r['id']),reverse=True)
archives={l:json.loads((ROOT/f'data/{l}.json').read_text()) for l in ['ru','be','uk','hr','en','sk','lv']}
checks=[];screenshots=[];matrix=[];errors=[]
url=f'http://127.0.0.1:{args.port}/medjugorje-messages/'

def shot(page,name,full=False):
    page.screenshot(path=str(shots/(name+'.png')),full_page=full,animations='disabled')
    screenshots.append('screenshots/'+name+'.png')

def fits(page):
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')

def ready(page,count=None):
    expect(page.locator('#search-results')).to_have_attribute('aria-busy','false')
    expect(page.locator('#retry-search')).to_have_count(0)
    if count is not None:expect(page.locator('#result-total')).to_have_text(str(count))

def count(language='en',**filters):
    return sum(r['availability'][language]!='translation_not_present' and all(
        (r['date'][:4]==v if k=='year' else r['date'][5:7]==v if k=='month' else
         (r['visionary']['value'] or 'unattributed')==v if k=='visionary' else r[k]['value']==v)
        for k,v in filters.items()) for r in rows)

def boot(browser,width=390,ui='ru',language='en',suffix=''):
    context=browser.new_context(viewport={'width':width,'height':844},service_workers='block')
    defaults={'medjugorje-language':language,'medjugorje-interface-language':ui,'medjugorje-theme':'light'}
    context.add_init_script('for(const [k,v] of Object.entries('+json.dumps(defaults)+')){if(!localStorage.getItem(k))localStorage.setItem(k,v);}')
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url+suffix);expect(page.locator('.reading')).to_be_visible() if not suffix else None
    return context,page

def languages(page,ui=None,language=None):
    page.locator('#language-button').click()
    if ui:page.locator('#ui-language').select_option(ui)
    if language:page.locator('#reading-language').select_option(language)
    page.locator('#close-settings').click();expect(page.locator('.v-dialog')).not_to_be_visible()

def phase_filters(browser):
    for width in [320,390]:
        context,page=boot(browser,width)
        page.locator('#query').click();ready(page,894)
        expect(page.locator('#search-filters')).to_have_count(0)
        expect(page.locator('#reset-search')).to_have_count(0)
        page.locator('#query').fill('peace');ready(page)
        assert int(page.locator('#result-total').inner_text())>0
        page.locator('#filter-toggle').click()
        assert page.locator('#search-filters select').evaluate_all('(nodes)=>nodes.map(n=>n.id)')==['visionary','message-type','year','month']
        assert page.locator('#search-filters input').count()==0
        assert page.locator('input[type=search]').count()==1
        page.locator('#query').fill('')
        page.locator('#month').select_option('09');ready(page,count(month='09'))
        assert len({r['date'][:4] for r in rows if r['date'][5:7]=='09'})>1
        page.locator('#year').select_option('2020');ready(page,count(month='09',year='2020'))
        fits(page);shot(page,f'a-filters-{width}')
        page.locator('#query').fill('peace');ready(page)
        page.locator('#reset-search').click();ready(page)
        assert page.locator('#query').input_value()=='peace'
        assert int(page.locator('#result-total').inner_text())>1
        expect(page.locator('#reset-search')).to_have_count(0)
        assert page.locator('#month').input_value()==page.locator('#year').input_value()==''
        page.locator('#query').fill('')
        page.locator('#year').select_option('2020');page.locator('#month').select_option('09')
        ready(page,count(month='09',year='2020'))
        page.locator('.result-card').first.click();expect(page.locator('.reading')).to_be_visible()
        page.locator('.reader-back').click();ready(page,count(month='09',year='2020'))
        assert page.locator('#year').input_value()=='2020' and page.locator('#month').input_value()=='09'
        context.close()
    checks.append('A PASS: four controls only, word search before filters, month across years, year AND month, live updates, reset preserves query, 320/390px')

def phase_languages(browser):
    for width in [320,390]:
        context,page=boot(browser,width,language='ru')
        assert page.locator('.top-actions button').count()==2
        page.locator('#language-button').click()
        assert page.locator('.settings-dialog select').evaluate_all('(nodes)=>nodes.map(n=>n.id)')==['ui-language','reading-language']
        page.locator('#ui-language').focus();page.keyboard.press('Tab');expect(page.locator('#reading-language')).to_be_focused()
        shot(page,f'b-languages-{width}')
        page.keyboard.press('Escape');expect(page.locator('.v-dialog')).not_to_be_visible()
        expect(page.locator('#language-button')).to_be_focused()
        shot(page,f'b-light-{width}')
        page.locator('#theme-button').click();expect(page.locator('html')).to_have_attribute('data-theme','dark')
        expect(page.locator('.v-dialog')).not_to_be_visible();fits(page);shot(page,f'b-dark-{width}')
        languages(page,ui='be',language='lv')
        expect(page.locator('html')).to_have_attribute('lang','be')
        expect(page.locator('#language-button')).to_have_text('LV')
        page.reload();expect(page.locator('.reading')).to_be_visible()
        expect(page.locator('html')).to_have_attribute('lang','be')
        expect(page.locator('html')).to_have_attribute('data-theme','dark')
        expect(page.locator('#language-button')).to_have_text('LV')
        page.locator('#theme-button').click();expect(page.locator('html')).to_have_attribute('data-theme','light')
        page.reload();expect(page.locator('html')).to_have_attribute('data-theme','light')
        context.close()
    checks.append('B PASS: language sheet has two independent languages only; sun/moon never opens sheet; settings persist on refresh; keyboard focus returns')

def phase_reader(browser):
    for width in [320,390]:
        context,page=boot(browser,width,language='ru')
        latest=next(r for r in rows if r['availability']['ru']=='with_text')
        expect(page.locator('.reading')).to_have_attribute('data-message-id',latest['id'])
        expect(page.locator('.reading-person')).to_have_text('Мария Павлович-Лунетти')
        expect(page.locator('.reading-type')).to_have_text('Ежемесячное послание')
        assert page.locator('.reading-kicker svg,.brand svg,.footer svg').count()==0
        assert page.locator('.reading-divider').count()==1
        assert 'Серия' not in page.locator('.reading').inner_text()
        record=next(r for r in archives['ru']['messages'] if r['id']==latest['id'])
        assert '\n\n'.join(page.locator('.message-text').all_text_contents())==record['text']
        fits(page);shot(page,f'c-latest-{width}')
        page.goto(url+'#message/850114w')
        expect(page.locator('.reading-person')).to_have_text('Вицка Иванкович-Миятович')
        expect(page.locator('.reading .pending-label')).to_be_visible()
        expect(page.locator('.reading-kicker')).to_have_count(0)
        fits(page);shot(page,f'c-vicka-{width}')
        context.close()
    checks.append('C PASS: full names, human message type, no series placeholders or brand stars; one divider; historical reader has no Latest label; unchanged long text at 320px and pending preserved')

def regression(browser):
    for width in [320,390]:
        for language in archives:
            context,page=boot(browser,width,ui=language,language=language)
            latest=next(r for r in rows if r['availability'][language]=='with_text')
            expect(page.locator('.reading')).to_have_attribute('data-message-id',latest['id'])
            for theme in ['light','dark']:
                if theme=='dark':page.locator('#theme-button').click()
                expect(page.locator('html')).to_have_attribute('data-theme',theme)
                fits(page)
                if width==390:shot(page,f'after-{language}-{width}-{theme}')
                matrix.append({'width':width,'ui_language':language,'theme':theme,'status':'PASS'})
            page.locator('#query').click();ready(page,len(archives[language]['messages']))
            page.locator('#filter-toggle').click()
            assert page.locator('#visionary option').count()==8 # all + six people + unknown
            for person in ['marija','mirjana','ivanka','jakov','ivan','vicka','unattributed']:
                page.locator('#visionary').select_option(person);ready(page,count(language,visionary=person));fits(page)
            context.close()
    checks.append('Regression PASS: 28 real Chromium viewport/language/theme combinations; all six people plus unknown, full labels fit, present translations only, no horizontal scroll')
    context,page=boot(browser,ui='en')
    page.add_init_script("window.workerMessages=[];const send=Worker.prototype.postMessage;Worker.prototype.postMessage=function(data,...rest){window.workerMessages.push(data);return send.call(this,data,...rest);};")
    page.reload();expect(page.locator('.reading')).to_be_visible()
    page.locator('#query').click();ready(page,894)
    page.locator('#query').fill('"dear children" peace');ready(page)
    assert page.locator('.card-snippet mark').count()>0
    page.locator('#query').fill('<img onerror=window.injected=1>');ready(page,0)
    assert page.locator('#search-results img').count()==0 and page.evaluate('window.injected===undefined')
    page.locator('#query').fill('peace');ready(page)
    page.locator('#filter-toggle').click()
    page.locator('#message-type').select_option('monthly');ready(page)
    page.locator('#filter-toggle').click();page.locator('#show-more').click()
    target=page.locator('.result-card').nth(43);target.scroll_into_view_if_needed()
    before=page.evaluate('scrollY');identifier=target.get_attribute('data-id');total=int(page.locator('#result-total').inner_text())
    target.press('Enter');expect(page.locator('.reading')).to_have_attribute('data-message-id',identifier)
    page.go_back();ready(page,total)
    assert page.locator('#query').input_value()=='peace' and page.locator('.result-card').count()==70
    page.wait_for_function('(y)=>Math.abs(scrollY-y)<3',arg=before)
    expect(page.locator(f'[data-id="{identifier}"]')).to_be_focused()
    page.go_forward();expect(page.locator('.reading')).to_have_attribute('data-message-id',identifier)
    page.locator('.reader-back').click();ready(page,total)
    page.wait_for_function('(y)=>Math.abs(scrollY-y)<3',arg=before)
    checks.append('Regression PASS: safe word/phrase highlights; keyboard Enter; Back/Forward/in-app Back restore query/type/language/70 cards/scroll/focus')
    page.locator('#query').fill('oldquery');page.locator('#query').fill('dear children')
    page.locator('#language-button').click()
    for language in ['uk','en','lv']:page.locator('#reading-language').select_option(language)
    page.locator('#close-settings').click();expect(page.locator('.v-dialog')).not_to_be_visible()
    page.locator('#filter-toggle').click();page.locator('#reset-search').click()
    page.locator('#query').fill('"Dargie berni"');ready(page)
    assert int(page.locator('#result-total').inner_text())>0
    messages=page.evaluate('window.workerMessages')
    assert any(m.get('method')=='searchIds' and m['args'][0]=='lv' for m in messages)
    assert all(m['args'][1]['filters']['availability']=='present' for m in messages if m.get('method')=='searchIds')
    shot(page,'d-results-lv')
    checks.append('Regression PASS: real module Worker RPC; rapid query/language changes finish with latest LV result; no hidden availability mode')
    # Pre-polish browser history must not retain invisible series/date/search controls.
    page.evaluate("history.replaceState({readerV2:true,snapshot:{language:'en',query:'',filters:{year:'2020',month:'09',series:'ivan_special',date:'1984-08-14'},mode:'phrase',includeMissing:true,foldDiacritics:false,searchOpen:true,filtersOpen:true,limit:35,scrollTop:0}},'','#search')")
    page.reload();ready(page,count(year='2020',month='09'))
    assert page.locator('#year').input_value()=='2020' and page.locator('#month').input_value()=='09'
    page.goto(url+'#archive');ready(page,894)
    page.goto(url+'#message/140812s');expect(page.locator('.reading')).to_have_attribute('data-message-id','140812s')
    assert page.locator('.message-text').count()==0
    expect(page.locator('.reading .pending-label')).to_be_visible()
    shot(page,'d-missing-translation')
    page.reload();expect(page.locator('.reading')).to_have_attribute('data-message-id','140812s')
    assert page.locator('.message-text').count()==0
    page.locator('.other-languages button').first.click();expect(page.locator('.message-text').first).to_be_visible()
    assert page.url.endswith('#message/140812s')
    unknown=next(r for r in rows if r['visionary']['value'] is None and r['availability']['en']=='with_text')
    languages(page,language='en');page.goto(url+'#message/'+unknown['id'])
    expect(page.locator('.reading-person')).to_have_text('Not specified')
    expect(page.locator('.reading .pending-label')).to_have_count(0)
    page.goto(url+'#message/230225m');languages(page,language='uk')
    expect(page.locator('.context-text')).not_to_have_count(0);assert page.locator('.message-text').count()==0
    checks.append('Regression PASS: old history drops removed controls; month restores; #archive and #message refresh work; missing translation never falls back; context stays separate')
    page.goto(url+'#search');page.locator('#query').fill('neexistujucislovo');ready(page,0)
    page.set_viewport_size({'width':390,'height':430});page.locator('#query').focus();page.locator('#query').press('Enter')
    expect(page.locator('#query')).not_to_be_focused();fits(page);shot(page,'d-keyboard-space')
    page.set_viewport_size({'width':390,'height':844})
    worker_url='**/assets/worker-*.js'
    page.route(worker_url,lambda route:route.abort());page.reload()
    expect(page.locator('#retry-search')).to_be_visible(timeout=15000)
    page.unroute(worker_url);page.locator('#retry-search').click();ready(page,0)
    assert page.locator('#query').input_value()=='neexistujucislovo'
    archive_url='**/data/*/'+page.evaluate("localStorage.getItem('medjugorje-language')")+'.json'
    page.route(archive_url,lambda route:route.fulfill(status=500,body='failure'));page.reload()
    expect(page.locator('#retry-search')).to_be_visible()
    page.unroute(archive_url);page.locator('#retry-search').click();ready(page,0)
    checks.append('Regression PASS: empty results, reduced 430px viewport, Worker/archive loading error and retry preserve query; actual Android keyboard NOT TESTED')
    context.close()

with tempfile.TemporaryDirectory() as temp:
    with (Path(temp)/'preview.log').open('w+') as log:
        server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port',str(args.port),'--strictPort'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+25
            while True:
                if server.poll() is not None:log.seek(0);raise RuntimeError(log.read())
                try:
                    with urlopen(url,timeout=1) as response:
                        if response.status==200:break
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.1)
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
                if args.phase in ['filters','regression']:phase_filters(browser)
                if args.phase in ['languages','regression']:phase_languages(browser)
                if args.phase in ['reader','regression']:phase_reader(browser)
                if args.phase=='regression':regression(browser)
                assert not errors,errors
                report={'status':'PASS','phase':args.phase,'browser':browser.version,'checks':checks,'matrix':matrix,'screenshots':screenshots,'page_errors':errors,
                    'physical_android':'NOT TESTED','physical_software_keyboard':'NOT TESTED','pwa_install_offline':'NOT TESTED','deployment':'NOT RUN',
                    'original_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'data').glob('*.json'))},
                    'scope':'Built production app over loopback, service workers blocked. Before screenshots copied unchanged from PR19 2c69a62. No Android device or OS keyboard.'}
                target=args.output/('browser.json' if args.phase=='regression' else args.phase+'.json')
                target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(json.dumps({'status':'PASS','phase':args.phase,'checks':checks,'matrix_cases':len(matrix),'screenshots':len(screenshots)},ensure_ascii=False,indent=2))
                browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
