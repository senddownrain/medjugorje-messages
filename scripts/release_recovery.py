"""Recover a committed but unpublished database without creating duplicate commits."""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

LANGUAGES=('ru','be','uk','hr','en','sk','lv','index')
PUBLIC_RELEASE='https://senddownrain.github.io/medjugorje-messages/release.json'


def data_hashes(data):
    return {lang+'.json':hashlib.sha256((data/(lang+'.json')).read_bytes()).hexdigest() for lang in LANGUAGES}


def publication_needed(data,public_release):
    return public_release.get('source_sha256')!=data_hashes(data)


if __name__=='__main__':
    try:
        with urlopen(Request(PUBLIC_RELEASE,headers={'Cache-Control':'no-cache'}),timeout=20) as response:
            raw=response.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('Oversize public release metadata')
        needed=publication_needed(Path('data'),json.loads(raw))
    except Exception:
        # Public release unavailable: build/deploy the already tested commit,
        # then let the public verification job report an actual serving failure.
        needed=True
    print('Publication required: '+str(needed).lower())
    with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('publish_needed='+str(needed).lower()+'\n')
