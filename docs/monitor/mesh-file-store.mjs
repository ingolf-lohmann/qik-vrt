// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// File persistence adapter on the existing monitor listener, without an executor.
import './mesh-file-codec.js';
import {open,lstat,statfs,unlink,mkdir,readFile,writeFile} from 'node:fs/promises';
import {constants} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
import {timingSafeEqual,createHash} from 'node:crypto';
const M=globalThis.QikvrtMeshFile;
const identity=s=>[s.dev,s.ino,s.size,s.mtimeMs,s.ctimeMs].join(':');
export class FileMetrics {
  constructor(clock=()=>performance.now()){this.clock=clock;this.started=clock();this.samples=[];this.errors=0;}
  record(kind,bytes,ms=0){this.samples.push({at:this.clock(),kind,bytes,ms});this.prune();}
  prune(){const cut=this.clock()-10000;this.samples=this.samples.filter(s=>s.at>=cut);}
  status(){this.prune();const seconds=Math.max(0.001,Math.min(10,(this.clock()-this.started)/1000));
    const stat=kind=>{const s=this.samples.filter(s=>s.kind===kind);return {operations_per_second:s.length/seconds,
      bytes_per_second:s.reduce((n,x)=>n+x.bytes,0)/seconds,operations:s.length,bytes:s.reduce((n,x)=>n+x.bytes,0),
      mean_latency_ms:s.length?s.reduce((n,x)=>n+x.ms,0)/s.length:null};};
    return {scope:'THIS_ADAPTER_FILE_IO; NOT_DEVICE_IOPS',window_seconds:seconds,read:stat('read'),write:stat('write'),
      sync:stat('sync'),errors:this.errors,observed_at:new Date().toISOString()};}
}
export class MeshFileStore {
  constructor(path,{io={open,lstat,statfs,unlink},metrics=new FileMetrics(),construction=false}={}){
    this.path=path;this.io=io;this.metrics=metrics;this.checkpoint=null;this.hold=null;
    this.construction=construction;
  }
  async reader(){
    const stat=await this.io.lstat(this.path);
    if(!stat.isFile()||stat.isSymbolicLink())throw Error('REGULAR_MESH_FILE_REQUIRED');
    const handle=await this.io.open(this.path,constants.O_RDONLY|(constants.O_NOFOLLOW||0));
    const opened=await handle.stat();if(identity(opened)!==identity(stat)){await handle.close();throw Error('FILE_IDENTITY_CHANGED');}
    return {handle,stat:opened,size:opened.size,read:async(offset,length)=>{
      const b=Buffer.alloc(length);let done=0;const start=performance.now();
      while(done<length){const r=await handle.read(b,done,length-done,offset+done);if(!r.bytesRead)break;done+=r.bytesRead;}
      this.metrics.record('read',done,performance.now()-start);return new Uint8Array(b.subarray(0,done));
    }};
  }
  async inspect(){
    let source;
    try{
      source=await this.reader();const state=await M.scan(source,this.checkpoint);
      if(!this.construction)await M.transportImage(source,state);
      const after=await source.handle.stat(),pathStat=await this.io.lstat(this.path);
      if(identity(source.stat)!==identity(after)||identity(after)!==identity(pathStat))throw Error('FILE_CHANGED_DURING_READ');
      this.checkpoint=state.checkpoint;return state;
    }catch(error){this.metrics.errors++;throw error;}finally{await source?.handle.close();}
  }
  async status(){
    let state,error=null;try{state=await this.inspect();}catch(e){error=e.message;}
    let fs=null;try{const s=await this.io.statfs(dirname(this.path));fs={available_bytes:s.bavail*s.bsize,total_bytes:s.blocks*s.bsize,
      source:'STATFS; NOT_PHYSICAL_DEVICE_ATTESTATION'};}catch{}
    let locked=false;try{await this.io.lstat(this.path+'.lock');locked=true;}catch(e){if(e.code!=='ENOENT')locked=true;}
    const cause=this.hold||error||(locked?'WRITER_LOCK_PRESENT':null);
    const writable=this.construction&&!!state&&!cause&&(!fs||fs.available_bytes>2*M.LIMITS.payload_bytes);
    return {...(state?M.summary(state):{schema:'qikvrt-mesh-file-status/v1',state:'HOLD',effect_ack_done:false}),
      state:cause?'HOLD':state?.state||'HOLD',cause,metrics:this.metrics.status(),filesystem:fs,
      canonical_format:'SQLITE3_WITH_CARRIER_META_AND_EVENTS',transport_role:'DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY',
      orchestration:{accept_writes:writable,max_append_bytes:8*1024*1024,reserve_bytes:2*M.LIMITS.payload_bytes,
        decision:cause?'HOLD':writable?'READY':'READ_ONLY_EXPORT'},checkpoint:this.checkpoint};
  }
  async export(offset=0){
    const state=await this.inspect();
    if(!Number.isSafeInteger(offset)||offset<0||offset>state.bytes||!(offset===0||Array.from(state.heads.values()).includes(offset)))throw Error('FRAME_BOUNDARY_REQUIRED');
    const source=await this.reader();
    // Streaming export is bounded; the caller must verify the final received chain.
    return {state,source,offset};
  }
  async append(suffix,expected){
    if(!this.construction)throw Error('DERIVED_SQLITE_TRANSPORT_READ_ONLY');
    if(this.hold)throw Error(this.hold);
    if(!/^[a-f0-9]{64}$/.test(expected)||!suffix.length||suffix.length>8*1024*1024)throw Error('BOUNDED_APPEND_AND_EXPECTED_HEAD_REQUIRED');
    let lock,writer,source,startedWriting=false,complete=false;
    try{
      lock=await this.io.open(this.path+'.lock','wx',0o600);
      const state=await this.inspect();source=await this.reader();
      if(state.genesis.provenance?.schema==='qikvrt-sqlite-transport/v1')throw Error('DERIVED_SQLITE_TRANSPORT_READ_ONLY');
      const baseOffset=state.heads.get(expected);
      if(baseOffset===undefined)throw Error('HEAD_CONFLICT');
      if(expected!==state.head){
        // Ambiguous/lost HTTP acknowledgement: read back the same immutable suffix.
        if(baseOffset+suffix.length>state.bytes)throw Error('HEAD_CONFLICT');
        for(let at=0;at<suffix.length;at+=M.LIMITS.payload_bytes){
          const got=await source.read(baseOffset+at,Math.min(M.LIMITS.payload_bytes,suffix.length-at));
          if(got.length!==Math.min(M.LIMITS.payload_bytes,suffix.length-at)||!Buffer.from(got).equals(suffix.subarray(at,at+got.length)))throw Error('HEAD_CONFLICT');
        }
        return {...M.summary(state),state:'FILE_APPEND_ALREADY_PRESENT',changed:false};
      }
      const candidate=await M.scan(M.suffixSource(source,suffix),state.checkpoint);
      const fs=await this.io.statfs(dirname(this.path)).catch(()=>null);
      if(fs&&fs.bavail*fs.bsize<suffix.length+2*M.LIMITS.payload_bytes)throw Error('INSUFFICIENT_FILESYSTEM_SPACE');
      const stat=await this.io.lstat(this.path);if(stat.nlink!==1)throw Error('EXCLUSIVE_REGULAR_FILE_REQUIRED');
      writer=await this.io.open(this.path,constants.O_WRONLY|constants.O_APPEND|(constants.O_NOFOLLOW||0));
      if(identity(await writer.stat())!==identity(source.stat))throw Error('FILE_CHANGED_BEFORE_WRITE');
      const began=performance.now();let written=0;startedWriting=true;
      while(written<suffix.length){const r=await writer.write(suffix,written,suffix.length-written);if(!r.bytesWritten)throw Error('ZERO_LENGTH_WRITE');written+=r.bytesWritten;this.metrics.record('write',r.bytesWritten,performance.now()-began);}
      const syncStart=performance.now();await writer.sync();this.metrics.record('sync',0,performance.now()-syncStart);
      await writer.close();writer=null;await source.handle.close();source=null;
      const readback=await this.inspect();if(readback.head!==candidate.head)throw Error('WRITE_READBACK_MISMATCH');
      complete=true;return {...M.summary(readback),state:'FILE_APPEND_DURABLE_READBACK',changed:true,
        durability_scope:'OS_FSYNC_AND_BYTE_READBACK; DEVICE_AND_HOST_POLICY_EXTERNAL'};
    }catch(e){
      this.metrics.errors++;if(startedWriting&&!complete)this.hold='AMBIGUOUS_WRITE_REOPEN_AND_VERIFY';
      if(e.code==='EEXIST')throw Error('WRITER_LOCK_PRESENT');throw e;
    }finally{
      await writer?.close();await source?.handle.close();if(lock){await lock.close();await this.io.unlink(this.path+'.lock');}
    }
  }
}
const equal=(a,b)=>{const x=Buffer.from(a),y=Buffer.from(b);return x.length===y.length&&timingSafeEqual(x,y);};
export function meshFileRoutes(store,token,{allowedOrigins=[]}={}){
  if(!token||token.length<32)throw Error('PRIVATE_MESH_FILE_TOKEN_REQUIRED');
  return async(request,response,url)=>{
    if(!url.pathname.startsWith('/api/mesh-file/'))return false;
    const origin=request.headers.origin;
    const allowed=!origin||origin===new URL('http://'+request.headers.host).origin||origin===new URL('https://'+request.headers.host).origin||allowedOrigins.includes(origin);
    if(origin&&allowed){response.setHeader('Access-Control-Allow-Origin',origin);response.setHeader('Vary','Origin');response.setHeader('Access-Control-Expose-Headers','ETag, Content-Length, X-Qikvrt-Repository-Id, X-Qikvrt-Base-Head');}
    const reply=(code,value)=>{response.writeHead(code,{'content-type':'application/json','cache-control':'no-store','x-content-type-options':'nosniff'});response.end(JSON.stringify(value));};
    if(!allowed){reply(403,{error:'EXPLICIT_CLIENT_ORIGIN_REQUIRED'});return true;}
    if(request.method==='OPTIONS'){
      response.setHeader('Access-Control-Allow-Methods','GET, OPTIONS');response.setHeader('Access-Control-Allow-Headers','Authorization, Content-Type, If-Match');reply(204,{});return true;
    }
    if(!equal(request.headers.authorization||'','Bearer '+token)){reply(401,{error:'OWNER_STORAGE_CREDENTIAL_REQUIRED'});return true;}
    try{
      if(url.pathname==='/api/mesh-file/status'&&request.method==='GET')reply(200,await store.status());
      else if(url.pathname==='/api/mesh-file/bytes'&&request.method==='GET'){
        const raw=url.searchParams.get('after');if(raw&&!/^[a-f0-9]{64}$/.test(raw))throw Error('INVALID_HEAD');
        const state=await store.inspect();if(raw&&!state.heads.has(raw))throw Error('HEAD_CONFLICT');
        const exported=await store.export(raw?state.heads.get(raw):0),{source,offset}=exported;
        try{
          response.writeHead(200,{'content-type':'application/octet-stream','content-length':source.size-offset,
            'cache-control':'no-store','etag':'"'+exported.state.head+'"','x-qikvrt-repository-id':exported.state.repository_id,
            'x-qikvrt-base-head':raw||M.ZERO,'x-content-type-options':'nosniff'});
          for(let at=offset;at<source.size;at+=M.LIMITS.payload_bytes){
            const b=await source.read(at,Math.min(M.LIMITS.payload_bytes,source.size-at));
            if(!response.write(b))await new Promise((resolve,reject)=>{response.once('drain',resolve);response.once('close',()=>reject(Error('EXPORT_DISCONNECTED')));});
          }
        }finally{await source.handle.close();response.end();}
      }else if(url.pathname==='/api/mesh-file/append'&&request.method==='POST'){
        reply(405,{error:'DERIVED_SQLITE_TRANSPORT_READ_ONLY',effect_ack_done:false});
      }else reply(405,{error:'MESH_FILE_OPERATION_NOT_ALLOWED'});
    }catch(e){if(response.headersSent)response.destroy();else reply(/CONFLICT|CHECKPOINT|LOCK|AMBIGUOUS/.test(e.message)?409:422,{error:e.message,effect_ack_done:false});}
    return true;
  };
}

