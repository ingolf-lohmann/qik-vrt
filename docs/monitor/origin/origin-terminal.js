// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Passive React readback, explicit file import/export, no executor or polling.
(async function () {
  'use strict';
  const messages = {
    FILE_START_UNSUPPORTED:'Eine lokale Datei startet diese Laufzeit nicht. Öffne den eingerichteten HTTPS-Origin und wähle dort den SQLite-Monolithen.',
    SECURE_ORIGIN_REQUIRED:'Dieser Origin ist unsicher. Öffne den eingerichteten HTTPS-Origin.',
    STORE_BYTES_DIGEST_MISMATCH:'Die Store-Bytes stimmen nicht mit dem gebundenen Image überein. Der bisherige Store bleibt erhalten.',
    STORE_IDENTITY_MISMATCH:'Die Store-Identität weicht ab. Der bisherige Store bleibt erhalten.',
    SHELL_OFFLINE_READINESS_FAILED:'Der Offline-Bootstrap ist noch nicht vollständig geprüft. Der bisherige Store bleibt erhalten.',
    ORIGIN_STORAGE_QUOTA:'Der Browser hat zu wenig Speicher freigegeben. Der bisherige Store bleibt erhalten.'
  };
  const explain = error => messages[error.message] || 'Readback angehalten ('+error.message+'). Der bisherige Store bleibt erhalten.';
  let adapter, failure='', shellReady=false;
  try {
    QikvrtOriginStore.checkOrigin();
    const response=await fetch('./ORIGIN_PROFILE.json',{cache:'no-store'});
    if(!response.ok)throw Error('BOUND_BOOTSTRAP_PROFILE_REQUIRED');
    const profile=await response.json();
    await navigator.serviceWorker.register('./service-worker.js',{scope:'./'});
    await Promise.race([(async()=>{
      await navigator.serviceWorker.ready;
      if(!navigator.serviceWorker.controller)await new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true}));
      await new Promise((resolve,reject)=>{
        const channel=new MessageChannel();const timer=setTimeout(()=>reject(Error('SHELL_OFFLINE_READINESS_FAILED')),5000);
        channel.port1.onmessage=event=>{clearTimeout(timer);channel.port1.close();event.data?.cache?.startsWith('qikvrt-origin-')?resolve():reject(Error('SHELL_OFFLINE_READINESS_FAILED'));};
        navigator.serviceWorker.controller.postMessage({type:'QIKVRT_ORIGIN_READY'},[channel.port2]);
      });
    })(),new Promise((_,reject)=>setTimeout(()=>reject(Error('SHELL_OFFLINE_READINESS_FAILED')),15000))]);
    shellReady=true;adapter=await QikvrtOriginStore.create(profile);
  } catch(error) {failure=explain(error);}
  const {React,ReactDOM}=globalThis.QikvrtReact, h=React.createElement;
  function App() {
    const [view,setView]=React.useState(null),[error,setError]=React.useState(failure),[online,setOnline]=React.useState(navigator.onLine),[busy,setBusy]=React.useState(false);
    const [persistent,setPersistent]=React.useState(false);
    async function read() {
      if(!adapter)return;
      try {setView(await adapter.read());setPersistent(await navigator.storage?.persisted?.()===true);setError('');}
      catch(e){setError(explain(e));setView(null);}
    }
    React.useEffect(()=>{
      read();const resume=()=>{setOnline(navigator.onLine);if(!document.hidden)read();};
      document.addEventListener('visibilitychange',resume);window.addEventListener('pageshow',resume);window.addEventListener('online',resume);window.addEventListener('offline',resume);
      return ()=>{document.removeEventListener('visibilitychange',resume);window.removeEventListener('pageshow',resume);window.removeEventListener('online',resume);window.removeEventListener('offline',resume);};
    },[]);
    async function importFile(event) {
      const file=event.target.files[0];if(!file)return;setBusy(true);
      try {
        if(file.size>64*1024*1024)throw Error('STORE_SIZE_UNSUPPORTED');
        const next=await adapter.accept(await file.arrayBuffer());setView(next);setPersistent(next.persistent_storage_granted);setError('');
      }catch(e){setError(explain(e));}finally{setBusy(false);event.target.value='';}
    }
    async function exportFile() {
      setBusy(true);try {
        const bytes=await adapter.exportBytes(),url=URL.createObjectURL(new Blob([bytes],{type:'application/vnd.sqlite3'}));
        const link=document.createElement('a');link.href=url;link.download='qikvrt-monolith.sqlite3';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      }catch(e){setError(explain(e));}finally{setBusy(false);}
    }
    return h('main',{id:'main'},h('h1',null,'Universales Raumzeit-Terminal'),
      h('p',null,online?'Browser-Origin erreichbar.':'Offline: der zuletzt geprüfte lokale Store wird gelesen.'),
      h('p',null,'Node und Client verwenden dasselbe SQLite-Image. Diese Ansicht startet keine nativen Befehle.'),
      error?h('p',{role:'alert'},error):null,
      h('label',null,'Gebundenen SQLite-Monolithen übernehmen ',h('input',{type:'file',accept:'.sqlite3,.sqlite,.db',onChange:importFile,disabled:!adapter||busy,'aria-label':'SQLite-Monolith importieren'})),
      h('button',{onClick:exportFile,disabled:!view||busy},'Originalbytes exportieren'),
      h('p',null,shellReady?'Offline-Bootstrap geprüft.':'Offline-Bootstrap offen.'),
      h('p',null,persistent?'Persistenter Origin-Speicher vom Browser gewährt.':'Origin-Speicher nach Browser-Richtlinie; Speicherfreigabe oder Eviktion kann ihn löschen.'),
      view?h(React.Fragment,null,h('dl',null,
        h('dt',null,'Store-Identität'),h('dd',{'data-testid':'ledger-id'},view.ledger_id),
        h('dt',null,'SQLite-Image SHA-256'),h('dd',{'data-testid':'store-digest'},view.file_sha256),
        h('dt',null,'Original-Ledger-Ereignisse'),h('dd',{'data-testid':'ledger-count'},String(view.ledger_records))),
        h('ol',null,view.events.slice(-50).map(event=>h('li',{key:event.id},h('code',null,event.id),' · ',event.message)))):
        h('p',null,'Noch kein gültiger Store übernommen.'),
      h('p',null,'Der Speicher ist an diesen Browser-Origin gebunden. Datei-Auswahl und Export erfolgen ausdrücklich durch dich. Android-/iOS-Abnahme bleibt offen.'));
  }
  ReactDOM.createRoot(document.getElementById('qikvrt-react')).render(h(App));
})();
