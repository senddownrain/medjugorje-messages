"""PR15 QA entrypoint adapted to PR19; loopback only, no deployment."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, default=Path('/tmp/current-preview-qa'))
p.add_argument('--port', type=int, default=5176)
args = p.parse_args()
html = (root / 'dist/index.html').read_text()
assert 'noindex,nofollow,noarchive' in html
assert '<script type="module" crossorigin src="/assets/' in html, 'Requires build:private at domain root'
assert 'Disallow: /' in (root / 'dist/robots.txt').read_text()
# Full C regression already exercises independent languages, themes, text identity,
# missing translations, four filters, navigation/scroll, Worker races/errors/retry.
subprocess.run([sys.executable, str(root / 'scripts/check-reader-browser.py'),
    '--base', '/', '--port', str(args.port), '--output', str(args.output)], cwd=root, check=True)
report = json.loads((args.output / 'browser.json').read_text())
report['privacy'] = {'robots':'PASS', 'root_build':'PASS',
    'hosted_anonymous_html_json_sw':'NOT TESTED — requires authorized deployment',
    'deployment':'NOT RUN', 'physical_android':'NOT TESTED'}
(args.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print('PASS: current PR19 reader, root build, noindex. Hosted access/device NOT TESTED.')
