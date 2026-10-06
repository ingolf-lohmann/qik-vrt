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
        error ? h('p',{role:'alert',className:'error'},'Readback offen: ',error,'; der letzte Datenstand bleibt sichtbar.') : null,
        h('section',null,h('h2',null,'Repository-Nodes'),h('div',{className:'grid'},
          repos.length ? repos.map(repo => h('article',{key:repo.name},h('h3',null,repo.name),h('p',null,repo.availability?.state || repo.state || 'beobachtet'),
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
