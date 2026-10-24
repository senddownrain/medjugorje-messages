import { normalizeText, parseQuery, tokens, containsPhrase, matchingRanges } from './unicode.js';

export const LANGUAGES = ['ru', 'be', 'uk', 'hr', 'en', 'sk', 'lv'];
const validDate = value => {
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(value) || !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value) throw new RangeError('Invalid ISO date');
  return value;
};
function has(sorted, n) {
  let low = 0, high = sorted.length;
  while (low < high) { const mid = (low + high) >>> 1; if (sorted[mid] < n) low = mid + 1; else high = mid; }
  return sorted[low] === n;
}
function optionsFor(options) {
  const f = { ...(options.filters || {}) };
  for (const name of ['dateFrom', 'dateTo', 'date']) if (f[name]) validDate(f[name]);
  if (f.dateFrom && f.dateTo && f.dateFrom > f.dateTo) throw new RangeError('Reversed date interval');
  if (f.year != null && !/^\d{4}$/u.test(String(f.year))) throw new RangeError('Invalid year');
  if (f.month != null) {
    if (!/^(?:0?[1-9]|1[0-2])$/u.test(String(f.month))) throw new RangeError('Invalid month');
    f.month = String(f.month).padStart(2, '0');
  }
  if (f.attributionPolicy && !['include_pending', 'without_pending'].includes(f.attributionPolicy)) throw new RangeError('Unknown attribution policy');
  if (f.availability && !['all', 'present', 'with_text', 'missing'].includes(f.availability)) throw new RangeError('Unknown availability filter');
  return f;
}

/** Indexes are local and bounded by an LRU; data loading and PWA caching are external. */
export class SearchCatalog {
  constructor(metadata, archives, { maxIndexes = 2 } = {}) {
    if (metadata.schema_version !== 1 || !Number.isInteger(maxIndexes) || maxIndexes < 1) throw new Error('Invalid search configuration');
    this.metadata = metadata;
    this.rows = [...metadata.messages].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
    this.byId = new Map(this.rows.map(r => [r.id, r]));
    if (this.byId.size !== this.rows.length) throw new Error('Duplicate metadata IDs');
    this.archives = new Map(); this.cache = new Map(); this.maxIndexes = maxIndexes;
    this.facets = new Map();
    const add = (key, n) => { if (!this.facets.has(key)) this.facets.set(key, []); this.facets.get(key).push(n); };
    this.rows.forEach((row, n) => {
      for (const [name, value] of Object.entries({ type: row.type.value, series: row.series.value ?? 'unattributed',
        year: row.date.slice(0, 4), month: row.date.slice(5, 7), date: row.date, visionary: row.visionary.value ?? 'unattributed',
        withoutPending: row.visionary.editorial_status === 'pending' ? 'unattributed' : row.visionary.value ?? 'unattributed',
        reviewStatus: row.visionary.editorial_status })) add(`${name}:${value}`, n);
      for (const l of LANGUAGES) {
        const a = row.availability[l];
        add(`${l}:${a === 'translation_not_present' ? 'missing' : 'present'}`, n);
        if (a === 'with_text') add(`${l}:with_text`, n);
      }
    });
    for (const [key, list] of this.facets) this.facets.set(key, Uint32Array.from(list));
    for (const [language, data] of Object.entries(archives)) this.addLanguageArchive(language, data);
  }

  addLanguageArchive(language, data) {
      if (!LANGUAGES.includes(language) || data.language !== language) throw new Error('Language mismatch');
      const records = new Map();
      for (const r of data.messages) {
        if (!this.byId.has(r.id) || records.has(r.id) || r.language !== language) throw new Error('Invalid language record');
        records.set(r.id, r);
      }
      for (const row of this.rows) {
        const local = records.get(row.id);
        if ((row.availability[language] !== 'translation_not_present') !== Boolean(local)) throw new Error('Incomplete language archive');
        if (local && (local.date !== row.date || local.type !== row.type.value)) throw new Error('Archive metadata mismatch');
      }
      this.archives.set(language, records);
      this.cache.delete(`${language}:true`); this.cache.delete(`${language}:false`);
  }

  getIndex(language, foldDiacritics = true) {
    if (!LANGUAGES.includes(language)) throw new RangeError('Unknown language');
    const key = `${language}:${foldDiacritics}`;
    if (this.cache.has(key)) { const value = this.cache.get(key); this.cache.delete(key); this.cache.set(key, value); return value; }
    const records = this.archives.get(language);
    if (!records) throw new Error(`Language archive not loaded: ${language}`);
    const postings = new Map(), fields = new Map(); let characters = 0;
    this.rows.forEach((row, n) => {
      const local = records.get(row.id);
      if (!local) return;
      const original = [{ kind: 'title', text: local.title }, { kind: 'message', text: local.text },
        ...local.segments.filter(s => s.kind === 'context').map(s => ({ kind: 'context', text: s.text }))];
      const normalized = original.filter(f => f.text).map(f => ({ ...f, normalized: normalizeText(f.text, { foldDiacritics }) }));
      fields.set(n, normalized); const unique = new Set();
      for (const f of normalized) { characters += f.normalized.length; for (const term of tokens(f.normalized)) unique.add(term); }
      for (const term of unique) { if (!postings.has(term)) postings.set(term, []); postings.get(term).push(n); }
    });
    let postingEntries = 0;
    for (const [term, list] of postings) { postingEntries += list.length; postings.set(term, Uint32Array.from(list)); }
    const result = { fields, postings, stats: { documents: fields.size, vocabulary: postings.size, postingEntries,
      normalizedCharacters: characters, payloadBytesLowerBound: characters * 2 + postingEntries * 4 + [...postings.keys()].reduce((n, t) => n + t.length * 2, 0) } };
    this.cache.set(key, result);
    if (this.cache.size > this.maxIndexes) this.cache.delete(this.cache.keys().next().value);
    return result;
  }

