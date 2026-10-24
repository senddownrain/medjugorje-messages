"""Additional regression gates for Draft PR #21; no live network or Issues writes."""
import unittest
from copy import deepcopy
from scripts.watch_review import compare_observations

SOURCE = "https://www.medjugorje.hr/en/our-lady-messages-archive"

def official(dates, new_dates=(), checked="2026-10-24T12:00:00Z", status="no_newer_dates"):
    return {"source": SOURCE, "checked_at_utc": checked, "status": status,
            "new_dates": list(new_dates),
            "observations": [{"date": d, "sections": ["Text for " + d]} for d in dates]}

def community(items, status="ok"):
    return {"checked_at_utc": "2026-10-24T12:00:00Z", "status": status, "candidates": items}

def item(lang="ru", guid="post-1", published="2026-10-24T09:00:00Z", notify=True):
    return {"language":lang, "guid":guid, "url":"https://example.org/messages/"+guid+"/",
            "title":"Message", "published":published, "categories":["Messages"],
            "summary":"Metadata", "notify_new":notify}

class AdditionalSafetyGates(unittest.TestCase):
    def test_first_official_scan_is_baseline(self):
        state, events = compare_observations("official", official(["2026-09-25"]), {}, {})
        self.assertEqual(events, [])
        self.assertEqual(len(state), 1)

    def test_new_official_date_notifies_once(self):
        report = official(["2026-09-25", "2026-10-25"], ["2026-10-25"])
        state, events = compare_observations("official", report, {}, {})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["message_date"], "2026-10-25")
        self.assertEqual(compare_observations("official", report, state, {})[1], [])

    def test_same_official_date_revised_is_correction(self):
        report = official(["2026-09-25"])
        state, _ = compare_observations("official", report, {}, {})
        report["observations"][0]["sections"] = ["Corrected"]
        _, events = compare_observations("official", report, state, {})
        self.assertEqual([e["kind"] for e in events], ["source_correction"])

    def test_delayed_language_is_independent_observation(self):
        first = community([item(lang="ru")])
        state, events = compare_observations("community", first, {}, {})
        self.assertEqual(len(events), 1)
        delayed = community([item(lang="ru"), item(lang="uk")])
        state, events = compare_observations("community", delayed, state, {})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["identity"]["language"], "uk")
        self.assertEqual(events[0]["available_languages"], ["uk"])

    def test_publication_date_not_treated_as_message_date(self):
        _, events = compare_observations("community", community([item(published="2026-10-24T09:00:00Z")]), {}, {})
        self.assertIsNone(events[0]["message_date"])
        self.assertFalse(events[0]["message_text_compared"])

    def test_failed_source_does_not_erase_baseline(self):
        state, _ = compare_observations("community", community([item()]), {}, {})
        frozen = deepcopy(state)
        next_state, events = compare_observations("community", community([], "incomplete"), state, {})
        self.assertEqual(next_state, frozen)
        self.assertEqual(events, [])

    def test_old_rss_item_can_be_baselined_without_notification(self):
        state, events = compare_observations("community", community([item(notify=False)]), {}, {})
        self.assertEqual(events, [])
        self.assertEqual(len(state), 1)
        self.assertEqual(compare_observations("community", community([item(notify=False)]), state, {})[1], [])

    def test_distinct_guid_does_not_collapse_equal_metadata(self):
        a = item(guid="post-1")
        b = item(guid="post-2")
        _, events = compare_observations("community", community([a,b]), {}, {})
        self.assertEqual(len(events), 2)
        self.assertNotEqual(events[0]["key"], events[1]["key"])

    def test_no_mutation_of_previous_state(self):
        state, _ = compare_observations("community", community([item()]), {}, {})
        old = deepcopy(state)
        compare_observations("community", community([item()]), state, {})
        self.assertEqual(state, old)

    def test_first_source_bootstrap_suppresses_historical_issue_flood(self):
        report = community([item(guid="old-1"), item(guid="old-2")])
        state, events = compare_observations(
            "community", report, {}, {}, bootstrap_sources={("example.org", "ru")})
        self.assertEqual(events, [])
        self.assertEqual(len(state), 2)
        self.assertEqual(compare_observations("community", report, state, {})[1], [])
        later = community([item(guid="old-1"), item(guid="old-2"), item(guid="new-3")])
        _, events = compare_observations("community", later, state, {})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["identity"]["source_id"], "new-3")

    def test_lost_cache_rebootstrap_is_quiet(self):
        report = community([item(guid="old-1"), item(guid="old-2")])
        _, events = compare_observations(
            "community", report, {}, {}, bootstrap_sources={("example.org", "ru")})
        self.assertEqual(events, [])

    def test_recovered_language_source_bootstraps_independently(self):
        state, _ = compare_observations(
            "community", community([item(lang="ru", guid="old")]), {}, {},
            bootstrap_sources={("example.org", "ru")})
        _, events = compare_observations(
            "community", community([item(lang="ru", guid="old"), item(lang="uk", guid="old-uk")]),
            state, {}, bootstrap_sources={("example.org", "uk")})
        self.assertEqual(events, [])

    def test_correction_after_quiet_bootstrap_is_reported(self):
        report = community([item(guid="old")])
        state, _ = compare_observations(
            "community", report, {}, {}, bootstrap_sources={("example.org", "ru")})
        corrected = deepcopy(report)
        corrected["candidates"][0]["summary"] = "Corrected metadata"
        _, events = compare_observations("community", corrected, state, {})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "source_correction")

if __name__ == "__main__":
    unittest.main()
