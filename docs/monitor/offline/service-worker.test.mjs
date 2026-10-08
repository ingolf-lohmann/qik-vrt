// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
const template=await readFile(new URL('./service-worker.template.js',import.meta.url),'utf8');
const data={'index.html':'<script type="module" src="client.js"></script>','client.js':'import "./repository.js";','repository.js':'export const revision="A";'};
const assets=Object.fromEntries(Object.entries(data).sort().map(([p,v])=>[p,createHash('sha256').update(v).digest('hex')]));
const templateSha=createHash('sha256').update(template).digest('hex');
const id=createHash('sha256').update(JSON.stringify({assets,worker_template_sha256:templateSha})).digest('hex'),scope='https://example.test/app/';
function networkURL(response,url){const clone=response.clone.bind(response);Object.defineProperty(response,'url',{value:url});response.clone=()=>networkURL(clone(),url);return response;}
function worker({bad=false,disconnect=false,clients=[],arriving=false,stores=new Map()}={}) {
  const listeners=new Map();let skipped=0,censuses=0;
  const cache={async has(name){return stores.has(name);},async delete(name){return stores.delete(name);},async open(name){if(!stores.has(name))stores.set(name,new Map());const map=stores.get(name);return {async match(url){return map.get(String(url))?.clone();},async put(url,response){map.set(String(url),response.clone());}};}};
  const self={registration:{scope},location:{origin:'https://example.test'},clients:{async claim(){},async matchAll(){if(arriving&&++censuses>1)return [...clients,{id:'late',url:scope+'hold.html'}];return clients;}},addEventListener:(name,fn)=>listeners.set(name,fn),async skipWaiting(){skipped++;}};
  const fetch=async url=>{const path=String(url).slice(scope.length);if(disconnect&&path==='repository.js')throw Error('NETWORK_INTERRUPTED');return networkURL(new Response(bad&&path==='repository.js'?'bad':data[path]),String(url));};
  vm.runInNewContext(template.replace('__SHELL_ID__',id).replace('__ASSETS__',JSON.stringify(assets)).replace('__WORKER_TEMPLATE_SHA256__',templateSha),{self,caches:cache,fetch,crypto,URL,Response,Headers,TextEncoder,Uint8Array,MessageChannel,setTimeout,clearTimeout});
  const dispatch=(name,event={})=>{let result;listeners.get(name)({...event,waitUntil:p=>{result=p;},respondWith:p=>{result=p;}});return result;};
  const message=async(type,extra={},client='one')=>{let result;await dispatch('message',{source:{url:scope,id:client},data:{type,...extra},ports:[{postMessage:value=>{result=value;}}]});return result;};
  return {dispatch,message,stores,cache,skipped:()=>skipped};
}
const peer=(ready,id='one')=>({id,url:scope,postMessage(message,ports=[]){if(message.type==='QIKVRT_UPDATE_PREPARE'){ports[0].postMessage({ready,shell:'a'.repeat(64),attempt:message.attempt});ports[0].close();}}});
test('bad or interrupted install leaves an existing active cache and no complete candidate',async()=>{
  for(const failure of [{bad:true},{disconnect:true}]){const w=worker(failure);w.stores.set('predecessor',new Map());await assert.rejects(w.dispatch('install'));assert.equal(w.stores.has('predecessor'),true);assert.equal(w.stores.has('qikvrt-offline-'+id),false);assert.equal(w.skipped(),0);}
});
test('health receipts bind navigation token, release and client; two peers must both pass',async()=>{
  const clients=[peer(true),peer(true,'two')],w=worker({clients});await w.dispatch('install');
  const nav=async client=>{await w.dispatch('fetch',{request:{method:'GET',mode:'navigate',url:scope},resultingClientId:client});return JSON.parse(await(await(await w.cache.open('qikvrt-health-v1')).match(scope+'.qikvrt-health.json')).text());};
  let state=await nav('one');const one=Object.keys(state.leases)[0];state=await nav('two');const two=Object.keys(state.leases).find(t=>t!==one);
  assert.equal((await w.message('QIKVRT_HEALTH_OK',{token:one,shell:id},'two')).accepted,false);
  assert.equal((await w.message('QIKVRT_HEALTH_OK',{token:one,shell:id},'one')).accepted,false);
  assert.equal((await w.message('QIKVRT_HEALTH_OK',{token:two,shell:id},'two')).accepted,true);
  assert.equal((await w.message('QIKVRT_HEALTH_OK',{token:one,shell:'f'.repeat(64)},'one')).accepted,false);
});
test('post-activation failure and cold-worker timeout select only complete retained healthy bytes and quarantine candidate',async()=>{
  for(const mode of ['failure','timeout']){
    const w=worker({clients:[peer(true)]});await w.dispatch('install');
    const old=createHash('sha256').update(JSON.stringify(assets)).digest('hex'),oldCache=await w.cache.open('qikvrt-offline-'+old);
    for(const [path,bytes]of Object.entries(data))await oldCache.put(scope+path,new Response(bytes));
    await oldCache.put(scope+'.qikvrt-release.json',new Response(JSON.stringify(assets)));
    const control=await w.cache.open('qikvrt-health-v1');
    await control.put(scope+'.qikvrt-health.json',new Response(JSON.stringify({good:old,failed:[],leases:{},pending:{shell:id,deadline:Date.now()+60000}})));
    await w.dispatch('fetch',{request:{method:'GET',mode:'navigate',url:scope},resultingClientId:'one'});
    const state=await(await control.match(scope+'.qikvrt-health.json')).json(),token=Object.keys(state.leases)[0];
    if(mode==='failure')assert.equal((await w.message('QIKVRT_HEALTH_FAILED',{shell:id,token})).recovery,true);
    else{state.pending.deadline=0;await control.put(scope+'.qikvrt-health.json',new Response(JSON.stringify(state)));}
    const cold=worker({stores:w.stores,clients:[peer(true)]});
    assert.equal((await cold.message('QIKVRT_OFFLINE_READY')).shell,old);
    assert.equal((await cold.message('QIKVRT_UPDATE_REQUEST')).state,'UPDATE_REJECTED');assert.equal(cold.skipped(),0);
    assert.equal((await(await control.match(scope+'.qikvrt-health.json')).json()).failed.includes(id),true);
    await oldCache.put(scope+'client.js',new Response('corrupted last healthy cache'));
    assert.equal((await cold.message('QIKVRT_OFFLINE_READY')).ready,false);
  }
});
test('complete install is read back but cannot skip the live-client barrier',async()=>{
  const w=worker({clients:[peer(false)]});await w.dispatch('install');assert.equal((await w.message('QIKVRT_OFFLINE_READY')).ready,true);assert.equal(w.skipped(),0);assert.equal((await w.message('QIKVRT_UPDATE_REQUEST')).state,'WAITING_FOR_CLIENTS');assert.equal(w.skipped(),0);
});
test('late failure after accepted health preserves the in-flight peer token and restores the previous healthy version',async()=>{
  const w=worker({clients:[peer(true),peer(true,'two')]});await w.dispatch('install');
  const old=createHash('sha256').update(JSON.stringify(assets)).digest('hex'),cache=await w.cache.open('qikvrt-offline-'+old);
  for(const [path,bytes]of Object.entries(data))await cache.put(scope+path,new Response(bytes));
  await cache.put(scope+'.qikvrt-release.json',new Response(JSON.stringify(assets)));
  const control=await w.cache.open('qikvrt-health-v1');
  await control.put(scope+'.qikvrt-health.json',new Response(JSON.stringify({good:id,previous:old,pending:null,failed:[],leases:{first:{shell:id,client:'one',ok:true},late:{shell:id,client:'two',ok:false}}})));
  assert.equal((await w.message('QIKVRT_HEALTH_FAILED',{shell:id,token:'first',reason:'error'},'one')).recovery,true);
  assert.equal((await w.message('QIKVRT_HEALTH_FAILED',{shell:id,token:'late',reason:'error'},'two')).recovery,true);
  assert.equal((await w.message('QIKVRT_OFFLINE_READY')).shell,old);
  const state=await(await control.match(scope+'.qikvrt-health.json')).json();assert.ok(state.leases.late);assert.equal(state.previous,null);assert.deepEqual(state.failed,[id]);
});
test('all prepared clients permit activation; a newly arriving client prevents it',async()=>{
  const w=worker({clients:[peer(true),peer(true,'two')]});await w.dispatch('install');assert.equal((await w.message('QIKVRT_UPDATE_REQUEST')).state,'ACTIVATING');assert.equal(w.skipped(),1);
  const racing=worker({clients:[peer(true)],arriving:true});await racing.dispatch('install');assert.equal((await racing.message('QIKVRT_UPDATE_REQUEST')).state,'WAITING_FOR_CLIENTS');assert.equal(racing.skipped(),0);
});
test('release namespace returns exact module bytes and rejects corrupt/unknown assets without fallback',async()=>{
  const w=worker();await w.dispatch('install');
  const fetch=path=>w.dispatch('fetch',{request:{method:'GET',url:scope+path}});
  const html=await (await fetch('')).text();assert.ok(html.includes(scope+'__qikvrt_release__/'+id+'/client.js'));
  assert.equal(await(await fetch('__qikvrt_release__/'+id+'/repository.js')).text(),data['repository.js']);
  assert.equal((await fetch('__qikvrt_release__/'+id+'/client.js')).url,'','module response must inherit the requested release URL rather than the cached network URL');
  const cache=await w.cache.open('qikvrt-offline-'+id);await cache.put(scope+'repository.js',new Response('corrupt'));
  assert.equal((await fetch('__qikvrt_release__/'+id+'/repository.js')).status,503);assert.equal((await fetch('__qikvrt_release__/'+id+'/missing.js')).status,503);
});
test('retained asset-only predecessor cache is still readable through its exact namespace',async()=>{
  const w=worker();await w.dispatch('install');
  const old=createHash('sha256').update(JSON.stringify(assets)).digest('hex');
  const cache=await w.cache.open('qikvrt-offline-'+old);
  for(const [path,bytes] of Object.entries(data))await cache.put(scope+path,new Response(bytes));
  await cache.put(scope+'.qikvrt-release.json',new Response(JSON.stringify(assets)));
  const response=await w.dispatch('fetch',{request:{method:'GET',url:scope+'__qikvrt_release__/'+old+'/repository.js'}});
  assert.equal(response.status,200);assert.equal(await response.text(),data['repository.js']);
});
