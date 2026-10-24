# PWA prototype (private, not yet published)

**Stack:** Vue 3, Vite, vite-plugin-pwa/Workbox, static JSON from the repository's data/ folder.

## What the first screen does

- Displays the most recently published monthly message **with text**, separately for RU/BE/UK.
- Opens any record and preserves editorial notes without rewriting the original text.
- Archive filtering by year, exact date, message category, visionary and text search.
- Separates absent translations from entries whose source heading has no quoted message text.
- Remembers language preference and theme, supports system dark mode.
- PWA manifest and service worker pre-cache the three JSON archives and index for offline reading after successful first installation/download.

## Testing without publishing

Run:

    npm install
    npm run check:data
    npm run dev

Dev URL uses the GitHub Pages project base (typically http://localhost:5173/medjugorje-messages/).

To compile a distributable package:

    npm run build

The project copies data/*.json into its generated public/data directory before building. Only these four JSONs are included: the extra ZIP and README are not distributed. The entire dist/ folder is attached as a **private** artifact by the "PWA preview build (private)" GitHub Actions workflow.

Public GitHub Pages is **not configured**, and no deployment is triggered. A review and mobile visual smoke test must precede release.

## Outstanding before release

- Ensure the community approves the design and how attribution/licensing should be displayed.
- Review unresolved original-source anomalies, including missing text records.
- Verify icon installability on current Android/iOS. Approved PNG/ICO/WebP assets, maskable safe area, screenshots and Android verification steps are documented in [branding/README.md](branding/README.md).
- Add proper versioned content updates; live HTTP 403 from GitHub Actions prevents unattended harvesting until authorized access is configured.
- In the future, use an approved import/update feed and manual publication process, not bypasses of source-server restrictions.
