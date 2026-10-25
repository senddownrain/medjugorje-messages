"""Fail-closed full-text adapters. No access-control workarounds or translation.

Selectors and literal boundary markers must be approved against real source pages
before a policy can enable an adapter. RSS is discovery only.
"""
from datetime import date
from functools import lru_cache
import re
from urllib.parse import urlsplit, parse_qs
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


@lru_cache(maxsize=1)
def language_model():
    from langid.langid import LanguageIdentifier, model
    return LanguageIdentifier.from_modelstring(model,norm_probs=True)


def check_language(text,expected):
    language,confidence=language_model().classify(text)
    if language!=expected or confidence<0.90:
        error=SourceBlocked('Text language mismatch or low confidence')
        error.language_check=dict(expected=expected,detected=language,confidence=float(confidence))
        raise error
    return dict(language=language,confidence=float(confidence),model='langid-1.1.6')


def message_date_from_heading(heading,policy):
    matches = list(re.finditer(policy['date_pattern'], heading, flags=re.I))
    if len(matches) != 1:
        raise SourceBlocked('Missing or ambiguous explicit message date')
    parts = matches[0].groupdict()
    month=parts['month']
    if policy.get('month_names'):
        month=policy['month_names'].index(month.casefold())+1
    stamp = date(int(parts['year']), int(month), int(parts['day'])).isoformat()
    if stamp > date.today().isoformat():
        raise SourceBlocked('Future message date')
    return stamp


def parse_article(raw, policy, post):
    """Preserve quote punctuation; reject ambiguous bodies/dates and excerpt markers."""
    soup = BeautifulSoup(raw, 'html.parser')
    for node in soup.select('script,style,noscript'):
        node.decompose()
    lang = (soup.html.get('lang', '') if soup.html else '').lower().split('-')[0]
    if lang != policy['language']:
        raise SourceBlocked('HTML language mismatch')
    selector=policy['body_selector']
    if '{wordpress_id}' in selector:
        guid=post.get('guid','')
        if https_origin(guid)!=https_origin(policy['origin']):
            raise SourceBlocked('Unapproved WordPress identity origin')
        values=parse_qs(urlsplit(guid).query).get('p',[])
        if len(values)!=1 or not re.fullmatch(r'[1-9][0-9]*',values[0]):
            raise SourceBlocked('Missing stable WordPress post ID')
        selector=selector.replace('{wordpress_id}',values[0])
    bodies, dates = soup.select(selector), soup.select(policy['date_selector'])
    if len(bodies) != 1 or len(dates) != 1:
        raise SourceBlocked('Ambiguous full text or message date')
    heading = dates[0].get_text(' ', strip=True)
    stamp=message_date_from_heading(heading,policy)
    text = bodies[0].get_text('\n', strip=True)
    context=''
    if policy.get('context_suffix'):
        suffix=policy['context_suffix']
        if not text.endswith(suffix):
            raise SourceBlocked('Unrecognized source editorial suffix')
        text,context=text[:-len(suffix)].rstrip(),suffix
    if not text.startswith(policy['opening']) or not text.endswith(policy['closing']):
        raise SourceBlocked('Full quote boundaries missing')
    if len(text) < 100 or len(text) > 15000 or re.search(r'\[\s*…\s*\]|read more|читать далее|čítaj viac', text, re.I):
        raise SourceBlocked('Incomplete or implausible full text')
    language_check=check_language(text,policy['language'])
    iso_instant(post['published'], 'published_at', nullable=policy.get('allow_unknown_publication') is True)
    uncertainty='publication_time_not_exposed_by_source' if post['published'] is None else None
    return dict(language=policy['language'], message_date=stamp, published_at=post['published'], publication_uncertainty=uncertainty,
                source_id=post.get('guid') or post['url'], source_url=post['url'], text=text, language_check=language_check,
                text_sha256=sha256(text.encode()), raw_sha256=sha256(raw),
                title=heading, context_text=context, editorial_status='source_import_unreviewed', verified=False,
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
    if isinstance(error, PermissionError):
        match=re.search(r'HTTP (\d{3})',str(error))
        if match:return dict(error_type='PermissionError',layer='origin_http',http_status=int(match[1]))
    if isinstance(error, SourceBlocked):
        match = re.search(r'HTTP (\d{3})', str(error))
        return dict(error_type='SourceBlocked', layer='origin_http' if match else 'validation',
                    **({'language_check':error.language_check} if hasattr(error,'language_check') else {}),
                    **({'http_status':int(match[1])} if match else {'code':str(error)}))
    return dict(error_type=type(error).__name__, layer='network_or_parser')