  searchIds(language, options = {}) {
    if (!LANGUAGES.includes(language)) throw new RangeError('Unknown language');
    const f = optionsFor(options), parsed = parseQuery(options.query, options);
    if (parsed.active && !this.archives.has(language)) throw new Error('Language archive not loaded');
    let candidates = null, index;
    const lists = [];
    for (const name of ['type', 'series', 'year', 'month', 'date', 'visionary', 'reviewStatus']) {
      if (!f[name] || name === 'reviewStatus' && f[name] === 'any') continue;
      const facet = name === 'visionary' && f.attributionPolicy === 'without_pending' ? 'withoutPending' : name;
      lists.push(this.facets.get(`${facet}:${f[name]}`));
    }
    if (f.availability && f.availability !== 'all') lists.push(this.facets.get(`${language}:${f.availability}`));
    if (lists.some(list => !list)) return [];
    if (parsed.active) {
      index = this.getIndex(language, options.foldDiacritics !== false);
      if (!parsed.terms.length && !parsed.phrases.length) return [];
      lists.push(...parsed.terms.map(t => index.postings.get(t)));
      if (lists.some(v => !v)) return [];
      if (!lists.length) candidates = [...index.fields.keys()];
    }
    if (lists.length) {
      lists.sort((a, b) => a.length - b.length);
      const remaining = lists.slice(1);
      candidates = Array.from(lists[0]).filter(n => remaining.every(list => has(list, n)));
    }
    const result = [];
    for (const n of candidates || this.rows.keys()) {
      const row = this.rows[n];
      const person = f.attributionPolicy === 'without_pending' && row.visionary.editorial_status === 'pending' ? null : row.visionary.value;
      if (f.visionary && (f.visionary === 'unattributed' ? person !== null : person !== f.visionary)) continue;
      if (f.series && (f.series === 'unattributed' ? row.series.value !== null : row.series.value !== f.series)) continue;
      if (f.type && row.type.value !== f.type) continue;
      if (f.year && row.date.slice(0, 4) !== String(f.year)) continue;
      if (f.month && row.date.slice(5, 7) !== f.month) continue;
      if (f.date && row.date !== f.date || f.dateFrom && row.date < f.dateFrom || f.dateTo && row.date > f.dateTo) continue;
      if (f.reviewStatus && f.reviewStatus !== 'any' && row.visionary.editorial_status !== f.reviewStatus) continue;
      const state = row.availability[language];
      if (f.availability === 'present' && state === 'translation_not_present' ||
          f.availability === 'missing' && state !== 'translation_not_present' ||
          f.availability === 'with_text' && state !== 'with_text') continue;
      if (parsed.phrases.some(phrase => !index.fields.get(n)?.some(field => containsPhrase(field.normalized, phrase)))) continue;
      result.push(row.id);
    }
    return result;
  }

  projectResults(ids, language) {
    if (!LANGUAGES.includes(language)) throw new RangeError('Unknown language');
    return ids.map(id => {
      const metadata = this.byId.get(id);
      if (!metadata) throw new RangeError(`Unknown canonical ID: ${id}`);
      const record = this.archives.get(language)?.get(id) || null;
      return { id, metadata, language, availability: metadata.availability[language], record,
        archiveLoaded: this.archives.has(language), pendingAttribution: metadata.visionary.editorial_status === 'pending' };
    });
  }

  search(language, options = {}) {
    const ids = this.searchIds(language, options);
    const offset = options.offset ?? 0, limit = options.limit ?? 35;
    if (![offset, limit].every(n => Number.isInteger(n) && n >= 0)) throw new RangeError('Invalid pagination');
    return { language, ids, total: ids.length, rows: this.projectResults(ids.slice(offset, offset + limit), language) };
  }

  highlights(id, language, query, options = {}) {
    const n = this.rows.findIndex(r => r.id === id);
    if (n < 0) throw new RangeError('Unknown canonical ID');
    return (this.getIndex(language, options.foldDiacritics !== false).fields.get(n) || []).map(field =>
      ({ kind: field.kind, text: field.text, ranges: matchingRanges(field.text, query, options) }));
  }

  clearIndexes() { this.cache.clear(); }
  diagnostics() { return [...this.cache].map(([key, index]) => ({ key, ...index.stats })); }
}
