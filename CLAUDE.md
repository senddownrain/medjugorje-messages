# Medjugorje Messages — instructions for Claude Code cloud sessions

## Mission
Build and maintain a calm, lightweight Marian-themed Vue 3 + Vuetify 3 PWA to read the messages of Our Lady of Medjugorje in seven languages. Work in **Russian** when reporting to the project owner, who generally reviews changes from an Android phone.

## Canonical repository and state
- Repository: `senddownrain/medjugorje-messages` (PUBLIC, API-confirmed 2026-10-25).
- Default branch `main` contains both the application and imported seven-language JSON archive.
- Message languages: `ru`, `be`, `uk`, `hr`, `en`, `sk`, `lv`.
- User-facing **interface language and message text language are independent** preferences.
- JSON: `data/{ru,be,uk,hr,en,sk,lv}.json` and `data/index.json`.
- Historical snapshot: 899 unique records, first 3 languages preserved. These counts are a baseline, not an invariant after importing genuinely new messages.
- The historical Latvian MHTML snapshot ends January 2019, so don't claim Latvian texts after that date without separately verifying their source.
- Some message headings have no quoted message text; preserve explicit `has_text=false`.

## Cloud setup and verification
On an isolated remote environment, in the repository root run:

```bash
bash scripts/setup-cloud.sh
npm run check:data
python -m unittest discover -s tests -v
npm run build
```

For an interactive preview (when a preview port can be forwarded): `npm run dev`; Vite runs on port 5173, path `/medjugorje-messages/`. Codespaces and Claude Code cloud environments are not the same service. A passing build does **not** prove Android PWA installation or offline behavior; perform those smoke tests separately.

## Non-negotiable content integrity
1. Never invent, paraphrase, auto-translate, modernize or silently correct the texts of messages.
2. Do not silently substitute a different language when the chosen one is missing. Display absence and only offer an explicit user-selected switch.
3. Preserve individual date, message type, original URL, source slug, visionary when grounded, separately stored editorial notes, and SHA256 text hashes.
4. Distinct messages on the same day must remain separate; source URL/date mismatches require a report, not silently dropping records.
5. Check translations and historical archive rights/source credits before any public release.
6. `www.medjugorje.ws` and `text.medjugorje.ws` returned HTTP 403 from GitHub Actions. Do not evade restrictions; use owner-supplied archives or authorized feeds.
7. Existing RSS/date watchers remain metadata only. Owner authorized automatic source-attributed publication of new translations in all seven languages on 2026-10-25 without per-message approval. Full-text automation is separate: read docs/AUTOMATIC_UPDATES.md and research/automatic-source-policies.json, respect readiness gates, and keep unavailable languages blocked. Do not infer seven-language completeness or editorial verification from technical PASS.
8. No credentials, tokens, private keys or local `.env` in commits or user-facing logs.

## Development workflow
- Read the relevant import/update docs under `docs/`.
- Make **one feature branch and one PR per coherent task**. Do not commit unrelated changes.
- Run tests and build; confirm `npm run check:data` for edits affecting data or reader. Fix failures before asking for merge.
- Existing Pages automation is authorized within this task after end-to-end/readiness gates; production remains disabled pending recorded checks. Do not request the already recorded translation/publication authorization again. New infrastructure or Firestore changes need explicit scope. Repository is public: no complete third-party HTML in public artifacts or full protected source text in audit logs.
- Test both light/dark and compact phone widths around 320/390px; keep Vuetify styling extremely subtle: pale Marian blue and a little gold, legible typography, generous whitespace.
- Include in the final report: files changed, tests (pass/fail/not run), exact PR link, how to inspect from Android, outstanding risks.
- When code can't be visually tested, state **NOT TESTED**. Do not claim a successful preview based only on build passing.
- Ask the owner only for account-specific approvals and external access genuinely unavailable to the environment.
