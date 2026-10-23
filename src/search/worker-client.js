/** Off-main-thread option for stage C. The caller supplies already loaded data. */
export function createSearchWorker(metadata, { maxIndexes = 2 } = {}) {
  const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
  let sequence = 0, disposed = false;
  const pending = new Map();
  const fail = error => { for (const request of pending.values()) request.reject(error); pending.clear(); };
  worker.onmessage = ({ data }) => {
    const request = pending.get(data.id);
    if (!request) return;
    pending.delete(data.id);
    if (data.error) request.reject(new Error(data.error)); else request.resolve(data.result);
  };
  worker.onerror = event => { disposed = true; fail(new Error(event.message || 'Search worker failed')); worker.terminate(); };
  const rpc = (method, args = []) => new Promise((resolve, reject) => {
    if (disposed) { reject(new Error('Search worker disposed')); return; }
    const id = ++sequence;
    pending.set(id, { resolve, reject });
    try { worker.postMessage({ id, method, args }); } catch (error) { pending.delete(id); reject(error); }
  });
  const ready = rpc('init', [metadata, { maxIndexes }]);
  return { ready,
    loadLanguage: async (language, archive) => { await ready; return rpc('loadLanguage', [language, archive]); },
    searchIds: async (language, options = {}) => { await ready; return rpc('searchIds', [language, options]); },
    highlights: async (id, language, query, options = {}) => { await ready; return rpc('highlights', [id, language, query, options]); },
    diagnostics: async () => { await ready; return rpc('diagnostics'); },
    dispose: () => { disposed = true; worker.terminate(); fail(new Error('Search worker disposed')); }
  };
}
