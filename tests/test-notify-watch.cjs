const {test} = require('node:test');
const assert = require('node:assert/strict');
const {mkdtempSync, writeFileSync, rmSync} = require('node:fs');
const {tmpdir} = require('node:os');
const {join} = require('node:path');
const notify = require('../scripts/notify-watch.cjs');

test('notifications deduplicate revisions across reruns and closed issues; no code evaluation', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'watch-notify-'));
  const path = join(dir, 'review.json');
  const issues = [], comments = [], calls = [];
  const api = {
    listForRepo: 'issues', listComments: 'comments',
    create: async body => { calls.push('create'); const data={...body, number:1, state:'closed'}; issues.push(data); return {data}; },
    createComment: async body => { calls.push('comment'); comments.push(body); },
    update: async () => { calls.push('update'); }
  };
  const github = {rest:{issues:api}, paginate:async method => method==='issues' ? issues : comments};
  const params = {github, context:{repo:{owner:'owner',repo:'private'}}, core:{info(){}}, path};
  const event = {key:'a'.repeat(64), fingerprint:'b'.repeat(64), identity:{language:'en'},
    checked_at_utc:'2026-10-23T12:00:00Z', source:'https://thelightofmary.com/message/',
    diff:'```\n@owner <script> throw new Error("never execute"); </script>'};
  try {
    writeFileSync(path, JSON.stringify({events:[]}));
    await notify(params); assert.deepEqual(calls, []);
    writeFileSync(path, JSON.stringify({events:[event]}));
    await notify(params); await notify(params);
    assert.deepEqual(calls, ['create']);
    assert(!issues[0].body.includes('@owner'));
    assert(!issues[0].body.includes('<script>'));
    event.fingerprint = 'c'.repeat(64);
    writeFileSync(path, JSON.stringify({events:[event]}));
    await notify(params); await notify(params);
    assert.deepEqual(calls, ['create','comment']);
  } finally { rmSync(dir, {recursive:true,force:true}); }
});
