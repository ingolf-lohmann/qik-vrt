import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, writeFileSync, rmSync, mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHmac, createHash, webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {MonitorStore, createMonitor, verifyWebhook, replicationSignature, VERSION} from './server.mjs';
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

const primaryId = 'test:writer', replicaId = 'test:replica';
const peerSecret = 'configured-test-peer-secret';
const replicaEnv = {QIKVRT_MONITOR_NODE_ID:replicaId,QIKVRT_MONITOR_ROLE:'replica',QIKVRT_MONITOR_PRIMARY_NODE_ID:primaryId,QIKVRT_MONITOR_REPLICATION_SECRET:peerSecret};
const writerEnv = url => ({QIKVRT_MONITOR_NODE_ID:primaryId,QIKVRT_GITHUB_WEBHOOK_SECRET:secret,QIKVRT_MONITOR_REPLICA_URL:url,QIKVRT_MONITOR_REPLICA_NODE_ID:replicaId,QIKVRT_MONITOR_REPLICATION_SECRET:peerSecret});
async function pair(t, options={}) {
  const follower=await start(t,{env:replicaEnv,...options.replica});
  const writer=await start(t,{env:writerEnv(follower.url),...options.writer});
  return {writer,follower};
}
function packet(store, after=0) {
  return {schema:'qikvrt-monitor-replication/v1',version:VERSION,source_node_id:primaryId,
    epoch:store.state.epoch,after,previous_digest:store.state.deliveries[after-1]?.record_digest||'0'.repeat(64),
    events:structuredClone(store.state.deliveries.slice(after)),checkpoint:structuredClone(store.checkpoint())};
}
async function peer(url,path,body=null,overrides={}) {
  const method=body?'POST':'GET',raw=body?JSON.stringify(body):'';
  return fetch(url+path,{method,headers:{'content-type':'application/json',
    'x-qikvrt-replication-signature':replicationSignature(raw,method,path,peerSecret),...overrides},body:body?raw:undefined});
}
function assertEqualJournals(writer,follower) {
  assert.equal(follower.store.state.epoch,writer.store.state.epoch);
  assert.deepEqual(follower.store.state.deliveries,writer.store.state.deliveries);
  assert.equal(follower.store.visible().digest,writer.store.visible().digest);
  assert.deepEqual(new MonitorStore(follower.store.path,replicaId).state.deliveries,writer.store.state.deliveries);
}

// Local process separation is explicit. This is no deployment or physical-node
// acceptance: two child processes and durable directories share this test host.
async function processNode(t, env, dir) {
  const program=`import {createMonitor,VERSION} from ${JSON.stringify(new URL('./server.mjs',import.meta.url).href)};
    const m=createMonitor({observe:async()=>({schema:'qikvrt-public-activity/v1',version:VERSION,generated_at:new Date().toISOString(),repositories:[],delivery:{periodic_polling:false}})});
    m.server.listen(0,'127.0.0.1',()=>process.send({url:'http://127.0.0.1:'+m.server.address().port}));`;
  const child=spawn(process.execPath,['--input-type=module','-e',program],{
    env:{...process.env,...env,QIKVRT_MONITOR_STATE_DIR:dir},stdio:['ignore','ignore','pipe','ipc']});
  let errors='';child.stderr.on('data',chunk=>{errors+=chunk});
  const ready=await Promise.race([once(child,'message'),once(child,'exit').then(()=>{throw new Error('Child exited: '+errors)})]);
  async function stop(){if(child.exitCode===null&&child.signalCode===null){const ended=once(child,'exit');child.kill('SIGKILL');await ended;}}
  t.after(stop);
  return {url:ready[0].url,stop};
}

