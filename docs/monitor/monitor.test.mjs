import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHmac, createHash, webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {MonitorStore, createMonitor, verifyWebhook, VERSION} from './server.mjs';
import './health-projection.js';

test('health separates failures, stale evidence, live runtime and client phase',()=>{
  const now=Date.now(), source={observed_at:new Date(now).toISOString(),interval_seconds:240};
  const observed={repositories:[{name:'mirror',sources:Object.fromEntries(['branch','recent','active','queued'].map(name=>[name,{...source}])),runs:[{state:'success'}]}]};
  const node={webhook_registration:'VERIFIED',last_verified_delivery:{id:'verified'},runtime_health:{state:'HEALTHY',cause:'Runtime self-test',observed_at:source.observed_at,ttl_seconds:60},native_runtime:{state:'READY',whole_transputer_verified:true,cause:'Exact native binding'}};
  const client={snapshot:observed,transport:'connected',last_node_at:now,sequence:1,node_sequence:1,event_sequence:3,node_event_sequence:3};
  const project=globalThis.QikvrtHealth.project;
  assert.equal(project(observed,node,client,now).state,'HEALTHY');
  assert.equal(project(observed,node,client,now+300000).state,'UNKNOWN');
  node.native_runtime={state:'BLOCK',cause:'NATIVE_BINARY_DIGEST_MISMATCH'};
  assert.equal(project(observed,node,client,now).state,'DEGRADED');
  assert.ok(project(observed,node,client,now).checks.some(check=>check.cause==='NATIVE_BINARY_DIGEST_MISMATCH'));
  node.native_runtime={state:'READY',whole_transputer_verified:false};
  assert.equal(project(observed,node,client,now).state,'UNKNOWN');
  observed.repositories[0].sources.branch.error={status:404,message:'Not Found'};
  assert.equal(project(observed,node,client,now).state,'DEGRADED');
  assert.match(project(observed,node,client,now).cause,/Rechte/);
  assert.equal(project(observed,node,client,now,'other').checks[0].id,'repositories');
});

test('a snapshot does not hide a detected event gap or corrupted event',async()=>{
  const copy=replica(),dir=mkdtempSync(join(tmpdir(),'qikvrt-health-event-'));
  try {
    const store=new MonitorStore(join(dir,'node.json'),'mirror');store.update(base());
    await copy.accept(store.envelope());
    assert.equal((await copy.acceptEvent({epoch:store.state.epoch,event_sequence:2})).reason,'EVENT_SEQUENCE_GAP');
    await copy.accept(store.envelope());
    assert.equal(copy.error,'EVENT_SEQUENCE_GAP');
  } finally {rmSync(dir,{recursive:true,force:true});}
});

test('node health reports missing carrier and native-cache failure without green CI masking it',async t=>{
  const monitor=await start(t);
  await monitor.observeLatest();
  const binding=await (await fetch(monitor.url+'/api/node')).json();
  assert.equal(binding.health.state,'DEGRADED');
  assert.equal(binding.health.checks.find(c=>c.id==='runtime').state,'UNKNOWN');
  assert.equal(binding.health.checks.find(c=>c.id==='native').state,'UNKNOWN');
  assert.equal(binding.periodic_polling,false);
});

