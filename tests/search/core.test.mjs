import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { buildMetadata } from '../../scripts/build-search-metadata.mjs';
import { SearchCatalog, LANGUAGES } from '../../src/search/catalog.js';
import { SearchSession } from '../../src/search/session.js';
import { normalizeText, normalizeWithMap, matchingRanges, highlightParts } from '../../src/search/unicode.js';

const read = async p => JSON.parse(await readFile(new URL('../../' + p, import.meta.url), 'utf8'));
const model = await read('derived/search-metadata.json');
const archives = Object.fromEntries(await Promise.all(LANGUAGES.map(async l => [l, await read(`data/${l}.json`)])));
const catalog = () => new SearchCatalog(model, archives);

test('derived metadata is reproducible, covers every canonical ID and preserves all eight source hashes', async () => {
  assert.deepEqual(await buildMetadata(), model);
  const original = await read('data/index.json');
  assert.deepEqual(new Set(model.messages.map(r => r.id)), new Set(original.messages.map(r => r.id)));
  for (const l of [...LANGUAGES, 'index']) {
    const bytes = await readFile(new URL(`../../data/${l}.json`, import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), model.inputs[`data/${l}.json`]);
  }
});

test('all assignments have resolvable evidence; 258 group-backed series and eight pending recipients remain separate', () => {
  const counts = {}, series = {}, pending = [];
  for (const row of model.messages) {
    counts[row.visionary.value ?? 'unattributed'] = (counts[row.visionary.value ?? 'unattributed'] || 0) + 1;
    if (row.series.value) series[row.series.value] = (series[row.series.value] || 0) + 1;
    if (row.visionary.editorial_status === 'pending') pending.push(row.id);
    for (const field of ['visionary', 'type', 'series']) {
      assert.notEqual(row[field].editorial_status, 'approved');
      assert.ok(row[field].evidence.length);
      for (const ref of row[field].evidence) assert.ok(model.evidence[ref]);
    }
  }
  assert.deepEqual(counts, { marija: 480, mirjana: 211, jakov: 30, ivanka: 20, ivan: 3, vicka: 1, unattributed: 154 });
  assert.equal(pending.length, 8);
  assert.equal(Object.values(series).reduce((a, b) => a + b), 258);
  for (const id of ['110625a', '160625a', '140812s', '050402s']) assert.equal(model.messages.find(r => r.id === id).series.value, null);
  assert.equal(model.messages.find(r => r.id === '850114w').type.value, 'weekly');
});

test('provenance JSON pointers and verbatim candidate quotes resolve to unchanged source artifacts', async () => {
  const documents = new Map();
  const doc = async path => { if (!documents.has(path)) documents.set(path, await read(path)); return documents.get(path); };
  const pointer = (value, path) => path.slice(1).split('/').reduce((node, key) => node[key.replaceAll('~1', '/').replaceAll('~0', '~')], value);
  for (const evidence of Object.values(model.evidence)) {
    assert.ok(pointer(await doc(evidence.artifact), evidence.pointer));
    for (const quote of evidence.quotes || []) assert.equal(pointer(await doc(quote.artifact), quote.json_pointer), quote.quote);
  }
});

test('filter-only search retains 899 IDs in every language and reports all 1942 missing translations', () => {
  const c = catalog(); let missing = 0;
  const expected = c.searchIds('en');
  for (const lang of LANGUAGES) {
    assert.deepEqual(c.searchIds(lang), expected);
    assert.equal(c.searchIds(lang, { filters: { availability: 'present' } }).length, archives[lang].messages.length);
    missing += c.searchIds(lang, { filters: { availability: 'missing' } }).length;
  }
  assert.equal(expected.length, 899); assert.equal(missing, 1942);
  assert.deepEqual(c.diagnostics(), []); // Metadata filters do not construct text indexes.
  const metadataOnly = new SearchCatalog(model, {});
  assert.equal(metadataOnly.searchIds('lv').length, 899);
  assert.equal(metadataOnly.projectResults(['140812s'], 'uk')[0].archiveLoaded, false);
  assert.throws(() => metadataOnly.searchIds('uk', { query: 'Ivan' }), /not loaded/);
});

test('pending policy never approves a candidate or drops their canonical record', () => {
  const c = catalog();
  assert.equal(c.searchIds('en', { filters: { visionary: 'ivan' } }).length, 3);
  assert.equal(c.searchIds('en', { filters: { visionary: 'vicka' } }).length, 1);
  assert.equal(c.searchIds('en', { filters: { visionary: 'unattributed' } }).length, 154);
  assert.equal(c.searchIds('en', { filters: { visionary: 'ivan', attributionPolicy: 'without_pending' } }).length, 0);
  assert.equal(c.searchIds('en', { filters: { visionary: 'unattributed', attributionPolicy: 'without_pending' } }).length, 162);
  assert.equal(c.searchIds('en', { filters: { attributionPolicy: 'without_pending' } }).length, 899);
  assert.equal(c.searchIds('en', { filters: { reviewStatus: 'pending' } }).length, 8);
  assert.ok(c.projectResults(['060908s'], 'en')[0].pendingAttribution);
});

