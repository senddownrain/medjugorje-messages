import { matchingRanges } from '../search/unicode.js';

export const emptyFilters = () => ({ visionary: '', series: '', type: '', year: '', date: '', dateFrom: '', dateTo: '' });
export const defaultState = (language = 'ru') => ({ language, query: '', mode: 'words', foldDiacritics: true,
  filters: emptyFilters(), includeMissing: false, searchOpen: false, filtersOpen: false,
  limit: 35, selectedId: null, scrollTop: 0, focusId: null });

export function route(hash) {
  try {
    const value = decodeURIComponent(hash.slice(1));
    if (value.startsWith('message/')) return { selectedId: value.slice(8), searchOpen: false };
    return { selectedId: null, searchOpen: value === 'search' || value === 'archive' };
  } catch { return { selectedId: null, searchOpen: false }; }
}
export const hashFor = state => state.selectedId ? '#message/' + encodeURIComponent(state.selectedId) : state.searchOpen ? '#search' : '#';
export function searchOptions(state) {
  return { query: state.query, mode: state.mode, foldDiacritics: state.foldDiacritics,
    filters: { ...Object.fromEntries(Object.entries(state.filters).filter(([, value]) => value !== '')),
      availability: state.includeMissing ? 'all' : 'present' } };
}

/** Clip only the presentation; the original message/segments are never changed. */
export function snippet(record, query, options) {
  if (!record) return null;
  const fields = [{ kind: 'message', text: record.text },
    ...record.segments.filter(s => s.kind === 'context'), { kind: 'title', text: record.title }].filter(f => f.text);
  let field = fields[0];
  let ranges = [];
  for (const candidate of fields) {
    const found = matchingRanges(candidate.text, query, options);
    if (found.length) { field = candidate; ranges = found; break; }
  }
  if (!field) return null;
  let start = ranges.length ? Math.max(0, ranges[0][0] - 55) : 0;
  if (start) { const space = field.text.indexOf(' ', start); if (space !== -1 && space < start + 25) start = space + 1; }
  if (/\p{M}/u.test(field.text[start] || '')) while (start > 0 && /\p{M}/u.test(field.text[start])) start--;
  if (start && /[\uDC00-\uDFFF]/u.test(field.text[start])) start--;
  let end = Math.min(field.text.length, start + 200);
  if (end < field.text.length && /[\uDC00-\uDFFF\p{M}]/u.test(field.text[end])) end--;
  const text = (start ? '…' : '') + field.text.slice(start, end) + (end < field.text.length ? '…' : '');
  return { kind: field.kind, text, ranges: matchingRanges(text, query, options) };
}