const base = () => ({schema:'qikvrt-public-activity/v1',version:VERSION,generated_at:new Date().toISOString(),repositories:[],delivery:{periodic_polling:false}});
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const secret = 'local-test-secret-not-a-production-credential';
function replica() {
  const storage = new Map();
  const context = {crypto:webcrypto, TextEncoder, Uint8Array, atob, Date, sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)}};
  vm.createContext(context); vm.runInContext(readFileSync(new URL('./client-replica.js',import.meta.url),'utf8'),context);
  return context.QikvrtReplica.create({version:VERSION});
}
async function start(t, options = {}) {
  const dir = options.dir || mkdtempSync(join(tmpdir(),'qikvrt-monitor-test-'));
  const monitor = createMonitor({env:{QIKVRT_GITHUB_WEBHOOK_SECRET:secret},statePath:join(dir,'node.json'),observe:async()=>base(),...options});
  await new Promise(resolve=>monitor.server.listen(0,'127.0.0.1',resolve));
  t.after(async()=>{monitor.server.closeAllConnections();await new Promise(resolve=>monitor.server.close(resolve));if(!options.dir)rmSync(dir,{recursive:true,force:true});});
  return {...monitor,dir,url:'http://127.0.0.1:'+monitor.server.address().port};
}
async function send(url,id,n,overrides={}) {
  const raw=JSON.stringify({repository:{full_name:'ingolf-lohmann/qik-vrt',private:false},workflow_run:{id:n},message:'Exact public bytes: Grüße '+n});
  const response=await fetch(url+'/api/webhooks/github',{method:'POST',headers:{'content-type':'application/json','x-github-event':'workflow_run','x-github-delivery':id,'x-hub-signature-256':'sha256='+createHmac('sha256',secret).update(raw).digest('hex'),...overrides},body:raw});
  return {response,raw,value:await response.json()};
}
async function stream(url, headers={}) {
  const abort=new AbortController();
  const response=await fetch(url+'/api/stream',{headers,signal:abort.signal});
  assert.equal(response.status,200);
  const reader=response.body.getReader();let buffer='';
  return {abort,async next(){
    while(true){
      const at=buffer.indexOf('\n\n');
      if(at>=0){const frame=buffer.slice(0,at);buffer=buffer.slice(at+2);const event=frame.match(/^event: (.+)$/m),data=frame.match(/^data: (.+)$/m);if(event&&data)return {name:event[1],value:JSON.parse(data[1]),id:frame.match(/^id: (.+)$/m)?.[1]};continue;}
      const chunk=await reader.read();if(chunk.done)throw new Error('Unexpected stream close');buffer+=new TextDecoder().decode(chunk.value);
    }
  }};
}

test('snapshot integrity, distinct client instances, versions, order and epoch fail closed',async()=>{
  const dir=mkdtempSync(join(tmpdir(),'qikvrt-monitor-replica-'));
  try {
    const store=new MonitorStore(join(dir,'node.json'),'mirror');store.update(base());
    const one=replica(),two=replica();assert.notEqual(one.id,two.id);
    const envelope=store.envelope('a'.repeat(40));
    assert.equal((await one.accept(envelope)).accepted,true);
    assert.equal((await two.accept(envelope)).accepted,true);
    one.transport='connected';assert.equal(one.status().label,'Client und Node synchron');
    assert.equal((await one.accept({...envelope,generated_at:'altered'})).reason,'SNAPSHOT_DIGEST_MISMATCH');
    assert.equal((await two.accept({...envelope,version:'wrong-build'})).reason,'CLIENT_VERSION_MISMATCH');
    store.update({...base(),generated_at:'later'});const next=store.envelope();
    assert.equal((await one.accept(next)).accepted,true);
    assert.equal((await one.accept(envelope)).reason,'OUT_OF_ORDER_SNAPSHOT');
    assert.equal((await one.accept({...next,replication:{...next.replication,epoch:'replacement'}})).reason,'NODE_EPOCH_CHANGED');
    assert.equal(one.sequence,2);
  } finally {rmSync(dir,{recursive:true,force:true});}
});

test('durable acknowledgment, byte-exact journal, duplicates and signature rejection',async t=>{
  const monitor=await start(t);
  const first=await send(monitor.url,'delivery-one-0001',1);
  assert.equal(first.response.status,200);assert.equal(first.value.durable,true);
  const restored=new MonitorStore(join(monitor.dir,'node.json'),monitor.store.nodeId);
  assert.equal(restored.state.deliveries.length,1);
  assert.equal(Buffer.from(restored.state.deliveries[0].payload_base64,'base64').toString(),first.raw);
  assert.equal(restored.state.deliveries[0].payload_sha256,digest(first.raw));
  const repeat=await send(monitor.url,'delivery-one-0001',1);assert.equal(repeat.value.duplicate,true);
  const conflict=await send(monitor.url,'delivery-one-0001',2);assert.equal(conflict.response.status,409);
  const bad=await send(monitor.url,'delivery-invalid-0001',3,{'x-hub-signature-256':'sha256='+'0'.repeat(64)});
  assert.equal(bad.response.status,401);assert.equal(monitor.store.state.deliveries.length,1);
  assert.equal(verifyWebhook(Buffer.from(first.raw),'sha256='+'0'.repeat(64),secret),false);
});

