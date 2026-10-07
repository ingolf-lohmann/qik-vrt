// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import {Repository} from './repository.js';
const {React,ReactDOM}=globalThis.QikvrtReact,h=React.createElement;
const messages={CONCURRENT_REPOSITORY_CHANGE:'Ein anderer Tab hat den Arbeitsstand verändert. Lade den aktuellen Stand erneut; dein Text bleibt hier erhalten.',ARCHIVE_CONTENT_DIGEST_MISMATCH:'Die übertragenen Inhaltsbytes stimmen nicht mit ihrer Prüfsumme überein. Der aktuelle Arbeitsstand bleibt erhalten.',INCOMPLETE_ARCHIVE:'Die Übertragung ist unvollständig. Der aktuelle Arbeitsstand bleibt erhalten.',REPOSITORY_IDENTITY_MISMATCH:'Diese Datei gehört zu einem anderen Repository. Sie ersetzt diesen Arbeitsraum nicht.',OFFLINE_STORAGE_QUOTA:'Der Browser hat nicht genügend lokalen Speicher freigegeben. Der letzte bestätigte Arbeitsstand bleibt erhalten.',SECURE_BROWSER_STORAGE_REQUIRED:'Öffne diesen Client über HTTPS. Für die erste Einrichtung werden ein sicherer Origin und Browser-Speicher benötigt.',MERGE_CONFLICT_REQUIRES_DECISION:'Wähle für jede widersprüchliche Datei den zu bewahrenden Stand.',NO_COMMON_ANCESTOR:'Die Gerätestände haben keinen gemeinsamen Vorfahren. Exportiere beide getrennt; es erfolgt kein Überschreiben.'};
const explain=e=>messages[e.message]||'Vorgang angehalten: '+e.message+'. Der zuletzt bestätigte Arbeitsstand bleibt erhalten.';
const bytes=n=>new Intl.NumberFormat('de',{maximumFractionDigits:1}).format(n/1048576)+' MiB';
function workerMessage(worker,message,timeout=10000){return new Promise((resolve,reject)=>{
  const channel=new MessageChannel(),timer=setTimeout(()=>{channel.port1.close();reject(Error('OFFLINE_SHELL_NOT_READY'));},timeout);
  channel.port1.onmessage=({data})=>{clearTimeout(timer);channel.port1.close();resolve(data);};
  try{worker.postMessage(message,[channel.port2]);}catch(e){clearTimeout(timer);channel.port1.close();reject(e);}
});}
async function shell(){
  if(!isSecureContext||!navigator.serviceWorker)throw Error('SECURE_BROWSER_STORAGE_REQUIRED');
  const registration=await navigator.serviceWorker.register('./service-worker.js',{scope:'./',updateViaCache:'none'});
  await navigator.serviceWorker.ready;
  if(!navigator.serviceWorker.controller)await Promise.race([new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true})),new Promise((_,reject)=>setTimeout(()=>reject(Error('OFFLINE_SHELL_NOT_READY')),15000))]);
  const receipt=await workerMessage(navigator.serviceWorker.controller,{type:'QIKVRT_OFFLINE_READY'});
  if(receipt?.ready!==true)throw Error('OFFLINE_SHELL_NOT_READY');
  return {registration,cache:receipt.cache};
}
function automaticUpdates(registration,pageCache,runtime,setLocked,setError){
  let disposed=false,timer,checking,lastCheck=0,draftWrite=Promise.resolve(),lastDraft;
  const listeners=[];
  const on=(target,event,handler)=>{target.addEventListener(event,handler);listeners.push(()=>target.removeEventListener(event,handler));};
  const lock=value=>{runtime.locked=value;setLocked(value);};
  const canCheckpoint=()=>runtime.ready&&!runtime.busy&&!runtime.composing&&Date.now()-runtime.changedAt>=1000;
  function persist(){
    const element=document.activeElement;
    const focus={testid:element?.getAttribute('data-testid'),start:element?.selectionStart,end:element?.selectionEnd,direction:element?.selectionDirection,scrollTop:element?.scrollTop,scroll:[scrollX,scrollY]};
    const state={...runtime.state,focus};
    // Queue snapshots in observation order; an older write cannot win a race.
    draftWrite=draftWrite.catch(()=>{}).then(()=>runtime.store.checkpointEditor(runtime.tab,state));
    return draftWrite;
  }
  async function checkpoint(){
    if(!canCheckpoint())return false;
    lock(true);
    try{
      await persist();
      return true;
    }catch(e){lock(false);setError(explain(e));return false;}
  }
  async function advance(){
    if(disposed||!runtime.ready||document.hidden)return;
    try{
      if(!runtime.locked&&canCheckpoint()&&lastDraft!==runtime.state){
        lastDraft=runtime.state;
        try{await persist();}catch(e){lastDraft=null;setError(explain(e));return;}
      }
      const receipt=await workerMessage(navigator.serviceWorker.controller,{type:'QIKVRT_OFFLINE_READY'});
      if(receipt.ready&&receipt.cache!==pageCache){
        if(runtime.locked||await checkpoint())location.reload();
        return;
      }
      if(registration.waiting&&canCheckpoint()&&!runtime.locked)
        await workerMessage(registration.waiting,{type:'QIKVRT_ACTIVATE_UPDATE'},15000);
    }catch{/* Offline or rejected update: retain the current verified client. */}
  }
  function schedule(){clearTimeout(timer);if(!disposed)timer=setTimeout(advance,1200);}
  runtime.schedule=schedule;
  function observe(worker){if(worker)on(worker,'statechange',()=>{if(worker.state==='installed')schedule();});}
  on(registration,'updatefound',()=>observe(registration.installing));observe(registration.installing);
  on(navigator.serviceWorker,'controllerchange',schedule);
  on(navigator.serviceWorker,'message',event=>{
    if(event.data?.type==='QIKVRT_PREPARE_UPDATE'){
      const port=event.ports[0];
      checkpoint().then(ready=>port?.postMessage({ready,cache:event.data.cache})).finally(()=>port?.close());
    }
    if(event.data?.type==='QIKVRT_UPDATE_RELEASE'){lock(false);}
  });
  async function contact(force=false){
    if(disposed||document.hidden||!navigator.onLine)return;
    schedule();
    if(checking||(!force&&Date.now()-lastCheck<30000))return;
    lastCheck=Date.now();
    checking=registration.update().catch(()=>{}).finally(()=>{checking=null;schedule();});
    await checking;
  }
  on(window,'online',()=>contact(true));
  on(window,'pageshow',()=>contact());on(window,'focus',()=>contact());
  on(document,'visibilitychange',()=>{if(!document.hidden)contact();});
  on(document,'input',()=>{runtime.changedAt=Date.now();schedule();});
  on(document,'compositionstart',()=>{runtime.composing=true;});
  on(document,'compositionend',()=>{runtime.composing=false;runtime.changedAt=Date.now();schedule();});
  // Prevent a new edit/action between durable checkpoint and controller switch.
  const prevent=event=>{if(runtime.locked){event.preventDefault();event.stopImmediatePropagation();}};
  document.addEventListener('beforeinput',prevent,true);document.addEventListener('click',prevent,true);
  contact();
  return ()=>{disposed=true;clearTimeout(timer);runtime.schedule=null;for(const off of listeners)off();document.removeEventListener('beforeinput',prevent,true);document.removeEventListener('click',prevent,true);};
}
function App(){const [store,setStore]=React.useState(null),[head,setHead]=React.useState(null),[error,setError]=React.useState(''),[notice,setNotice]=React.useState(''),[busy,setBusy]=React.useState(false),[ready,setReady]=React.useState(false),[online,setOnline]=React.useState(navigator.onLine),[persistent,setPersistent]=React.useState(false),[quota,setQuota]=React.useState(null),[path,setPath]=React.useState('personal/arbeitsnotiz.md'),[text,setText]=React.useState(''),[filter,setFilter]=React.useState(''),[incoming,setIncoming]=React.useState([]),[plan,setPlan]=React.useState(null),[choices,setChoices]=React.useState({}),[monitor,setMonitor]=React.useState(null),[report,setReport]=React.useState(null),[prepared,setPrepared]=React.useState(null),[history,setHistory]=React.useState([]),[locked,setLocked]=React.useState(false),[version,setVersion]=React.useState('');
  const runtimeRef=React.useRef({busy:false,locked:false,composing:false,changedAt:0,ready:false}),runtime=runtimeRef.current;
  React.useLayoutEffect(()=>{runtime.state={path,text,filter,plan,choices,prepared};runtime.ready=!!store&&ready;});
  async function refresh(adapter=store){if(!adapter)return;const next=await adapter.head();setHead(next);setHistory(await adapter.history());setIncoming(await adapter.incoming());setPersistent(await navigator.storage?.persisted?.()===true);setQuota(await navigator.storage?.estimate?.());if(next?.snapshot.files.some(f=>f.path==='monitor/observation.json')){const file=await adapter.file('monitor/observation.json');setMonitor(JSON.parse(await file.text()));}}
  React.useEffect(()=>{
    let live=true,adapter,stopUpdates;
    const resume=()=>{setOnline(navigator.onLine);if(!document.hidden&&adapter&&!runtime.locked)refresh(adapter).catch(e=>setError(explain(e)));};
    (async()=>{try{
      const {registration,cache}=await shell();adapter=await Repository.open();
      if(!live){adapter.close();return;}
      let tab;try{tab=sessionStorage.getItem('qikvrt-editor-tab-v1');}catch{}
      const draft=await adapter.editorDraft(tab);
      runtime.tab=crypto.randomUUID();try{sessionStorage.setItem('qikvrt-editor-tab-v1',runtime.tab);}catch{}
      runtime.store=adapter;
      if(draft?.schema==='qikvrt-editor-checkpoint/v1'){
        const d=draft.state;setPath(d.path);setText(d.text);setFilter(d.filter);setPlan(d.plan);setChoices(d.choices);setPrepared(d.prepared);
        setNotice('Bearbeitungszustand wiederhergestellt. Lokale Revisionen bleiben erhalten.');
        setTimeout(()=>{const f=d.focus,e=f?.testid&&document.querySelector('[data-testid="'+f.testid+'"]');if(e){e.focus();if(typeof f.start==='number')e.setSelectionRange(f.start,f.end,f.direction);e.scrollTop=f.scrollTop||0;}if(f?.scroll)scrollTo(...f.scroll);},0);
      }
      setStore(adapter);setReady(true);setVersion(cache);await refresh(adapter);
      if(live)stopUpdates=automaticUpdates(registration,cache,runtime,setLocked,setError);
    }catch(e){if(live)setError(explain(e));}})();
    window.addEventListener('online',resume);window.addEventListener('offline',resume);window.addEventListener('pageshow',resume);document.addEventListener('visibilitychange',resume);
    return()=>{live=false;stopUpdates?.();adapter?.close();window.removeEventListener('online',resume);window.removeEventListener('offline',resume);window.removeEventListener('pageshow',resume);document.removeEventListener('visibilitychange',resume);};
  },[]);
  async function run(action){
    if(runtime.locked||runtime.busy)return;
    runtime.busy=true;setBusy(true);setError('');setReport(null);
    try{await action();await refresh();}catch(e){setError(explain(e));}
    finally{runtime.busy=false;setBusy(false);runtime.schedule?.();}
  }
  async function download(blob,name){const file=new File([blob],name,{type:blob.type});if(navigator.canShare?.({files:[file]})){await navigator.share({files:[file],title:'QIK-VRT Repository-Stand'});return;}const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
  async function openFile(selected){await run(async()=>{const f=await store.file(selected.path);if(f.size>2097152)throw Error('TEXT_EDITOR_FILE_LIMIT_USE_EXPORT');const body=new TextDecoder('utf-8',{fatal:true}).decode(await f.arrayBuffer());setPath(selected.path);setText(body);setNotice('Datei geladen. Speichern erzeugt einen neuen lokalen Arbeitsstand.');});}
  async function importPack(event){const file=event.target.files[0];event.target.value='';if(file)await run(async()=>{const r=await store.importArchive(file);setNotice(r.state==='DIVERGENT_IMPORTED'?'Parallelstand übernommen. Der aktuelle Stand bleibt erhalten; führe die Gerätestände unten bewusst zusammen.':'Repository-Stand vollständig geprüft und lokal übernommen.');setPlan(null);});}
  async function importFiles(event){const files=[...event.target.files];event.target.value='';await run(async()=>{let current=await store.head();if(!current)current=await store.create();for(const f of files)current=await store.save(f.name,f,{expected:current.id,message:'Lokale Datei übernommen: '+f.name});setNotice('Dateien gespeichert und zurückgelesen.');});}
  async function observe(){await run(async()=>{if(!head)throw Error('NO_LOCAL_REPOSITORY');const repository='ingolf-lohmann/qik-vrt',observed_at=new Date().toISOString();const paths=[['main','branches/main'],['pulls','pulls?state=open&per_page=20'],['runs','actions/runs?per_page=30']];const sources=await Promise.all(paths.map(async([name,p])=>{try{const r=await fetch('https://api.github.com/repos/'+repository+'/'+p,{cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(20000),headers:{Accept:'application/vnd.github+json'}});if(!r.ok)return {name,state:'UNAVAILABLE',http_status:r.status};return {name,state:'OBSERVED',http_status:r.status,value:await r.json()};}catch(e){return {name,state:'UNAVAILABLE',http_status:null,error:e.name};}}));const data={schema:'qikvrt-offline-monitor-observation/v1',repository,observed_at,sources,native_review_or_merge_inferred:false};await store.save('monitor/observation.json',new Blob([JSON.stringify(data,null,2)]),{expected:head.id,message:'Explizite Repository-Beobachtung gespeichert'});setNotice('Beobachtung gespeichert. Offline wird dieser Zeitpunkt angezeigt; es gibt keinen Polling-Timer.');});}
  const disabled=busy||locked||!store||!ready,files=(head?.snapshot.files||[]).filter(f=>f.path.toLowerCase().includes(filter.toLowerCase()));
  return h(React.Fragment,null,h('header',null,h('p',{className:'eyebrow'},'QIK-VRT · Universales Raumzeit-Terminal'),h('h1',null,'Deine Arbeit bleibt anschlussfähig.'),h('p',null,'Dateien, Entscheidungen und Repository-Kontext lokal bearbeiten — auch ohne Netz.'),h('p',{className:'status','data-testid':'connection'},online?'Browser meldet Netz · Erreichbarkeit erst beim Abruf geprüft.':'Browser meldet offline · lokale Arbeitskopie und gespeicherte Beobachtungen.'),h('div',{className:'actions'},h('button',{className:'primary',disabled:disabled||!!head,onClick:()=>run(async()=>{await store.create();setNotice('Lokale Arbeitskopie angelegt.');})},'Arbeitskopie anlegen'),h('button',{disabled:disabled||!head,onClick:()=>run(async()=>{const blob=await store.exportArchive(),meta=JSON.parse((await blob.slice(0,2048).text()).split('\n')[0]);setPrepared(new File([blob],'qikvrt-'+meta.head.slice(0,12)+'.qikvrt',{type:blob.type}));setNotice('Export vollständig geprüft und vorbereitet. Tippe jetzt „Fertigen Stand teilen“, um ihn in Dateien zu sichern oder auf dein anderes iPhone zu übertragen.');})},'Sicherung vorbereiten'),prepared?h('button',{className:'primary',disabled,onClick:()=>run(async()=>{await download(prepared,prepared.name);setNotice('Teilen-Ansicht geöffnet. Bestätige die Datei am gewählten Ziel und importiere sie auf dem zweiten iPhone.');})},'Fertigen Stand teilen'):null),prepared?h('p',{className:'muted'},'Vorbereitete Sicherung: '+prepared.name):null,h('label',null,'Repository-Stand vom anderen iPhone übernehmen',h('input',{'data-testid':'archive-import',type:'file',accept:'.qikvrt,.qikvrt.gz,application/x-qikvrt-repository',disabled,onChange:importPack}))),
    h('main',{id:'main'},error?h('p',{className:'alert',role:'alert'},error):null,notice?h('p',{role:'status'},notice):null,
      h('div',{className:'grid'},h('section',{className:'card'},h('h2',null,'Dein Repository'),head?h(React.Fragment,null,h('p',null,head.snapshot.repository_id),h('p',null,head.snapshot.files.length+' Dateien · '+bytes(head.snapshot.files.reduce((n,f)=>n+f.bytes,0))),h('label',null,'Datei suchen',h('input',{'data-testid':'editor-filter',disabled,value:filter,onChange:e=>setFilter(e.target.value),placeholder:'Pfad oder Name'})),h('ul',{className:'files'},files.slice(0,200).map(f=>h('li',{key:f.path},h('button',{disabled,onClick:()=>openFile(f)},f.path,h('span',null,f.bytes+' Bytes · '+f.mode))))),files.length>200?h('p',{className:'muted'},'Weitere Dateien durch die Suche eingrenzen.'):null):h('p',null,'Lege eine Arbeitskopie an oder importiere den vorbereiteten Repository-Stand.'),h('label',null,'Weitere Dateien lokal übernehmen',h('input',{type:'file',multiple:true,disabled,onChange:importFiles}))),
      h('section',{className:'card'},h('h2',null,'Arbeitsstand bearbeiten'),h('label',null,'Repository-Pfad',h('input',{'data-testid':'editor-path',value:path,onChange:e=>setPath(e.target.value),disabled})),h('label',null,'Text / Entscheidung / Quellcode',h('textarea',{'data-testid':'editor-text',value:text,onChange:e=>setText(e.target.value),disabled,spellCheck:false})),h('div',{className:'actions'},h('button',{'data-testid':'save',className:'primary',disabled:disabled||!head,onClick:()=>run(async()=>{await store.save(path,new Blob([text],{type:'text/plain;charset=utf-8'}),{expected:head.id});setNotice('Neuer Arbeitsstand gespeichert und zurückgelesen.');})},'Neuen Stand speichern'),h('button',{disabled:disabled||!head?.snapshot.files.some(f=>f.path===path),onClick:()=>run(async()=>{await download(await store.file(path),path.split('/').at(-1));})},'Datei exportieren'),h('button',{disabled:disabled||!head?.snapshot.files.some(f=>f.path===path),onClick:()=>run(async()=>{await store.remove(path,head.id);setNotice('Datei im neuen Stand entfernt; frühere Versionen bleiben in der Historie.');})},'Datei entfernen')))),
      history.length>1?h('section',{className:'card'},h('h2',null,'Frühere Arbeitsstände'),h('p',null,'Wiederherstellen erzeugt eine neue Revision und bewahrt die bisherige Historie.'),h('ul',{className:'files'},history.slice(1,21).map(revision=>h('li',{key:revision.id},h('button',{disabled,onClick:()=>run(async()=>{await store.restore(revision.id,head.id);setNotice('Früherer Stand als neue Revision wiederhergestellt.');})},revision.message+' · '+revision.id.slice(0,12)))))):null,
      incoming.length?h('section',{className:'card'},h('h2',null,'Zwei Gerätestände zusammenführen'),incoming.map(id=>h('button',{key:id,disabled,onClick:()=>run(async()=>{setPlan(await store.mergePlan(id));setChoices({});})},'Parallelstand '+id.slice(0,12)+' vergleichen')),plan?h(React.Fragment,null,h('p',null,plan.conflicts.length+' widersprüchliche Dateien. Andere Änderungen werden gemeinsam bewahrt.'),plan.conflicts.map(c=>h('label',{key:c.path},c.path,h('select',{disabled,value:choices[c.path]||'',onChange:e=>setChoices({...choices,[c.path]:e.target.value})},h('option',{value:''},'Bewusst entscheiden …'),h('option',{value:'local'},'Aktuellen Stand behalten'+(c.local?'':' (Datei entfernt)')),h('option',{value:'incoming'},'Übertragenen Stand behalten'+(c.incoming?'':' (Datei entfernt)'))))),h('button',{disabled:disabled||plan.conflicts.some(c=>!choices[c.path]),onClick:()=>run(async()=>{await store.merge(plan.remote,choices);setPlan(null);setNotice('Beide Gerätestände historienerhaltend zusammengeführt. Exportiere diesen Stand und übertrage ihn zurück.');})},'Gemeinsamen Stand speichern')):null):null,
      h('section',{className:'card'},h('h2',null,'Repository-Monitor'),h('p',null,'Gespeicherte Beobachtung, kein Offline-Live-Status und keine Freigabe- oder Merge-Behauptung.'),h('button',{disabled:disabled||!head||!online,onClick:observe},'GitHub einmal beobachten'),monitor?h(React.Fragment,null,h('p',null,'Beobachtet am '+new Date(monitor.observed_at).toLocaleString('de')),monitor.sources.map(s=>h('p',{key:s.name},s.name+' · '+s.state+' · HTTP '+(s.http_status??'nicht beobachtet'))),h('details',null,h('summary',null,'Originale Beobachtung ansehen'),h('pre',null,JSON.stringify(monitor,null,2)))):h('p',{className:'muted'},'Noch keine Repository-Beobachtung gespeichert. Lokale Arbeit ist davon unabhängig.')),
      h('section',{className:'card'},h('h2',null,'Offline-Bereitschaft und Sicherung'),h('p',{'data-testid':'client-version',className:'muted'},'Clientversion '+version.slice(-12)),h('p',{'data-testid':'shell-ready',className:ready?'success':''},ready?'Client vollständig im Offline-Cache geprüft.':'Offline-Client noch nicht vollständig eingerichtet.'),h('p',null,persistent?'Browser gewährt persistenten Speicher.':'Speicherung nach Browser-Richtlinie. Sichere wichtige Stände zusätzlich als Datei.'),quota?h('p',null,'Browser-Speicher: '+bytes(quota.usage||0)+' genutzt, Kontingent '+bytes(quota.quota||0)):null,h('div',{className:'actions'},h('button',{disabled,onClick:()=>run(async()=>{const granted=await navigator.storage?.persist?.();setNotice(granted?'Persistenter Browser-Speicher gewährt.':'Der Browser hat persistenten Speicher nicht gewährt. Datei-Export bleibt verfügbar.');})},'Persistenten Speicher anfordern'),h('button',{'data-testid':'verify',disabled:disabled||!head,onClick:()=>run(async()=>{setReport(await store.verify());setNotice('Historie, Inhaltsblöcke und Git-Objektbytes frisch zurückgelesen.');})},'Gespeicherten Stand prüfen')),report?h('pre',{'data-testid':'verification'},JSON.stringify(report,null,2)):null,head?h('details',null,h('summary',null,'Bindung und Quellen'),h('p',{className:'break','data-testid':'snapshot-head'},'Lokaler Stand: '+head.id),h('p',{className:'break'},'Git-Arbeitsbaum: '+head.snapshot.git_tree_sha1),h('pre',null,JSON.stringify(head.snapshot.source,null,2)),h('p',null,'Quellbindung aus dem importierten Paket; keine neue GitHub-Beobachtung. Lokale Versionen sind Arbeitskopien, keine nativen GitHub-Commits oder Reviews.')):null)),
    h('footer',null,h('details',null,h('summary',null,'Auf beiden iPhones verwenden'),h('ol',null,h('li',null,'Diesen HTTPS-Einstieg auf jedem iPhone in Safari öffnen, „Teilen“ → „Zum Home-Bildschirm“ → „Als Web-App öffnen“.'),h('li',null,'Die installierte App öffnen und den vorbereiteten .qikvrt- oder .qikvrt.gz-Stand über die Dateien-App importieren. Safari und Home-Screen-App besitzen getrennten lokalen Speicher.'),h('li',null,'„Client vollständig im Offline-Cache geprüft“ abwarten. Danach im Flugmodus öffnen, bearbeiten, speichern und erneut öffnen.'),h('li',null,'„Sicherung vorbereiten“ → „Fertigen Stand teilen“: Datei in „Dateien“ sichern oder per AirDrop übertragen; in der App auf dem zweiten iPhone importieren. Für widersprüchliche Änderungen den Vergleich verwenden.')),h('p',null,'Die erste Einrichtung braucht HTTPS. Eine HTML-Datei in der Dateien-Vorschau installiert keine Offline-Web-App. Gerätespeicherfreigabe kann Browser-Daten löschen; der Datei-Export bewahrt die überprüfbare Übertragung.')),h('p',null,'Ingolf Lohmann · Product Owner und Code Owner. Clientaktualisierung automatisch bei Online-Kontakt. Repository-Beobachtung auf Anfrage; keine native Befehlsausführung.')));
}
ReactDOM.createRoot(document.getElementById('qikvrt-react')).render(h(App));
