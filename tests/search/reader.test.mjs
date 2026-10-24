import test from 'node:test';
import assert from 'node:assert/strict';
import { WorkerSearch } from '../../src/search/worker-search.js';
import { defaultState, hashFor, route, searchOptions, snippet, restoreReaderState } from '../../src/ui/reader-state.js';
import { languages, translations } from '../../src/ui/translations.js';

const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return { promise, resolve, reject }; };
test('Worker controller serializes load/search and rejects stale results across A→B→A', async () => {
  const gate = deferred(), changes = [], calls = [];
  let active = null, queries = 0;
  const client = { ready:Promise.resolve(),
    loadLanguage:async language => { active=language; calls.push(language); },
    searchIds:async (language, options) => {
      assert.equal(language, active);
      if (++queries === 1) await gate.promise;
      return [options.query];
    }, dispose() {} };
  const search = new WorkerSearch({}, { en:{}, ru:{} }, value => changes.push(value), () => client);
  const first = search.run('en', {query:'old'});
  await new Promise(resolve => setImmediate(resolve));
  const second = search.run('ru', {query:'middle'});
  const third = search.run('en', {query:'latest'});
  gate.resolve(); await Promise.all([first,second,third]);
  assert.deepEqual(changes.filter(s => s.status === 'ready').map(s => s.ids), [['latest']]);
  assert.deepEqual(calls, ['en']); // superseded middle request never loads another corpus
});
test('Worker controller surfaces current errors and suppresses late errors after disposal', async () => {
  const gate = deferred(), changes=[]; let disposed=false;
  const client = { ready:Promise.resolve(),loadLanguage:async()=>{},searchIds:()=>gate.promise,dispose(){disposed=true;} };
  const search = new WorkerSearch({}, {ru:{}}, s=>changes.push(s),()=>client);
  const request = search.run('ru',{});
  await new Promise(resolve=>setImmediate(resolve));
  search.dispose(); gate.reject(new Error('late failure')); await request;
  assert.equal(disposed,true); assert.deepEqual(changes.map(s=>s.status),['loading']);
  const failed = new WorkerSearch({}, {}, s=>changes.push(s),()=>({ ...client, ready:Promise.reject(new Error('init failed')) }));
  await failed.run('ru',{}); assert.equal(changes.at(-1).status,'error'); assert.equal(changes.at(-1).error,'init failed');
});
test('Canonical legacy routes, filter-only defaults and complete UI localization', () => {
  assert.deepEqual(route('#archive'),{selectedId:null,searchOpen:true});
  assert.deepEqual(route('#message/140812s'),{selectedId:'140812s',searchOpen:false});
  assert.deepEqual(route('#message/%E0%A4'),{selectedId:null,searchOpen:false});
  const state=defaultState('en');
  assert.equal(hashFor(state),'#');
  assert.equal(searchOptions(state).filters.availability,'present');
  state.includeMissing=true; state.filters.visionary='vicka';
  assert.deepEqual(searchOptions(state).filters,{visionary:'vicka',availability:'present'});
  const restored=restoreReaderState({ ...state, filters:{year:'2020',month:'09',date:'1984-08-14',series:'ivan_special'},mode:'phrase' },'en');
  assert.deepEqual(searchOptions(restored),{query:'',mode:'words',foldDiacritics:true,filters:{year:'2020',month:'09',availability:'present'}});
  assert.equal(restored.includeMissing,undefined);
  const keys=['vicka','pending','month','allMonths','languageSettings','backToResults'];
  for (const {code} of languages) for (const key of keys) assert.ok(translations[code][key],`${code}:${key}`);
  for (const {code} of languages) {
    for (const person of ['mirjana','marija','ivan','vicka','jakov','ivanka']) assert.ok(translations[code][person].includes(' '),`${code}:${person} must include the surname`);
    for (const type of ['monthly','weekly','annual','special']) assert.ok(translations[code].messageTypes[type],`${code}:${type}`);
    assert.equal(translations[code].messageTypes.unattributed,undefined);
  }
});
test('Snippet highlights source context without promoting it to message text or HTML', () => {
  const record={text:'', title:'Title', segments:[{kind:'context',text:'Before <img onerror=x> Наверніться. After'}]};
  const result=snippet(record,'наверніться',{});
  assert.equal(result.kind,'context'); assert.ok(result.text.includes('<img onerror=x>'));
  assert.equal(result.text.slice(...result.ranges[0]),'Наверніться');
  assert.equal(record.text,''); assert.equal(snippet(null,'',{}),null);
});
