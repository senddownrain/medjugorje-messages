import { createHash } from 'node:crypto';
// Canonical JSON matches the Python seal generator; source words are never normalized.
const canonical = value => value && typeof value === 'object' ? Array.isArray(value) ? value.map(canonical) : Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
const digest = value => createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
export function validateUpdateIntegrity(baseline, archives, index) {
  const fail = message => { throw new Error('Update integrity: ' + message); };
  const indexed = new Map(index.map(r => [r.id, r]));
  if (indexed.size !== index.length) fail('duplicate canonical IDs');
  for (const [id, seal] of Object.entries(baseline.index)) {
    const row = indexed.get(id);
    if (!row || digest(Object.fromEntries(Object.entries(row).filter(([k]) => k !== 'translations'))) !== seal.canonical) fail('historical canonical mutation: ' + id);
    for (const [lang, hash] of Object.entries(seal.translations)) {
      if (digest(row.translations?.[lang]) !== hash) fail('historical translation metadata mutation: ' + lang + '/' + id);
    }
  }
  for (const [lang, archive] of Object.entries(archives)) {
    const seals = baseline.languages[lang];
    if (archive.verified !== seals.verified) fail('archive approval changed: ' + lang);
    const rows = new Map(archive.messages.map(r => [r.id, r]));
    if (rows.size !== archive.messages.length) fail('duplicate translation IDs: ' + lang);
    for (const [id, hash] of Object.entries(seals.rows)) if (!rows.has(id) || digest(rows.get(id)) !== hash) fail('historical text mutation: ' + lang + '/' + id);
    for (const row of archive.messages) if (!seals.rows[row.id]) {
      const p = row.provenance;
      if (row.verified !== false || p?.technical_status !== 'validated' || p?.editorial_status !== 'source_import_unreviewed' ||
          !p.official_evidence || !/^[a-f0-9]{64}$/.test(p.official_sha256 || '') || !p.source_url || !p.source_id || (!p.published_at && p.publication_uncertainty !== 'publication_time_not_exposed_by_source') ||
          !/^[a-f0-9]{64}$/.test(p.raw_sha256 || '') || !/^[a-f0-9]{64}$/.test(p.policy_sha256 || '')) fail('new translation lacks provenance: ' + row.id);
      const meta = indexed.get(row.id);
      const hash = createHash('sha256').update(row.text || '').digest('hex');
      if (!meta || meta.date !== row.date || meta.type !== row.type || !row.text || hash !== row.text_sha256 ||
          hash !== meta.translations?.[lang]?.text_sha256 || !meta.translations[lang].present) fail('new translation mismatch: ' + row.id);
    }
    for (const row of index) if (Boolean(row.translations?.[lang]?.present) !== rows.has(row.id)) fail('index presence mismatch: ' + row.id);
  }
}
