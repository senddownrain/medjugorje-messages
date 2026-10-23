/** Serializable UI-independent state: language changes never discard canonical IDs. */
export class SearchSession {
  constructor(catalog, state = {}) {
    this.catalog = catalog;
    this.state = { language: 'ru', query: '', mode: 'words', foldDiacritics: true,
      filters: {}, selectedId: null, scrollTop: 0, ...structuredClone(state) };
    this.previousResults = null;
    if (this.state.selectedId && !catalog.byId.has(this.state.selectedId)) throw new RangeError('Unknown selected ID');
    this.run();
  }
  run() { this.result = this.catalog.search(this.state.language, this.state); return this.result; }
  update(patch) {
    const next = { ...this.state, ...structuredClone(patch) };
    if (next.selectedId && !this.catalog.byId.has(next.selectedId)) throw new RangeError('Unknown selected ID');
    const result = this.catalog.search(next.language, next);
    this.state = next; this.result = result; return result;
  }
  setLanguage(language) {
    const previous = { language: this.state.language, ids: [...this.result.ids] };
    const result = this.update({ language });
    this.previousResults = previous; return result;
  }
  select(id) { if (id !== null && !this.catalog.byId.has(id)) throw new RangeError('Unknown ID'); this.state.selectedId = id; }
  selection() { return this.state.selectedId ? this.catalog.projectResults([this.state.selectedId], this.state.language)[0] : null; }
  snapshot() { return structuredClone(this.state); }
}
