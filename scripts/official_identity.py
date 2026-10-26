"""Identify only unambiguous explicitly labelled official monthly records.

The literal Monthly label is source evidence. Day-of-month is never a type or
visionary rule. Annual/special/duplicate sections remain blocked pending adapters.
"""
from datetime import date
import json
from scripts.update_candidate_gate import sha256
from scripts.watch_official_updates import URL


def identify_records(observations):
    identities={}
    for observation in observations:
        stamp=observation['date']
        date.fromisoformat(stamp)
        # Source may have multiple same-day messages; never collapse these.
        if observation['sections'] != ['Monthly']:
            continue
        parsed=date.fromisoformat(stamp)
        if parsed>date.today():
            continue
        key=parsed.strftime('%y%m%d')+'m'
        evidence=sha256(json.dumps(observation,sort_keys=True,ensure_ascii=False).encode())
        if key in identities:
            raise ValueError('Duplicate official monthly identity')
        identities[key]=dict(date=stamp,type='monthly',visionary=None,status='identity_confirmed',
            source_id='archive-date:'+stamp+':monthly',evidence_url=URL,evidence_sha256=evidence,
            attribution_status='unattributed',identity_rule='unique_official_date_and_literal_Monthly_label')
    return identities


def associate(item,identities):
    matches=[key for key,r in identities.items() if r['date']==item['message_date']]
    if len(matches)!=1:
        raise ValueError('No unique typed official record for candidate date')
    return matches[0]


def parse_official_archive(raw,policy,observed_at,errors=None):
    from bs4 import BeautifulSoup
    from scripts.automatic_sources import parse_article,SourceBlocked,message_date_from_heading,error_metadata
    soup=BeautifulSoup(raw,'html.parser')
    language=(soup.html.get('lang','') if soup.html else '').split('-')[0]
    observed_language=language
    if language!=policy['language']:
        from urllib.parse import urlsplit
        override=policy.get('html_locale_override',{})
        if (override.get('observed')!=language or override.get('expected')!=policy['language']
            or not override.get('evidence') or urlsplit(policy['source_url']).path.split('/')[1]!=policy['language']):
            raise SourceBlocked('Official archive language mismatch')
        language=policy['language']
    results=[]
    found_typed=False
    if errors is None: errors=[]
    for heading in soup.select('h2'):
        title=heading.get_text(' ',strip=True)
        header=heading.parent
        if header.get_text(' ',strip=True).removeprefix(title).strip()!=policy['monthly_label']:
            continue
        found_typed=True
        try:
            stamp=message_date_from_heading(title,policy)
            if stamp<policy.get('not_before','2026-10-25'):
                continue
            card=header.parent
            if len(card.select('h2'))!=1:
                raise SourceBlocked('Ambiguous official message card')
            # Isolate the actual card to prevent cross-record date/body pairing.
            isolated=('<html lang="'+language+'"><body>'+str(card)+'</body></html>').encode()
            item=parse_article(isolated,{**policy,'date_selector':'h2'},
                               dict(url=policy['source_url'],guid='official-card:'+title,published=None))
            item['language_check'].update(html_language=observed_language,source_route_language=language)
            if observed_language!=language:item['language_check']['html_locale_override']=policy['html_locale_override']
            item['raw_sha256']=sha256(raw)
            item['source_id']='archive-date:'+item['message_date']+':monthly:'+language
            item['observed_at']=observed_at
            results.append(item)
        except (ValueError,KeyError,TypeError) as error:
            errors.append(dict(language=language,source_url=policy['source_url'],heading=title,
                               status='blocked',**error_metadata(error)))
    if not found_typed:
        raise SourceBlocked('No recognizable typed official message cards')
    return results


def cached_identities(baseline,observations,current):
    # Archive pagination/year rollover must not strand late translations of a
    # previously observed official record. Never use a cache to override a
    # currently visible ambiguous or changed official date section.
    from scripts.check_append_only_updates import load_archives
    archives,index=load_archives(baseline)
    rows={r['id']:r for r in index['messages']}
    visible={o['date'] for o in observations}
    restored={}
    for archive in archives.values():
        for message in archive['messages']:
            record=message.get('provenance',{}).get('official_record',{})
            key=message['id'];row=rows.get(key,{})
            if (key in current or row.get('date') in visible or record.get('date')!=row.get('date')
                or record.get('type')!=row.get('type') or record.get('type')!='monthly'
                or record.get('evidence_url')!=URL or record.get('status')!='identity_confirmed'
                or record.get('identity_rule')!='unique_official_date_and_literal_Monthly_label'
                or not record.get('evidence_sha256')):
                continue
            restored[key]=record
    return restored
