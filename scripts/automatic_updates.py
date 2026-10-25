"""Independent candidate isolation and transactional staging; never writes live data/.

A publishable association requires explicit official record evidence, never the
calendar, a title heuristic, or a date watcher alone. Logs contain metadata only.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from scripts.check_append_only_updates import LANGUAGES, gate, load_archives
from scripts.update_candidate_gate import sha256, iso_date, https_origin, iso_instant, HEX256
from scripts.automatic_sources import authorized, discover, get_page, parse_article, new_session, error_metadata
from scripts.watch_official_updates import fetch_archive, extract_observations
from scripts.official_identity import identify_records, associate


def validate_candidate(c, official, policy):
    lang, key = c['language'], c['canonical_id']
    if lang not in LANGUAGES or not authorized(policy) or policy['language'] != lang:
        raise ValueError('Source not authorized for automatic publication')
    if https_origin(c['source_url']) != https_origin(policy['origin']):
        raise ValueError('Source origin mismatch')
    iso_date(c['message_date'], 'message_date')
    iso_instant(c['published_at'], 'published_at')
    if c['message_date'] > datetime.now(timezone.utc).date().isoformat():
        raise ValueError('Future date')
    text = c['text']
    if not isinstance(text, str) or not 100 <= len(text) <= 15000:
        raise ValueError('Incomplete full text')
    if sha256(text.encode()) != c['text_sha256'] or not c.get('source_id'):
        raise ValueError('Invalid source identity or text hash')
    if c.get('verified') is not False or c.get('technical_status') != 'validated' or c.get('editorial_status') != 'source_import_unreviewed':
        raise ValueError('Invalid integrity/editorial separation')
    record = official.get(key)
    # An official date alone cannot prove type, person or identity. Mapping must
    # include a reviewed stable identity and source-specific evidence references.
    if not record or record.get('status') != 'identity_confirmed' or not record.get('evidence_url') or not record.get('evidence_sha256'):
        raise ValueError('Official record identity not confirmed')
    if record['date'] != c['message_date']:
        raise ValueError('Official message date mismatch')
    if record.get('type') not in ('monthly', 'weekly', 'annual', 'special'):
        raise ValueError('Unconfirmed message type')
    https_origin(record['evidence_url'])
    if not HEX256.fullmatch(c.get('raw_sha256', '')) or not HEX256.fullmatch(record.get('evidence_sha256', '')):
        raise ValueError('Missing original-byte fingerprint')
    return record


def stage(baseline, destination, candidates, official, policies):
    """Commit the complete candidate directory only after append-only validation.

    Invalid candidates roll back independently. Failure in the final gate leaves
    baseline and previous successful destination untouched.
    """
    archives, index = load_archives(baseline)
    events = []
    seen = set()
    for c in candidates:
        lang, key = c.get('language'), c.get('canonical_id')
        event = dict(language=lang, id=key, source_url=c.get('source_url'))
        previous = deepcopy((archives, index))
        try:
            record = validate_candidate(c, official, policies.get(lang, {}))
            identity = (lang, key)
            if identity in seen:
                raise ValueError('Duplicate candidate identity')
            seen.add(identity)
            old = next((r for r in archives[lang]['messages'] if r['id'] == key), None)
            if old:
                if old['text_sha256'] != c['text_sha256']:
                    raise ValueError('Source correction: existing translation is immutable')
                event.update(status='skipped', reason='already_present')
                events.append(event)
                continue
            for r in archives[lang]['messages']:
                if r['text_sha256'] == c['text_sha256'] or r.get('source_url') == c['source_url'] or r.get('source_id') == c['source_id']:
                    raise ValueError('Duplicate text or source identity')
            row = next((r for r in index['messages'] if r['id'] == key), None)
            if row and (row['date'] != record['date'] or row['type'] != record['type'] or (record.get('visionary') is not None and row.get('visionary') != record.get('visionary'))):
                raise ValueError('Canonical attribution conflict')
            if not row:
                row = dict(id=key, date=record['date'], type=record['type'], visionary=record.get('visionary'),
                           translations={l:dict(present=False, has_text=False) for l in LANGUAGES})
                index['messages'].append(row)
            provenance = {k:c[k] for k in ('source_url','source_id','published_at','raw_sha256','text_sha256','editorial_status','technical_status','language_check')}
            provenance.update(imported_at=datetime.now(timezone.utc).isoformat(), official_evidence=record['evidence_url'],
                              official_sha256=record['evidence_sha256'], policy_sha256=sha256(json.dumps(policies[lang], sort_keys=True).encode()))
            message = dict(id=key, date=row['date'], type=row['type'], visionary=row.get('visionary'), language=lang,
                           title=c.get('title',''), text=c['text'], text_sha256=c['text_sha256'], segments=[dict(kind='message', text=c['text'])],
                           status='contains_message', source_url=c['source_url'], source_id=c['source_id'], verified=False,
                           provenance=provenance)
            if c.get('context_text'):
                message['segments'].append(dict(kind='context',text=c['context_text']))
            archives[lang]['messages'].append(message)
            row['translations'][lang] = {k:message[k] for k in ('title','status','source_url','source_id','text_sha256')}
            row['translations'][lang].update(present=True, has_text=True)
            event.update(status='added', reason='validated_unreviewed')
        except (ValueError, KeyError, TypeError) as error:
            archives, index = previous
            event.update(status='blocked', reason=str(error))
        events.append(event)
    index['unique_records'] = len(index['messages'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError('Staging destination already exists; use a fresh run directory')
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        folder = Path(temp)/'candidate'; folder.mkdir()
        for lang in LANGUAGES:
            old_path = baseline/(lang+'.json')
            # Do not reformat an unchanged archive.
            value = archives[lang]
            if value == json.loads(old_path.read_text()):
                shutil.copyfile(old_path, folder/old_path.name)
            else:
                (folder/old_path.name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
        old_index = baseline/'index.json'
        if index == json.loads(old_index.read_text()):
            shutil.copyfile(old_index, folder/'index.json')
        else:
            (folder/'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n')
        result = gate(baseline, folder)
        folder.rename(destination)
    return dict(gate=result, events=events, added=sum(e['status']=='added' for e in events))


def run(output, policy_path, baseline, live=True):
    output.mkdir(parents=True, exist_ok=True)
    policies = json.loads(policy_path.read_text())['languages']
    report = dict(started_at=datetime.now(timezone.utc).isoformat(), status='dry_run', sources={}, candidates=[],
                  run_url=os.environ.get('GITHUB_SERVER_URL','https://github.com')+'/'+os.environ.get('GITHUB_REPOSITORY','senddownrain/medjugorje-messages')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','local'),
                  base_commit=os.environ.get('GITHUB_SHA'), publication='disabled')
    # Never put official full sections or RSS summaries/titles into audit artifacts.
    identities = {}
    if live:
        try:
            official_html = fetch_archive()
            observations = extract_observations(official_html)
            identities = identify_records(observations)
            report['official'] = dict(status='accessible', identity_count=len(identities), raw_sha256=sha256(official_html.encode()), observations=[dict(date=o['date'], section_sha256=[sha256(s.encode()) for s in o['sections']]) for o in observations])
        except Exception as error:
            report['official'] = dict(status='error', **error_metadata(error))
    candidates = []
    session = new_session()
    for lang, policy in policies.items():
        entry = dict(status='blocked', reason=policy['blocker'], automatic_publication=authorized(policy))
        report['sources'][lang] = entry
        if not live or not policy.get('origin'):
            continue
        try:
            posts = discover(session, policy)
            entry['discovery_status'] = 'accessible'
            entry['detected'] = len(posts)
            for post in posts:
                summary = dict(language=lang, source_id=post.get('guid') or post['url'], source_url=post['url'], published_at=post['published'])
                if authorized(policy):
                    try:
                        raw = get_page(session, post['url'], policy['origin'])
                        item = parse_article(raw, policy, post)
                        summary['message_date']=item['message_date']
                        if item['message_date'] < policy.get('not_before','2026-10-25'):
                            summary.update(status='skipped',reason='before_automation_start')
                            report['candidates'].append(summary)
                            continue
                        item['canonical_id'] = associate(item, identities)
                        candidates.append(item)
                        summary['status'] = 'fetched'
                    except Exception as error:
                        summary.update(status='blocked', **error_metadata(error))
                else:
                    summary.update(status='blocked', reason=policy['blocker'])
                report['candidates'].append(summary)
        except Exception as error:
            entry.update(discovery_status='error', **error_metadata(error))
    staged = stage(baseline, output/'candidate', candidates, identities, policies)
    report.update(staged)
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    report['status'] = 'blocked' if any(s.get('discovery_status')=='error' or not s['automatic_publication'] for s in report['sources'].values()) else 'validated'
    (output/'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    lines = ['## Автоматическое обновление — '+report['status'], '',
             'Публикация: '+report['publication']+'. Добавлено переводов: '+str(report['added']), '',
             '| Язык | Обнаружение | Ограничение |', '|---|---|---|']
    lines += ['| '+l+' | '+s.get('discovery_status','not_configured')+' | '+s['reason']+' |' for l,s in report['sources'].items()]
    lines += ['', 'Кандидатов: '+str(len(report['candidates'])), '[Workflow]('+report['run_url']+')', '',
              'Полные тексты отсутствуют в журнале. HTTP/парсинг/проверки: см. audit.json.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f: f.write('\n'.join(lines)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('work/automatic-updates'))
    p.add_argument('--policies',type=Path,default=Path('research/automatic-source-policies.json'))
    p.add_argument('--baseline',type=Path,default=Path('data'))
    p.add_argument('--offline',action='store_true')
    a=p.parse_args(); run(a.output,a.policies,a.baseline,not a.offline)

if __name__=='__main__': main()
