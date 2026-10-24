import { computed, shallowRef } from 'vue';
import { SearchSession } from './session.js';

/** Adapter for stage C; no fetch, storage, routing or service-worker side effects. */
export function useMessageSearch(catalog, initialState = {}) {
  const session = new SearchSession(catalog, initialState);
  const result = shallowRef(session.result), state = shallowRef(session.snapshot());
  function sync(action) { action(); result.value = session.result; state.value = session.snapshot(); }
  return { result, state, selection: computed(() => { state.value; return session.selection(); }),
    update: patch => sync(() => session.update(patch)),
    setLanguage: language => sync(() => session.setLanguage(language)),
    select: id => sync(() => session.select(id)), snapshot: () => session.snapshot() };
}
