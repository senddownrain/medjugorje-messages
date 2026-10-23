from copy import deepcopy
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from scripts.watch_community_messages import inspect_all
from scripts.watch_review import compare_observations, from_report
from scripts.watch_official_updates import extract_observations


class ReviewTests(unittest.TestCase):
    def report(self):
        return {'checked_at_utc':'2026-10-23T12:00:00Z', 'status':'ok', 'candidates':[
            {'guid':'post-123', 'language':'en', 'title':"Our Lady's message", 'published':'2026-10-25T12:00:00Z',
             'url':'https://thelightofmary.com/messages/test/', 'categories':['Messages'], 'summary':'Metadata'}]}

    def test_same_guid_is_correction_not_second_message(self):
        report = self.report()
        state, first = compare_observations('community', report, {}, {})
        self.assertEqual(first[0]['kind'], 'new_publication_candidate')
        report['candidates'][0]['title'] += ' corrected'
        state, corrections = compare_observations('community', report, state, {})
        self.assertEqual(len(corrections), 1)
        self.assertEqual(corrections[0]['key'], first[0]['key'])
        self.assertEqual(corrections[0]['kind'], 'source_correction')
        self.assertIn('+', corrections[0]['diff'])
        self.assertIsNone(corrections[0]['visionary'])
        self.assertFalse(corrections[0]['message_text_compared'])

    def test_source_connection_error_is_an_incomplete_report(self):
        with patch('scripts.watch_community_messages.load_feed', side_effect=ConnectionError('robots HTTP 500')):
            report = inspect_all(datetime(2026,10,23,tzinfo=timezone.utc))
        self.assertEqual(report['status'], 'incomplete')
        self.assertTrue(all(s['state'] == 'failed' for s in report['sites'].values()))
        self.assertEqual(report['candidates'], [])

    def test_time_of_check_never_creates_notification(self):
        report = self.report()
        state, _ = compare_observations('community', report, {}, {})
        report['checked_at_utc'] = '2026-10-23T23:00:00Z'
        self.assertEqual(compare_observations('community', report, state, {})[1], [])

    def test_same_text_distinct_origin_or_guid_is_not_merged(self):
        report = self.report()
        a = from_report('community', report)[0]
        report['candidates'][0]['guid'] = 'post-124'
        self.assertNotEqual(a['key'], from_report('community', report)[0]['key'])
        report['candidates'][0]['guid'] = 'post-123'
        report['candidates'][0]['url'] = 'https://svetmariji.ru/example/'
        self.assertNotEqual(a['key'], from_report('community', report)[0]['key'])

    def test_failure_retains_state_and_healthy_sources(self):
        report = self.report()
        state, _ = compare_observations('community', report, {}, {})
        failed = {'checked_at_utc':report['checked_at_utc'], 'status':'incomplete', 'candidates':[]}
        next_state, events = compare_observations('community', failed, state, {})
        self.assertEqual(state, next_state)
        self.assertEqual(events, [])

    def test_official_bootstrap_then_change_and_new_date(self):
        report = {'source':'https://www.medjugorje.hr/en/our-lady-messages-archive',
            'checked_at_utc':'2026-10-23T12:00:00Z', 'status':'no_newer_dates', 'new_dates':[],
            'observations':extract_observations('<h2>September 25, 2026</h2><p>Text</p><h2>September 25, 2026</h2><p>Second</p>')}
        self.assertEqual(len(report['observations']), 1)
        self.assertEqual(report['observations'][0]['sections'], ['Text', 'Second'])
        state, events = compare_observations('official', report, {}, {})
        self.assertEqual(events, [])
        report['observations'][0]['sections'][0] = 'Revised'
        self.assertEqual(compare_observations('official', report, state, {})[1][0]['kind'], 'source_correction')
        report['new_dates'] = ['2026-10-25']
        report['observations'].append({'date':'2026-10-25', 'sections':['New']})
        self.assertEqual(len(compare_observations('official', report, state, {})[1]), 2)

    def test_exact_provenance_matches_existing_data_without_edits(self):
        local = {'en':{'verified':False, 'messages':[{'id':'known', 'source_id':'original',
            'source_url':'https://thelightofmary.com/messages/test/', 'text_sha256':'abc'}]}}
        original = deepcopy(local)
        _, events = compare_observations('community', self.report(), {}, local)
        self.assertEqual(events[0]['kind'], 'existing_source_review')
        self.assertEqual(events[0]['local_provenance_matches'][0]['id'], 'known')
        self.assertEqual(local, original)


if __name__ == '__main__':
    unittest.main()
