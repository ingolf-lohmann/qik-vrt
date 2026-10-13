// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0; Copyright 2026 Ingolf Lohmann.
// Real IndexedDB, cache, reload and two browser origins. Mobile layout is not an iPhone-device witness.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir,mkdtemp,readdir} from 'node:fs/promises';
import {createHash,randomUUID} from 'node:crypto';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../../..');
const clientRoot=resolve(process.env.QIKVRT_OFFLINE_CLIENT_DIR||resolve(root,'public/offline'));
const require=createRequire(import.meta.url);
const modulePath=process.env.QIKVRT_PLAYWRIGHT_MODULE||resolve(here,'node_modules/playwright');
const {chromium,webkit}=require(modulePath);
const lock=JSON.parse(await readFile(resolve(here,'../BROWSER_LOCK.json'),'utf8'));
assert.equal(require(resolve(modulePath,'package.json')).version,lock.playwright);
const browserLock=require(resolve(modulePath,'../playwright-core/browsers.json'));
for(const expected of lock.browsers)assert.deepEqual(browserLock.browsers.find(b=>b.name===expected.name),expected);
const sourceBytes=await readFile(resolve(clientRoot,'SOURCE.json'));
const site32={head:'17fb5f3ff3904bbdc389a85d10a72c06eb7f5395',tree:'2f3440e0e441f8da3e6624688d57f699ac2d7f83',source_json_sha256:'fdfd21d6ee2b6893a9e1dfd3700803f099899b7d2361c9a146bc1fffd0e14428',public_origin:'https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site'};
assert.equal(createHash('sha256').update(sourceBytes).digest('hex'),site32.source_json_sha256,'the suite must select the frozen derived Site32 client');
const source=JSON.parse(sourceBytes);
for(const [path,binding]of Object.entries(source.files)){
 const bytes=await readFile(resolve(clientRoot,path));
 assert.equal(bytes.length,binding.bytes,'source length: '+path);
 assert.equal(createHash('sha256').update(bytes).digest('hex'),binding.sha256,'source digest: '+path);
}
const workerSource=await readFile(resolve(clientRoot,'service-worker.js'),'utf8');
const cacheName=workerSource.match(/const CACHE='([^']+)'/)[1];
const cacheAssets=JSON.parse(workerSource.match(/ASSETS=(\{.*?\});/)[1]);
for(const [path,sha]of Object.entries(cacheAssets))assert.equal(sha,source.files[path].sha256);
const expectedFixture={path:'qikvrt-browser-acceptance.txt',text:'QIKVRT_SITE31_BROWSER_ACCEPTANCE_20261013\n',bytes:42,sha256:'e1bc337f3ce0605ece250eaf5748b3acc8f70ce8847b863df48172741b63a6db',git_blob_sha1:'638d1b19598c3077b89f3a954d2974baca2c3117',tree:'99b939da0bc046ab0f7a362b1d83ed596254d949'};
async function cacheReadback(page){
 const result=await page.evaluate(async({cacheName,cacheAssets})=>{
  const registration=await navigator.serviceWorker.getRegistration(location.href);
  const controller=navigator.serviceWorker.controller;
  if(!registration?.active||registration.active.state!=='activated'||!controller)throw Error('ACTIVE_PERSONAL_WORKER_REQUIRED');
  if(new URL(controller.scriptURL).pathname!==new URL('./service-worker.js',location.href).pathname)throw Error('WRONG_CONTROLLER');
  const cache=await caches.open(cacheName),files=[];
  for(const [path,expected]of Object.entries(cacheAssets)){
   const response=await cache.match(new URL(path,registration.scope));
   if(!response?.ok)throw Error('CACHE_MISSING: '+path);
   const bytes=await response.arrayBuffer();
   const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
   if(sha256!==expected)throw Error('CACHE_DIGEST_DRIFT: '+path);
   files.push({path,bytes:bytes.byteLength,sha256});
  }
  return {active_state:registration.active.state,controller:controller.scriptURL,scope:registration.scope,cache:cacheName,files};
 },{cacheName,cacheAssets});
 return result;
}
async function localReadback(page,path){return page.evaluate(async path=>{
 const {Repository,digest}=await import('./repository.js');const r=await Repository.open();
 try{const head=await r.head(),report=await r.verify(),archive=await r.exportArchive();
  const file=path?await r.file(path):null;
  return {head:head.id,tree:head.snapshot.git_tree_sha1,report,archive_sha256:await digest(await archive.arrayBuffer()),file:path?{path,bytes:file.size,text:await file.text(),sha256:await digest(await file.arrayBuffer()),git_blob_sha1:head.snapshot.files.find(f=>f.path===path).git_blob_sha1}:null};
 }finally{r.close();}
},path);}
async function negativeControl(page){
 const path='/SOURCE.json?uncached-negative='+randomUUID();
 const cached=await page.evaluate(async path=>!!await caches.match(new URL(path,location.href)),path);
 assert.equal(cached,false,'negative control must never be cached');
 const failure=await page.evaluate(async path=>{try{const r=await fetch(path,{cache:'no-store',signal:AbortSignal.timeout(5000)});return {failed:false,status:r.status};}catch(e){return {failed:true,error:e.name};}},path);
 assert.equal(failure.failed,true,'a stopped origin must fail its uncached fetch');
 return {path,cache_match:false,...failure};
}
async function profilePids(profile){
 if(process.platform!=='linux')return null;
 const pids=[];
 for(const entry of await readdir('/proc')){
  if(!/^\d+$/.test(entry))continue;
  try{const argv=(await readFile('/proc/'+entry+'/cmdline','utf8')).split('\0');
   if(argv.some(arg=>arg==='--user-data-dir='+profile))pids.push(Number(entry));
  }catch{}
 }
 return pids.sort((a,b)=>a-b);
}
const timeline=[],cacheStages=[],negativeControls=[];
function observed(stage,details){timeline.push({stage,observed_at:new Date().toISOString(),...details});}