test('four concurrent clients receive all 32 accepted events and agree on original bytes',async t=>{
  const monitor=await start(t);await monitor.observeLatest('test-baseline');
  const copies=Array.from({length:4},()=>replica());
  const streams=await Promise.all(copies.map(()=>stream(monitor.url)));
  t.after(()=>streams.forEach(s=>s.abort.abort()));
  await Promise.all(streams.map(async(s,i)=>{
    copies[i].transport='connected';const node=await s.next();copies[i].observe(node.value);
    const initial=await s.next();assert.equal(initial.name,'snapshot');await copies[i].accept(initial.value);
  }));
  const receivers=streams.map(async(s,i)=>{
    let count=0;
    while(count<32){const event=await s.next();if(event.name==='delivery'){assert.equal((await copies[i].acceptEvent(event.value)).accepted,true);count++;}else if(event.name==='snapshot')await copies[i].accept(event.value);else copies[i].observe(event.value);}
  });
  const sent=[];
  for(let batch=0;batch<4;batch++)sent.push(...await Promise.all(Array.from({length:8},(_,i)=>send(monitor.url,'fanout-delivery-'+(batch*8+i),batch*8+i))));
  await Promise.all(receivers);
  assert.ok(sent.every(item=>item.response.status===200));
  assert.equal(monitor.store.state.deliveries.length,32);
  for(const copy of copies){assert.equal(copy.event_sequence,32);assert.equal(copy.event_digest,monitor.store.state.deliveries.at(-1).record_digest);
    for(const item of sent)assert.ok(copy.events.some(event=>event.payload_sha256===digest(item.raw)));}
});

test('disconnect and node restart replay every missing event from the durable cursor',async t=>{
  const dir=mkdtempSync(join(tmpdir(),'qikvrt-monitor-restart-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
  const first=await start(t,{dir});await first.observeLatest('test-baseline');
  for(let n=1;n<=3;n++)await send(first.url,'restart-delivery-'+n,n);
  const epoch=first.store.state.epoch;
  const second=await start(t,{dir});assert.equal(second.store.state.epoch,epoch);
  const connection=await stream(second.url,{'Last-Event-ID':epoch+':1'});t.after(()=>connection.abort.abort());
  assert.equal((await connection.next()).name,'node');
  const a=await connection.next(),b=await connection.next();assert.equal(a.value.event_sequence,2);assert.equal(b.value.event_sequence,3);
  assert.equal((await connection.next()).name,'snapshot');
  assert.equal(Buffer.from(b.value.payload_base64,'base64').toString(),JSON.stringify({repository:{full_name:'ingolf-lohmann/qik-vrt',private:false},workflow_run:{id:3},message:'Exact public bytes: Grüße 3'}));
});

test('storage failure never acknowledges or broadcasts an event as durable',async t=>{
  const monitor=await start(t);await monitor.observeLatest('test-baseline');
  const before=JSON.stringify(monitor.store.state);
  monitor.store.persist=()=>{throw new Error('SIMULATED_STORAGE_FULL')};
  const failed=await send(monitor.url,'disk-failure-delivery',1);
  assert.equal(failed.response.status,500);assert.notEqual(failed.value.durable,true);
  assert.equal(JSON.stringify(monitor.store.state),before);
});

test('client event gaps and journal corruption are detected rather than promoted to synchrony',async t=>{
  const monitor=await start(t);await send(monitor.url,'gap-delivery-0001',1);await send(monitor.url,'gap-delivery-0002',2);
  const copy=replica();await copy.accept(monitor.store.envelope());
  const events=monitor.store.state.deliveries.map(event=>({...event,epoch:monitor.store.state.epoch}));
  assert.equal((await copy.acceptEvent(events[1])).reason,'EVENT_SEQUENCE_GAP');
  assert.equal((await copy.acceptEvent(events[0])).accepted,true);
  assert.equal((await copy.acceptEvent(events[1])).accepted,true);assert.equal(copy.event_sequence,2);
  const corrupt=JSON.parse(readFileSync(join(monitor.dir,'node.json'),'utf8'));corrupt.deliveries[0].payload_base64=Buffer.from('corrupt').toString('base64');
  writeFileSync(join(monitor.dir,'node.json'),JSON.stringify(corrupt));
  assert.throws(()=>new MonitorStore(join(monitor.dir,'node.json'),monitor.store.nodeId),/DURABLE_EVENT_JOURNAL_MISMATCH/);
});
