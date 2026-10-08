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
function worker({bad=false,disconnect=false,clients=[],arriving=false}={}) {
  const stores=new Map(),listeners=new Map();let skipped=0,censuses=0;
  const cache={async has(name){return stores.has(name);},async delete(name){return stores.delete(name);},async open(name){if(!stores.has(name))stores.set(name,new Map());const map=stores.get(name);return {async match(url){return map.get(String(url))?.clone();},async put(url,response){map.set(String(url),response.clone());}};}};
  const self={registration:{scope},location:{origin:'https://example.test'},clients:{async claim(){},async matchAll(){if(arriving&&++censuses>1)return [...clients,{id:'late',url:scope+'hold.html'}];return clients;}},addEventListener:(name,fn)=>listeners.set(name,fn),async skipWaiting(){skipped++;}};
  const fetch=async url=>{const path=String(url).slice(scope.length);if(disconnect&&path==='repository.js')throw Error('NETWORK_INTERRUPTED');return networkURL(new Response(bad&&path==='repository.js'?'bad':data[path]),String(url));};
  vm.runInNewContext(template.replace('__SHELL_ID__',id).replace('__ASSETS__',JSON.stringify(assets)).replace('__WORKER_TEMPLATE_SHA256__',templateSha),{self,caches:cache,fetch,crypto,URL,Response,Headers,TextEncoder,Uint8Array,MessageChannel,setTimeout,clearTimeout});
  const dispatch=(name,event={})=>{let result;listeners.get(name)({...event,waitUntil:p=>{result=p;},respondWith:p=>{result=p;}});return result;};
  const message=async type=>{let result;await dispatch('message',{source:{url:scope},data:{type},ports:[{postMessage:value=>{result=value;}}]});return result;};
  return {dispatch,message,stores,cache,skipped:()=>skipped};
}
const peer=(ready,id='one')=>({id,url:scope,postMessage(message,ports=[]){if(message.type==='QIKVRT_UPDATE_PREPARE'){ports[0].postMessage({ready,shell:'a'.repeat(64),attempt:message.attempt});ports[0].close();}}});
test('bad or interrupted install leaves an existing active cache and no complete candidate',async()=>{
  for(const failure of [{bad:true},{disconnect:true}]){const w=worker(failure);w.stores.set('predecessor',new Map());await assert.rejects(w.dispatch('install'));assert.equal(w.stores.has('predecessor'),true);assert.equal(w.stores.has('qikvrt-offline-'+id),false);assert.equal(w.skipped(),0);}
});
test('complete install is read back but cannot skip the live-client barrier',async()=>{
  const w=worker({clients:[peer(false)]});await w.dispatch('install');assert.equal((await w.message('QIKVRT_OFFLINE_READY')).ready,true);assert.equal(w.skipped(),0);assert.equal((await w.message('QIKVRT_UPDATE_REQUEST')).state,'WAITING_FOR_CLIENTS');assert.equal(w.skipped(),0);
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