assert.equal(Buffer.byteLength(expectedFixture.text),expectedFixture.bytes);
assert.equal(createHash('sha256').update(expectedFixture.text).digest('hex'),expectedFixture.sha256);
assert.equal(createHash('sha1').update('blob 42\0').update(expectedFixture.text).digest('hex'),expectedFixture.git_blob_sha1);
const fixtureTree=Buffer.concat([Buffer.from('100644 '+expectedFixture.path+'\0'),Buffer.from(expectedFixture.git_blob_sha1,'hex')]);
assert.equal(createHash('sha1').update('tree '+fixtureTree.length+'\0').update(fixtureTree).digest('hex'),expectedFixture.tree);
if(process.argv.includes('--precheck')){
 console.log(JSON.stringify({status:'PASS_PRECHECK_ONLY',source_files:Object.keys(source.files).length,cache_assets:Object.keys(cacheAssets).length,fixture:expectedFixture,playwright:lock.playwright,browser_execution:false}));
 process.exit(0);
}

const servers=[];
async function serve(port){const child=spawn(process.execPath,[resolve(clientRoot,'static-server.mjs')],{env:{...process.env,PORT:String(port)},stdio:['ignore','pipe','pipe']});servers.push(child);await new Promise((resolve,reject)=>{child.stdout.once('data',resolve);child.once('error',reject);child.once('exit',()=>reject(Error('SERVER_STOPPED')));});return 'http://127.0.0.1:'+port;}
let browser,activePage;
async function stopOrigin(child){if(child.exitCode!==null)return;await new Promise(resolve=>{child.once('exit',resolve);child.kill();});}
const output=process.env.QIKVRT_OFFLINE_EVIDENCE_DIR||'/tmp/qikvrt-offline-browser';await mkdir(output,{recursive:true});
const errors=[],checks=[];let processRestart=null,fixtureBefore=null,fixtureOffline=null,beforeRestart=null,afterRestart=null;
try{const [one,two]=await Promise.all([serve(Number(process.env.QIKVRT_OFFLINE_PORT_A||8765)),serve(Number(process.env.QIKVRT_OFFLINE_PORT_B||8766))]);const engine=process.env.QIKVRT_OFFLINE_ENGINE==='webkit'?webkit:chromium,profile=await mkdtemp(resolve(output,'persistent-browser-profile-')),options={headless:true,viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true,...(process.env.QIKVRT_BROWSER_EXECUTABLE?{executablePath:process.env.QIKVRT_BROWSER_EXECUTABLE}:{}),args:engine===chromium?['--no-sandbox']:[]};
  const context=await engine.launchPersistentContext(profile,options);browser=context.browser();assert.equal(browser.version(),lock.browsers.find(b=>b.name===(engine===chromium?'chromium':'webkit')).browserVersion);context.setDefaultTimeout(20000);const page=await context.newPage();activePage=page;page.on('pageerror',e=>errors.push(e.message));await page.goto(one);await page.getByTestId('shell-ready').filter({hasText:/^Client vollständig im Offline-Cache geprüft\.$/}).waitFor();
  cacheStages.push(await cacheReadback(page));observed('worker_activated',cacheStages.at(-1));
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);checks.push('390px layout has no horizontal overflow');
  await page.getByRole('button',{name:'Arbeitskopie anlegen',exact:true}).click();await page.getByTestId('editor-path').fill(expectedFixture.path);await page.getByTestId('editor-text').fill(expectedFixture.text);await page.getByTestId('save').click();await page.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();
  fixtureBefore=await localReadback(page,expectedFixture.path);assert.equal(fixtureBefore.tree,expectedFixture.tree);assert.deepEqual(fixtureBefore.file,{path:expectedFixture.path,text:expectedFixture.text,bytes:expectedFixture.bytes,sha256:expectedFixture.sha256,git_blob_sha1:expectedFixture.git_blob_sha1});observed('fixture_saved',fixtureBefore);
  const first=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();const text=await(await r.file('qikvrt-browser-acceptance.txt')).text();r.close();return {head:h.id,text};});assert.equal(first.text,expectedFixture.text);checks.push('UI edit commits and reads back real IndexedDB bytes');
  await stopOrigin(servers[0]);assert.ok(servers[0].exitCode!==null||servers[0].signalCode!==null);observed('origin_process_exited',{pid:servers[0].pid,exit_code:servers[0].exitCode,signal:servers[0].signalCode});
  negativeControls.push(await negativeControl(page));
  if(engine===chromium)await context.setOffline(true);
  const cacheNavigation=await page.reload();assert.equal(cacheNavigation.fromServiceWorker(),true,'offline navigation must come from the worker');await page.reload();await page.getByTestId('shell-ready').filter({hasText:/^Client vollständig im Offline-Cache geprüft\.$/}).waitFor();assert.equal((await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();r.close();return h.id;})),first.head);fixtureOffline=await localReadback(page,expectedFixture.path);assert.deepEqual(fixtureOffline,fixtureBefore);cacheStages.push(await cacheReadback(page));
  await page.getByRole('button',{name:/^qikvrt-browser-acceptance\.txt/}).click();await page.getByRole('status').filter({hasText:'Datei geladen. Speichern erzeugt einen neuen lokalen Arbeitsstand.'}).waitFor();assert.equal(await page.getByTestId('editor-text').inputValue(),expectedFixture.text);
  await page.getByTestId('verify').click();await page.getByTestId('verification').waitFor();assert.equal(JSON.parse(await page.getByTestId('verification').innerText()).head,fixtureBefore.head);
  observed('offline_reload_verified',{head:fixtureOffline.head,tree:fixtureOffline.tree});
  checks.push('origin is stopped, uncached negative control fails, navigation comes from the SHA-256-verified worker cache, and unchanged 42-byte file, HEAD, TREE and history reopen offline');
  await page.getByTestId('editor-text').fill('edited while offline');await page.getByTestId('save').click();await page.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();checks.push('offline UI writes survive storage readback');
  const result=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();let h=await r.head();const n=1048576*3+71,raw=new Uint8Array(n);for(let i=0;i<n;i++)raw[i]=i%251;h=await r.save('binary/three-chunks.bin',new Blob([raw]),{expected:h.id});const read=new Uint8Array(await(await r.file('binary/three-chunks.bin')).arrayBuffer());if(read.length!==n||read.some((v,i)=>v!==i%251))throw Error('BINARY_DRIFT');const report=await r.verify();const pack=await r.exportArchive();const text=await pack.text();r.close();return {report,text};});assert.equal(result.report.files,2);checks.push('multi-block binary contents and full history are verified');
  const beforeRecovery=await localReadback(page,expectedFixture.path);
  await context.setOffline(false);await serve(Number(process.env.QIKVRT_OFFLINE_PORT_A||8765));
  const recovery=await page.evaluate(async()=>{const r=await fetch('./SOURCE.json?recovery='+crypto.randomUUID(),{cache:'no-store'});return {status:r.status,source:await r.json()};});assert.equal(recovery.status,200);assert.deepEqual(recovery.source,source);await page.reload();await page.getByTestId('shell-ready').filter({hasText:/^Client vollständig im Offline-Cache geprüft\.$/}).waitFor();assert.deepEqual(await localReadback(page,expectedFixture.path),beforeRecovery);checks.push('online recovery restores a real uncached origin response without changing local HEAD, TREE, files or history');const second=await context.newPage();activePage=second;second.on('pageerror',e=>errors.push(e.message));await second.goto(two);await second.getByTestId('shell-ready').filter({hasText:/^Client vollständig im Offline-Cache geprüft\.$/}).waitFor();const beforeEmpty=await second.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();r.close();return h;});assert.equal(beforeEmpty,null);checks.push('different origins have separate local repositories');
  const imported=await second.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const result=await r.importArchive(new Blob([text]));const report=await r.verify();r.close();return {result,report};},result.text);assert.equal(imported.report.head,result.report.head);checks.push('complete export/import preserves exact revision and byte-level Git working tree');
  // Two offline devices diverge, import preserves the visible branch, explicit conflict decisions merge both histories.
  const branchA=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();const next=await r.save('qikvrt-browser-acceptance.txt',new Blob(['phone A']),{expected:h.id});r.close();return next.id;});
  const branchB=await second.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();await r.save('qikvrt-browser-acceptance.txt',new Blob(['phone B']),{expected:h.id});const pack=await r.exportArchive();r.close();return pack.text();});
  const merged=await page.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const imported=await r.importArchive(new Blob([text]));const unchanged=(await r.head()).id;const plan=await r.mergePlan(imported.incoming);let refused=false;try{await r.merge(imported.incoming);}catch(e){refused=e.message==='MERGE_CONFLICT_REQUIRES_DECISION';}const merged=await r.merge(imported.incoming,{'qikvrt-browser-acceptance.txt':'incoming'});const body=await(await r.file('qikvrt-browser-acceptance.txt')).text();const report=await r.verify();const pack=await r.exportArchive();r.close();return {imported,unchanged,conflicts:plan.conflicts.length,refused,merged,body,report,pack:await pack.text()};},branchB);assert.equal(merged.imported.state,'DIVERGENT_IMPORTED');assert.equal(merged.unchanged,branchA);assert.equal(merged.conflicts,1);assert.equal(merged.refused,true);assert.equal(merged.body,'phone B');assert.equal(merged.merged.snapshot.parents.length,2);checks.push('divergence never overwrites; explicit merge preserves two parents and chosen conflict');
  await second.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();await r.importArchive(new Blob([text]));const report=await r.verify();r.close();return report;},merged.pack).then(report=>assert.equal(report.head,merged.report.head));checks.push('merged stand transfers back to second origin without losing history');
  const negative=await page.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const head=(await r.head()).id;const lines=text.trimEnd().split('\n');const index=lines.findIndex(l=>JSON.parse(l).type==='block');const row=JSON.parse(lines[index]);row.data='eA==';lines[index]=JSON.stringify(row);let damaged=false,truncated=false,wrong=false;try{await r.importArchive(new Blob([lines.join('\n')+'\n']));}catch{damaged=true;}try{await r.importArchive(new Blob([text.slice(0,text.lastIndexOf('\n',text.length-2)+1)]));}catch{truncated=true;}const alien=JSON.parse(text.split('\n')[0]);alien.repository_id='another/repository';try{await r.importArchive(new Blob([JSON.stringify(alien)+'\n'+text.slice(text.indexOf('\n')+1)]));}catch{wrong=true;}const after=(await r.head()).id;r.close();return {damaged,truncated,wrong,head,after};},merged.pack);assert.deepEqual([negative.damaged,negative.truncated,negative.wrong],[true,true,true]);assert.equal(negative.after,negative.head);checks.push('tamper, truncation and repository-identity mismatch preserve the admitted head');
  const race=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const a=await Repository.open(),b=await Repository.open(),h=await a.head();const results=await Promise.allSettled([a.save('race/a.txt',new Blob(['a']),{expected:h.id}),b.save('race/b.txt',new Blob(['b']),{expected:h.id})]);a.close();b.close();return results.map(r=>({status:r.status,error:r.reason?.message}));});assert.equal(race.filter(r=>r.status==='fulfilled').length,1);assert.equal(race.find(r=>r.status==='rejected').error,'CONCURRENT_REPOSITORY_CHANGE');checks.push('two-tab writes use an atomic expected-head lease');
  const mismatch=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open(),h=await r.head();const f=h.snapshot.files.find(f=>f.chunks.length);const tx=r.db.transaction('blocks','readwrite');tx.objectStore('blocks').put(new Blob(['corrupt']),f.chunks[0].sha256);await new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onabort=reject;});let refused=false;try{await r.verify();}catch(e){refused=e.message==='CONTENT_READBACK_MISMATCH';}r.close();return refused;});assert.equal(mismatch,true);checks.push('fresh stored-byte tampering blocks verification');
  // Independent cold browser process reopens persisted second-origin storage.
  beforeRestart=await localReadback(second,expectedFixture.path);const large=beforeRestart.head;
  await second.screenshot({path:resolve(output,'iphone-layout.png'),fullPage:true});
  const oldBrowser=browser,pidsBefore=await profilePids(profile);if(engine===chromium&&process.platform==='linux')assert.ok(pidsBefore.length>0,'browser OS process must be observed');
  await context.close();assert.equal(oldBrowser.isConnected(),false);
  assert.deepEqual(await profilePids(profile),process.platform==='linux'?[]:null,'old profile process must have exited');
  await stopOrigin(servers[1]);assert.ok(servers[1].exitCode!==null||servers[1].signalCode!==null);
  const reopened=await engine.launchPersistentContext(profile,options);browser=reopened.browser();reopened.setDefaultTimeout(20000);
  assert.notEqual(browser,oldBrowser);assert.equal(browser.isConnected(),true);const pidsAfter=await profilePids(profile);
  if(engine===chromium&&process.platform==='linux'){assert.ok(pidsAfter.length>0);assert.ok(pidsAfter.every(pid=>!pidsBefore.includes(pid)));}
  processRestart={profile_reused:true,old_browser_disconnected:true,new_browser_connected:true,browser_object_reused:false,pids_before:pidsBefore,pids_after:pidsAfter,old_profile_pids_after_close:process.platform==='linux'?[]:null,origin_still_stopped:true};observed('full_browser_process_restart',processRestart);
  if(engine===chromium)await reopened.setOffline(true);const cold=await reopened.newPage();activePage=cold;cold.on('pageerror',e=>errors.push(e.message));const coldNavigation=await cold.goto(two);assert.equal(coldNavigation.fromServiceWorker(),true);await cold.getByTestId('shell-ready').filter({hasText:/^Client vollständig im Offline-Cache geprüft\.$/}).waitFor();const fresh=await cold.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const report=await r.verify();r.close();return report;});assert.equal(fresh.head,large);afterRestart=await localReadback(cold,expectedFixture.path);assert.deepEqual(afterRestart,beforeRestart);cacheStages.push(await cacheReadback(cold));negativeControls.push(await negativeControl(cold));
  await cold.getByRole('button',{name:/^qikvrt-browser-acceptance\.txt/}).click();await cold.getByRole('status').filter({hasText:'Datei geladen. Speichern erzeugt einen neuen lokalen Arbeitsstand.'}).waitFor();assert.equal(await cold.getByTestId('editor-text').inputValue(),beforeRestart.file.text);
  await cold.getByTestId('verify').click();await cold.getByTestId('verification').waitFor();assert.equal(JSON.parse(await cold.getByTestId('verification').innerText()).head,beforeRestart.head);
  checks.push('full browser process exits and a different process reopens the same profile offline; HEAD, TREE, archive digest, every historical block and UI file are unchanged');
  // Corrupt an installed cache entry, independently exercise the real worker,
  // then restore its exact response. Storage-integrity gates must remain closed.
  const refusal=await cold.evaluate(async cacheName=>{const cache=await caches.open(cacheName),url=new URL('./style.css',location.href),original=await cache.match(url);await cache.put(url,new Response('tampered'));const r=await fetch(url);const registration=await navigator.serviceWorker.getRegistration();const ready=await new Promise((resolve,reject)=>{const c=new MessageChannel(),timer=setTimeout(()=>reject(Error('READY_TIMEOUT')),5000);c.port1.onmessage=e=>{clearTimeout(timer);c.port1.close();resolve(e.data);};registration.active.postMessage({type:'QIKVRT_OFFLINE_READY'},[c.port2]);});await cache.put(url,original);return {status:r.status,ready:ready.ready};},cacheName);
  assert.deepEqual(refusal,{status:503,ready:false});cacheStages.push(await cacheReadback(cold));assert.deepEqual(await localReadback(cold,expectedFixture.path),beforeRestart);checks.push('real worker rejects a corrupted cache entry with 503 and ready=false while local repository bytes remain unchanged');
  let completeSource=null;
  if(process.env.QIKVRT_COMPLETE_REPOSITORY){
    // Filesystem -> actual browser File -> streaming gzip -> independently verified full Git tree.
    await reopened.setOffline(false);const three=await serve(Number(process.env.QIKVRT_OFFLINE_PORT_C||8767)),full=await reopened.newPage();activePage=full;full.on('pageerror',e=>errors.push(e.message));await full.goto(three);
    await full.getByTestId('shell-ready').filter({hasText:/^Client vollständig im Offline-Cache geprüft\.$/}).waitFor();await full.waitForFunction(()=>!document.querySelector('[data-testid=archive-import]').disabled);
    await full.getByTestId('archive-import').setInputFiles(process.env.QIKVRT_COMPLETE_REPOSITORY);
    await full.getByRole('status').filter({hasText:'Repository-Stand vollständig geprüft und lokal übernommen.'}).waitFor({timeout:600000});
    completeSource=await full.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const report=await r.verify(),head=await r.head();r.close();return {...report,source:head.snapshot.source,git_tree_sha1:head.snapshot.git_tree_sha1};});
    const receipt=JSON.parse(await readFile(resolve(dirname(process.env.QIKVRT_COMPLETE_REPOSITORY),'RECEIPT.json'),'utf8'));
    assert.equal(completeSource.head,receipt.snapshot);assert.equal(completeSource.git_tree_sha1,receipt.source_tree);assert.equal(completeSource.files,receipt.files);assert.equal(completeSource.bytes,receipt.source_bytes);
    await full.getByLabel('Datei suchen',{exact:true}).fill('docs/monitor/offline/');assert.equal(await full.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await full.screenshot({path:resolve(output,'complete-repository-iphone-layout.png'),fullPage:true});
    checks.push('complete frozen repository gzip imports through the real React file chooser and verifies all source bytes, native Git tree and populated mobile layout');
  }
  assert.deepEqual(errors,[]);await writeFile(resolve(output,'browser-readback.json'),JSON.stringify({schema:'qikvrt-offline-browser-readback/v2',source:{site32,live_origin_browser_acceptance:false,derived_source:source,worker_sha256:createHash('sha256').update(workerSource).digest('hex'),suite_sha256:createHash('sha256').update(await readFile(fileURLToPath(import.meta.url))).digest('hex')},fixture:{expected:expectedFixture,before:fixtureBefore,offline:fixtureOffline},restart:{...processRestart,before:beforeRestart,after:afterRestart},cache_stages:cacheStages,negative_controls:negativeControls,timeline,engine:engine===webkit?'webkit':'chromium',mobile_layout:{width:390,height:844},actual_iphone_devices:false,offline_disruption:{origin_server_stopped:true,uncached_network_request_failed:true,playwright_offline_flag:engine===chromium,webkit_offline_emulation:'Excluded from acceptance after native internal error; upstream microsoft/playwright#42775'},complete_source:completeSource,checks,check_count:checks.length,second_origin_final_head:large,console_errors:errors,native_execution:false,main_effect:false},null,2)+'\n');console.log(JSON.stringify({checks:checks.length,engine:engine===webkit?'webkit':'chromium',actual_iphone_devices:false,output}));
}catch(error){let state;try{state=await activePage?.evaluate(()=>({url:location.href,online_hint:navigator.onLine,controlled:!!navigator.serviceWorker.controller,text:document.body.innerText.slice(0,3000)}));await activePage?.screenshot({path:resolve(output,'failure.png'),fullPage:true});}catch{}await writeFile(resolve(output,'failure.json'),JSON.stringify({error:error.message,stack:error.stack,checks,console_errors:errors,state},null,2)+'\n');throw error;}finally{await browser?.close();for(const child of servers)child.kill();}
