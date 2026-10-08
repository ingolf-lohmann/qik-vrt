// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
const SHELL='0358e8e1c6232e928945961152ecdf708effabc2ec4385cbe354f1bebd93606c', ASSETS={"client.js":"83f35ecb0ab2b373cae1ee365563c09f777e62bb4d5cc9f9680725cc907c6757","git-hash.js":"308dbe4365f71a37c900175ccc619b370863b6505236c4fb4f3e3001baabd8bb","icon.svg":"dc09b8a107eb3919dc203253cba602fe39bd1723adcf679b9cc9b68e8035da53","index.html":"2281a5a5cabacad9f2278b34fa4d978d8c2669b13fbb3bd4c2e05aafe43940b3","manifest.webmanifest":"419262c911585c4dcc0edcf71497319fb3200b55c704c87029102b43900a99ad","repository.js":"bb11532077b2f044d56e7193fd3c2dc6ff1655fa337fe2e248edecb58e158476","style.css":"c2e106dbb8afcd8b4a684a73f067fbc43bfdbfaf89257685d749c766945f2aa6","updates.js":"6f13c243255da93c3e47611bfd3b166d548b0b375e9b992f89b79669e5520821","vendor/REACT_LICENSE.txt":"da6d3703ed11cbe42bd212c725957c98da23cbff1998c05fa4b3d976d1a58e93","vendor/react-runtime.js":"fb03ce4c32ffbcacd04d55efb547e85610805571ee8025636bd7992c80db9cca"};
const PREFIX='qikvrt-offline-', CACHE=PREFIX+SHELL, NAMESPACE='__qikvrt_release__/';
const scope=new URL(self.registration.scope), metadata=new URL('.qikvrt-release.json',scope);
const hex=b=>[...new Uint8Array(b)].map(v=>v.toString(16).padStart(2,'0')).join('');
const digest=async b=>hex(await crypto.subtle.digest('SHA-256',b));
const canonical=map=>JSON.stringify(Object.fromEntries(Object.entries(map).sort(([a],[b])=>a<b?-1:a>b?1:0)));
async function valid(response,sha){return response?.ok&&!response.redirected&&await digest(await response.clone().arrayBuffer())===sha;}
async function manifest(shell) {
  if(!/^[a-f0-9]{64}$/.test(shell))throw Error('INVALID_RELEASE');
  const cache=await caches.open(PREFIX+shell),response=await cache.match(metadata);
  if(!response?.ok)throw Error('INCOMPLETE_RELEASE');
  const assets=await response.json();
  if(!assets||Array.isArray(assets)||Object.keys(assets).length>64||!Object.hasOwn(assets,'index.html')||Object.entries(assets).some(([path,sha])=>!Object.hasOwn(ASSETS,path)||!/^[a-f0-9]{64}$/.test(sha)))throw Error('INVALID_RELEASE_MANIFEST');
  if(await digest(new TextEncoder().encode(canonical(assets)))!==shell)throw Error('RELEASE_BINDING_MISMATCH');
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
    await cache.put(metadata,new Response(canonical(ASSETS),{headers:{'content-type':'application/json'}}));
    if(!await complete())throw Error('OFFLINE_SHELL_READBACK_MISMATCH');
  }catch(error){if(!present)await caches.delete(CACHE);throw error;}
}
self.addEventListener('install',event=>event.waitUntil(install()));
// No unconditional skipWaiting: live clients must confirm recoverable state.
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
const windows=async()=> (await self.clients.matchAll({type:'window',includeUncontrolled:true})).filter(client=>client.url.startsWith(scope.href));
const notify=(clients,message)=>{for(const client of clients)client.postMessage(message);};
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
    // A known damaged/evicted staging cache can be rebuilt only from the same
    // fully verified release bytes. A failed repair leaves the active worker.
    if(!await complete())await install();
    const replies=await Promise.all(clients.map(client=>prepare(client,attempt)));
    const confirmed=new Set(clients.filter((_,i)=>replies[i]).map(c=>c.id));
    if((await windows()).some(c=>!confirmed.has(c.id)))return {state:'WAITING_FOR_CLIENTS'};
    if(!await complete())throw Error('INCOMPLETE_RELEASE');
    if((await windows()).some(c=>!confirmed.has(c.id)))return {state:'WAITING_FOR_CLIENTS'};
    await self.skipWaiting();committed=true;return {state:'ACTIVATING',shell:SHELL};
  }catch{return {state:'UPDATE_REJECTED'};}
  finally{if(!committed)notify(clients,{type:'QIKVRT_UPDATE_ABORT',attempt});}
}
self.addEventListener('message',event=>{
  if(!event.source?.url?.startsWith(scope.href))return;
  if(event.data?.type==='QIKVRT_OFFLINE_READY')event.waitUntil((async()=>{
    event.ports[0]?.postMessage({ready:await complete(),cache:CACHE,shell:SHELL});
  })());
  if(event.data?.type==='QIKVRT_UPDATE_REQUEST')event.waitUntil((async()=>{
    if(!preparing)preparing=prepareAll().finally(()=>{preparing=null;});
    event.ports[0]?.postMessage(await preparing);
  })());
});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.origin!==scope.origin||!url.pathname.startsWith(scope.pathname))return;
  let path=url.pathname.slice(scope.pathname.length)||'index.html',shell=SHELL;
  const pinned=path.startsWith(NAMESPACE);
  if(pinned){const parts=path.slice(NAMESPACE.length).split('/');shell=parts.shift();path=parts.join('/')||'index.html';}
  if(!pinned&&!Object.hasOwn(ASSETS,path))return;
  event.respondWith((async()=>{
    try {
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
      const html=(await response.text()).replace(/\b(href|src)="([^"]+)"/g,(all,attribute,target)=>Object.hasOwn(assets,target)?attribute+'="'+new URL(NAMESPACE+shell+'/'+target,scope).href+'"':all);
      const headers=new Headers(response.headers);headers.delete('content-length');headers.set('x-qikvrt-shell',shell);
      return new Response(html,{status:200,headers});
    }catch{return new Response('Offline-Client unvollständig oder verändert',{status:503,headers:{'content-type':'text/plain;charset=utf-8'}});}
  })());
});
