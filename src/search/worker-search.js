import { createSearchWorker } from './worker-client.js';

/** Serial worker messages + generation checks: stale loads/results/errors never reach UI. */
export class WorkerSearch {
  constructor(metadata, archives, changed, factory = createSearchWorker) {
    this.worker = factory(metadata);
    this.archives = archives;
    this.changed = changed;
    this.version = 0;
    this.disposed = false;
    this.language = null;
    this.queue = Promise.resolve();
    // Observe initialization failures immediately, even before the first search.
    this.worker.ready.catch(() => {});
  }
  async run(language, options) {
    const version = ++this.version;
    const current = () => !this.disposed && version === this.version;
    this.changed({ status: 'loading', ids: [], language });
    this.queue = this.queue.then(async () => { try {
      if (!current()) return;
      await this.worker.ready;
      if (!current()) return;
      if (!this.archives[language]) throw new Error('Language archive unavailable');
      if (this.language !== language) {
        await this.worker.loadLanguage(language, this.archives[language]);
        this.language = language;
      }
      if (!current()) return;
      const ids = await this.worker.searchIds(language, structuredClone(options));
      if (current()) this.changed({ status: 'ready', ids, language });
    } catch (error) {
      if (current()) this.changed({ status: 'error', ids: [], language, error: error.message });
    } });
    return this.queue;
  }
  dispose() { this.disposed = true; this.version++; this.worker.dispose(); }
}
