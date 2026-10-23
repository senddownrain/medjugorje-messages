# Monitoring and seven-language coverage

GitHub Actions can read the official Information Centre English archive at https://www.medjugorje.hr/en/our-lady-messages-archive, but tests from GitHub runners confirm **HTTP 403** at www.medjugorje.ws and text.medjugorje.ws.

The scheduled watcher checks **only new publication dates** twice daily: 09:17 and 21:17 UTC. It creates a GitHub Issue assigned to the repository owner, with 7 separate language checkboxes (RU, BE, UK, HR, EN, SK, LV) when it finds a new date. The source website's translations are NOT checked automatically, because that is presently blocked.

The local index currently contains only RU/BE/UK. HR/EN/SK/LV need full archive imports from available saved .mht/.html files. The Latvian source last shows entries in 2019; don't claim a current Latvian translation exists without evidence. Older revisions/late translations are NOT detected by this date watcher.

An access failure or unexpected page structure results in a failed workflow, never a 'no new messages' result. This run does NOT deploy or change the PWA.
