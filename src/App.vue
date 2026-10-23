<script setup>
import { computed, onMounted, ref, watch } from 'vue';

const languages = [
  { code: 'ru', short: 'RU', full: 'Русский' },
  { code: 'be', short: 'BY', full: 'Беларуская' },
  { code: 'uk', short: 'UA', full: 'Українська' }
];
const translations = {
  ru: {
    brand: 'Царица Мира', subtitle: 'Послания из Меджугорья',
    latest: 'Последнее', archive: 'Архив', latestMonthly: 'Последнее ежемесячное послание',
    date: 'Дата', year: 'Год', type: 'Тип', visionary: 'Визионер', search: 'Поиск',
    allYears: 'Все годы', allTypes: 'Все типы', allVisionaries: 'Все',
    anyDate: 'Любая дата', searchPlaceholder: 'Искать по тексту или названию',
    monthly: 'Ежемесячное', weekly: 'Еженедельное', annual: 'Ежегодное',
    special: 'Особое', other: 'Другое',
    marija: 'Мария', mirjana: 'Мирьяна', ivanka: 'Иванка', jakov: 'Яков', ivan: 'Иван',
    unknown: 'Не указан', noText: 'Текст послания отсутствует в сохранённом архиве.',
    unavailable: 'Перевод этого послания отсутствует на выбранном языке.',
    available: 'Есть на других языках', found: 'Найдено посланий',
    showMore: 'Показать ещё', noResults: 'Не найдено посланий с такими параметрами.',
    reset: 'Сбросить фильтры', original: 'Источник', back: 'Назад к архиву',
    note: 'Примечание источника', read: 'Читать послание', loading: 'Загружаем архив…',
    error: 'Не удалось загрузить архив. Проверьте подключение и повторите попытку.',
    retry: 'Повторить', footer: 'Переводы предоставлены общиной. Тексты сверяются с источником.',
    light: 'Светлая тема', dark: 'Тёмная тема', stored: 'Архив доступен для чтения офлайн после первой загрузки.',
    notVerified: 'Исследовательский архив — данные проходят проверку'
  },
  be: {
    brand: 'Каралева Супакою', subtitle: 'Пасланні з Меджугор’я',
    latest: 'Апошняе', archive: 'Архіў', latestMonthly: 'Апошняе штомесячнае пасланне',
    date: 'Дата', year: 'Год', type: 'Тып', visionary: 'Візіянер', search: 'Пошук',
    allYears: 'Усе гады', allTypes: 'Усе тыпы', allVisionaries: 'Усе',
    anyDate: 'Любая дата', searchPlaceholder: 'Пошук у тэкстах і назвах',
    monthly: 'Штомесячнае', weekly: 'Штотыднёвае', annual: 'Штогадовае',
    special: 'Асаблівае', other: 'Іншае',
    marija: 'Марыя', mirjana: 'Мір’яна', ivanka: 'Іванка', jakov: 'Якаў', ivan: 'Іван',
    unknown: 'Не пазначаны', noText: 'Тэкст паслання адсутнічае ў захаваным архіве.',
    unavailable: 'Перакладу гэтага паслання на выбраную мову няма.',
    available: 'Даступныя мовы', found: 'Знойдзена пасланняў',
    showMore: 'Паказаць яшчэ', noResults: 'Пасланні з такімі параметрамі не знойдзены.',
    reset: 'Скінуць фільтры', original: 'Крыніца', back: 'Назад да архіва',
    note: 'Заўвага крыніцы', read: 'Чытаць пасланне', loading: 'Загружаем архіў…',
    error: 'Не ўдалося загрузіць архіў. Праверце злучэнне і паўтарыце.',
    retry: 'Паўтарыць', footer: 'Пераклады прадастаўлены супольнасцю. Тэксты звяраюцца з крыніцай.',
    light: 'Светлая тэма', dark: 'Цёмная тэма', stored: 'Пасля першай загрузкі архіў будзе даступны афлайн.',
    notVerified: 'Даследчы архіў — даныя яшчэ правяраюцца'
  },
  uk: {
    brand: 'Цариця Миру', subtitle: 'Послання з Меджугор’я',
    latest: 'Останнє', archive: 'Архів', latestMonthly: 'Останнє щомісячне послання',
    date: 'Дата', year: 'Рік', type: 'Тип', visionary: 'Візіонер', search: 'Пошук',
    allYears: 'Усі роки', allTypes: 'Усі типи', allVisionaries: 'Усі',
    anyDate: 'Будь-яка дата', searchPlaceholder: 'Пошук у текстах і назвах',
    monthly: 'Щомісячне', weekly: 'Щотижневе', annual: 'Щорічне',
    special: 'Особливе', other: 'Інше',
    marija: 'Марія', mirjana: 'Мір’яна', ivanka: 'Іванка', jakov: 'Яків', ivan: 'Іван',
    unknown: 'Не вказано', noText: 'Текст послання відсутній у збереженому архіві.',
    unavailable: 'Переклад цього послання вибраною мовою відсутній.',
    available: 'Доступні мови', found: 'Знайдено послань',
    showMore: 'Показати ще', noResults: 'Послань за такими параметрами не знайдено.',
    reset: 'Скинути фільтри', original: 'Джерело', back: 'Назад до архіву',
    note: 'Примітка джерела', read: 'Читати послання', loading: 'Завантажуємо архів…',
    error: 'Не вдалося завантажити архів. Перевірте підключення та повторіть.',
    retry: 'Повторити', footer: 'Переклади надані спільнотою. Тексти звіряються з джерелом.',
    light: 'Світла тема', dark: 'Темна тема', stored: 'Після першого завантаження архів доступний офлайн.',
    notVerified: 'Дослідницький архів — дані ще перевіряються'
  }
};
function initialSetting(key, fallback) {
  try { return localStorage.getItem(key) || fallback; }
  catch { return fallback; }
}
const lang = ref(['ru', 'be', 'uk'].includes(initialSetting('medjugorje-language', 'ru'))
  ? initialSetting('medjugorje-language', 'ru') : 'ru');
