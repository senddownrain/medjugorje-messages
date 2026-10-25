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
