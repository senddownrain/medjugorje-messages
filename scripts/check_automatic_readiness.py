"""Production interlock, independent of workflow_dispatch and repository variables."""
import json
from pathlib import Path
from scripts.automatic_sources import authorized


def ready(readiness, policies):
    return all(readiness.get(k) is True for k in ('production_enabled','live_end_to_end_passed',
               'official_identity_adapter_validated','android_installed_pwa_tested')) and any(
               authorized(p) for p in policies['languages'].values())


if __name__ == '__main__':
    import os
    passed = ready(json.loads(Path('reports/updates/readiness.json').read_text()),
                   json.loads(Path('research/automatic-source-policies.json').read_text()))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f: f.write('ready='+str(passed).lower()+'\n')
    print('Production readiness: '+('PASS' if passed else 'BLOCKED'))
