import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import notify from '../../scripts/notify-automatic-updates.cjs';
test('recurring failures update one issue without comments; recovery closes it',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'message-notify-'));const path=join(dir,'audit.json');
 try {
  await writeFile(path,JSON.stringify({status:'blocked',sources:{ru:{status:'blocked'}},run_url:'https://example.org/run'}));
  const issues=[],calls=[];
  const api={listForRepo:()=>{},create:async o=>{calls.push('create');issues.push({...o,number:1,state:'open'});},
   update:async o=>{calls.push(o.state==='closed'?'close':'update');Object.assign(issues[0],o);},
   createComment:()=>{throw new Error('Must never spam comments');}};
  const github={paginate:async()=>issues,rest:{issues:api}};
  const args={github,context:{repo:{owner:'test',repo:'test'}},audit:path,validation:'success',publication:'skipped'};
  await notify(args);await notify(args);assert.deepEqual(calls,['create','update']);
  await writeFile(path,JSON.stringify({status:'validated',sources:{},run_url:'https://example.org/run'}));
  await notify(args);assert.deepEqual(calls,['create','update','close']);
 } finally {await rm(dir,{recursive:true,force:true});}
});