export async function transportExport(store,path,info){
  const source=await new MeshFileStore(store).reader();
  let target,created=false;
  try{
    if(source.size!==info.bytes)throw Error('CANONICAL_IMAGE_SIZE_MISMATCH');
    const provenance={schema:'qikvrt-sqlite-transport/v1',canonical_format:'SQLITE3_WITH_CARRIER_META_AND_EVENTS',
      transport_role:'DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY',canonical_sha256:info.file_sha256,
      canonical_bytes:info.bytes,manifest_sha256:info.manifest_sha256,ledger_id:info.ledger_id,
      source_head:info.source_head,source_tree:info.source_tree};
    const initial=await M.create(info.repositoryId,provenance);
    target=await open(path,'wx',0o600);created=true;
    const wire=createHash('sha256'),image=createHash('sha256');
    let current=M.hex(initial.slice(-32)),sequence=1,size=initial.length;
    async function write(raw){let at=0;while(at<raw.length){const r=await target.write(raw,at,raw.length-at);if(!r.bytesWritten)throw Error('EXPORT_SHORT_WRITE');at+=r.bytesWritten;}wire.update(raw);}
    async function frame(kind,key,payload,id){const raw=await M.frame(current,sequence++,id,kind,key,payload);
      if(size+raw.length>M.LIMITS.file_bytes||sequence>M.LIMITS.records)throw Error('PORTABLE_FILE_LIMIT');
      await write(raw);current=M.hex(raw.slice(-32));size+=raw.length;}
    await write(initial);const refs=[],known=new Set();
    for(let at=0,index=0;at<source.size;at+=M.LIMITS.payload_bytes,index++){
      const raw=await source.read(at,Math.min(M.LIMITS.payload_bytes,source.size-at));
      if(raw.length!==Math.min(M.LIMITS.payload_bytes,source.size-at))throw Error('CANONICAL_IMAGE_TRUNCATED');
      image.update(raw);const sha=await M.digest(raw);refs.push({digest:sha,bytes:raw.length});
      if(!known.has(sha)){await frame('chunk',sha,raw,'sqlite-chunk:'+index);known.add(sha);}
    }
    if(image.digest('hex')!==info.file_sha256)throw Error('CANONICAL_IMAGE_PIN_MISMATCH');
    await frame('entry','canonical/store.sqlite3',M.encoder.encode(M.canonical({bytes:source.size,chunks:refs,media_type:'application/vnd.sqlite3'})),'sqlite-image');
    if(identity(await source.handle.stat())!==identity(source.stat)||identity(await lstat(store))!==identity(source.stat))throw Error('CANONICAL_IMAGE_CHANGED_DURING_EXPORT');
    await target.sync();await target.close();target=null;
    const dir=await open(dirname(path),'r');try{await dir.sync();}finally{await dir.close();}
    const state=await new MeshFileStore(path).inspect();if(state.head!==current)throw Error('EXPORT_READBACK_MISMATCH');
    return {...M.summary(state),canonical_sha256:info.file_sha256,manifest_sha256:info.manifest_sha256,
      canonical_bytes:info.bytes,transport_sha256:wire.digest('hex'),transport_role:provenance.transport_role,
      canonical_format:provenance.canonical_format,effect_ack_done:false};
  }catch(error){await target?.close();if(created)await unlink(path);throw error;}
  finally{await source.handle.close();}
}

