import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { validateUpdateIntegrity } from './update-integrity.mjs';

export const LANGUAGES = ['ru', 'be', 'uk', 'hr', 'en', 'sk', 'lv'];
const root = new URL('../', import.meta.url);
const hash = raw => createHash('sha256').update(raw).digest('hex');

/** Derive facts exclusively from the frozen Stage A evidence; never write data/. */
export async function buildMetadata() {
  const paths = [...LANGUAGES.map(l => `data/${l}.json`), 'data/index.json',
    ...['summary', 'sources', 'thematic', 'proposals'].map(n => `reports/stage-a/${n}.json`)];
  const raw = Object.fromEntries(await Promise.all(paths.map(async p => [p, await readFile(new URL(p, root))])));
  const inputs = Object.fromEntries(paths.map(p => [p, hash(raw[p])]));
  const json = p => JSON.parse(raw[p]);
  const summary = json('reports/stage-a/summary.json');
  const sources = json('reports/stage-a/sources.json');
  const thematic = json('reports/stage-a/thematic.json');
  const proposals = json('reports/stage-a/proposals.json');
  if (summary.status !== 'VERIFIED_SOURCE_SNAPSHOT_COVERAGE' || sources.status !== summary.status ||
      thematic.status !== summary.status || thematic.violation_count !== 0) throw new Error('Stage A coverage is not verified');
  const baseline = JSON.parse(await readFile(new URL('research/update-integrity-baseline.json', root)));
  validateUpdateIntegrity(baseline, Object.fromEntries(LANGUAGES.map(l => [l, json(`data/${l}.json`)])), json('data/index.json').messages);
  const index = json('data/index.json').messages;
  const indexIds = new Set(index.map(r => r.id));
  const archives = Object.fromEntries(LANGUAGES.map(l => [l, json(`data/${l}.json`).messages]));
  const maps = Object.fromEntries(LANGUAGES.map(l => [l, new Map(archives[l].map((r, n) => [r.id, { row: r, position: n }]))]));
  const evidence = {};
  const memberships = new Map();
  for (const [page, source] of Object.entries(thematic.source_pages)) {
    for (const [anchor, group] of Object.entries(source.groups)) {
      const ref = `group:${page}:${anchor}`;
      evidence[ref] = { kind: 'thematic_group', artifact: 'reports/stage-a/thematic.json',
        pointer: `/source_pages/${page.replaceAll('/', '~1')}/groups/${anchor}`,
        source_url: source.content_location, group_url: group.url, anchor, label: group.label,
        zip_member: source.zip_member, source_sha256: source.mhtml_sha256, series: group.series_candidate,
        recipient: anchor.split('.')[1] };
      for (const id of group.ids) {
        if (!indexIds.has(id)) throw new Error(`Unknown thematic ID: ${id}`);
        const refs = memberships.get(id) || [];
        refs.push(ref); memberships.set(id, refs);
      }
    }
  }
  const candidateMap = new Map(proposals.map((p, n) => {
    if (p.applied || p.review_status !== 'PENDING_EDITORIAL_ATTRIBUTION') throw new Error('Unexpected editorial decision');
    const ref = `proposal:${p.id}`;
    evidence[ref] = { kind: 'source_attribution_candidate', artifact: 'reports/stage-a/proposals.json',
      pointer: `/${n}`, quotes: p.evidence, source_confirmed: true, owner_approved: false };
    return [p.id, { ...p, ref }];
  }));
  const fact = (value, source_status, editorial_status, refs) => ({ value, source_status, editorial_status, evidence: refs });
  const messages = index.map((r, n) => {
    const ref = `index:${r.id}`;
    const lang = LANGUAGES.find(l => maps[l].has(r.id));
    const { row: original, position } = maps[lang].get(r.id);
    const snapshot = sources.sources.find(s => s.language === lang);
    const isUpdate = !baseline.index[r.id];
    evidence[ref] = { kind: isUpdate ? 'automatic_source_import_unreviewed' : 'audited_import_record', artifact: 'data/index.json', pointer: `/messages/${n}`,
      language: lang, language_artifact: `data/${lang}.json`, language_pointer: `/messages/${position}`,
      source_url: original.source_url, source_id: original.source_id,
      source_sha256: isUpdate ? original.provenance?.raw_sha256 : snapshot.source_sha256, heading_position: original.source_position,
      ...(isUpdate ? { provenance:original.provenance } : {}) };
    const groups = memberships.get(r.id) || [];
    const series = [...new Set(groups.map(g => evidence[g].series))];
    if (series.length > 1 || series.includes(null)) throw new Error(`Conflicting source groups: ${r.id}`);
    const candidate = candidateMap.get(r.id);
    if (candidate && candidate.before !== r.visionary) throw new Error(`Stale proposal: ${r.id}`);
    const person = candidate ? candidate.proposed : r.visionary;
    if (groups.some(g => evidence[g].recipient !== person)) throw new Error(`Conflicting recipient: ${r.id}`);
    return {
      id: r.id, date: r.date,
      type: fact(r.type, isUpdate ? 'official_identity_mapping' : 'source_confirmed', 'unreviewed', [ref]),
      visionary: fact(person, candidate || groups.length ? 'source_confirmed' : person ? 'legacy_import' : 'unattributed',
        candidate ? 'pending' : 'unreviewed', candidate ? [candidate.ref, ...groups] : [ref, ...groups]),
      series: fact(series[0] || null, groups.length ? 'source_confirmed' : 'unknown', 'unreviewed', groups.length ? groups : [ref]),
      availability: Object.fromEntries(LANGUAGES.map(l => {
        const local = maps[l].get(r.id)?.row;
        return [l, !local ? 'translation_not_present' : local.text ? 'with_text' :
          local.segments.some(s => s.kind === 'context' && s.text) ? 'context_only' : 'no_message_text'];
      }))
    };
  });
  if (new Set(messages.map(r => r.id)).size !== index.length) throw new Error('Duplicate metadata ID');
  return { schema_version: 1, source_snapshot_status: summary.status,
    editorial_policy: 'Source candidates are pending until an explicit owner decision; no owner approvals inferred.',
    inputs, evidence, messages };
}

export async function writeMetadata() {
  const model = await buildMetadata();
  const target = new URL('../derived/search-metadata.json', import.meta.url);
  const output = JSON.stringify(model) + '\n';
  if (process.argv.includes('--check')) {
    if (await readFile(target, 'utf8') !== output) throw new Error('Derived metadata is stale; run npm run build:search-metadata');
  } else {
    await mkdir(new URL('../derived/', import.meta.url), { recursive: true });
    await writeFile(target, output);
  }
  console.log(`Derived metadata: ${model.messages.length} IDs, ${Object.keys(model.evidence).length} evidence references`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await writeMetadata();
