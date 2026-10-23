# Повторная техническая приёмка C — 23.10.2026

Проверенная исходная голова #19: `3653ce8e8d5a326b895869f72e81f0fd2561fe1c`.
Исходники C не изменялись в этой проверке. Этот коммит добавляет протокол.

- **PASS CI #18** `3c2d667`: Search foundation, Parser tests, PWA preview build. Браузерная отмена закрыта успешной повторной попыткой.
- **PASS CI #19** `3653ce8`: [Search foundation 40016877496](https://github.com/senddownrain/medjugorje-messages/actions/runs/40016877496), job `120631091238`: Chromium install, настоящий Worker, production build и UI regression завершены `success`. Parser/PWA workflows также success. Последующий CI коммита документации нужно читать отдельно.
- **PASS локально:** `npm run test:search` (17), `python -m unittest discover -s tests -v` (66), `npm run test:search:browser` (5 сценариев), `npm run check:data`, `npm run check:search-metadata`, `npm run build`.
- **PASS локально:** полный `check-reader-browser.py`: 28 сочетаний 320/390 × 7 языков × light/dark; четыре фильтра, месяц, слова/фразы, независимые языки UI/чтения, long names, pending/unknown, пропуски/контекст, безопасный highlight, Back/Forward/70 карточек/scroll/focus, быстрые запросы и языки, Worker RPC, loading/error/retry. [JSON](../reports/stage-c-acceptance/browser.json).
- **NOT TESTED:** физический Android, настоящая экранная клавиатура, установка и офлайн на телефоне, доступ анонимного браузера к хостингу. Эмуляция окна 390×430 не заменяет клавиатуру Android.

Технических блокеров C на проверенной голове нет. Визуальная приёмка владельца и редакционное решение о восьми pending-атрибуциях остаются открыты. 154 unknown не атрибутированы; все восемь JSON сохранены. Ни один PR не объединён, сайт не обновлён.

С телефона: открыть [галерею C](UX_POLISH_SCREENSHOTS.md), сравнить чтение/фильтры/языковой лист при 320 и 390 px. Интерактивная проверка актуального C требует подготовленного отдельного приватного превью; прежний живой сайт #15 ещё содержит старый UI. После разрешённого обновления: выбрать язык, открыть поиск и четыре фильтра, открыть результат, нажать Android Back/Forward, переключить тему и перезагрузить.
