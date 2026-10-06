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
  // Source successor of #468's feedback semantics, not its test/effect receipts.
  const redact = value => String(value ?? '').replace(/\bBearer\s+[^\s;,]+/gi, 'Bearer [REDACTED]')
    .replace(/\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+/g, '[REDACTED]')
    .replace(/([?&](?:access_token|token|secret|password)=)[^\s&#]+/gi, '$1[REDACTED]');
  const safeDiagnostic = value => typeof value === 'string' ? redact(value) :
    value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).map(([key,item]) => [key,safeDiagnostic(item)])) : value;
  function diagnostic(error, source = {}) {
    const bound = error?.diagnostic || {};
    const status = bound.status ?? error?.status ?? source.http_status ?? null;
    return {
      source_url:bound.source_url ?? source.endpoint ?? null, method:bound.method ?? 'GET',
      observed_at:bound.observed_at ?? source.attempted_at ?? null,
      last_success_at:source.observed_at ?? null, phase:bound.phase ?? (status === null ? 'EVALUATION' : 'HTTP'),
      status:Number.isInteger(status) ? status : null, status_text:bound.status_text ?? null,
      original_error:redact(bound.original_error ?? error?.message ?? String(error)), error_name:bound.error_name ?? error?.name ?? 'Error',
      provider_request_id:bound.provider_request_id ?? null,
      rate_limit_remaining:bound.rate_limit_remaining ?? source.rate?.remaining ?? null,
      rate_limit_reset:bound.rate_limit_reset ?? source.rate?.reset_at ?? null, retry_after:bound.retry_after ?? null,
      response_body:bound.response_body ?? null, response_sha256:bound.response_sha256 ?? null,
      next_attempt_at:source.next_attempt_at ?? null, cause_established:false
    };
  }
  function explainFailure(d) {
    let state='Die Quelle konnte nicht aktualisiert werden.', cause='Die Ursache ist nicht geklärt.',
      actor='Repository-Verantwortliche',
      next='Den angegebenen REST-Endpunkt und den Zugriff prüfen; nach der Korrektur „Readback erneuern“ wählen.';
    if (d.phase === 'EVALUATION' || d.phase === 'JSON') {
      state='Die gelesenen Daten konnten nicht ausgewertet werden.';
      cause=d.phase === 'JSON' ? 'Die HTTP-Antwort liegt vor, aber das Lesen als JSON scheiterte. Die Ursache ist ungeklärt.' :
        'Die Readback-Auswertung scheiterte. Ein HTTP-Status ist an diesen Auswertungsfehler nicht gebunden; die Ursache ist ungeklärt.';
      actor='Monitor-Verantwortliche'; next='Antwortformat und Fehlerdiagnose des REST-Pfads prüfen; nach der Korrektur „Readback erneuern“ wählen.';
    } else if (d.status === 404) {
      state='Die angefragte Quelle ist derzeit nicht lesbar.';
      cause='Die REST-Anfrage erhielt HTTP 404. Ob die Quelle fehlt oder für diesen Zugriff nicht sichtbar ist, ist nicht geklärt.';
    } else if (d.status === 429 || (d.status === 403 && String(d.rate_limit_remaining) === '0')) {
      state='Der Anbieter begrenzt den Abruf.';
      cause='Die Antwort meldet HTTP '+d.status+(String(d.rate_limit_remaining) === '0' ? ' und ein verbleibendes API-Kontingent von 0.' : '.')+' Weitere Sperrgründe sind nicht geklärt.';
      actor='Monitor-Nutzende'; next='Retry-After-/Reset-Zeitpunkt in den technischen Details beachten; danach den REST-Readback erneuern. Ohne Wartezeit die Begrenzung durch Repository-Verantwortliche prüfen lassen.';
    } else if (d.status === 401 || d.status === 403) {
      state='Der Zugriff auf die Quelle wurde abgewiesen.';
      cause='Die Antwort meldet HTTP '+d.status+'. Ob Zugangsdaten, Leseberechtigung oder eine andere Zugriffssperre verantwortlich sind, ist nicht geklärt.';
    } else if (d.status >= 500) {
      state='Der angefragte Dienst meldet einen Serverfehler.';
      cause='Die Antwort meldet HTTP '+d.status+'. Die Ursache im Dienst oder seinem vorgeschalteten System ist nicht geklärt.';
      next='Den Dienst über den angegebenen REST-Pfad prüfen; nach bestätigter Wiederherstellung den Readback erneuern.';
    } else if (d.status === null) {
      state='Der Abruf lieferte keine HTTP-Antwort.';
      cause='Gemeldet wurde '+d.error_name+'. Ob Netzwerk, Browser-Zugriffsschutz oder die Gegenstelle verantwortlich ist, ist nicht geklärt.';
      actor='Monitor-Nutzende'; next='Verbindung und Browser-Netzwerkdiagnose für den REST-Endpunkt prüfen; nach Beseitigung des Hindernisses den Readback erneuern.';
    } else {
      cause='Die Antwort meldet HTTP '+d.status+'. Die Ursache ist nicht geklärt.';
    }
    return {state,cause,actor,next};
  }
  function ReadbackFeedback({failure, previous = false}) {
    const text=explainFailure(failure);
    const impact=failure.source_url === '/api/runtime' ? 'Kein frischer Runtime-Readback verfügbar. Ein früherer Runtime-Stand bestätigt keinen aktuellen Betriebszustand.' :
      failure.source_url === '/api/terminal' ? 'Kein frischer Terminal- und Lifecycle-Readback verfügbar. Die Wirkungsbestätigung bleibt offen.' :
        previous ? 'Kein neuer vollständiger Repository- und Workflow-Stand. Der letzte erfolgreiche Stand bleibt als veraltet sichtbar. Daraus folgt kein aktueller Betriebszustand.' :
          'Kein vollständiger Repository- und Workflow-Stand verfügbar. Daraus folgt kein Betriebszustand des Knotens.';
    return h('section', {className:'readback-feedback', 'aria-label':'Readback offen'},
      fields({'Zustand':text.state, 'Auswirkung':impact,
        'Belegter Status / Unsicherheit':text.cause, 'Zuständiger Akteur':text.actor,
        'Nächster REST-Schritt':text.next+(failure.source_url ? ' Endpunkt: '+redact(failure.source_url) : ' Ein REST-Endpunkt ist an diese Diagnose nicht gebunden.'),
        'Reparaturfortschritt':'Ein Reparaturstart ist durch diesen Monitor nicht belegt. Die Meldung beschreibt den beobachteten Abruf.'}),
      h('details', null, h('summary', null, 'Technische Details: ', failure.status === null ? failure.error_name : 'HTTP '+failure.status),
        h('pre', {tabIndex:0, 'aria-label':'Kopierbare Fehlerdiagnose'}, JSON.stringify(safeDiagnostic(failure),null,2))));
  }
  function RepositoryReadback({repo}) {
    const sources=Object.entries(repo.sources || {}), failed=sources.filter(([,source]) => source?.error);
    if (failed.length) return h('div', {role:'status', 'aria-live':'polite'}, ...failed.map(([key,source]) =>
      h(ReadbackFeedback, {key, failure:diagnostic(source.error,source), previous:!!source.observed_at})));
    const stale=sources.some(([,source]) => source?.stale);
    const availability=typeof repo.availability === 'string' ? repo.availability : repo.availability?.state || repo.state;
    return h('p', null, stale ? 'Datenstand veraltet oder unvollständig; aktuelle Aktivität ist unbekannt.' :
      availability === 'available' ? 'Repository-Lesepfad beobachtet. Daraus folgt keine Abnahme der Knotenlaufzeit.' :
        'Kein vollständiger frischer Repository-Readback belegt. Eine Fehlerursache ist nicht gebunden.');
  }
  function App() {
    const [data, setData] = React.useState(null);
    const [runtime, setRuntime] = React.useState(null);
    const [native, setNative] = React.useState(null);
    const [transport, setTransport] = React.useState('verbinde');
    const [error, setError] = React.useState([]);
    const [tick, setTick] = React.useState(Date.now());
    const refresh = React.useRef(() => {});
    React.useEffect(() => {
      if(document.documentElement.dataset.qikvrtOffline==='true'){setTransport('lokale Datei');return;}
      const replica = globalThis.QikvrtReplica.create({version:document.documentElement.dataset.qikvrtMonitorVersion});
      let alive = true, stream, pending = false;
      async function get(path) {
        let response=null, phase='REQUEST';
        try {
          response = await fetch(path, {cache:'no-store', signal:AbortSignal.timeout(8000)});
          phase='HTTP';
          if (!response.ok) throw Error(path + ': HTTP ' + response.status);
          phase='JSON'; return await response.json();
        } catch (e) {
          const wrapped=Error(redact(e.message));
          wrapped.diagnostic={source_url:path, method:'GET', observed_at:new Date().toISOString(), phase,
            status:response?.status ?? null, status_text:response?.statusText ?? null, original_error:wrapped.message,
            error_name:e.name || 'Error', provider_request_id:response?.headers.get('x-github-request-id') ?? null,
            rate_limit_remaining:response?.headers.get('x-ratelimit-remaining') ?? null,
            rate_limit_reset:response?.headers.get('x-ratelimit-reset') ?? null, retry_after:response?.headers.get('retry-after') ?? null};
          throw wrapped;
        }
      }
      async function apply(value) {
        const result = await replica.accept(value);
        if (!alive) return;
        if (result.accepted) {
          setData(result.snapshot);
          setError(prior => prior.filter(d => !['/api/activity','/api/stream'].includes(d.source_url)));
        }
        else if (!result.duplicate) throw Error(result.reason);
      }
      async function read() {
        if (pending) return;
        pending = true;
        try {
          const results = await Promise.allSettled([get('/api/activity'),get('/api/runtime'),get('/api/terminal')]);
          if (!alive) return;
          if (results[1].status === 'fulfilled') setRuntime(results[1].value);
          if (results[2].status === 'fulfilled') setNative(results[2].value);
          const failed=results.filter(result => result.status === 'rejected').map(result => diagnostic(result.reason));
          if (results[0].status === 'fulfilled') {
            try {await apply(results[0].value);} catch (e) {failed.push(diagnostic(e,{endpoint:'/api/activity'}));}
          }
          if (alive) setError(failed);
        } catch (e) {if (alive) setError([diagnostic(e)]);} finally {pending = false;}
      }
      function connect() {
        stream?.close();
        stream = new EventSource('/api/stream'+(replica.epoch ? '?epoch='+encodeURIComponent(replica.epoch)+'&after='+replica.event_sequence : ''));
        stream.onopen = () => {if (alive) setTransport('verbunden');};
        stream.onerror = () => {if (alive) setTransport('unterbrochen');};
        const streamFailure=e => {if (alive) setError(prior => [...prior.filter(d => d.source_url !== '/api/stream'), diagnostic(e,{endpoint:'/api/stream'})]);};
        stream.addEventListener('snapshot', event => {
          try {apply(JSON.parse(event.data)).catch(streamFailure);} catch (e) {streamFailure(e);}
        });
        stream.addEventListener('delivery', event => {
          try {replica.acceptEvent(JSON.parse(event.data)).then(result => {
            if (!alive) return;
            if (result.reason === 'EVENT_SEQUENCE_GAP') connect();
            else if (result.reason && !result.accepted && !result.duplicate) streamFailure(Error(result.reason));
          }).catch(streamFailure);} catch (e) {streamFailure(e);}
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
    const params = new URL(location.href).searchParams;
    const scope = location.pathname === '/node' || params.get('view') === 'node' ? 'node' : 'mesh';
    const repository = new URL(location.href).searchParams.get('repository') || runtime?.source_repository;
    const repos = (data?.repositories || []).filter(repo => scope === 'mesh' || repo.name === repository);
    const observed = data?.generated_at;
    const age = observed ? Math.max(0, Math.floor((tick-Date.parse(observed))/1000)) : null;
    const runs = repos.flatMap(repo => [...(repo.running?.runs || []), ...(repo.waiting?.runs || []), ...(repo.recent?.runs || [])])
      .filter((run,index,all) => all.findIndex(other => other.id === run.id && other.repository === run.repository) === index);
    return h(React.Fragment,null,
      h('header',null,h('strong',null,'RaumzeitTerminal'),h('nav',{'aria-label':'Terminal-Bereiche'},h('a',{href:'index-react.html?view=mesh'},'Mesh-Monitor'),h('a',{href:'index-react.html?view=node'},'Repository-Node'),h('a',{href:'index.html'},'Vorhandener Monitor'))),
      h('main',{id:'main'},h('p',{className:'sub'},'Universales Raumzeit-Terminal'),
        h('h1',null,scope === 'mesh' ? 'Das Mesh im aktuellen Nachweisstand' : repository || 'Repository-Node'),
        h('div',{className:'meta'},h('p',null,'Stream: ',transport,' · Datenstand: ',date(observed), age !== null ? ' · Alter: '+age+' s' : ''),h('button',{onClick:()=>refresh.current()},'Readback erneuern')),
        error.length ? h('div',{role:'alert'},
          h('p',{className:'error'},'Readback offen: Der letzte Datenstand bleibt sichtbar. Die folgenden Diagnosen beschreiben die offenen Abrufe.'), ...error.map((failure,index) =>
          h(ReadbackFeedback,{key:String(failure.source_url)+'-'+index,failure,previous:failure.source_url === '/api/activity' && !!data}))) : null,
        h('section',null,h('h2',null,'Repository-Nodes'),h('div',{className:'grid'},
          repos.length ? repos.map(repo => h('article',{key:repo.name},h('h3',null,repo.name),h(RepositoryReadback,{repo}),
            h('a',{href:'index-react.html?view=node&repository='+encodeURIComponent(repo.name)},'Node öffnen'))) : h('p',null,'Kein frisch bestätigter Remote-Node-Stand.'))),
        h('section',null,h('h2',null,'Gebundene Laufzeit'),runtime ? fields({
          'Node':runtime.node_id,'Quellrepository':runtime.source_repository,'Commit':runtime.source_head,'Tree':runtime.source_tree,
          'Paket':runtime.manifest_sha256,'Profil':runtime.terminal_profile,'Nativer Kanal':native?.state || 'offen',
          'Ledger-Epoch':native?.ledger_id || 'offen','Öffentliches Routing':runtime.public_routing_verified === true ? 'bestätigt' : 'separate Abnahme offen',
          'Mesh-Abnahme':'offen'}) : h('p',null,'Noch kein Runtime-Readback.')),
        h('section',null,h('h2',null,'Aktivität'),h('div',{className:'table'},h('table',null,
          h('thead',null,h('tr',null,...['Workflow','Zustand','Commit','Beobachtung'].map(v=>h('th',{key:v},v)))),
          h('tbody',null,runs.slice(0,50).map((run,i)=>h('tr',{key:String(run.id)+'-'+i},h('td',null,run.name),h('td',null,run.state),h('td',null,h('code',null,short(run.head_sha))),h('td',null,date(run.updated_at))))))),
          runs.length ? null : h('p',null,'Keine bestätigte Workflow-Aktivität in diesem Datenstand.')),
        h('footer',null,'Ingolf Lohmann · Statische React-Auslieferung mit geprüftem Ereignis-Readback · ',h('a',{href:'index.html'},'Vorhandener Monitor'))));
  }
  ReactDOM.createRoot(document.getElementById('qikvrt-react')).render(h(App));
})();
