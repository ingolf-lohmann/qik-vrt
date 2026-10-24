// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHmac} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {verifyClient} from '../tools/qikvrt_mesh_monitor_readback.mjs';

const contract=JSON.parse(readFileSync(new URL('../state/deployments/MESH_MONITOR_RAILWAY_EXACT_674aa35.json',import.meta.url)));
// Test the existing exact deployment subject even when another writer advances
// docs/monitor on the executor branch. These are original Git bytes, no new server.
const fixture=mkdtempSync(join(tmpdir(),'qikvrt-exact-deploy-subject-'));
after(()=>rmSync(fixture,{recursive:true,force:true}));
for(const name of Object.keys(contract.artifact_files_sha256))writeFileSync(join(fixture,name),
  execFileSync('git',['show',contract.source_head+':docs/monitor/'+name],{timeout:30000,maxBuffer:1024*1024}));
const {createMonitor,VERSION}=await import(pathToFileURL(join(fixture,'server.mjs')).href);
const secret='fixture-only-webhook-key';
async function start(t,override={}) {
  const dir=mkdtempSync(join(tmpdir(),'qikvrt-deploy-readback-'));
  const monitor=createMonitor({statePath:join(dir,'node.json'),env:{
    QIKVRT_MONITOR_SOURCE_HEAD:contract.source_head,QIKVRT_MONITOR_SOURCE_TREE:contract.source_tree,
    QIKVRT_MONITOR_SOURCE_REPOSITORY:contract.source_repository,QIKVRT_MONITOR_NODE_ID:contract.node_id,
    QIKVRT_GITHUB_WEBHOOK_SECRET:secret,...override},
    observe:async()=>({schema:'qikvrt-public-activity/v1',version:VERSION,generated_at:'2026-10-04T15:09:52Z',repositories:[],delivery:{periodic_polling:false}})});
  await new Promise(resolve=>monitor.server.listen(0,'127.0.0.1',resolve));
  t.after(async()=>{monitor.server.closeAllConnections();await new Promise(resolve=>monitor.server.close(resolve));rmSync(dir,{recursive:true,force:true});});
  await monitor.observeLatest();
  return {...monitor,plan:{...contract,public_url:'http://127.0.0.1:'+monitor.server.address().port}};
}

test('fresh HTTP source/health and independent replica are accepted with unknown global health',async t=>{
  const monitor=await start(t);const receipt=await verifyClient(monitor.plan);
  assert.equal(receipt.state,'CLIENT_BYTE_READBACK_VERIFIED');
  assert.equal(receipt.source_head,contract.source_head);assert.equal(receipt.event_sequence,0);
  assert.notEqual(receipt.health_state,'HEALTHY');assert.equal(receipt.effect_ack_done,false);
});

test('old public carrier source fails before snapshot acceptance',async t=>{
  const monitor=await start(t,{QIKVRT_MONITOR_SOURCE_HEAD:'0'.repeat(40)});
  await assert.rejects(verifyClient(monitor.plan),/HOLD_PUBLIC_SOURCE_BINDING/);
});

test('a stale binding cannot pass as a fresh public readback',async t=>{
  const monitor=await start(t);
  const request=async(url,options)=>{
    const response=await fetch(url,options);if(!url.endsWith('/health'))return response;
    const value=await response.json();value.observed_at='2026-09-19T00:00:00Z';return Response.json(value);
  };
  await assert.rejects(verifyClient(monitor.plan,request),/HOLD_PUBLIC_OBSERVATION_NOT_FRESH/);
});

test('remote client byte tampering cannot inherit advertised server hashes',async t=>{
  const monitor=await start(t);
  const request=(url,options)=>url.endsWith('/client-replica.js')?Promise.resolve(new Response('altered-client')):fetch(url,options);
  await assert.rejects(verifyClient(monitor.plan,request),/HOLD_PUBLIC_CLIENT_BYTES/);
});

test('snapshot byte tampering is rejected by the reused replica implementation',async t=>{
  const monitor=await start(t);
  const request=async(url,options)=>{
    const response=await fetch(url,options);if(!url.endsWith('/api/activity'))return response;
    const value=await response.json();value.generated_at='tampered';return Response.json(value);
  };
  await assert.rejects(verifyClient(monitor.plan,request),/HOLD_CLIENT_SNAPSHOT_REJECTED/);
});

async function delivery(monitor) {
  const raw=JSON.stringify({repository:{full_name:contract.source_repository,private:false},message:'Exact Grüße 1'});
  const response=await fetch(monitor.plan.public_url+'/api/webhooks/github',{method:'POST',headers:{
    'content-type':'application/json','x-github-event':'workflow_run','x-github-delivery':'fixture-delivery',
    'x-hub-signature-256':'sha256='+createHmac('sha256',secret).update(raw).digest('hex')},body:raw});
  assert.equal(response.status,200);
}

test('accepted durable event is replayed through an independent byte validator',async t=>{
  const monitor=await start(t);await delivery(monitor);
  const receipt=await verifyClient(monitor.plan);assert.equal(receipt.event_sequence,1);
  assert.equal(receipt.journal_head_digest,monitor.store.state.deliveries[0].record_digest);
});

test('altered original event payload is rejected even if sequence count matches',async t=>{
  const monitor=await start(t);await delivery(monitor);
  const request=async(url,options)=>{
    const response=await fetch(url,options);if(!url.includes('/api/events'))return response;
    const value=await response.json();value.events[0].payload_base64=Buffer.from('tampered').toString('base64');return Response.json(value);
  };
  await assert.rejects(verifyClient(monitor.plan,request),/HOLD_CLIENT_EVENT_REJECTED/);
});

test('a concurrent journal change leaves readback unverified',async t=>{
  const monitor=await start(t);let reads=0;
  const request=async(url,options)=>{
    if(url.endsWith('/api/node')&&++reads===2)await delivery(monitor);
    return fetch(url,options);
  };
  await assert.rejects(verifyClient(monitor.plan,request),/HOLD_READBACK_CHANGED_OR_CLIENT_DIFFERS/);
});
