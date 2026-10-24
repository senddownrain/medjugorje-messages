import { createApp, h } from 'vue';
import { SearchCatalog, LANGUAGES } from '../../src/search/catalog.js';
import { useMessageSearch } from '../../src/search/useMessageSearch.js';
import SearchHighlight from '../../src/search/SearchHighlight.vue';
import { matchingRanges } from '../../src/search/unicode.js';
import { benchmarkLanguage } from './benchmark.js';
import { createSearchWorker } from '../../src/search/worker-client.js';

const read = async path => { const response = await fetch(new URL('../../' + path, import.meta.url)); if (!response.ok) throw new Error(path); return response.json(); };
const metadata = await read('derived/search-metadata.json');
const archives = Object.fromEntries(await Promise.all(LANGUAGES.map(async l => [l, await read(`data/${l}.json`)])));
const original = await read('data/index.json');
const catalog = new SearchCatalog(metadata, archives);
const malicious = '🙂 C\u030car Āmen <img src=x onerror="window.injected=1">';
let adapter;
createApp({ setup() {
  adapter = useMessageSearch(catalog, { language: 'en' });
  return () => h('main', [
    h('p', 'Локальный тестовый стенд. Не является интерфейсом этапа C.'),
    h('input', { id: 'query', 'aria-label': 'Query', value: adapter.state.value.query, onInput: e => adapter.update({ query: e.target.value }) }),
    h('select', { id: 'language', value: adapter.state.value.language, onChange: e => adapter.setLanguage(e.target.value) }, LANGUAGES.map(l => h('option', { value: l }, l))),
    h('output', { id: 'total' }, String(adapter.result.value.total)),
    h('pre', { id: 'selection' }, JSON.stringify(adapter.selection.value && { id: adapter.selection.value.id,
      availability: adapter.selection.value.availability, pending: adapter.selection.value.pendingAttribution, text: adapter.selection.value.record?.text || null })),
    h('div', { id: 'safe-highlight' }, [h(SearchHighlight, { text: malicious, ranges: matchingRanges(malicious, 'car amen img') })]),
    h('ul', adapter.result.value.rows.map(row => h('li', { 'data-id': row.id, 'data-pending': String(row.pendingAttribution) }, row.id)))
  ]);
} }).mount('#app');
window.searchHarness = { metadata, catalog, archives, adapter,
  workerCheck: async () => {
    const worker = createSearchWorker(metadata);
    try {
      await worker.ready; await worker.loadLanguage('en', archives.en);
      let ticks = 0;
      const timer = setInterval(() => ticks++, 1);
      const start = performance.now();
      const [found, empty] = await Promise.all([worker.searchIds('en', { query: '"Dear children"' }), worker.searchIds('en', { query: 'definitelyabsentzz' })]);
      const cold_request_ms = performance.now() - start;
      clearInterval(timer);
      if (JSON.stringify(found) !== JSON.stringify(catalog.searchIds('en', { query: '"Dear children"' })) || empty.length) throw new Error('Worker result mismatch');
      await worker.loadLanguage('uk', archives.uk);
      const selected = await worker.searchIds('uk', { query: 'Ivan', filters: { visionary: 'ivan' } });
      if (!selected.includes('140812s')) throw new Error('Worker lost canonical ID');
      let invalidRejected = false;
      try { await worker.searchIds('en', { query: 'children' }); } catch { invalidRejected = true; }
      if (!invalidRejected) throw new Error('Worker retained previous language corpus');
      return { cold_request_ms, main_thread_timer_ticks: ticks, worker_cpu_throttle_verified: false,
        checks: ['concurrent RPC responses', 'same IDs as synchronous catalog', 'active-language corpus replacement', 'no loss of pending ID'] };
    } finally { worker.dispose(); }
  },
  benchmark: (language, iterations = 50) => benchmarkLanguage(metadata, archives, original.messages, language, iterations, catalog) };
