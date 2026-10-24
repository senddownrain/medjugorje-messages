const LATIN = /\p{Script=Latin}[\p{Script=Latin}\p{M}]*/gu;
const WORD = /[\p{L}\p{N}][\p{L}\p{M}\p{N}]*/gu;
const WORD_CHAR = /[\p{L}\p{M}\p{N}]/u;
const EXTRAS = { 'đ': 'd', 'ł': 'l', 'ø': 'o', 'ß': 'ss' };

/** Latin accent folding deliberately preserves Cyrillic й, ё, ў and ї. */
export function normalizeText(text, { foldDiacritics = true } = {}) {
  let value = String(text).normalize('NFC').toLowerCase();
  if (foldDiacritics !== false) value = value.replace(LATIN, run => run.normalize('NFD').replace(/\p{M}/gu, '')
    .replace(/[đłøß]/gu, c => EXTRAS[c]));
  return value.replace(/[’ʼʻ`]/gu, "'").replace(/\s+/gu, ' ');
}

export function tokens(text) { return text.match(WORD) || []; }

export function parseQuery(query = '', options = {}) {
  const input = String(query).trim();
  const mode = options.mode || 'words';
  if (!['words', 'phrase'].includes(mode)) throw new RangeError('Unknown search mode');
  const phrases = [], words = [];
  if (mode === 'phrase' && input) phrases.push(normalizeText(input.replace(/^"(.*)"$/su, '$1'), options));
  else for (const match of input.matchAll(/"([^"]+)"|([^\s"]+)/gu)) {
    const normalized = normalizeText(match[1] || match[2], options);
    if (match[1]) phrases.push(normalized);
    else words.push(...tokens(normalized));
  }
  return { active: Boolean(input), words: [...new Set(words)], phrases,
    terms: [...new Set([...words, ...phrases.flatMap(tokens)])] };
}

export function phraseRanges(text, phrase) {
  const ranges = [];
  if (!phrase) return ranges;
  let at = 0;
  while ((at = text.indexOf(phrase, at)) !== -1) {
    const end = at + phrase.length;
    const before = Array.from(text.slice(Math.max(0, at - 2), at)).at(-1) || '';
    const after = Array.from(text.slice(end, end + 2))[0] || '';
    const points = Array.from(phrase);
    if ((!WORD_CHAR.test(points[0]) || !WORD_CHAR.test(before)) &&
        (!WORD_CHAR.test(points.at(-1)) || !WORD_CHAR.test(after))) ranges.push([at, end]);
    at += Math.max(1, phrase.length);
  }
  return ranges;
}

export function containsPhrase(text, phrase) {
  if (!phrase) return false;
  const points = Array.from(phrase), firstWord = WORD_CHAR.test(points[0]), lastWord = WORD_CHAR.test(points.at(-1));
  let at = 0;
  while ((at = text.indexOf(phrase, at)) !== -1) {
    const end = at + phrase.length;
    let before = text.codePointAt(at - 1);
    if (before >= 0xdc00 && before <= 0xdfff) before = text.codePointAt(at - 2);
    const after = text.codePointAt(end);
    if ((!firstWord || before === undefined || !WORD_CHAR.test(String.fromCodePoint(before))) &&
        (!lastWord || after === undefined || !WORD_CHAR.test(String.fromCodePoint(after)))) return true;
    at += phrase.length;
  }
  return false;
}

/** Offset maps are built for displayed matches only, not retained for the corpus. */
export function normalizeWithMap(text, options = {}) {
  const chunks = [], starts = [], ends = [];
  for (const match of text.matchAll(/\P{M}\p{M}*|\p{M}+/gu)) {
    const normalized = normalizeText(match[0], options);
    for (const char of normalized) {
      if (char === ' ' && chunks.at(-1) === ' ') { ends[ends.length - 1] = match.index + match[0].length; continue; }
      chunks.push(char);
      for (let n = 0; n < char.length; n++) { starts.push(match.index); ends.push(match.index + match[0].length); }
    }
  }
  return { text: chunks.join(''), starts, ends };
}

export function matchingRanges(text, query, options = {}) {
  const parsed = parseQuery(query, options);
  const normalized = normalizeWithMap(text, options);
  const wanted = new Set(parsed.words);
  const ranges = [...parsed.phrases.flatMap(p => phraseRanges(normalized.text, p))];
  for (const match of normalized.text.matchAll(WORD)) if (wanted.has(match[0])) ranges.push([match.index, match.index + match[0].length]);
  const mapped = ranges.map(([start, end]) => [normalized.starts[start], normalized.ends[end - 1]]).sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const range of mapped) {
    const last = merged.at(-1);
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]); else merged.push(range);
  }
  return merged;
}

/** Plain text parts only. Render with textContent / Vue interpolation, never v-html. */
export function highlightParts(text, ranges = []) {
  const parts = []; let offset = 0;
  for (const [start, end] of ranges) {
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < offset || end < start || end > text.length) throw new RangeError('Invalid highlight range');
    if (start > offset) parts.push({ text: text.slice(offset, start), match: false });
    if (end > start) parts.push({ text: text.slice(start, end), match: true });
    offset = end;
  }
  if (offset < text.length) parts.push({ text: text.slice(offset), match: false });
  return parts;
}
