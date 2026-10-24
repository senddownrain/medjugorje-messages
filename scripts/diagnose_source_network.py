"""Read-only, bounded source diagnostics. No bypasses, imports or notifications."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
import requests

TARGETS = [
    ('primary', 'https://www.medjugorje.hr/en/our-lady-messages-archive'),
    ('supplementary', 'https://www.medjugorje.ws/en/messages/'),
]
USER_AGENT = 'MedjugorjeMessagesWatch/0.1 (https://github.com/senddownrain/medjugorje-messages)'


def safe_proxy(value):
    if not value:
        return None
    p = urlsplit(value)
    return {'scheme':p.scheme, 'host':p.hostname, 'port':p.port, 'credentials_redacted':bool(p.username or p.password)}


def route_for(url):
    proxies = requests.utils.get_environ_proxies(url)
    proxy = proxies.get('https') or proxies.get('all')
    return {'route':'HTTPS via configured proxy CONNECT' if proxy else 'runner HTTPS egress (no environment proxy)',
            'proxy':safe_proxy(proxy), 'tls_verification':True}


def classify_error(error):
    # Do not serialize exception strings: they may embed proxy credentials.
    if isinstance(error, requests.exceptions.ProxyError):
        match = re.search(r'Tunnel connection failed:\s*(\d{3})', str(error))
        return {'layer':'proxy_connect', 'connect_status':int(match[1]) if match else None,
                'http_status':None, 'error_type':type(error).__name__, 'origin_reached':False}
    if isinstance(error, requests.exceptions.SSLError):
        layer = 'tls'
    elif isinstance(error, requests.exceptions.Timeout):
        layer = 'timeout'
    else:
        layer = 'transport'
    return {'layer':layer, 'http_status':None, 'error_type':type(error).__name__, 'origin_reached':None}


def probe(session, url, method):
    attempt = {'url':url, 'method':method, 'checked_at_utc':datetime.now(timezone.utc).isoformat(), 'route':route_for(url)}
    try:
        with session.request(method, url, timeout=(10,25), allow_redirects=False, stream=True) as response:
            attempt.update({'http_status':response.status_code, 'layer':'http_response', 'origin_reached':True,
                'response_headers':{k.lower():v for k,v in response.headers.items()
                    if k.lower() in ['server','via','cf-ray','location','content-type','x-cache']}})
            body = b''
            if method == 'GET' and response.status_code == 200:
                chunks = []
                for chunk in response.iter_content(65536):
                    chunks.append(chunk)
                    if sum(map(len,chunks)) > 4*1024*1024:
                        raise ValueError('Diagnostic body limit exceeded')
                body = b''.join(chunks)
                attempt.update({'body_bytes':len(body), 'body_sha256':hashlib.sha256(body).hexdigest()})
            return attempt, body
    except requests.RequestException as error:
        return {**attempt, **classify_error(error)}, b''
    except ValueError:
        return {**attempt, 'layer':'validation', 'http_status':None, 'error_type':'BodyLimit'}, b''


def inspect(role, url, session):
    parts = urlsplit(url)
    robots_url = f'{parts.scheme}://{parts.netloc}/robots.txt'
    robots, policy = probe(session, robots_url, 'GET')
    head, _ = probe(session, url, 'HEAD')
    result = {'role':role, 'source_url':url, 'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'state':'ERROR', 'attempts':[robots,head], 'message_content_imported':False}
    if robots['http_status'] not in (200,404):
        result['reason'] = 'robots_unavailable; content GET skipped; HEAD is metadata-only'
        return result
    rules = RobotFileParser()
    rules.parse(policy.decode('utf-8', errors='replace').splitlines() if robots['http_status']==200 else [])
    if not rules.can_fetch(USER_AGENT, url):
        result['reason'] = 'robots_disallow; content GET skipped'
        return result
    current = url
    for _ in range(3):
        response, body = probe(session, current, 'GET')
        result['attempts'].append(response)
        status = response.get('http_status')
        if status in (301,302,307,308):
            target = urljoin(current, response.get('response_headers',{}).get('location',''))
            # Only the same source's ordinary trailing-slash canonicalization is allowed.
            if target not in (url, url.rstrip('/')+'/') or target == current:
                result['reason'] = 'redirect_requires_source_review'
                return result
            current = target
            continue
        if status != 200:
            result['reason'] = 'source_request_failed'
            return result
        if 'html' not in response.get('response_headers',{}).get('content-type','').lower():
            result['reason'] = 'unexpected_content_type'
            return result
        if role == 'primary':
            from scripts.watch_official_updates import extract_dates
            try:
                dates = extract_dates(body)
            except ValueError:
                result['reason'] = 'unrecognized_archive_structure'
                return result
            result['observed_dates'] = dates[:3]
        result.update({'state':'OK', 'reason':'source_access_confirmed; this is not a no-new-messages decision', 'final_url':current})
        return result
    result['reason'] = 'redirect_limit'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('research-output/source-network.json'))
    args = parser.parse_args()
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    report = {'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'environment':'github-hosted-actions' if os.environ.get('GITHUB_ACTIONS')=='true' else 'codex',
        'github_run_url':('https://github.com/'+os.environ.get('GITHUB_REPOSITORY','')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','')) if os.environ.get('GITHUB_RUN_ID') else None,
        'sources':[inspect(role,url,session) for role,url in TARGETS],
        'no_updates_claimed':False, 'automatic_import':False,
        'fallback':'ERROR: editor may manually confirm source/date/ID and attach an authorized saved HTML/MHT; unverified text is never auto-imported.'}
    report['state']='OK' if all(r['state']=='OK' for r in report['sources']) else 'ERROR'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['state']=='OK' else 2


if __name__=='__main__':
    raise SystemExit(main())
