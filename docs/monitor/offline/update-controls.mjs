// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Extends the existing real-browser controls with mutable HTTPS-origin fixtures
// (loopback secure context). Fixture releases are tests, never publication claims.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(test){const end=Date.now()+30000;for(;;){let passed=false;try{passed=await test();}catch(e){if(!e.message.includes('Execution context was destroyed'))throw e;}if(passed)return;if(Date.now()>end)throw Error('UPDATE_CONTROL_TIMEOUT');await pause(100);}}
export async function updateControls(engine, output, here, options) {
  const worker=await readFile(resolve(here,'service-worker.js'),'utf8');
  const assets=JSON.parse(worker.match(/ASSETS=(\{[^\n]+\});/)[1]);
  const template=await readFile(resolve(here,'service-worker.template.js'),'utf8');
  const original=new Map(await Promise.all(Object.keys(assets).map(async name=>[name,await readFile(resolve(here,name))])));
  const build=tag=>{
    const files=new Map(original);
    if(tag!=='A')files.set('client.js',Buffer.concat([files.get('client.js'),Buffer.from('\n// bounded release fixture '+(tag==='E'?'D':tag)+'\n')]));
    if(tag==='F')files.set('client.js',Buffer.concat([files.get('client.js'),Buffer.from('\nconst = invalid post-activation syntax;\n')]));
    if(tag==='G')files.set('client.js',Buffer.concat([Buffer.from("throw Error('QIKVRT_INJECTED_BOOT_FAILURE');\n"),files.get('client.js')]));
    if(tag==='H')files.set('client.js',Buffer.from(files.get('client.js').toString().replace(/ReactDOM\.createRoot[^\n]+/, '// injected missing UI readiness')));
    const hashes=Object.fromEntries([...files].sort(([a],[b])=>a<b?-1:a>b?1:0).map(([name,data])=>[name,hash(data)]));
    const nextTemplate=template+(tag==='E'?'\n// bounded worker-only release fixture\n':'');
    const templateSha=hash(nextTemplate),id=hash(JSON.stringify({assets:hashes,worker_template_sha256:templateSha}));
    files.set('service-worker.js',Buffer.from(tag==='A'?worker:nextTemplate.replaceAll('__SHELL_ID__',id).replace('__ASSETS__',JSON.stringify(hashes)).replace('__WORKER_TEMPLATE_SHA256__',templateSha)));
    return {id,files};
  };
  const releases=Object.fromEntries(['A','B','C','D','E','F','G','H','I'].map(tag=>[tag,build(tag)]));
  let current=releases.A,fault=null,port,context,server,active;
  const requests=[],checks=[],errors=[],prefix='/update-fixture/',clocked=new WeakSet();
  async function serve(){server=createServer((req,res)=>{
    const path=new URL(req.url,'http://localhost').pathname.slice(prefix.length);
    requests.push({path,release:current.id,fault:fault?.type||null});
    if(fault?.path===path&&fault.type==='disconnect'){req.socket.destroy();return;}
    if(path==='hold.html'){res.writeHead(200,{'content-type':'text/html','cache-control':'no-store'});res.end('<!doctype html><p>Non-cooperating client</p>');return;}
    if(path==='runtime-fault.js'){res.writeHead(200,{'content-type':'text/javascript','cache-control':'no-store'});res.end("throw Error('QIKVRT_INJECTED_LATE_FAILURE');");return;}
    const data=current.files.get(path||'index.html');
    if(!data){res.writeHead(404);res.end();return;}
    res.writeHead(200,{'content-type':path.endsWith('.js')?'text/javascript':path.endsWith('.css')?'text/css':path.endsWith('.svg')?'image/svg+xml':path.endsWith('.webmanifest')?'application/manifest+json':'text/html','cache-control':'no-store'});
    res.end(fault?.path===path&&fault.type==='tamper'?Buffer.from('damaged update'):data);
  });await new Promise(resolve=>server.listen(port||0,'127.0.0.1',resolve));port=server.address().port;return 'http://127.0.0.1:'+port+prefix;}
  async function stop(){server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
  const ready=async page=>{await page.getByTestId('shell-ready').filter({hasText:/^Client vollständig im Offline-Cache geprüft\.$/}).waitFor();await page.waitForFunction(()=>!document.querySelector('[data-testid=editor-text]').disabled);};
  const healthy=async(page,clock=false)=>{await until(async()=>{if(clock)await page.clock.runFor(600);return page.evaluate(()=>document.documentElement.dataset.qikvrtHealth===document.querySelector('[data-testid=release-version]')?.textContent);});};
  const version=page=>page.getByTestId('release-version').textContent();
  const report=page=>page.evaluate(async()=>{const src=document.querySelector('script[type=module]').src;const {Repository}=await import(new URL('repository.js',src));const r=await Repository.open();try{return await r.verify();}finally{r.close();}});
  // Cadence advances timers once, after the foreground check has settled.
  // Event controls advance Date only: jumping live MessageChannel timeouts
  // while a real worker is reading cache bytes creates a false clock race.
  const interval=async page=>{await page.clock.fastForward(310000);};
  const eventCheck=async(page,event='online')=>{const now=await page.evaluate(()=>Date.now());await page.clock.setSystemTime(now+70000);await page.bringToFront();await page.evaluate(name=>window.dispatchEvent(new Event(name)),event);};
  const waiting=page=>page.evaluate(async()=>!!(await navigator.serviceWorker.getRegistration()).waiting);
  const sameVersion=async(page,id)=>assert.equal(await version(page),id);
  const adopted=async(page,id)=>{await page.waitForFunction(id=>document.querySelector('[data-testid=release-version]')?.textContent===id,id);await ready(page);await healthy(page,clocked.has(page));};
  try {
    const url=await serve(),profile=resolve(output,'update-browser-profile');
    context=await engine.launchPersistentContext(profile,options);
    const one=await context.newPage();clocked.add(one);active=one;one.on('pageerror',e=>errors.push(e.message));await one.clock.install();await one.goto(url);await ready(one);
    assert.equal(await version(one),releases.A.id);
    await healthy(one,true);
    assert.equal(await one.evaluate(async()=>{const src=document.querySelector('script[type=module]').src;return (await import(new URL('updates.js',src))).release;}),releases.A.id);
    await one.getByRole('button',{name:'Arbeitskopie anlegen',exact:true}).click();
    await one.getByTestId('editor-text').fill('confirmed before release switch\n');await one.getByTestId('save').click();
    await one.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();const before=await report(one);
    const draftA='unconfirmed α\n🛰️\n',draftB='parallel draft β\n';
    await one.getByTestId('editor-path').fill('personal/draft-A.md');await one.getByTestId('editor-text').fill(draftA);
    const two=await context.newPage();two.on('pageerror',e=>errors.push(e.message));await two.goto(url);await ready(two);
    await two.getByTestId('editor-path').fill('personal/draft-B.md');await two.getByTestId('editor-text').fill(draftB);
    await healthy(two);

    await one.bringToFront();await one.waitForFunction(()=>document.querySelector('[data-testid=update-state]')?.getAttribute('data-state')==='current');
    current=releases.B;fault={path:'repository.js',type:'tamper'};const count=requests.length;
    await interval(one);await until(()=>requests.slice(count).some(r=>r.path==='repository.js'));
    await until(async()=>!await one.evaluate(async()=>!!(await navigator.serviceWorker.getRegistration()).installing));
    await sameVersion(one,releases.A.id);assert.equal(await waiting(one),false);assert.deepEqual(await report(one),before);
    assert.equal(await one.getByTestId('editor-text').inputValue(),draftA);checks.push('five-minute active-session check rejects a SHA-256-damaged release without head/draft changes');

    fault={path:'repository.js',type:'disconnect'};const dropped=requests.length;await eventCheck(one);
    await until(()=>requests.slice(dropped).some(r=>r.path==='repository.js'));
    await until(async()=>!await one.evaluate(async()=>!!(await navigator.serviceWorker.getRegistration()).installing));
    await sameVersion(one,releases.A.id);assert.equal(await waiting(one),false);assert.deepEqual(await report(one),before);
    checks.push('interrupted asset transfer cannot install or expose a partial release');

    const peer=await context.newPage();await peer.goto(url+'hold.html');fault=null;
    await eventCheck(one,'focus');await until(()=>waiting(one));await one.waitForFunction(()=>document.querySelector('[data-testid=update-state]')?.getAttribute('data-state')==='preparing');assert.equal(await one.getByTestId('editor-text').isDisabled(),true);assert.equal(await one.getByLabel('Datei suchen',{exact:true}).isDisabled(),true);await pause(8500);
    await sameVersion(one,releases.A.id);await sameVersion(two,releases.A.id);
    assert.equal(await one.getByTestId('editor-text').isEnabled(),true);
    checks.push('focus event stages a complete release; a non-cooperating peer holds activation and timeout unlocks editing');
    await peer.close();await eventCheck(one,'online');
    await adopted(one,releases.B.id);await adopted(two,releases.B.id);
    await healthy(one,true);await healthy(two);
    assert.equal(await one.getByTestId('editor-text').inputValue(),draftA);assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);
    assert.equal(await one.getByTestId('editor-path').inputValue(),'personal/draft-A.md');assert.equal(await two.getByTestId('editor-path').inputValue(),'personal/draft-B.md');
    assert.deepEqual(await report(one),before);
    checks.push('online recovery switches two clients automatically and restores distinct unsaved paths/text with unchanged confirmed history');
    const pinned=await one.evaluate(async id=>{const scripts=[...document.scripts].filter(s=>s.src).map(s=>s.src);const old=await fetch('__qikvrt_release__/'+id+'/client.js');return {scripts,old:await old.text(),status:old.status};},releases.A.id);
    assert.ok(pinned.scripts.every(src=>src.includes('__qikvrt_release__/'+releases.B.id+'/')||src.includes('__qikvrt_health__/')));assert.equal(pinned.status,200);assert.equal(pinned.old,original.get('client.js').toString());
    checks.push('release-qualified resources retain old exact bytes after claim; relative modules cannot mix releases');

    // The normal UI write is held in progress, rather than replacing the update
    // predicate with a mocked busy flag. Activation must wait for the operation.
    await one.evaluate(async()=>{const {Repository}=await import(new URL('repository.js',document.querySelector('script[type=module]').src));const save=Repository.prototype.save;
      Repository.prototype.save=async function(...args){window.pendingSaveEntered=true;await new Promise(resolve=>{window.finishPendingSave=resolve;});return save.apply(this,args);};});
    await one.getByTestId('save').click();await one.waitForFunction(()=>window.pendingSaveEntered);
    current=releases.C;await eventCheck(one);await until(()=>waiting(one));await pause(1000);await sameVersion(one,releases.B.id);
    await one.evaluate(()=>window.finishPendingSave());await one.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();
    const saved=await report(one);assert.notEqual(saved.head,before.head);assert.equal(saved.revisions,before.revisions+1);
    checks.push('an in-flight real UI save holds activation until its new revision is committed and read back');

    await two.evaluate(()=>{window.realTransaction=IDBDatabase.prototype.transaction;IDBDatabase.prototype.transaction=function(names,mode,...rest){if(mode==='readwrite'&&[names].flat().includes('refs'))throw new DOMException('Test quota boundary','QuotaExceededError');return window.realTransaction.call(this,names,mode,...rest);};});
    await eventCheck(one);await pause(1500);await sameVersion(one,releases.B.id);await sameVersion(two,releases.B.id);assert.deepEqual(await report(one),saved);
    checks.push('failed strict IndexedDB checkpoint blocks release adoption without losing the unconfirmed peer draft');
    await two.evaluate(()=>{IDBDatabase.prototype.transaction=window.realTransaction;document.querySelector('[data-testid=editor-text]').dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true,data:'β'}));});
    await eventCheck(one);await pause(1500);await sameVersion(one,releases.B.id);await sameVersion(two,releases.B.id);
    assert.equal(await two.getByTestId('editor-text').isEnabled(),true);
    checks.push('active IME composition in one peer holds every client on the predecessor without disabling its editor');
    await two.evaluate(()=>document.querySelector('[data-testid=editor-text]').dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'β'})));
    await adopted(one,releases.C.id);await adopted(two,releases.C.id);assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(one),saved);
    checks.push('compositionend resumes the already-staged release after input quiescence without manual reload or another update request');

    await one.bringToFront();await one.getByRole('button',{name:'Sicherung vorbereiten',exact:true}).click();await one.getByRole('button',{name:'Fertigen Stand teilen',exact:true}).waitFor();
    await one.getByTestId('editor-text').focus();await one.getByTestId('editor-text').evaluate(editor=>editor.setSelectionRange(2,6,'backward'));
    await pause(1300);
    const exportBefore=await one.evaluate(async()=>{const src=document.querySelector('script[type=module]').src;const {Repository,digest}=await import(new URL('repository.js',src));const r=await Repository.open();try{const d=await r.session(sessionStorage.getItem('qikvrt-editor-session'));return {name:d.prepared.name,size:d.prepared.size,sha256:await digest(await d.prepared.arrayBuffer())};}finally{r.close();}});

    const hold=await context.newPage();await hold.goto(url+'hold.html');current=releases.D;await eventCheck(one);await until(()=>waiting(one));await pause(8500);
    await one.evaluate(async id=>{const cache=await caches.open('qikvrt-offline-'+id);const url=new URL('repository.js',location.href);await cache.put(url,new Response('damaged staged cache'));},releases.D.id);
    await stop();await hold.close();await eventCheck(one);await pause(1500);await sameVersion(one,releases.C.id);assert.deepEqual(await report(one),saved);
    checks.push('post-install cache corruption is reverified before skipWaiting; network loss holds the healthy predecessor');
    await serve();await eventCheck(one,'pageshow');await adopted(one,releases.D.id);await adopted(two,releases.D.id);
    assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(one),saved);
    checks.push('pageshow recovery rebuilds damaged staging only from complete digest-bound bytes and adopts without manual reload');
    await one.getByRole('button',{name:'Fertigen Stand teilen',exact:true}).waitFor();
    const exportAfter=await one.evaluate(async()=>{const src=document.querySelector('script[type=module]').src;const {Repository,digest}=await import(new URL('repository.js',src));const r=await Repository.open();try{const d=await r.session(sessionStorage.getItem('qikvrt-editor-session'));return {name:d.prepared.name,size:d.prepared.size,sha256:await digest(await d.prepared.arrayBuffer())};}finally{r.close();}});
    assert.deepEqual(exportAfter,exportBefore);assert.deepEqual(await one.getByTestId('editor-text').evaluate(e=>[e.selectionStart,e.selectionEnd,e.selectionDirection]),[2,6,'backward']);
    checks.push('prepared export retains exact bytes/name and backward caret selection survives the version handoff');

    assert.notEqual(releases.D.id,releases.E.id);assert.deepEqual(releases.D.files.get('client.js'),releases.E.files.get('client.js'));
    current=releases.E;await eventCheck(one);await adopted(one,releases.E.id);await adopted(two,releases.E.id);assert.deepEqual(await report(one),saved);
    await healthy(one,true);await healthy(two);
    const retained=await one.evaluate(async id=>{const response=await fetch('__qikvrt_release__/'+id+'/repository.js');return {status:response.status,body:await response.text()};},releases.D.id);
    assert.equal(retained.status,200);assert.equal(retained.body,releases.D.files.get('repository.js').toString());
    checks.push('worker-only release receives a distinct cache, is automatically adopted and keeps the predecessor namespace readable');

    // Fully hashed, installed releases fail only AFTER skipWaiting/claim. The
    // fault is in the actual executed application, not in the update predicate.
    await one.clock.resume();clocked.delete(one);
    const injected=[];one.removeAllListeners('pageerror');two.removeAllListeners('pageerror');
    one.on('pageerror',e=>injected.push(e.message));two.on('pageerror',e=>injected.push(e.message));
    for(const tag of ['F','G','H']){
      current=releases[tag];await eventCheck(one);
      await until(()=>requests.some(r=>r.release===current.id&&r.path==='client.js'));
      await until(async()=>one.evaluate(async id=>{const c=await caches.open('qikvrt-health-v1'),s=await(await c.match(new URL('.qikvrt-health.json',location.href))).json();return s.failed.includes(id);},current.id));
      await adopted(one,releases.E.id);await adopted(two,releases.E.id);await healthy(one);await healthy(two);
      assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(one),saved);
      const denied=await one.evaluate(async()=>{const r=await navigator.serviceWorker.getRegistration();const c=new MessageChannel();return new Promise(resolve=>{c.port1.onmessage=({data})=>{c.port1.close();resolve(data);};r.active.postMessage({type:'QIKVRT_UPDATE_REQUEST'},[c.port2]);});});assert.equal(denied.state,'UPDATE_REJECTED');
      checks.push('post-activation '+tag+' fault rolls both clients back to E, retains distinct draft/history, and quarantines the failed release');
    }
    assert.ok(injected.some(e=>e.includes('QIKVRT_INJECTED_BOOT_FAILURE')));assert.ok(injected.some(e=>/Unexpected|Syntax|identifier/.test(e)));
    current=releases.I;await eventCheck(one);await adopted(one,releases.I.id);await adopted(two,releases.I.id);await healthy(one);await healthy(two);
    await one.getByTestId('editor-text').fill('late runtime draft after health receipt');await one.clock.runFor(1300);
    // A real same-origin script throws after the application health receipt.
    // Script execution is independent of the context-wide cadence timer mock.
    await two.evaluate(()=>{const script=document.createElement('script');script.src=new URL('runtime-fault.js',location.href);document.head.append(script);});
    await until(()=>injected.some(e=>e.includes('QIKVRT_INJECTED_LATE_FAILURE')));
    await adopted(one,releases.E.id);await adopted(two,releases.E.id);await healthy(one);await healthy(two);
    assert.equal(await one.getByTestId('editor-text').inputValue(),'late runtime draft after health receipt');assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(one),saved);
    checks.push('runtime exception after positive health receipt checkpoints newer work and recovers both clients without altering confirmed history');
    assert.ok(injected.some(e=>e.includes('QIKVRT_INJECTED_LATE_FAILURE')));
    one.removeAllListeners('pageerror');two.removeAllListeners('pageerror');one.on('pageerror',e=>errors.push(e.message));two.on('pageerror',e=>errors.push(e.message));

    const checkpointGuard=await one.evaluate(async()=>{const src=document.querySelector('script[type=module]').src;const {Repository}=await import(new URL('repository.js',src));const r=await Repository.open();try{
      const id=sessionStorage.getItem('qikvrt-editor-session'),pointer=await r.get('refs','editor:last'),peer=crypto.randomUUID();
      await r.checkpointSession(peer,{path:'personal/background.md',text:'background draft',prepared:null},{foreground:false});
      const unchanged=await r.get('refs','editor:last')===pointer,row=await r.get('refs','editor:'+id),data=new Uint8Array(await row.prepared.arrayBuffer());data[0]^=1;
      await new Promise((resolve,reject)=>{const tx=r.db.transaction('refs','readwrite',{durability:'strict'});tx.objectStore('refs').put({...row,prepared:new Blob([data],{type:row.prepared.type})},'editor:'+peer);tx.oncomplete=resolve;tx.onabort=reject;});
      let rejected=false;try{await r.session(peer);}catch(e){rejected=e.message==='EDITOR_CHECKPOINT_READBACK_MISMATCH';}return {unchanged,rejected};
    }finally{r.close();}});
    assert.deepEqual(checkpointGuard,{unchanged:true,rejected:true});
    checks.push('background checkpoints cannot replace foreground recovery; same-size prepared-byte corruption is rejected');

    // Corruption of a retained old namespace must fail closed, never substitute D.
    const rejected=await one.evaluate(async id=>{const cache=await caches.open('qikvrt-offline-'+id);await cache.put(new URL('client.js',location.href),new Response('tampered retained release'));return (await fetch('__qikvrt_release__/'+id+'/client.js')).status;},releases.A.id);
    assert.equal(rejected,503);checks.push('corrupt retained-version asset returns 503 instead of a different release or network fallback');
    await one.bringToFront();await one.getByTestId('editor-text').fill(draftA);await pause(1300);
    await stop();await context.close();context=null;
    context=await engine.launchPersistentContext(profile,options);const restored=await context.newPage();active=restored;restored.on('pageerror',e=>errors.push(e.message));
    await restored.goto(url);await ready(restored);await sameVersion(restored,releases.E.id);await healthy(restored);assert.deepEqual(await report(restored),saved);
    assert.equal(await restored.getByTestId('editor-text').inputValue(),draftA);
    checks.push('cold process reopen automatically restores the last foreground draft without using a background checkpoint');
    checks.push('browser process restart with stopped origin restores the final verified release and confirmed IndexedDB history');
    const recovery=restored.getByTestId('recover-draft').filter({hasText:'personal/draft-B.md'}).first();await recovery.click();await restored.getByRole('status').filter({hasText:'Gesicherter Entwurf geöffnet.'}).waitFor();assert.equal(await restored.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(restored),saved);checks.push('orphaned parallel draft remains recoverable through the UI after process restart loses the tab session key');
    await pause(1300);
    const damaged=await restored.evaluate(async()=>{const src=document.querySelector('script[type=module]').src;const {Repository}=await import(new URL('repository.js',src));const r=await Repository.open();try{
      const id=await r.get('refs','editor:last'),row=await r.get('refs','editor:'+id);row.value.state.text+=' damaged checkpoint';
      await new Promise((resolve,reject)=>{const tx=r.db.transaction('refs','readwrite',{durability:'strict'});tx.objectStore('refs').put(row,'editor:'+id);tx.oncomplete=resolve;tx.onabort=reject;});
      let rejected=false;try{await r.session(id);}catch(e){rejected=e.message==='EDITOR_CHECKPOINT_READBACK_MISMATCH';}return {id,rejected};
    }finally{r.close();}});assert.equal(damaged.rejected,true);
    await context.close();context=null;context=await engine.launchPersistentContext(profile,options);
    const intact=await context.newPage();active=intact;intact.on('pageerror',e=>errors.push(e.message));await intact.goto(url);await ready(intact);assert.deepEqual(await report(intact),saved);
    await intact.getByRole('alert').filter({hasText:'EDITOR_CHECKPOINT_READBACK_MISMATCH'}).waitFor();
    const inventory=await intact.evaluate(async id=>{const src=document.querySelector('script[type=module]').src;const {Repository}=await import(new URL('repository.js',src));const r=await Repository.open();try{return (await r.sessions()).find(row=>row.id===id);}finally{r.close();}},damaged.id);
    assert.equal(inventory.unavailable,true);
    const healthyDraft=intact.getByTestId('recover-draft').filter({hasText:'personal/draft-B.md'}).first();await healthyDraft.click();await intact.getByRole('status').filter({hasText:'Gesicherter Entwurf geöffnet.'}).waitFor();assert.equal(await intact.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(intact),saved);
    checks.push('corrupt foreground checkpoint fails closed on offline cold restart while intact revisions and older verified drafts remain accessible');
    assert.deepEqual(errors,[]);
    const result={schema:'qikvrt-offline-update-browser-readback/v1',releases:Object.fromEntries(Object.entries(releases).map(([tag,r])=>[tag,r.id])),checks,check_count:checks.length,requests,confirmed_before:before,confirmed_after:saved,console_errors:errors,injected_errors:injected,recovery_health:await intact.evaluate(async()=>await(await(await caches.open('qikvrt-health-v1')).match(new URL('.qikvrt-health.json',location.href))).json()),physical_ios_witness:false,background_update_guarantee:false};
    await writeFile(resolve(output,'update-readback.json'),JSON.stringify(result,null,2)+'\n');return result;
  }catch(error){let state;try{state=await active?.evaluate(async()=>{const registration=await navigator.serviceWorker.getRegistration();return {url:location.href,text:document.body.innerText,controlled:!!navigator.serviceWorker.controller,hidden:document.hidden,now:Date.now(),active:registration?.active?.state,waiting:registration?.waiting?.state,installing:registration?.installing?.state};});await active?.screenshot({path:resolve(output,'update-failure.png'),fullPage:true});}catch{}
    await writeFile(resolve(output,'update-failure.json'),JSON.stringify({error:error.message,stack:error.stack,checks,requests,state,errors},null,2)+'\n');throw error;
  }finally{await context?.close();if(server?.listening)await stop();}
}
