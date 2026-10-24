# CONNECT 403: Codex и GitHub-hosted Actions — 24.10.2026

Диагностика добавлена в **Draft #21**, без merge, импорта или включения нового расписания. Использованы одни и те же два URL и идентифицирующий User-Agent проекта. Запреты не обходились: обычный HTTPS с проверкой TLS, штатные proxy-переменные, без VPN, смены IP/UA, браузерного обхода Cloudflare или отключения TLS.

## Фактические результаты

| Источник | Codex, 07:54:16 UTC | GitHub-hosted, 07:54:30–32 UTC |
|---|---|---|
| `https://www.medjugorje.hr/en/our-lady-messages-archive` | **ERROR:** proxy CONNECT 403; HTTP-ответ сайта не получен | **OK:** HEAD 200 и GET 200; HTML 577 728 bytes; nginx; распознаны даты |
| `https://www.medjugorje.ws/en/messages/` | **ERROR:** proxy CONNECT 403; HTTP-ответ сайта не получен | **ERROR:** HEAD 403 и GET 403; HTTP-ответ Cloudflare, `cf-ray` записан |

Официальный HR-архив вернул последние наблюдаемые заголовки дат `2026-09-25`, `2026-08-25`, `2026-07-25`. Диагностика **не утверждает «новых посланий нет»**, не сравнивает семь переводов и не импортирует этот HTML. В отчёте сохранены URL, timestamp, методы, статусы, разрешённые response headers и SHA-256 тела успешного ответа, без самих текстов и секретов.

[Codex JSON](../reports/source-network/codex.json) · [Actions JSON](../reports/source-network/actions.json) · [настоящий Actions run](https://github.com/senddownrain/medjugorje-messages/actions/runs/40075963937).

## Источник ошибки и маршрут

**Codex:** Python requests → настроенный `http://proxy:8080` → CONNECT к host:443 → **403 от proxy до TLS и HTTP сайта**. Политика среды `restricted/enforced`; ни `www.medjugorje.hr`, ни `www.medjugorje.ws` не входят в разрешённые destinations. Поэтому это ошибка выхода среды, а не доказательство HTTP 403 сайтов. HTTP status источника в JSON — `null`, CONNECT status — 403. robots GET также блокируется на этом же этапе; выполнен только metadata HEAD точного URL, content GET пропущен.

**GitHub-hosted Ubuntu:** requests → штатный HTTPS egress GitHub runner без environment proxy → сервер/front-end указанного hostname. Для HR robots 200, HEAD/GET 200, `server: nginx/1.18.0 (Ubuntu)`. Для WS robots 200, HEAD/GET 403 от Cloudflare; например `cf-ray: a4f76a007a81206f-IAD`. Это уже **HTTP-отказ front-end сайта**, не CONNECT proxy. Что именно в политике Cloudflare вызвало отказ (WAF, IP reputation, география и т.п.), по этим заголовкам установить нельзя; причина не выдумана. До внутреннего origin за Cloudflare запрос мог не дойти.

Низкоуровневые NAT/маршрутизаторы и внутренний origin не трассировались. «Без environment proxy» не означает доказанного отсутствия промежуточной инфраструктуры GitHub. Поле `origin_reached` в JSON означает получение HTTP-ответа authority URL, включая его CDN/front-end.

## Политика источников

- **Основной источник обнаружения — `medjugorje.hr`**, уже используемый official watcher. Его доступ из Actions подтверждён. Не делать доступность WS условием успешного HR-сканирования.
- **`medjugorje.ws` — дополнительный источник.** При 403 его состояние остаётся **ERROR**, без попыток обойти защиту или автоматически подставить чужой текст. Недоступность дополнительного источника не скрывается и не обозначается «изменений нет».
- Новый `source-network-diagnostic.yml` — только read-only `pull_request`/`workflow_dispatch`, без schedule/Issues write. Весь run остаётся **FAIL**, потому что один источник ERROR; unit tests, summary и artifact отработали успешно. Красный diagnostic не замаскирован `continue-on-error`.
- Official watcher сохраняет URL/checked_at и явный `state: ERROR` при отказе; старый подробный `status: blocked_or_failed` оставлен для совместимости. Ошибка возвращает exit 2 и `new_dates: null`.
- Расписание #21 не активировано: PR остаётся Draft и не merged. Существующие main workflows не менялись.

## Разрешённый резервный механизм

При ERROR редактор может вручную проверить доступный официальный источник в своём обычном авторизованном браузере либо предоставить законно сохранённый HTML/MHT. В редакционном issue фиксировать исходный URL, дату/время проверки, source ID/slug, дату послания, язык и отдельные неподтверждённые поля визионера/типа. Сверить запись с устойчивыми локальными ID и SHA, а не только с похожим текстом. Исправление существующей записи оформить как correction с точным diff.

Подтверждение редактором и отдельное утверждение владельца предшествуют изменению JSON. До них — кандидат/ERROR, без автоматического импорта, перевода, утверждения атрибуции или публикации. Если источник недоступен совсем, сохранять ERROR и ждать разрешённого источника; не выдавать это за отсутствие новых сообщений.

## Проверки с телефона

Открыть #21 → Files → этот документ и два JSON; затем Actions run → Summary. HR должен быть OK/200, WS — ERROR/403, общий диагностический run — красный. Artifact содержит тот же JSON. Ручной повтор можно запустить через Actions → Source network diagnostic (read only), выбрав ветку PR, когда workflow доступен в интерфейсе. Текущий проверенный запуск уже выполнен автоматически на PR; включать расписание или делать merge для него не потребовалось.
