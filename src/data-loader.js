const pending = new Map();
const root = import.meta.env.BASE_URL + 'data/';
export function readData(path, { refresh = false } = {}) {
  // Paths come only from our generated manifest; never cross-origin or traversal.
  if (!/^[a-zA-Z0-9/._-]+$/.test(path) || path.includes('..') || path.startsWith('/')) return Promise.reject(new Error('Invalid data path'));
  if (refresh && /^latest(?:-for-[a-z]{2})?\.json$/.test(path)) pending.delete(path);
  if (!pending.has(path)) pending.set(path, fetch(root + path).then(async response => {
    if (!response.ok) throw new Error(path + ': HTTP ' + response.status);
    if (!response.headers.get('content-type')?.includes('json')) throw new Error('Expected JSON: ' + path);
    return response.json();
  }).catch(error => { pending.delete(path); throw error; }));
  return pending.get(path);
}
