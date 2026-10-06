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
  constructor(path,{io={open,lstat,statfs,unlink},metrics=new FileMetrics()}={}){
    this.path=path;this.io=io;this.metrics=metrics;this.checkpoint=null;this.hold=null;
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
    const writable=!!state&&!cause&&(!fs||fs.available_bytes>2*M.LIMITS.payload_bytes);
    return {...(state?M.summary(state):{schema:'qikvrt-mesh-file-status/v1',state:'HOLD',effect_ack_done:false}),
      state:cause?'HOLD':state?.state||'HOLD',cause,metrics:this.metrics.status(),filesystem:fs,
      orchestration:{accept_writes:writable,max_append_bytes:8*1024*1024,reserve_bytes:2*M.LIMITS.payload_bytes,
        decision:cause?'HOLD':writable?'READY':'CAPACITY_HOLD'},checkpoint:this.checkpoint};
  }
  async export(offset=0){
    const state=await this.inspect();
    if(!Number.isSafeInteger(offset)||offset<0||offset>state.bytes||!(offset===0||Array.from(state.heads.values()).includes(offset)))throw Error('FRAME_BOUNDARY_REQUIRED');
    const source=await this.reader();
    // Streaming export is bounded; the caller must verify the final received chain.
    return {state,source,offset};
  }
  async append(suffix,expected){
    if(this.hold)throw Error(this.hold);
    if(!/^[a-f0-9]{64}$/.test(expected)||!suffix.length||suffix.length>8*1024*1024)throw Error('BOUNDED_APPEND_AND_EXPECTED_HEAD_REQUIRED');
    let lock,writer,source,startedWriting=false,complete=false;
    try{
      lock=await this.io.open(this.path+'.lock','wx',0o600);
      const state=await this.inspect();source=await this.reader();
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
      response.setHeader('Access-Control-Allow-Methods','GET, POST, OPTIONS');response.setHeader('Access-Control-Allow-Headers','Authorization, Content-Type, If-Match');reply(204,{});return true;
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
        if(request.headers['content-type']!=='application/octet-stream'){reply(415,{error:'BINARY_SUFFIX_REQUIRED'});return true;}
        const match=/^"([a-f0-9]{64})"$/.exec(request.headers['if-match']||'');if(!match)throw Error('EXPECTED_HEAD_REQUIRED');
        const parts=[];let size=0;for await(const p of request){size+=p.length;if(size>8*1024*1024){reply(413,{error:'APPEND_LIMIT'});return true;}parts.push(p);}
        reply(200,await store.append(Buffer.concat(parts),match[1]));
      }else reply(405,{error:'MESH_FILE_OPERATION_NOT_ALLOWED'});
    }catch(e){if(response.headersSent)response.destroy();else reply(/CONFLICT|CHECKPOINT|LOCK|AMBIGUOUS/.test(e.message)?409:422,{error:e.message,effect_ack_done:false});}
    return true;
  };
}

export async function portableExport(root,output,{files,head,tree,repositoryId}){
  // Extend the existing S1 exporter. There is one persistent data file and one
  // self-contained React HTML client; Git is used only to verify source export.
  await mkdir(output,{mode:0o700});
  const path=join(output,'repository.qmesh'),file=await open(path,'wx',0o600);
  const git=spawn('git',['-C',root,'cat-file','--batch'],{stdio:['pipe','pipe','pipe']});
  const stream=git.stdout[Symbol.asyncIterator]();let pending=Buffer.alloc(0);
  // Read original object bytes, not checkout text transformed by .gitattributes.
  // Paths stay virtual; even unextractable OS names can be exported this way.
  async function read(length){
    while(pending.length<length){const next=await stream.next();if(next.done)throw Error('GIT_BLOB_STREAM_TRUNCATED');pending=Buffer.concat([pending,next.value]);}
    const out=pending.subarray(0,length);pending=pending.subarray(length);return out;
  }
  async function header(){let value='';for(let i=0;i<256;i++){const b=await read(1);if(b[0]===10)return value;value+=String.fromCharCode(b[0]);}throw Error('GIT_BLOB_HEADER_LIMIT');}
  const initial=await M.create(repositoryId,{source_repository:'ingolf-lohmann/qik-vrt',source_head:head,source_tree:tree,
    human_actor:'Ingolf Lohmann',ai_actor:'OpenAI Codex / GPT-6',scope:'EXACT_SOURCE_FILES; NOT_LIVE_CLOUD_STATE'});
  let sequence=1,current=M.hex(initial.slice(-32)),size=initial.length;const known=new Set();
  async function write(bytes){let offset=0;while(offset<bytes.length){const r=await file.write(bytes,offset,bytes.length-offset);if(!r.bytesWritten)throw Error('EXPORT_SHORT_WRITE');offset+=r.bytesWritten;}}
  async function append(id,kind,key,payload){if(sequence>=M.LIMITS.records)throw Error('RECORD_LIMIT');const raw=await M.frame(current,sequence++,id,kind,key,payload);
    if(size+raw.length>M.LIMITS.file_bytes)throw Error('PORTABLE_FILE_LIMIT');await write(raw);current=M.hex(raw.slice(-32));size+=raw.length;}
  async function entry(key,source,id,mediaType='application/octet-stream',gitSha=null){
    const gitHash=gitSha?createHash('sha1').update('blob '+source.size+'\0'):null;
    const chunks=[];for(let at=0,index=0;at<source.size;at+=M.LIMITS.payload_bytes,index++){
      const bytes=await source.read(at,Math.min(M.LIMITS.payload_bytes,source.size-at));if(bytes.length!==Math.min(M.LIMITS.payload_bytes,source.size-at))throw Error('SOURCE_TRUNCATED');
      gitHash?.update(bytes);
      const sha=await M.digest(bytes);chunks.push({digest:sha,bytes:bytes.length});if(!known.has(sha)){await append(id+':'+index,'chunk',sha,bytes);known.add(sha);}
    }
    if(gitHash&&gitHash.digest('hex')!==gitSha)throw Error('SOURCE_BLOB_DRIFT');
    await append(id,'entry',key,M.encoder.encode(M.canonical({bytes:source.size,chunks,media_type:mediaType})));
  }
  try{
    await write(initial);
    for(const item of files){
      if(!/^[a-f0-9]{40}$/.test(item.sha))throw Error('INVALID_SOURCE_BLOB');
      git.stdin.write(item.sha+'\n');const metadata=await header(),match=/^([a-f0-9]{40}) blob ([0-9]+)$/.exec(metadata);
      if(!match||match[1]!==item.sha)throw Error('EXACT_SOURCE_BLOB_REQUIRED');
      const source={size:Number(match[2]),async read(at,length){return new Uint8Array(await read(length));}};
      await entry(item.path,source,'source:'+item.sha+':'+sequence,'application/octet-stream',item.sha);
      if((await read(1))[0]!==10)throw Error('GIT_BLOB_BOUNDARY_MISMATCH');
    }
    await entry('QIKVRT_SOURCE_TREE.json',M.byteSource(M.encoder.encode(M.canonical({head,tree,files,
      representation:'ORIGINAL_COMMITTED_BLOB_BYTES; CHECKOUT_EOL_TRANSFORMS_NOT_APPLIED'}))), 'source-tree');
    await file.sync();
  }finally{git.stdin.end();git.kill();await file.close();}
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
  const store=new MeshFileStore(path),state=await store.inspect();if(state.head!==current)throw Error('EXPORT_READBACK_MISMATCH');
  return {...M.summary(state),state:'PORTABLE_SOURCE_EXPORTED',source_head:head,source_tree:tree,source_files:files.length,
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
