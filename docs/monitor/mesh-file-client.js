// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Local files and explicit REST synchronization; no Git, account or executor.
(() => {
  'use strict';
  const M=globalThis.QikvrtMeshFile;
  class Session {
    constructor(){this.blob=null;this.state=null;this.savedHead=null;this.handle=null;this.hold=null;this.io=[];this.writeMeasured=false;this.checkpoints=new Map();this.started=performance.now();}
    source(blob=this.blob){return M.blobSource(blob,(bytes,ms)=>this.io.push({at:performance.now(),kind:'read',bytes,ms}));}
    async open(blob,{handle=null}={}){
      const state=await M.scan(this.source(blob));
      if(this.state&&this.savedHead!==this.state.head&&state.repository_id!==this.state.repository_id)throw Error('ARBEITSKOPIE_ZUERST_SPEICHERN_UND_OEFFNEN');
      const pinned=this.checkpoints.get(state.repository_id);
      if(pinned&&!state.heads.has(pinned.head))throw Error('CONFIRMED_CHECKPOINT_MISSING');
      this.checkpoints.set(state.repository_id,state.checkpoint);
      this.blob=blob;this.state=state;this.savedHead=state.head;this.handle=handle;this.hold=null;return this.status();
    }
    async create(id){if(this.state&&this.savedHead!==this.state.head)throw Error('ARBEITSKOPIE_ZUERST_SPEICHERN_UND_OEFFNEN');
      const b=await M.create(id,{created_at:new Date().toISOString(),human_actor:'Ingolf Lohmann',client:'React Universal Terminal'});
      await this.open(new Blob([b]));this.savedHead=null;return this.status();}
    status(){
      const now=performance.now();this.io=this.io.filter(s=>s.at>=now-10000);const seconds=Math.max(.001,Math.min(10,(now-this.started)/1000));
      const stats=kind=>{const samples=this.io.filter(s=>s.kind===kind),known=kind==='read'||this.writeMeasured;
        return {operations_per_second:known?samples.length/seconds:null,bytes_per_second:known?samples.reduce((n,s)=>n+s.bytes,0)/seconds:null,
          mean_latency_ms:samples.length?samples.reduce((n,s)=>n+s.ms,0)/samples.length:null};};
      return {...(this.state?M.summary(this.state):{state:'CLOSED',entries:0,bytes:0}),cause:this.hold,
        state:this.hold?'HOLD':this.state?'VERIFIED':'CLOSED',pending_save:!!this.state&&this.savedHead!==this.state.head,
        access:this.handle?'DIRECT_FILE_HANDLE':'FILE_CHOOSER_AND_COPY',filesystem:null,
        metrics:{scope:'BROWSER_BLOB_READS_AND_FILE_STREAM_WRITES; NOT_DEVICE_IOPS',window_seconds:seconds,read:stats('read'),write:stats('write')},
        orchestration:{accept_writes:!!this.state&&!this.hold,decision:this.hold?'HOLD':this.state?'LOCAL_READY':'CLOSED'}};
    }
    async verify(){if(!this.blob)throw Error('DATEI_ZUERST_OEFFNEN');
      try{this.state=await M.scan(this.source(),this.state.checkpoint);return this.status();}
      catch(e){this.hold='FILE_SANITY_FAILED: '+e.message;throw e;}}
    async add(key,blob,options={}){
      if(!this.state||this.hold)throw Error(this.hold||'DATEI_ZUERST_OEFFNEN');
      const value=await M.addEntry(this.state,key,M.blobSource(blob),{...options,asBlob:true});
      const next=new Blob([this.blob,value.suffix]);const state=await M.scan(this.source(next),this.state.checkpoint);
      this.blob=next;this.state=state;this.checkpoints.set(state.repository_id,state.checkpoint);return this.status();
    }
    async entry(key){if(!this.state)throw Error('DATEI_ZUERST_OEFFNEN');return M.entryBlob(this.source(),this.state,key);}
    async saveDirect(){
      if(!this.handle||this.hold)throw Error(this.hold||'DIREKTZUGRIFF_NICHT_VERFUEGBAR');
      let writing=false;
      try{
        const before=await M.scan(this.source(await this.handle.getFile()));
        if(before.repository_id!==this.state.repository_id||before.head!==this.savedHead)throw Error('DATEI_EXTERN_GEAENDERT');
        const stream=await this.handle.createWritable({keepExistingData:false});writing=true;
        const began=performance.now();await stream.write(this.blob);this.writeMeasured=true;
        this.io.push({at:performance.now(),kind:'write',bytes:this.blob.size,ms:performance.now()-began});await stream.close();
        const file=await this.handle.getFile(),after=await M.scan(this.source(file),this.state.checkpoint);
        if(after.head!==this.state.head)throw Error('SCHREIB_READBACK_ABWEICHEND');
        this.blob=file;this.savedHead=after.head;return this.status();
      }catch(e){if(writing)this.hold='SCHREIBSTATUS_UNBEKANNT_DATEI_NEU_OEFFNEN';throw e;}
    }
    async sync(base,token,{fetcher=fetch}={}){
      if(!this.state||this.hold)throw Error(this.hold||'DATEI_ZUERST_OEFFNEN');
      const url=new URL(base||location.origin);if(!['https:','http:'].includes(url.protocol)||url.username||url.password||url.search||url.hash||url.pathname!=='/')throw Error('CLOUD_BASIS_URL_ERFORDERLICH');
      if(url.protocol==='http:'&&!['localhost','127.0.0.1','[::1]'].includes(url.hostname))throw Error('HTTPS_ERFORDERLICH');
      const get=async(path,init={})=>{
        const r=await fetcher(new URL(path,url),{...init,cache:'no-store',credentials:'omit',redirect:'error',headers:{Authorization:'Bearer '+token,...init.headers},signal:AbortSignal.timeout(20000)});
        if(!r.ok){const e=await r.json().catch(()=>({error:'HTTP '+r.status}));throw Error(e.error||'CLOUD_READBACK_FEHLT');}return r;
      };
      let remote=await (await get('/api/mesh-file/status')).json();
      if(remote.state!=='VERIFIED'||remote.repository_id!==this.state.repository_id)throw Error(remote.cause||'CLOUD_REPOSITORY_ABWEICHEND');
      if(remote.head===this.state.head)return {changed:false,state:'LOCAL_CLOUD_EQUAL_BY_VERIFIED_HEAD',remote};
      if(this.state.heads.has(remote.head)){
        let offset=this.state.heads.get(remote.head),expected=remote.head;
        const records=this.state.records.filter(r=>r.offset>=offset);
        for(let index=0;index<records.length;){
          let end=offset,next=index;
          while(next<records.length&&records[next].end-offset<=8*1024*1024){end=records[next++].end;}
          if(next===index)throw Error('CLOUD_BATCH_LIMIT');
          const head=records[next-1].digest;
          try{await get('/api/mesh-file/append',{method:'POST',headers:{'Content-Type':'application/octet-stream','If-Match':'"'+expected+'"'},body:this.blob.slice(offset,end)});}
          catch(e){
            // A timeout is UNKNOWN: read the authoritative head, never resend blindly.
            remote=await (await get('/api/mesh-file/status')).json();
            if(remote.repository_id!==this.state.repository_id||!this.state.heads.has(remote.head)||this.state.heads.get(remote.head)<end)throw Error('CLOUD_SCHREIBSTATUS_UNBEKANNT: '+e.message);
          }
          remote=await (await get('/api/mesh-file/status')).json();
          if(remote.repository_id!==this.state.repository_id||remote.state!=='VERIFIED'||remote.head!==head)throw Error('CLOUD_NACH_SCHREIBEN_GEAENDERT_READBACK_ERFORDERLICH');
          expected=head;offset=end;index=next;
        }
        return {changed:true,state:'CLOUD_APPEND_READBACK_VERIFIED',remote};
      }
      const response=await get('/api/mesh-file/bytes?after='+this.state.head);
      if(response.headers.get('x-qikvrt-base-head')!==this.state.head||response.headers.get('x-qikvrt-repository-id')!==this.state.repository_id)throw Error('CLOUD_PREFIX_ABWEICHEND');
      const size=Number(response.headers.get('content-length'));
      if(!Number.isSafeInteger(size)||size<0||size+this.blob.size>M.LIMITS.file_bytes)throw Error('CLOUD_DATEIGROESSE_ABWEICHEND');
      const tail=await response.blob();if(tail.size!==size)throw Error('CLOUD_UEBERTRAGUNG_UNVOLLSTAENDIG');
      const next=new Blob([this.blob,tail]),state=await M.scan(this.source(next),this.state.checkpoint);
      if('"'+state.head+'"'!==response.headers.get('etag'))throw Error('CLOUD_HEAD_ABWEICHEND');
      this.blob=next;this.state=state;this.checkpoints.set(state.repository_id,state.checkpoint);return {changed:true,state:'LOCAL_EXTENSION_VERIFIED_SAVE_REQUIRED',remote};
    }
  }
  function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
  globalThis.QikvrtMeshFiles={Session,download};
})();
