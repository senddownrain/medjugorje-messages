<script setup>
import { computed, markRaw, nextTick, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue';
import { useTheme } from 'vuetify';
import metadata from '../derived/search-metadata.json';
import { SearchCatalog } from './search/catalog.js';
import { WorkerSearch } from './search/worker-search.js';
import { languages, translations } from './ui/translations.js';
import { defaultState, emptyFilters, hashFor, route, searchOptions, restoreReaderState } from './ui/reader-state.js';
import ResultCard from './ui/ResultCard.vue';
import MessageReader from './ui/MessageReader.vue';

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
const settingsOpen = ref(false), queryInput = ref(null), resultHeading = ref(null), searchScroller = ref(null);
const searchSheetOpen = computed(() => state.searchOpen && !state.selectedId);
let focusSearchOnOpen = false;
const busy = ref(true), failed = ref(false);
const catalog = shallowRef(null);
const search = shallowRef({ status: 'loading', ids: [], language: state.language });
let archives = {}, workerSearch, restoring = false, scrollFrame = null, navigationVersion = 0;
const originalScrollRestoration = history.scrollRestoration;
history.scrollRestoration = 'manual';
const people = ['marija', 'mirjana', 'ivanka', 'jakov', 'ivan', 'vicka', 'unattributed'];
const types = ['monthly', 'weekly', 'annual', 'special'];
const years = [...new Set(metadata.messages.map(r => r.date.slice(0, 4)))].sort().reverse();
const months = computed(() => Array.from({ length:12 }, (_, n) => ({ value:String(n + 1).padStart(2, '0'),
  label:new Intl.DateTimeFormat(uiLang.value, { month:'long', timeZone:'UTC' }).format(new Date(Date.UTC(2020, n, 1))) })));
const hasActiveFilters = computed(() => Object.values(state.filters).some(Boolean));
const options = computed(() => searchOptions(state));
const latestRow = computed(() => catalog.value?.rows.find(r => r.availability[state.language] === 'with_text'));
const currentRow = computed(() => state.selectedId ? catalog.value?.byId.get(state.selectedId) : latestRow.value);
const currentRecord = computed(() => currentRow.value ? catalog.value?.archives.get(state.language)?.get(currentRow.value.id) || null : null);
const availableLanguages = computed(() => languages.filter(l => currentRow.value && currentRow.value.availability[l.code] !== 'translation_not_present'));
const visibleRows = computed(() => catalog.value?.projectResults(search.value.ids.slice(0, state.limit), state.language) || []);
const recentRows = computed(() => catalog.value?.projectResults(catalog.value.rows.filter(r =>
  r.availability[state.language] !== 'translation_not_present' && r.id !== latestRow.value?.id).slice(0, 4).map(r => r.id), state.language) || []);
function formatDate(value) {
  return new Date(value + 'T12:00:00Z').toLocaleDateString(({ be:'be-BY',uk:'uk-UA',hr:'hr-HR',sk:'sk-SK',lv:'lv-LV',en:'en-GB' })[uiLang.value] || 'ru-RU',
    { day:'numeric', month:'long', year:'numeric', timeZone:'UTC' });
}
function applyTheme() {
  document.documentElement.dataset.theme = isDark.value ? 'dark' : 'light';
  vuetifyTheme.global.name.value = isDark.value ? 'marianDark' : 'marianLight';
}
watch([theme, systemDark], applyTheme, { immediate: true });
watch(theme, value => save('medjugorje-theme', value));
watch(uiLang, value => { save('medjugorje-interface-language', value); document.documentElement.lang = value; }, { immediate:true });
watch(() => state.language, value => save('medjugorje-language', value));

function snapshot() { return JSON.parse(JSON.stringify(state)); }
function replaceEntry() {
  history.replaceState({ ...history.state, readerV2: true, snapshot: snapshot() }, '', hashFor(state));
}
function saveScroll() { state.scrollTop = searchSheetOpen.value ? searchScroller.value?.scrollTop || 0 : window.scrollY; replaceEntry(); }
function onScroll() {
  if (scrollFrame !== null || restoring) return;
  scrollFrame = requestAnimationFrame(() => { scrollFrame = null; saveScroll(); });
}
function searchNow() { if (workerSearch) workerSearch.run(state.language, options.value); }
watch(options, () => { if (!restoring) { state.limit = 35; state.scrollTop = 0; nextTick(() => searchScroller.value?.scrollTo({top:0,behavior:'instant'})); } searchNow(); replaceEntry(); }, { deep: true });
watch(() => state.language, () => { searchNow(); replaceEntry(); });
watch(() => state.limit, replaceEntry);
watch(() => state.filtersOpen, replaceEntry);

function startSearch() {
  workerSearch?.dispose();
  try {
    workerSearch = new WorkerSearch(metadata, archives, value => { search.value = value; });
    searchNow();
  } catch (error) { search.value = { status:'error', ids:[], error:error.message, language:state.language }; }
}
async function restorePosition(version, y, focusId) {
  await nextTick();
  // Data/search can finish after popstate. Restore after the complete list exists.
  if (state.searchOpen && !state.selectedId && search.value.status === 'loading') return;
  requestAnimationFrame(() => {
    if (version !== navigationVersion) return;
    if (searchSheetOpen.value) {
      if (!searchScroller.value) return;
      searchScroller.value.scrollTo({ top:y, behavior:'instant' });
    } else window.scrollTo({ top:y, behavior:'instant' });
    if (focusId) (searchSheetOpen.value ? searchScroller.value : document)?.querySelector(`[data-id="${CSS.escape(focusId)}"]`)?.focus({ preventScroll:true });
    restoring = false;
  });
}
let restoreTarget = null;
function readRoute() {
  if (scrollFrame !== null) { cancelAnimationFrame(scrollFrame); scrollFrame = null; }
  const parsed = route(location.hash);
  const saved = history.state?.readerV2 && history.state.snapshot;
  restoring = true;
  navigationVersion++;
  if (saved && hashFor(saved) === hashFor(parsed)) Object.assign(state, restoreReaderState(saved, state.language));
  else Object.assign(state, defaultState(state.language), parsed);
  if (!validLanguage(state.language)) state.language = 'ru';
  restoreTarget = { version:navigationVersion, y:state.scrollTop, focusId:state.focusId };
  searchNow();
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
  focusSearchOnOpen = true;
  state.filtersOpen = false;
  state.searchOpen = true; state.selectedId = null; state.scrollTop = 0;
  history.pushState({ readerV2:true, snapshot:snapshot(), returnHome:true }, '', '#search');
  searchNow();
  await nextTick(); searchScroller.value?.scrollTo({ top:0, behavior:'instant' });
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
function toggleFilters() { state.filtersOpen = !state.filtersOpen; }
function sheetVisibility(value) { if (!value && searchSheetOpen.value) goBack(); }
function sheetEntered() {
  if (focusSearchOnOpen) { queryInput.value?.focus({ preventScroll:true }); focusSearchOnOpen = false; }
  if (restoring && restoreTarget) restorePosition(restoreTarget.version, restoreTarget.y, restoreTarget.focusId);
}
function settingsLeft() { if (searchSheetOpen.value) document.querySelector('#search-language-button')?.focus({ preventScroll:true }); }
function sheetLeft() {
  if (state.selectedId) document.querySelector('.reader-back')?.focus({ preventScroll:true });
  else document.querySelector('#search-button')?.focus({ preventScroll:true });
}
function submitSearch() { queryInput.value?.blur(); resultHeading.value?.focus({ preventScroll:true }); }
function selectLanguage(language) { state.language = language; }
function systemChanged(event) { systemDark.value = event.matches; }
async function load() {
  busy.value = true; failed.value = false;
  workerSearch?.dispose(); workerSearch = null;
  try {
    // Keep stage B's existing index + seven-language loading policy. Stage D owns changes.
    const required = ['index', 'ru', 'be', 'uk'];
    const optional = ['hr', 'en', 'sk', 'lv'];
    async function read(name, allowMissing = false) {
      const response = await fetch(import.meta.env.BASE_URL + 'data/' + name + '.json');
      if (!response.ok) {
        if (allowMissing && response.status === 404) return null;
        throw new Error(name + ': HTTP ' + response.status);
      }
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('json')) {
        if (allowMissing) return null;
        throw new Error('Expected JSON for ' + name + ', got ' + contentType);
      }
      const result = await response.json();
      if (!result || typeof result !== 'object') throw new Error('Invalid JSON: ' + name);
      return result;
    }
    const first = await Promise.all(required.map(code => read(code)));
    const extras = await Promise.all(optional.map(code => read(code, true)));
    if (!Array.isArray(first[0].messages)) throw new Error('Invalid data index');
    const languageFiles = [...first.slice(1), ...extras];
    archives = Object.fromEntries([...required.slice(1), ...optional].map((code,n) => [code,languageFiles[n]])
      .filter(([,file]) => file && Array.isArray(file.messages)));
    catalog.value = markRaw(new SearchCatalog(metadata, archives));
    startSearch();
  } catch (error) { console.error('Archive unavailable:', error); failed.value = true; }
  finally {
    busy.value = false;
    if (restoreTarget) restorePosition(restoreTarget.version, restoreTarget.y, restoreTarget.focusId);
  }
}
readRoute();
onMounted(() => {
  darkSystem.addEventListener('change', systemChanged);
  window.addEventListener('popstate', readRoute);
  window.addEventListener('hashchange', onHashChange);
  window.addEventListener('scroll', onScroll, { passive:true });
  load();
});
onUnmounted(() => {
  workerSearch?.dispose();
  window.removeEventListener('popstate', readRoute); window.removeEventListener('hashchange', onHashChange);
  window.removeEventListener('scroll', onScroll); darkSystem.removeEventListener('change', systemChanged);
  if (scrollFrame !== null) cancelAnimationFrame(scrollFrame);
  history.scrollRestoration = originalScrollRestoration;
});
</script>

<template>
  <v-app><div class="app-shell">
    <a class="skip-link" href="#main-content" @click.prevent="$refs.mainContent.focus()">{{ T.read }}</a>
    <header class="topbar">
      <a href="#" class="brand" @click.prevent="goHome">
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
        <button id="search-button" class="search-button" type="button" :aria-label="T.search" aria-haspopup="dialog" :aria-expanded="searchSheetOpen" :disabled="busy || failed" @click="openSearch">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg>
        </button>
      </div>
    </header>
    <v-dialog v-model="settingsOpen" activator="#language-button" class="language-sheet" max-width="480" scrollable :aria-label="T.languageSettings" @after-leave="settingsLeft">
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

    <v-dialog :model-value="searchSheetOpen" class="search-sheet" max-width="720" :aria-label="T.search" @update:model-value="sheetVisibility" @after-enter="sheetEntered" @after-leave="sheetLeft">
      <v-card class="search-panel">
        <div class="sheet-handle" aria-hidden="true"></div>
        <div class="search-sheet-heading"><h2>{{ T.search }}</h2><div class="sheet-actions"><button id="search-language-button" class="language-shortcut" type="button" :aria-label="T.languageSettings" aria-haspopup="dialog" @click="settingsOpen = true">{{ state.language.toUpperCase() }}</button><button id="close-search" class="icon-button" type="button" :aria-label="T.closeSearch" @click="goBack">×</button></div></div>
        <div v-if="busy" class="state-message" role="status">{{ T.loading }}</div>
        <div v-else-if="failed" class="state-message" role="alert"><p>{{ T.error }}</p><button class="plain-button" @click="load">{{ T.retry }}</button></div>
        <section v-else class="search-surface" :aria-label="T.search">
          <form class="search-bar" role="search" @submit.prevent="submitSearch">
            <label for="query" class="sr-only">{{ T.search }}</label>
            <span class="search-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></svg></span>
            <input id="query" ref="queryInput" type="search" enterkeyhint="search" autocomplete="off" v-model="state.query" :placeholder="T.searchHint" />
            <button id="filter-toggle" class="filter-icon" type="button" :aria-label="T.filters + (hasActiveFilters ? ': ' + T.filtersActive : '')" :aria-expanded="state.filtersOpen" aria-controls="search-filters" @click="toggleFilters">
              <svg data-icon="sliders-horizontal" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 4h-7M10 4H3M21 12h-9M8 12H3M21 20h-3M14 20H3M14 2v4M8 10v4M18 18v4"/></svg>
              <span v-if="hasActiveFilters" class="filter-indicator" data-active-filters aria-hidden="true"></span>
            </button>
          </form>
          <div ref="searchScroller" id="search-scroll" class="search-scroll" @scroll.passive="onScroll">
          <div v-if="hasActiveFilters" class="search-tools"><button id="reset-search" type="button" @click="reset">{{ T.reset }}</button></div>
          <form v-if="state.filtersOpen" id="search-filters" class="filters" @submit.prevent="submitSearch">
            <label class="field wide"><span>{{ T.visionary }}</span><select id="visionary" v-model="state.filters.visionary"><option value="">{{ T.allVisionaries }}</option><option v-for="person in people" :key="person" :value="person">{{ person === 'unattributed' ? T.unknown : T[person] }}</option></select></label>
            <label class="field wide"><span>{{ T.type }}</span><select id="message-type" v-model="state.filters.type"><option value="">{{ T.allTypes }}</option><option v-for="type in types" :key="type" :value="type">{{ T.messageTypes[type] }}</option></select></label>
            <label class="field"><span>{{ T.year }}</span><select id="year" v-model="state.filters.year"><option value="">{{ T.allYears }}</option><option v-for="year in years" :key="year" :value="year">{{ year }}</option></select></label>
            <label class="field"><span>{{ T.month }}</span><select id="month" v-model="state.filters.month"><option value="">{{ T.allMonths }}</option><option v-for="month in months" :key="month.value" :value="month.value">{{ month.label }}</option></select></label>
          </form>
          <section v-if="state.searchOpen" id="search-results" :aria-busy="search.status === 'loading'">
            <h1 ref="resultHeading" class="result-count" tabindex="-1" aria-live="polite" aria-atomic="true">{{ T.found }} <span id="result-total">{{ search.status === 'ready' ? search.ids.length : '…' }}</span></h1>
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
          </div>
        </section>
      </v-card>
    </v-dialog>

    <main id="main-content" ref="mainContent" class="content" tabindex="-1">
      <div v-if="busy" class="state-message" role="status">{{ T.loading }}</div>
      <div v-else-if="failed" class="state-message" role="alert"><p>{{ T.error }}</p><button class="plain-button" @click="load">{{ T.retry }}</button></div>
      <template v-else>
        <button v-if="state.selectedId" class="reader-back" type="button" @click="goBack">← {{ state.searchOpen ? T.backToResults : T.back }}</button>
          <MessageReader v-if="currentRow" :row="currentRow" :record="currentRecord" :date="formatDate(currentRow.date)" :latest="currentRow.id === latestRow?.id" :t="T" :language="state.language" :languages="availableLanguages" :archive-loaded="catalog.archives.has(state.language)" @language="selectLanguage" />
          <p v-else class="state-message" role="status">{{ T.notFound }}</p>
          <section v-if="!state.selectedId" class="recent" :aria-label="T.recent">
            <h2>{{ T.recent }}</h2><ResultCard v-for="row in recentRows" :key="row.id" :row="row" :t="T" :date="formatDate(row.metadata.date)" query="" :options="{}" @open="openMessage" />
          </section>
      </template>
    </main>
    <footer class="footer"><p>{{ T.footer }}</p><p>{{ T.notVerified }}</p></footer>
  </div></v-app>
</template>
