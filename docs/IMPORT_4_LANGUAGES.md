# Import Croatian, English, Slovak and Latvian archives (HR / EN / SK / LV)

**Project:** https://github.com/senddownrain/medjugorje-messages  
**Context:** Existing RU, BE and UK archives were imported successfully (787 / 153 / 205 messages; 802 merged records). The current MHTML importer and merger support **only these 3 languages**. Do not upload four extra files under `data/` or replace `index.json` before code updates and regression checks.

## Step 1 — Owner saves the 4 source pages

Use a desktop browser, open the full list (with **full message texts**), press Ctrl+S, and save as **MHTML** (`.mht`/`.mhtml`) if available. Plain `.html` is also accepted if all message bodies remain in the file. Send the files to the project; do not import manually in GitHub:

| Code | Source page | Suggested filename |
|---|---|---|
| HR | https://www.medjugorje.ws/hr/messages/all | `medjugorje_hr.mht` |
| EN | https://www.medjugorje.ws/en/messages/all | `medjugorje_en.mht` |
| SK (Slovenčina, **not** Slovenščina) | https://www.medjugorje.ws/sk/messages/all | `medjugorje_sk.mht` |
| LV | https://www.medjugorje.ws/lv/messages/all | `medjugorje_lv.mht` |

Check that top, middle and bottom messages are visible offline after saving. Do not convert the page to PDF, Word, screenshots, or a link-only bookmark.

**Note:** medjugorje.ws is a historical archive; the Latvian page ends in 2019, so it is **not** the source for all recent Latvian publications. Authorized later translations should be checked against https://medjugorje.lv/. English updates: https://thelightofmary.com/ and https://www.medjugorje.hr/en/our-lady-messages-archive. Slovak updates: https://svetlomariino.sk/. Croatian originals: verify against https://www.medjugorje.hr/.

## Step 2 — Developer/Codex migration plan

Perform work on a separate branch and **Draft PR**. No public GitHub Pages, merge, database publication or Firebase changes without a subsequent review.

1. **Baseline:** Capture hashes and counts for current `data/ru.json`, `be.json`, `uk.json`, `index.json`. Keep the existing 802 IDs and every original RU/BE/UK text byte-identical. Back up the input files.
2. **Parse four additional formats:** Extend language allowlists and the `Content-Location` path checks in `scripts/import_mhtml.py` to `ru,be,uk,hr,en,sk,lv`. Verify HTML structure and date metadata independently for each language. Do not assume the same page template.
3. **Preserve metadata:** retain ID, dated occurrence, type (monthly/weekly/annual/special), visionary when grounded, original URL and URL slug, full original wording, separate editorial context segments, original title, source position, text SHA-256 and explicit no-text status. If original URL's slug disagrees with date, preserve both and log it; if two distinct messages collide on ID, never overwrite one silently.
4. **Create four JSONs:** `data/hr.json`, `data/en.json`, `data/sk.json`, `data/lv.json` using the existing language JSON schema, marked `verified: false` pending review. Never fill missing texts from another language or by machine translation.
5. **Merge conservatively:** Update `scripts/merge_archives.py` or create a separate merger that reuses existing **approved input JSONs** without regenerating the original three. Build one union `data/index.json` with seven explicit `translations` entries per canonical record, including `present`, `has_text`, source URL, title, slug, status and checksum. The union should contain at least 802 existing records and possibly more. Verify old IDs and checksums remain intact.
6. **Integrate with Vuetify PR #6:** Branch `feat/pwa-first-screen` already has seven **interface** language options but fetches only the original 3 message files. Adapt `src/App.vue` and `scripts/stage-data.mjs`/`scripts/check-data.mjs` to fetch, stage and validate seven datasets. Keep message language selection independent of interface language. For missing translations show unavailable state, never a silent fallback.
7. **Quality gate:** Report counts, date range, types, duplicate IDs, conflicting source dates, absent quote bodies and URL errors **per language**. Manually sample monthly, annual and special messages, two messages on the same date, and selected early/late texts. Validate accents in Croatian, Slovak and Latvian. Run Python unittest, `npm run check:data`, `npm run build`, 320px/390px reader checks and production-mode PWA offline smoke.
8. **Editorial review:** Determine attribution and provenance for historical medjugorje.ws material vs contemporary community translations. Mark all unapproved records `verified: false`. No automatic approval, publication or replacement of missing translations.

## Update sources

New translations should be reviewed from the respective community sites: Latvian https://medjugorje.lv/, Slovak https://svetlomariino.sk/, English https://thelightofmary.com/. The separate watcher only reports likely new RSS publications; RSS articles can be meditations or news and their publication dates are not necessarily apparition dates. The site medjugorje.ws returned HTTP 403 to GitHub Actions. Respect access denials: use user-provided saved pages or a sanctioned export rather than bypassing restrictions.

**Success:** four source snapshots parsed; all seven JSONs and union index validated; original three unchanged; editor reports reviewed; Draft PR ready, no public deployment.

**Important:** Commands with `--language hr/en/sk/lv` or seven-language merge flags will only work **after the code is extended**. Do not run them assuming current support.
