import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const data = new URL('../data/', import.meta.url);
const requireLang = ['ru', 'be', 'uk'];
const allLang = ['ru', 'be', 'uk', 'hr', 'en', 'sk', 'lv'];
const read = async name => JSON.parse(await readFile(new URL(name, data), 'utf8'));
const index = await read('index.json');
if (!Array.isArray(index.messages) || index.messages.length === 0) throw new Error('Empty index');
if (index.unique_records !== index.messages.length) throw new Error('Wrong index count');
const indexed = new Map();
for (const row of index.messages) {
  if (indexed.has(row.id)) throw new Error('Duplicate index ID: ' + row.id);
  indexed.set(row.id, row);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(row.date)) throw new Error('Bad date: ' + row.id);
  if (!row.translations || requireLang.some(lang => !row.translations[lang])) {
    throw new Error('Core language metadata missing: ' + row.id);
  }
}
for (const lang of allLang) {
  let source;
  try { source = await read(lang + '.json'); } catch (error) {
    if (error.code === 'ENOENT' && !requireLang.includes(lang)) {
      if (index.messages.some(row => row.translations?.[lang]?.present)) {
        throw new Error('Index includes ' + lang + ' texts but ' + lang + '.json is absent');
      }
      console.log(lang + ': archive not yet imported');
      continue;
    }
    throw error;
  }
  if (source.language !== lang || !Array.isArray(source.messages)) {
    throw new Error('Invalid file: ' + lang);
  }
  const found = new Set();
  for (const m of source.messages) {
    if (found.has(m.id)) throw new Error('Duplicate ' + lang + ' ID: ' + m.id);
    found.add(m.id);
    const row = indexed.get(m.id);
    if (!row) throw new Error('Unindexed ' + lang + ' message: ' + m.id);
    if (!row.translations?.[lang]?.present) throw new Error('Incorrect presence: ' + m.id);
    if (m.date !== row.date || m.type !== row.type) throw new Error('Metadata mismatch: ' + m.id);
    if (Boolean(m.text) !== Boolean(row.translations[lang].has_text)) {
      throw new Error('Incorrect text flag: ' + m.id);
    }
    const digest = createHash('sha256').update(m.text || '').digest('hex');
    if (digest !== m.text_sha256 || digest !== row.translations[lang].text_sha256) {
      throw new Error('Text checksum mismatch: ' + lang + ' / ' + m.id);
    }
  }
  for (const row of index.messages) {
    if (Boolean(row.translations?.[lang]?.present) !== found.has(row.id)) {
      throw new Error('Index/source mismatch: ' + lang + ' ' + row.id);
    }
  }
  console.log(lang + ': ' + found.size + ' records validated');
}
console.log('Index: ' + indexed.size + ' unique records, all available language references checked.');
