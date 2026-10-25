// Identity is translation-specific. A late SK translation cannot reset RU reading.
export const NEW_MESSAGES_KEY = 'medjugorje-new-messages-v1';
const keyFor = (language, id) => `${language}/${id}`;
export function restoreNewMessages(raw) {
  try {
    const value = JSON.parse(raw);
    if (value?.version === 1 && Array.isArray(value.known) && Array.isArray(value.unread) &&
        [...value.known, ...value.unread].every(k => typeof k === 'string')) return value;
  } catch { /* Old or unavailable storage is a first visit. */ }
  return { version:1, initialized:false, known:[], unread:[] };
}
export function observeArrivals(state, arrivals = {}) {
  const keys = Object.entries(arrivals).flatMap(([language, ids]) => ids.map(id => keyFor(language, id)));
  const known = new Set(state.known), unread = new Set(state.unread);
  for (const key of keys) {
    if (state.initialized && !known.has(key)) unread.add(key);
    known.add(key);
  }
  return { version:1, initialized:true, known:[...known], unread:[...unread] };
}
export const isNewMessage = (state, language, id) => state.unread.includes(keyFor(language, id));
export function readMessage(state, language, id) {
  return { ...state, unread:state.unread.filter(key => key !== keyFor(language, id)) };
}
export const newLabels = { ru:'Новое', be:'Новае', uk:'Нове', hr:'Novo', en:'New', sk:'Nové', lv:'Jauns' };
