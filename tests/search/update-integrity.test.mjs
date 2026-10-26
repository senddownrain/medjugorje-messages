import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { validateUpdateIntegrity } from '../../scripts/update-integrity.mjs';
const languages = ['ru','be','uk','hr','en','sk','lv'];
const read = async path => JSON.parse(await readFile(new URL('../../'+path,import.meta.url)));
const baseline = await read('research/update-integrity-baseline.json');
const originals = Object.fromEntries(await Promise.all(languages.map(async l => [l,await read(`data/${l}.json`)])));
const index = (await read('data/index.json')).messages;
test('historical seal validates actual archive and rejects punctuation or attribution edits', () => {
 validateUpdateIntegrity(baseline, originals,index);
 const changed = structuredClone(originals);
 changed.ru.messages[0].text += '.';
 assert.throws(() => validateUpdateIntegrity(baseline,changed,index),/historical text mutation/);
 const meta = structuredClone(index);meta[0].visionary='invented';
 assert.throws(() => validateUpdateIntegrity(baseline,originals,meta),/canonical mutation/);
});
test('a new unreviewed translation passes; an automatic editorial approval fails', () => {
 const archives=structuredClone(originals), meta=structuredClone(index);
 const text='Parser fixture only. '+('No source content. '.repeat(10));
 const digest=createHash('sha256').update(text).digest('hex');
 const row=meta.find(r=>!r.translations.ru.present);
 const record={id:row.id,date:row.date,type:row.type,language:'ru',text,text_sha256:digest,verified:false,
  provenance:{technical_status:'validated',editorial_status:'source_import_unreviewed',
   official_evidence:'https://example.org/official',official_sha256:'a'.repeat(64),
   source_url:'https://example.org/message',source_id:'test',published_at:'2026-10-25T10:00:00Z',
   raw_sha256:'b'.repeat(64),policy_sha256:'c'.repeat(64)}};
 archives.ru.messages.push(record);row.translations.ru={present:true,text_sha256:digest};
 validateUpdateIntegrity(baseline,archives,meta);
 record.verified=true;
 assert.throws(()=>validateUpdateIntegrity(baseline,archives,meta),/lacks provenance/);
});
