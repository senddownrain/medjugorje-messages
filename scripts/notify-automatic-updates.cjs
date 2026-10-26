// Trusted default-branch job only. One issue, body updates, no recurring comments.
module.exports = async ({github, context, audit, validation, publication}) => {
  const fs = require('node:fs');
  const report = JSON.parse(fs.readFileSync(audit, 'utf8'));
  const marker = '<!-- automatic-updates-health-v1 -->';
  const {owner, repo} = context.repo;
  const issues = await github.paginate(github.rest.issues.listForRepo, {owner, repo, state:'all', per_page:100});
  const issue = issues.find(i => !i.pull_request && (i.body || '').includes(marker));
  const failed = report.status !== 'validated' || validation !== 'success' || publication === 'failure';
  if (!failed) {
    if (issue?.state === 'open') await github.rest.issues.update({owner,repo,issue_number:issue.number,state:'closed'});
    return;
  }
  const safe = JSON.stringify({status:report.status, sources:report.sources, validation, publication},null,2)
    .replace(/[`<>@]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
  const body = ['Автоматическое обновление ограничено. Подробности — в Summary и audit.json последнего запуска.',
    '',report.run_url,'','```json',safe,'```',marker].join('\n');
  if (issue) await github.rest.issues.update({owner,repo,issue_number:issue.number,body,state:'open'});
  else await github.rest.issues.create({owner,repo,title:'Автообновления: состояние источников и выпуска',body});
};
