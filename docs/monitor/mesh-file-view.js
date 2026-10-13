// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// File panel for the existing React Universal Terminal, including offline HTML.
(() => {
  'use strict';
  const {React}=globalThis.QikvrtReact,h=React.createElement,M=globalThis.QikvrtMeshFile;
  const number=n=>n==null?'unbekannt':new Intl.NumberFormat('de-DE',{maximumFractionDigits:1}).format(n);
  function Meter({label,value,max=1,unit=''}){
    const fraction=value==null?0:Math.max(0,Math.min(1,value/max));
    return h('div',{className:'file-meter'},h('span',{className:'meter-label'},label),
      h('div',{className:'meter-dial','aria-hidden':true},h('span',{className:'meter-needle',style:{transform:'rotate('+(-90+180*fraction)+'deg)'}})),
      h('output',null,number(value),value==null?'':' '+unit),h('small',null,value==null?'nicht messbar':'Skala 0–'+number(max)+' '+unit));
  }
  const fields=values=>h('dl',null,Object.entries(values).flatMap(([key,value])=>[h('dt',{key:key+'-k'},key),h('dd',{key},value)]));
  function FileTerminal(){
    const session=React.useRef(null);if(!session.current)session.current=new globalThis.QikvrtMeshFiles.Session();
    const [status,setStatus]=React.useState(session.current.status()),[message,setMessage]=React.useState(''),[busy,setBusy]=React.useState(false);
    const [key,setKey]=React.useState('/working-memory/note.txt'),[text,setText]=React.useState(''),[selected,setSelected]=React.useState('');
    const [endpoint,setEndpoint]=React.useState(location.protocol==='file:'?'':location.origin),[token,setToken]=React.useState(''),[cloud,setCloud]=React.useState(null);
    async function act(task){if(busy)return;setBusy(true);setMessage('');try{const value=await task();setStatus(session.current.status());if(typeof value==='string')setMessage(value);}catch(e){setMessage(e.message);setStatus(session.current.status());}finally{setBusy(false);}}
    const names=Array.from(session.current.state?.entries.keys()||[]).sort();
    const input=(label,props)=>h('label',null,label,h('input',props));
    return h('section',{className:'file-terminal','aria-labelledby':'file-terminal-title'},
      h('h2',{id:'file-terminal-title'},'Universal Terminal · SQLite-Export'),
      h('p',null,'SQLite ist der gemeinsame Speicher für Node und Client. Diese Ansicht liest einen daraus abgeleiteten QIKMESH1-Export. Änderungen erfolgen über das native Owner-REST-Terminal. Für die Browser-Persistenz die sichere Origin-Ansicht verwenden.'),
      h('div',{className:'file-actions'},input('Repository-Datei öffnen',{type:'file',accept:'.qmesh,application/octet-stream',disabled:busy,onChange:e=>{const f=e.target.files[0];if(f)act(()=>session.current.open(f));e.target.value='';}}),
        globalThis.showOpenFilePicker?h('button',{disabled:busy,onClick:()=>act(async()=>{const [handle]=await showOpenFilePicker({multiple:false});await session.current.open(await handle.getFile(),{handle});})},'Datei direkt öffnen'):null,
        h('button',{disabled:busy||!session.current.blob,onClick:()=>act(async()=>{globalThis.QikvrtMeshFiles.download(session.current.blob,'repository.qmesh');return 'Speicherkopie angefordert. Die gespeicherte Datei erneut öffnen, um den Schreibnachweis zu prüfen.';})},'Kopie speichern'),
        h('button',{disabled:busy||!session.current.blob,onClick:()=>act(()=>session.current.verify())},'Sanity-Check')),
      h('p',{role:'status','aria-live':'polite'},busy?'Prüfung läuft …':status.state+(status.pending_save?' · Änderungen noch in der Arbeitskopie; Datei speichern.':'')+(status.cause?' · '+status.cause:'')),
      message?h('p',{role:'alert',className:'error'},message):null,
      status.repository_id?fields({'Repository-ID':status.repository_id,'Head SHA-256':status.head,'Datensätze':number(status.records),'Einträge':number(status.entries),'Dateizugriff':status.access,'Freier Platz im gewählten Dateisystem':'unbekannt (Browser erteilt keinen statfs-Zugriff)'}):null,
      h('div',{className:'file-meters'},h(Meter,{label:'Dateigröße',value:status.bytes,max:M.LIMITS.file_bytes,unit:'Byte'}),
        h(Meter,{label:'Lesezugriffe',value:status.metrics?.read.operations_per_second,max:1000,unit:'/s'}),
        h(Meter,{label:'Lesedurchsatz',value:status.metrics?.read.bytes_per_second,max:100*1024*1024,unit:'Byte/s'}),
        h(Meter,{label:'Schreibzugriffe',value:status.metrics?.write.operations_per_second,max:1000,unit:'/s'})),
      h('p',{className:'sub'},'Messbereich: Browser-Dateizugriffe im letzten 10-Sekunden-Fenster. Laufwerkswerte bleiben unbekannt, wenn keine Messung vorliegt. Die Prüfsumme bestätigt Byte-Konsistenz; Herkunft und externe Wirkungen benötigen eigene Nachweise.'),
      h('fieldset',{disabled:busy||!session.current.state},h('legend',null,'Kanonische SQLite-Datei'),
        h('p',null,'Der Export enthält genau die ursprüngliche SQLite-Datei. Vor Wiederaufnahme müssen unabhängige Datei- und Carrier-Pins sowie der native Ledger geprüft werden.'),
        h('button',{onClick:()=>act(async()=>{const blob=await session.current.canonical();globalThis.QikvrtMeshFiles.download(blob,'repository.sqlite3');return 'SQLite-Kopie ausgegeben. Native Importprüfung vor der Wiederaufnahme erforderlich.';})},'SQLite-Datei ausgeben')),
      h('fieldset',{disabled:busy},h('legend',null,'Universal Transceiver · Cloud-Datei'),
        input('Cloud-Basis-URL (HTTPS)',{type:'url',value:endpoint,onChange:e=>setEndpoint(e.target.value),placeholder:'https://mesh.example/'}),
        input('Owner-Schlüssel (nur für diese Sitzung)',{type:'password',autoComplete:'off',value:token,onChange:e=>setToken(e.target.value)}),
        h('button',{disabled:!session.current.state||!token,onClick:()=>act(async()=>{const result=await session.current.sync(endpoint,token);setCloud(result.remote);return result.state;})},'Exportstand vergleichen')),
      cloud?h('div',null,h('h3',null,'Cloud-Readback'),fields({'Zustand':cloud.state,'Dateigröße':number(cloud.bytes)+' Byte','Messstand':cloud.metrics?.observed_at||'unbekannt','Freier Dateisystemplatz':cloud.filesystem?.available_bytes==null?'unbekannt':number(cloud.filesystem.available_bytes)+' Byte','Orchestrierung':cloud.orchestration?.decision||'unbekannt'}),
        h('div',{className:'file-meters'},h(Meter,{label:'Cloud-Lesen',value:cloud.metrics?.read.operations_per_second,max:1000,unit:'/s'}),h(Meter,{label:'Cloud-Schreiben',value:cloud.metrics?.write.operations_per_second,max:1000,unit:'/s'}),h(Meter,{label:'Cloud-Durchsatz',value:cloud.metrics?.write.bytes_per_second,max:100*1024*1024,unit:'Byte/s'}))):null);
  }
  globalThis.QikvrtMeshFileView=FileTerminal;
})();
