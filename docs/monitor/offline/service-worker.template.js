// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0; Copyright 2026 Ingolf Lohmann.
// Implementation contribution: OpenAI Codex. HTTPS origin is the trust authority.
const CACHE='qikvrt-offline-__SHELL_ID__',ASSETS=__ASSETS__;
const hex=b=>[...new Uint8Array(b)].map(v=>v.toString(16).padStart(2,'0')).join('');
async function valid(response,sha){return response?.ok&&!response.redirected&&hex(await crypto.subtle.digest('SHA-256',await response.clone().arrayBuffer()))===sha;}
async function ready(){
  const cache=await caches.open(CACHE);
  for(const [path,sha]of Object.entries(ASSETS))if(!await valid(await cache.match(new URL(path,self.registration.scope)),sha))return false;
  return true;
}
self.addEventListener('install',event=>event.waitUntil((async()=>{
  const present=await caches.has(CACHE);
  try{
    const rows=[];
    for(const [path,sha]of Object.entries(ASSETS)){
      const url=new URL(path,self.registration.scope),response=await fetch(url,{cache:'no-store',credentials:'same-origin'});
      if(new URL(response.url).origin!==self.location.origin||!await valid(response,sha))throw Error('OFFLINE_SHELL_DIGEST_MISMATCH');
      rows.push([url,response]);
    }
    const cache=await caches.open(CACHE);
    for(const [url,response]of rows)await cache.put(url,response);
    if(!await ready())throw Error('OFFLINE_SHELL_READBACK_MISMATCH');
    // Legacy clients safely defer until their windows close: this worker cannot
    // retroactively recover another page's uncheckpointed in-memory drafts.
    if(!self.registration.active)await self.skipWaiting();
  }catch(e){if(!present)await caches.delete(CACHE);throw e;}
})()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
const inScope=client=>client.url.startsWith(self.registration.scope);
async function windows(){return (await self.clients.matchAll({type:'window',includeUncontrolled:true})).filter(inScope);}
function prepare(client){return new Promise(resolve=>{
  const channel=new MessageChannel();
  const finish=ready=>{clearTimeout(timer);channel.port1.close();resolve(ready);};
  const timer=setTimeout(()=>finish(false),5000);
  channel.port1.onmessage=({data})=>finish(data?.ready===true&&data.cache===CACHE);
  try{client.postMessage({type:'QIKVRT_PREPARE_UPDATE',cache:CACHE},[channel.port2]);}catch{finish(false);}
});}
let activation;
async function activate(){
  const clients=await windows();
  try{
    if(!(await Promise.all(clients.map(prepare))).every(Boolean))throw Error('CLIENT_CHECKPOINT_PENDING');
    const current=await windows(),ids=new Set(clients.map(c=>c.id));
    if(current.some(c=>!ids.has(c.id))||!await ready())throw Error('UPDATE_READBACK_PENDING');
    await self.skipWaiting();
    return {state:'ACTIVATING',cache:CACHE};
  }catch{
    for(const client of clients)client.postMessage({type:'QIKVRT_UPDATE_RELEASE',cache:CACHE});
    return {state:'HELD',cache:CACHE};
  }
}
self.addEventListener('message',event=>{
  if(event.data?.type==='QIKVRT_OFFLINE_READY')event.waitUntil((async()=>{
    event.ports[0]?.postMessage({ready:await ready(),cache:CACHE});
  })());
  if(event.data?.type==='QIKVRT_ACTIVATE_UPDATE'&&event.source&&inScope(event.source))event.waitUntil((async()=>{
    if(!activation)activation=activate().finally(()=>{activation=null;});
    event.ports[0]?.postMessage(await activation);
  })());
});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url),scope=new URL(self.registration.scope);
  if(url.origin!==scope.origin||!url.pathname.startsWith(scope.pathname))return;
  const path=url.pathname.slice(scope.pathname.length)||'index.html';
  if(!Object.hasOwn(ASSETS,path))return;
  event.respondWith((async()=>{
    const response=await(await caches.open(CACHE)).match(new URL(path,scope));
    return await valid(response,ASSETS[path])?response:new Response('Offline-Client unvollständig oder verändert',{status:503});
  })());
});
