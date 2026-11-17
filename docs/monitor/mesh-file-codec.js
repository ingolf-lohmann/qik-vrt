// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// One byte format shared by the existing React client and Node REST carrier.
(() => {
  'use strict';
  const encoder = new TextEncoder(), decoder = new TextDecoder('utf-8', {fatal:true});
  const MAGIC = encoder.encode('QIKMESH1'), ZERO = '0'.repeat(64);
  const LIMITS = Object.freeze({file_bytes:0xffffffff, metadata_bytes:16384, payload_bytes:1048576, records:100000});
  const fail = message => {throw Error(message);};
  const canonical = value => {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
    return '{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+canonical(value[key])).join(',')+'}';
  };
  const join = (...parts) => {const out=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let offset=0;for(const p of parts){out.set(p,offset);offset+=p.length;}return out;};
  const hex = bytes => Array.from(bytes,v=>v.toString(16).padStart(2,'0')).join('');
  const unhex = value => /^[a-f0-9]{64}$/.test(value) ? Uint8Array.from(value.match(/../g),v=>parseInt(v,16)) : fail('INVALID_DIGEST');
  const digest = async bytes => hex(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes)));
  const u32 = n => {const out=new Uint8Array(4);new DataView(out.buffer).setUint32(0,n,false);return out;};
  const parse = raw => {const value=JSON.parse(decoder.decode(raw));if(canonical(value)!==decoder.decode(raw))fail('NON_CANONICAL_JSON');return value;};
  const validKey = key => typeof key==='string' && key.length>0 && key.length<=4096 && decoder.decode(encoder.encode(key))===key && !/[\u0000-\u001f\u007f]/.test(key);
  const blobSource = (blob, onRead=()=>{}) => ({size:blob.size, async read(offset,length){
    const started=performance.now();const out=new Uint8Array(await blob.slice(offset,offset+length).arrayBuffer());onRead(out.length,performance.now()-started);return out;
  }});
  const byteSource = bytes => ({size:bytes.length, async read(offset,length){return bytes.slice(offset,offset+length);}});
  const suffixSource = (source, suffix) => ({size:source.size+suffix.length, async read(offset,length){
    if(offset>=source.size)return suffix.slice(offset-source.size,offset-source.size+length);
    const first=await source.read(offset,Math.min(length,source.size-offset));
    return first.length===length?first:join(first,suffix.slice(0,length-first.length));
  }});
  async function frame(previous, sequence, id, kind, key, payload) {
    if (!(payload instanceof Uint8Array) || payload.length>LIMITS.payload_bytes) fail('PAYLOAD_LIMIT');
    const meta={sequence,id,kind,key,previous_digest:previous,content_sha256:await digest(payload)};
    const raw=encoder.encode(canonical(meta));if(raw.length>LIMITS.metadata_bytes)fail('METADATA_LIMIT');
    const body=join(u32(raw.length),u32(payload.length),raw,payload);
    const head=await digest(join(encoder.encode('qikmesh-frame/v1\0'),unhex(previous),body));
    return join(body,unhex(head));
  }
  async function create(repositoryId, provenance={}) {
    if(!/^[A-Za-z0-9_.:-]{1,100}$/.test(repositoryId))fail('INVALID_REPOSITORY_ID');
    const payload=encoder.encode(canonical({schema:'qikvrt-mesh-file/v1',repository_id:repositoryId,provenance}));
    return join(MAGIC,await frame(ZERO,0,repositoryId,'genesis','',payload));
  }
  async function scan(source, checkpoint=null) {
    if(!Number.isSafeInteger(source.size)||source.size>LIMITS.file_bytes)fail('PORTABLE_FILE_LIMIT');
    const read=async (offset,length)=>{const b=await source.read(offset,length);if(b.length!==length)fail('TRUNCATED_FILE');return b;};
    if(source.size<8||hex(await read(0,8))!==hex(MAGIC))fail('MAGIC_OR_VERSION_MISMATCH');
    let offset=8,head=ZERO,sequence=0,repositoryId=null,checkpointFound=!checkpoint,genesis=null;
    const records=[], ids=new Map(), chunks=new Map(), entries=new Map(), heads=new Map();
    heads.set(ZERO,8);
    while(offset<source.size){
      if(records.length>=LIMITS.records)fail('RECORD_LIMIT');
      const header=await read(offset,8), view=new DataView(header.buffer,header.byteOffset,8);
      const m=view.getUint32(0,false),p=view.getUint32(4,false),length=8+m+p+32;
      if(!m||m>LIMITS.metadata_bytes||p>LIMITS.payload_bytes)fail('FRAME_LENGTH_LIMIT');
      if(offset+length>source.size)fail('TRUNCATED_FRAME');
      const raw=await read(offset+8,m),meta=parse(raw),payload=await read(offset+8+m,p),claimed=hex(await read(offset+8+m+p,32));
      if(!meta||Object.keys(meta).sort().join(',')!=='content_sha256,id,key,kind,previous_digest,sequence'||
          meta.sequence!==sequence||meta.previous_digest!==head||typeof meta.id!=='string'||
          !/^[A-Za-z0-9_.:-]{1,160}$/.test(meta.id)||ids.has(meta.id))fail('RECORD_IDENTITY_OR_ORDER');
      if(await digest(payload)!==meta.content_sha256)fail('CONTENT_DIGEST_MISMATCH');
      const calculated=await digest(join(encoder.encode('qikmesh-frame/v1\0'),unhex(head),header,raw,payload));
      if(calculated!==claimed)fail('CHAIN_DIGEST_MISMATCH');
      const record={...meta,digest:claimed,offset,end:offset+length,payload_offset:offset+8+m,payload_bytes:p};
      if(sequence===0){
        genesis=parse(payload);
        if(meta.kind!=='genesis'||meta.key!==''||genesis.schema!=='qikvrt-mesh-file/v1'||genesis.repository_id!==meta.id)fail('GENESIS_MISMATCH');
        repositoryId=genesis.repository_id;
        if(checkpoint && checkpoint.repository_id!==repositoryId)fail('CHECKPOINT_REPOSITORY_MISMATCH');
      }else if(meta.kind==='chunk'){
        if(meta.key!==meta.content_sha256)fail('CHUNK_KEY_MISMATCH');
        chunks.set(meta.key,record);
      }else if(meta.kind==='entry'){
        if(!validKey(meta.key))fail('INVALID_VIRTUAL_KEY');
        const value=parse(payload);
        if(!value||Object.keys(value).sort().join(',')!=='bytes,chunks,media_type'||!Array.isArray(value.chunks)||
            typeof value.media_type!=='string'||value.media_type.length>200||/[\r\n]/.test(value.media_type)||
            !Number.isSafeInteger(value.bytes)||value.bytes<0)fail('INVALID_ENTRY_DESCRIPTOR');
        let size=0;
        for(const chunk of value.chunks){
          if(!chunk||Object.keys(chunk).sort().join(',')!=='bytes,digest'||!chunks.has(chunk.digest)||
             chunks.get(chunk.digest).payload_bytes!==chunk.bytes)fail('UNRESOLVED_CHUNK');
          size+=chunk.bytes;
        }
        if(size!==value.bytes)fail('ENTRY_SIZE_MISMATCH');
        entries.set(meta.key,{...value,record,content_root_sha256:meta.content_sha256});
      }else if(meta.kind==='event'){
        if(!validKey(meta.key))fail('INVALID_VIRTUAL_KEY');
      }else fail('UNKNOWN_RECORD_KIND');
      records.push(record);ids.set(meta.id,record);head=claimed;heads.set(head,record.end);
      if(checkpoint?.head===head)checkpointFound=true;
      offset+=length;sequence++;
    }
    if(!genesis)fail('GENESIS_REQUIRED');
    if(!checkpointFound)fail('CONFIRMED_CHECKPOINT_MISSING');
    return {schema:'qikvrt-mesh-file-status/v1',state:'VERIFIED',repository_id:repositoryId,head,bytes:source.size,
      records,ids,chunks,entries,heads,genesis,checkpoint:{repository_id:repositoryId,head},
      format_limits:LIMITS,integrity_scope:'BYTE_CONSISTENCY; NOT_AUTHOR_AUTHENTICATION',effect_ack_done:false};
  }
  function summary(state){return {schema:state.schema,state:state.state,repository_id:state.repository_id,head:state.head,
    bytes:state.bytes,records:state.records.length,entries:state.entries.size,format_limits:LIMITS,
    integrity_scope:state.integrity_scope,effect_ack_done:false};}
  async function addEntry(state,key,source,{id,mediaType='application/octet-stream',asBlob=false}={}) {
    if(!validKey(key)||!Number.isSafeInteger(source.size)||source.size<0||source.size>LIMITS.file_bytes)fail('INVALID_ENTRY_INPUT');
    id=id||crypto.randomUUID();let sequence=state.records.length,head=state.head;
    const parts=[],chunks=[],known=new Set(state.chunks.keys());
    async function append(kind,k,p,recordId){const raw=await frame(head,sequence++,recordId,kind,k,p);head=hex(raw.slice(-32));parts.push(asBlob?new Blob([raw]):raw);}
    for(let at=0,index=0;at<source.size;at+=LIMITS.payload_bytes,index++){
      const payload=await source.read(at,Math.min(LIMITS.payload_bytes,source.size-at));
      if(!payload.length||payload.length!==Math.min(LIMITS.payload_bytes,source.size-at))fail('ENTRY_READ_TRUNCATED');
      const sha=await digest(payload);chunks.push({digest:sha,bytes:payload.length});
      if(!known.has(sha)){await append('chunk',sha,payload,id+':'+index);known.add(sha);}
    }
    const descriptor=encoder.encode(canonical({bytes:source.size,chunks,media_type:mediaType}));
    await append('entry',key,descriptor,id);
    const suffix=asBlob?new Blob(parts):join(...parts);
    if(state.bytes+(asBlob?suffix.size:suffix.length)>LIMITS.file_bytes)fail('PORTABLE_FILE_LIMIT');
    return {suffix,head,id};
  }
  async function entryBlob(source,state,key,onRead=()=>{}){
    const entry=state.entries.get(key);if(!entry)fail('ENTRY_NOT_FOUND');const parts=[];
    for(const ref of entry.chunks){
      const chunk=state.chunks.get(ref.digest);const raw=await source.read(chunk.payload_offset,chunk.payload_bytes);
      if(raw.length!==ref.bytes||await digest(raw)!==ref.digest)fail('ENTRY_READBACK_DIGEST');
      onRead(raw.length);parts.push(new Blob([raw]));
    }
    return new Blob(parts,{type:entry.media_type});
  }
  async function transportImage(source,state,pins={}){
    const p=state.genesis?.provenance, key='canonical/store.sqlite3';
    if(!p||p.schema!=='qikvrt-sqlite-transport/v1'||p.canonical_format!=='SQLITE3_WITH_CARRIER_META_AND_EVENTS'||
        p.transport_role!=='DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY'||!Number.isSafeInteger(p.canonical_bytes)||
        p.canonical_bytes<100||!/^[a-f0-9]{64}$/.test(p.canonical_sha256)||
        !/^[a-f0-9]{64}$/.test(p.manifest_sha256)||!/^[a-f0-9]{32}$/.test(p.ledger_id)||
        !/^[a-f0-9]{40}$/.test(p.source_head)||!/^[a-f0-9]{40}$/.test(p.source_tree)||
        state.entries.size!==1||!state.entries.has(key)||
        state.records.filter(r=>r.kind==='entry').length!==1||state.records.some(r=>r.kind==='event'))
      fail('DERIVED_SQLITE_TRANSPORT_REQUIRED; LEGACY_SOURCE_ONLY_QIKMESH_NOT_A_PRODUCT_STORE');
    if(pins.file_sha256&&pins.file_sha256!==p.canonical_sha256)fail('CANONICAL_IMAGE_PIN_MISMATCH');
    if(pins.manifest_sha256&&pins.manifest_sha256!==p.manifest_sha256)fail('PACKAGE_MANIFEST_PIN_MISMATCH');
    const blob=await entryBlob(source,state,key);
    if(blob.size!==p.canonical_bytes)fail('CANONICAL_IMAGE_SIZE_MISMATCH');
    const bytes=new Uint8Array(await blob.arrayBuffer());
    const header=new DataView(bytes.buffer,bytes.byteOffset,bytes.length);
    if(decoder.decode(bytes.slice(0,16))!=='SQLite format 3\0'||bytes[18]!==1||bytes[19]!==1||
        header.getUint32(68)!==0x51495654||header.getUint32(60)!==1)fail('CHECKPOINTED_SQLITE_MONOLITH_REQUIRED');
    if(await digest(bytes)!==p.canonical_sha256)fail('CANONICAL_IMAGE_DIGEST_MISMATCH');
    return {blob,provenance:p,scope:'BYTE_EXACT_EXPORT; NATIVE_SCHEMA_AND_LEDGER_VALIDATION_REQUIRED_BEFORE_IMPORT',
      canonical_format:p.canonical_format,transport_role:p.transport_role,effect_ack_done:false};
  }
  globalThis.QikvrtMeshFile=Object.freeze({MAGIC,ZERO,LIMITS,canonical,join,hex,digest,frame,create,scan,summary,
    blobSource,byteSource,suffixSource,addEntry,entryBlob,transportImage,encoder,decoder});
})();
