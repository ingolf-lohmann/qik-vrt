// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// This client consumes the existing monitor replica; it creates no executor.
(() => {
  'use strict';
  const {React, ReactDOM} = globalThis.QikvrtReact;
  const h = React.createElement;
  const short = value => value ? String(value).slice(0, 12) : 'offen';
  const date = value => value ? new Date(value).toLocaleString('de-DE') : 'noch nicht beobachtet';
  const fields = values => h('dl', null, Object.entries(values).flatMap(([key, value]) => [
    h('dt', {key:key+'-key'}, key), h('dd', {key}, typeof value === 'string' ? value : JSON.stringify(value))]));
  const componentEvidence = 'https://github.com/ingolf-lohmann/qik-vrt/actions/runs/37444676087';
  function PersonalEntry() {
    const [filesOpen, setFilesOpen] = React.useState(false);
    const [onboardingOpen, setOnboardingOpen] = React.useState(false);
    const [name, setName] = React.useState('');
    const [origin, setOrigin] = React.useState('LOCAL_ONLY');
    const [originUrl, setOriginUrl] = React.useState('');
    const [retention, setRetention] = React.useState('METADATA_ONLY');
    const [preview, setPreview] = React.useState(null);
    const [error, setError] = React.useState('');
    const edit = setter => event => {setter(event.target.value); setPreview(null); setError('');};
    function prepare(event) {
      event.preventDefault();
      setPreview(null); setError('');
      if (!name.trim()) {setError('Bitte eine Kennung für deine Beiträge angeben. Ein Pseudonym genügt.'); return;}
      if (origin !== 'LOCAL_ONLY') {
        try {
          const url = new URL(originUrl);
          if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) throw Error();
        } catch {setError('Bitte eine HTTPS-Zieladresse ohne Zugangsdaten, Abfrage oder Fragment angeben.'); return;}
      }
      setPreview({'Beitragskennung':name.trim(), 'Persönlicher Ursprung':origin === 'LOCAL_ONLY' ? 'Nur lokal' : origin + ': ' + originUrl,
        'Nachweistiefe':retention, 'Einrichtung':'offen · Vorschau im Arbeitsspeicher dieser Seite'});
    }
    return h(React.Fragment, null,
      h('section', {className:'entry-hero', 'aria-labelledby':'entry-title'},
        h('p', {className:'sub'}, 'RaumzeitTerminal · Universales Raumzeit-Terminal'),
        h('h1', {id:'entry-title'}, 'Deine Arbeit mit Kontext fortsetzen'),
        h('p', {className:'entry-lead'}, 'Der erste Produktfall ist ein persönlicher Browserassistent: Einen unterbrochenen Arbeitsauftrag mit Quellen, Entscheidungen und Freigaben über mehrere Sitzungen weiterführen.'),
        h('p', null, 'Gedacht für Menschen, die recherchieren, Software entwickeln oder länger an Projekten arbeiten.'),
        h('div', {className:'entry-status-grid'},
          h('article', null, h('h2', null, 'Technisch belegt · begrenzter Testumfang'),
            h('p', null, 'Komponententests dokumentieren SQLite-Persistenz, Neustart und Replay ohne doppelten Effekt sowie Offline-Lesen im Desktop-Browser.'),
            h('a', {href:componentEvidence}, 'Teststand #474 vom 6. Oktober 2026')),
          h('article', null, h('h2', null, 'Produktziel · noch offen'),
            h('p', null, 'Persönliche Anmeldung, automatische Kontextfortsetzung, öffentlicher HTTPS-Betrieb und reale Mobilgeräte sind noch nicht gemeinsam abgenommen. Ein messbarer Anwendervergleich fehlt.'))),
        h('div', {className:'entry-actions'},
          h('a', {className:'primary-action', href:'#persoenlicher-kontext', onClick:()=>setFilesOpen(true)}, 'Kontextdatei öffnen'),
          h('a', {className:'secondary-action', href:'#persoenlicher-einstieg', onClick:()=>setOnboardingOpen(true)}, 'Persönlichen Einstieg vorbereiten')),
        h('p', {className:'sub entry-boundary'}, 'Heute kannst du einen lokalen Export prüfen und die Einrichtung vorbereiten. Das Terminal bleibt passiv; Ausführung, dauerhafte Speicherung und Wirkungsbestätigung gehören zur gebundenen Laufzeit.')),
      h('details', {id:'persoenlicher-kontext', className:'entry-panel', open:filesOpen, onToggle:event=>setFilesOpen(event.currentTarget.open)},
        h('summary', null, 'Vorhandene Kontextdatei öffnen und prüfen'),
        h('p', null, 'Wähle deinen vorhandenen lokalen SQLite-Export. Er wird in dieser Ansicht gelesen; private Inhalte werden dabei nicht an den öffentlichen Monitor übertragen. Die Dateiöffnung bestätigt weder deine Identität noch eine Arbeitsfortsetzung.'),
        h(globalThis.QikvrtMeshFileView)),
      h('details', {id:'persoenlicher-einstieg', className:'entry-panel', open:onboardingOpen, onToggle:event=>setOnboardingOpen(event.currentTarget.open)},
        h('summary', null, 'Neuen persönlichen Einstieg vorbereiten'),
        h('p', {id:'onboarding-boundary'}, 'Diese drei Angaben bereiten nur die Einrichtung vor. Bereits gebundene Antworten sollen bei der späteren Wiederaufnahme übernommen werden. Hier wird kein Konto oder Speicher angelegt; die Vorschau geht beim Schließen oder Neuladen verloren.'),
        h('form', {onSubmit:prepare, 'aria-describedby':'onboarding-boundary'},
          h('label', null, '1. Kennung für deine Beiträge (Name oder Pseudonym)',
            h('input', {value:name, onChange:edit(setName), required:true, maxLength:160, autoComplete:'off'})),
          h('fieldset', null, h('legend', null, '2. Persönlicher Ursprung'),
            h('label', null, 'Zielkonfiguration', h('select', {value:origin, onChange:edit(setOrigin)},
              h('option', {value:'LOCAL_ONLY'}, 'Nur lokal (Voreinstellung)'),
              h('option', {value:'PRIVATE_ORIGIN'}, 'Eigene private Zieladresse'),
              h('option', {value:'PUBLIC_ORIGIN'}, 'Eigene öffentliche Zieladresse'))),
            origin === 'LOCAL_ONLY' ? null : h('label', null, 'Eigene HTTPS-Zieladresse',
              h('input', {type:'url', value:originUrl, onChange:edit(setOriginUrl), required:true, autoComplete:'off'})),
            h('p', {className:'sub'}, 'Ein entferntes Ziel benötigt Verfügungsrecht und eine gesonderte Freigabe. Die Vorschau stellt keine Verbindung her.')),
          h('label', null, '3. Nachweistiefe', h('select', {value:retention, onChange:edit(setRetention)},
            h('option', {value:'METADATA_ONLY'}, 'Nur Metadaten (Voreinstellung)'),
            h('option', {value:'REDACTED_EVIDENCE'}, 'Gekürzte Nachweise'),
            h('option', {value:'FULL_TRANSCRIPT'}, 'Vollständiger Verlauf (Rechteprüfung erforderlich)'))),
          h('button', {type:'submit'}, 'Angaben als Vorschau prüfen')),
        error ? h('p', {role:'alert', className:'error'}, error) : null,
        preview ? h('div', {role:'status'}, h('h3', null, 'Einrichtungsvorschau'), fields(preview),
          h('p', null, 'Noch nicht an eine Laufzeit übergeben oder dauerhaft gespeichert. Rechte, Einwilligungen und Authentifizierung bleiben zu prüfen. Geheimnisse gehören in keinen Nachweismodus.')) : null),
      h('section', {id:'nachweise', 'aria-labelledby':'evidence-title'},
        h('h2', {id:'evidence-title'}, 'Leistung, Verantwortung und Kosten'),
        h('details', null, h('summary', null, 'Sechs konkrete Fragen zum Produkt'),
          h('ol', {className:'product-answers'},
            h('li', null, h('h3', null, 'Welchen Arbeitsauftrag löst es?'),
              h('p', null, 'Produktziel: Eine Recherche oder Entwicklungsaufgabe am nächsten Tag am letzten nachvollziehbaren Stand fortsetzen. Quellen, offene Fragen, Entscheidungen und Freigaben sollen erhalten bleiben. Außenwirkungen sollen nur im autorisierten Laufzeitpfad erfolgen.')),
            h('li', null, h('h3', null, 'Wer nutzt und kauft es?'),
              h('p', null, 'Die genannten Zielgruppen sind mögliche Anwender. Eine tatsächliche Kunden- oder Käuferbasis ist in diesem Nachweisstand nicht belegt.')),
            h('li', null, h('h3', null, 'Wer verantwortet Updates?'),
              h('p', null, 'Product- und Code-Verantwortung: Ingolf Lohmann. Technische Umsetzung: OpenAI Codex. Änderungen werden versioniert und geprüft; verbindliche Update-Intervalle und Supportzusagen sind noch offen.')),
            h('li', null, h('h3', null, 'Was kostet es später?'),
              h('p', null, 'Es gibt noch keine verbindliche Preisliste. Kommerzielle Nutzung erfordert eine separate schriftliche Lizenz. Künftige Betriebs-, Modell- und Supportkosten sind noch nicht verbindlich festgelegt.')),
            h('li', null, h('h3', null, 'Was leistet der heutige Stand genau?'),
              h('p', null, 'Diese Ansicht liest lokale Exporte und vorhandene technische Readbacks; sie zeigt eine unverbindliche Einrichtungsvorschau. Die verlinkten Komponententests betreffen jeweils ihren exakten Quellstand. Sie belegen keine vollständige Browserassistenten- oder Produktabnahme.'),
              h('a', {href:componentEvidence}, 'Komponentenbelege und Geltungsgrenzen'), ' · ', h('a', {href:'/mesh'}, 'Mesh-Monitor öffnen')),
            h('li', null, h('h3', null, 'Welcher Vorteil ist messbar?'),
              h('p', null, 'Erwartet werden weniger wiederholte Kontextangaben und eine nachvollziehbare Fortsetzung. Ein Vorteil für Anwender ist noch nicht gemessen. Geplant ist ein Vergleich derselben unterbrochenen Aufgabe: Zeit bis zur Fortsetzung, erneut nötige Angaben und korrekt bestätigte Wirkungen ohne Duplikat.')))),
        h('p', {className:'sub'}, 'Ein verbundener Stream, eine erfolgreiche CI oder eine gelesene Datei ersetzen keine bestätigte Außenwirkung (EFFECT_ACK).')));
  }
  function App() {
    const [data, setData] = React.useState(null);
    const [runtime, setRuntime] = React.useState(null);
    const [native, setNative] = React.useState(null);
    const [transport, setTransport] = React.useState('verbinde');
    const [error, setError] = React.useState('');
    const [tick, setTick] = React.useState(Date.now());
    const refresh = React.useRef(() => {});
    React.useEffect(() => {
      if(document.documentElement.dataset.qikvrtOffline==='true'){setTransport('lokale Datei');return;}
      const replica = globalThis.QikvrtReplica.create({version:document.documentElement.dataset.qikvrtMonitorVersion});
      let alive = true, stream, pending = false;
      async function get(path) {
        const response = await fetch(path, {cache:'no-store', signal:AbortSignal.timeout(8000)});
        if (!response.ok) throw Error(path + ': HTTP ' + response.status);
        return response.json();
      }
      async function apply(value) {
        const result = await replica.accept(value);
        if (!alive) return;
        if (result.accepted) {setData(result.snapshot); setError('');}
        else if (!result.duplicate) throw Error(result.reason);
      }
      async function read() {
        if (pending) return;
        pending = true;
        try {
          const results = await Promise.allSettled([get('/api/activity'),get('/api/runtime'),get('/api/terminal')]);
          if (!alive) return;
          if (results[0].status === 'fulfilled') await apply(results[0].value);
          else throw results[0].reason;
          if (results[1].status === 'fulfilled') setRuntime(results[1].value);
          if (results[2].status === 'fulfilled') setNative(results[2].value);
          const failed = results.slice(1).filter(result => result.status === 'rejected');
          if (failed.length) setError(failed.map(result => result.reason.message).join(' · '));
        } catch (e) {if (alive) setError(e.message);} finally {pending = false;}
      }
      function connect() {
        stream?.close();
        stream = new EventSource('/api/stream'+(replica.epoch ? '?epoch='+encodeURIComponent(replica.epoch)+'&after='+replica.event_sequence : ''));
        stream.onopen = () => {if (alive) setTransport('verbunden');};
        stream.onerror = () => {if (alive) setTransport('unterbrochen');};
        stream.addEventListener('snapshot', event => {apply(JSON.parse(event.data)).catch(e => {if (alive) setError(e.message);});});
        stream.addEventListener('delivery', event => {
          replica.acceptEvent(JSON.parse(event.data)).then(result => {
            if (!alive) return;
            if (result.reason === 'EVENT_SEQUENCE_GAP') connect();
            else if (result.reason && !result.accepted && !result.duplicate) setError(result.reason);
          }).catch(e => {if (alive) setError(e.message);});
        });
        stream.addEventListener('node', event => replica.observe(JSON.parse(event.data)));
      }
      function resume() {if (!document.hidden) {read(); if (stream?.readyState === EventSource.CLOSED) connect();}}
      refresh.current = read;
      read(); connect();
      document.addEventListener('visibilitychange', resume);
      window.addEventListener('online', resume);
      // The clock updates age only; it never relabels old data as a new readback.
      const clock = setInterval(() => {if (alive) setTick(Date.now());}, 1000);
      return () => {alive=false;stream?.close();clearInterval(clock);document.removeEventListener('visibilitychange',resume);window.removeEventListener('online',resume);};
    }, []);
    const offline = document.documentElement.dataset.qikvrtOffline === 'true';
    const scope = !offline && location.pathname === '/node' ? 'node' : !offline && location.pathname === '/mesh' ? 'mesh' : 'entry';
    if (scope === 'entry') return h(React.Fragment, null,
      h('header', null, h('strong', null, 'RaumzeitTerminal'), h('nav', {'aria-label':'Terminal-Bereiche'},
        h('a', {href:'#entry-title'}, 'Mein Kontext'),
        offline ? null : h('a', {href:'/mesh'}, 'Mesh-Monitor'), h('a', {href:'#nachweise'}, 'Nachweise'))),
      h('main', {id:'main'}, h(PersonalEntry),
        h('footer', null, 'Ingolf Lohmann · QIK-VRT · Passives React Universal Terminal')));
    const repository = new URL(location.href).searchParams.get('repository') || runtime?.source_repository;
    const repos = (data?.repositories || []).filter(repo => scope === 'mesh' || repo.name === repository);
    const observed = data?.generated_at;
    const age = observed ? Math.max(0, Math.floor((tick-Date.parse(observed))/1000)) : null;
    const runs = repos.flatMap(repo => [...(repo.running?.runs || []), ...(repo.waiting?.runs || []), ...(repo.recent?.runs || [])])
      .filter((run,index,all) => all.findIndex(other => other.id === run.id && other.repository === run.repository) === index);
    return h(React.Fragment,null,
      h('header',null,h('strong',null,'RaumzeitTerminal'),h('nav',{'aria-label':'Terminal-Bereiche'},h('a',{href:'/'},'Mein Kontext'),h('a',{href:'/mesh'},'Mesh-Monitor'),h('a',{href:'/node'},'Repository-Node'),h('a',{href:'/#nachweise'},'Nachweise'),h('a',{href:'/AI/'},'Technisches Terminal'))),
      h('main',{id:'main'},h('p',{className:'sub'},'Universales Raumzeit-Terminal'),
        h('h1',null,scope === 'mesh' ? 'Das Mesh im aktuellen Nachweisstand' : repository || 'Repository-Node'),
        h('div',{className:'meta'},h('p',null,'Stream: ',transport,' · Datenstand: ',date(observed), age !== null ? ' · Alter: '+age+' s' : ''),h('button',{onClick:()=>refresh.current()},'Readback erneuern')),
        error ? h('p',{role:'alert',className:'error'},'Readback offen: ',error,'; der letzte Datenstand bleibt sichtbar.') : null,
        h(globalThis.QikvrtMeshFileView),
        h('section',{className:'notice'},h('h2',null,'Erster gemeinsamer Ping'),
          h('p',null,'Noch nicht abgenommen. Öffentliche Self-Host-Auslieferung, Hosting-CI und Empfang an allen zugelassenen Terminals sind offen.'),
          h('p',{className:'sub'},'Ein verbundener Stream und ein Runtime-Readback werden getrennt vom vollständigen Round Trip geführt.')),
        h('section',null,h('h2',null,'Repository-Nodes'),h('div',{className:'grid'},
          repos.length ? repos.map(repo => h('article',{key:repo.name},h('h3',null,repo.name),h('p',null,repo.availability?.state || repo.state || 'beobachtet'),
            h('a',{href:'/node?repository='+encodeURIComponent(repo.name)},'Node öffnen'))) : h('p',null,'Kein frisch bestätigter Remote-Node-Stand.'))),
        h('section',null,h('h2',null,'Dieser Self-Host-Kandidat'),runtime ? fields({
          'Node':runtime.node_id,'Quellrepository':runtime.source_repository,'Commit':runtime.source_head,'Tree':runtime.source_tree,
          'Paket':runtime.manifest_sha256,'Profil':runtime.terminal_profile,'Nativer Kanal':native?.state || 'offen',
          'Ledger-Epoch':native?.ledger_id || 'offen','Öffentliches Routing':runtime.public_routing_verified === true ? 'bestätigt' : 'separate Abnahme offen',
          'Mesh-Abnahme':'offen'}) : h('p',null,'Noch kein Runtime-Readback.')),
        h('section',null,h('h2',null,'Aktivität'),h('div',{className:'table'},h('table',null,
          h('thead',null,h('tr',null,...['Workflow','Zustand','Commit','Beobachtung'].map(v=>h('th',{key:v},v)))),
          h('tbody',null,runs.slice(0,50).map((run,i)=>h('tr',{key:String(run.id)+'-'+i},h('td',null,run.name),h('td',null,run.state),h('td',null,h('code',null,short(run.head_sha))),h('td',null,date(run.updated_at))))))),
          runs.length ? null : h('p',null,'Keine bestätigte Workflow-Aktivität in diesem Datenstand.')),
        h('footer',null,'Ingolf Lohmann · Statische React-Auslieferung mit geprüftem Ereignis-Readback · ',h('a',{href:'/scheibenhard-original.html'},'Erhaltenes Ausgangsdokument'))));
  }
  ReactDOM.createRoot(document.getElementById('qikvrt-react')).render(h(App));
})();
