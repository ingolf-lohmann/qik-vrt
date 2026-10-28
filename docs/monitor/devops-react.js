// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
(() => {
  'use strict';
  const {React,ReactDOM}=globalThis.QikvrtReact, h=React.createElement, api=globalThis.QikVrtDevops, wire=globalThis.QikvrtDevopsWire;
  const labels={success:'erfolgreich',failure:'fehlgeschlagen',timed_out:'Zeitbudget erreicht',cancelled:'abgebrochen',skipped:'übersprungen',in_progress:'laufend',queued:'wartend',waiting:'wartend',blocked:'offen / gesperrt',unknown:'unbekannt',neutral:'neutral',action_required:'Aktion erforderlich'};
  const pill=value=>h('span',{className:'pill '+(Object.hasOwn(labels,value)?value:'unknown')},labels[value]||value||'unbekannt');
  const date=value=>value&&Number.isFinite(Date.parse(value))?new Date(value).toLocaleString('de-DE'):'unbekannt';
  const short=value=>value?String(value).slice(0,12):'offen';
  function Stage({title,state,detail,url}){return h('div',{className:'stage '+state},h('div',{className:'dot','aria-hidden':true}),h('div',null,h('strong',null,title),' ',pill(state),h('p',null,detail),url?.startsWith('https://github.com/')?h('a',{href:url,target:'_blank',rel:'noopener noreferrer'},'Originalbeleg ↗'):null));}
  class Boundary extends React.Component {
    constructor(props){super(props);this.state={failed:false};}
    static getDerivedStateFromError(){return {failed:true};}
    render(){return this.state.failed?h('main',null,h('h1',null,'QIK-VRT · Ansicht unterbrochen'),h('p',{role:'alert'},'Die Oberfläche konnte nicht vollständig dargestellt werden. Der Serverzustand wurde dadurch nicht verändert.'),h('a',{href:'/.well-known/effect-ack'},'Protokollfähigkeiten als JSON öffnen')):this.props.children;}
  }
  function NativeTerminal({native,onRefresh}){
    const [principal,setPrincipal]=React.useState('ingolf-lohmann'),[token,setToken]=React.useState(''),[text,setText]=React.useState('');
    const [prepared,setPrepared]=React.useState(null),[phase,setPhase]=React.useState('idle'),[receipt,setReceipt]=React.useState(null),[message,setMessage]=React.useState('');
    const busy=React.useRef(false),epoch=React.useRef(0);
    const ready=native?.state==='NATIVE_EAP_HTTP_READY';
    function invalidate(setter,value){epoch.current++;setter(value);setPrepared(null);setReceipt(null);setPhase('idle');setMessage('');}
    async function request(path,options={}){
      const response=await fetch(path,{cache:'no-store',signal:AbortSignal.timeout(12000),...options,headers:{Authorization:'Bearer '+token,'QIKVRT-Owner':principal,...options.headers}});
      if(!/^application\/json(?:;|$)/i.test(response.headers.get('content-type')||''))throw Error('Der Server stellt diesen EAP-Endpunkt noch nicht bereit.');
      const body=wire.parse(await response.text());
      if(!response.ok)throw Error(body.reason||body.error||'HTTP '+response.status);
      if(path==='/api/eap/effect'&&options.method==='POST')wire.compact(response.headers.get('effect-ack'),body);
      return body;
    }
    async function readContext(value){
      const record=await request(value.record_url),context=await request(value.context_url);
      if(wire.canonical(record)!==wire.canonical(context.chain?.at(-1)))throw Error('Record und unabhängiger Kontext stimmen nicht überein.');
      await wire.verify(context,{request:value.request,recordHash:value.recordHash,principal,expiresAt:value.expires_at});
      return {record,ledgerId:Object.values(context.evidence).find(x=>x.schema==='qikvrt_eap_subject_v1').ledger_id};
    }
    async function prepare(){
      if(busy.current)return;busy.current=true;const generation=epoch.current;
      setPhase('preparing');setMessage('Vorbereitung und unabhängige Record-Prüfung laufen.');setPrepared(null);setReceipt(null);
      try{
        const capability=await fetch('/api/eap/capabilities',{cache:'no-store',signal:AbortSignal.timeout(8000)});
        if(!capability.ok||!/^application\/json(?:;|$)/i.test(capability.headers.get('content-type')||''))throw Error('EAP-Fähigkeiten sind nicht erreichbar.');
        const support=wire.parse(await capability.text());
        if(support.message_type!=='effect-ack-capabilities'||!support.supported_versions?.includes(1))throw Error('Wire-Version 1 wurde nicht bestätigt.');
        const requestBody={schema:'qikvrt_owner_rest_input_v1',request_id:'eap-'+crypto.randomUUID(),subject:native.subject,input:{schema:'qikvrt_terminal_input_v1',text,audio:null,video:null}};
        const result=await request('/api/eap/effect',{method:'POST',headers:{'Content-Type':'application/json','Effect-Ack-Request':'v=1, mode=prepare'},body:wire.canonical(requestBody)});
        if(result.state!=='EFFECT_ACK_DONE'||!result.commit_token)throw Error('Keine Freigabe: '+result.state);
        if(!/^\/api\/eap\/records\/[a-f0-9]{64}$/.test(result.record_url)||result.context_url!==result.record_url+'/context'||!/^[a-f0-9]{64}$/.test(result.commit_token))throw Error('Ungültige Prepare-Bindung.');
        const value={...result,request:requestBody,recordHash:result.record.protocol_hash};
        const checked=await readContext(value);
        if(generation!==epoch.current)return;
        setPrepared({...value,ledgerId:checked.ledgerId});setPhase('prepared');setMessage('Record, Policy und Belege geprüft. Die Texteingabe ist vorbereitet.');
      }catch(error){if(generation===epoch.current){setPhase('idle');setMessage(error.message);}}
      finally{busy.current=false;}
    }
    async function commit(){
      if(!prepared||busy.current)return;busy.current=true;const generation=epoch.current;let attempted=false;setPhase('committing');
      try{
        await readContext(prepared);
        const hash=Uint8Array.from(prepared.recordHash.slice(7).match(/../g),x=>parseInt(x,16));
        const field='v=1, mode=commit, token=:'+btoa(prepared.commit_token)+':, hash=:'+btoa(String.fromCharCode(...hash))+':';
        attempted=true;
        const result=await request('/api/eap/effect',{method:'POST',headers:{'Content-Type':'application/json','Effect-Ack-Request':field},body:wire.canonical(prepared.request)});
        if(result.record.protocol_hash!==prepared.recordHash||result.independent_readback_verified!==true||!result.native_receipt?.durable_readback)throw Error('Native Rücklesung fehlt.');
        const observed=await request('/api/eap/receipts/'+encodeURIComponent(prepared.request.request_id));
        await wire.receipt(observed,{request:prepared.request,principal,ledgerId:prepared.ledgerId});
        if(wire.canonical(observed.durable_readback)!==wire.canonical(result.native_receipt.durable_readback))throw Error('Die separat gelesene Originalquittung widerspricht der Commit-Antwort.');
        if(generation!==epoch.current)return;
        setReceipt(observed);setPhase('committed');setMessage('Texteingabe im Originaljournal übernommen und unabhängig zurückgelesen.');
        onRefresh();
      }catch(error){if(generation===epoch.current){setPhase(attempted?'uncertain':'idle');if(!attempted)setPrepared(null);setMessage(attempted?'Ausgang offen: '+error.message+'. Zuerst Rücklesung ausführen.':'Vorbereitung erneut erforderlich: '+error.message);}}
      finally{busy.current=false;}
    }
    async function readback(){
      if(!prepared||busy.current)return;busy.current=true;const generation=epoch.current;
      try{const result=await request('/api/eap/receipts/'+encodeURIComponent(prepared.request.request_id));
        await wire.receipt(result,{request:prepared.request,principal,ledgerId:prepared.ledgerId});
        if(generation!==epoch.current)return;setReceipt(result);setPhase('committed');setMessage('Vorhandene Originalquittung unabhängig zurückgelesen.');
      }catch(error){if(generation===epoch.current)setMessage('Rücklesung offen: '+error.message);}
      finally{busy.current=false;}
    }
    const editingBlocked=['preparing','committing','uncertain'].includes(phase);
    return h('section',{className:'panel wide',id:'effect-ack','aria-labelledby':'native-title'},h('h2',{id:'native-title'},'Effect Acknowledgement · Native Eingabe'),
      h('p',{className:'compact'},'Vorbereiten → Record unabhängig prüfen → Eingabe übernehmen → Originaljournal zurücklesen.'),
      h('div',{className:'native-grid'},h('div',{className:'native-form'},
        h('div',{className:'credential-row'},h('label',null,'Principal',h('input',{value:principal,disabled:editingBlocked,onChange:e=>invalidate(setPrincipal,e.target.value),autoComplete:'off'})),
          h('label',null,'Vorhandener Owner-Zugang',h('input',{type:'password',value:token,disabled:editingBlocked,onChange:e=>invalidate(setToken,e.target.value),autoComplete:'off',placeholder:'Geschützter REST-Zugang'}))),
        h('label',null,'Texteingabe für das native Terminal',h('textarea',{value:text,maxLength:4096,disabled:editingBlocked,onChange:e=>invalidate(setText,e.target.value),placeholder:'Eine konkrete Nachricht für das Universal Terminal …'})),
        h('div',{className:'toolbar'},h('button',{className:'primary',onClick:prepare,disabled:!ready||!token||!principal||!text||phase!=='idle'},phase==='preparing'?'Prüfung läuft …':'Vorbereiten'),
          h('button',{onClick:commit,disabled:phase!=='prepared'},phase==='committing'?'Übernahme läuft …':'Eingabe übernehmen'),
          h('button',{onClick:readback,disabled:!prepared||['preparing','committing'].includes(phase)},'Originalquittung lesen'),
          h('button',{onClick:()=>{epoch.current++;setToken('');setPrepared(null);setReceipt(null);setPhase('idle');setMessage('Zugang aus dieser Ansicht entfernt.');}},'Abmelden')),
        h('p',{className:'compact'},'Der Zugang bleibt im Arbeitsspeicher dieser Ansicht. Er wird weder im Browser gespeichert noch in den Export aufgenommen.'),
        h('p',{role:'status','aria-live':'polite'},message)),
      h('div',{className:'native-status'},h('strong',null,ready?'Nativer EAP-Dienst erreichbar':'Nativer EAP-Dienst noch nicht bestätigt'),
        h('p',{className:'hash'},native?.subject?.head||native?.reason||'Ein frischer Server-Readback ist erforderlich.'),
        prepared?h(React.Fragment,null,h('p',null,'Geprüfter Record'),h('p',{className:'hash'},prepared.recordHash),h('p',{className:'compact'},'Gültig bis '+date(new Date(prepared.expires_at*1000).toISOString()))):null,
        receipt?h(React.Fragment,null,h('h3',null,'Native Quittung'),h('pre',null,JSON.stringify({request_id:receipt.request_id,event_id:receipt.durable_readback?.id,ledger_digest:receipt.durable_readback?.ledger_digest,independent_readback:receipt.independent_sqlite_readback,replayed:receipt.replayed},null,2))):h('p',{className:'compact'},'Noch keine native Übernahme für diesen Auftrag zurückgelesen.'),
        h('p',{className:'compact'},'Abnahmeumfang: dauerhafte lokale Texteingabe. Repository-, Host- und Domain-Abnahmen behalten ihre eigenen Belege.'))));
  }
  function App(){
    const [data,setData]=React.useState(()=>globalThis.QikvrtDevopsCapture),[native,setNative]=React.useState(null),[message,setMessage]=React.useState('Historische Momentaufnahme geladen.'),[transport,setTransport]=React.useState('Momentaufnahme');
    const [query,setQuery]=React.useState(''),[state,setState]=React.useState(''),[exact,setExact]=React.useState(true),[page,setPage]=React.useState(0),[loading,setLoading]=React.useState(false);
    const pending=React.useRef(false),alive=React.useRef(true),downloadURL=React.useRef(null),importInput=React.useRef(null);
    const model=api.project(data);
    const read=React.useCallback(async()=>{
      if(pending.current||!['http:','https:'].includes(location.protocol))return;
      pending.current=true;setLoading(true);
      try{
        const values=await Promise.allSettled(['/api/activity','/api/eap/state'].map(async path=>{const response=await fetch(path,{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!/^application\/json(?:;|$)/i.test(response.headers.get('content-type')||''))throw Error(path==='/api/eap/state'?'Der EAP-Dienst ist auf diesem Server noch nicht angebunden.':'Dieser Server stellt noch keine Workflow-Livedaten bereit.');const value=await response.json();if(!response.ok)throw Error(value.reason||value.error||'HTTP '+response.status);return value;}));
        if(!alive.current)return;
        if(values[0].status==='fulfilled'){api.project(values[0].value);setData(values[0].value);setMessage('Originalquelle gelesen.');}else setMessage('Workflow-Readback offen: '+values[0].reason.message);
        if(values[1].status==='fulfilled')setNative(values[1].value);else setNative({state:'unknown',reason:values[1].reason.message});
      }catch(error){if(alive.current)setMessage(error.message);}finally{pending.current=false;if(alive.current)setLoading(false);}
    },[]);
    React.useEffect(()=>{
      alive.current=true;read();let stream;
      if(['http:','https:'].includes(location.protocol)&&typeof EventSource!=='undefined'){
        stream=new EventSource('/api/stream');
        stream.onopen=()=>{if(alive.current)setTransport('Ereigniskanal verbunden');};
        stream.onerror=()=>{if(alive.current)setTransport('Ereigniskanal unterbrochen');};
        stream.addEventListener('snapshot',event=>{try{const value=JSON.parse(event.data);api.project(value);if(alive.current){setData(value);setMessage('Original-Ereignisstand übernommen.');}}catch(error){if(alive.current)setMessage('Stream-Readback offen: '+error.message);}});
      }
      const resume=()=>{if(!document.hidden)read();};document.addEventListener('visibilitychange',resume);window.addEventListener('online',resume);
      return()=>{alive.current=false;stream?.close();document.removeEventListener('visibilitychange',resume);window.removeEventListener('online',resume);if(downloadURL.current)URL.revokeObjectURL(downloadURL.current);};
    },[read]);
    const repo=model.primary,rows=model.rows;
    const filtered=rows.filter(r=>(!state||r.state===state)&&(!query||(r.name+' '+r.sha).toLowerCase().includes(query.toLowerCase()))&&(!exact||r.sha===model.repositories.find(x=>x.name===r.repo)?.head));
    const pages=Math.max(1,Math.ceil(filtered.length/15)),current=Math.min(page,pages-1),max=Math.max(1,...model.jobs.map(j=>j.duration||0));
    const merge=(data.pull_requests||[]).find(p=>p.repository===repo?.name&&p.merged===true&&p.merge_commit===repo?.head);
    async function exportRows(){try{const values=await api.exportRows(model);if(downloadURL.current)URL.revokeObjectURL(downloadURL.current);downloadURL.current=URL.createObjectURL(new Blob([values.map(x=>JSON.stringify(x)).join('\n')+'\n'],{type:'application/x-ndjson'}));const link=document.createElement('a');link.href=downloadURL.current;link.download='qikvrt-devops-workflow-observations.jsonl';link.click();setMessage(values.length+' Projektionszeilen exportiert.');}catch(error){setMessage(error.message);}}
    async function importFile(event){try{const file=event.target.files[0];if(!file)return;if(file.size>8*1024*1024)throw Error('Die Momentaufnahme überschreitet 8 MiB.');const value=JSON.parse(await file.text());api.project(value);setData(value);setPage(0);setMessage('Externe Momentaufnahme geöffnet; Herkunft bleibt gesondert zu prüfen.');}catch(error){setMessage(error.message);}}
    return h(React.Fragment,null,
      h('header',null,h('div',{className:'headerline'},h('div',{className:'eyebrow'},'QIK-VRT / Engineering evidence'),h('a',{href:'#effect-ack'},'Zum Effect-Ack-Terminal ↓')),h('h1',null,'Vom Commit zur Wirkung.'),h('p',{className:'sub'},'DevOps-Verläufe, Laufzeiten und überprüfbare native Eingaben. Jeder Zustand bleibt mit seinem Quellstand und Originalbeleg verbunden.'),h('span',{className:'tag'},'Ingolf Lohmann · QIK-VRT'),h('span',{className:'tag'},transport),h('span',{className:'tag'},'React · EAP Wire v1')),
      h('main',null,h('div',{className:'toolbar'},h('button',{className:'primary',onClick:read,disabled:loading},loading?'Quelle wird gelesen …':'Originalquelle lesen'),h('button',{onClick:exportRows},'ClickHouse-JSONL exportieren'),h('button',{onClick:()=>importInput.current.click()},'Momentaufnahme öffnen'),h('input',{ref:importInput,type:'file',accept:'.json,application/json',onChange:importFile,hidden:true}),h('span',{className:'compact'},'Erfasst: '+date(model.captured_at))),
        h('p',{role:'status','aria-live':'polite',className:'compact'},message),
        h('section',{className:'overview','aria-label':'Beobachteter Umfang'},...[
          ['ERFASSTE LÄUFE',rows.length,repo?.coverage_complete?'Vollständig erfasster API-Umfang':'Teilumfang · keine Gesamtaussage'],
          ['PLATTFORMSTATUS ERFOLGREICH',rows.filter(r=>r.state==='success').length,'Beobachtete Ausführungsergebnisse'],
          ['FEHLGESCHLAGEN / ABGEBROCHEN',rows.filter(r=>['failure','cancelled','timed_out'].includes(r.state)).length,'Fehler, Timeout oder Abbruch'],
          ['QUELLSTAND',short(repo?.head),repo?.source_fresh&&repo?.head_fresh?'Quelle beim Readback aktuell':'Historische / unvollständige Beobachtung']
        ].map(([label,value,detail])=>h('div',{className:'card',key:label},h('span',null,label),h('strong',{className:label==='QUELLSTAND'?'head-value':undefined},value),h('small',null,detail)))),
        h('div',{className:'grid'},h('section',{className:'panel'},h('h2',null,'Abnahmen bleiben getrennt'),h('div',{className:'flow'},
          h(Stage,{title:'01 · Quellstand',state:repo?.head_fresh?'success':'unknown',detail:repo?.head||'Quellstand fehlt'}),
          h(Stage,{title:'02 · CI auf genau diesem Head',state:repo?.ci_state||'unknown',detail:repo?.ci?'Lauf '+repo.ci.id+' · Versuch '+repo.ci.attempt:'Kein gebundener CI-Nachweis',url:repo?.ci?.url}),
          h(Stage,{title:'03 · Merge-Beobachtung',state:merge?'success':'unknown',detail:merge?'PR #'+merge.number+' · '+date(merge.merged_at):'Kein passender Merge-Nachweis in diesem Datenstand',url:merge?.url}),
          h(Stage,{title:'04 · Originalhost / Runtime',state:native?.state==='NATIVE_EAP_HTTP_READY'?'success':model.native.state,detail:native?.state==='NATIVE_EAP_HTTP_READY'?'Admittierter EAP-HTTP-Pfad zurückgelesen':native?.reason||model.native.reason}),
          h(Stage,{title:'05 · Exakte Domain',state:model.domain.state,detail:model.domain.http_status?'HTTP '+model.domain.http_status+' · '+date(model.domain.observed_at):'Kein Domain-Readback'}))),
          h('section',{className:'panel'},h('h2',null,'CI-Jobs · Zeit und Ergebnis'),model.jobs.length?model.jobs.map(j=>h('div',{className:'job',key:j.id},h('div',{className:'jobline'},h('span',null,j.name),h('span',null,pill(j.state),' ',j.duration===null?'—':j.duration+' s')),h('progress',{value:j.duration??0,max,'aria-label':j.name+' · '+(j.duration===null?'nicht ausgeführt':j.duration+' Sekunden')}))):h('p',{className:'empty'},'Keine Jobdetails für den exakten CI-/Head-Gegenstand geladen.'),h('p',{className:'caption'},'Übersprungene Jobs bleiben übersprungen. Ihre Null-Dauer belegt keine Ausführung.'))),
        h(NativeTerminal,{native,onRefresh:read}),
        h('section',{className:'panel wide'},h('div',{className:'toolbar'},h('h2',null,'Workflow-Verlauf'),h('input',{type:'search',value:query,onChange:e=>{setQuery(e.target.value);setPage(0);},placeholder:'Workflow oder Commit filtern','aria-label':'Workflow oder Commit filtern'}),h('select',{value:state,'aria-label':'Status filtern',onChange:e=>{setState(e.target.value);setPage(0);}},h('option',{value:''},'Alle Zustände'),...['success','failure','cancelled','skipped','in_progress','queued'].map(s=>h('option',{value:s,key:s},labels[s]))),h('label',null,h('input',{type:'checkbox',checked:exact,onChange:e=>{setExact(e.target.checked);setPage(0);}}),' aktueller Head')),
          h('div',{className:'table-scroll'},h('table',null,h('thead',null,h('tr',null,...['Workflow','Zustand','Auslöser','Commit / Versuch','Aktualisiert · UTC'].map(x=>h('th',{key:x,scope:'col'},x)))),h('tbody',null,filtered.slice(current*15,(current+1)*15).map(r=>h('tr',{key:r.repo+':'+r.id+':'+r.attempt},h('td',null,r.url?h('a',{href:r.url,target:'_blank',rel:'noopener noreferrer'},r.name):r.name,h('small',null,r.repo+' · Lauf '+r.id)),h('td',null,pill(r.state)),h('td',null,r.event),h('td',null,h('code',null,short(r.sha)),h('small',null,'Versuch '+r.attempt)),h('td',null,r.updated_at.replace('T',' '))))))),
          h('div',{className:'pagination'},h('button',{onClick:()=>setPage(current-1),disabled:current===0},'Zurück'),h('span',null,filtered.length+' Läufe · Seite '+(current+1)+' / '+pages),h('button',{onClick:()=>setPage(current+1),disabled:current>=pages-1},'Weiter'))),
        h('details',{className:'panel wide'},h('summary',null,'Protokoll und Nachweisgrenzen'),h('p',null,'Grundlage: draft-lohmann-qikvrt-effect-ack-03. Die HTTP-Prepare-/Commit-Abbildung folgt dem vorhandenen HTTP-Binding-Kandidaten. Abgenommen wird die dauerhafte lokale Terminaleingabe über das Originaljournal.'),h('p',null,'Der JSONL-Export bindet Projektionsbytes. Eine ClickHouse-Datenübernahme wird durch den Export nicht bestätigt.'),h('a',{href:'https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03',target:'_blank',rel:'noopener noreferrer'},'IETF-Originalfassung öffnen')),
        h('footer',{className:'footer'},'Anforderungen und Autorisierung: Ingolf Lohmann. Implementierung: OpenAI Codex. · Ereignisbasierter Readback, ohne Client-Polling.')));
  }
  ReactDOM.createRoot(document.getElementById('qikvrt-devops')).render(h(Boundary,null,h(App)));
})();
