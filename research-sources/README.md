# Оригиналы для этапа A

`medjugorje_original_sources_seven.zip` — побайтная копия ZIP, предоставленного
пользователем в этой сессии. Размер: 1 397 664 байта. SHA-256:
`00f3b0d539345a8d4d697a91be987b6b78c1d5e8c5079f780fa693eb18b740cb`.

Содержит семь MHTML `/messages/all` в `original_sources/{lang}_all.mht`
и три сопроводительных отчёта в `audit/`. Сопроводительные отчёты сохранены как
часть оригинального ZIP; они не заменяют независимую сверку.
Четырёх тематических MHTML EN/HR annual/special в этом архиве нет;
они получены и сохранены в отдельном ZIP ниже.

ZIP читается напрямую без распаковки в репозиторий и без сетевых обращений.
Сверщик `scripts/audit_source_snapshots.py` независимо извлекает исходные
контейнеры сообщений и сравнивает их с неизменёнными JSON. Команда:

```bash
python3 -m scripts.audit_stage_a --source-zip research-sources/medjugorje_original_sources_seven.zip --out reports/stage-a
```

Эта команда только с `/all` выдаёт код 2: тематические источники не проверены этим запуском.
Все исходники и отчёты остаются в приватном репозитории. Публикация приложения
и текстов не выполняется. Редакторские статусы посланий не повышаются.

## Четыре тематических снимка

`medjugorje_thematic_en_hr_sources_audit_2026-10-23.zip` сохранён побайтно:
434 324 байта, SHA-256
`e300ebe4af0c0b2c619d7de7daca61c9aba8ccb50475e09de06b3b450e613654`.
Внутри четыре оригинальных MHTML EN/HR annual/special, независимый скрипт,
README и три исходных отчёта. Все три отчёта воспроизведены побайтно; тест
`test_original_independent_script_reproduces_all_three_supplied_reports`
повторяет проверку офлайн во временной папке.

Полная техническая сверка обоих ZIP:

```bash
python3 -m scripts.audit_stage_a \
  --source-zip research-sources/medjugorje_original_sources_seven.zip \
  --thematic-zip research-sources/medjugorje_thematic_en_hr_sources_audit_2026-10-23.zip \
  --out reports/stage-a
```

Код 0 — VERIFIED_SOURCE_SNAPSHOT_COVERAGE относительно предоставленных снимков.
Редакционное утверждение восьми атрибуций остаётся PENDING_EDITORIAL_ATTRIBUTION.
Данные приложения, `verified`, тексты, хеши и ссылки не изменяются.
