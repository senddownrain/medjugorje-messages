// One source of truth: original JSON + reproducible B metadata. No text edits/approval.
import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile, rm } from 'node:fs/promises';
const root = new URL('../', import.meta.url);
const languages = ['ru', 'be', 'uk', 'hr', 'en', 'sk', 'lv'];
const inputs = await Promise.all(['derived/search-metadata.json', ...languages.map(l => `data/${l}.json`)]
  .map(path => readFile(new URL(path, root))));
const version = createHash('sha256').update(Buffer.concat(inputs)).digest('hex').slice(0, 24);
const metadata = JSON.parse(inputs[0]);
for (const [n, language] of languages.entries()) {
  const hash = createHash('sha256').update(inputs[n + 1]).digest('hex');
  if (metadata.inputs[`data/${language}.json`] !== hash) throw new Error('Stale metadata: run build:search-metadata before building runtime data');
}

const rows = [...metadata.messages].sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
const dest = new URL('../public/data/', import.meta.url);
await rm(dest, { recursive:true, force:true });
await mkdir(new URL(version + '/', dest), { recursive:true });
const manifest = { schema_version:1, data_version:version,
  editorial_policy:metadata.editorial_policy, source_snapshot_status:metadata.source_snapshot_status,
  metadata:`${version}/metadata.json`, latest:{}, arrivals:{} };
await writeFile(new URL(manifest.metadata, dest), inputs[0]);
for (const [n, language] of languages.entries()) {
  const archive = JSON.parse(inputs[n + 1]);
  manifest.arrivals[language] = archive.messages.filter(r => r.provenance?.imported_at).map(r => r.id);
  const row = rows.find(r => r.availability[language] === 'with_text');
  const record = archive.messages.find(r => r.id === row?.id);
  if (!row || !record?.text) throw new Error('No latest text: ' + language);
  const file = `${version}/latest-${language}.json`;
  manifest.latest[language] = { id:row.id, date:row.date, available_languages:languages.filter(l => row.availability[l] !== 'translation_not_present'),
    file, archive:`${version}/${language}.json` };
  // Preserve unverified and pending statuses; generating a manifest never approves them.
  await writeFile(new URL(file, dest), JSON.stringify({ schema_version:1, data_version:version,
    language, verified:archive.verified, row, record }));
  await writeFile(new URL(manifest.latest[language].archive, dest), inputs[n + 1]);
}
await writeFile(new URL('latest.json', dest), JSON.stringify(manifest));
console.log(`Runtime data ${version}: seven independent latest records; archives only on demand.`);
