// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
const SHELL='__SHELL_ID__', ASSETS=__ASSETS__;
const TEMPLATE='__WORKER_TEMPLATE_SHA256__';
const PREFIX='qikvrt-offline-', CACHE=PREFIX+SHELL, NAMESPACE='__qikvrt_release__/';
const scope=new URL(self.registration.scope), metadata=new URL('.qikvrt-release.json',scope);
const hex=b=>[...new Uint8Array(b)].map(v=>v.toString(16).padStart(2,'0')).join('');
const digest=async b=>hex(await crypto.subtle.digest('SHA-256',b));
const canonical=value=>value&&typeof value==='object'?'{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+canonical(value[key])).join(',')+'}':JSON.stringify(value);
async function valid(response,sha){return response?.ok&&!response.redirected&&await digest(await response.clone().arrayBuffer())===sha;}
async function manifest(shell) {
  if(!/^[a-f0-9]{64}$/.test(shell))throw Error('INVALID_RELEASE');
  const cache=await caches.open(PREFIX+shell),response=await cache.match(metadata);
  if(!response?.ok)throw Error('INCOMPLETE_RELEASE');
  const binding=await response.json(),assets=binding.assets||binding;
  if(!assets||Array.isArray(assets)||Object.keys(assets).length>64||!Object.hasOwn(assets,'index.html')||Object.entries(assets).some(([path,sha])=>!Object.hasOwn(ASSETS,path)||!/^[a-f0-9]{64}$/.test(sha)))throw Error('INVALID_RELEASE_MANIFEST');
  // Retained #493 caches use the old asset-only identity; new releases bind
  // the worker template too, so a worker-only update cannot reuse its cache.
  if(binding.assets&&(!/^[a-f0-9]{64}$/.test(binding.worker_template_sha256||'')||(shell===SHELL&&binding.worker_template_sha256!==TEMPLATE)))throw Error('INVALID_WORKER_BINDING');
  if(await digest(new TextEncoder().encode(canonical(binding)))!==shell)throw Error('RELEASE_BINDING_MISMATCH');
  return {cache,assets};
}
async function complete(shell=SHELL) {
  try{const {cache,assets}=await manifest(shell);for(const [path,sha]of Object.entries(assets))if(!await valid(await cache.match(new URL(path,scope)),sha))return false;return true;}catch{return false;}
}
async function install() {
  const present=await caches.has(CACHE);
  if(await complete())return;
  try {
    const rows=[];
    for(const [path,sha]of Object.entries(ASSETS)) {
      const url=new URL(path,scope),response=await fetch(url,{cache:'no-store',credentials:'same-origin',redirect:'error'});
      if(new URL(response.url).origin!==scope.origin||!await valid(response,sha))throw Error('OFFLINE_SHELL_DIGEST_MISMATCH');
      rows.push([url,response]);
    }
    const cache=await caches.open(CACHE);
    for(const [url,response]of rows)await cache.put(url,response);
    await cache.put(metadata,new Response(canonical({assets:ASSETS,worker_template_sha256:TEMPLATE}),{headers:{'content-type':'application/json'}}));
    if(!await complete())throw Error('OFFLINE_SHELL_READBACK_MISMATCH');
  }catch(error){if(!present)await caches.delete(CACHE);throw error;}
}
self.addEventListener('install',event=>event.waitUntil(install()));
// No unconditional skipWaiting: live clients must confirm recoverable state.
self.addEventListener('activate',event=>event.waitUntil(serial(async()=>{
  const state=await journal();
  if(state.good!==SHELL&&!state.failed.includes(SHELL)){state.pending={shell:SHELL,deadline:Date.now()+60000};state.leases={};await saveJournal(state);}
  await selected();await self.clients.claim();
})));
const windows=async()=> (await self.clients.matchAll({type:'window',includeUncontrolled:true})).filter(client=>client.url.startsWith(scope.href));
const notify=(clients,message)=>{for(const client of clients)client.postMessage(message);};
// One origin/scope-bound journal; asset caches and Repository IndexedDB stay
// untouched. Every event reopens the journal, including a restarted worker.
const journalURL=new URL('.qikvrt-health.json',scope),GUARD='__qikvrt_health__/';
let operations=Promise.resolve();
function serial(action){const next=operations.then(action);operations=next.catch(()=>{});return next;}
async function journal(){const response=await(await caches.open('qikvrt-health-v1')).match(journalURL);if(!response)return {good:null,pending:null,failed:[],leases:{}};const state=await response.json();if(!Array.isArray(state.failed)||!state.leases||typeof state.leases!=='object')throw Error('INVALID_HEALTH_JOURNAL');return state;}
async function saveJournal(state){const cache=await caches.open('qikvrt-health-v1'),bytes=JSON.stringify(state);await cache.put(journalURL,new Response(bytes));if(await(await cache.match(journalURL)).text()!==bytes)throw Error('HEALTH_JOURNAL_READBACK');}
async function reject(state,shell){
  if(state.pending?.shell!==shell&&state.good!==shell)return;
  if(!state.failed.includes(shell))state.failed.push(shell);
  if(state.good===shell){state.good=state.previous||null;state.previous=null;}
  // Keep in-flight navigation tokens: a second client may load its guard
  // just after the first client's failure broadcast. Its own receipt still
  // needs an authenticated recovery response rather than a stranded page.
  state.pending=null;await saveJournal(state);
  notify(await windows(),{type:'QIKVRT_RECOVERY',shell:state.good});
}
async function selected(){
  const state=await journal();
  if(state.pending&&Date.now()>state.pending.deadline)await reject(state,state.pending.shell);
  const target=state.failed.includes(SHELL)?state.good:SHELL;
  if(!target||state.failed.includes(target)||!await complete(target))throw Error('NO_VERIFIED_RECOVERY');
  return target;
}
// This independent script executes before React/modules. CSP permits only the
// same-origin external script. Missing readiness, syntax errors and rejected
// startup promises cannot disable the watchdog by preventing module execution.
function healthGuard(shell,token,root){
  let stopped=false,checking=false,healthy=false;
  const call=message=>new Promise((resolve,reject)=>{const c=new MessageChannel(),t=setTimeout(()=>{c.port1.close();reject(Error('HEALTH_ACK_TIMEOUT'));},5000);c.port1.onmessage=({data})=>{clearTimeout(t);c.port1.close();resolve(data);};navigator.serviceWorker.controller.postMessage({...message,shell,token},[c.port2]);});
  const recover=async()=>{const checkpoint=globalThis.qikvrtRecoveryCheckpoint;if(typeof checkpoint==='function'){if(!await checkpoint())return;}else if(document.querySelector('[data-testid=editor-text]')?.disabled===false)return;location.replace(root);};
  const fail=async(reason='STARTUP_TIMEOUT')=>{if(stopped)return;stopped=true;clearInterval(timer);try{const result=await call({type:'QIKVRT_HEALTH_FAILED',reason:typeof reason==='string'?reason:reason.type});if(result?.recovery)await recover();}catch{}};
  window.addEventListener('error',fail,true);window.addEventListener('unhandledrejection',fail);
  navigator.serviceWorker.addEventListener('message',event=>{if(event.source===navigator.serviceWorker.controller&&event.data?.type==='QIKVRT_RECOVERY'&&!stopped){stopped=true;clearInterval(timer);recover().catch(()=>{});}});
  const timer=setInterval(async()=>{if(stopped||checking)return;checking=true;try{
    if(!healthy&&document.querySelector('[data-testid=shell-ready]')?.classList.contains('success')&&document.querySelector('[data-testid=release-version]')?.textContent===shell&&document.querySelector('[data-testid=editor-text]')){
      clearTimeout(timeout); // Ready but legitimately busy is not a startup failure.
      const src=new URL('__qikvrt_release__/'+shell+'/repository.js',root),{Repository}=await import(src),r=await Repository.open();try{await r.head();await r.sessions();}finally{r.close();}healthy=true;
    }
    if(healthy){const result=await call({type:'QIKVRT_HEALTH_OK'});if(result?.accepted){document.documentElement.dataset.qikvrtHealth=shell;clearTimeout(timeout);clearInterval(timer);}if(result?.recovery){stopped=true;await recover();}}
  }catch{await fail('READBACK_FAILED');}finally{checking=false;}},500);
  const timeout=setTimeout(fail,20000);
  window.addEventListener('pagehide',()=>{stopped=true;clearInterval(timer);clearTimeout(timeout);});
  window.addEventListener('pageshow',event=>{if(event.persisted)healthGuard(shell,token,root);});
}
async function healthMessage(event){
  const state=await journal(),lease=state.leases[event.data.token];
  if(!lease||lease.shell!==event.data.shell||lease.client!==event.source.id)return {accepted:false,recovery:!!state.good&&state.failed.includes(event.data.shell)};
  if(event.data.type==='QIKVRT_HEALTH_FAILED'){state.lastFailure={shell:lease.shell,reason:['STARTUP_TIMEOUT','READBACK_FAILED','error','unhandledrejection'].includes(event.data.reason)?event.data.reason:'UNSPECIFIED'};await reject(state,lease.shell);return {recovery:state.good&&state.failed.includes(lease.shell)};}
  if(state.failed.includes(lease.shell))return {recovery:!!state.good};
  lease.ok=true;
  const peers=await windows();
  const all=peers.length>0&&peers.every(client=>Object.values(state.leases).some(l=>l.client===client.id&&l.shell===lease.shell&&l.ok));
  if(all&&await complete(lease.shell)){if(state.good!==lease.shell){state.previous=state.good;state.good=lease.shell;}if(state.pending?.shell===lease.shell)state.pending=null;}
  await saveJournal(state);return {accepted:state.good===lease.shell};
}
function prepare(client,attempt) {return new Promise(resolve=>{
  const channel=new MessageChannel(),timer=setTimeout(()=>finish(false),8000);
  const finish=ready=>{clearTimeout(timer);channel.port1.close();resolve(ready);};
  channel.port1.onmessage=({data})=>finish(data?.ready===true&&data.attempt===attempt&&/^[a-f0-9]{64}$/.test(data.shell||''));
  try{client.postMessage({type:'QIKVRT_UPDATE_PREPARE',shell:SHELL,attempt},[channel.port2]);}catch{finish(false);}
});}
let preparing;
async function prepareAll() {
  const attempt=crypto.randomUUID(),clients=await windows();let committed=false;
  try {
    const health=await journal();
    if(health.failed.includes(SHELL)||health.pending||health.failed.length>=128)return {state:'UPDATE_REJECTED'};
    // A known damaged/evicted staging cache can be rebuilt only from the same
    // fully verified release bytes. A failed repair leaves the active worker.
    if(!await complete())await install();
    const replies=await Promise.all(clients.map(client=>prepare(client,attempt)));
    const confirmed=new Set(clients.filter((_,i)=>replies[i]).map(c=>c.id));
    if((await windows()).some(c=>!confirmed.has(c.id)))return {state:'WAITING_FOR_CLIENTS'};
    if(!await complete())throw Error('INCOMPLETE_RELEASE');
    if((await windows()).some(c=>!confirmed.has(c.id)))return {state:'WAITING_FOR_CLIENTS'};
    // No older release is called healthy just because its bytes are intact.
    if(health.good&&!await complete(health.good))throw Error('RECOVERY_CACHE_INCOMPLETE');
    await self.skipWaiting();committed=true;return {state:'ACTIVATING',shell:SHELL};
  }catch{return {state:'UPDATE_REJECTED'};}
  finally{if(!committed)notify(clients,{type:'QIKVRT_UPDATE_ABORT',attempt});}
}
self.addEventListener('message',event=>{
  if(!event.source?.url?.startsWith(scope.href))return;
  if(['QIKVRT_HEALTH_OK','QIKVRT_HEALTH_FAILED'].includes(event.data?.type))event.waitUntil(serial(async()=>event.ports[0]?.postMessage(await healthMessage(event))));
  if(event.data?.type==='QIKVRT_OFFLINE_READY')event.waitUntil((async()=>{
    try{const shell=await serial(selected);event.ports[0]?.postMessage({ready:await complete(shell),cache:PREFIX+shell,shell});}catch{event.ports[0]?.postMessage({ready:false});}
  })());
  if(event.data?.type==='QIKVRT_UPDATE_REQUEST')event.waitUntil((async()=>{
    // skipWaiting may wait for activate: do not queue activate behind the
    // very promise requesting it. Only the active worker writes the journal.
    if(!preparing)preparing=prepareAll().finally(()=>{preparing=null;});
    event.ports[0]?.postMessage(await preparing);
  })());
});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.origin!==scope.origin||!url.pathname.startsWith(scope.pathname))return;
  let path=url.pathname.slice(scope.pathname.length)||'index.html',shell=SHELL;
  if(path.startsWith(GUARD)){event.respondWith(serial(async()=>{const token=path.slice(GUARD.length).replace(/\.js$/,''),state=await journal(),lease=state.leases[token];if(!lease)return new Response('',{status:404});return new Response('('+healthGuard.toString()+')('+JSON.stringify(lease.shell)+','+JSON.stringify(token)+','+JSON.stringify(scope.href)+');',{headers:{'content-type':'text/javascript','cache-control':'no-store'}});}));return;}
  const pinned=path.startsWith(NAMESPACE);
  if(pinned){const parts=path.slice(NAMESPACE.length).split('/');shell=parts.shift();path=parts.join('/')||'index.html';}
  if(!pinned&&!Object.hasOwn(ASSETS,path))return;
  event.respondWith(serial(async()=>{
    try {
      if(!pinned)shell=await selected();
      const {cache,assets}=await manifest(shell);
      if(!Object.hasOwn(assets,path))throw Error('ASSET_NOT_IN_RELEASE');
      const response=await cache.match(new URL(path,scope));
      if(!await valid(response,assets[path]))throw Error('ASSET_DIGEST_MISMATCH');
      if(path==='manifest.webmanifest'){
        const data=await response.json();data.id=scope.href;data.start_url=scope.href;data.scope=scope.href;
        if(data.icons)data.icons=data.icons.map(icon=>({...icon,src:new URL(NAMESPACE+shell+'/'+icon.src,scope).href}));
        const headers=new Headers(response.headers);headers.delete('content-length');
        return new Response(JSON.stringify(data),{status:200,headers});
      }
      // A cached network Response retains its original URL. Rewrap the verified
      // bytes so import.meta.url / relative imports use the requested namespace.
      if(path!=='index.html')return new Response(response.body,{status:response.status,statusText:response.statusText,headers:response.headers});
      // Versioned resource URLs preserve relative imports across claim/restart.
      let html=(await response.text()).replace(/\b(href|src)="([^"]+)"/g,(all,attribute,target)=>Object.hasOwn(assets,target)?attribute+'="'+new URL(NAMESPACE+shell+'/'+target,scope).href+'"':all);
      if(event.request.mode==='navigate'){
        const state=await journal();if(state.failed.includes(shell))return Response.redirect(scope.href);
        const token=crypto.randomUUID();state.leases[token]={shell,client:event.resultingClientId||event.clientId,ok:false,started:Date.now()};
        // A resulting client is not necessarily enumerable until navigation
        // commits. Keep recent in-flight leases as well as every live client.
        const ids=new Set((await windows()).map(c=>c.id));ids.add(state.leases[token].client);for(const [id,l]of Object.entries(state.leases))if(!ids.has(l.client)&&Date.now()-(l.started||0)>60000)delete state.leases[id];
        if(Object.keys(state.leases).length>4096)throw Error('HEALTH_LEASE_CAPACITY');
        await saveJournal(state);html=html.replace('<title>','<script src="'+new URL(GUARD+token+'.js',scope).href+'"></script><title>');
      }
      const headers=new Headers(response.headers);headers.delete('content-length');headers.set('x-qikvrt-shell',shell);
      return new Response(html,{status:200,headers});
    }catch{return new Response('Offline-Client unvollständig oder verändert',{status:503,headers:{'content-type':'text/plain;charset=utf-8'}});}
  }));
});
