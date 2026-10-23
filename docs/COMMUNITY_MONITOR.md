# Monitoring community translations

Confirmed from GitHub Actions on October 23, 2026: the general RSS feeds of the Russian, Ukrainian, Slovak, Latvian and English *Light of Mary* sites are accessible. `medjugorje.ws` continues to return HTTP 403 from GitHub-hosted runners. A separate official-date watcher uses the Medjugorje Information Centre archive for the appearance of a new monthly message.

## Workflow

`watch-community-messages.yml` runs twice a day (10:23 and 22:23 UTC) on main once merged. It:

- Reads RSS *metadata only*, respects each site's robots.txt, and does not download message article bodies
- Filters for explicit message titles or message archive permalinks, while excluding daily devotional/audio/news categories
- Looks at posts published **on or after October 23, 2026** to avoid creating hundreds of historical issues on first run
- Opens deduplicated GitHub Issues for editorial review (language, source link, publication time, five checkboxes)
- Never translates, merges JSON, or publicly deploys the site
- Reports blocked or malformed feeds as incomplete/failure rather than reporting "no new messages"

The filter is intentionally conservative. It can miss a message published only to a dedicated archive outside the general RSS window. For stronger guarantees, add confirmed category-specific feeds/API URLs once verified per language. RSS publication dates are **not** the same as Marian apparition dates.

For Croatian, monitor the independent official archive date watcher; no new Croatian text is imported yet. For Belarusian, the existing saved archive remains the only connected source until an authorized current translation feed is identified.

## Manual test

Run **Actions → Watch community translations (review only) → Run workflow**.

Look at the job summary and downloaded `community-translation-watch` JSON report. A passing Actions run with zero candidates only means that no matching **new RSS entries in the available feed window** were found.
