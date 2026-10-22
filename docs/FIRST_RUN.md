# Step 1: private research import

This is **not** a public app or an approved collection of translations.

1. Open **Actions → Research messages (manual only) → Run workflow**.
2. Wait for the run to finish, and download **medjugorje-research** from its Artifacts section.
3. Inspect research-output/report.json, including warnings and missing_ids; compare samples with the source manually.
4. Only after verification should any data be committed or added to a PWA.

No secrets, Firebase project, hosting, scheduled scraping or server are needed for this test. The job is manual, read-only and saves temporary GitHub Actions artifacts for 14 days. Output language JSONs are explicitly marked verified=false.

The importer visits the public RU, BE and UK archive and category pages, respects robots.txt, uses at least a 1.5-second delay, and stops on denials or rate limits. It does **not** fill in missing translations, fabricate attributions, or automatically publish texts. Some HTML structures or message types may not yet be supported; the first run is designed to expose those gaps.

## Before public redistribution

Check each translation's licensing and get relevant authorization for reproducing full texts. Consider the Holy See's 19 September 2024 Note *The Queen of Peace* and ecclesiastical review before launching a public archive. A PR and manual review process will be added after validating source extraction.
