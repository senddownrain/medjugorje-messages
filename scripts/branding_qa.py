"""Brand checks shared by local production and public HTTPS release QA."""
import hashlib
from urllib.parse import urljoin
from playwright.sync_api import expect


def check_theme(page, base, theme):
    origin = page.evaluate('performance.timeOrigin')
    if page.locator('html').get_attribute('data-theme') != theme:
        page.locator('#theme-button').click()
    expect(page.locator('.brand-symbol')).to_have_attribute('src', '/medjugorje-messages/'+f'logo-{theme}-96.webp')
    page.wait_for_function('t => { const i=document.querySelector(".brand-symbol"); return i.complete && i.naturalWidth>0 && i.currentSrc.includes("logo-"+t+"-"); }', arg=theme)
    assert page.evaluate('performance.timeOrigin') == origin, 'Theme change must not reload the document'
    expected = ['favicon.ico','favicon-64.png','favicon-16.png'] if theme == 'light' else ['favicon-dark.ico','favicon-dark-64.png','favicon-dark-16.png']
    actual = page.locator('link[data-theme-icon]').evaluate_all('(nodes)=>nodes.map(n=>new URL(n.href).pathname)')
    assert actual == ['/medjugorje-messages/'+name for name in expected], actual


def check_branding_assets(page, base):
    names = ['favicon.ico','favicon-dark.ico','favicon-16.png','favicon-dark-16.png',
             'favicon-64.png','favicon-dark-64.png','apple-touch-icon.png',
             'icon-192.png','icon-512.png','icon-maskable-512.png']
    names += [f'logo-{t}-{n}.webp' for t in ['light','dark'] for n in [96,192]]
    hashes = {}
    for name in names:
        response = page.request.get(urljoin(base,name))
        assert response.status == 200, (name,response.status)
        hashes[name] = hashlib.sha256(response.body()).hexdigest()
    return hashes
