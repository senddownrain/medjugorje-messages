import { SearchCatalog } from '../../src/search/catalog.js';

export const PHRASES = { ru: 'Дорогие дети', be: 'Дарагія дзеці', uk: 'Дорогі діти', hr: 'Draga djeco', en: 'Dear children', sk: 'Drahé deti', lv: 'Dārgie bērni' };

/** Existing App.vue predicate, including per-record lowercase and language presence. */
export function legacySearch(index, local, language, options) {
  const f = options.filters || {};
  return index.filter(row => {
    if (!row.translations?.[language]?.present) return false;
    if (f.year && !row.date.startsWith(String(f.year))) return false;
    if (f.type && row.type !== f.type) return false;
    if (f.visionary && row.visionary !== f.visionary) return false;
    if (f.date && row.date !== f.date) return false;
    const text = (options.query || '').trim().toLocaleLowerCase();
    if (text) {
      const record = local.get(row.id);
      if (!(record?.title || '').toLocaleLowerCase().includes(text) &&
          !(record?.text || '').toLocaleLowerCase().includes(text)) return false;
    }
    return true;
  }).map(row => row.id);
}

function measure(fn, count) {
  for (let n = 0; n < 5; n++) fn();
  const samples = [];
  for (let n = 0; n < count; n++) { const start = performance.now(); fn(); samples.push(performance.now() - start); }
  samples.sort((a, b) => a - b);
  return { p50_ms: samples[Math.floor(samples.length * 0.5)], p95_ms: samples[Math.floor(samples.length * 0.95)],
    max_ms: samples.at(-1), iterations: count };
}

export function benchmarkLanguage(metadata, archives, originalIndex, language, iterations = 50, catalog = null) {
  const engine = catalog || new SearchCatalog(metadata, archives);
  engine.clearIndexes();
  const start = performance.now();
  const index = engine.getIndex(language);
  const cold_ms = performance.now() - start;
  const local = new Map(archives[language].messages.map(r => [r.id, r]));
  const cases = [
    { name: 'phrase', query: PHRASES[language], mode: 'phrase', filters: { availability: 'present' } },
    { name: 'missing-word', query: 'definitelyabsentzz', filters: { availability: 'present' } },
    { name: 'type-year', filters: { type: 'monthly', year: 2026, availability: 'present' } },
    { name: 'phrase-year', query: PHRASES[language], mode: 'phrase', filters: { year: 2020, availability: 'present' } }
  ];
  return { language, cold_ms, index: index.stats, cases: cases.map(options => {
    const next = () => engine.searchIds(language, options);
    const old = () => legacySearch(originalIndex, local, language, options);
    const newIds = next(), oldIds = old();
    const equivalent_result_ids = JSON.stringify(newIds) === JSON.stringify(oldIds);
    const indexed = measure(next, iterations), legacy = measure(old, iterations);
    return { name: options.name, query: options.query || '', filters: options.filters,
      indexed_count: newIds.length, legacy_count: oldIds.length, equivalent_result_ids, indexed, legacy,
      p95_speedup: equivalent_result_ids && indexed.p95_ms > 0 ? legacy.p95_ms / indexed.p95_ms : null };
  }) };
}
