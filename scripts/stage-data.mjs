import { cp, mkdir, stat } from 'node:fs/promises';

const mandatory = ['index', 'ru', 'be', 'uk'];
const optional = ['hr', 'en', 'sk', 'lv'];
const data = new URL('../data/', import.meta.url);
const dest = new URL('../public/data/', import.meta.url);
await mkdir(dest, { recursive: true });
for (const code of [...mandatory, ...optional]) {
  const name = code + '.json';
  const from = new URL(name, data);
  let info;
  try { info = await stat(from); } catch (error) {
    if (optional.includes(code) && error.code === 'ENOENT') continue;
    throw new Error('Missing required data file: ' + name);
  }
  if (!info.isFile() || info.size < 100) throw new Error('Invalid data file: ' + name);
  await cp(from, new URL(name, dest));
  console.log('Staged ' + name);
}
console.log('Only available, reviewed language archives were staged.');
