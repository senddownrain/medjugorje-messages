# Публичный релиз Medjugorje Messages — проверено

24 октября 2026, московское время.

Сайт: https://senddownrain.github.io/medjugorje-messages/

Опубликованный SHA: `4fdf86e893d08e6335839f34bf632240aad19b71`.

[Workflow](https://github.com/senddownrain/medjugorje-messages/actions/runs/40079682173) — **SUCCESS**. `test-build`, `deploy`, `verify-public` — SUCCESS. [Deployment](https://github.com/senddownrain/medjugorje-messages/actions/runs/40079682173/job/120830810776), [публичная проверка](https://github.com/senddownrain/medjugorje-messages/actions/runs/40079682173/job/120830865502). Pages deployment ID совпадает с SHA. Анонимный Chromium 155.0.8059.0 открыл реальный публичный HTTPS после deployment, получил HTTP 200 и сверил SHA из публичного release.json.

## Интеграция

Релизный [PR #24](https://github.com/senddownrain/medjugorje-messages/pull/24) слит после успешных четырёх проверок GitHub.

- #16 включён в историю main и автоматически отмечен GitHub как merged.
- Весь код #17 → #18 → #19 и оптимизация D из #22 включены через #24. Отдельные stacked PR #17/#18/#19/#22 технически остаются открытыми Draft.
- #15/#20 остаются Draft отдельного приватного Sites-превью; его deployment и доступ не изменялись.
- #21 остаётся Draft и не включён. Новый автоматический импорт и автослияние не включались. Существующие watchers обнаруживают кандидатов для ручной проверки.
- #23 остаётся Draft; предложенный там UX заменён корректным отдельным экраном поиска в #24.
- [Будущие обновления: задача #25](https://github.com/senddownrain/medjugorje-messages/issues/25) отдельно описывает официальный HR, независимые даты публикации RU/BE и остальных языков, staging/review, append-only проверки, запрет изменения существующих текстов, диагностику недоступных источников. Реализация импорта не включена.

## Что изменилось

`src/App.vue`, `src/style.css`: лупа справа открывает отдельный экран результатов. Строка закреплена снизу, sliders внутри строки открывает только четыре фильтра в нижнем листе. Фильтры независимы, сброс сохраняет запрос, есть индикатор активности. Back/Escape закрывают лист; Back/Forward из послания возвращают запрос, фильтры, 70 загруженных карточек, прокрутку и фокус. Добавлены visualViewport/SafeArea и viewport для клавиатуры.

`vite.config.js`, `index.html`, `public/icon-*.png`: корректный Pages base, manifest scope/start_url, семь языков в описании, PNG/maskable-иконки. `package.json`, `package-lock.json`, `scripts/write-release.mjs`: npm ci и SHA сборки/оригиналов. `.github/workflows/pages.yml`: официальные checkout/setup-node/configure-pages/upload-pages-artifact/deploy-pages, обязательные проверки до публикации и публичная проверка после. Contents:read для тестов; pages:write и id-token:write только для deployment. Production-секреты в клиент не передавались.

Проверки: `scripts/check-release-browser.py`, `scripts/check-dist.py`, `scripts/check-startup-browser.py`, `scripts/measure-startup.py`. Документация: `docs/PUBLIC_RELEASE.md`. `.gitignore` исключает временные файлы, название старого workflow артефакта уточнено в `.github/workflows/pwa-preview.yml`.

## Результаты

| Команда или проверка | Результат |
|---|---|
| npm ci (Node 22 в Actions) | PASS |
| npm run check:data | PASS: RU 787, BE 153, UK 205, HR 853, EN 894, SK 831, LV 628; 899 ID |
| npm run check:search-metadata | PASS: 899 ID, 917 evidence references |
| npm run test:search | PASS: три Node-файла поисковых тестов |
| python -m unittest discover -s tests -v | PASS: 66 тестов |
| npm run test:search:browser | PASS: пять сценариев, настоящий module Worker, семь языков, безопасная подсветка |
| npm run build; python scripts/check-dist.py | PASS: base/manifest/PNG/хеши; нет noindex, исходных ZIP/MHTML, отчётов и признаков ключей в dist |
| npm run test:ui:browser | PASS: 28 сочетаний 320/390 × семь языков × light/dark; без горизонтального скролла; поиск, фильтры, Back/Forward, refresh |
| npm run test:startup | PASS: ленивый старт, офлайн, malformed JSON не кешируется, retry, failed/successful SW update, data-only update и сохранение старого LV |
| Публичный HTTPS, HTTP 200, SHA | PASS, анонимный Chromium Actions |
| Семь опубликованных архивов | PASS: побайтно совпадают с исходными JSON |
| Manifest/SW scope и Chromium installability | PASS: scope публичного сайта, installabilityErrors=[] в обычном профиле |
| Публичный офлайн | PASS: все семь предварительно загруженных языков, последние послания, поиск, архив, перезагрузка отдельных записей |
| Физический Android, настоящая клавиатура, установка через меню ОС | NOT TESTED: физического устройства нет |

Восемь исходных JSON, все тексты/segments/порядок/ID/даты/ссылки/verified и производная B-модель сохранены побайтно. Проверен diff относительно исходного main d6dccd7 и D; рабочее дерево чистое. 899 ID и 4351 языковая запись. Восемь предложений атрибуции остаются pending; неизвестные получатели не утверждались.

Обновление кеша проверено на production-сборке с синтетической неудачной/успешной сменой SW и версии данных; реальное обновление установленного приложения на физическом телефоне не выполнялось. CDP проверяет техническую устанавливаемость, действие «Установить» в ОС Android не выполнялось.

Прямой доступ среды к github.io блокировался CONNECT-прокси, веб-инструмент также не смог открыть домен. Публичный URL проверен реальным браузером runner-а Actions; JSON и PNG получены из его артефакта. Блокеров публикации не осталось, дополнительных разрешений для релиза не требуется.

## Пять реальных скриншотов публичного сайта

Это мобильные viewport Chromium на публичном URL, без авторизации; не фотографии физического телефона.

- [Главная 320×844, светлая](screenshots/home-320-light.png)
- [Главная 390×844, тёмная](screenshots/home-390-dark.png)
- [Экран результатов 390×844](screenshots/search-390-light.png)
- [Отдельный лист фильтров 390×844](screenshots/filters-390-light.png)
- [Поиск 320×430](screenshots/search-320-reduced.png) — уменьшенный viewport, место под клавиатуру эмулировано.

## Проверка с Android

1. Открыть сайт в обычной вкладке Chrome. Кнопкой RU выбрать отдельно язык интерфейса и послания; проверить семь языков и обе темы.
2. Лупа → слово → результаты над нижней строкой → sliders → год и визионер → закрыть лист. Результаты остаются, на sliders виден индикатор.
3. Сбросить фильтры, прокрутить список, открыть послание → системный Back: запрос и позиция возвращаются. Проверить Forward и перезагрузку прямой ссылки.
4. Меню Chrome → «Добавить на главный экран» → «Установить». Для каждого нужного языка сначала открыть последнее послание и поиск онлайн. Включить авиарежим, закрыть и снова открыть приложение. Загруженные данные должны работать; незагруженный язык показывает явную ошибку без подстановки чужого текста.
5. При предложении обновления нажать «Обновить», проверить язык и офлайн. Первая установка и ещё не сохранённый язык требуют интернета.

## Доказательства

`public-check.json` содержит 28 результатов, проверки, реальный SHA, scope, браузер и SHA-256 восьми исходных JSON. `pwa-cache-check.json` содержит сценарии обновления кеша. `deployment.json` содержит статусы jobs, IDs и проверенные SHA-256 скачанных ZIP.

Оригиналы: [public-release-proof](https://github.com/senddownrain/medjugorje-messages/actions/runs/40079682173/artifacts/12555100495), [release-tests](https://github.com/senddownrain/medjugorje-messages/actions/runs/40079682173/artifacts/12554259329). Отдельная ветка доказательств не меняет main и опубликованный SHA.
