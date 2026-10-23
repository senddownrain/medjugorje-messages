import { cp, mkdir, stat } from 'node:fs/promises';
import { join } from 'node:path';

const data = new URL('../data/', import.meta.url);
const dest = new URL('../public/data/', import.meta.url);
await mkdir(dest, { recursive: true });
for (const name of ['ru.json', 'be.json', 'uk.json', 'index.json']) {
  const source = new URL(name, data);
  const info = await stat(source);
  if (!info.isFile() || info.size < 100) throw new Error('Missing data file: ' + name);
  await cp(source, new URL(name, dest));
}
console.log('Staged four message JSON files for Vite (not publishing).');
