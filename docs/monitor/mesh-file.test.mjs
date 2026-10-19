// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm,open,lstat,statfs,unlink,symlink,mkdir} from 'node:fs/promises';
import {constants} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn,execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {once} from 'node:events';
import {createServer} from 'node:http';
import {MeshFileStore,meshFileRoutes,FileMetrics,transportExport} from './mesh-file-store.mjs';
import './mesh-file-client.js';
const M=globalThis.QikvrtMeshFile,Session=globalThis.QikvrtMeshFiles.Session;
const bytes=s=>new TextEncoder().encode(s);
async function fixture(t){const dir=await mkdtemp(join(tmpdir(),'qikmesh-'));t.after(()=>rm(dir,{recursive:true,force:true}));
  const initial=await M.create('test-repository',{test_fixture:true});const path=join(dir,'repository.qmesh');await writeFile(path,initial,{mode:0o600});
  const state=await M.scan(M.byteSource(initial));return {dir,path,initial,state,store:new MeshFileStore(path,{construction:true})};
}
const add=(state,key='AI',text='unchanged historical bytes',id='event-1')=>M.addEntry(state,key,M.byteSource(bytes(text)),{id,mediaType:'text/plain'});
test('single-file binary contents, revisions, long/case-sensitive virtual names and >1MiB chunks round trip',async t=>{
  const f=await fixture(t),data=new Uint8Array(M.LIMITS.payload_bytes+321);data.fill(237);
  const value=await M.addEntry(f.state,'../CON:'+('ü'.repeat(200))+'/AI',M.byteSource(data),{id:'large'});
  await f.store.append(value.suffix,f.state.head);const first=await f.store.inspect();
  assert.deepEqual(new Uint8Array(await (await M.entryBlob(M.byteSource(await readFile(f.path)),first,'../CON:'+('ü'.repeat(200))+'/AI')).arrayBuffer()),data);
  const next=await add(first,'AI','successor','revision-2');await f.store.append(next.suffix,first.head);
  const state=await f.store.inspect();assert(state.heads.has(f.state.head));assert(state.heads.has(first.head));assert.equal(state.entries.size,2);
  assert.equal(state.records.length,6);assert.equal((await readFile(f.path)).subarray(0,f.initial.length).equals(Buffer.from(f.initial)),true);
});
test('corrupt payload, chain, magic, truncation and invented chunk reference are refused',async t=>{
  const f=await fixture(t),entry=await add(f.state),full=M.join(f.initial,entry.suffix),good=await M.scan(M.byteSource(full));
  for(const offset of [0,good.records[1].payload_offset,full.length-1]){const bad=full.slice();bad[offset]^=1;await assert.rejects(M.scan(M.byteSource(bad)),/MISMATCH/);}
  await assert.rejects(M.scan(M.byteSource(full.slice(0,-1))),/TRUNCATED_FRAME/);
  const unknown=await M.frame(f.state.head,1,'dangling','entry','AI',bytes(M.canonical({bytes:1,chunks:[{digest:'1'.repeat(64),bytes:1}],media_type:'text/plain'})));
  await assert.rejects(M.scan(M.byteSource(M.join(f.initial,unknown))),/UNRESOLVED_CHUNK/);
});
test('a confirmed checkpoint cannot be rolled back or transferred to another repository',async t=>{
  const f=await fixture(t),entry=await add(f.state);await f.store.append(entry.suffix,f.state.head);
  const confirmed=await f.store.inspect();await writeFile(f.path,f.initial);
  assert.equal((await f.store.status()).state,'HOLD');assert.equal((await f.store.status()).cause,'CONFIRMED_CHECKPOINT_MISSING');
  const other=await M.create('another');await assert.rejects(M.scan(M.byteSource(other),confirmed.checkpoint),/CHECKPOINT_REPOSITORY/);
});
test('lost append acknowledgement is read back without a second record or overwritten identity',async t=>{
  const f=await fixture(t),entry=await add(f.state);const receipt=await f.store.append(entry.suffix,f.state.head);const saved=await readFile(f.path);
  const duplicate=await f.store.append(entry.suffix,f.state.head);assert.equal(duplicate.changed,false);assert.equal(duplicate.state,'FILE_APPEND_ALREADY_PRESENT');
  assert.deepEqual(await readFile(f.path),saved);assert.equal(receipt.effect_ack_done,false);
  const changed=await add(f.state,'AI','different bytes','event-1');await assert.rejects(f.store.append(changed.suffix,f.state.head),/HEAD_CONFLICT/);
  await assert.rejects(f.store.append(entry.suffix,'1'.repeat(64)),/HEAD_CONFLICT/);
});
test('two cooperating writers admit one competing append and retain the other as a conflict',async t=>{
  const f=await fixture(t),left=await add(f.state,'AI','left','left'),right=await add(f.state,'AI','right','right');
  const result=await Promise.allSettled([f.store.append(left.suffix,f.state.head),new MeshFileStore(f.path,{construction:true}).append(right.suffix,f.state.head)]);
  assert.equal(result.filter(r=>r.status==='fulfilled').length,1);
  assert.match(result.find(r=>r.status==='rejected').reason.message,/LOCK|CONFLICT/);
  assert.equal((await f.store.inspect()).records.length,3);
});
test('filesystem capacity and symlinks block writes without creating a replacement repository',async t=>{
  const f=await fixture(t),entry=await add(f.state),io={open,lstat,unlink,statfs:async()=>({bavail:1,bsize:1,blocks:1})};
  await assert.rejects(new MeshFileStore(f.path,{io,construction:true}).append(entry.suffix,f.state.head),/INSUFFICIENT_FILESYSTEM_SPACE/);
  assert.deepEqual(await readFile(f.path),Buffer.from(f.initial));const alias=join(f.dir,'alias.qmesh');await symlink(f.path,alias);
  assert.equal((await new MeshFileStore(alias,{construction:true}).status()).state,'HOLD');
  const missing=join(f.dir,'missing.qmesh');assert.equal((await new MeshFileStore(missing,{construction:true}).status()).state,'HOLD');await assert.rejects(lstat(missing),/ENOENT/);
});
test('partial write and failed fsync preserve all bytes and quarantine further writes',async t=>{
  for(const fault of ['partial','sync']){
    const f=await fixture(t),entry=await add(f.state),io={lstat,statfs,unlink,open:async(...args)=>{
      const handle=await open(...args);if(typeof args[1]!=='number'||!(args[1]&constants.O_WRONLY))return handle;
      return {stat:()=>handle.stat(),close:()=>handle.close(),write:async(...a)=>{
        if(fault==='partial'){await handle.write(a[0],0,13);throw Error('INJECTED_DISK_FULL');}return handle.write(...a);},
        sync:async()=>{if(fault==='sync')throw Error('INJECTED_FSYNC_FAILURE');return handle.sync();}};
    }};
    const store=new MeshFileStore(f.path,{io,construction:true});await assert.rejects(store.append(entry.suffix,f.state.head),/INJECTED/);
    const saved=await readFile(f.path);assert.equal(saved.subarray(0,f.initial.length).equals(Buffer.from(f.initial)),true);
    assert.equal((await store.status()).state,'HOLD');await assert.rejects(store.append(entry.suffix,f.state.head),/AMBIGUOUS_WRITE/);
    assert.deepEqual(await readFile(f.path),saved);
  }
});
test('SIGKILL after durable receipt reopens one monolithic file without duplicate records',async t=>{
  const f=await fixture(t),script=`import {MeshFileStore} from ${JSON.stringify(import.meta.resolve('./mesh-file-store.mjs'))};
    const M=globalThis.QikvrtMeshFile,store=new MeshFileStore(process.argv[1],{construction:true}),state=await store.inspect();
    const added=await M.addEntry(state,'AI',M.byteSource(new TextEncoder().encode('confirmed before kill')),{id:'crash-event'});
    const receipt=await store.append(added.suffix,state.head);console.log(JSON.stringify(receipt));setInterval(()=>{},1000);`;
  const child=spawn(process.execPath,['--input-type=module','-e',script,f.path],{stdio:['ignore','pipe','pipe']});
  const chunk=await once(child.stdout,'data');const receipt=JSON.parse(chunk[0]);child.kill('SIGKILL');await once(child,'exit');
  const reopened=new MeshFileStore(f.path,{construction:true}),state=await reopened.inspect();assert.equal(state.head,receipt.head);assert.equal(state.records.length,3);
  const suffix=(await readFile(f.path)).subarray(f.initial.length);assert.equal((await reopened.append(suffix,f.state.head)).changed,false);
});
async function boundFixture(t){
  const f=await fixture(t),store=join(f.dir,'events.sqlite3');
  execFileSync('python3',['-c',"import sqlite3,sys;db=sqlite3.connect(sys.argv[1]);db.execute('PRAGMA application_id=0x51495654');db.execute('PRAGMA user_version=1');db.execute('CREATE TABLE transport_fixture(value TEXT)');db.commit();db.close()",store]);
  const raw=await readFile(store),info={bytes:raw.length,file_sha256:await M.digest(raw),manifest_sha256:'2'.repeat(64),
    ledger_id:'3'.repeat(32),source_head:'4'.repeat(40),source_tree:'5'.repeat(40),repositoryId:'transport-fixture'};
  const path=join(f.dir,'derived.qmesh'),receipt=await transportExport(store,path,info),wire=await readFile(path);
  return {...f,path,raw,info,receipt,wire,store:new MeshFileStore(path)};
}
test('browser opens and extracts derived SQLite but cannot create, append or directly write a product format',async t=>{
  const f=await boundFixture(t),session=new Session();await session.open(new Blob([f.wire]));
  assert.deepEqual(Buffer.from(await (await session.canonical()).arrayBuffer()),f.raw);
  assert.equal(session.status().orchestration.accept_writes,false);assert.equal(session.status().pending_save,false);
  await assert.rejects(session.add('AI',new Blob(['forbidden'])),/SCHREIBGESCHUETZT/);
  await assert.rejects(session.create('competitor'),/SQLITE_IST_KANONISCH/);
  await assert.rejects(session.saveDirect(),/SCHREIBGESCHUETZT/);
  await session.verify();assert.deepEqual(Buffer.from(await session.blob.arrayBuffer()),f.wire);
  const legacy=await M.create('legacy-source');await assert.rejects(new Session().open(new Blob([legacy])),/DERIVED_SQLITE_TRANSPORT_REQUIRED/);
  await assert.rejects(M.transportImage(M.byteSource(f.wire),await M.scan(M.byteSource(f.wire)),{file_sha256:'0'.repeat(64)}),/PIN_MISMATCH/);
});
test('actual REST transport enforces bearer and CORS, compares exports and rejects every POST without a second ledger',async t=>{
  const f=await boundFixture(t),token='fixture-token-'.repeat(4),route=meshFileRoutes(f.store,token,{allowedOrigins:['null']});
  const server=createServer(async(req,res)=>{if(!await route(req,res,new URL(req.url,'http://local')))res.end();});
  server.listen(0,'127.0.0.1');await once(server,'listening');t.after(()=>{server.closeAllConnections();server.close();});
  const base='http://127.0.0.1:'+server.address().port+'/',headers={Authorization:'Bearer '+token};
  assert.equal((await fetch(base+'api/mesh-file/status')).status,401);
  assert.equal((await fetch(base+'api/mesh-file/status',{headers:{...headers,Origin:'https://untrusted.example'}})).status,403);
  const preflight=await fetch(base+'api/mesh-file/append',{method:'OPTIONS',headers:{Origin:'null'}});
  assert.equal(preflight.status,204);assert.equal(preflight.headers.get('access-control-allow-methods'),'GET, OPTIONS');
  const session=new Session();await session.open(new Blob([f.wire]));let posts=0;
  const readOnly=async(url,init)=>{if(init.method==='POST')posts++;return fetch(url,init);};
  assert.equal((await session.sync(base,token,{fetcher:readOnly})).state,'LOCAL_CLOUD_EQUAL_BY_VERIFIED_HEAD');
  assert.equal(posts,0);assert.equal((await f.store.status()).orchestration.accept_writes,false);
  const bytes=await fetch(base+'api/mesh-file/bytes',{headers});assert.equal(bytes.headers.get('etag'),'"'+session.state.head+'"');
  assert.deepEqual(Buffer.from(await bytes.arrayBuffer()),f.wire);
  assert.equal((await fetch(base+'api/mesh-file/append',{method:'POST',headers,body:new Uint8Array([1])})).status,405);
  await assert.rejects(f.store.append(new Uint8Array([1]),session.state.head),/READ_ONLY/);
  const divergent=async()=>({ok:true,json:async()=>({...M.summary(session.state),head:'f'.repeat(64)})});
  await assert.rejects(session.sync(base,token,{fetcher:divergent}),/SQLITE_STAND_ABWEICHEND/);
  assert.deepEqual(await readFile(f.path),f.wire);
});
test('direct file selection grants no write operation or mutable QIKMESH product state',async t=>{
  const f=await boundFixture(t),session=new Session();let writes=0;
  const handle={getFile:async()=>new Blob([await readFile(f.path)]),createWritable:async()=>{writes++;throw Error('must never run');}};
  await session.open(await handle.getFile(),{handle});await assert.rejects(session.saveDirect(),/SCHREIBGESCHUETZT/);
  assert.equal(writes,0);assert.equal(session.status().metrics.write.bytes_per_second,null);
  assert.equal(session.status().access,'DIRECT_FILE_HANDLE');
});
test('metric window ages out actual operations and exposes unknown latency instead of a fabricated measurement',()=>{
  let now=0;const metrics=new FileMetrics(()=>now);now=1000;metrics.record('read',2048,2);metrics.record('write',100,5);
  assert.equal(metrics.status().read.bytes_per_second,2048);assert.equal(metrics.status().write.operations_per_second,1);
  now=12000;assert.equal(metrics.status().read.operations_per_second,0);assert.equal(metrics.status().read.mean_latency_ms,null);
});
test('a bound export refuses appended revisions even when the frame chain is coherent',async t=>{
  const f=await boundFixture(t),state=await M.scan(M.byteSource(f.wire)),changed=await add(state,'AI','not canonical','extra-entry');
  const wire=M.join(f.wire,changed.suffix),scan=await M.scan(M.byteSource(wire));
  await assert.rejects(M.transportImage(M.byteSource(wire),scan),/DERIVED_SQLITE_TRANSPORT_REQUIRED/);
  await assert.rejects(new MeshFileStore(f.path,{construction:true}).append(changed.suffix,state.head),/READ_ONLY/);
  assert.deepEqual(await readFile(f.path),f.wire);
});
