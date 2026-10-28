import fs from 'node:fs';
import crypto from 'node:crypto';
import vm from 'node:vm';
import path from 'node:path';
const [carrierPath,codecPath,outputPath]=process.argv.slice(2);
if(!carrierPath||!codecPath||!outputPath)throw Error('Usage: node verify-carrier.mjs CARRIER CODEC OUTPUT_DIRECTORY');
const root=path.resolve(outputPath);
fs.mkdirSync(root,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const code=fs.readFileSync(codecPath);
if(sha(code)!=='8c8d73f45cc8298c765842759451eaa3686541765952a77d05f2f928c7160515')throw Error('SOURCE_BYTES_MISMATCH');
if(!globalThis.crypto)globalThis.crypto=crypto.webcrypto;
vm.runInThisContext(code.toString());
const q=globalThis.QikvrtMeshFile;
const raw=new Uint8Array(fs.readFileSync(carrierPath));
if(sha(raw)!=='6d3421652aa1ba0f4782e30120f407183d3be2c49a069d6d3d1d17998f5bfac0')throw Error('OWNER_CARRIER_MISMATCH');
const source=q.byteSource(raw), state=await q.scan(source), restored=[];
const decoded=new Map();
for(const [key,value] of state.entries){
 const b=new Uint8Array(await (await q.entryBlob(source,state,key)).arrayBuffer());
 if(b.length!==value.bytes)throw Error('LENGTH_MISMATCH');
 decoded.set(key,b);restored.push({key,bytes:b.length,sha256:sha(b)});
}
const receiptKey=[...decoded.keys()].find(k=>k.endsWith('READBACK_RECEIPT.json'));
const prior=JSON.parse(new TextDecoder().decode(decoded.get(receiptKey)));
for(const input of prior.restored_entries){
 const key=`recursive-pass-${input.pass}/${input.path}`;
 const b=decoded.get(key);if(!b||b.length!==input.bytes||sha(b)!==input.sha256)throw Error('PINNED_ORIGINAL_MISMATCH');
}
const first=await q.scan(q.byteSource(raw.slice(0,prior.first_pass_container_bytes)));
const second=await q.scan(q.byteSource(raw.slice(0,prior.container_bytes)));
const controls=[];
for(const [name,b,pin] of [
 ['changed_digest',(()=>{const b=raw.slice();b[b.length-1]^=1;return b})(),null],
 ['truncation',raw.slice(0,-1),null],
 ['wrong_repository',raw,{...state.checkpoint,repository_id:'wrong-repository'}]
]){let error=null;try{await q.scan(q.byteSource(b),pin)}catch(e){error=e.message}if(!error)throw Error('CONTROL_ACCEPTED');controls.push({name,rejected:true,error});}
const result={schema:'qikvrt-carrier-independent-readback-v1',observed_at:new Date().toISOString(),implementation_sha256:sha(code),carrier_sha256:sha(raw),carrier_bytes:raw.length,source_bytes_per_pass:prior.source_bytes_per_pass,first_pass_container_bytes:first.bytes,second_pass_added_bytes:second.bytes-first.bytes,second_pass_new_chunks:second.records.filter(r=>r.kind==='chunk').length-first.records.filter(r=>r.kind==='chunk').length,second_pass_reduction_percent:100*(1-(second.bytes-first.bytes)/prior.source_bytes_per_pass),all_restored_entries:restored,original_data_entries_verified:prior.restored_entries.length,negative_controls:controls,scope:'LOCAL_READBACK_WITH_SHARED_ORIGINAL_CODEC; NOT_INDEPENDENT_IMPLEMENTATION_OR_PEER_ACK',effect_ack_done:false};
fs.mkdirSync(root+'/evidence',{recursive:true});
fs.writeFileSync(root+'/evidence/CARRIER_READBACK.json',JSON.stringify(result,null,2)+'\n');
for(const [key,b] of decoded)if(/RECEIPT|NATIVE|journal|events/i.test(key))fs.writeFileSync(root+'/evidence/'+key.split('/').at(-1),b);
console.log(JSON.stringify(result));
