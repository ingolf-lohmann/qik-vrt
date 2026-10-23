/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
// Simulated DOM/HTTP controller checks; no rendered-browser acceptance claim.
'use strict';
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
class Element {
  constructor(){this.value='';this.files=[];this.children=[];this.disabled=false;this.textContent='';this.events={};this.classList={toggle(){}};}
  addEventListener(name,fn){this.events[name]=fn;}
  append(node){this.children.push(node);}
  replaceChildren(){this.children=[];}
}
function harness(mode='offline',failure=null){
  const elements=new Map(),objects=new Map(),calls=[];
  const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  get('text').value='Alles q.e.d.\r\nGrüße ♾️ e\u0301';get('persist').disabled=true;get('recover').disabled=true;
  let expectedRaw=new TextEncoder().encode(get('text').value),expectedHash=null;
  const subject={repository:'synthetic/local-fixture',pr:1,head:'a'.repeat(40),tree:'b'.repeat(40)};
  const context=vm.createContext({console,crypto:webcrypto,TextEncoder,TextDecoder,Uint8Array,DataView,Blob,
    btoa:globalThis.btoa,location:{protocol:mode==='offline'?'file:':'http:',hostname:mode==='offline'?'':'127.0.0.1'},
    document:{getElementById:get,createElement:()=>new Element()},window:{addEventListener(){}},
    URL:{createObjectURL(blob){const id='blob:fixture:'+objects.size;objects.set(id,blob);return id;},revokeObjectURL(id){objects.delete(id);}},
    async fetch(url,init={}){
      calls.push({url,...init});
      if(url==='/api/temdd/subject')return{ok:true,json:async()=>({subject})};
      if(url.endsWith('/prepare')){
        if(failure==='auth')return{ok:false,status:403,json:async()=>({reason:'synthetic authentication refusal'})};
        return{ok:true,json:async()=>({record_hash:'01'.repeat(32),commit_token:'synthetic-ticket'})};
      }
      if(url.endsWith('/commit')){
        if(failure==='lost')throw Error('synthetic lost commit response');
        return{ok:true,json:async()=>({state:'RESULT_PERSISTED'})};
      }
      if(url.includes('/receipts/'))return{ok:true,json:async()=>({execution:{payload:{result:{payload_sha256:expectedHash}}}})};
      if(url.endsWith('/data'))return{ok:true,arrayBuffer:async()=>Uint8Array.from(failure==='wrong-bytes'?[0]:expectedRaw).buffer};
      throw Error('Unexpected URL '+url);
    }});
  vm.runInContext(fs.readFileSync('docs/terminal/morse/codec.js','utf8'),context);
  vm.runInContext(fs.readFileSync('docs/terminal/morse/ui.js','utf8'),context);
  return{get,objects,calls,context,async encode(){await get('encode').events.click();expectedHash=get('hash').textContent;},
    async click(id){await get(id).events.click();},get raw(){return expectedRaw;}};
}
(async()=>{
  const offline=harness();await offline.encode();
  assert.match(offline.get('status').textContent,/Bytegleich/);assert.equal(offline.get('persist').disabled,true);
  let original=offline.get('downloads').children.find(a=>a.download==='qikvrt-result.bin');
  assert.deepEqual(new Uint8Array(await offline.objects.get(original.href).arrayBuffer()),offline.raw);
  offline.get('morse').value+=' -';offline.get('morse').events.input();await offline.click('decode');
  assert.match(offline.get('status').textContent,/Zurückgewiesen/);assert.equal(offline.get('downloads').children.length,0);
  assert.equal(offline.calls.length,0);
  const valid=harness('http');await valid.encode();await valid.click('persist');
  assert.match(valid.get('status').textContent,/unabhängig zurückgelesen/);
  assert.equal(valid.calls.filter(c=>c.url.endsWith('/commit')).length,1);
  assert.ok(valid.calls.find(c=>c.url.endsWith('/data')));
  const prepared=valid.calls.find(c=>c.url.endsWith('/prepare')),committed=valid.calls.find(c=>c.url.endsWith('/commit'));
  assert.equal(prepared.body,committed.body);assert.match(committed.headers['Effect-Ack-Request'],/mode=commit, hash=:/);
  const wrong=harness('http','wrong-bytes');await wrong.encode();await wrong.click('persist');
  assert.match(wrong.get('status').textContent,/Speicherantwort offen/);
  assert.ok(!wrong.get('downloads').children.some(a=>a.download==='qikvrt-native-receipt.json'));
  const auth=harness('http','auth');await auth.encode();await auth.click('persist');
  assert.match(auth.get('status').textContent,/Nicht gespeichert/);assert.equal(auth.get('persist').disabled,false);
  const lost=harness('http','lost');await lost.encode();await lost.click('persist');
  assert.equal(lost.get('recover').disabled,false);assert.equal(lost.get('persist').disabled,true);
  await lost.click('recover');await new Promise(resolve=>setTimeout(resolve,10));
  assert.match(lost.get('status').textContent,/unabhängig zurückgelesen/);
  assert.equal(lost.calls.filter(c=>c.url.endsWith('/commit')).length,1);
  console.log('PASS: 5 Morse controller scenarios; simulated DOM/HTTP, actual codec and byte downloads; no rendered-browser claim.');
})().catch(error=>{console.error(error);process.exitCode=1;});
