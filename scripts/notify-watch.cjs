// Invoked only by the trusted schedule/dispatch job, with issues:write.
module.exports = async function notify({github, context, core, path}) {
  const report = JSON.parse(require('fs').readFileSync(path, 'utf8'));
  if (!Array.isArray(report.events)) throw new Error('Invalid review report');
  if (!report.events.length) { core.info('No review events; no issues or comments created.'); return; }
  const {owner, repo} = context.repo;
  const issues = await github.paginate(github.rest.issues.listForRepo, {owner, repo, state:'all', per_page:100});
  // External fields are inert JSON. Escape markdown fences, mentions and HTML;
  // never interpolate external source data in shell, JS source or workflow expressions.
  const inert = value => JSON.stringify(value, null, 2).replace(/[`<>@]/g,
    c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
  for (const event of report.events) {
    if (!/^[a-f0-9]{64}$/.test(event.key) || !/^[a-f0-9]{64}$/.test(event.fingerprint)) throw new Error('Invalid event identity');
    const marker = '<!-- source-review:' + event.key + ' -->';
    const revision = '<!-- observation:' + event.fingerprint + ' -->';
    const issue = issues.find(i => !i.pull_request && (i.body || '').includes(marker));
    let previousBody = issue?.body || '';
    if (issue) {
      const comments = await github.paginate(github.rest.issues.listComments, {owner, repo, issue_number:issue.number, per_page:100});
      previousBody += comments.map(c => c.body || '').join('\n');
      if (previousBody.includes(revision)) continue;
    }
    const payload = inert(event);
    const body = [
      '**Редакционная проверка. Ничего не утверждено и не импортировано.**', '',
      'Дата послания: ' + (event.message_date || 'не подтверждена; см. дату публикации RSS'),
      'Визионер / тип: **не подтверждены**. Языки относятся к наблюдаемому источнику, не к полноте переводов.',
      'Точное отличие полей источника находится в `diff`; это не доказательство изменения перевода в JSON.',
      'Проверено: ' + event.checked_at_utc, '',
      '```json', payload.slice(0, 48000), '```',
      ...(payload.length > 48000 ? ['Полный diff доступен в приватном workflow artifact; отображение сокращено.'] : []),
      '', '- [ ] Проверить дату, происхождение, визионера и тип',
      '- [ ] Проверить текст и доступные языки; разрешить спорные атрибуции вручную',
      '- [ ] Подготовить отдельное изменение базы и получить утверждение',
      marker, revision
    ].join('\n');
    if (issue) {
      await github.rest.issues.createComment({owner, repo, issue_number:issue.number, body});
    } else {
      // Compatibility with the former date/RSS watchers, including closed issues.
      const legacy = issues.find(i => !i.pull_request &&
        (event.message_date ? i.title === 'Новое послание: ' + event.message_date + ' — проверить 7 языков' :
          (i.body || '').includes('<!-- message-watch ' + event.identity.language + ' ' + event.source + ' -->')));
      if (legacy) {
        await github.rest.issues.update({owner, repo, issue_number:legacy.number, body:(legacy.body || '')+'\n\n'+body});
      } else {
        const created = await github.rest.issues.create({owner, repo,
          title:'Проверить источник ['+event.identity.language+']: '+(event.message_date || event.key.slice(0,12)), body});
        issues.push(created.data);
      }
    }
  }
};
