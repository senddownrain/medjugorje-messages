import { SearchCatalog } from './catalog.js';
let catalog;
self.onmessage = ({ data: { id, method, args } }) => {
  try {
    let result;
    if (method === 'init') { catalog = new SearchCatalog(args[0], {}, args[1]); result = true; }
    else if (method === 'loadLanguage') {
      // Keep only the active language corpus in this worker; no fetch/cache policy here.
      catalog.addLanguageArchive(args[0], args[1]);
      for (const l of [...catalog.archives.keys()]) if (l !== args[0]) catalog.archives.delete(l);
      catalog.clearIndexes(); result = true;
    } else if (['searchIds', 'highlights', 'diagnostics'].includes(method)) result = catalog[method](...args);
    else throw new Error('Unknown worker method');
    self.postMessage({ id, result });
  } catch (error) { self.postMessage({ id, error: error.message }); }
};
