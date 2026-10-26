"""Reconstruct the frozen audit view without weakening tests of live updates.

Every reconstructed file must match the original Stage A whole-file SHA. Current
archives are never edited; late translations are absent from this historical view.
"""
import hashlib
import json
from pathlib import Path
from scripts.check_append_only_updates import LANGUAGES


def write_historical_baseline(data, output, root=None):
    root=root or Path(__file__).resolve().parents[1]
    seal=json.loads((root/'research/update-integrity-baseline.json').read_text())
    hashes=json.loads((root/'reports/stage-a/summary.json').read_text())['file_sha256']
    output.mkdir(parents=True,exist_ok=True)
    for lang in (*LANGUAGES,'index'):
        document=json.loads((data/(lang+'.json')).read_text())
        by_id={r['id']:r for r in document['messages']}
        if lang=='index':
            document['messages']=[by_id[key] for key in seal['index']]
            document['unique_records']=len(document['messages'])
            for row in document['messages']:
                for language in LANGUAGES:
                    if language not in seal['index'][row['id']]['translations']:
                        row['translations'][language]={'present':False,'has_text':False}
        else:
            document['messages']=[by_id[key] for key in seal['languages'][lang]['rows']]
        raw=(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode()
        if hashlib.sha256(raw).hexdigest()!=hashes[lang+'.json']:
            raise ValueError('Historical snapshot mutated: '+lang)
        (output/(lang+'.json')).write_bytes(raw)
    return output
