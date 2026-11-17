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
      await M.transportImage(this.source(blob),state);
      if(this.state&&this.savedHead!==this.state.head&&state.repository_id!==this.state.repository_id)throw Error('ARBEITSKOPIE_ZUERST_SPEICHERN_UND_OEFFNEN');
      const pinned=this.checkpoints.get(state.repository_id);
      if(pinned&&!state.heads.has(pinned.head))throw Error('CONFIRMED_CHECKPOINT_MISSING');
      this.checkpoints.set(state.repository_id,state.checkpoint);
      this.blob=blob;this.state=state;this.savedHead=state.head;this.handle=handle;this.hold=null;return this.status();
    }
    async create(){throw Error('SQLITE_IST_KANONISCH; QIKMESH_IST_NUR_EXPORT');}
    status(){
      const now=performance.now();this.io=this.io.filter(s=>s.at>=now-10000);const seconds=Math.max(.001,Math.min(10,(now-this.started)/1000));
      const stats=kind=>{const samples=this.io.filter(s=>s.kind===kind),known=kind==='read'||this.writeMeasured;
        return {operations_per_second:known?samples.length/seconds:null,bytes_per_second:known?samples.reduce((n,s)=>n+s.bytes,0)/seconds:null,
          mean_latency_ms:samples.length?samples.reduce((n,s)=>n+s.ms,0)/samples.length:null};};
      return {...(this.state?M.summary(this.state):{state:'CLOSED',entries:0,bytes:0}),cause:this.hold,
        state:this.hold?'HOLD':this.state?'VERIFIED':'CLOSED',pending_save:!!this.state&&this.savedHead!==this.state.head,
        access:this.handle?'DIRECT_FILE_HANDLE':'FILE_CHOOSER_AND_COPY',filesystem:null,
        metrics:{scope:'BROWSER_BLOB_READS_AND_FILE_STREAM_WRITES; NOT_DEVICE_IOPS',window_seconds:seconds,read:stats('read'),write:stats('write')},
        canonical_format:'SQLITE3_WITH_CARRIER_META_AND_EVENTS',transport_role:'DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY',
        orchestration:{accept_writes:false,decision:this.hold?'HOLD':this.state?'READ_ONLY_EXPORT':'CLOSED'}};
    }
    async verify(){if(!this.blob)throw Error('DATEI_ZUERST_OEFFNEN');
      try{this.state=await M.scan(this.source(),this.state.checkpoint);await M.transportImage(this.source(),this.state);return this.status();}
      catch(e){this.hold='FILE_SANITY_FAILED: '+e.message;throw e;}}
    async add(){throw Error('ABGELEITETER_SQLITE_EXPORT_IST_SCHREIBGESCHUETZT');}
    async entry(key){if(!this.state)throw Error('DATEI_ZUERST_OEFFNEN');return M.entryBlob(this.source(),this.state,key);}
    async canonical(){if(!this.state)throw Error('DATEI_ZUERST_OEFFNEN');return (await M.transportImage(this.source(),this.state)).blob;}
    async saveDirect(){throw Error('ABGELEITETER_SQLITE_EXPORT_IST_SCHREIBGESCHUETZT');}
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
      throw Error('KANONISCHER_SQLITE_STAND_ABWEICHEND; NEUER_GEBUNDENER_EXPORT_UND_UNABHAENGIGE_PINS_ERFORDERLICH');
    }
  }
  function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
  globalThis.QikvrtMeshFiles={Session,download};
})();
