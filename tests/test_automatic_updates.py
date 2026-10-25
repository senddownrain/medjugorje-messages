"""Synthetic fixtures, never presented as real Marian messages or source validation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from scripts.automatic_sources import authorized, parse_article, get_page, SourceBlocked
from scripts.automatic_updates import stage, run
from scripts.check_automatic_readiness import ready
from scripts.check_append_only_updates import LANGUAGES

TEXT_SK='TEST FIXTURE ONLY: '+('Toto je iba skúšobný text softvérovej aplikácie. Používateľ môže otvoriť zoznam nových záznamov a skontrolovať jazyk správy. '*5)+'End of test.'
TEXT='TEST FIXTURE ONLY: '+('Synthetic parser words. '*9)+'End of test.'
HASH=lambda t:hashlib.sha256(t.encode()).hexdigest()
POLICY=dict(enabled=True,language='en',origin='https://example.org/',access_evidence='test-only',
 publication_permission='test-only',fixture_evidence='test-only',body_selector='.quote',date_selector='h1',
 date_pattern=r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})',opening='TEST FIXTURE ONLY:',closing='End of test.')
POST=dict(url='https://example.org/message/1',guid='post:1',published='2026-09-26T12:00:00+00:00')
HTML=f'<html lang="en"><h1>2026-09-25</h1><main class="quote">{TEXT}</main></html>'.encode()
OFFICIAL={'test:1':dict(date='2026-09-25',type='monthly',visionary=None,status='identity_confirmed',
 evidence_url='https://www.medjugorje.hr/en/our-lady-messages-archive',evidence_sha256='a'*64)}


def candidate(lang='en'):
 p={**POLICY,'language':lang}
 raw=HTML.replace(b'lang="en"',('lang="'+lang+'"').encode())
 if lang=='sk': raw=raw.replace(TEXT.encode(),TEXT_SK.encode())
 return {**parse_article(raw,p,POST),'canonical_id':'test:1'}


def dump(path,data): path.write_text(json.dumps(data))


class AutomaticTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.base=self.root/'base';self.base.mkdir()
  for lang in LANGUAGES: dump(self.base/(lang+'.json'),dict(language=lang,verified=False,messages=[]))
  dump(self.base/'index.json',dict(verified=False,unique_records=0,messages=[]))
  self.policies={l:{**POLICY,'language':l} for l in LANGUAGES}
 def stage(self,candidates,base=None,name='out'):
  return stage(base or self.base,self.root/name,candidates,OFFICIAL,self.policies)
 def test_new_one_language_late_translation_and_idempotent_rerun(self):
  first=self.stage([candidate()]);self.assertEqual(first['added'],1)
  second=self.stage([candidate('sk')],self.root/'out','late');self.assertEqual(second['added'],1)
  third=self.stage([candidate(),candidate('sk')],self.root/'late','repeat');self.assertEqual(third['added'],0)
  for name in (*LANGUAGES,'index'):
   self.assertEqual((self.root/'late'/(name+'.json')).read_bytes(),(self.root/'repeat'/(name+'.json')).read_bytes())
  msg=json.loads((self.root/'late'/'sk.json').read_text())['messages'][0]
  self.assertFalse(msg['verified']);self.assertEqual(msg['provenance']['published_at'],POST['published'])
 def test_correction_never_mutates_old_text_or_baseline(self):
  self.stage([candidate()]);base=self.root/'out';original=(base/'en.json').read_bytes()
  c=candidate();c['text']=TEXT+' changed';c['text_sha256']=HASH(c['text'])
  r=self.stage([c],base,'correction');self.assertEqual(r['added'],0)
  self.assertIn('immutable',r['events'][0]['reason'])
  self.assertEqual(original,(base/'en.json').read_bytes())
  self.assertEqual(original,(self.root/'correction'/'en.json').read_bytes())
 def test_bad_candidate_does_not_block_other_language(self):
  bad=candidate('sk');bad['message_date']='2026-13-25'
  r=self.stage([bad,candidate()]);self.assertEqual(r['added'],1)
  self.assertEqual([e['status'] for e in r['events']],['blocked','added'])
 def test_duplicate_candidates_and_different_id_same_source(self):
  r=self.stage([candidate(),candidate()]);self.assertEqual(r['added'],1)
  self.assertEqual(r['events'][1]['status'],'blocked')
 def test_missing_permission_or_official_identity_blocks_only_candidate(self):
  self.policies['sk']['publication_permission']=None
  r=self.stage([candidate('sk'),candidate()]);self.assertEqual(r['added'],1)
  c=candidate();c['canonical_id']='unknown';r=self.stage([c],name='noidentity');self.assertEqual(r['added'],0)
 def test_final_gate_failure_leaves_no_candidate_and_recovers(self):
  before={p.name:p.read_bytes() for p in self.base.iterdir()}
  with patch('scripts.automatic_updates.gate',side_effect=ValueError('test gate failed')):
   with self.assertRaises(ValueError): self.stage([candidate()])
  self.assertFalse((self.root/'out').exists())
  self.assertEqual(before,{p.name:p.read_bytes() for p in self.base.iterdir()})
  self.assertEqual(self.stage([candidate()])['added'],1)
 def test_bad_hash_approval_and_short_text_rejected(self):
  for field,value in [('text_sha256','b'*64),('verified',True),('text','excerpt')]:
   c=candidate();c[field]=value
   r=self.stage([c],name=field);self.assertEqual(r['added'],0)
 def test_parser_rejects_incomplete_date_language_and_multiple_quotes(self):
  for raw in [HTML.replace(b'End of test.',b'...'),HTML.replace(b'2026-09-25',b'2026-02-30'),
              HTML.replace(b'lang="en"',b'lang="sk"'),HTML.replace(b'</html>',b'<main class="quote">Duplicate</main></html>')]:
   with self.assertRaises((ValueError,SourceBlocked)):parse_article(raw,POLICY,POST)
 def test_official_identity_requires_literal_source_type_and_unique_section(self):
  from scripts.official_identity import identify_records,associate
  rows=[dict(date='2026-10-25',sections=['Monthly']),dict(date='2026-09-25',sections=['Monthly','Monthly']),
        dict(date='2026-08-25',sections=['Unclear']),dict(date='2026-07-24',sections=['Monthly'])]
  identities=identify_records(rows)
  self.assertEqual(set(identities),{'261025m','260724m'}) # Type is explicit even on a day other than 25.
  self.assertIsNone(identities['261025m']['visionary'])
  self.assertEqual(associate({'message_date':'2026-10-25'},identities),'261025m')
  with self.assertRaises(ValueError):associate({'message_date':'2026-09-25'},identities)
 def test_invalid_official_date_is_isolated_without_inventing_a_date(self):
  from scripts.watch_official_updates import extract_observations
  errors=[]
  rows=extract_observations('<h2>February 30, 2026</h2>Monthly<h2>October 25, 2026</h2>Monthly',errors=errors)
  self.assertEqual([r['date'] for r in rows],['2026-10-25'])
  self.assertEqual(len(errors),1)
 def test_reviewed_html_locale_override_still_rejects_wrong_body_language(self):
  from scripts.official_identity import parse_official_archive
  raw=('<html lang="en"><section><div><h2>2026-09-25</h2>Monthly</div><div class="quote">'+TEXT+'</div></section></html>').encode()
  policy={**POLICY,'language':'hr','source_url':'https://example.org/hr/archive','monthly_label':'Monthly',
          'allow_unknown_publication':True,'not_before':'2026-09-25',
          'html_locale_override':{'observed':'en','expected':'hr','evidence':'synthetic test only'}}
  errors=[];items=parse_official_archive(raw,policy,'2026-10-25T12:00:00Z',errors)
  self.assertEqual(items,[]);self.assertEqual(errors[0]['language_check']['detected'],'en')
 def test_shared_official_archive_url_allows_distinct_confirmed_records(self):
  first=candidate();second=candidate();second.update(canonical_id='test:2',message_date='2026-09-26',source_id='post:2')
  second['text']+=' Another distinct fixture.';second['text_sha256']=HASH(second['text'])
  official={**OFFICIAL,'test:2':{**OFFICIAL['test:1'],'date':'2026-09-26'}}
  self.policies['en']['source_kind']='official_archive'
  r=stage(self.base,self.root/'shared',[first,second],official,self.policies)
  self.assertEqual(r['added'],2)
 def test_cached_official_record_survives_archive_window_but_not_ambiguity(self):
  from scripts.official_identity import cached_identities
  official=deepcopy(OFFICIAL);official['test:1']['identity_rule']='unique_official_date_and_literal_Monthly_label'
  stage(self.base,self.root/'cached',[candidate()],official,self.policies)
  self.assertIn('test:1',cached_identities(self.root/'cached',[],{}))
  self.assertEqual(cached_identities(self.root/'cached',[{'date':'2026-09-25','sections':['Monthly','Monthly']}],{}),{})
 def test_integration_replay_of_two_languages_and_source_correction(self):
  from scripts.automatic_updates import exercise_replays
  candidates=[candidate(),candidate('sk')]
  for item in candidates:item['observed_at']='2026-10-25T12:00:00Z'
  self.stage(candidates)
  r=exercise_replays(self.base,self.root/'out',self.root,candidates,OFFICIAL,self.policies)
  self.assertEqual(r['status'],'PASS');self.assertEqual(r['repeat_added'],0)
  self.assertEqual(r['independently_added'],2)
  self.assertEqual(r['source_correction'],'blocked_database_unchanged')
 def test_official_fulltext_has_unknown_publication_time_and_isolates_bad_cards(self):
  from scripts.official_identity import parse_official_archive
  card=lambda day,body:f'<section><div><h2>{day}</h2><span>Monthly</span></div><div class="quote">{body}</div></section>'
  raw=('<html lang="en">'+card('2026-09-25',TEXT)+card('2026-09-26','excerpt')+'</html>').encode()
  policy={**POLICY,'source_url':POST['url'],'monthly_label':'Monthly','allow_unknown_publication':True,'not_before':'2026-09-25'}
  errors=[];items=parse_official_archive(raw,policy,'2026-09-27T12:00:00Z',errors)
  self.assertEqual(len(items),1);self.assertEqual(len(errors),1)
  self.assertIsNone(items[0]['published_at'])
  self.assertEqual(items[0]['publication_uncertainty'],'publication_time_not_exposed_by_source')
  self.assertEqual(items[0]['raw_sha256'],hashlib.sha256(raw).hexdigest())
 def test_decorative_heading_cannot_replace_explicit_article_heading(self):
  raw=HTML.replace(b'<h1>',b'<h1 class="article-title">').replace(b'<main',b'<h1>Decorative popup</h1><main')
  with self.assertRaises(SourceBlocked):parse_article(raw,POLICY,POST)
  parsed=parse_article(raw,{**POLICY,'date_selector':'.article-title'},POST)
  self.assertEqual(parsed['message_date'],'2026-09-25')
 def test_wrong_body_language_cannot_pass_correct_html_metadata(self):
  from scripts.automatic_sources import check_language
  with self.assertRaises(SourceBlocked):check_language(TEXT,'sk')
 def test_403_robots_and_redirect_never_bypassed(self):
  for robots_status,article_status in [(403,200),(200,403),(200,302)]:
   session=Mock();robots=Mock(status_code=robots_status,text='User-agent: *\nAllow: /')
   article=Mock(status_code=article_status)
   session.get.side_effect=[robots,article]
   with self.assertRaises(SourceBlocked):get_page(session,POST['url'],POLICY['origin'])
   self.assertEqual(session.get.call_count,1 if robots_status==403 else 2)
   self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
 def test_robots_disallow_article_is_respected(self):
  session=Mock();session.get.return_value=Mock(status_code=200,text='User-agent: *\nDisallow: /')
  with self.assertRaises(SourceBlocked):get_page(session,POST['url'],POLICY['origin'])
  self.assertEqual(session.get.call_count,1)
 def test_production_disabled_even_if_dispatch_requests_it(self):
  self.assertFalse(ready(json.loads(Path('reports/updates/readiness.json').read_text()),{'languages':self.policies}))
 def test_offline_audit_has_no_copyright_text(self):
  policies=self.root/'policies.json';dump(policies,{'languages':{l:{**p,'enabled':False,'blocker':'test blocked'} for l,p in self.policies.items()}})
  r=run(self.root/'run',policies,self.base,False)
  self.assertEqual(r['added'],0);self.assertEqual(r['status'],'blocked')
  self.assertNotIn(TEXT,(self.root/'run'/'audit.json').read_text())

if __name__=='__main__':unittest.main()