export async function portableExport(root,output,value){
  const {head,tree}=value;
  const exported=await transportExport(value.store,join(output,'repository.qmesh'),value);
  const order=['react-runtime.js','mesh-file-codec.js','mesh-file-client.js','mesh-file-view.js','mesh-react.js'];
  const scripts=await Promise.all(order.map(async name=>(await readFile(join(root,'docs/monitor',name),'utf8')).replace(/<\/script/gi,'<\\/script')));
  const pins=scripts.map(s=>"'sha256-"+createHash('sha256').update(s).digest('base64')+"'").join(' ');
  const css=await readFile(join(root,'docs/monitor/mesh-react.css'),'utf8');
  const html='<!doctype html>\n<!-- Copyright 2026 Ingolf Lohmann. SPDX-License-Identifier: CC-BY-NC-ND-4.0; embedded implementation and React retain their notices. -->\n'+
    '<html lang="de" data-qikvrt-offline="true"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src '+pins+'; style-src \'unsafe-inline\'; connect-src https: http://127.0.0.1:* http://localhost:*; base-uri \'none\'; form-action \'none\'">'+
    '<meta name="qikvrt-source-head" content="'+head+'"><meta name="qikvrt-source-tree" content="'+tree+'"><title>QIK-VRT · Universal Terminal</title><style>'+css+'</style></head>'+
    '<body><a class="skip" href="#main">Zum Inhalt</a><div id="qikvrt-react"><p>Universal Terminal wird geladen.</p></div><noscript>Dieser lokale React-Client benötigt JavaScript.</noscript>'+scripts.map(s=>'<script>'+s+'</script>').join('')+'</body></html>\n';
  await writeFile(join(output,'universal-terminal.html'),html,{flag:'wx',mode:0o600});
  const dir=await open(output,'r');try{await dir.sync();}finally{await dir.close();}
  return {...exported,state:'PORTABLE_CANONICAL_SQLITE_EXPORTED',source_head:head,source_tree:tree,
    html_bytes:Buffer.byteLength(html),html_sha256:createHash('sha256').update(html).digest('hex'),whole_runtime_effect_ack_done:false};
}
const main=process.argv[1] && import.meta.url===pathToFileURL(resolve(process.argv[1])).href;
if(main && process.argv[2]==='portable-export'){
  const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
  const value=JSON.parse(Buffer.concat(chunks));
  console.log(JSON.stringify(await portableExport(value.root,value.output,value)));
}
if(main && process.argv[2]==='verify-file'){
  console.log(JSON.stringify(M.summary(await new MeshFileStore(process.argv[3]).inspect())));
}
if(main && process.argv[2]==='verify-frames'){
  console.log(JSON.stringify({...M.summary(await new MeshFileStore(process.argv[3],{construction:true}).inspect()),
    scope:'ARCHIVAL_FRAME_CONSISTENCY_ONLY; NOT_CANONICAL_STORAGE_OR_PRODUCT_ADMISSION'}));
}

if(main && process.argv[2]==='transport-export'){
  const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
  const v=JSON.parse(Buffer.concat(chunks));console.log(JSON.stringify(await transportExport(v.store,v.output,v)));
}
if(main && process.argv[2]==='transport-extract'){
  const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
  const v=JSON.parse(Buffer.concat(chunks)),wire=await readFile(v.source);
  if(createHash('sha256').update(wire).digest('hex')!==v.transport_sha256)throw Error('TRANSPORT_PIN_MISMATCH');
  const source=M.byteSource(wire),state=await M.scan(source),image=await M.transportImage(source,state,v);
  const raw=new Uint8Array(await image.blob.arrayBuffer());
  const file=await open(v.output,'wx',0o600);try{
    await file.writeFile(raw);await file.sync();
  }finally{await file.close();}
  if(createHash('sha256').update(await readFile(v.output)).digest('hex')!==v.file_sha256)throw Error('CANONICAL_IMPORT_READBACK_MISMATCH');
  console.log(JSON.stringify({state:'DERIVED_SQLITE_IMAGE_EXTRACTED; NATIVE_VALIDATION_PENDING',effect_ack_done:false}));
}
