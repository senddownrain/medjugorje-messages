# Medjugorje Messages — search-first PWA v2 (architecture, NOT implemented)

## Product model

One calm reading home; remove the separate user-facing "Archive" destination after navigation parity tests, **not** the underlying data. Home shows the latest published/available message on the selected text language. A prominent search field below it opens a full-screen mobile search view with results on the same surface; a "Filters" disclosure expands advanced options. Header has 2 controls: **language** (settings sheet with independently chosen interface and text language) and **theme** (accessible light/dark; auto theme still available inside sheet). No redundant cogwheel.

## Search interaction

- Default: latest message followed by recent history; search remains discoverable and usable immediately.
- Search with or without entered keywords. Selecting only a visionary or series returns matching messages, newest first.
- Filters: person (Marija, Mirjana, Ivanka, Jakov, Ivan, Vicka where data exists, and Unattributed), **series**, type, date range/from-to, optional year. Dependent controls hide no data; zero matches have a truthful empty state.
- Results are compact cards: date, person or "Parish series / not specified", type/series, a highlighted *short* snippet, exact match counts, source-language availability.
- In-reader "Back" restores entered text, selected filters, scroll position and language.
- Exact date, phrase search and diacritic-insensitive search are distinct modes; normalize Unicode correctly for RU/BE/UK/HR/SK/LV. Highlight user text safely, not by arbitrary HTML injection.
- Accessible keyboard, screen readers, Android software keyboard, 320px viewport and reduced-motion. No horizontal overflow.
- Preserve deep links and bookmarks to `#message/<id>`; migrate old `#archive` routes gracefully.

## Performance and offline model

Presently the app requests index + all seven language JSONs at startup, which is unnecessary. Load compact metadata and the chosen text language **lazily**. Build a local language-aware search index once per chosen language; query locally (no network per keystroke), with approx. 100–150ms debounce only if needed on low-powered Android. Avoid scanning each message text anew on every render. Track version and checksum per language; cache unchanged resources across app updates and provide an explicit "Save all languages for offline use" option. Set a storage-size budget; ensure old caches are retired. Service worker in production mode may precache app shell/metadata, with language JSON cached on demand. Don't leak private message data into public hosting or cross-user caching. Test Android disk persistence and site sign-in separately.

## Implementation sequencing

1. PR-A: attribution and series **audit first**, read-only reporting, explicit source-backed metadata review; absolutely no changes to original message texts.
2. PR-B: search data model and fast client index; regressions, e2e tests with realistic query/filter combinations.
3. PR-C: new search-first unified reader UI and header controls; preserve deep links and browser Back; real 320/390 viewport captures.
4. PR-D: measured lazy loading and PWA cache changes with offline/privacy tests, compare load/interaction timing against baseline.
5. PR-E: Marian symbol integration, app icon PNG 192/512 + SVG, installability and themes after iconography approval.

Don't combine all five steps in one large PR. Do not publish to private Sites until reviews and owner approval. Existing private preview PR #15 should be checked for conflicts.
