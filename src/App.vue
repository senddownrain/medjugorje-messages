<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useTheme } from 'vuetify';

const languages = [
  { code: 'ru', short: 'RU', full: 'Русский' },
  { code: 'be', short: 'BY', full: 'Беларуская' },
  { code: 'uk', short: 'UA', full: 'Українська' },
  { code: 'hr', short: 'HR', full: 'Hrvatski' },
  { code: 'en', short: 'EN', full: 'English' },
  { code: 'sk', short: 'SK', full: 'Slovenčina' },
  { code: 'lv', short: 'LV', full: 'Latviešu' }
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

const extraTranslations = {
  en: {
    brand: 'Queen of Peace', subtitle: 'Messages from Medjugorje',
    latest: 'Latest', archive: 'Archive', latestMonthly: 'Latest monthly message',
    date: 'Date', year: 'Year', type: 'Type', visionary: 'Visionary', search: 'Search',
    allYears: 'All years', allTypes: 'All types', allVisionaries: 'All',
    anyDate: 'Any date', searchPlaceholder: 'Search titles and messages',
    monthly: 'Monthly', weekly: 'Weekly', annual: 'Annual', special: 'Special', other: 'Other',
    marija: 'Marija', mirjana: 'Mirjana', ivanka: 'Ivanka', jakov: 'Jakov', ivan: 'Ivan',
    unknown: 'Not specified', noText: 'No message text in this archived entry.',
    unavailable: 'Translation unavailable in this language.',
    available: 'Available in', found: 'Messages found', showMore: 'Show more',
    noResults: 'No matching messages.', reset: 'Clear filters', original: 'Source',
    back: 'Back to archive', note: 'Source note', read: 'Read message',
    loading: 'Loading archive…', error: 'Could not load the archive.',
    retry: 'Try again', footer: 'Translations provided by the community; texts are under review.',
    light: 'Light theme', dark: 'Dark theme',
    stored: 'After the first successful load, you can read offline.',
    notVerified: 'Research archive — editorial verification in progress'
  },
  hr: {
    brand: 'Kraljica Mira', subtitle: 'Poruke iz Međugorja', latest: 'Najnovija',
    archive: 'Arhiva', latestMonthly: 'Najnovija mjesečna poruka',
    date: 'Datum', year: 'Godina', type: 'Vrsta', visionary: 'Vidjelac', search: 'Pretraga',
    allYears: 'Sve godine', allTypes: 'Sve vrste', allVisionaries: 'Svi',
    anyDate: 'Bilo koji datum', searchPlaceholder: 'Pretraži poruke',
    monthly: 'Mjesečna', weekly: 'Tjedna', annual: 'Godišnja', special: 'Posebna', other: 'Druga',
    marija: 'Marija', mirjana: 'Mirjana', ivanka: 'Ivanka', jakov: 'Jakov', ivan: 'Ivan',
    unknown: 'Nije navedeno', noText: 'Tekst poruke nije dostupan u arhivi.',
    unavailable: 'Prijevod na ovom jeziku još nije učitan.',
    available: 'Dostupni jezici', found: 'Pronađene poruke', showMore: 'Prikaži više',
    noResults: 'Nema odgovarajućih poruka.', reset: 'Poništi filtre',
    original: 'Izvor', back: 'Natrag u arhivu', note: 'Napomena izvora',
    read: 'Pročitaj poruku', loading: 'Učitavanje arhive…',
    error: 'Arhiva se ne može učitati.', retry: 'Pokušaj ponovno',
    footer: 'Prijevode je osigurala zajednica; tekstovi se provjeravaju.',
    light: 'Svijetla tema', dark: 'Tamna tema',
    stored: 'Arhiva je dostupna izvan mreže nakon prvog učitavanja.',
    notVerified: 'Istraživačka arhiva — provjera je u tijeku'
  },
  sk: {
    brand: 'Kráľovná pokoja', subtitle: 'Posolstvá z Medžugoria',
    latest: 'Najnovšie', archive: 'Archív', latestMonthly: 'Najnovšie mesačné posolstvo',
    date: 'Dátum', year: 'Rok', type: 'Typ', visionary: 'Vizionár', search: 'Hľadať',
    allYears: 'Všetky roky', allTypes: 'Všetky typy', allVisionaries: 'Všetci',
    anyDate: 'Ľubovoľný dátum', searchPlaceholder: 'Hľadať v posolstvách',
    monthly: 'Mesačné', weekly: 'Týždenné', annual: 'Ročné', special: 'Osobitné', other: 'Iné',
    marija: 'Marija', mirjana: 'Mirjana', ivanka: 'Ivanka', jakov: 'Jakov', ivan: 'Ivan',
    unknown: 'Neuvedené', noText: 'Text posolstva nie je v archíve.',
    unavailable: 'Preklad v tomto jazyku zatiaľ nebol nahraný.',
    available: 'Dostupné jazyky', found: 'Nájdené posolstvá', showMore: 'Zobraziť viac',
    noResults: 'Nenašli sa žiadne posolstvá.', reset: 'Vymazať filtre',
    original: 'Zdroj', back: 'Späť do archívu', note: 'Poznámka zdroja',
    read: 'Čítať posolstvo', loading: 'Načítava sa archív…',
    error: 'Archív sa nepodarilo načítať.', retry: 'Skúsiť znova',
    footer: 'Preklady poskytla komunita; texty sa overujú.',
    light: 'Svetlá téma', dark: 'Tmavá téma',
    stored: 'Po prvom načítaní je archív dostupný offline.',
    notVerified: 'Výskumný archív — prebieha kontrola'
  },
  lv: {
    brand: 'Miera Karaliene', subtitle: 'Medžugorjes vēstījumi',
    latest: 'Jaunākais', archive: 'Arhīvs', latestMonthly: 'Jaunākais ikmēneša vēstījums',
    date: 'Datums', year: 'Gads', type: 'Veids', visionary: 'Vizionārs', search: 'Meklēt',
    allYears: 'Visi gadi', allTypes: 'Visi veidi', allVisionaries: 'Visi',
    anyDate: 'Jebkurš datums', searchPlaceholder: 'Meklēt vēstījumos',
    monthly: 'Ikmēneša', weekly: 'Iknedēļas', annual: 'Ikgadējs', special: 'Īpašs', other: 'Cits',
    marija: 'Marija', mirjana: 'Mirjana', ivanka: 'Ivanka', jakov: 'Jakovs', ivan: 'Ivans',
    unknown: 'Nav norādīts', noText: 'Šajā arhīva ierakstā nav vēstījuma teksta.',
    unavailable: 'Tulkojums šajā valodā vēl nav pievienots.',
    available: 'Pieejamās valodas', found: 'Atrasti vēstījumi', showMore: 'Rādīt vairāk',
    noResults: 'Vēstījumi nav atrasti.', reset: 'Notīrīt filtrus',
    original: 'Avots', back: 'Atpakaļ uz arhīvu', note: 'Avota piezīme',
    read: 'Lasīt vēstījumu', loading: 'Ielādē arhīvu…',
    error: 'Neizdevās ielādēt arhīvu.', retry: 'Mēģināt vēlreiz',
    footer: 'Tulkojumus nodrošinājusi kopiena; tekstus vēl pārbauda.',
    light: 'Gaišais režīms', dark: 'Tumšais režīms',
    stored: 'Pēc pirmās ielādes arhīvs pieejams bezsaistē.',
    notVerified: 'Pētniecības arhīvs — notiek pārbaude'
  }
};
Object.assign(translations, extraTranslations);
const settingsStrings = {
  ru: {settings:'Настройки',interfaceLanguage:'Язык интерфейса',readingLanguage:'Язык посланий',appearance:'Оформление',systemTheme:'Как в системе',lightTheme:'Светлая',darkTheme:'Тёмная',close:'Закрыть',awaiting:'Архив этого языка ещё готовится. Можно выбрать язык интерфейса уже сейчас.'},
  be: {settings:'Налады',interfaceLanguage:'Мова інтэрфейсу',readingLanguage:'Мова пасланняў',appearance:'Афармленне',systemTheme:'Як у сістэме',lightTheme:'Светлая',darkTheme:'Цёмная',close:'Закрыць',awaiting:'Архіў гэтай мовы яшчэ рыхтуецца. Мову інтэрфейсу ўжо можна выбраць.'},
  uk: {settings:'Налаштування',interfaceLanguage:'Мова інтерфейсу',readingLanguage:'Мова послань',appearance:'Вигляд',systemTheme:'Як у системі',lightTheme:'Світла',darkTheme:'Темна',close:'Закрити',awaiting:'Архів цією мовою ще готується. Мову інтерфейсу вже можна обрати.'},
  en: {settings:'Settings',interfaceLanguage:'Interface language',readingLanguage:'Message language',appearance:'Appearance',systemTheme:'System default',lightTheme:'Light',darkTheme:'Dark',close:'Close',awaiting:'This language archive is being prepared. You can already use its interface language.'},
  hr: {settings:'Postavke',interfaceLanguage:'Jezik sučelja',readingLanguage:'Jezik poruka',appearance:'Izgled',systemTheme:'Prema sustavu',lightTheme:'Svijetla',darkTheme:'Tamna',close:'Zatvori',awaiting:'Arhiva na ovom jeziku još se priprema. Jezik sučelja već možete odabrati.'},
  sk: {settings:'Nastavenia',interfaceLanguage:'Jazyk rozhrania',readingLanguage:'Jazyk posolstiev',appearance:'Vzhľad',systemTheme:'Podľa systému',lightTheme:'Svetlá',darkTheme:'Tmavá',close:'Zavrieť',awaiting:'Archív v tomto jazyku sa pripravuje. Jazyk rozhrania si už môžete vybrať.'},
  lv: {settings:'Iestatījumi',interfaceLanguage:'Saskarnes valoda',readingLanguage:'Vēstījumu valoda',appearance:'Izskats',systemTheme:'Sistēmas iestatījums',lightTheme:'Gaišais',darkTheme:'Tumšais',close:'Aizvērt',awaiting:'Šīs valodas arhīvs vēl tiek sagatavots. Saskarnes valodu jau var izvēlēties.'}
};
for (const code of Object.keys(settingsStrings)) Object.assign(translations[code], settingsStrings[code]);

function initialSetting(key, fallback) {
  try { return localStorage.getItem(key) || fallback; }
  catch { return fallback; }
}
const allowedLanguages = languages.map(item => item.code);
const lang = ref(allowedLanguages.includes(initialSetting('medjugorje-language', 'ru'))
  ? initialSetting('medjugorje-language', 'ru') : 'ru');
const uiLang = ref(allowedLanguages.includes(initialSetting('medjugorje-interface-language', 'ru'))
  ? initialSetting('medjugorje-interface-language', 'ru') : 'ru');
const languageOptions = languages.map(item => ({title: item.full, value: item.code}));
const settingsOpen = ref(false);
const vuetifyTheme = useTheme();
const theme = ref(initialSetting('medjugorje-theme', 'auto'));
const T = computed(() => translations[uiLang.value] || translations.ru);
const appearanceOptions = computed(() => [
  {title:T.value.systemTheme,value:'auto'},
  {title:T.value.lightTheme,value:'light'},
  {title:T.value.darkTheme,value:'dark'}
]);
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
  const dark = value === 'dark' || (value === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  vuetifyTheme.global.name.value = dark ? 'marianDark' : 'marianLight';
}
watch(lang, value => {
  try { localStorage.setItem('medjugorje-language', value); } catch { /* private browser mode */ }
  limit.value = 35;
});
watch(uiLang, value => {
  try { localStorage.setItem('medjugorje-interface-language', value); } catch { /* private mode */ }
  document.documentElement.lang = value;
});
watch(theme, value => {
  try { localStorage.setItem('medjugorje-theme', value); } catch { /* private browser mode */ }
  applyTheme(value);
});

function formatDate(value) {
  if (!value) return '';
  const locale = ({be:'be-BY',uk:'uk-UA',hr:'hr-HR',sk:'sk-SK',lv:'lv-LV',en:'en-US'})[uiLang.value] || 'ru-RU';
  return new Date(value + 'T12:00:00Z').toLocaleDateString(locale,
    { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
}
function typename(type) { return T.value[type] || T.value.other; }
function visionaryName(value) { return T.value[value] || (value || T.value.unknown); }
function getTranslation(id) { return localized.value[lang.value]?.[id] || null; }
const latestRow = computed(() => index.value.find(row =>
  row.type === 'monthly' && row.translations?.[lang.value]?.has_text)
  || index.value.find(row => row.type === 'monthly'));
const currentRow = computed(() => selectedId.value
  ? index.value.find(row => row.id === selectedId.value) : latestRow.value);
const currentTranslation = computed(() => currentRow.value
  ? getTranslation(currentRow.value.id) : null);
const hasLanguageArchive = computed(() => Boolean(localized.value[lang.value]));
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
    const required = ['index', 'ru', 'be', 'uk'];
    const optional = ['hr', 'en', 'sk', 'lv'];
    async function read(name, allowMissing = false) {
      const response = await fetch(import.meta.env.BASE_URL + 'data/' + name + '.json');
      if (!response.ok) {
        if (allowMissing && response.status === 404) return null;
        throw new Error(name + ': HTTP ' + response.status);
      }
      const result = await response.json();
      if (!result || typeof result !== 'object') throw new Error('Invalid JSON: ' + name);
      return result;
    }
    const first = await Promise.all(required.map(code => read(code)));
    const extras = await Promise.all(optional.map(code => read(code, true)));
    if (!Array.isArray(first[0].messages)) throw new Error('Invalid data index');
    index.value = [...first[0].messages].sort((a, b) =>
      b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
    const languageFiles = [...first.slice(1), ...extras];
    localized.value = Object.fromEntries(
      [...required.slice(1), ...optional]
        .map((code, n) => [code, languageFiles[n]])
        .filter(([,file]) => file && Array.isArray(file.messages))
        .map(([code,file]) => [code, Object.fromEntries(file.messages.map(row => [row.id, row]))])
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
  document.documentElement.lang = uiLang.value;
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (theme.value === 'auto') applyTheme('auto'); });
  window.addEventListener('hashchange', readHash);
  load();
});
</script>

<template>
  <v-app><div class="app-shell">
    <header class="topbar">
      <div class="brand" @click="selectSection('latest')" role="button" tabindex="0" @keydown.enter="selectSection('latest')">
        <span class="brand-symbol" aria-hidden="true">✳</span>
        <span class="brand-copy">
          <strong>{{ T.brand }}</strong>
          <span>{{ T.subtitle }}</span>
        </span>
      </div>
      <div class="top-actions">
        <button class="language-shortcut" type="button" @click="settingsOpen = true" :aria-label="T.readingLanguage">
          {{ languages.find(item => item.code === lang)?.short || 'RU' }}
        </button>
        <v-btn class="settings-button" variant="text" size="small"
          :aria-label="T.settings" :title="T.settings" @click="settingsOpen = true">⚙</v-btn>
        <button class="theme-button" type="button"
          :title="theme === 'dark' ? T.light : T.dark"
          :aria-label="theme === 'dark' ? T.light : T.dark"
          @click="theme = theme === 'dark' ? 'light' : 'dark'">
          <span aria-hidden="true">{{ theme === 'dark' ? '☼' : '☾' }}</span>
        </button>
      </div>
    </header>

    <v-dialog v-model="settingsOpen" max-width="470" scrollable>
      <v-card class="settings-dialog">
        <v-card-title class="dialog-title">{{ T.settings }}</v-card-title>
        <v-card-text>
          <v-select v-model="uiLang" :items="languageOptions" :label="T.interfaceLanguage"
            density="comfortable" variant="outlined" hide-details="auto" class="setting-control" />
          <v-select v-model="lang" :items="languageOptions" :label="T.readingLanguage"
            density="comfortable" variant="outlined" hide-details="auto" class="setting-control" />
          <p v-if="!hasLanguageArchive" class="settings-hint">{{ T.awaiting }}</p>
          <v-select v-model="theme" :items="appearanceOptions" :label="T.appearance"
            density="comfortable" variant="outlined" hide-details="auto" class="setting-control" />
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" color="primary" @click="settingsOpen = false">{{ T.close }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
              {{ currentTranslation ? T.noText : (!hasLanguageArchive ? T.awaiting : T.unavailable) }}
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
          <div v-if="results.length === 0" class="state-message">{{ hasLanguageArchive ? T.noResults : T.awaiting }}</div>
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
  </div></v-app>
</template>
