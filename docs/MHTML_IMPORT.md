# Browser MHTML import (preferred for saved full-archive pages)

The 23 October 2026 Russian Chrome MHTML archive supplied by the translation community included **787 entries** from 1984 through 25 September 2026; **784** had message text and **3** did not. The importer preserves editorial commentary separately from quoted messages.

Use this command on a local computer with Python and the project requirements installed:

    pip install -r requirements.txt
    python -m scripts.import_mhtml "saved_russian_archive.mht" --language ru --output research-output/ru

Change --language to be or uk for pages saved from their respective /messages/all URLs. A plain .html saved page is also supported.

The generated JSON is not automatically published. It contains original titles, entire message text, notes/context segments in reading order, IDs, source links, SHA256 checksums, and verification flags. Check report.json and compare selected records with the original site before release. Do not assume that the saved snapshot includes messages posted after its capture date.

## Important source anomalies found in Russian snapshot

- 2011-12-25: the original link slug is 121125m (which indicates 2012-11-25).
- 2014-03-18: original link slug is 140418a.
- 2016-06-25: original link slug is 120625a.
- The original URLs 121125m and 120625a occur twice each.
- 1984-06-14 and 1985-09-19 explicitly state no special message.
- 2010-12-25 has a heading but no message body in the saved archive.

The importer treats the date in the source page's checkbox metadata as canonical for indexing, while keeping the original slug and URL. This avoids losing distinct same-date entries and keeps questionable original links discoverable for editorial review.

**Source copyright:** The requesting translation community confirms it authorizes use of the translations for this project. Before a public launch, retain translation attribution and confirm rights to any other third-party materials.

The online GitHub Actions import still encounters HTTP 403 and should not be scheduled until an authorized access mechanism exists.
