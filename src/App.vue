<script setup>
import { computed, markRaw, nextTick, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue';
import { useTheme } from 'vuetify';
import { readData } from './data-loader.js';
import { languages, translations } from './ui/translations.js';
import { defaultState, emptyFilters, hashFor, route, searchOptions, restoreReaderState } from './ui/reader-state.js';
import ResultCard from './ui/ResultCard.vue';
import MessageReader from './ui/MessageReader.vue';

const baseUrl = import.meta.env.BASE_URL;

function setting(key, fallback) { try { return localStorage.getItem(key) || fallback; } catch { return fallback; } }
function save(key, value) { try { localStorage.setItem(key, value); } catch { /* private mode */ } }
const validLanguage = value => languages.some(l => l.code === value);
const readingLanguage = setting('medjugorje-language', 'ru');
const state = reactive(defaultState(validLanguage(readingLanguage) ? readingLanguage : 'ru'));
const interfaceLanguage = setting('medjugorje-interface-language', 'ru');
const uiLang = ref(validLanguage(interfaceLanguage) ? interfaceLanguage : 'ru');
const themeSetting = setting('medjugorje-theme', 'auto');
const theme = ref(['auto', 'light', 'dark'].includes(themeSetting) ? themeSetting : 'auto');
const darkSystem = window.matchMedia('(prefers-color-scheme: dark)');
const systemDark = ref(darkSystem.matches);
const isDark = computed(() => theme.value === 'dark' || theme.value === 'auto' && systemDark.value);
const vuetifyTheme = useTheme();
const T = computed(() => translations[uiLang.value]);
const searchActive = computed(() => state.searchOpen && !state.selectedId);
const settingsOpen = ref(false), queryInput = ref(null), resultHeading = ref(null);
const busy = ref(true), failed = ref(false);
const catalog = shallowRef(null);
const manifest = shallowRef(null), latest = shallowRef({});
const online = ref(navigator.onLine);
const updateReady = ref(false);
let dataUpdateReady = false, checkingUpdate = false;
function applyUpdate() {
  replaceEntry();
  if (dataUpdateReady) location.reload();
  else window.dispatchEvent(new Event('accept-app-update'));
}
async function checkDataUpdate() {
  if (document.visibilityState !== 'visible' || !navigator.onLine || !manifest.value || checkingUpdate) return;
  checkingUpdate = true;
  try {
    const value = await readData('latest.json', { refresh:true });
    if (value.schema_version === 1 && value.data_version !== manifest.value.data_version) {
      dataUpdateReady = true; updateReady.value = true;
    }
  } catch { /* Preserve the last successful data during a failed update check. */ }
  finally { checkingUpdate = false; }
}
function networkChanged() { online.value = navigator.onLine; }
function foundUpdate() { updateReady.value = true; }
const search = shallowRef({ status: 'loading', ids: [], language: state.language });
let archives = {}, metadata, searchModule, advancedPromise, workerSearch, restoring = false, scrollFrame = null, navigationVersion = 0;
let loadVersion = 0, searchVersion = 0, advancedGeneration = 0, advancedChunkFailed = false;
const originalScrollRestoration = history.scrollRestoration;
history.scrollRestoration = 'manual';
const people = ['marija', 'mirjana', 'ivanka', 'jakov', 'ivan', 'vicka', 'unattributed'];
const types = ['monthly', 'weekly', 'annual', 'special'];
const years = computed(() => [...new Set(catalog.value?.rows.map(r => r.date.slice(0, 4)) || [])].sort().reverse());
const months = computed(() => Array.from({ length:12 }, (_, n) => ({ value:String(n + 1).padStart(2, '0'),
  label:new Intl.DateTimeFormat(uiLang.value, { month:'long', timeZone:'UTC' }).format(new Date(Date.UTC(2020, n, 1))) })));
const hasActiveFilters = computed(() => Object.values(state.filters).some(Boolean));
const options = computed(() => searchOptions(state));
const latestRow = computed(() => latest.value[state.language]?.row);
const currentRow = computed(() => state.selectedId ? catalog.value?.byId.get(state.selectedId) : latestRow.value);
const currentRecord = computed(() => currentRow.value ? (state.selectedId ? catalog.value?.archives.get(state.language)?.get(currentRow.value.id) : latest.value[state.language]?.record) || null : null);
const availableLanguages = computed(() => languages.filter(l => currentRow.value && currentRow.value.availability[l.code] !== 'translation_not_present'));
const visibleRows = computed(() => catalog.value?.projectResults(search.value.ids.slice(0, state.limit), state.language) || []);
function formatDate(value) {
  return new Date(value + 'T12:00:00Z').toLocaleDateString(({ be:'be-BY',uk:'uk-UA',hr:'hr-HR',sk:'sk-SK',lv:'lv-LV',en:'en-GB' })[uiLang.value] || 'ru-RU',
    { day:'numeric', month:'long', year:'numeric', timeZone:'UTC' });
}
function applyTheme() {
  document.documentElement.dataset.theme = isDark.value ? 'dark' : 'light';
  vuetifyTheme.global.name.value = isDark.value ? 'marianDark' : 'marianLight';
  for (const icon of document.querySelectorAll('link[data-theme-icon]')) {
    icon.href = `${baseUrl}${icon.dataset[isDark.value ? 'dark' : 'light']}`;
  }
}
watch([theme, systemDark], applyTheme, { immediate: true });
watch(theme, value => save('medjugorje-theme', value));
watch(uiLang, value => { save('medjugorje-interface-language', value); document.documentElement.lang = value; }, { immediate:true });
watch(() => state.language, value => save('medjugorje-language', value));

function snapshot() { return JSON.parse(JSON.stringify(state)); }
function replaceEntry() {
  history.replaceState({ ...history.state, readerV2: true, snapshot: snapshot() }, '', hashFor(state));
}
function saveScroll() { state.scrollTop = window.scrollY; replaceEntry(); }
function onScroll() {
  if (scrollFrame !== null || restoring) return;
  scrollFrame = requestAnimationFrame(() => { scrollFrame = null; saveScroll(); });
}
async function ensureAdvanced(language) {
  const generation = advancedGeneration;
  if (!advancedPromise) advancedPromise = Promise.all([
    readData(manifest.value.metadata), import('./search/catalog.js'), import('./search/controller.js')
  ]).then(([model, { SearchCatalog }, module]) => {
    if (generation !== advancedGeneration) throw new Error('Obsolete snapshot');
    metadata = model; searchModule = module;
    catalog.value = markRaw(new SearchCatalog(metadata, archives));
  }).catch(error => { if (generation === advancedGeneration) { advancedPromise = null; advancedChunkFailed = error instanceof TypeError; } throw error; });
  await advancedPromise;
  if (generation !== advancedGeneration) throw new Error('Obsolete snapshot');
  if (!archives[language]) {
    const archive = await readData(manifest.value.latest[language].archive);
    if (generation !== advancedGeneration) throw new Error('Obsolete snapshot');
    archives[language] = archive;
    catalog.value.addLanguageArchive(language, archive);
  }
}
async function searchNow() {
  if (!manifest.value || !state.searchOpen) return;
  const version = ++searchVersion, language = state.language, opts = structuredClone(JSON.parse(JSON.stringify(options.value)));
  search.value = { status:'loading', ids:[], language };
  // Immediately invalidate an in-flight Worker result while the new corpus downloads.
  if (workerSearch) workerSearch.version++;
  try {
    await ensureAdvanced(language);
    if (version !== searchVersion || !state.searchOpen || language !== state.language) return;
    if (!workerSearch) workerSearch = new searchModule.WorkerSearch(metadata, archives, value => {
      if (value.language === state.language && state.searchOpen) search.value = value;
    });
    await workerSearch.run(language, opts);
    if (search.value.status === 'ready') performance.mark('search-ready');
  } catch (error) {
    if (version === searchVersion) search.value = { status:'error', ids:[], language, error:error.message };
  }
}
watch(options, () => { if (!restoring) { state.limit = 35; state.scrollTop = 0; } searchNow(); replaceEntry(); }, { deep: true });
watch(() => state.language, () => { load(); replaceEntry(); });
watch(() => state.limit, replaceEntry);
watch(() => state.filtersOpen, replaceEntry);

function startSearch() {
  if (advancedChunkFailed) { replaceEntry(); location.reload(); return; }
  workerSearch?.dispose(); workerSearch = null; searchNow();
}
async function restorePosition(version, y, focusId) {
  await nextTick();
  // Data/search can finish after popstate. Restore after the complete list exists.
  if (state.searchOpen && !state.selectedId && search.value.status === 'loading') return;
  requestAnimationFrame(() => {
    if (version !== navigationVersion) return;
    window.scrollTo({ top:y, behavior:'instant' });
    if (focusId) document.querySelector(`[data-id="${CSS.escape(focusId)}"]`)?.focus({ preventScroll:true });
    restoring = false;
  });
}
let restoreTarget = null;
function readRoute() {
  if (scrollFrame !== null) { cancelAnimationFrame(scrollFrame); scrollFrame = null; }
  const parsed = route(location.hash);
  const saved = history.state?.readerV2 && history.state.snapshot;
  const closingFilters = state.filtersOpen && !saved?.filtersOpen && parsed.searchOpen && !parsed.selectedId;
  const liveSearch = closingFilters ? snapshot() : null;
  restoring = true;
  navigationVersion++; filterClosePending = false;
  if (saved && hashFor(saved) === hashFor(parsed)) Object.assign(state, restoreReaderState(saved, state.language));
  else Object.assign(state, defaultState(state.language), parsed);
  if (liveSearch) { Object.assign(state, liveSearch, { filtersOpen:false }); replaceEntry(); }
  if (!validLanguage(state.language)) state.language = 'ru';
  restoreTarget = { version:navigationVersion, y:state.scrollTop, focusId:state.focusId };
  if (manifest.value && state.selectedId) load();
  else searchNow();
  restorePosition(restoreTarget.version, restoreTarget.y, restoreTarget.focusId);
}
watch(() => search.value.status, status => {
  if (restoring && status !== 'loading' && restoreTarget) restorePosition(restoreTarget.version, restoreTarget.y, restoreTarget.focusId);
});
function onHashChange() {
  // popstate already restored known entries; handle legacy links/external hash edits too.
  if (hashFor(state) !== hashFor(route(location.hash))) readRoute();
}
async function openSearch() {
  if (state.searchOpen) return;
  saveScroll();
  state.searchOpen = true; state.selectedId = null; state.scrollTop = 0;
  history.pushState({ readerV2:true, snapshot:snapshot(), returnHome:true }, '', '#search');
  searchNow();
  await nextTick(); window.scrollTo({ top:0, behavior:'instant' }); queryInput.value?.focus({ preventScroll:true });
}
function openMessage(id) {
  if (!catalog.value?.byId.has(id)) return;
  state.focusId = id; saveScroll();
  state.selectedId = id; state.scrollTop = 0;
  history.pushState({ readerV2:true, snapshot:snapshot(), returnReader:true }, '', hashFor(state));
  navigationVersion++;
  nextTick(() => { window.scrollTo({ top:0, behavior:'instant' }); document.querySelector('.reader-back')?.focus({ preventScroll:true }); });
}
function goBack() {
  if (history.state?.returnReader || history.state?.returnHome) history.back();
  else goHome();
}
function goHome() {
  searchVersion++;
  if (workerSearch) workerSearch.version++;
  Object.assign(state, defaultState(state.language));
  restoring = false; navigationVersion++;
  history.pushState({ readerV2:true, snapshot:snapshot() }, '', '#');
  nextTick(() => window.scrollTo({ top:0, behavior:'instant' }));
  searchNow();
}
function reset() {
  state.filters = emptyFilters(); state.limit = 35;
  nextTick(() => document.querySelector('#filter-toggle')?.focus({ preventScroll:true }));
}
function toggleFilters() {
  if (state.filtersOpen) { closeFilters(); return; }
  queryInput.value?.blur(); saveScroll(); state.filtersOpen = true;
  history.pushState({ readerV2:true, snapshot:snapshot(), filterSheet:true }, '', hashFor(state));
}
let filterClosePending = false;
function closeFilters() {
  if (!state.filtersOpen || filterClosePending) return;
  filterClosePending = true;
  if (history.state?.filterSheet) history.back();
  else { state.filtersOpen = false; filterClosePending = false; }
  nextTick(() => document.querySelector('#filter-toggle')?.focus({ preventScroll:true }));
}
function filterKeydown(event) {
  if (event.key !== 'Escape' || !state.filtersOpen) return;
  event.preventDefault(); event.stopImmediatePropagation(); closeFilters();
}
function resizeViewport() {
  const viewport = window.visualViewport;
  document.documentElement.style.setProperty('--keyboard-bottom', `${viewport ? Math.max(0, innerHeight - viewport.height - viewport.offsetTop) : 0}px`);
}
function submitSearch() { queryInput.value?.blur(); resultHeading.value?.focus({ preventScroll:true }); }
function selectLanguage(language) { state.language = language; }
function systemChanged(event) { systemDark.value = event.matches; }
async function load() {
  const version = ++loadVersion, language = state.language;
  busy.value = true; failed.value = false;
  searchVersion++;
  if (workerSearch) workerSearch.version++;
  try {
    if (!manifest.value) {
      const value = await readData('latest.json');
      if (value.schema_version !== 1 || !/^[a-f0-9]{24}$/.test(value.data_version)) throw new Error('Incompatible manifest');
      manifest.value = value;
    }
    if (!navigator.onLine) {
      try {
        const saved = await readData(`latest-for-${language}.json`, { refresh:true });
        if (saved.schema_version === 1 && saved.data_version !== manifest.value.data_version && version === loadVersion) {
          // Use the last successful whole snapshot of the requested language.
          advancedGeneration++;
          manifest.value = saved; latest.value = {}; catalog.value = null;
          advancedPromise = null; metadata = null; archives = {}; advancedChunkFailed = false;
          workerSearch?.dispose(); workerSearch = null;
        }
      } catch { /* An uncached language uses the normal explicit offline error below. */ }
    }
    const loadedManifest = manifest.value;
    const value = await readData(loadedManifest.latest[language].file);
    if (value.data_version !== loadedManifest.data_version || value.language !== language) throw new Error('Incompatible latest data');
    latest.value = { ...latest.value, [language]:value };
    navigator.serviceWorker?.ready.then(registration => {
      registration.active?.postMessage({ type:'COMMIT_MANIFEST', manifest:JSON.parse(JSON.stringify(loadedManifest)), language, latest:value });
    }).catch(() => {});
    if (state.selectedId) await ensureAdvanced(language);
    if (version !== loadVersion || language !== state.language) return;
    busy.value = false;
    await nextTick(); performance.mark('latest-visible');
    searchNow();
  } catch (error) {
    if (version === loadVersion) { console.error('Data unavailable:', error); failed.value = true; busy.value = false; }
  } finally {
    if (version === loadVersion && restoreTarget) restorePosition(restoreTarget.version, restoreTarget.y, restoreTarget.focusId);
  }
}
readRoute();
onMounted(() => {
  window.addEventListener('keydown', filterKeydown, true);
  darkSystem.addEventListener('change', systemChanged);
  window.addEventListener('online', networkChanged); window.addEventListener('offline', networkChanged);
  window.addEventListener('app-update-ready', foundUpdate);
  document.addEventListener('visibilitychange', checkDataUpdate);
  window.addEventListener('popstate', readRoute);
  window.addEventListener('hashchange', onHashChange);
  window.addEventListener('scroll', onScroll, { passive:true });
  window.visualViewport?.addEventListener('resize', resizeViewport);
  window.visualViewport?.addEventListener('scroll', resizeViewport); resizeViewport();
  load();
});
onUnmounted(() => {
  window.visualViewport?.removeEventListener('resize', resizeViewport);
  window.visualViewport?.removeEventListener('scroll', resizeViewport);
  window.removeEventListener('keydown', filterKeydown, true);
  loadVersion++; searchVersion++; workerSearch?.dispose();
  window.removeEventListener('online', networkChanged); window.removeEventListener('offline', networkChanged);
  window.removeEventListener('app-update-ready', foundUpdate);
  document.removeEventListener('visibilitychange', checkDataUpdate);
  window.removeEventListener('popstate', readRoute); window.removeEventListener('hashchange', onHashChange);
  window.removeEventListener('scroll', onScroll); darkSystem.removeEventListener('change', systemChanged);
  if (scrollFrame !== null) cancelAnimationFrame(scrollFrame);
  history.scrollRestoration = originalScrollRestoration;
});
</script>

<template>
  <v-app><div class="app-shell" :class="{ 'search-active':searchActive }">
    <a class="skip-link" href="#main-content" @click.prevent="$refs.mainContent.focus()">{{ T.read }}</a>
    <header class="topbar">
      <a href="#" class="brand" @click.prevent="goHome">
        <img class="brand-symbol" :src="`${baseUrl}logo-${isDark ? 'dark' : 'light'}-96.webp`"
          :srcset="`${baseUrl}logo-${isDark ? 'dark' : 'light'}-96.webp 96w, ${baseUrl}logo-${isDark ? 'dark' : 'light'}-192.webp 192w`"
          sizes="(max-width: 350px) 32px, (max-width: 600px) 36px, 48px"
          width="48" height="48" alt="" aria-hidden="true" />
        <span class="brand-copy"><strong>{{ T.brand }}</strong><span>{{ T.subtitle }}</span></span>
      </a>
      <div class="top-actions">
        <button id="language-button" class="language-shortcut" type="button" :aria-label="T.languageSettings"
          aria-haspopup="dialog" :aria-expanded="settingsOpen">{{ state.language.toUpperCase() }}</button>
        <button id="theme-button" class="theme-button" type="button" :aria-label="isDark ? T.light : T.dark"
          :title="isDark ? T.light : T.dark" @click="theme = isDark ? 'light' : 'dark'">
          <svg v-if="isDark" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M20 15.5A8.8 8.8 0 0 1 8.5 4 9 9 0 1 0 20 15.5Z"/></svg>
        </button>
        <button id="open-search" class="theme-button" type="button" :aria-label="T.search" @click="openSearch">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg>
        </button>
      </div>
    </header>
    <v-dialog v-model="settingsOpen" activator="#language-button" class="language-sheet" max-width="480" scrollable :aria-label="T.languageSettings">
      <v-card class="settings-dialog">
        <div class="sheet-handle" aria-hidden="true"></div>
        <v-card-title class="dialog-title">{{ T.languageSettings }}</v-card-title>
        <v-card-text>
          <label class="field"><span>{{ T.interfaceLanguage }}</span><select id="ui-language" v-model="uiLang"><option v-for="item in languages" :key="item.code" :value="item.code">{{ item.full }}</option></select></label>
          <label class="field"><span>{{ T.readingLanguage }}</span><select id="reading-language" v-model="state.language"><option v-for="item in languages" :key="item.code" :value="item.code">{{ item.full }}</option></select></label>
        </v-card-text>
        <v-card-actions><v-btn id="close-settings" variant="text" @click="settingsOpen = false">{{ T.close }}</v-btn></v-card-actions>
      </v-card>
    </v-dialog>

    <p v-if="!online" class="state-message" role="status">{{ T.offline }}</p>
    <p v-if="updateReady" class="state-message" role="status"><button class="plain-button" @click="applyUpdate">{{ T.updateApp }}</button></p>
    <main id="main-content" ref="mainContent" class="content" tabindex="-1">
      <div v-if="busy" class="state-message" role="status">{{ T.loading }}</div>
      <div v-else-if="failed" class="state-message" role="alert"><p>{{ T.error }}</p><button class="plain-button" @click="load">{{ T.retry }}</button></div>
      <template v-else>
        <button v-if="state.selectedId" class="reader-back" type="button" @click="goBack">← {{ state.searchOpen ? T.backToResults : T.back }}</button>
        <section v-else-if="state.searchOpen" class="search-surface expanded" :aria-label="T.search">
          <div class="search-screen-heading"><h1>{{ T.search }}</h1><button id="close-search" type="button" class="icon-button" :aria-label="T.closeSearch" @click="goBack">×</button></div>
          <form class="search-bar" role="search" @submit.prevent="submitSearch">
            <label for="query" class="sr-only">{{ T.search }}</label>
            <span class="search-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg></span>
            <input id="query" ref="queryInput" type="search" enterkeyhint="search" autocomplete="off" v-model="state.query" :placeholder="T.searchHint" />
            <button id="filter-toggle" type="button" class="icon-button filter-button" :class="{ active:hasActiveFilters }" :aria-label="T.filters + (hasActiveFilters ? ': ' + T.found + ' ' + Object.values(state.filters).filter(Boolean).length : '')" :aria-expanded="state.filtersOpen" aria-haspopup="dialog" aria-controls="search-filters" @click="toggleFilters">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h6m4 0h8M3 12h10m4 0h4M3 18h2m4 0h12M9 3v6m4 0v6M5 15v6"/></svg><span v-if="hasActiveFilters" class="filter-dot" aria-hidden="true"></span>
            </button>
          </form>
          <v-dialog :model-value="state.filtersOpen" @update:model-value="value => !value && closeFilters()" :close-on-back="false" class="language-sheet filter-sheet" max-width="480" scrollable :aria-label="T.filters">
            <v-card class="settings-dialog">
              <div class="sheet-handle" aria-hidden="true"></div>
              <v-card-title class="dialog-title">{{ T.filters }}</v-card-title>
              <v-card-text>
          <form id="search-filters" class="filters" @submit.prevent="closeFilters">
            <label class="field wide"><span>{{ T.visionary }}</span><select id="visionary" v-model="state.filters.visionary"><option value="">{{ T.allVisionaries }}</option><option v-for="person in people" :key="person" :value="person">{{ person === 'unattributed' ? T.unknown : T[person] }}</option></select></label>
            <label class="field wide"><span>{{ T.type }}</span><select id="message-type" v-model="state.filters.type"><option value="">{{ T.allTypes }}</option><option v-for="type in types" :key="type" :value="type">{{ T.messageTypes[type] }}</option></select></label>
            <label class="field"><span>{{ T.year }}</span><select id="year" v-model="state.filters.year"><option value="">{{ T.allYears }}</option><option v-for="year in years" :key="year" :value="year">{{ year }}</option></select></label>
            <label class="field"><span>{{ T.month }}</span><select id="month" v-model="state.filters.month"><option value="">{{ T.allMonths }}</option><option v-for="month in months" :key="month.value" :value="month.value">{{ month.label }}</option></select></label>
          </form>
              </v-card-text>
              <v-card-actions><v-btn v-if="hasActiveFilters" id="reset-search" variant="text" @click="reset">{{ T.reset }}</v-btn><v-btn id="close-filters" variant="text" @click="closeFilters">{{ T.close }}</v-btn></v-card-actions>
            </v-card>
          </v-dialog>
          <section v-if="state.searchOpen" id="search-results" :aria-busy="search.status === 'loading'">
            <h2 ref="resultHeading" class="result-count" tabindex="-1" aria-live="polite" aria-atomic="true">{{ T.found }} <span id="result-total">{{ search.status === 'ready' ? search.ids.length : '…' }}</span></h2>
            <p v-if="search.status === 'loading'" class="search-status" role="status">{{ T.searchLoading }}</p>
            <div v-else-if="search.status === 'error'" class="state-message" role="alert"><p>{{ T.searchError }}</p><button id="retry-search" class="plain-button" @click="startSearch">{{ T.retry }}</button></div>
            <template v-else>
              <p v-if="!search.ids.length" class="state-message" role="status">{{ T.noResults }}</p>
              <div v-else class="results-list">
                <ResultCard v-for="row in visibleRows" :key="row.id" :row="row" :t="T" :date="formatDate(row.metadata.date)" :query="state.query" :options="options" @open="openMessage" />
              </div>
              <button v-if="search.ids.length > state.limit" id="show-more" class="more-button" @click="state.limit += 35">{{ T.showMore }} ↓</button>
            </template>
          </section>
        </section>
        <template v-if="state.selectedId || !state.searchOpen">
          <MessageReader v-if="currentRow" :row="currentRow" :record="currentRecord" :date="formatDate(currentRow.date)" :latest="currentRow.id === latestRow?.id" :t="T" :language="state.language" :languages="availableLanguages" :archive-loaded="Boolean(latest[state.language]) || Boolean(catalog?.archives.has(state.language))" @language="selectLanguage" />
          <p v-else class="state-message" role="status">{{ T.notFound }}</p>
          <section v-if="!state.selectedId" class="recent" :aria-label="T.recent">
            <button class="more-button" id="open-archive" @click="openSearch">{{ T.recent }} ↓</button>
          </section>
        </template>
      </template>
    </main>
    <footer class="footer"><p>{{ T.footer }}</p><p>{{ T.notVerified }}</p></footer>
  </div></v-app>
</template>
