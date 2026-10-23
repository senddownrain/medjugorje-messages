# Evidence-first audit: visionary and message series — 2026-10-23

Status: **READ-ONLY FINDINGS; no original messages edited; editorial audit incomplete**.

Дополнение этапа A: [актуальный отчёт](AUDIT_STAGE_A_2026-10-23.md) выявил ещё
пять кандидатов по контексту, включая прямое свидетельство Вицки в `850114w`.
Нулевой счётчик Вицки в индексе не подтверждает отсутствие исходных записей.
Из 159 неизвестных weekly пять имеют индивидуальные свидетельства;
остальные 154 не получают атрибуции автоматически. Семь оригинальных MHTML `/all`
теперь сверены: 4 351 запись, ноль расхождений; все восемь предложений подтверждены
оригиналами. Тематические EN/HR annual/special пока не предоставлены.

## Inputs and integrity

The original seven-language package was parsed locally and compared against its index. All 899 canonical IDs are unique; each per-language text SHA-256 matches; concatenated message segments reproduce the stored message text; date, type, translation presence and source-language URLs agree with the union index. **Zero structural violations** in these checks. These results do NOT prove source completeness, proper ecclesiastical authorization, or authoritative attribution.

Language record counts: RU 787, BE 153, UK 205, HR 853, EN 894, SK 831, LV 628. Types: monthly 477; special 181; weekly 160; annual 81.

Current index visionary counts: Marija 478, Mirjana 210, Jakov 29, Ivanka 20, null 162. **Zero Ivan and Vicka** currently appear because the original importer had limited name detection. Of the 162 unknowns, 159 are the **historical weekly parish series**; do not force a visionary assignment where original headings provide none.

## Three clear missed attributions

The original saved headings explicitly name:

| ID | Date | Language and verbatim source-title evidence | Candidate |
|---|---|---|---|
| `060908s` | 2006-09-08 | EN: `Our Lady's apparitions to Ivan` | Ivan Dragićević |
| `140812s` | 2014-08-12 | UK: `- Ivan` | Ivan Dragićević |
| `050402s` | 2005-04-02 | LV: `Dievmātes vēstījums Mirjamai` | Mirjana Dragićević-Soldo |

Do **not** change canonical IDs, titles, original text, URLs or hashes to repair metadata. A follow-up PR should make metadata-only proposals with per-record provenance and tests, and keep unknown weekly recipients unknown.

## Evidence about distinct series

The source site separately groups special messages to Ivan, special messages to Marija, and Mirjana's 2nd-of-month messages: https://www.medjugorje.ws/en/messages/special/ . It separately groups annual messages to Ivanka, Jakov, and Mirjana: https://www.medjugorje.ws/en/messages/annual/ . Monthly 25th messages are attributed to Marija: https://www.medjugorje.ws/en/messages/ . These source **group labels** are stronger evidence than guessing by month/day alone.

Recommended metadata schema: `visionary: marija|mirjana|ivanka|jakov|ivan|vicka|null`; `series: marija_monthly_25|mirjana_second_day|mirjana_annual|ivanka_annual|jakov_annual|parish_weekly|ivan_special|marija_special|other_special|null`; `attribution: { source_url, evidence_type, evidence_lang, review_status }`. Keep series **independent** of message type and visionary. Distinguish provisional candidates from editorially approved attribution.

Historical exceptions (not annual recurring dates) include 1985-05-07 to Ivanka and 1998-09-12 to Jakov. Do not reclassify them solely on calendar dates. For weekly parish records do not assume recipient is Marija. Do not add empty/fictional messages for Vicka.

## Incomplete coverage and caveats

Only 894 of 899 union IDs are present in English; the five absent: `160625a`, `140812s`, `110625a`, `050402s`, `840705w`. No automatic inference from the English archive will cover these.

The main `/messages/all` archives preserve text and title, but can discard their **category grouping**; therefore they alone cannot prove that all original messages or source series survived extraction. For an independent comparison, request saved MHTML of these **four** category pages, without replacing the seven existing snapshots:

- https://www.medjugorje.ws/en/messages/annual/
- https://www.medjugorje.ws/en/messages/special/
- https://www.medjugorje.ws/hr/messages/annual/
- https://www.medjugorje.ws/hr/messages/special/

Optional additional spot checks, if discrepancies appear: RU annual/special and individual dated message pages. Compare source URLs and IDs as sets for each category; report missing IDs, duplicate source links, date/type mismatches, and text-only-in-context anomalies. Do not infer absence when the source request returned HTTP 403.

The 2024 Vatican Note https://www.vatican.va/roman_curia/congregations/cfaith/documents/rc_ddf_doc_20240919_nota-esperienza-medjugorje_en.html (paras. 38–39) describes the ecclesial status of the phenomenon and requirements for collected-message publications. Public distribution and editorial authorization require separate review.

## Release gate

1. Confirm audit with independent source category snapshots.
2. Apply only evidence-backed metadata changes, each with source link/evidence and diff.
3. Validate unchanged exact bytes and SHA-256 for `data/{ru,be,uk,hr,en,sk,lv}.json` (if only metadata index changes) and unchanged `text_sha256` values.
4. Run `python3 -m unittest discover -s tests -v`, `npm run check:data`, `npm run build`, and targeted UI tests for each of the six visionary filters plus unknown parish messages.
5. No public deployment or auto-publication until owner approves results.