test('series, type, year, inclusive intervals and annual exceptions are independent', () => {
  const c = catalog();
  assert.equal(c.searchIds('hr', { filters: { series: 'mirjana_second_day' } }).length, 177);
  assert.equal(c.searchIds('hr', { filters: { series: 'mirjana_second_day', availability: 'present' } }).length, 139);
  assert.ok(c.searchIds('en', { filters: { series: 'ivanka_annual' } }).includes('850507a'));
  assert.ok(c.searchIds('en', { filters: { series: 'jakov_annual' } }).includes('980912a'));
  assert.deepEqual(c.searchIds('en', { filters: { dateFrom: '2014-08-12', dateTo: '2014-08-12', year: 2014 } }), ['140812s']);
  assert.equal(c.searchIds('en', { filters: { date: '2014-08-12', type: 'monthly' } }).length, 0);
  const sameDay = c.searchIds('en', { filters: { date: '2010-12-25' } });
  assert.ok(sameDay.includes('101225a') && sameDay.includes('101225m'));
  assert.throws(() => c.searchIds('en', { filters: { dateFrom: '2026-02-30' } }), RangeError);
  assert.throws(() => c.searchIds('en', { filters: { dateFrom: '2026-12-01', dateTo: '2026-01-01' } }), RangeError);
});

test('Unicode canonical equivalents and Latin accents match without erasing Cyrillic letters', () => {
  assert.equal(normalizeText('ČĆŽŠĐ ĽĹŇŔÔ ĀĒĢĶĻŅŪ'), 'cczsd llnro aegklnu');
  assert.equal(normalizeText('č'), normalizeText('c\u030c'));
  assert.notEqual(normalizeText('Й'), normalizeText('И'));
  assert.notEqual(normalizeText('Ў'), normalizeText('У'));
  assert.notEqual(normalizeText('Ї'), normalizeText('І'));
  assert.notEqual(normalizeText('Ё'), normalizeText('Е'));
  assert.equal(normalizeText('З’ЯВЛЕННЯ'), normalizeText("з'явлення"));
  assert.notEqual(normalizeText('č', { foldDiacritics: false }), 'c');
});

test('real seven-language phrases, quoted clauses, word order and AND semantics', () => {
  const c = catalog();
  const phrases = { ru: 'Дорогие дети', be: 'Дарагія дзеці', uk: 'Дорогі діти', hr: 'Draga djeco', en: 'Dear children', sk: 'Drahé deti', lv: 'Dārgie bērni' };
  for (const [language, phrase] of Object.entries(phrases)) {
    assert.ok(c.searchIds(language, { query: phrase, mode: 'phrase' }).length > 0, language);
    assert.deepEqual(c.searchIds(language, { query: `"${phrase}"` }), c.searchIds(language, { query: phrase, mode: 'phrase' }));
    assert.equal(c.searchIds(language, { query: phrase + ' definitelyabsentzz' }).length, 0);
  }
  const hr = c.searchIds('hr', { query: 'kraljica' });
  assert.ok(hr.length > 0);
  assert.deepEqual(c.searchIds('en', { query: 'children dear' }), c.searchIds('en', { query: 'dear children' }));
  assert.ok(c.searchIds('en', { query: '"dear children" peace' }).length > 0);
  assert.deepEqual(c.searchIds('en', { query: '???' }), []);
});

test('context-only messages are searchable without promoting notes to message text', () => {
  const c = catalog();
  assert.ok(c.searchIds('uk', { query: 'Наверніться' }).includes('230225m'));
  const row = c.projectResults(['230225m'], 'uk')[0];
  assert.equal(row.availability, 'context_only'); assert.equal(row.record.text, '');
  assert.equal(c.projectResults(['101225m'], 'ru')[0].availability, 'no_message_text');
  assert.equal(c.projectResults(['140812s'], 'en')[0].record, null);
  assert.ok(c.searchIds('en', { query: 'Ivan' }).includes('060908s'));
  assert.ok(!c.searchIds('hr', { query: 'Ivan' }).includes('060908s'));
});

test('highlight ranges preserve original characters, combining marks, emoji offsets and HTML as text', () => {
  const text = '🙂 C\u030car Āmen <img src=x onerror=alert(1)> ß';
  const ranges = matchingRanges(text, 'car amen img ss');
  const parts = highlightParts(text, ranges);
  assert.equal(parts.map(p => p.text).join(''), text);
  assert.deepEqual(parts.filter(p => p.match).map(p => p.text), ['C\u030car', 'Āmen', 'img', 'ß']);
  assert.equal(normalizeWithMap('A\n\t B').text, normalizeText('A\n\t B'));
  assert.deepEqual(matchingRanges('Мир мирон', 'мир'), [[0, 3]]);
  assert.throws(() => highlightParts(text, [[5, 2]]), RangeError);
});

test('language changes and JSON roundtrips preserve selection, filters, scroll, IDs and honest missing content', () => {
  const c = catalog();
  const s = new SearchSession(c, { language: 'uk', filters: { visionary: 'ivan' }, selectedId: '140812s', scrollTop: 320 });
  const before = [...s.result.ids];
  s.setLanguage('en');
  assert.deepEqual(s.result.ids, before); assert.equal(s.selection().record, null);
  assert.equal(s.selection().id, '140812s'); assert.equal(s.state.scrollTop, 320);
  const restored = new SearchSession(c, JSON.parse(JSON.stringify(s.snapshot())));
  assert.deepEqual(restored.result.ids, before);
  assert.deepEqual(c.projectResults(before, 'hr').map(r => r.id), before);
  s.update({ query: 'Ivan' }); s.setLanguage('uk');
  assert.equal(s.state.query, 'Ivan'); assert.equal(s.selection().id, '140812s');
  const state = s.snapshot();
  assert.throws(() => s.setLanguage('invalid'));
  assert.deepEqual(s.snapshot(), state);
});

test('index LRU bounds retained languages and rejects partial archives', () => {
  const c = catalog();
  for (const language of LANGUAGES) c.searchIds(language, { query: 'a' });
  assert.equal(c.diagnostics().length, 2);
  assert.deepEqual(c.diagnostics().map(d => d.key), ['sk:true', 'lv:true']);
  c.clearIndexes(); assert.deepEqual(c.diagnostics(), []);
  assert.throws(() => new SearchCatalog(model, { en: { language: 'en', messages: [] } }), /Incomplete/);
});
