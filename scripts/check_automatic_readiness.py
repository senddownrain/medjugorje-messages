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
    checks=json.loads(Path('reports/updates/readiness.json').read_text())
    passed = ready(checks,
                   json.loads(Path('research/automatic-source-policies.json').read_text()))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f: f.write('ready='+str(passed).lower()+'\n')
    print('Production readiness: '+('PASS' if passed else 'BLOCKED'))

    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
            f.write('\n## Готовность production: '+('PASS' if passed else 'ВЫКЛЮЧЕН / BLOCKED')+'\n\n')
            for key in ('production_enabled','live_end_to_end_passed','official_identity_adapter_validated','android_installed_pwa_tested'):
                f.write('- '+key+': '+str(checks.get(key) is True)+'\n')
