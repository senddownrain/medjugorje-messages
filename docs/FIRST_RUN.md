# Step 1: private research import

This is **not** a public app or an approved collection of translations.

## Current blocking observation

On 22 October 2026, manual workflow run [#39862437372](https://github.com/senddownrain/medjugorje-messages/actions/runs/39862437372) ran all five parser tests successfully, but requests from GitHub Actions to all three full-list pages received **HTTP 403 Forbidden**:

- `https://www.medjugorje.ws/ru/messages/all`
- `https://www.medjugorje.ws/be/messages/all`
- `https://www.medjugorje.ws/uk/messages/all`

**Zero messages were retrieved.** The original workflow was incorrectly green because of `continue-on-error: true`; that setting has now been removed. The HTTP 403 could be an IP restriction, hosting rule, or another access policy. Do not assume its precise cause and do not bypass a denied request with rotating IPs, proxies, or impersonating browsers.

**Next step:** Ask the webmaster for permission to reuse the translations, a bulk export in RU / BE / UK (CSV, JSON or HTML), and an authorized way to check for updates (e.g. feed/API or permission for a specific client). They ask for technical requests to be written in English, Czech or Slovak: https://www.medjugorje.ws/en/about/contact

## Operation after source access is confirmed

1. Open **Actions → Research messages (manual only) → Run workflow**.
2. The job will now clearly be **red** if a source refuses access or a required archive is missing. This is intentional and does not mean the unit tests failed.
3. Download the `medjugorje-research` artifact, inspect `report.json` and compare real samples with source pages.
4. Only after validation should the archive be committed or integrated with PWA.

The job is manual, read-only and saves temporary GitHub Actions artifacts for 14 days. Output language JSONs are explicitly marked `verified=false`.

The importer respects robots.txt and server denials; it does **not** invent translations or automatically publish texts. HTML parsing must be checked against real exports once available.

## Before public redistribution

Get the necessary permissions for redistribution of each language's translations and relevant ecclesiastical review. Consider the Holy See's 19 September 2024 Note *The Queen of Peace* before launching a public archive.
