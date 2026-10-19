// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, writeFileSync, mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import vm from 'node:vm';
import './sqlite-reader.js';

const directory=process.env.QIKVRT_ORIGIN_FIXTURE_DIR;
if(!directory)throw Error('Set QIKVRT_ORIGIN_FIXTURE_DIR to the original-kernel synthetic export.');
const raw=readFileSync(join(directory,'monolith.sqlite3'));
const profile=JSON.parse(readFileSync(join(directory,'origin/ORIGIN_PROFILE.json')));
const event=JSON.parse(readFileSync(join(directory,'expected-event.json')));
const temporary=mkdtempSync(join(tmpdir(),'qikvrt-sqlite-node-'));
const loader=join(temporary,'sql-wasm.cjs');
writeFileSync(loader,readFileSync(new URL('./vendor/sql-wasm.js',import.meta.url)));
const init=createRequire(import.meta.url)(loader);
const SQL=await init({wasmBinary:readFileSync(new URL('./vendor/sql-wasm.wasm',import.meta.url))});
test.after(()=>rmSync(temporary,{recursive:true,force:true}));
const inspect=(bytes=raw,p=profile)=>QikvrtSQLiteReader.inspect(SQL,bytes,p,p.store_sha256);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const repin=bytes=>({...profile,store_sha256:hash(bytes)});
function alter(sql) {const db=new SQL.Database(new Uint8Array(raw));try{db.run(sql);return db.export();}finally{db.close();}}
function context(url,secure=true) {
  const scope={URL,location:new URL(url),isSecureContext:secure,indexedDB:{},crypto:globalThis.crypto,navigator:{serviceWorker:{}},Worker:function(){}};
  vm.createContext(scope);vm.runInContext(readFileSync(new URL('./origin-store.js',import.meta.url),'utf8'),scope);return scope.QikvrtOriginStore;
}
test('the actual original SQLite image retains native epoch, event identity and byte digest',async()=>{
  const before=hash(raw),view=await inspect();
  assert.equal(view.ledger_id,event.id.split(':')[0]);assert.deepEqual(view.events,[event]);
  assert.equal(view.file_sha256,before);assert.equal(hash(raw),before);
  assert.equal(view.native_execution,false);assert.equal(view.mobile_runtime_verified,false);assert.equal(view.effect_ack_done,false);
});
test('unsafe HTTP and secure-looking foreign HTTP origins are refused',()=>{
  assert.throws(()=>context('http://unsafe.example/',false).checkOrigin(),/SECURE_ORIGIN_REQUIRED/);
  assert.throws(()=>context('http://unsafe.example/',true).checkOrigin(),/SECURE_ORIGIN_REQUIRED/);
  assert.doesNotThrow(()=>context('https://example.test/mesh/').checkOrigin());
  assert.doesNotThrow(()=>context('http://localhost/mesh/').checkOrigin());
});
test('a pure file start is refused even if the browser treats file as trustworthy',()=>{
  assert.throws(()=>context('file:///tmp/index.html',true).checkOrigin(),/FILE_START_UNSUPPORTED/);
});
test('changed original bytes fail the independent image pin',async()=>{
  const corrupt=Buffer.from(raw);corrupt[corrupt.length-8]^=0x80;
  await assert.rejects(inspect(corrupt),/STORE_BYTES_DIGEST_MISMATCH/);
});
test('corrupted SQLite pages are refused even with a test-rebound image digest',async()=>{
  const corrupt=Buffer.from(raw);corrupt[100]=0xff;
  await assert.rejects(inspect(corrupt,repin(corrupt)),/CORRUPT/);
});
test('a WAL-mode main file cannot masquerade as a checkpointed portable image',async()=>{
  const wal=Buffer.from(raw);wal[18]=wal[19]=2;
  await assert.rejects(inspect(wal,repin(wal)),/CHECKPOINTED_SQLITE_MONOLITH_REQUIRED/);
});
test('changed carrier pin, bytes, native identity and unadmitted schema fail closed',async()=>{
  await assert.rejects(inspect(raw,{...profile,manifest_sha256:'0'.repeat(64)}),/PACKAGE_MANIFEST_PIN_MISMATCH/);
  for(const [sql,error] of [
    ["UPDATE meta SET value='00000000000000000000000000000000' WHERE key='epoch'",/STORE_IDENTITY_MISMATCH/],
    ["UPDATE carrier SET body=x'0001' WHERE path='docs/monitor/react-runtime.js'",/CARRIER_BYTES_MISMATCH/],
    ["CREATE TRIGGER unadmitted AFTER DELETE ON carrier BEGIN SELECT 1; END",/MONOLITH_UNADMITTED_SCHEMA/],
    ["UPDATE events SET body_digest='bad'",/LEDGER_READBACK_MISMATCH/]]) {
    const changed=alter(sql);await assert.rejects(inspect(changed,repin(changed)),error);
  }
});
test('declared capacity bounds reject without rewriting or truncating the original store',async()=>{
  await assert.rejects(inspect(raw,{...profile,max_store_bytes:100}),/STORE_SIZE_UNSUPPORTED/);
  await assert.rejects(inspect(raw,{...profile,max_events:0}),/LEDGER_SIZE_UNSUPPORTED/);
  assert.equal(hash(raw),profile.store_sha256);
});
test('optional full source tree preserves the same SQLite Origin path and refuses tree/body changes',async()=>{
  const bytes=readFileSync(join(directory,'full-tree.sqlite3')),p=JSON.parse(readFileSync(join(directory,'full-tree-profile.json')));
  const view=await inspect(bytes,p);assert.equal(view.ledger_id,p.ledger_id);assert.equal(view.ledger_records,0);
  assert.equal(view.native_execution,false);assert.equal(hash(bytes),p.store_sha256);
  for(const sql of ["DELETE FROM repository_files WHERE path='AI'",
                    "UPDATE repository_files SET body=x'0001' WHERE path='AI'",
                    "UPDATE repository_files SET path='ai' WHERE path='AI'"]){
    const db=new SQL.Database(new Uint8Array(bytes));let changed;try{db.run(sql);changed=db.export();}finally{db.close();}
    await assert.rejects(inspect(changed,{...p,store_sha256:hash(changed)}),/SOURCE_/);
  }
});
