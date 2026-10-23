# Seven-language archive import — 23 October 2026

Four complete MHTML archives were supplied by the translation community:

| Language | Entries | Quoted text | Date range |
|---|---:|---:|---|
| Croatian (hr) | 853 | 844 | 1982–2026-09-25 |
| English (en) | 894 | 883 | 1982–2026-09-25 |
| Slovak (sk) | 831 | 827 | 1984–2026-09-25 |
| Latvian (lv) | 628 | 623 | 1984–2019-01-02 |

Combining with the three *existing* languages gives 899 distinct canonical entries (97 additions) and 45 entries with text in all seven. There were 36 source anomalies in the four snapshots: 29 headings without message quotes, 5 source URL/date mismatches and 2 duplicate source URLs. These are not necessarily 36 editorial mistakes: some headings explicitly announce that no special message was given. Review originals rather than inventing text.

The Ukrainian, Belarusian and Russian JSON files were retained **byte-for-byte** in the generated candidate ZIP. The old 802 entries and their RU/BE/UK translation metadata were unchanged.

## How to run the expanded importer

Install dependencies with `pip install -r requirements.txt`. The updated `scripts/import_mhtml.py` recognizes all 7 languages.

For each of the four source snapshots, run:

```bash
python -m scripts.import_mhtml saved/hr.mht --language hr --output research-output/hr
python -m scripts.import_mhtml saved/en.mht --language en --output research-output/en
python -m scripts.import_mhtml saved/sk.mht --language sk --output research-output/sk
python -m scripts.import_mhtml saved/lv.mht --language lv --output research-output/lv
```

Inspect `report.json` for each. Copy only the resulting HR/EN/SK/LV language JSON files to a **review branch**, alongside the original `data/ru.json`, `be.json`, `uk.json`, and the current 3-language `data/index.json`. Then run:

```bash
python -m scripts.assemble_seven --data data --out research-output/seven-language-candidate
```

The assembler checks every text checksum, preserves old metadata, rejects duplicate IDs and date/type disagreements, and writes a proposed seven-language `index.json`, summary and issue report under `research-output/seven-language-candidate`. Review it before replacing `data/index.json`. Never overwrite the approved three source-language files with re-imported approximations. Run Python tests and the PWA integrity/build checks before merging.

## Current release gate

The new HR/EN/SK/LV JSONs and seven-language index are supplied **separately**, not embedded in this source-code PR. The owner/reviewer must upload them on a review branch, because GitHub repository access from this working environment cannot directly push those large generated local artifacts.

The Latvian historical snapshot ends January 2019, so post-2019 LV translations must be sourced from https://medjugorje.lv/ and checked by the community. An absent language should be shown as absent, not substituted or machine translated. Do not publicly publish the unverified archive or launch Firebase/Pages deployment as part of this import.
