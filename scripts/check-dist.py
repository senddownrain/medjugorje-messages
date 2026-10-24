"""Validate the exact Pages artifact, including the frozen original JSON bytes."""
import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
dist = root/'dist'
base = '/medjugorje-messages/'
html = (dist/'index.html').read_text()
assert 'noindex' not in html.lower()
assert base+'assets/' in html
manifest = json.loads((dist/'manifest.webmanifest').read_text())
assert manifest['start_url'] == manifest['scope'] == base
for icon in manifest['icons']:
    path = dist/icon['src']
    assert path.is_file() and path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
release = json.loads((dist/'release.json').read_text())
runtime = json.loads((dist/'data/latest.json').read_text())
for language in ['ru','be','uk','hr','en','sk','lv']:
    source = (root/f'data/{language}.json').read_bytes()
    deployed = (dist/'data'/runtime['latest'][language]['archive']).read_bytes()
    assert source == deployed
    assert release['source_sha256'][language+'.json'] == hashlib.sha256(source).hexdigest()
assert release['source_sha256']['index.json'] == hashlib.sha256((root/'data/index.json').read_bytes()).hexdigest()
for path in dist.rglob('*'):
    if not path.is_file(): continue
    assert not any(part in {'.env','.git','reports','research-sources','.openai','node_modules'} for part in path.relative_to(dist).parts)
    assert path.suffix not in {'.zip','.mhtml','.mht','.map'}
    if path.suffix in {'.js','.html','.json'}:
        text = path.read_text()
        assert not re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text)
print('PASS: Pages base, manifest, PNG icons, eight source hashes, seven byte-identical deployed archives, artifact excludes source snapshots/reports/credentials')
