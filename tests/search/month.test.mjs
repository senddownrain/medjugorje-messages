import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { SearchCatalog, LANGUAGES } from '../../src/search/catalog.js';
const metadata=JSON.parse(readFileSync(new URL('../../derived/search-metadata.json',import.meta.url)));

test('Month is independent of year and intersects the chosen language/year/type/recipient', () => {
  const catalog=new SearchCatalog(metadata,{});
  for (const language of LANGUAGES) {
    const september=catalog.rows.filter(r=>r.date.slice(5,7)==='09' && r.availability[language]!=='translation_not_present');
    assert.ok(new Set(september.map(r=>r.date.slice(0,4))).size>1);
    assert.deepEqual(catalog.searchIds(language,{filters:{month:9,availability:'present'}}),september.map(r=>r.id));
    const combined=september.filter(r=>r.date.startsWith('2020') && r.type.value==='monthly' && r.visionary.value==='marija');
    assert.deepEqual(catalog.searchIds(language,{filters:{month:'09',year:2020,type:'monthly',visionary:'marija',availability:'present'}}),combined.map(r=>r.id));
  }
  assert.deepEqual(catalog.searchIds('en',{filters:{month:2}}),catalog.searchIds('en',{filters:{month:'02'}}));
  for (const month of [0,13,1.5,'x','009']) assert.throws(()=>catalog.searchIds('en',{filters:{month}}),/Invalid month/);
});
