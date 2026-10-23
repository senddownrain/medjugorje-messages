# Alternative source: saved HTML pages (offline)

**Why:** GitHub Actions run #39862437372 received **HTTP 403** for the RU, BE and UK archive pages. This option never makes a network request to medjugorje.ws.

The community sponsoring this project manages the translations and has offered permission for their use. Check the scope and attribution in the published app, but a separate permission request to that same community is not needed.

## One simple trial

1. In a normal browser, open https://www.medjugorje.ws/ru/messages/all
2. Save the **complete HTML page**, not a screenshot or print-to-PDF. A browser's "Save Page As → HTML only" is suitable if it preserves text and markup.
3. Supply that HTML file to the project for an initial parser check. You can also upload it in this ChatGPT conversation for us to inspect.
4. The parser generates unverified JSON files and a completeness report. We will manually compare samples and count linked IDs.

Repeat with:
- https://www.medjugorje.ws/be/messages/all
- https://www.medjugorje.ws/uk/messages/all

Example command after placing the files in a local (ignored) folder named "saved":

    pip install -r requirements.txt
    python -m scripts.import_saved_html --ru saved/ru.html --be saved/be.html --uk saved/uk.html --output research-output/offline

Pass just one language for an initial smoke test; the other languages will be reported as "not_provided" until supplied. A warning and exit code 2 is expected for incomplete input; it is **not** automatic publication.

## Data safeguards

- Saved source HTML stays on the user's machine or in temporary conversation attachments unless intentionally uploaded.
- JSON is written only to a chosen local folder and marked "verified": false.
- No silent machine translation; missing translations remain missing.
- Preserve IDs, dates, separate same-day messages, source links, and text hashes.
- Review problem records, duplicates, categories and author/visionary details before publishing.
- Once archival data is verified, we can use the same format for the future Vue PWA.

A native site-provided bulk export remains preferable if one is available. The HTML route is for source files saved by people with legitimate access.
