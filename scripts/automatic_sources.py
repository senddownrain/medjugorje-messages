"""Fail-closed full-text adapters. No access-control workarounds or translation.

Selectors and literal boundary markers must be approved against real source pages
before a policy can enable an adapter. RSS is discovery only.
"""
from datetime import date
import re
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from scripts.update_candidate_gate import https_origin, iso_instant, sha256
from scripts.watch_community_messages import load_feed, is_message_candidate
from scripts.probe_community_feeds import USER_AGENT


class SourceBlocked(ValueError):
    pass


def get_page(session, url, origin):
    if https_origin(url) != https_origin(origin):
        raise SourceBlocked('Unapproved article origin')
    robots = session.get(origin.rstrip('/') + '/robots.txt', timeout=15, allow_redirects=False)
    if robots.status_code not in (200, 404):
        raise SourceBlocked('robots HTTP ' + str(robots.status_code))
    rules = RobotFileParser()
    rules.parse(robots.text.splitlines() if robots.status_code == 200 else [])
    if not rules.can_fetch(USER_AGENT, url):
        raise SourceBlocked('robots forbids article')
    response = session.get(url, timeout=25, allow_redirects=False)
    if response.status_code != 200:
        raise SourceBlocked('article HTTP ' + str(response.status_code))
    if 'html' not in response.headers.get('content-type', '').lower():
        raise SourceBlocked('Expected full HTML article')
    if len(response.content) > 2_000_000:
        raise SourceBlocked('Article exceeds size bound')
    return response.content


def authorized(policy):
    required = ('access_evidence', 'publication_permission', 'fixture_evidence')
    return policy.get('enabled') is True and all(policy.get(k) for k in required) and all(
        policy.get(k) for k in ('body_selector', 'date_selector', 'date_pattern', 'opening', 'closing'))


def parse_article(raw, policy, post):
    """Preserve quote punctuation; reject ambiguous bodies/dates and excerpt markers."""
    soup = BeautifulSoup(raw, 'html.parser')
    for node in soup.select('script,style,noscript'):
        node.decompose()
    lang = (soup.html.get('lang', '') if soup.html else '').lower().split('-')[0]
    if lang != policy['language']:
        raise SourceBlocked('HTML language mismatch')
    bodies, dates = soup.select(policy['body_selector']), soup.select(policy['date_selector'])
    if len(bodies) != 1 or len(dates) != 1:
        raise SourceBlocked('Ambiguous full text or message date')
    heading = dates[0].get_text(' ', strip=True)
    matches = list(re.finditer(policy['date_pattern'], heading))
    if len(matches) != 1:
        raise SourceBlocked('Missing or ambiguous explicit message date')
    parts = matches[0].groupdict()
    # Source-specific numeric regex must supply named year/month/day. No date inferred from pubDate.
    stamp = date(int(parts['year']), int(parts['month']), int(parts['day'])).isoformat()
    if stamp > date.today().isoformat():
        raise SourceBlocked('Future message date')
    text = bodies[0].get_text('\n', strip=True)
    if not text.startswith(policy['opening']) or not text.endswith(policy['closing']):
        raise SourceBlocked('Full quote boundaries missing')
    if len(text) < 100 or len(text) > 15000 or re.search(r'\[\s*…\s*\]|read more|читать далее|čítaj viac', text, re.I):
        raise SourceBlocked('Incomplete or implausible full text')
    iso_instant(post['published'], 'published_at')
    return dict(language=policy['language'], message_date=stamp, published_at=post['published'],
                source_id=post.get('guid') or post['url'], source_url=post['url'], text=text,
                text_sha256=sha256(text.encode()), raw_sha256=sha256(raw),
                editorial_status='source_import_unreviewed', verified=False,
                technical_status='validated', attribution_status='unconfirmed')


def discover(session, policy):
    posts = load_feed(session, policy['origin'])
    return [p for p in posts if is_message_candidate(policy['language'], p, policy['origin'])]


def new_session():
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    return session


def error_metadata(error):
    # Requests exception strings can contain credentials from proxy URLs.
    # Persist only bounded status codes and our own constant parser messages.
    if isinstance(error, requests.exceptions.ProxyError):
        return dict(error_type='ProxyError', layer='proxy_connect', code='CONNECT_BLOCKED')
    response = getattr(error, 'response', None)
    if response is not None:
        return dict(error_type=type(error).__name__, layer='origin_http', http_status=response.status_code)
    if isinstance(error, SourceBlocked):
        match = re.search(r'HTTP (\d{3})', str(error))
        return dict(error_type='SourceBlocked', layer='origin_http' if match else 'validation',
                    **({'http_status':int(match[1])} if match else {'code':str(error)}))
    return dict(error_type=type(error).__name__, layer='network_or_parser')
