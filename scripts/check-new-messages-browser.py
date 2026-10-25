"""Production Chromium: synthetic arrival metadata, real unchanged archive.

Not an installed Android-device test. No fabricated source content.
"""
import argparse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'work/new-messages');a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
checks=[]
with tempfile.TemporaryDirectory() as temp:
 site=Path(temp)/'site';shutil.copytree(ROOT/'dist',site)
 manifest_path=site/'data/latest.json';manifest=json.loads(manifest_path.read_text());manifest['arrivals']={}
 manifest_path.write_text(json.dumps(manifest))
 class Handler(SimpleHTTPRequestHandler):
  def translate_path(self,path):return str(site/path.split('?',1)[0].removeprefix('/medjugorje-messages/'))
  def end_headers(self):self.send_header('Cache-Control','no-store');super().end_headers()
  def log_message(self,*_):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{server.server_port}/medjugorje-messages/'
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
   context=browser.new_context(viewport={'width':390,'height':844})
   page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(url);expect(page.locator('.reading')).to_be_visible()
   expect(page.locator('.new-badge')).to_have_count(0)
   page.wait_for_function('Boolean(navigator.serviceWorker.controller)')
   checks.append('PASS first visit: no archive marked new')
   ru=manifest['latest']['ru']['id'];sk=manifest['latest']['sk']['id']
   manifest['arrivals']={'ru':[ru]};manifest_path.write_text(json.dumps(manifest))
   page.reload();expect(page.locator('.reading .new-badge')).to_have_text('Новое')
   page.wait_for_function("async()=>Boolean(await(await caches.open('message-manifest-schema-1')).match('/medjugorje-messages/data/latest.json'))")
   for theme in ('light','dark'):
    for width in (320,390):
     page.evaluate("theme=>localStorage.setItem('medjugorje-theme',theme)",theme)
     page.set_viewport_size({'width':width,'height':844});page.reload()
     expect(page.locator('html')).to_have_attribute('data-theme',theme)
     badge=page.locator('.reading .new-badge');expect(badge).to_be_visible()
     assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
     page.screenshot(path=str(a.output/f'new-home-{theme}-{width}.png'),full_page=True)
     page.locator('#open-search').click();expect(page.locator('#search-results')).to_have_attribute('aria-busy','false')
     expect(page.locator(f'.result-card[data-id="{ru}"] .new-badge')).to_be_visible()
     page.screenshot(path=str(a.output/f'new-list-{theme}-{width}.png'),full_page=True)
     page.goto(url)
   checks.append('PASS home/list badge: light/dark at 320/390px, no horizontal overflow')
   context.set_offline(True);page.reload();expect(page.locator('.reading .new-badge')).to_be_visible()
   checks.append('PASS badge survives offline restart with cached manifest')
   page.locator('#open-search').click();expect(page.locator('#search-results')).to_have_attribute('aria-busy','false')
   page.locator(f'.result-card[data-id="{ru}"]').click();expect(page.locator('.reading .new-badge')).to_have_count(0)
   page.reload();expect(page.locator('.reading')).to_be_visible();expect(page.locator('.new-badge')).to_have_count(0)
   checks.append('PASS explicit open marks selected translation read; survives offline restart')
   context.set_offline(False)
   manifest['arrivals']['sk']=[sk];manifest_path.write_text(json.dumps(manifest));page.goto(url)
   expect(page.locator('.new-badge')).to_have_count(0)
   page.locator('#language-button').click();page.locator('#reading-language').select_option('sk');page.locator('#close-settings').click()
   expect(page.locator('.reading .new-badge')).to_be_visible()
   page.locator('.reading .new-badge').click();expect(page.locator('.new-badge')).to_have_count(0)
   checks.append('PASS late SK translation is independent of already read RU')
   assert not errors,errors
   context.close();browser.close()
 finally:server.shutdown()
(a.output/'result.json').write_text(json.dumps({'status':'PASS','checks':checks,'android_device':'NOT TESTED','fixtures':'Arrival metadata only; source archive unchanged'},ensure_ascii=False,indent=2)+'\n')
print('\n'.join(checks))
