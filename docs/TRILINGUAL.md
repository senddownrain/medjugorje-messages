# Three-language archive build

The translation community provided complete archive snapshots in Russian, Belarusian and Ukrainian and has authorized use of its translations for the project. Since medjugorje.ws returned HTTP 403 to GitHub Actions, this importer runs on saved HTML/MHTML files and performs no network requests.

Install requirements, then run from the repository root:

    pip install -r requirements.txt
    python -m scripts.merge_archives --ru saved/ru.mht --be saved/be.mht --uk saved/uk.mht --output research-output/combined

Use the three original files in the correct language order. It writes:

- data/ru.json, be.json, uk.json — complete source texts and separate contextual notes
- data/index.json — one merged index with translation presence and message source URL
- reports/summary.json — aggregate counts and latest/earliest dates
- reports/index.csv and by_year.csv — sortable data
- reports/absent_in_saved_language_archive.csv — absent entries, not proof a translation never existed
- reports/issues.json and issues.csv — source link mismatches, missing text and more

The saved 23 October 2026 snapshots contained 787 Russian, 153 Belarusian, 205 Ukrainian records and 802 distinct IDs; 144 were shared by all three. Latest monthly message in all three: 25 September 2026.

Special cases to review: Ukrainian 25 February 2023 and Russian 25 December 2010 have headings without text; two early Russian weekly entries explicitly report no message. Source URL/date errors are preserved, not silently overwritten.

Output is always unverified research data and is not automatically committed or published. Do not substitute another language for missing text. Attribution and review remain necessary for public PWA deployment.
