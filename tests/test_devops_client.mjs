// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Real browser-side wire/projection code; DOM presentation is verified separately.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash,webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const sandbox={crypto:webcrypto,TextEncoder,URL};vm.createContext(sandbox);
for(const file of ['devops-wire.js','devops-projection.js','devops-capture.js','react-runtime.js'])vm.runInContext(readFileSync(root+'docs/monitor/'+file,'utf8'),sandbox,{timeout:2000});
assert.equal(sandbox.QikvrtReact.React.version,JSON.parse(readFileSync(root+'runtime/self-host/REACT_LOCK.json')).versions.react);
const p=sandbox.QikVrtDevops.project(sandbox.QikvrtDevopsCapture);
assert.equal(p.rows.length,127);assert.equal(p.primary.source_fresh,false);
const rows=await sandbox.QikVrtDevops.exportRows(p);
for(const row of rows){const {projection_sha256,...body}=row;assert.equal(createHash('sha256').update(sandbox.QikVrtDevops.canonical(body)).digest('hex'),projection_sha256);}
const wire=sandbox.QikvrtDevopsWire;
for(const source of ['{"x":1,"x":2}','{"e\\u0301":1,"\\u00e9":2}','{"x":1.0}','{"x":1e3}','{"x":9007199254740992}','{"x":"\\ud800"}'])assert.throws(()=>wire.parse(source));
assert.equal(wire.canonical({'\ue000':1,'\u{10000}':2}),'{"\u{10000}":2,"\ue000":1}');
const input=readFileSync(0,'utf8').trim();
if(input){
 const value=JSON.parse(input);await wire.verify(value.context,value.expected);
 for(const field of ['origin_checked','semantics_reconstructed','policy_allows_release']){
   const bad=structuredClone(value.context);bad.chain.at(-1)[field]=false;bad.chain.at(-1).protocol_hash=await wire.digest(wire.projection(bad.chain.at(-1)));
   await assert.rejects(wire.verify(bad,{...value.expected,recordHash:bad.chain.at(-1).protocol_hash}));
 }
 const bad=structuredClone(value.context);bad.latest_hash='sha256:'+'0'.repeat(64);await assert.rejects(wire.verify(bad,value.expected));
 await assert.rejects(wire.verify(value.context,{...value.expected,principal:'another-principal'}));
 await assert.rejects(wire.verify(value.context,{...value.expected,expiresAt:0}));
 const policy=structuredClone(value.context);policy.policy.effect='DIFFERENT_UNTRUSTED_EFFECT';policy.chain.at(-1).policy_hash=await wire.digest(policy.policy);
 policy.chain.at(-1).protocol_hash=await wire.digest(wire.projection(policy.chain.at(-1)));policy.latest_hash=policy.chain.at(-1).protocol_hash;
 await assert.rejects(wire.verify(policy,{...value.expected,recordHash:policy.latest_hash}));
 const date=structuredClone(value.context);date.chain.at(-1).created_utc='2026-02-30T12:00:00Z';await assert.rejects(wire.verify(date,value.expected));
}
for(const file of ['devops-react.js','devops-wire.js']){
 const source=readFileSync(root+'docs/monitor/'+file,'utf8');new vm.Script(source);
 assert(!/setInterval\s*\(|setTimeout\s*\(|localStorage|sessionStorage/.test(source));
}
console.log('DEVOPS_CLIENT_PASS: original React lock, 127 projection hashes, strict wire parser, state/policy/chain/freshness controls, no client timers or persistent credentials.');