test('separate local processes: writer crash leaves four clients byte-exact replay on replica', {timeout:15000}, async t=>{
  const dir=mkdtempSync(join(tmpdir(),'qikvrt-cross-process-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
  const follower=await processNode(t,replicaEnv,join(dir,'replica'));
  const writer=await processNode(t,writerEnv(follower.url),join(dir,'writer'));
  const originals=[];
  for(let n=0;n<32;n++){
    const sent=await send(writer.url,'process-failover-'+n,n);originals.push(sent.raw);
    assert.equal(sent.response.status,200);assert.equal(sent.value.cross_node_durable,true);assert.equal(sent.value.effect_ack_done,false);
  }
  const primaryJournal=await (await fetch(writer.url+'/api/events')).json();
  const copies=Array.from({length:4},()=>replica());
  const sourceSnapshot=await (await fetch(follower.url+'/api/activity')).json();
  for(const copy of copies){await copy.accept(sourceSnapshot);for(const event of primaryJournal.events.slice(0,7))await copy.acceptEvent({...event,epoch:primaryJournal.epoch});}
  await writer.stop();
  const streams=await Promise.all(copies.map(()=>stream(follower.url,{'Last-Event-ID':primaryJournal.epoch+':7'})));
  t.after(()=>streams.forEach(s=>s.abort.abort()));
  await Promise.all(streams.map(async(s,index)=>{
    const node=await s.next();assert.equal(node.value.node_id,primaryId);assert.equal(node.value.serving_node_id,replicaId);
    assert.equal(node.value.journal_replication.write_failover,'FORBIDDEN_WITHOUT_FENCING');
    copies[index].observe(node.value);
    for(let n=7;n<32;n++){const event=await s.next();assert.equal(event.name,'delivery');assert.equal((await copies[index].acceptEvent(event.value)).accepted,true);}
    const final=await s.next();assert.equal(final.name,'snapshot');await copies[index].accept(final.value);
    assert.equal(copies[index].event_digest,primaryJournal.events.at(-1).record_digest);
    assert.deepEqual(Array.from(copies[index].events,event=>Buffer.from(event.payload_base64,'base64').toString()),originals);
  }));
  const disk=new MonitorStore(join(dir,'replica','node.json'),replicaId);
  assert.deepEqual(disk.state.deliveries,primaryJournal.events);
});

test('interruption with local pending tail withholds ACK and stream until reconnect and duplicate retry',async t=>{
  let interrupted=false;
  const {writer,follower}=await pair(t,{writer:{replicationFetch:(...args)=>{if(interrupted)throw new Error('LINK_INTERRUPTED');return fetch(...args);}}});
  await send(writer.url,'cross-link-first',1);
  const connection=await stream(writer.url);t.after(()=>connection.abort.abort());
  assert.equal((await connection.next()).name,'node');assert.equal((await connection.next()).name,'delivery');assert.equal((await connection.next()).name,'snapshot');
  interrupted=true;
  const failed=await send(writer.url,'cross-link-second',2);assert.equal(failed.response.status,503);assert.notEqual(failed.value.durable,true);
  assert.equal(writer.store.state.deliveries.length,2);assert.equal(writer.store.visible().deliveries.length,1);
  assert.equal((await connection.next()).name,'node'); // Failure evidence, no delivery publication.
  assert.equal((await (await fetch(writer.url+'/api/events')).json()).events.length,1);
  const original=JSON.stringify(writer.store.state.deliveries[1]);
  interrupted=false;
  const retried=await send(writer.url,'cross-link-second',2);assert.equal(retried.response.status,200);assert.equal(retried.value.duplicate,true);assert.equal(retried.value.cross_node_durable,true);
  assert.equal(JSON.stringify(writer.store.state.deliveries[1]),original);
  assert.equal((await connection.next()).value.event_sequence,2);
  assertEqualJournals(writer,follower);
});

test('writer restart preserves the unacknowledged tail and reconnects without regenerating records',async t=>{
  const dir=mkdtempSync(join(tmpdir(),'qikvrt-writer-recovery-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));
  let interrupted=true;
  const {writer,follower}=await pair(t,{writer:{dir,replicationFetch:(...args)=>{if(interrupted)throw new Error('LINK_INTERRUPTED');return fetch(...args);}}});
  const failed=await send(writer.url,'cross-restart-pending',1);assert.equal(failed.response.status,503);
  const original=JSON.stringify(writer.store.state.deliveries[0]);
  writer.server.closeAllConnections();await new Promise(resolve=>writer.server.close(resolve));
  const restored=await start(t,{dir,env:writerEnv(follower.url)});
  assert.equal(restored.store.visible().deliveries.length,0);
  const retried=await send(restored.url,'cross-restart-pending',1);assert.equal(retried.response.status,200);
  assert.equal(JSON.stringify(restored.store.state.deliveries[0]),original);
  assertEqualJournals(restored,follower);
});

test('signed append rejects missing events, reversed order, conflicting bytes and invalid checkpoints atomically',async t=>{
  const {writer,follower}=await pair(t);await send(writer.url,'cross-invalid-one',1);
  // Build pending records with the real store format, without a peer receipt.
  const value=base();
  for(let n=2;n<=3;n++){
    const raw=JSON.stringify({repository:{full_name:'ingolf-lohmann/qik-vrt',private:false},number:n});
    writer.store.update(value,{id:'cross-invalid-'+n,event:'push',repository:'ingolf-lohmann/qik-vrt',payload_base64:Buffer.from(raw).toString('base64'),payload_sha256:digest(raw),observed_at:'2026-10-04T00:00:00Z',verification:'HMAC_SHA256'});
  }
  const valid=packet(writer.store,1),before=JSON.stringify(follower.store.state);
  const cases=[
    {...valid,after:2,previous_digest:writer.store.state.deliveries[1].record_digest,events:valid.events.slice(1)},
    {...valid,events:[valid.events[1],valid.events[0]]},
    {...valid,events:[{...valid.events[0],payload_base64:Buffer.from('altered').toString('base64')},valid.events[1]]},
    {...valid,checkpoint:{...valid.checkpoint,digest:'0'.repeat(64)}},
    {...valid,checkpoint:{...valid.checkpoint,event_sequence:2}},
    {...valid,epoch:'different-epoch'},
    {...valid,source_node_id:'unbound-source'}
  ];
  for(const candidate of cases){const result=await peer(follower.url,'/api/replication/append',candidate);assert.equal(result.status,409);assert.equal(JSON.stringify(follower.store.state),before);}
  await writer.syncReplica();assertEqualJournals(writer,follower);
});

test('a valid conflicting replica prefix blocks the writer rather than overwriting the replica',async t=>{
  const follower=await start(t,{env:replicaEnv});
  const writer=await start(t,{env:writerEnv(follower.url)});
  const alternate=new MonitorStore(join(writer.dir,'alternate.json'),primaryId);
  alternate.state.epoch=writer.store.state.epoch;
  const raw=JSON.stringify({repository:{full_name:'ingolf-lohmann/qik-vrt',private:false},number:'other'});
  alternate.update(base(),{id:'cross-prefix-other',event:'push',repository:'ingolf-lohmann/qik-vrt',payload_base64:Buffer.from(raw).toString('base64'),payload_sha256:digest(raw),observed_at:'2026-10-04T00:00:00Z',verification:'HMAC_SHA256'});
  assert.equal((await peer(follower.url,'/api/replication/append',packet(alternate))).status,200);
  const before=JSON.stringify(follower.store.state);
  const sent=await send(writer.url,'cross-prefix-real',1);assert.equal(sent.response.status,409);assert.match(sent.value.cause,/REPLICA_PREFIX_CONFLICT/);
  assert.equal(JSON.stringify(follower.store.state),before);assert.equal(writer.store.visible().deliveries.length,0);
});

test('peer request and readback authentication failures never produce cross-node ACK',async t=>{
  const {writer,follower}=await pair(t);
  const before=JSON.stringify(follower.store.state);
  const bad=await peer(follower.url,'/api/replication/append',packet(writer.store),{'x-qikvrt-replication-signature':'sha256='+'0'.repeat(64)});
  assert.equal(bad.status,401);assert.equal(JSON.stringify(follower.store.state),before);
  const realFetch=fetch;
  const broken=await start(t,{env:writerEnv(follower.url),replicationFetch:async(...args)=>{
    const response=await realFetch(...args);return new Response(await response.text(),{status:response.status,headers:{'x-qikvrt-replication-signature':'sha256='+'0'.repeat(64)}});
  }});
  const result=await send(broken.url,'cross-readback-invalid',1);assert.equal(result.response.status,503);assert.match(result.value.cause,/INVALID_REPLICA_READBACK_SIGNATURE/);
  assert.equal(broken.store.visible().deliveries.length,0);
});

test('replica storage failure freezes receipts, then restart restores the prefix and permits recovery',async t=>{
  const {writer,follower}=await pair(t);await send(writer.url,'cross-storage-before',1);
  const oldPath=follower.store.path,before=JSON.stringify(follower.store.state);
  const occupied=join(follower.dir,'occupied');mkdirSync(occupied);follower.store.path=occupied;
  const result=await send(writer.url,'cross-storage-pending',2);assert.equal(result.response.status,503);assert.equal(follower.store.storageFailed,true);
  assert.equal(JSON.stringify(follower.store.state),before);assert.equal(writer.store.visible().deliveries.length,1);
  follower.store.path=oldPath;await assert.rejects(writer.syncReplica(),/STORAGE_RESTART_REQUIRED/);
  follower.server.closeAllConnections();await new Promise(resolve=>follower.server.close(resolve));
  const recovered=await start(t,{dir:follower.dir,env:replicaEnv});
  // New process address is a transport change; the configured peer ID is fixed.
  const writerState=writer.store.path;
  writer.server.closeAllConnections();await new Promise(resolve=>writer.server.close(resolve));
  const resumed=await start(t,{dir:writer.dir,env:writerEnv(recovered.url)});assert.equal(resumed.store.path,writerState);
  const retried=await send(resumed.url,'cross-storage-pending',2);assert.equal(retried.response.status,200);
  assertEqualJournals(resumed,recovered);
});

test('source receipt storage failure after peer durability requires fresh confirmation on restart',async t=>{
  const {writer,follower}=await pair(t);await send(writer.url,'cross-receipt-before',1);
  const persist=writer.store.persist.bind(writer.store);
  writer.store.persist=function(){if(this.state.confirmed?.event_sequence===2)throw new Error('SOURCE_RECEIPT_DISK_FULL');return persist()};
  const result=await send(writer.url,'cross-receipt-pending',2);assert.equal(result.response.status,503);assert.equal(writer.store.visible().deliveries.length,1);
  assert.equal(follower.store.visible().deliveries.length,2);
  writer.server.closeAllConnections();await new Promise(resolve=>writer.server.close(resolve));
  const restored=await start(t,{dir:writer.dir,env:writerEnv(follower.url)});
  await restored.syncReplica();assertEqualJournals(restored,follower);
});

test('interrupted bounded suffix batches restart at the durable prefix and expose only a complete checkpoint', {timeout:15000}, async t=>{
  let appends=0,breakAfterFirst=true;
  const {writer,follower}=await pair(t,{writer:{replicationFetch:async(url,init)=>{
    if(new URL(url).pathname.endsWith('/append')){appends++;if(breakAfterFirst&&appends===2)throw new Error('BATCH_LINK_INTERRUPTED');}
    return fetch(url,init);
  }}});
  for(let n=0;n<12;n++){
    const raw=JSON.stringify({repository:{full_name:'ingolf-lohmann/qik-vrt',private:false},number:n,padding:'x'.repeat(600000)});
    writer.store.update(base(),{id:'large-batch-'+n,event:'push',repository:'ingolf-lohmann/qik-vrt',payload_base64:Buffer.from(raw).toString('base64'),payload_sha256:digest(raw),observed_at:'2026-10-04T00:00:00Z',verification:'HMAC_SHA256'});
  }
  await assert.rejects(writer.syncReplica(),/BATCH_LINK_INTERRUPTED/);
  assert.ok(follower.store.state.deliveries.length>0&&follower.store.state.deliveries.length<12);
  assert.equal(follower.store.visible().deliveries.length,0);
  assert.equal((await fetch(follower.url+'/api/activity')).status,503);
  breakAfterFirst=false;
  await writer.syncReplica();assertEqualJournals(writer,follower);assert.equal(follower.store.visible().deliveries.length,12);
  assert.ok(appends>=3);
});

test('replicas remain read-only, do not observe GitHub, and cannot be promoted by changing role',async t=>{
  let observations=0;
  const {writer,follower}=await pair(t,{replica:{observe:async()=>{observations++;throw new Error('SHOULD_NOT_OBSERVE')}}});
  assert.equal((await fetch(follower.url+'/api/activity')).status,503);
  await send(writer.url,'cross-readonly-one',1);
  assert.equal((await fetch(follower.url+'/api/activity')).status,200);
  assert.equal((await fetch(follower.url+'/api/run?repo=ingolf-lohmann/qik-vrt&id=1')).status,503);
  assert.equal((await send(follower.url,'cross-readonly-two',2)).response.status,409);
  await assert.rejects(follower.observeLatest(),/REPLICA_READ_ONLY/);assert.equal(observations,0);
  assert.throws(()=>createMonitor({env:{QIKVRT_MONITOR_NODE_ID:replicaId},statePath:follower.store.path}),/DURABLE_REPLICATION_CONFIGURATION_MISMATCH/);
  assert.throws(()=>createMonitor({env:{QIKVRT_MONITOR_NODE_ID:primaryId},statePath:writer.store.path}),/DURABLE_REPLICATION_CONFIGURATION_MISMATCH/);
});

test('contradictory duplicate client record is rejected even if it repeats the claimed digest',async t=>{
  const {writer,follower}=await pair(t);await send(writer.url,'cross-client-conflict',1);
  const copy=replica();await copy.accept(follower.store.envelope());
  const event={...follower.store.state.deliveries[0],epoch:follower.store.state.epoch};
  assert.equal((await copy.acceptEvent(event)).accepted,true);
  assert.equal((await copy.acceptEvent({...event,payload_base64:Buffer.from('altered').toString('base64')})).reason,'EVENT_CONTENT_MISMATCH');
});

test('peer timeout withholds the positive receipt and reconnect recovers the original pending event',async t=>{
  let delayed=true;
  const {writer,follower}=await pair(t,{writer:{replicationTimeoutMs:20,replicationFetch:async(...args)=>{
    if(delayed)await new Promise(resolve=>setTimeout(resolve,40));return fetch(...args);
  }}});
  const failed=await send(writer.url,'cross-timeout-event',1);assert.equal(failed.response.status,503);assert.notEqual(failed.value.durable,true);
  assert.equal(writer.store.visible().deliveries.length,0);assert.equal(follower.store.state.deliveries.length,0);
  const original=JSON.stringify(writer.store.state.deliveries[0]);delayed=false;
  const retry=await send(writer.url,'cross-timeout-event',1);assert.equal(retry.response.status,200);
  assert.equal(JSON.stringify(writer.store.state.deliveries[0]),original);assertEqualJournals(writer,follower);
});

test('lost peer response after durable append is recovered by exact readback without duplicate events',async t=>{
  let loseReceipt=true;
  const {writer,follower}=await pair(t,{writer:{replicationFetch:async(url,init)=>{
    const response=await fetch(url,init);
    if(loseReceipt&&new URL(url).pathname.endsWith('/append')){await response.arrayBuffer();loseReceipt=false;throw new Error('REPLICA_RESPONSE_LOST');}
    return response;
  }}});
  const failed=await send(writer.url,'cross-lost-receipt',1);assert.equal(failed.response.status,503);
  assert.equal(follower.store.visible().deliveries.length,1);assert.equal(writer.store.visible().deliveries.length,0);
  const original=JSON.stringify(follower.store.state.deliveries);
  const retry=await send(writer.url,'cross-lost-receipt',1);assert.equal(retry.response.status,200);
  assert.equal(JSON.stringify(follower.store.state.deliveries),original);assertEqualJournals(writer,follower);
});

test('valid conflicting overlap and private payload are rejected before any replica mutation',async t=>{
  const {writer,follower}=await pair(t);await send(writer.url,'cross-valid-conflict',1);
  const before=JSON.stringify(follower.store.state);
  function rehash(event){const record={...event};delete record.record_digest;return {...record,record_digest:digest(JSON.stringify(record))};}
  const valid=packet(writer.store);
  const overlap=structuredClone(valid);overlap.events[0]=rehash({...overlap.events[0],observed_at:'2026-10-04T00:00:00Z'});
  const privatePacket=structuredClone(valid);
  const payload=JSON.parse(Buffer.from(privatePacket.events[0].payload_base64,'base64').toString());payload.repository.private=true;
  const raw=JSON.stringify(payload);privatePacket.events[0]=rehash({...privatePacket.events[0],payload_base64:Buffer.from(raw).toString('base64'),payload_sha256:digest(raw)});
  const extraBinding={...valid,checkpoint:{...valid.checkpoint,epoch:'shadow-epoch'}};
  for(const candidate of [overlap,privatePacket,extraBinding]){
    const response=await peer(follower.url,'/api/replication/append',candidate);assert.ok(response.status>=400);
    assert.equal(JSON.stringify(follower.store.state),before);
  }
});

test('restart rejects a corrupt durable replica confirmation instead of serving a fabricated prefix',async t=>{
  const {writer,follower}=await pair(t);await send(writer.url,'cross-confirmation-corrupt',1);
  const state=JSON.parse(readFileSync(follower.store.path,'utf8'));state.confirmed.journal_head_digest='0'.repeat(64);
  writeFileSync(follower.store.path,JSON.stringify(state));
  assert.throws(()=>new MonitorStore(follower.store.path,replicaId),/DURABLE_REPLICA_RECEIPT_MISMATCH/);
});
