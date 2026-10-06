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
import {MeshFileStore,meshFileRoutes,FileMetrics,portableExport} from './mesh-file-store.mjs';
import './mesh-file-client.js';
const M=globalThis.QikvrtMeshFile,Session=globalThis.QikvrtMeshFiles.Session;
const bytes=s=>new TextEncoder().encode(s);
async function fixture(t){const dir=await mkdtemp(join(tmpdir(),'qikmesh-'));t.after(()=>rm(dir,{recursive:true,force:true}));
  const initial=await M.create('test-repository',{test_fixture:true});const path=join(dir,'repository.qmesh');await writeFile(path,initial,{mode:0o600});
  const state=await M.scan(M.byteSource(initial));return {dir,path,initial,state,store:new MeshFileStore(path)};
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
  const result=await Promise.allSettled([f.store.append(left.suffix,f.state.head),new MeshFileStore(f.path).append(right.suffix,f.state.head)]);
  assert.equal(result.filter(r=>r.status==='fulfilled').length,1);
  assert.match(result.find(r=>r.status==='rejected').reason.message,/LOCK|CONFLICT/);
  assert.equal((await f.store.inspect()).records.length,3);
});
test('filesystem capacity and symlinks block writes without creating a replacement repository',async t=>{
  const f=await fixture(t),entry=await add(f.state),io={open,lstat,unlink,statfs:async()=>({bavail:1,bsize:1,blocks:1})};
  await assert.rejects(new MeshFileStore(f.path,{io}).append(entry.suffix,f.state.head),/INSUFFICIENT_FILESYSTEM_SPACE/);
  assert.deepEqual(await readFile(f.path),Buffer.from(f.initial));const alias=join(f.dir,'alias.qmesh');await symlink(f.path,alias);
  assert.equal((await new MeshFileStore(alias).status()).state,'HOLD');
  const missing=join(f.dir,'missing.qmesh');assert.equal((await new MeshFileStore(missing).status()).state,'HOLD');await assert.rejects(lstat(missing),/ENOENT/);
});
test('partial write and failed fsync preserve all bytes and quarantine further writes',async t=>{
  for(const fault of ['partial','sync']){
    const f=await fixture(t),entry=await add(f.state),io={lstat,statfs,unlink,open:async(...args)=>{
      const handle=await open(...args);if(typeof args[1]!=='number'||!(args[1]&constants.O_WRONLY))return handle;
      return {stat:()=>handle.stat(),close:()=>handle.close(),write:async(...a)=>{
        if(fault==='partial'){await handle.write(a[0],0,13);throw Error('INJECTED_DISK_FULL');}return handle.write(...a);},
        sync:async()=>{if(fault==='sync')throw Error('INJECTED_FSYNC_FAILURE');return handle.sync();}};
    }};
    const store=new MeshFileStore(f.path,{io});await assert.rejects(store.append(entry.suffix,f.state.head),/INJECTED/);
    const saved=await readFile(f.path);assert.equal(saved.subarray(0,f.initial.length).equals(Buffer.from(f.initial)),true);
    assert.equal((await store.status()).state,'HOLD');await assert.rejects(store.append(entry.suffix,f.state.head),/AMBIGUOUS_WRITE/);
    assert.deepEqual(await readFile(f.path),saved);
  }
});
test('SIGKILL after durable receipt reopens one monolithic file without duplicate records',async t=>{
  const f=await fixture(t),script=`import {MeshFileStore} from ${JSON.stringify(import.meta.resolve('./mesh-file-store.mjs'))};
    const M=globalThis.QikvrtMeshFile,store=new MeshFileStore(process.argv[1]),state=await store.inspect();
    const added=await M.addEntry(state,'AI',M.byteSource(new TextEncoder().encode('confirmed before kill')),{id:'crash-event'});
    const receipt=await store.append(added.suffix,state.head);console.log(JSON.stringify(receipt));setInterval(()=>{},1000);`;
  const child=spawn(process.execPath,['--input-type=module','-e',script,f.path],{stdio:['ignore','pipe','pipe']});
  const chunk=await once(child.stdout,'data');const receipt=JSON.parse(chunk[0]);child.kill('SIGKILL');await once(child,'exit');
  const reopened=new MeshFileStore(f.path),state=await reopened.inspect();assert.equal(state.head,receipt.head);assert.equal(state.records.length,3);
  const suffix=(await readFile(f.path)).subarray(f.initial.length);assert.equal((await reopened.append(suffix,f.state.head)).changed,false);
});
test('browser file selection, pending save and direct readback never manufacture a saved acknowledgement',async t=>{
  const f=await fixture(t),session=new Session();await session.open(new Blob([f.initial]));await session.add('AI',new Blob(['note']),{id:'local-event'});
  assert.equal(session.status().pending_save,true);await session.verify();assert.equal(session.status().pending_save,true);
  await assert.rejects(session.create('another-repository'),/ARBEITSKOPIE_ZUERST/);
  await assert.rejects(session.open(new Blob([f.initial])),/CONFIRMED_CHECKPOINT_MISSING/);
  assert.equal(await (await session.entry('AI')).text(),'note');await session.open(session.blob);assert.equal(session.status().pending_save,false);
});
test('REST bearer, CORS, ETag, bidirectional sync, divergence and lost HTTP response use the actual file adapter',async t=>{
  const f=await fixture(t),token='fixture-token-'.repeat(4),route=meshFileRoutes(f.store,token,{allowedOrigins:['null']});
  const server=createServer(async(req,res)=>{if(!await route(req,res,new URL(req.url,'http://local')))res.end();});
  server.listen(0,'127.0.0.1');await once(server,'listening');t.after(()=>{server.closeAllConnections();server.close();});
  const base='http://127.0.0.1:'+server.address().port+'/';
  assert.equal((await fetch(base+'api/mesh-file/status')).status,401);
  assert.equal((await fetch(base+'api/mesh-file/status',{headers:{Authorization:'Bearer '+token,Origin:'https://untrusted.example'}})).status,403);
  const preflight=await fetch(base+'api/mesh-file/append',{method:'OPTIONS',headers:{Origin:'null'}});assert.equal(preflight.status,204);assert.equal(preflight.headers.get('access-control-allow-origin'),'null');
  const session=new Session();await session.open(new Blob([f.initial]));await session.add('AI',new Blob(['local']),{id:'local'});
  let posts=0;const lost=async(url,init)=>{const r=await fetch(url,init);if(init.method==='POST'){posts++;throw Error('INJECTED_LOST_RESPONSE');}return r;};
  const synced=await session.sync(base,token,{fetcher:lost});assert.equal(synced.state,'CLOUD_APPEND_READBACK_VERIFIED');assert.equal(posts,1);assert.equal((await f.store.inspect()).head,session.state.head);
  const remote=await f.store.inspect(),extension=await add(remote,'cloud.txt','cloud extension','cloud');await f.store.append(extension.suffix,remote.head);
  assert.equal((await session.sync(base,token)).state,'LOCAL_EXTENSION_VERIFIED_SAVE_REQUIRED');assert.equal(await (await session.entry('cloud.txt')).text(),'cloud extension');
  const peer=new Session();await peer.open(new Blob([f.initial]));await peer.add('AI',new Blob(['other']),{id:'other'});
  await assert.rejects(peer.sync(base,token),/HEAD_CONFLICT/);assert.equal((await f.store.inspect()).head,session.state.head);
});
test('direct file stream readback measures writes and holds after an uncertain close',async t=>{
  const f=await fixture(t),session=new Session();let failClose=false,writes=0;
  const handle={getFile:async()=>new Blob([await readFile(f.path)]),createWritable:async()=>({
    write:async blob=>{writes++;await writeFile(f.path,new Uint8Array(await blob.arrayBuffer()));},
    close:async()=>{if(failClose)throw Error('INJECTED_BROWSER_CLOSE_FAILURE');}})};
  await session.open(await handle.getFile(),{handle});await session.add('AI',new Blob(['first']),{id:'direct-first'});
  assert.equal(session.status().metrics.write.bytes_per_second,null);await session.saveDirect();assert.equal(session.status().pending_save,false);
  assert(session.status().metrics.write.bytes_per_second>0);await session.add('AI',new Blob(['second']),{id:'direct-second'});
  failClose=true;await assert.rejects(session.saveDirect(),/INJECTED/);assert.equal(session.status().state,'HOLD');
  await assert.rejects(session.saveDirect(),/SCHREIBSTATUS_UNBEKANNT/);assert.equal(writes,2);
  await session.open(await handle.getFile(),{handle});assert.equal(session.status().state,'VERIFIED');
});
test('metric window ages out actual operations and exposes unknown latency instead of a fabricated measurement',()=>{
  let now=0;const metrics=new FileMetrics(()=>now);now=1000;metrics.record('read',2048,2);metrics.record('write',100,5);
  assert.equal(metrics.status().read.bytes_per_second,2048);assert.equal(metrics.status().write.operations_per_second,1);
  now=12000;assert.equal(metrics.status().read.operations_per_second,0);assert.equal(metrics.status().read.mean_latency_ms,null);
});
test('portable exporter retains original source bytes despite Windows checkout line ending conversion',async t=>{
  const f=await fixture(t),root=join(f.dir,'source');await mkdir(root);await writeFile(join(root,'.gitattributes'),'*.cmd text eol=crlf\n');
  await writeFile(join(root,'example.cmd'),'@echo off\r\necho source\r\n');
  const git=(...args)=>execFileSync('git',['-C',root,...args]);git('init','-q');git('add','.');
  git('-c','user.name=QIKVRT fixture','-c','user.email=fixture@example.invalid','commit','-qm','Source-byte fixture');
  await mkdir(join(root,'docs'));await symlink(fileURLToPath(new URL('.',import.meta.url)),join(root,'docs','monitor'));
  const files=git('ls-tree','-r','HEAD').toString().trim().split('\n').map(line=>{const [meta,path]=line.split('\t'),[mode,,sha]=meta.split(' ');return {path,mode,sha};});
  const output=join(f.dir,'portable');const result=await portableExport(root,output,{files,head:git('rev-parse','HEAD').toString().trim(),tree:git('rev-parse','HEAD^{tree}').toString().trim(),repositoryId:'source-byte-fixture'});
  const raw=await readFile(join(output,'repository.qmesh')),state=await M.scan(M.byteSource(raw)),entry=await M.entryBlob(M.byteSource(raw),state,'example.cmd');
  assert.deepEqual(Buffer.from(await entry.arrayBuffer()),git('show','HEAD:example.cmd'));
  assert.notDeepEqual(Buffer.from(await entry.arrayBuffer()),await readFile(join(root,'example.cmd')));
  assert.equal(result.source_files,2);assert((await readFile(join(output,'universal-terminal.html'),'utf8')).includes('MIT License'));
});
