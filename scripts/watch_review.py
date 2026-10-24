"""Compare source observations without editing data/*.json or approving candidates."""
import argparse
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def canonical_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Expected a source HTTPS URL')
    # Feed permalinks, not arbitrary query strings, are the documented fallback identity.
    query = urlencode(sorted((k,v) for k,v in parse_qsl(parsed.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')))
    return urlunsplit(('https', parsed.netloc.lower(), parsed.path.rstrip('/') + '/', query, ''))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def observation(source, language, source_id, fields, date=None):
    origin = urlsplit(canonical_url(source)).netloc
    identity = {'origin':origin, 'language':language, 'source_id':source_id}
    return {'key':digest(identity), 'identity':identity, 'source':source, 'message_date':date,
            'fields':fields, 'fingerprint':digest(fields), 'visionary':None, 'type':None,
            'editorial_status':'unconfirmed', 'available_languages':[language]}


def from_report(kind, report):
    if kind == 'official':
        return [observation(report['source'], 'en', 'archive-date:' + item['date'],
            {'date':item['date'], 'source_sections':item['sections']}, item['date'])
            for item in report.get('observations', [])]
    return [{**observation(item['url'], item['language'], item.get('guid') or canonical_url(item['url']),
        {k:item.get(k) for k in ['title', 'url', 'published', 'categories', 'summary']}),
        'notify_new':item.get('notify_new', True)} for item in report.get('candidates', [])]


def compare_observations(kind, report, previous, local, bootstrap_sources=None):
    """First official read is a baseline except genuinely newer publication dates.

    Stable provenance identifies an observation. A changed fingerprint of the same
    observation is a correction candidate, never a second new message.
    Missing feed-window entries do not mean deletion. Failed sources retain state.
    """
    state = deepcopy(previous)
    events = []
    bootstrap_sources = set(bootstrap_sources or ())
    for item in from_report(kind, report):
        key = item['key']
        before = state.get(key)
        state[key] = item
        if before and before['fingerprint'] == item['fingerprint']:
            continue
        if not before and kind == 'official' and item['message_date'] not in report.get('new_dates', []):
            continue
        if not before and kind == 'community' and (
            not item['notify_new'] or
            (item['identity']['origin'], item['identity']['language']) in bootstrap_sources
        ):
            continue
        matches = []
        for language, archive in local.items():
            for row in archive.get('messages', []):
                if row.get('source_url') and canonical_url(row['source_url']) == canonical_url(item['source']):
                    matches.append({'id':row['id'], 'language':language, 'source_id':row.get('source_id'),
                        'text_sha256':row.get('text_sha256'), 'verified':archive.get('verified', False)})
        event = {**item, 'kind':'source_correction' if before else ('existing_source_review' if matches else 'new_publication_candidate'),
                 'checked_at_utc':report['checked_at_utc'], 'local_provenance_matches':matches,
                 'previous_fingerprint':before['fingerprint'] if before else None,
                 'message_text_compared':False,
                 'uncertainties':['Визионер и тип не подтверждены.',
                    'RSS publication date не является датой послания.' if kind == 'community' else
                    'Раздел архива с датой может содержать несколько сообщений; атрибуция не выводится из даты.',
                    'Текст исходных JSON не сравнивался: источник имеет другое происхождение или даёт только метаданные.'],
                 'diff':'\n'.join(difflib.unified_diff(
                     json.dumps(before['fields'] if before else {}, ensure_ascii=False, indent=2, sort_keys=True).splitlines(),
                     json.dumps(item['fields'], ensure_ascii=False, indent=2, sort_keys=True).splitlines(),
                     fromfile='previous-source-observation' if before else 'no-previous-observation',
                     tofile='current-source-observation', lineterm=''))}
        events.append(event)
    return state, events


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--kind', choices=['official', 'community'], required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    report = json.loads(args.report.read_text())
    state_existed = args.state.exists()
    previous = json.loads(args.state.read_text()) if state_existed else {}
    local = {path.stem:json.loads(path.read_text()) for path in Path('data').glob('*.json') if path.stem != 'index'}
    # Each newly observed RSS source gets one quiet baseline. This includes
    # lost caches and sources that recover after an earlier partial failure.
    known_sources = {(v['identity']['origin'], v['identity']['language'])
                     for v in previous.values() if isinstance(v, dict) and 'identity' in v}
    # Also remember healthy feeds with zero matching RSS entries, so their
    # first genuinely new candidate is not silently lost on the next run.
    known_sources.update((entry.split('@', 1)[1], entry.split('@', 1)[0])
                         for entry in previous.get('__observed_sources__', []))
    observed_sources = {(v['identity']['origin'], v['identity']['language'])
                        for v in from_report(args.kind, report)}
    bootstrap_sources = observed_sources - known_sources if args.kind == 'community' else set()
    state, events = compare_observations(args.kind, report, previous, local,
                                         bootstrap_sources=bootstrap_sources)
    if args.kind == 'community':
        from scripts.probe_community_feeds import SITES
        seen = set(previous.get('__observed_sources__', []))
        for language, origin in SITES.items():
            if report.get('sites', {}).get(language, {}).get('state') == 'accessible':
                seen.add(language + '@' + urlsplit(origin).netloc.lower())
        state['__observed_sources__'] = sorted(seen)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n')
    args.output.write_text(json.dumps({'source_status':report['status'], 'checked_at_utc':report['checked_at_utc'],
        'events':events, 'state_entries':sum(k != '__observed_sources__' for k in state),
        'baseline_initialized':not state_existed,
        'bootstrapped_sources':sorted(lang + '@' + origin for origin, lang in bootstrap_sources),
        'bootstrap_notifications_suppressed':bool(bootstrap_sources)}, ensure_ascii=False, indent=2)+'\n')
    print(f'{len(events)} editorial review events; source status {report["status"]}; originals unchanged')


if __name__ == '__main__':
    main()