const theme = ref(initialSetting('medjugorje-theme', 'auto'));
const T = computed(() => translations[lang.value]);
const section = ref('latest');
const selectedId = ref(null);
const index = ref([]);
const localized = ref({});
const busy = ref(true);
const failed = ref(false);
const year = ref('all');
const category = ref('all');
const visionary = ref('all');
const exactDay = ref('');
const query = ref('');
const limit = ref(35);
const knownVisionaries = ['marija', 'mirjana', 'ivanka', 'jakov', 'ivan'];
const knownCategories = ['monthly', 'weekly', 'annual', 'special', 'other'];

function applyTheme(value) {
  document.documentElement.dataset.theme = value === 'auto' ? '' : value;
}
watch(lang, value => {
  try { localStorage.setItem('medjugorje-language', value); } catch { /* private browser mode */ }
  document.documentElement.lang = value === 'be' ? 'be' : value;
  limit.value = 35;
});
watch(theme, value => {
  try { localStorage.setItem('medjugorje-theme', value); } catch { /* private browser mode */ }
  applyTheme(value);
});

function formatDate(value) {
  if (!value) return '';
  const locale = lang.value === 'be' ? 'be-BY' : lang.value === 'uk' ? 'uk-UA' : 'ru-RU';
  return new Date(value + 'T12:00:00Z').toLocaleDateString(locale,
    { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
}
function typename(type) { return T.value[type] || T.value.other; }
function visionaryName(value) { return T.value[value] || (value || T.value.unknown); }
function getTranslation(id) { return localized.value[lang.value]?.[id] || null; }
const latestRow = computed(() => index.value.find(row =>
  row.type === 'monthly' && row.translations?.[lang.value]?.has_text));
const currentRow = computed(() => selectedId.value
  ? index.value.find(row => row.id === selectedId.value) : latestRow.value);
const currentTranslation = computed(() => currentRow.value
  ? getTranslation(currentRow.value.id) : null);
const availableLanguages = computed(() => languages.filter(item =>
  currentRow.value?.translations?.[item.code]?.has_text));
const years = computed(() => Array.from(new Set(
  index.value.filter(row => row.translations?.[lang.value]?.present).map(row => row.date.slice(0, 4))
)).sort((a, b) => b.localeCompare(a)));
const results = computed(() => index.value.filter(row => {
  if (!row.translations?.[lang.value]?.present) return false;
  if (year.value !== 'all' && !row.date.startsWith(year.value)) return false;
  if (category.value !== 'all' && row.type !== category.value) return false;
  if (visionary.value !== 'all' && row.visionary !== visionary.value) return false;
  if (exactDay.value && row.date !== exactDay.value) return false;
  const text = query.value.trim().toLocaleLowerCase();
  if (text) {
    const record = getTranslation(row.id);
    if (!(record?.title || '').toLocaleLowerCase().includes(text) &&
        !(record?.text || '').toLocaleLowerCase().includes(text)) return false;
  }
  return true;
}));
const shownResults = computed(() => results.value.slice(0, limit.value));
function clearFilters() {
  year.value = 'all'; category.value = 'all'; visionary.value = 'all';
  exactDay.value = ''; query.value = ''; limit.value = 35;
}
function selectSection(name) {
  selectedId.value = null;
  section.value = name;
  history.replaceState({}, '', location.pathname + location.search + '#' + name);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function openMessage(id) {
  section.value = 'archive';
  selectedId.value = id;
  location.hash = 'message/' + encodeURIComponent(id);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function readHash() {
  const hash = decodeURIComponent(location.hash.slice(1));
  if (hash.startsWith('message/')) {
    selectedId.value = hash.slice(8);
    section.value = 'archive';
  } else {
    selectedId.value = null;
    section.value = hash === 'archive' ? 'archive' : 'latest';
  }
}
async function load() {
  busy.value = true; failed.value = false;
  try {
    const files = await Promise.all(['index', 'ru', 'be', 'uk'].map(async name => {
      const response = await fetch(import.meta.env.BASE_URL + 'data/' + name + '.json');
      if (!response.ok) throw new Error(name + ': HTTP ' + response.status);
      return await response.json();
    }));
    if (!Array.isArray(files[0].messages)) throw new Error('Invalid data index');
    index.value = [...files[0].messages].sort((a, b) =>
      b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
    localized.value = Object.fromEntries(
      ['ru', 'be', 'uk'].map((code, n) =>
        [code, Object.fromEntries(files[n + 1].messages.map(row => [row.id, row]))])
    );
    readHash();
  } catch (error) {
    console.error('Archive unavailable:', error);
    failed.value = true;
  } finally {
    busy.value = false;
  }
}
onMounted(() => {
  applyTheme(theme.value);
  document.documentElement.lang = lang.value;
  window.addEventListener('hashchange', readHash);
  load();
});
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand" @click="selectSection('latest')" role="button" tabindex="0" @keydown.enter="selectSection('latest')">
        <span class="brand-symbol" aria-hidden="true">✳</span>
        <span class="brand-copy">
          <strong>{{ T.brand }}</strong>
          <span>{{ T.subtitle }}</span>
        </span>
      </div>
      <div class="top-actions">
        <div class="language-picker" aria-label="Language">
          <button v-for="item in languages" :key="item.code" type="button"
            :class="{ active: lang === item.code }"
            :aria-label="item.full" :aria-pressed="lang === item.code"
            @click="lang = item.code">{{ item.short }}</button>
        </div>
        <button class="theme-button" type="button"
          :title="theme === 'dark' ? T.light : T.dark"
          :aria-label="theme === 'dark' ? T.light : T.dark"
          @click="theme = theme === 'dark' ? 'light' : 'dark'">
          <span aria-hidden="true">{{ theme === 'dark' ? '☼' : '☾' }}</span>
        </button>
      </div>
    </header>

    <main class="content">
      <nav class="main-nav" :aria-label="T.subtitle">
        <button type="button" :class="{ active: section === 'latest' && !selectedId }"
          @click="selectSection('latest')">{{ T.latest }}</button>
        <button type="button" :class="{ active: section === 'archive' }"
          @click="selectSection('archive')">{{ T.archive }}</button>
      </nav>

      <div v-if="busy" class="state-message" role="status">{{ T.loading }}</div>
      <div v-else-if="failed" class="state-message" role="alert">
        <p>{{ T.error }}</p>
        <button class="plain-button" @click="load">{{ T.retry }}</button>
      </div>

      <template v-else>
        <template v-if="section === 'latest' || selectedId">
          <button v-if="selectedId" type="button" class="return-link"
            @click="selectSection('archive')">← {{ T.back }}</button>
          <article v-if="currentRow" class="reading">
            <div class="reading-kicker">
              <span class="ornament" aria-hidden="true">✳</span>
              {{ selectedId ? typename(currentRow.type) : T.latestMonthly }}
            </div>
            <h1>{{ formatDate(currentRow.date) }}</h1>
            <div class="reading-meta">
              <span>{{ typename(currentRow.type) }}</span>
              <span class="meta-dot" aria-hidden="true">·</span>
              <span>{{ visionaryName(currentRow.visionary) }}</span>
            </div>
            <div class="reading-divider" aria-hidden="true"><span>✧</span></div>
            <div v-if="currentTranslation?.text" class="message-body">
              <template v-if="currentTranslation.segments?.length">
                <template v-for="(segment, n) in currentTranslation.segments" :key="n">
                  <p v-if="segment.kind === 'message'" class="message-text">{{ segment.text }}</p>
                  <p v-else class="context-text"><span>{{ T.note }} · </span>{{ segment.text }}</p>
                </template>
              </template>
              <p v-else class="message-text">{{ currentTranslation.text }}</p>
            </div>
            <p v-else class="empty-text">
              {{ currentTranslation ? T.noText : T.unavailable }}
            </p>
            <div v-if="availableLanguages.length > 0 && (selectedId || !currentTranslation?.text)"
              class="other-languages">
              <span>{{ T.available }}:</span>
              <button v-for="item in availableLanguages" :key="item.code" type="button"
                :class="{ active: lang === item.code }" @click="lang = item.code">
                {{ item.short }}
              </button>
            </div>
            <div class="reading-actions">
              <a v-if="currentTranslation?.source_url" :href="currentTranslation.source_url"
                target="_blank" rel="noopener noreferrer">{{ T.original }} ↗</a>
              <button v-if="!selectedId" type="button" @click="selectSection('archive')">
                {{ T.archive }} →
              </button>
            </div>
          </article>
          <p v-else class="state-message">{{ T.noResults }}</p>
        </template>

        <section v-else-if="section === 'archive'" class="archive">
          <header class="archive-heading">
            <span class="eyebrow">{{ T.subtitle }}</span>
            <h1>{{ T.archive }}</h1>
          </header>
          <form class="filters" @submit.prevent>
            <label>
              <span>{{ T.year }}</span>
              <select v-model="year" @change="limit = 35">
                <option value="all">{{ T.allYears }}</option>
                <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
              </select>
            </label>
            <label>
              <span>{{ T.date }}</span>
              <input type="date" v-model="exactDay" @input="limit = 35" />
            </label>
            <label>
              <span>{{ T.type }}</span>
              <select v-model="category" @change="limit = 35">
                <option value="all">{{ T.allTypes }}</option>
                <option v-for="type in knownCategories" :key="type" :value="type">{{ typename(type) }}</option>
              </select>
            </label>
            <label>
              <span>{{ T.visionary }}</span>
              <select v-model="visionary" @change="limit = 35">
                <option value="all">{{ T.allVisionaries }}</option>
                <option v-for="name in knownVisionaries" :key="name" :value="name">{{ visionaryName(name) }}</option>
              </select>
            </label>
            <label class="search-field">
              <span>{{ T.search }}</span>
              <input type="search" v-model="query" :placeholder="T.searchPlaceholder"
                @input="limit = 35" />
            </label>
          </form>
          <div class="result-count">
            <span>{{ T.found }}: <strong>{{ results.length }}</strong></span>
            <button type="button" @click="clearFilters">{{ T.reset }}</button>
          </div>
          <div v-if="results.length === 0" class="state-message">{{ T.noResults }}</div>
          <div v-else class="results-list">
            <button v-for="row in shownResults" :key="row.id"
              class="result-item" type="button" @click="openMessage(row.id)">
              <span class="result-date">{{ formatDate(row.date) }}</span>
              <span class="result-caption">{{ typename(row.type) }} · {{ visionaryName(row.visionary) }}</span>
              <span v-if="!row.translations[lang].has_text" class="record-warning">{{ T.noText }}</span>
              <span class="result-arrow" aria-hidden="true">↗</span>
            </button>
          </div>
          <button v-if="results.length > shownResults.length" type="button"
            class="more-button" @click="limit += 35">{{ T.showMore }} ↓</button>
        </section>
      </template>
    </main>

    <footer class="footer">
      <div class="footer-mark" aria-hidden="true">✳</div>
      <p>{{ T.footer }}</p>
      <p class="footnote">{{ T.notVerified }}</p>
      <p class="offline-note">{{ T.stored }}</p>
    </footer>
  </div>
</template>
