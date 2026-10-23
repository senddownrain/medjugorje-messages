import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { cpus, arch, platform } from 'node:os';
import { gzipSync } from 'node:zlib';
import { SearchCatalog, LANGUAGES } from '../src/search/catalog.js';
import { benchmarkLanguage } from '../tests/search/benchmark.js';

if (!global.gc) throw new Error('Run node --expose-gc scripts/benchmark-search.mjs');
const read = async p => JSON.parse(await readFile(new URL('../' + p, import.meta.url), 'utf8'));
global.gc(); const beforeMetadata = process.memoryUsage();
const metadata = await read('derived/search-metadata.json');
global.gc(); const metadata_heap_delta_bytes = process.memoryUsage().heapUsed - beforeMetadata.heapUsed;
const archives = Object.fromEntries(await Promise.all(LANGUAGES.map(async l => [l, await read(`data/${l}.json`)])));
const original = await read('data/index.json');
global.gc(); const beforeCatalog = process.memoryUsage();
const catalog = new SearchCatalog(metadata, archives);
global.gc(); const afterCatalog = process.memoryUsage();
const results = [];
for (const language of LANGUAGES) {
  catalog.clearIndexes(); global.gc(); const before = process.memoryUsage();
  const result = benchmarkLanguage(metadata, archives, original.messages, language, 100, catalog);
  global.gc(); const after = process.memoryUsage();
  result.retained_heap_delta_bytes = after.heapUsed - before.heapUsed;
  result.retained_array_buffers_delta_bytes = after.arrayBuffers - before.arrayBuffers;
  result.rss_delta_bytes = after.rss - before.rss;
  results.push(result);
}
const report = { runtime: process.version, platform: platform(), arch: arch(), cpu: cpus()[0].model,
  date_utc: new Date().toISOString(), corpus_ids: metadata.messages.length,
  source_inputs: metadata.inputs, metadata_bytes: (await readFile(new URL('../derived/search-metadata.json', import.meta.url))).byteLength,
  metadata_gzip_bytes: gzipSync(await readFile(new URL('../derived/search-metadata.json', import.meta.url))).byteLength,
  metadata_heap_delta_bytes, catalog_heap_delta_bytes: afterCatalog.heapUsed - beforeCatalog.heapUsed,
  catalog_array_buffers_delta_bytes: afterCatalog.arrayBuffers - beforeCatalog.arrayBuffers,
  methodology: 'Local Node CPU, one cold index per language, 5 warmups + 100 timed calls per case; explicit GC deltas. Per-index heap/ArrayBuffer deltas exclude already-loaded corpus, metadata and catalog. RSS is allocator-dependent and may decrease. Not Android.',
  results };
await mkdir(new URL('../reports/stage-b/', import.meta.url), { recursive: true });
await writeFile(new URL('../reports/stage-b/search-node.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
console.table(results.map(r => ({ language: r.language, cold_ms: r.cold_ms.toFixed(2),
  warm_p95_max_ms: Math.max(...r.cases.map(c => c.indexed.p95_ms)).toFixed(3), retained_MiB: (r.retained_heap_delta_bytes / 1048576).toFixed(2) })));
