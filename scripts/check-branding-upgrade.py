"""Real Chromium cache upgrade from the previous public release, on one local origin.

No source JSON is edited. Only the temporary HTTP document root changes.
Physical Android/iOS launcher icon refresh is a separate device check.
"""
import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect
from branding_qa import check_theme

ROOT=Path(__file__).resolve().parents[1]
BASE='/medjugorje-messages/'
OLD='4fdf86e893d08e6335839f34bf632240aad19b71'
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=ROOT/'work/branding-upgrade')
args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='branding-upgrade-') as tmp:
    old=Path(tmp)/'old';old.mkdir()
    if subprocess.run(['git','cat-file','-e',OLD],cwd=ROOT,stderr=subprocess.DEVNULL).returncode:
        subprocess.run(['git','fetch','--no-tags','--depth=1','origin',OLD],cwd=ROOT,check=True)
    archive=subprocess.check_output(['git','archive',OLD],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(old,filter='data')
    (old/'node_modules').symlink_to(ROOT/'node_modules',target_is_directory=True)
    subprocess.run(['npm','run','build'],cwd=old,env={**os.environ,'GITHUB_SHA':OLD},check=True,stdout=subprocess.DEVNULL)
    served={'root':old/'dist'}
    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self,path):return str(served['root']/path.split('?',1)[0].removeprefix(BASE))
        def log_message(self,*_):pass
        def end_headers(self):
            self.send_header('Cache-Control','no-store');super().end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}{BASE}'
    try:
        with sync_playwright() as pw:
            context=pw.chromium.launch_persistent_context(str(Path(tmp)/'profile'),executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'],viewport={'width':390,'height':844})
            page=context.pages[0];errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url);expect(page.locator('.reading')).to_be_visible()
            page.wait_for_function('!!navigator.serviceWorker.controller')
            # Relaunch the previously installed shell, rather than conflating
            # its very first SW installation with a later application upgrade.
            page.reload();expect(page.locator('.reading')).to_be_visible()
            page.wait_for_function('!!navigator.serviceWorker.controller')
            old_icon=page.evaluate('async ()=>Array.from(new Uint8Array(await (await fetch("icon-192.png")).arrayBuffer()))')
            assert hashlib.sha256(bytes(old_icon)).digest()==hashlib.sha256((old/'dist/icon-192.png').read_bytes()).digest()
            page.screenshot(path=str(args.output/'upgrade-before.png'))
            served['root']=ROOT/'dist'
            page.evaluate('navigator.serviceWorker.getRegistration().then(r=>r.update())')
            expect(page.get_by_text('Доступна новая версия — обновить',exact=True)).to_be_visible(timeout=30000)
            page.evaluate('window.__oldBrandDocument=true')
            page.get_by_text('Доступна новая версия — обновить',exact=True).click()
            page.wait_for_function('window.__oldBrandDocument !== true')
            expect(page.locator('.reading')).to_be_visible()
            for theme in ['dark','light']:
                check_theme(page,url,theme)
            new_icon=page.evaluate('async ()=>Array.from(new Uint8Array(await (await fetch("icon-192.png")).arrayBuffer()))')
            assert old_icon!=new_icon
            assert hashlib.sha256(bytes(new_icon)).digest()==hashlib.sha256((ROOT/'dist/icon-192.png').read_bytes()).digest()
            context.set_offline(True);page.reload();expect(page.locator('.reading')).to_be_visible()
            for theme in ['light','dark']:
                check_theme(page,url,theme)
                page.screenshot(path=str(args.output/f'upgrade-offline-{theme}.png'))
                result=page.evaluate('''async()=>Promise.all([...document.querySelectorAll('link[data-theme-icon]')].map(async i=>{const r=await fetch(i.href);return r.status}))''')
                assert result==[200,200,200]
            assert not errors,errors
            report={'status':'PASS','old_release':OLD,'old_icon_sha256':hashlib.sha256(bytes(old_icon)).hexdigest(),'new_icon_sha256':hashlib.sha256(bytes(new_icon)).hexdigest(),'browser':context.browser.version if context.browser else 'Chromium','origin':url,'checks':['Old public shell/manifest/icon cached','New SW offered explicit update','New document and icon bytes after acceptance','Both logos and favicons offline after reload'],'physical_os_install':'NOT TESTED','scope':'Old actual release and new production build on the same controlled localhost origin; not a physical phone or public HTTPS upgrade'}
            (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(report,ensure_ascii=False,indent=2));context.close()
    finally:server.shutdown()
