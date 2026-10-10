// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Desktop browser evidence only. No emulation is an Android/iOS witness.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync, writeFileSync, mkdtempSync, rmSync} from 'node:fs';
import {createRequire} from 'node:module';
import {join, resolve, extname} from 'node:path';
import {tmpdir} from 'node:os';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const require=createRequire(import.meta.url),{chromium}=require('playwright');
assert.equal(require('playwright/package.json').version,'1.62.1');
const fixture=process.env.QIKVRT_ORIGIN_FIXTURE_DIR;
if(!fixture)throw Error('QIKVRT_ORIGIN_FIXTURE_DIR required');
const root=join(fixture,'origin'),profile=JSON.parse(readFileSync(join(root,'ORIGIN_PROFILE.json')));
const original=readFileSync(join(fixture,'monolith.sqlite3')),sha=value=>createHash('sha256').update(value).digest('hex');
const scratch=mkdtempSync(join(tmpdir(),'qikvrt-origin-browser-'));
const server=createServer((request,response)=>{
  const path=new URL(request.url,'http://localhost').pathname;
  const relative=path.startsWith('/mesh/')?path.slice(6)||'index.html':null;
  if(!relative || relative.includes('..')){response.writeHead(404);response.end();return;}
  try {
    const bytes=readFileSync(join(root,relative));
    response.writeHead(200,{'Content-Type':({'.html':'text/html','.js':'text/javascript','.json':'application/json','.css':'text/css','.wasm':'application/wasm'})[extname(relative)]||'text/plain','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});response.end(bytes);
  }catch(_){response.writeHead(404);response.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url='http://localhost:'+server.address().port+'/mesh/';
let browser;
test.after(async()=>{await browser?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));rmSync(scratch,{recursive:true,force:true});});
const executable=process.env.QIKVRT_ORIGIN_CHROMIUM_EXECUTABLE || chromium.executablePath();
assert.match(execFileSync(executable,['--version'],{encoding:'utf8'}),/151\.0\.7922\.34/);
const launch=()=>chromium.launchPersistentContext(join(scratch,'browser-profile'),{executablePath:executable,headless:true,args:['--no-sandbox','--host-resolver-rules=MAP unsafe.qikvrt.test 127.0.0.1']});
const checks=[];
async function state(page) {return page.evaluate(async()=>{
  const p=await(await fetch('./ORIGIN_PROFILE.json')).json(),a=await QikvrtOriginStore.create(p);
  try{return await a.read();}finally{a.close();}
});}
async function ready(page) {await page.getByText('Offline-Bootstrap geprüft.',{exact:true}).waitFor();await page.locator('input[type=file]:enabled').waitFor();}
test('actual desktop Chromium: atomic original-store persistence, reload, offline and process restart',async()=>{
  browser=await launch();const page=await browser.newPage();await page.goto(url);await ready(page);
  assert.equal(await state(page),null);checks.push('EMPTY_BOOTSTRAP_DOES_NOT_CREATE_LEDGER');
  await page.getByLabel('SQLite-Monolith importieren').setInputFiles(join(fixture,'monolith.sqlite3'));
  await page.getByTestId('ledger-id').waitFor();
  const before=await state(page);assert.equal(before.ledger_id,profile.ledger_id);assert.equal(before.file_sha256,sha(original));
  checks.push('ORIGINAL_SQLITE_BYTES_AND_NATIVE_EPOCH_IMPORTED');
  // Explicit export must be byte-identical and remain SQLite-readable natively.
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Originalbytes exportieren'}).click();
  const exported=await download,target=join(scratch,'roundtrip.sqlite3');await exported.saveAs(target);
  assert.equal(sha(readFileSync(target)),sha(original));checks.push('BYTE_IDENTICAL_NATIVE_COMPATIBLE_EXPORT');
  await page.reload();await ready(page);assert.deepEqual(await state(page),before);checks.push('RELOAD_PRESERVES_IDENTITY_AND_READBACK');
  await browser.setOffline(true);await page.reload();await ready(page);assert.deepEqual(await state(page),before);checks.push('OFFLINE_RELOAD_WITH_CACHED_WORKER_WASM_AND_REACT');
  const corrupt=Buffer.from(original);corrupt[corrupt.length-8]^=0x80;
  await page.getByLabel('SQLite-Monolith importieren').setInputFiles({name:'bad.sqlite3',mimeType:'application/vnd.sqlite3',buffer:corrupt});
  await page.getByRole('alert').waitFor();assert.deepEqual(await state(page),before);checks.push('CORRUPT_IMPORT_PRESERVES_PRIOR_STORE');
  // Force an actual transaction abort: quota failure cannot replace acknowledged bytes.
  const quota=await page.evaluate(async()=>{
    const p=await(await fetch('./ORIGIN_PROFILE.json')).json(),a=await QikvrtOriginStore.create(p),bytes=await a.exportBytes();
    const put=IDBObjectStore.prototype.put;
    IDBObjectStore.prototype.put=function(){throw new DOMException('synthetic quota fault','QuotaExceededError');};
    try{await a.accept(bytes);return 'unexpected-success';}catch(e){return e.message;}finally{IDBObjectStore.prototype.put=put;a.close();}
  });assert.match(quota,/ORIGIN_STORAGE_(QUOTA|COMMIT_FAILED)/);assert.deepEqual(await state(page),before);checks.push('TRANSACTION_ABORT_PRESERVES_PRIOR_STORE');
  await browser.close();browser=undefined;
  browser=await launch();await browser.setOffline(true);const restarted=await browser.newPage();await restarted.goto(url);await ready(restarted);
  assert.deepEqual(await state(restarted),before);checks.push('BROWSER_PROCESS_CLOSE_RELAUNCH_OFFLINE_PRESERVES_STORE');
  await browser.setOffline(false);await restarted.reload();await ready(restarted);assert.deepEqual(await state(restarted),before);checks.push('RECONNECT_DOES_NOT_REINITIALIZE_STORE');
  const unsafe=await browser.newPage();await unsafe.goto(url.replace('localhost','unsafe.qikvrt.test'));
  await unsafe.getByRole('alert').waitFor();assert.match(await unsafe.getByRole('alert').innerText(),/unsicher/);
  assert.equal(await unsafe.locator('input[type=file]').isDisabled(),true);checks.push('ACTUAL_INSECURE_HTTP_ORIGIN_REFUSED');
  const file=await browser.newPage();await file.goto('file://'+join(root,'index.html'));await file.getByRole('alert').waitFor();
  assert.match(await file.getByRole('alert').innerText(),/lokale Datei startet/);checks.push('ACTUAL_FILE_START_REFUSED');
  // Corruption of saved IndexedDB bytes must not be displayed as admitted readback.
  await restarted.evaluate(async()=>{
    const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('qikvrt-original-monolith-v1',1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
    await new Promise((resolve,reject)=>{const tx=db.transaction('image','readwrite'),s=tx.objectStore('image'),r=s.get('monolith');r.onsuccess=()=>{const v=r.result;new Uint8Array(v.bytes)[100]^=0xff;s.put(v,'monolith');};tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error);});db.close();
  });
  await restarted.reload();await ready(restarted);await restarted.getByRole('alert').waitFor();
  assert.equal(await restarted.getByTestId('ledger-id').count(),0);checks.push('CORRUPT_PERSISTED_IMAGE_REFUSED_ON_RELOAD');
  const output=process.env.QIKVRT_ORIGIN_TEST_EVIDENCE;
  if(output){const git=(...args)=>execFileSync('git',args,{encoding:'utf8'}).trim();writeFileSync(output,JSON.stringify({schema:'qikvrt-origin-desktop-witness/v1',source_head:git('rev-parse','HEAD'),source_tree:git('rev-parse','HEAD^{tree}'),worktree_dirty:!!git('status','--porcelain'),platform:process.platform,architecture:process.arch,playwright:'1.62.1',browser_version:browser.browser()?.version()||'persistent-context',browser_executable_sha256:sha(readFileSync(executable)),origin:url,scope:'REAL_DESKTOP_CHROMIUM_LOOPBACK; SYNTHETIC_ORIGINAL_KERNEL_STORE',checks,android_verified:false,ios_verified:false,public_https_verified:false,effect_ack_done:false},null,2)+'\n');}
});
