// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Versioned offline working replica. Never an executor or native approval ledger.
import {gitBlobHasher,gitTree} from './git-hash.js';
export const LIMITS = Object.freeze({chunk:1048576, files:100000, revisions:10000, total:2147483648, line:1500000, path:1024});
const encoder = new TextEncoder(), decoder = new TextDecoder('utf-8',{fatal:true});
const fail = code => {throw Error(code);};
export function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
  return '{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+canonical(value[key])).join(',')+'}';
}
export async function digest(bytes) {return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
const hashObject = value => digest(encoder.encode(canonical(value)));
const sha = value => typeof value==='string' && /^[a-f0-9]{64}$/.test(value);
export function validPath(path) {
  if(typeof path!=='string'||!path||encoder.encode(path).length>LIMITS.path||/[\x00-\x1f\x7f\\]/.test(path)||path.startsWith('/')||path.split('/').some(p=>!p||p==='.'||p==='..'||['__proto__','constructor','prototype','.git'].includes(p)))fail('INVALID_REPOSITORY_PATH');
  return path;
}
function checkSnapshot(s) {
  if(!s||s.schema!=='qikvrt-offline-snapshot/v1'||typeof s.repository_id!=='string'||!s.repository_id||s.repository_id.length>150||!Array.isArray(s.parents)||s.parents.length>2||s.parents.some(p=>!sha(p))||new Set(s.parents).size!==s.parents.length||!Array.isArray(s.files)||s.files.length>LIMITS.files||typeof s.created_at!=='string'||!Number.isFinite(Date.parse(s.created_at))||typeof s.message!=='string'||s.message.length>1000)fail('INVALID_SNAPSHOT');
  let previous='',total=0;
  for(const f of s.files){validPath(f.path);if(f.path<=previous||!['100644','100755','120000'].includes(f.mode)||!Number.isSafeInteger(f.bytes)||f.bytes<0||!Array.isArray(f.chunks)||f.chunks.length>2048)fail('INVALID_FILE_INVENTORY');previous=f.path;
    if(!/^[a-f0-9]{40}$/.test(f.git_blob_sha1||''))fail('INVALID_GIT_BLOB');let bytes=0;for(const c of f.chunks){if(!sha(c.sha256)||!Number.isSafeInteger(c.bytes)||c.bytes<1||c.bytes>LIMITS.chunk)fail('INVALID_CONTENT_BLOCK');bytes+=c.bytes;}if(bytes!==f.bytes)fail('FILE_LENGTH_MISMATCH');total+=bytes;
  }if(total>LIMITS.total)fail('REPOSITORY_CAPACITY_LIMIT');
  const paths=new Set(s.files.map(f=>f.path));for(const path of paths){const parts=path.split('/');for(let i=1;i<parts.length;i++)if(paths.has(parts.slice(0,i).join('/')))fail('FILE_DIRECTORY_CONFLICT');}
  if(gitTree(s.files)!==s.git_tree_sha1)fail('GIT_TREE_READBACK_MISMATCH');
  if(s.source!==null&&(!s.source||s.source.repository!==s.repository_id||!/^[a-f0-9]{40}$/.test(s.source.head||'')||!/^[a-f0-9]{40}$/.test(s.source.tree||'')||!['COMPLETE_GIT_WORKING_TREE','SELECTED_GIT_FILES'].includes(s.source.scope)))fail('INVALID_SOURCE_BINDING');
  if(s.source?.scope==='COMPLETE_GIT_WORKING_TREE'&&!s.parents.length&&s.source.tree!==s.git_tree_sha1)fail('COMPLETE_SOURCE_TREE_MISMATCH');
  if(encoder.encode(canonical(s)).length>LIMITS.line-200)fail('SNAPSHOT_METADATA_CAPACITY_LIMIT');
  return total;
}
const request = r => new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
function write(db, stores, action) {return new Promise((resolve,reject)=>{
  let tx;try{tx=db.transaction(stores,'readwrite',{durability:'strict'});}catch(e){reject(e);return;}
  tx.oncomplete=()=>resolve();tx.onabort=tx.onerror=()=>reject(Error(tx.error?.name==='QuotaExceededError'?'OFFLINE_STORAGE_QUOTA':'OFFLINE_COMMIT_FAILED'));
  try{action(tx);}catch(e){tx.abort();reject(e);}
});}
async function* archiveLines(file) {
  if(!file||file.size>LIMITS.total*2)fail('ARCHIVE_CAPACITY_LIMIT');
  const gzip=file.name?.endsWith('.gz');if(gzip&&!globalThis.DecompressionStream)fail('GZIP_IMPORT_UNSUPPORTED');const reader=(gzip?file.stream().pipeThrough(new DecompressionStream('gzip')):file.stream()).getReader();let pending='';const d=new TextDecoder('utf-8',{fatal:true});let streamed=0;
  try{while(true){const {value,done}=await reader.read();streamed+=value?.length||0;if(streamed>LIMITS.total*2)fail('ARCHIVE_CAPACITY_LIMIT');pending+=d.decode(value,{stream:!done});let at;
    while((at=pending.indexOf('\n'))>=0){const line=pending.slice(0,at);pending=pending.slice(at+1);if(!line||line.length>LIMITS.line)fail('INVALID_ARCHIVE_RECORD');yield JSON.parse(line);}
    if(pending.length>LIMITS.line)fail('ARCHIVE_RECORD_TOO_LARGE');if(done)break;
  }if(pending)fail('TRUNCATED_ARCHIVE');}finally{reader.releaseLock();}
}
function fromBase64(text) {if(typeof text!=='string'||text.length>Math.ceil(LIMITS.chunk/3)*4||text.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(text))fail('INVALID_BASE64_BLOCK');const value=atob(text);return Uint8Array.from(value,c=>c.charCodeAt(0));}
function toBase64(bytes) {let out='';for(let at=0;at<bytes.length;at+=32768)out+=String.fromCharCode(...bytes.subarray(at,at+32768));return btoa(out);}
const asMap=s=>new Map(s.files.map(f=>[f.path,f]));
const equal=(a,b)=>canonical(a??null)===canonical(b??null);
export class Repository {
  static async open(name='qikvrt-offline-repository-v1') {
    if(!globalThis.indexedDB||!crypto?.subtle)fail('SECURE_BROWSER_STORAGE_REQUIRED');
    const db=await new Promise((resolve,reject)=>{const r=indexedDB.open(name,1);r.onupgradeneeded=()=>{for(const store of ['blocks','snapshots','refs'])r.result.createObjectStore(store);};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(Error('OFFLINE_STORAGE_UNAVAILABLE'));r.onblocked=()=>reject(Error('OFFLINE_STORAGE_BUSY'));});
    db.onversionchange=()=>db.close();return new Repository(db);
  }
  constructor(db){this.db=db;}
  close(){this.db.close();}
  get(store,key){return request(this.db.transaction(store,'readonly').objectStore(store).get(key));}
  async checkpointSession(id, state, {foreground=false}={}) {
    if (!/^[a-f0-9-]{36}$/.test(id) || !state || typeof state.path !== 'string' || typeof state.text !== 'string') fail('INVALID_EDITOR_CHECKPOINT');
    const prepared=state.prepared??null;
    if(prepared!==null&&(!(prepared instanceof Blob)||prepared.size>LIMITS.total*2))fail('INVALID_EDITOR_CHECKPOINT');
    const prepared_binding=prepared?{name:prepared.name||'qikvrt.qikvrt',type:prepared.type,size:prepared.size,sha256:await digest(await prepared.arrayBuffer())}:null;
    const value = {schema:'qikvrt-editor-checkpoint/v1', saved_at:new Date().toISOString(), state:{...state,prepared:null}, prepared_binding};
    if (encoder.encode(canonical(value)).length > 8388608) fail('EDITOR_CHECKPOINT_CAPACITY_LIMIT');
    const row = {value, prepared, sha256:await hashObject(value)};
    // Separate refs key: no snapshot/head mutation and no schema upgrade lock.
    await write(this.db, ['refs'], tx => {const refs=tx.objectStore('refs');refs.put(row,'editor:'+id);
      // Decide foreground ownership at the durable-write boundary, after hashing.
      if(typeof foreground==='function'?foreground():foreground)refs.put(id,'editor:last');});
    const readback = await this.session(id);
    if (!equal({...readback,prepared:null}, {...state,prepared:null})) fail('EDITOR_CHECKPOINT_READBACK_MISMATCH');
    return readback;
  }
  async session(id) {
    if (!/^[a-f0-9-]{36}$/.test(id)) fail('INVALID_EDITOR_CHECKPOINT');
    const row = await this.get('refs', 'editor:'+id);
    if (!row) return null;
    if (row.value?.schema !== 'qikvrt-editor-checkpoint/v1' || await hashObject(row.value) !== row.sha256) fail('EDITOR_CHECKPOINT_READBACK_MISMATCH');
    const binding=row.value.prepared_binding;
    if(binding&&(!(row.prepared instanceof Blob)||row.prepared.size!==binding.size||row.prepared.type!==binding.type||await digest(await row.prepared.arrayBuffer())!==binding.sha256))fail('EDITOR_CHECKPOINT_READBACK_MISMATCH');
    return {...row.value.state,prepared:binding?new File([row.prepared],binding.name,{type:binding.type}):null};
  }
  async sessions() {
    const keys=await request(this.db.transaction('refs','readonly').objectStore('refs').getAllKeys()),out=[];
    for(const key of keys){if(key==='editor:last'||!String(key).startsWith('editor:'))continue;const id=String(key).slice(7);
      try{const state=await this.session(id),row=await this.get('refs',key);out.push({id,state,saved_at:row.value.saved_at??null});}
      catch{out.push({id,unavailable:true});}
    }
    return out.sort((a,b)=>(b.saved_at??'').localeCompare(a.saved_at??''));
  }
  async snapshot(id){const row=await this.get('snapshots',id);if(!row||await hashObject(row)!==id)fail('SNAPSHOT_READBACK_MISMATCH');checkSnapshot(row);return row;}
  async head(){const id=await this.get('refs','head');return id?{id,snapshot:await this.snapshot(id)}:null;}
  async block(id){const blob=await this.get('blocks',id);if(!(blob instanceof Blob)||blob.size>LIMITS.chunk||await digest(await blob.arrayBuffer())!==id)fail('CONTENT_READBACK_MISMATCH');return blob;}
  async putBlock(bytes){const id=await digest(bytes);await write(this.db,['blocks'],tx=>tx.objectStore('blocks').put(new Blob([bytes]),id));await this.block(id);return {sha256:id,bytes:bytes.length};}
  async checkContent(snapshot){checkSnapshot(snapshot);for(const f of snapshot.files){const hash=gitBlobHasher(f.bytes);for(const c of f.chunks){const block=await this.block(c.sha256);if(block.size!==c.bytes)fail('CONTENT_LENGTH_MISMATCH');hash.update(new Uint8Array(await block.arrayBuffer()));}if(hash.hex()!==f.git_blob_sha1)fail('GIT_BLOB_READBACK_MISMATCH');}return snapshot;}
  async ancestors(id){const result=new Map(),queue=[id];while(queue.length){const key=queue.shift();if(result.has(key))continue;const s=await this.snapshot(key);result.set(key,s);if(result.size>LIMITS.revisions)fail('HISTORY_CAPACITY_LIMIT');queue.push(...s.parents);}return result;}
  async advance(snapshot,expected){checkSnapshot(snapshot);await this.checkContent(snapshot);const id=await hashObject(snapshot);let conflict=false;
    await new Promise((resolve,reject)=>{const tx=this.db.transaction(['snapshots','refs'],'readwrite',{durability:'strict'});tx.oncomplete=resolve;tx.onabort=tx.onerror=()=>reject(Error(conflict?'CONCURRENT_REPOSITORY_CHANGE':tx.error?.name==='QuotaExceededError'?'OFFLINE_STORAGE_QUOTA':'OFFLINE_COMMIT_FAILED'));
      const refs=tx.objectStore('refs'),r=refs.get('head');r.onsuccess=()=>{if((r.result??null)!==expected){conflict=true;tx.abort();return;}tx.objectStore('snapshots').put(snapshot,id);refs.put(id,'head');};});
    const after=await this.head();if(after.id!==id)fail('COMMIT_READBACK_MISMATCH');return after;
  }
  async create(repository_id='ingolf-lohmann/qik-vrt'){if(await this.head())fail('REPOSITORY_ALREADY_EXISTS');return this.advance({schema:'qikvrt-offline-snapshot/v1',repository_id,parents:[],source:null,created_at:new Date().toISOString(),message:'Offline-Arbeitskopie angelegt',files:[],git_tree_sha1:gitTree([])},null);}
  async save(path,file,{expected,mode,message='Lokaler Arbeitsstand'}={}){
    validPath(path);const head=await this.head();if(!head||head.id!==expected)fail('CONCURRENT_REPOSITORY_CHANGE');if(!(file instanceof Blob)||file.size>LIMITS.total)fail('FILE_REQUIRED');
    const chunks=[],hash=gitBlobHasher(file.size);for(let at=0;at<file.size;at+=LIMITS.chunk){const bytes=new Uint8Array(await file.slice(at,at+LIMITS.chunk).arrayBuffer());hash.update(bytes);chunks.push(await this.putBlock(bytes));}
    const files=asMap(head.snapshot);mode=mode??files.get(path)?.mode??'100644';files.set(path,{path,mode,bytes:file.size,chunks,git_blob_sha1:hash.hex()});const next=[...files.values()].sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);return this.advance({...head.snapshot,parents:[head.id],created_at:new Date().toISOString(),message,files:next,git_tree_sha1:gitTree(next)},expected);
  }
  async remove(path,expected){validPath(path);const head=await this.head();if(!head||head.id!==expected)fail('CONCURRENT_REPOSITORY_CHANGE');if(!head.snapshot.files.some(f=>f.path===path))fail('FILE_NOT_FOUND');const files=head.snapshot.files.filter(f=>f.path!==path);return this.advance({...head.snapshot,parents:[head.id],created_at:new Date().toISOString(),message:'Datei entfernt: '+path,files,git_tree_sha1:gitTree(files)},expected);}
  async file(path,id){const s=id?await this.snapshot(id):(await this.head())?.snapshot;const f=s?.files.find(f=>f.path===path);if(!f)fail('FILE_NOT_FOUND');const parts=[];for(const c of f.chunks)parts.push(await this.block(c.sha256));return new Blob(parts,{type:'application/octet-stream'});}
  async exportArchive(){const head=await this.head();if(!head)fail('NO_LOCAL_REPOSITORY');const history=await this.ancestors(head.id),parts=[JSON.stringify({schema:'qikvrt-offline-archive/v1',repository_id:head.snapshot.repository_id,head:head.id})+'\n'];const known=new Set();
    // Blob parts avoid concatenating a whole repository into one JS string.
    for(const s of history.values())for(const f of s.files)for(const c of f.chunks)if(!known.has(c.sha256)){known.add(c.sha256);const b=await this.block(c.sha256);parts.push(new Blob([JSON.stringify({type:'block',sha256:c.sha256,data:toBase64(new Uint8Array(await b.arrayBuffer()))})+'\n']));}
    const ordered=[...history].reverse();for(const [id,snapshot] of ordered)parts.push(JSON.stringify({type:'snapshot',id,snapshot})+'\n');parts.push(JSON.stringify({type:'end',head:head.id,blocks:known.size,snapshots:history.size})+'\n');return new Blob(parts,{type:'application/x-qikvrt-repository'});
  }
  async importArchive(file){const before=await this.head();let header,end,records=0,total=0;const blocks=new Set(),snapshots=new Map();
    for await(const row of archiveLines(file)){
      if(end)fail('TRAILING_ARCHIVE_RECORD');if(!header){if(row.schema!=='qikvrt-offline-archive/v1'||!sha(row.head)||typeof row.repository_id!=='string')fail('INVALID_ARCHIVE_HEADER');header=row;if(before&&row.repository_id!==before.snapshot.repository_id)fail('REPOSITORY_IDENTITY_MISMATCH');continue;}
      if(row.type==='block'){if(!sha(row.sha256)||blocks.has(row.sha256))fail('DUPLICATE_OR_INVALID_BLOCK');const bytes=fromBase64(row.data);if(!bytes.length||await digest(bytes)!==row.sha256)fail('ARCHIVE_CONTENT_DIGEST_MISMATCH');total+=bytes.length;if(total>LIMITS.total)fail('REPOSITORY_CAPACITY_LIMIT');await this.putBlock(bytes);blocks.add(row.sha256);}
      else if(row.type==='snapshot'){checkSnapshot(row.snapshot);if(row.snapshot.repository_id!==header.repository_id||!sha(row.id)||snapshots.has(row.id)||await hashObject(row.snapshot)!==row.id||++records>LIMITS.revisions)fail('ARCHIVE_SNAPSHOT_MISMATCH');snapshots.set(row.id,row.snapshot);}
      else if(row.type==='end')end=row;else fail('UNKNOWN_ARCHIVE_RECORD');
    }
    if(!header||!end||end.head!==header.head||end.blocks!==blocks.size||end.snapshots!==snapshots.size||!snapshots.has(header.head))fail('INCOMPLETE_ARCHIVE');
    for(const s of snapshots.values()){for(const parent of s.parents)if(!snapshots.has(parent))fail('INCOMPLETE_HISTORY');for(const f of s.files)for(const c of f.chunks)if(!blocks.has(c.sha256))fail('INCOMPLETE_CONTENT');await this.checkContent(s);}
    const reachable=new Set(),visiting=new Set(),stack=[[header.head,false]];while(stack.length){const [id,done]=stack.pop();if(done){visiting.delete(id);reachable.add(id);continue;}if(visiting.has(id))fail('CYCLIC_HISTORY');if(reachable.has(id))continue;visiting.add(id);stack.push([id,true]);for(const parent of snapshots.get(id).parents)stack.push([parent,false]);}if(reachable.size!==snapshots.size)fail('UNREACHABLE_ARCHIVE_HISTORY');
    // Unreferenced staged content may survive a rejected import; visible refs never do.
    await write(this.db,['snapshots'],tx=>{for(const [id,s]of snapshots)tx.objectStore('snapshots').put(s,id);});
    if(before&&!reachable.has(before.id)&&before.id!==header.head){await write(this.db,['refs'],tx=>tx.objectStore('refs').put(header.head,'incoming:'+header.head));return {state:'DIVERGENT_IMPORTED',head:before.id,incoming:header.head};}
    const result=await this.advance(snapshots.get(header.head),before?.id??null);return {state:'IMPORTED',head:result.id,incoming:null};
  }
  async incoming(){const tx=this.db.transaction('refs','readonly'),store=tx.objectStore('refs');const keys=await request(store.getAllKeys());const out=[];for(const key of keys)if(String(key).startsWith('incoming:'))out.push(await this.get('refs',key));return out;}
  async history(){const head=await this.head();return head?[...await this.ancestors(head.id)].map(([id,snapshot])=>({id,created_at:snapshot.created_at,message:snapshot.message,files:snapshot.files.length})):[];}
  async restore(id,expected){const head=await this.head();if(!head||head.id!==expected)fail('CONCURRENT_REPOSITORY_CHANGE');const history=await this.ancestors(head.id);if(!history.has(id))fail('RESTORE_REQUIRES_CURRENT_HISTORY');const past=history.get(id);return this.advance({...past,parents:[head.id],created_at:new Date().toISOString(),message:'Früheren Arbeitsstand wiederhergestellt: '+id.slice(0,12)},expected);}
  async mergePlan(remote){const local=await this.head();if(!local)fail('NO_LOCAL_REPOSITORY');const a=await this.ancestors(local.id),b=await this.ancestors(remote);let baseId;for(const id of a.keys())if(b.has(id)){baseId=id;break;}if(!baseId)fail('NO_COMMON_ANCESTOR');const base=asMap(a.get(baseId)),left=asMap(local.snapshot),right=asMap(b.get(remote)),files=[],conflicts=[];
    for(const path of [...new Set([...base.keys(),...left.keys(),...right.keys()])].sort()){const ancestor=base.get(path),l=left.get(path),r=right.get(path);let chosen;if(equal(l,r))chosen=l;else if(equal(l,ancestor))chosen=r;else if(equal(r,ancestor))chosen=l;else{conflicts.push({path,local:l??null,incoming:r??null});continue;}if(chosen)files.push(chosen);}
    return {local:local.id,remote,base:baseId,files,conflicts};
  }
  async merge(remote,resolutions={}){const plan=await this.mergePlan(remote),head=await this.head();if(head.id!==plan.local)fail('CONCURRENT_REPOSITORY_CHANGE');const files=plan.files.slice();for(const c of plan.conflicts){const side=resolutions[c.path];if(!['local','incoming'].includes(side))fail('MERGE_CONFLICT_REQUIRES_DECISION');const f=c[side];if(f)files.push(f);}
    const next=files.sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);const result=await this.advance({...head.snapshot,parents:[plan.local,remote],created_at:new Date().toISOString(),message:'Offline-Gerätestände zusammengeführt',files:next,git_tree_sha1:gitTree(next)},plan.local);await write(this.db,['refs'],tx=>tx.objectStore('refs').delete('incoming:'+remote));return result;}
  async verify(){const head=await this.head();if(!head)fail('NO_LOCAL_REPOSITORY');const history=await this.ancestors(head.id);for(const s of history.values())await this.checkContent(s);return {head:head.id,revisions:history.size,files:head.snapshot.files.length,bytes:checkSnapshot(head.snapshot),scope:'LOCAL_OFFLINE_WORKING_REPLICA',native_execution:false,github_write:false,native_review:false};}
}
