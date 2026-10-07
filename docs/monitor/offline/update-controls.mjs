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
async function until(test){const end=Date.now()+30000;while(!await test()){if(Date.now()>end)throw Error('UPDATE_CONTROL_TIMEOUT');await pause(100);}}
export async function updateControls(engine, output, here, options) {
  const worker=await readFile(resolve(here,'service-worker.js'),'utf8');
  const assets=JSON.parse(worker.match(/ASSETS=(\{[^\n]+\});/)[1]);
  const template=await readFile(resolve(here,'service-worker.template.js'),'utf8');
  const original=new Map(await Promise.all(Object.keys(assets).map(async name=>[name,await readFile(resolve(here,name))])));
  const build=tag=>{
    const files=new Map(original);
    if(tag!=='A')files.set('client.js',Buffer.concat([files.get('client.js'),Buffer.from('\n// bounded release fixture '+tag+'\n')]));
    const hashes=Object.fromEntries([...files].sort(([a],[b])=>a<b?-1:a>b?1:0).map(([name,data])=>[name,hash(data)]));
    const id=hash(JSON.stringify(hashes));
    files.set('service-worker.js',Buffer.from(tag==='A'?worker:template.replaceAll('__SHELL_ID__',id).replace('__ASSETS__',JSON.stringify(hashes))));
    return {id,files};
  };
  const releases=Object.fromEntries(['A','B','C','D'].map(tag=>[tag,build(tag)]));
  let current=releases.A,fault=null,port,context,server,active;
  const requests=[],checks=[],errors=[],prefix='/update-fixture/';
  async function serve(){server=createServer((req,res)=>{
    const path=new URL(req.url,'http://localhost').pathname.slice(prefix.length);
    requests.push({path,release:current.id,fault:fault?.type||null});
    if(fault?.path===path&&fault.type==='disconnect'){req.socket.destroy();return;}
    if(path==='hold.html'){res.writeHead(200,{'content-type':'text/html','cache-control':'no-store'});res.end('<!doctype html><p>Non-cooperating client</p>');return;}
    const data=current.files.get(path||'index.html');
    if(!data){res.writeHead(404);res.end();return;}
    res.writeHead(200,{'content-type':path.endsWith('.js')?'text/javascript':path.endsWith('.css')?'text/css':path.endsWith('.svg')?'image/svg+xml':path.endsWith('.webmanifest')?'application/manifest+json':'text/html','cache-control':'no-store'});
    res.end(fault?.path===path&&fault.type==='tamper'?Buffer.from('damaged update'):data);
  });await new Promise(resolve=>server.listen(port||0,'127.0.0.1',resolve));port=server.address().port;return 'http://127.0.0.1:'+port+prefix;}
  async function stop(){server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
  const ready=async page=>{await page.getByTestId('shell-ready').filter({hasText:'vollständig'}).waitFor();await page.waitForFunction(()=>!document.querySelector('[data-testid=editor-text]').disabled);};
  const version=page=>page.getByTestId('release-version').textContent();
  const report=page=>page.evaluate(async()=>{const src=document.querySelector('script[type=module]').src;const {Repository}=await import(new URL('repository.js',src));const r=await Repository.open();try{return await r.verify();}finally{r.close();}});
  const interval=async page=>page.clock.fastForward(310000);
  const eventCheck=async(page,event='online')=>{await page.clock.fastForward(70000);await page.evaluate(name=>window.dispatchEvent(new Event(name)),event);};
  const waiting=page=>page.evaluate(async()=>!!(await navigator.serviceWorker.getRegistration()).waiting);
  const sameVersion=async(page,id)=>assert.equal(await version(page),id);
  const adopted=async(page,id)=>{await page.waitForFunction(id=>document.querySelector('[data-testid=release-version]')?.textContent===id,id);await ready(page);};
  try {
    const url=await serve(),profile=resolve(output,'update-browser-profile');
    context=await engine.launchPersistentContext(profile,options);
    const one=await context.newPage();active=one;one.on('pageerror',e=>errors.push(e.message));await one.clock.install();await one.goto(url);await ready(one);
    assert.equal(await version(one),releases.A.id);
    await one.getByRole('button',{name:'Arbeitskopie anlegen',exact:true}).click();
    await one.getByTestId('editor-text').fill('confirmed before release switch\n');await one.getByTestId('save').click();
    await one.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();const before=await report(one);
    const draftA='unconfirmed α\n🛰️\n',draftB='parallel draft β\n';
    await one.getByTestId('editor-path').fill('personal/draft-A.md');await one.getByTestId('editor-text').fill(draftA);
    const two=await context.newPage();two.on('pageerror',e=>errors.push(e.message));await two.goto(url);await ready(two);
    await two.getByTestId('editor-path').fill('personal/draft-B.md');await two.getByTestId('editor-text').fill(draftB);

    current=releases.B;fault={path:'repository.js',type:'tamper'};const count=requests.length;
    await interval(one);await until(()=>requests.slice(count).some(r=>r.path==='repository.js'));
    await until(async()=>!await one.evaluate(async()=>!!(await navigator.serviceWorker.getRegistration()).installing));
    await sameVersion(one,releases.A.id);assert.equal(await waiting(one),false);assert.deepEqual(await report(one),before);
    assert.equal(await one.getByTestId('editor-text').inputValue(),draftA);checks.push('five-minute active-session check rejects a SHA-256-damaged release without head/draft changes');

    fault={path:'repository.js',type:'disconnect'};const dropped=requests.length;await interval(one);
    await until(()=>requests.slice(dropped).some(r=>r.path==='repository.js'));
    await until(async()=>!await one.evaluate(async()=>!!(await navigator.serviceWorker.getRegistration()).installing));
    await sameVersion(one,releases.A.id);assert.equal(await waiting(one),false);assert.deepEqual(await report(one),before);
    checks.push('interrupted asset transfer cannot install or expose a partial release');

    fault=null;const peer=await context.newPage();await peer.goto(url+'hold.html');
    await eventCheck(one,'focus');await until(()=>waiting(one));await pause(8500);
    await sameVersion(one,releases.A.id);await sameVersion(two,releases.A.id);
    assert.equal(await one.getByTestId('editor-text').isEnabled(),true);
    checks.push('focus event stages a complete release; a non-cooperating peer holds activation and timeout unlocks editing');
    await peer.close();await eventCheck(one,'online');
    await adopted(one,releases.B.id);await adopted(two,releases.B.id);
    assert.equal(await one.getByTestId('editor-text').inputValue(),draftA);assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);
    assert.equal(await one.getByTestId('editor-path').inputValue(),'personal/draft-A.md');assert.equal(await two.getByTestId('editor-path').inputValue(),'personal/draft-B.md');
    assert.deepEqual(await report(one),before);
    checks.push('online recovery switches two clients automatically and restores distinct unsaved paths/text with unchanged confirmed history');
    const pinned=await one.evaluate(async id=>{const scripts=[...document.scripts].filter(s=>s.src).map(s=>s.src);const old=await fetch('__qikvrt_release__/'+id+'/client.js');return {scripts,old:await old.text(),status:old.status};},releases.A.id);
    assert.ok(pinned.scripts.every(src=>src.includes('__qikvrt_release__/'+releases.B.id+'/')));assert.equal(pinned.status,200);assert.equal(pinned.old,original.get('client.js').toString());
    checks.push('release-qualified resources retain old exact bytes after claim; relative modules cannot mix releases');

    // The normal UI write is held in progress, rather than replacing the update
    // predicate with a mocked busy flag. Activation must wait for the operation.
    await one.evaluate(async()=>{const {Repository}=await import(new URL('repository.js',document.querySelector('script[type=module]').src));const save=Repository.prototype.save;
      Repository.prototype.save=async function(...args){window.pendingSaveEntered=true;await new Promise(resolve=>{window.finishPendingSave=resolve;});return save.apply(this,args);};});
    await one.getByTestId('save').click();await one.waitForFunction(()=>window.pendingSaveEntered);
    current=releases.C;await interval(one);await until(()=>waiting(one));await pause(1000);await sameVersion(one,releases.B.id);
    await one.evaluate(()=>window.finishPendingSave());await one.getByRole('status').filter({hasText:'gespeichert und zurückgelesen'}).waitFor();
    const saved=await report(one);assert.notEqual(saved.head,before.head);assert.equal(saved.revisions,before.revisions+1);
    checks.push('an in-flight real UI save holds activation until its new revision is committed and read back');

    await two.evaluate(()=>{window.realTransaction=IDBDatabase.prototype.transaction;IDBDatabase.prototype.transaction=function(names,mode,...rest){if(mode==='readwrite'&&[names].flat().includes('refs'))throw new DOMException('Test quota boundary','QuotaExceededError');return window.realTransaction.call(this,names,mode,...rest);};});
    await interval(one);await pause(1500);await sameVersion(one,releases.B.id);await sameVersion(two,releases.B.id);assert.deepEqual(await report(one),saved);
    checks.push('failed strict IndexedDB checkpoint blocks release adoption without losing the unconfirmed peer draft');
    await two.evaluate(()=>{IDBDatabase.prototype.transaction=window.realTransaction;});await interval(one);
    await adopted(one,releases.C.id);await adopted(two,releases.C.id);assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(one),saved);
    checks.push('recovered storage resumes the same waiting release and preserves the latest confirmed revision');

    const hold=await context.newPage();await hold.goto(url+'hold.html');current=releases.D;await interval(one);await until(()=>waiting(one));await pause(8500);
    await one.evaluate(async id=>{const cache=await caches.open('qikvrt-offline-'+id);const url=new URL('repository.js',location.href);await cache.put(url,new Response('damaged staged cache'));},releases.D.id);
    await stop();await hold.close();await interval(one);await pause(1500);await sameVersion(one,releases.C.id);assert.deepEqual(await report(one),saved);
    checks.push('post-install cache corruption is reverified before skipWaiting; network loss holds the healthy predecessor');
    await serve();await eventCheck(one,'pageshow');await adopted(one,releases.D.id);await adopted(two,releases.D.id);
    assert.equal(await two.getByTestId('editor-text').inputValue(),draftB);assert.deepEqual(await report(one),saved);
    checks.push('pageshow recovery rebuilds damaged staging only from complete digest-bound bytes and adopts without manual reload');

    // Corruption of a retained old namespace must fail closed, never substitute D.
    const rejected=await one.evaluate(async id=>{const cache=await caches.open('qikvrt-offline-'+id);await cache.put(new URL('client.js',location.href),new Response('tampered retained release'));return (await fetch('__qikvrt_release__/'+id+'/client.js')).status;},releases.A.id);
    assert.equal(rejected,503);checks.push('corrupt retained-version asset returns 503 instead of a different release or network fallback');
    await pause(700);await stop();await context.close();context=null;
    context=await engine.launchPersistentContext(profile,options);const restored=await context.newPage();active=restored;restored.on('pageerror',e=>errors.push(e.message));
    await restored.goto(url);await ready(restored);assert.deepEqual(await report(restored),saved);
    checks.push('browser process restart with stopped origin restores the final verified release and confirmed IndexedDB history');
    assert.deepEqual(errors,[]);
    const result={schema:'qikvrt-offline-update-browser-readback/v1',releases:Object.fromEntries(Object.entries(releases).map(([tag,r])=>[tag,r.id])),checks,check_count:checks.length,requests,confirmed_before:before,confirmed_after:saved,console_errors:errors,physical_ios_witness:false,background_update_guarantee:false};
    await writeFile(resolve(output,'update-readback.json'),JSON.stringify(result,null,2)+'\n');return result;
  }catch(error){let state;try{state=await active?.evaluate(()=>({url:location.href,text:document.body.innerText,controlled:!!navigator.serviceWorker.controller}));await active?.screenshot({path:resolve(output,'update-failure.png'),fullPage:true});}catch{}
    await writeFile(resolve(output,'update-failure.json'),JSON.stringify({error:error.message,stack:error.stack,checks,requests,state,errors},null,2)+'\n');throw error;
  }finally{await context?.close();if(server?.listening)await stop();}
}
