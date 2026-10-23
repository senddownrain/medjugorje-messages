import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const data = new URL('../data/', import.meta.url);
const read = async name => JSON.parse(await readFile(new URL(name, data), 'utf8'));
const index = await read('index.json');
const langs = ['ru', 'be', 'uk'];
if (!Array.isArray(index.messages) || index.messages.length === 0) throw new Error('Empty index');
if (index.unique_records !== index.messages.length) throw new Error('Wrong index count');
const ids = new Set();
for (const row of index.messages) {
  if (ids.has(row.id)) throw new Error('Duplicate index ID: ' + row.id);
  ids.add(row.id);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(row.date)) throw new Error('Bad date: ' + row.id);
  if (!row.translations || langs.some(l => !row.translations[l])) throw new Error('Language status missing');
}
for (const lang of langs) {
  const source = await read(lang + '.json');
  if (source.language !== lang || !Array.isArray(source.messages)) {
    throw new Error('Invalid file: ' + lang);
  }
  const found = new Set();
  for (const m of source.messages) {
    if (found.has(m.id)) throw new Error('Duplicate ' + lang + ' ID: ' + m.id);
    found.add(m.id);
    const row = index.messages.find(x => x.id === m.id);
    if (!row) throw new Error('Unindexed ' + lang + ' message: ' + m.id);
    if (!row.translations[lang].present) throw new Error('Incorrect presence: ' + m.id);
    if (m.date !== row.date || m.type !== row.type) throw new Error('Metadata mismatch: ' + m.id);
    if (Boolean(m.text) !== Boolean(row.translations[lang].has_text)) {
      throw new Error('Incorrect text flag: ' + m.id);
    }
    const digest = createHash('sha256').update(m.text || '').digest('hex');
    if (digest !== row.translations[lang].text_sha256) throw new Error('Text checksum mismatch: ' + m.id);
  }
  for (const row of index.messages) {
    if (Boolean(row.translations[lang].present) !== found.has(row.id)) {
      throw new Error('Index/source mismatch: ' + lang + ' ' + row.id);
    }
  }
  console.log(lang + ': ' + found.size + ' messages validated');
}
console.log('Index: ' + ids.size + ' unique records, all language references checked.');
