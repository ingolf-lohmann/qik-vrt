// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0; Copyright 2026 Ingolf Lohmann.
// Real IndexedDB, cache, reload and two browser origins. Mobile layout is not an iPhone-device witness.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {spawn,spawnSync} from 'node:child_process';
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir,cp,mkdtemp} from 'node:fs/promises';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const here=dirname(fileURLToPath(import.meta.url)),root=resolve(here,'../../..');
const require=createRequire(import.meta.url);
const {chromium,webkit}=require(process.env.QIKVRT_PLAYWRIGHT_MODULE||'playwright');
const servers=[];
async function serve(port){const child=spawn(process.execPath,[resolve(here,'static-server.mjs')],{env:{...process.env,PORT:String(port)},stdio:['ignore','pipe','pipe']});servers.push(child);await new Promise((resolve,reject)=>{child.stdout.once('data',resolve);child.once('error',reject);child.once('exit',()=>reject(Error('SERVER_STOPPED')));});return 'http://127.0.0.1:'+port;}
// Publish distinct production-built shells at one stable origin. Faults affect
// real worker HTTP downloads, not a mocked worker or an activation API shortcut.
async function updateControls(engine,options){
  const dir=await mkdtemp(resolve(output,'update-releases-')),releases={};
  async function release(label){
    const destination=resolve(dir,label);await cp(here,destination,{recursive:true});
    await writeFile(resolve(destination,'client.js'),(await readFile(resolve(destination,'client.js'),'utf8'))+'\nglobalThis.QIKVRT_TEST_RELEASE='+JSON.stringify(label)+';\n');
    const generated=spawnSync(process.env.PYTHON||'python3',['-B','-c','import pathlib,sys,json; from tools.qikvrt_offline_repository import shell; print(json.dumps(shell(pathlib.Path(sys.argv[1]))))',destination],{cwd:root,encoding:'utf8'});
    assert.equal(generated.status,0,generated.stderr);
    const binding=JSON.parse(generated.stdout),files=new Map();
    for(const name of [...Object.keys(binding.assets),'service-worker.js'])files.set('/'+name,await readFile(resolve(destination,name)));
    return releases[label]={label,binding,files};
  }
  const a=await release('A'),b=await release('B'),c=await release('C'),d=await release('D');
  let published=a,fault=null,downloads=[],context,netClosed=false;
  const server=createServer((req,res)=>{
    const path=new URL(req.url,'http://localhost').pathname;
    const bytes=published.files.get(path==='/'?'/index.html':path);
    downloads.push({release:published.label,path,fault:fault?.path===path?fault.kind:null});
    if(fault?.path===path&&fault.kind==='disconnect'){req.socket.destroy();return;}
    if(!bytes){res.writeHead(404);res.end();return;}
    const content=fault?.path===path&&fault.kind==='integrity'?Buffer.concat([bytes,Buffer.from('\nCORRUPTED_UPDATE')]):bytes;
    res.writeHead(200,{'content-type':path.endsWith('.js')?'text/javascript':path.endsWith('.css')?'text/css':path.endsWith('.svg')?'image/svg+xml':path.endsWith('.webmanifest')?'application/manifest+json':'text/html','cache-control':'no-store','content-length':content.length});res.end(content);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url='http://127.0.0.1:'+server.address().port,profile=resolve(dir,'browser-profile'),controls=[],updateErrors=[];
  const observeErrors=ctx=>ctx.on('page',page=>page.on('pageerror',error=>updateErrors.push(error.message)));
  async function loaded(page,label){await page.waitForFunction(value=>globalThis.QIKVRT_TEST_RELEASE===value,label,{timeout:30000});await page.getByTestId('shell-ready').filter({hasText:'vollständig'}).waitFor();await page.waitForFunction(()=>!document.querySelector('[data-testid=editor-text]').disabled);}
  const onlineContact=page=>page.evaluate(()=>window.dispatchEvent(new Event('online')));
  async function readback(page){return page.evaluate(async()=>{
    const {Repository}=await import('./repository.js');const r=await Repository.open(),head=await r.head(),history=await r.history();r.close();
    const reg=await navigator.serviceWorker.getRegistration();
    const receipt=await new Promise(resolve=>{const channel=new MessageChannel();channel.port1.onmessage=({data})=>{channel.port1.close();resolve(data);};navigator.serviceWorker.controller.postMessage({type:'QIKVRT_OFFLINE_READY'},[channel.port2]);});
    return {head:head.id,revisions:history.length,release:globalThis.QIKVRT_TEST_RELEASE,cache:receipt.cache,ready:receipt.ready,waiting:!!reg.waiting,installing:!!reg.installing,text:document.querySelector('[data-testid=editor-text]').value,path:document.querySelector('[data-testid=editor-path]').value};
  });}
  async function wholeShell(page,expected){
    const found=await page.evaluate(async assets=>{
      const out={};for(const path of Object.keys(assets)){const r=await fetch('./'+path);out[path]=[...new Uint8Array(await crypto.subtle.digest('SHA-256',await r.arrayBuffer()))].map(v=>v.toString(16).padStart(2,'0')).join('');}return out;
    },expected.binding.assets);
    assert.deepEqual(found,expected.binding.assets);
  }
  async function failed(page,target,kind){
    published=target;fault={path:'/repository.js',kind};const at=downloads.length;
    await page.evaluate(async()=>{const reg=await navigator.serviceWorker.getRegistration();globalThis.QIKVRT_FAILED_INSTALL=false;reg.addEventListener('updatefound',()=>{const worker=reg.installing;worker.addEventListener('statechange',()=>{if(worker.state==='redundant')globalThis.QIKVRT_FAILED_INSTALL=true;});},{once:true});});
    await onlineContact(page);
    await page.waitForFunction(()=>globalThis.QIKVRT_FAILED_INSTALL===true,{},{timeout:30000});
    assert(downloads.slice(at).some(r=>r.fault===kind),'fault reached real HTTP install fetch');
  }
  try{
    context=await engine.launchPersistentContext(profile,options);observeErrors(context);
    const first=await context.newPage();await first.goto(url);await loaded(first,'A');
    await first.getByRole('button',{name:'Arbeitskopie anlegen',exact:true}).click();await first.getByTestId('editor-text').fill('saved baseline');await first.getByTestId('save').click();await first.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();
    await first.getByTestId('editor-path').fill('personal/unsaved-first.md');await first.getByTestId('editor-text').fill('ungespeicherter Entwurf · erster Tab');
    const copiedTab=await first.evaluate(()=>sessionStorage.getItem('qikvrt-editor-tab-v1'));
    const second=await context.newPage();
    await second.addInitScript(key=>{if(!sessionStorage.getItem('test-inherited-tab')){sessionStorage.setItem('qikvrt-editor-tab-v1',key);sessionStorage.setItem('test-inherited-tab','1');}},copiedTab);
    await second.goto(url);await loaded(second,'A');
    assert.notEqual(await second.evaluate(()=>sessionStorage.getItem('qikvrt-editor-tab-v1')),copiedTab);
    await second.getByTestId('editor-path').fill('personal/in-flight.md');await second.getByTestId('editor-text').fill('laufender Speichervorgang');
    await second.evaluate(async()=>{const {Repository}=await import('./repository.js');const save=Repository.prototype.save;Repository.prototype.save=async function(...args){await new Promise(resolve=>globalThis.releaseInFlight=resolve);return save.apply(this,args);};});
    await second.getByTestId('save').click();await second.waitForFunction(()=>typeof globalThis.releaseInFlight==='function');
    const before=await readback(first);published=b;await onlineContact(first);await onlineContact(second);
    await second.waitForFunction(async()=>!!(await navigator.serviceWorker.getRegistration()).waiting);
    // The staged worker is complete, but the executing old client remains in charge.
    await new Promise(resolve=>setTimeout(resolve,1800));
    assert.equal((await readback(first)).cache,before.cache);assert.equal((await readback(second)).release,'A');
    assert.equal(await second.getByTestId('editor-text').isDisabled(),true);await wholeShell(first,a);
    controls.push('running repository action defers activation and finishes on the old client');
    await second.evaluate(()=>globalThis.releaseInFlight());
    await loaded(second,'B');await first.bringToFront();await loaded(first,'B');
    assert.equal(await first.getByTestId('editor-text').inputValue(),'ungespeicherter Entwurf · erster Tab');assert.equal(await first.getByTestId('editor-path').inputValue(),'personal/unsaved-first.md');
    assert.equal(await second.getByTestId('editor-text').inputValue(),'laufender Speichervorgang');
    const admitted=await readback(first);assert.notEqual(admitted.head,before.head);assert.equal(admitted.revisions,before.revisions+1);
    const unsavedAbsent=await first.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();r.close();return !h.snapshot.files.some(f=>f.path==='personal/unsaved-first.md');});assert.equal(unsavedAbsent,true);
    controls.push('automatic A to B transition preserves independent per-tab drafts without committing them');
    await wholeShell(first,b);controls.push('every served application asset belongs to one complete activated version');
    await first.getByTestId('editor-text').focus();await first.evaluate(()=>document.querySelector('[data-testid=editor-text]').setSelectionRange(3,9,'forward'));
    await failed(first,c,'disconnect');const brokenNetwork=await readback(first);assert.equal(brokenNetwork.cache,admitted.cache);assert.equal(brokenNetwork.head,admitted.head);assert.equal(brokenNetwork.text,admitted.text);assert.equal(brokenNetwork.waiting,false);await wholeShell(first,b);
    controls.push('interrupted HTTP asset transfer rejects installation and retains the last verified shell and repository');
    fault=null;await first.getByTestId('editor-text').dispatchEvent('compositionstart');await onlineContact(first);
    await first.waitForFunction(async()=>!!(await navigator.serviceWorker.getRegistration()).waiting);
    await new Promise(resolve=>setTimeout(resolve,1800));assert.equal((await readback(first)).cache,admitted.cache);
    controls.push('active IME composition defers the complete staged update until compositionend');
    await first.getByTestId('editor-text').dispatchEvent('compositionend');await loaded(first,'C');await second.bringToFront();await loaded(second,'C');await first.bringToFront();
    assert.equal(await first.getByTestId('editor-text').inputValue(),admitted.text);
    const caret=await first.evaluate(()=>{const e=document.querySelector('[data-testid=editor-text]');return [document.activeElement===e,e.selectionStart,e.selectionEnd];});assert.deepEqual(caret,[true,3,9]);
    const restored=await readback(first);assert.equal(restored.head,admitted.head);assert.equal(restored.revisions,admitted.revisions);await wholeShell(first,c);
    controls.push('next online event recovers a rejected download without manual update; text selection and history survive');
    await failed(first,d,'integrity');const badDigest=await readback(first);assert.equal(badDigest.cache,restored.cache);assert.equal(badDigest.head,restored.head);assert.equal(badDigest.text,restored.text);assert.equal(badDigest.waiting,false);await wholeShell(first,c);
    controls.push('SHA-256 mismatch rejects manipulated bytes and preserves the preceding complete version');
    // No scheduling or update promise while the browser process is fully closed.
    await context.close();context=null;fault=null;
    const closedAt=downloads.length;await new Promise(resolve=>setTimeout(resolve,300));assert.equal(downloads.length,closedAt);
    context=await engine.launchPersistentContext(profile,options);observeErrors(context);const cold=await context.newPage();await cold.goto(url);await loaded(cold,'D');
    const recovered=await readback(cold);assert.equal(recovered.head,restored.head);assert.equal(recovered.text,restored.text);await wholeShell(cold,d);
    assert.equal(await cold.evaluate(cache=>caches.has(cache),restored.cache),true);
    controls.push('cold reopen applies the healthy publication automatically and recovers the IndexedDB draft; the previous cache is retained');
    await new Promise(resolve=>server.close(resolve));netClosed=true;await cold.reload();await loaded(cold,'D');assert.equal((await readback(cold)).head,recovered.head);
    controls.push('updated version and repository remain usable on offline navigation after recovery');
    assert.deepEqual(updateErrors,[]);
    return {schema:'qikvrt-client-update-regression/v1',console_errors:updateErrors,controls,versions:Object.fromEntries(Object.entries(releases).map(([label,r])=>[label,r.binding.shell_sha256])),final:recovered,download_faults:downloads.filter(r=>r.fault),online_event_method:'DOM online lifecycle event; actual HTTP asset failures; no registration.update or skipWaiting call from tests',closed_app_background_update_guaranteed:false,actual_iphone_devices:false};
  }catch(error){
    console.log(JSON.stringify({schema:'qikvrt-client-update-failure/v1',error:error.message,controls,download_faults:downloads.filter(r=>r.fault),states:await Promise.all((context?.pages()||[]).map(page=>readback(page).catch(()=>null)))}));
    throw error;
  }finally{await context?.close();if(!netClosed)await new Promise(resolve=>server.close(resolve));}
}
let browser,activePage;
async function stopOrigin(child){if(child.exitCode!==null)return;await new Promise(resolve=>{child.once('exit',resolve);child.kill();});}
const output=process.env.QIKVRT_OFFLINE_EVIDENCE_DIR||'/tmp/qikvrt-offline-browser';await mkdir(output,{recursive:true});
const errors=[],checks=[];
try{const [one,two]=await Promise.all([serve(Number(process.env.QIKVRT_OFFLINE_PORT_A||8765)),serve(Number(process.env.QIKVRT_OFFLINE_PORT_B||8766))]);const engine=process.env.QIKVRT_OFFLINE_ENGINE==='webkit'?webkit:chromium,profile=resolve(output,'persistent-browser-profile'),options={headless:true,viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true,...(process.env.QIKVRT_BROWSER_EXECUTABLE?{executablePath:process.env.QIKVRT_BROWSER_EXECUTABLE}:{}),args:engine===chromium?['--no-sandbox']:[]};
  const context=await engine.launchPersistentContext(profile,options);browser=context.browser();const page=await context.newPage();activePage=page;page.on('pageerror',e=>errors.push(e.message));await page.goto(one);await page.getByTestId('shell-ready').filter({hasText:'vollständig'}).waitFor();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);checks.push('390px layout has no horizontal overflow');
  await page.getByRole('button',{name:'Arbeitskopie anlegen',exact:true}).click();await page.getByTestId('editor-text').fill('offline-first\n');await page.getByTestId('save').click();await page.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();
  const first=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();const text=await(await r.file('personal/arbeitsnotiz.md')).text();r.close();return {head:h.id,text};});assert.equal(first.text,'offline-first\n');checks.push('UI edit commits and reads back real IndexedDB bytes');
  await stopOrigin(servers[0]);if(engine===chromium)await context.setOffline(true);const outage=await page.evaluate(async()=>{try{await fetch('/uncached-network-control',{cache:'no-store'});return false;}catch{return true;}});assert.equal(outage,true);await page.reload();await page.getByTestId('shell-ready').filter({hasText:'vollständig'}).waitFor();assert.equal((await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();r.close();return h.id;})),first.head);checks.push('origin is stopped, an uncached fetch fails, and cached application navigation survives reload');
  await page.getByTestId('editor-text').fill('edited while offline');await page.getByTestId('save').click();await page.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();checks.push('offline UI writes survive storage readback');
  const result=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();let h=await r.head();const n=1048576*3+71,raw=new Uint8Array(n);for(let i=0;i<n;i++)raw[i]=i%251;h=await r.save('binary/three-chunks.bin',new Blob([raw]),{expected:h.id});const read=new Uint8Array(await(await r.file('binary/three-chunks.bin')).arrayBuffer());if(read.length!==n||read.some((v,i)=>v!==i%251))throw Error('BINARY_DRIFT');const report=await r.verify();const pack=await r.exportArchive();const text=await pack.text();r.close();return {report,text};});assert.equal(result.report.files,2);checks.push('multi-block binary contents and full history are verified');
  await context.setOffline(false);await serve(Number(process.env.QIKVRT_OFFLINE_PORT_A||8765));const second=await context.newPage();activePage=second;second.on('pageerror',e=>errors.push(e.message));await second.goto(two);await second.getByTestId('shell-ready').filter({hasText:'vollständig'}).waitFor();const beforeEmpty=await second.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();r.close();return h;});assert.equal(beforeEmpty,null);checks.push('different origins have separate local repositories');
  const imported=await second.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const result=await r.importArchive(new Blob([text]));const report=await r.verify();r.close();return {result,report};},result.text);assert.equal(imported.report.head,result.report.head);checks.push('complete export/import preserves exact revision and byte-level Git working tree');
  // Two offline devices diverge, import preserves the visible branch, explicit conflict decisions merge both histories.
  const branchA=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();const next=await r.save('personal/arbeitsnotiz.md',new Blob(['phone A']),{expected:h.id});r.close();return next.id;});
  const branchB=await second.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();await r.save('personal/arbeitsnotiz.md',new Blob(['phone B']),{expected:h.id});const pack=await r.exportArchive();r.close();return pack.text();});
  const merged=await page.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const imported=await r.importArchive(new Blob([text]));const unchanged=(await r.head()).id;const plan=await r.mergePlan(imported.incoming);let refused=false;try{await r.merge(imported.incoming);}catch(e){refused=e.message==='MERGE_CONFLICT_REQUIRES_DECISION';}const merged=await r.merge(imported.incoming,{'personal/arbeitsnotiz.md':'incoming'});const body=await(await r.file('personal/arbeitsnotiz.md')).text();const report=await r.verify();const pack=await r.exportArchive();r.close();return {imported,unchanged,conflicts:plan.conflicts.length,refused,merged,body,report,pack:await pack.text()};},branchB);assert.equal(merged.imported.state,'DIVERGENT_IMPORTED');assert.equal(merged.unchanged,branchA);assert.equal(merged.conflicts,1);assert.equal(merged.refused,true);assert.equal(merged.body,'phone B');assert.equal(merged.merged.snapshot.parents.length,2);checks.push('divergence never overwrites; explicit merge preserves two parents and chosen conflict');
  await second.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();await r.importArchive(new Blob([text]));const report=await r.verify();r.close();return report;},merged.pack).then(report=>assert.equal(report.head,merged.report.head));checks.push('merged stand transfers back to second origin without losing history');
  const negative=await page.evaluate(async text=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const head=(await r.head()).id;const lines=text.trimEnd().split('\n');const index=lines.findIndex(l=>JSON.parse(l).type==='block');const row=JSON.parse(lines[index]);row.data='eA==';lines[index]=JSON.stringify(row);let damaged=false,truncated=false,wrong=false;try{await r.importArchive(new Blob([lines.join('\n')+'\n']));}catch{damaged=true;}try{await r.importArchive(new Blob([text.slice(0,text.lastIndexOf('\n',text.length-2)+1)]));}catch{truncated=true;}const alien=JSON.parse(text.split('\n')[0]);alien.repository_id='another/repository';try{await r.importArchive(new Blob([JSON.stringify(alien)+'\n'+text.slice(text.indexOf('\n')+1)]));}catch{wrong=true;}const after=(await r.head()).id;r.close();return {damaged,truncated,wrong,head,after};},merged.pack);assert.deepEqual([negative.damaged,negative.truncated,negative.wrong],[true,true,true]);assert.equal(negative.after,negative.head);checks.push('tamper, truncation and repository-identity mismatch preserve the admitted head');
  const race=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const a=await Repository.open(),b=await Repository.open(),h=await a.head();const results=await Promise.allSettled([a.save('race/a.txt',new Blob(['a']),{expected:h.id}),b.save('race/b.txt',new Blob(['b']),{expected:h.id})]);a.close();b.close();return results.map(r=>({status:r.status,error:r.reason?.message}));});assert.equal(race.filter(r=>r.status==='fulfilled').length,1);assert.equal(race.find(r=>r.status==='rejected').error,'CONCURRENT_REPOSITORY_CHANGE');checks.push('two-tab writes use an atomic expected-head lease');
  const mismatch=await page.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open(),h=await r.head();const f=h.snapshot.files.find(f=>f.chunks.length);const tx=r.db.transaction('blocks','readwrite');tx.objectStore('blocks').put(new Blob(['corrupt']),f.chunks[0].sha256);await new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onabort=reject;});let refused=false;try{await r.verify();}catch(e){refused=e.message==='CONTENT_READBACK_MISMATCH';}r.close();return refused;});assert.equal(mismatch,true);checks.push('fresh stored-byte tampering blocks verification');
  // Independent cold browser process reopens persisted second-origin storage.
  const large=await second.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const h=await r.head();r.close();return h.id;});await second.screenshot({path:resolve(output,'iphone-layout.png'),fullPage:true});await context.close();await stopOrigin(servers[1]);const reopened=await engine.launchPersistentContext(profile,options);browser=reopened.browser();if(engine===chromium)await reopened.setOffline(true);const cold=await reopened.newPage();activePage=cold;cold.on('pageerror',e=>errors.push(e.message));await cold.goto(two);await cold.getByTestId('shell-ready').filter({hasText:'vollständig'}).waitFor();const fresh=await cold.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const report=await r.verify();r.close();return report;});assert.equal(fresh.head,large);checks.push('browser process closes and restarts with origin still stopped and the same verified durable repository');
  let completeSource=null;
  if(process.env.QIKVRT_COMPLETE_REPOSITORY){
    // Filesystem -> actual browser File -> streaming gzip -> independently verified full Git tree.
    await reopened.setOffline(false);const three=await serve(Number(process.env.QIKVRT_OFFLINE_PORT_C||8767)),full=await reopened.newPage();activePage=full;full.on('pageerror',e=>errors.push(e.message));await full.goto(three);
    await full.getByTestId('shell-ready').filter({hasText:'vollständig'}).waitFor();await full.waitForFunction(()=>!document.querySelector('[data-testid=archive-import]').disabled);
    await full.getByTestId('archive-import').setInputFiles(process.env.QIKVRT_COMPLETE_REPOSITORY);
    await full.getByRole('status').filter({hasText:'Repository-Stand vollständig geprüft und lokal übernommen.'}).waitFor({timeout:600000});
    completeSource=await full.evaluate(async()=>{const {Repository}=await import('./repository.js');const r=await Repository.open();const report=await r.verify(),head=await r.head();r.close();return {...report,source:head.snapshot.source,git_tree_sha1:head.snapshot.git_tree_sha1};});
    const receipt=JSON.parse(await readFile(resolve(dirname(process.env.QIKVRT_COMPLETE_REPOSITORY),'RECEIPT.json'),'utf8'));
    assert.equal(completeSource.head,receipt.snapshot);assert.equal(completeSource.git_tree_sha1,receipt.source_tree);assert.equal(completeSource.files,receipt.files);assert.equal(completeSource.bytes,receipt.source_bytes);
    await full.getByLabel('Datei suchen',{exact:true}).fill('docs/monitor/offline/');assert.equal(await full.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await full.screenshot({path:resolve(output,'complete-repository-iphone-layout.png'),fullPage:true});
    checks.push('complete frozen repository gzip imports through the real React file chooser and verifies all source bytes, native Git tree and populated mobile layout');
  }
  const updates=await updateControls(engine,options);checks.push(...updates.controls);console.log(JSON.stringify(updates));
  assert.deepEqual(errors,[]);await writeFile(resolve(output,'browser-readback.json'),JSON.stringify({schema:'qikvrt-offline-browser-readback/v1',engine:engine===webkit?'webkit':'chromium',mobile_layout:{width:390,height:844},actual_iphone_devices:false,offline_disruption:{origin_server_stopped:true,uncached_network_request_failed:true,playwright_offline_flag:engine===chromium,webkit_offline_emulation:'Excluded from acceptance after native internal error; upstream microsoft/playwright#42775'},complete_source:completeSource,automatic_updates:updates,checks,check_count:checks.length,second_origin_final_head:large,console_errors:errors,native_execution:false,main_effect:false},null,2)+'\n');console.log(JSON.stringify({checks:checks.length,engine:engine===webkit?'webkit':'chromium',actual_iphone_devices:false,output}));
}catch(error){let state;try{state=await activePage?.evaluate(()=>({url:location.href,online_hint:navigator.onLine,controlled:!!navigator.serviceWorker.controller,text:document.body.innerText.slice(0,3000)}));await activePage?.screenshot({path:resolve(output,'failure.png'),fullPage:true});}catch{}await writeFile(resolve(output,'failure.json'),JSON.stringify({error:error.message,stack:error.stack,checks,console_errors:errors,state},null,2)+'\n');throw error;}finally{await browser?.close();for(const child of servers)child.kill();}
