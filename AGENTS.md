# AGENTS.md — Medjugorje Messages / Codex Cloud

This file is authoritative for coding agents working in this repository.
Keep reports and user instructions in **Russian**. Owner usually works from Android.

## Repo and goals
- Private GitHub: `senddownrain/medjugorje-messages`, default branch `main`.
- Vue 3 + Vuetify 3 + Vite PWA, very subtle Marian pale blue/gold visual language.
- 7 **independently chosen** message and UI languages: `ru`, `be`, `uk`, `hr`, `en`, `sk`, `lv`.
- Messages: `data/{ru,be,uk,hr,en,sk,lv}.json`, union index `data/index.json`.
- Historical import: 899 distinct dated records, but this is a snapshot, not a permanent expected count. Some saved source entries legitimately have no text; some Latvian content stops in January 2019.
- JSON records are **unverified research data pending editorial review**, not silently approved liturgical or apparition texts.

## Getting started (Codex Cloud environment)
- Node.js 22+, Python 3.12 recommended, npm/PyPI dependencies.
- One-time reproducible setup: `bash scripts/setup-cloud.sh`.
- If Codex asks for Install script, start from `bash scripts/setup-cloud.sh` and let setup test it; use no Firebase or production secrets.
- After edits, run:
  - `npm run check:data` — JSON language presence, index, content SHA-256
  - `python3 -m unittest discover -s tests -v` — parser and import tests
  - `npm run build` — production PWA
- Dev server when a connected preview is supported: `npm run dev`, port 5173, base `/medjugorje-messages/`.
- Local Vite dev mode is not proof of service worker offline support. Validate production PWA offline/install separately with an authorized HTTPS preview or real device.

## Guardrails for content and infrastructure
1. **Never** invent, translate, paraphrase, silently repair or substitute a message. Preserve approved words and source punctuation.
2. Don't silently use one language's text for another. Explicitly show missing translation; user can manually switch language.
3. Preserve original message date, type, source, source ID/slug, visionary (when grounded), editorial notes, duplicate same-date messages, `text_sha256`, and `verified` status.
4. Source URL/date mismatches and missing message bodies must be logged for review, not merged away.
5. Source community has granted rights to its own translations. **Other rights and credits still require review** before public release.
6. The source site `medjugorje.ws` returned HTTP 403 to GitHub Actions; do not evade access controls. Use authorized saved HTML/MHT exports or approved APIs.
7. Official message date watcher and community feeds detect *candidates*, not confirmed seven-language translations; never auto-publish candidates.
8. No secrets, .env or access tokens in PRs. Never enable public GitHub Pages, publish message contents, change Firestore, or deploy to a public site without explicit user approval. Keep the repository and build artifacts private.
9. Cloud Codex currently does not provide guaranteed interactive browser/computer use; never report visual UI or PWA-install tests as PASSED if not actually executed.

## Routine
- One focused feature/bug per branch and PR. Always review current `main` before editing.
- For import work read `docs/SEVEN_LANGUAGE_IMPORT_REPORT.md`, `docs/MHTML_IMPORT.md`, `docs/COMMUNITY_MONITOR.md`.
- For phone-first workflow and Codex environment setup read `docs/CODEX_CLOUD.md`.
- Test light/dark, tiny 320px and common 390px viewport where visual automation is actually available; otherwise label NOT TESTED.
- Every result must include: task summary, changed files, command outputs & statuses (PASS/FAIL/NOT RUN), PR URL, issues requiring owner approval, and **simple Android testing steps**.
- Avoid claiming that GitHub Actions success alone proves visual/mobile/offline behavior.
