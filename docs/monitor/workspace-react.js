// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
(() => {
  'use strict';
  const {React, ReactDOM} = globalThis.QikvrtReact, h = React.createElement;
  const when = value => value ? new Date(value).toLocaleString('de-DE', {timeZone:'Europe/Paris'}) + ' (Paris)' : 'noch nicht gelesen';
  const link = (url, label = url) => h('a', {href:url}, label);
  const licenseRows = [
    ['Gekennzeichnete Dokumente und Nicht-Source-Materialien', 'CC-BY-NC-ND-4.0', 'Namensnennung; nichtkommerzielle Weitergabe; keine Weitergabe von Bearbeitungen nach dieser Lizenz.', '/workspace/licenses/CC-BY-NC-ND-4.0.txt'],
    ['Gekennzeichneter neuerer QIK-VRT-Source-Code und ausführbare Werkzeuge', 'PolyForm-Noncommercial-1.0.0', 'Die im Originaltext erlaubten Zwecke. Weitergehende kommerzielle Nutzung durch Dritte benötigt eine separate schriftliche Lizenz.', '/workspace/licenses/PolyForm-Noncommercial-1.0.0.txt'],
    ['Frühere oder ausdrücklich gekennzeichnete Apache-Dateien', 'Apache-2.0', 'Bereits erteilte Rechte bleiben in ihrem ursprünglichen Geltungsbereich erhalten.', '/workspace/licenses/Apache-2.0.txt'],
    ['Anders gekennzeichnete Komponenten und Drittmaterial', 'Jeweilige Original- und Dateilizenz', 'Keine pauschale Übertragung der Dokument- oder Software-Standardlizenz. React behält seine MIT-Lizenz.', '/workspace/licenses/REACT_LICENSE.txt']
  ];
  class Boundary extends React.Component {
    constructor(props) {super(props); this.state = {failed:false};}
    static getDerivedStateFromError() {return {failed:true};}
    render() {return this.state.failed ? h('main', {id:'main'}, h('h1', null, 'Ansicht unterbrochen'), h('p', {role:'alert'}, 'Die Darstellung ist ungeprüft. Bitte den Original-Einstieg und die Server-Nachweise verwenden.'), link('/workspace/original.html', 'Original-Einstieg')) : this.props.children;}
  }
  function App() {
    const [state, setState] = React.useState({verified:false, reading:true, transport:'nicht bestätigt'});
    const adapter = React.useRef(null);
    React.useEffect(() => {
      const client = globalThis.QikvrtWorkspace.create({version:document.documentElement.dataset.qikvrtMonitorVersion, onChange:setState});
      adapter.current = client;
      client.start();
      const resume = () => {if (!document.hidden) client.read();};
      document.addEventListener('visibilitychange', resume); window.addEventListener('online', resume);
      return () => {client.stop(); adapter.current = null; document.removeEventListener('visibilitychange', resume); window.removeEventListener('online', resume);};
    }, []);
    const runtime = state.runtime, native = state.native;
    const refresh = () => adapter.current?.read();
    const reason = state.reason === 'READBACK_EXPIRED' ? 'Der native Readback ist abgelaufen. Bitte erneut lesen.' :
      state.reason === 'EVENT_REPLAY_PENDING' ? 'Die ursprünglichen Ereignisse werden noch geprüft.' : state.reason;
    const origin = runtime?.source_head && /^[a-f0-9]{40}$/.test(runtime.source_head) ? 'https://github.com/ingolf-lohmann/qik-vrt/blob/' + runtime.source_head + '/' : 'https://github.com/ingolf-lohmann/qik-vrt/blob/main/';
    return h(React.Fragment, null,
      h('header', {className:'workspace-header'},
        h('div', {className:'headerline'}, h('div', {className:'eyebrow'}, 'QIK VRT Mesh Netzwerk'),
          h('nav', {'aria-label':'Hauptnavigation'}, link('/mesh', 'Mesh'), link('/devops', 'DevOps'), link('/AI/', 'Universal Terminal'))),
        h('h1', null, 'Wissen erschließen.\nVerbunden weiterarbeiten.'),
        h('p', {className:'sub'}, 'Originalquellen finden, Herkunft und Rechte prüfen, Arbeit nachvollziehbar an das bestehende Universal Terminal und den Universal Transputer anschließen.'),
        h('span', {className:'tag'}, 'Ingolf Lohmann · Schöpfer, Rechteinhaber und Product Owner'),
        h('span', {className:'tag'}, 'React · vorhandener S1-/EAP-Anschluss')),
      h('main', {id:'main'},
        h('section', {className:'workspace-intro', 'aria-labelledby':'entry-title'},
          h('div', null, h('p', {className:'workspace-kicker'}, 'Workspace-Einstieg'), h('h2', {id:'entry-title'}, 'Ein Zugang mit nachvollziehbaren Voraussetzungen.'),
            h('p', null, 'QIK-VRT verbindet Projektwissen, wissenschaftliche Veröffentlichungen, Software und Wirkungsnachweise. Natürliche und künstliche Kognitionen beginnen bei der passenden Originalquelle und bewahren Version, Herkunft und Aussageumfang.'),
            h('p', {className:'workspace-note'}, 'Die Zugangsvorgabe betrifft den vorgesehenen ChatGPT-Workspace. Bereits veröffentlichte Originale behalten ihre jeweiligen Zugriffsrechte und Lizenzen.')),
          h('div', {className:'workspace-status', role:'status', 'aria-live':'polite'},
            h('strong', null, state.reading ? 'Anschluss wird geprüft …' : state.verified ? 'Native Verbindung zurückgelesen' : 'Anschluss noch nicht bestätigt'),
            h('small', null, 'Readback: ' + when(state.observed_at)), h('small', null, 'Ereigniskanal: ' + state.transport),
            h('button', {onClick:refresh, disabled:state.reading, className:'primary'}, state.reading ? 'Prüfung läuft …' : 'Verbindung erneut prüfen'))),
        reason && !state.reading ? h('p', {className:'notice', role:'alert'}, 'Offener Nachweis: ', reason, '. Der letzte beobachtete Stand bleibt als solcher sichtbar.') : null,
        h('div', {className:'workspace-grid'},
          h('section', {className:'panel'}, h('h3', null, '1 · Quellenstand'), h('p', null, runtime?.source_repository || 'Authority: ingolf-lohmann/qik-vrt'),
            h('p', null, 'Head', h('code', null, runtime?.source_head || 'ungeprüft')), h('p', null, 'Tree', h('code', null, runtime?.source_tree || 'ungeprüft'))),
          h('section', {className:'panel'}, h('h3', null, '2 · Native Anbindung'), h('p', null, state.verified ? 'Runtime, Node, Replik und EAP-Subject stimmen im zurückgelesenen Stand überein.' : 'Native Admission und unabhängiger Readback sind noch nicht gemeinsam bestätigt.'),
            h('p', null, 'Node: ' + (runtime?.node_id || 'ungeprüft')), h('p', null, 'Geprüfte Originalereignisse: ' + (state.replica?.events ?? 0))),
          h('section', {className:'panel'}, h('h3', null, '3 · Workspace-Zugang'), h('p', null, 'Mitgliedschaft: ungeprüft'), h('p', null, 'Lizenzannahme: ungeprüft'), h('p', null, 'Zugriffsfreigabe: offen'))),
        h('section', {className:'panel workspace-section', 'aria-labelledby':'access-title'}, h('h2', {id:'access-title'}, 'So wird der Zugang freigegeben'),
          [
            ['Workspace und Mitglied binden', 'Den tatsächlichen Workspace und das authentifizierte Mitglied eindeutig feststellen.'],
            ['Originaltexte und Artefakte anzeigen', 'Getrennte Lizenztexte, konkrete Versionen und Artefaktmanifest vor Freigabe zuordnen.'],
            ['Annahme und Mitgliedschaft prüfen', 'Ausdrückliche Annahme an Mitglied, Workspace, Zeitpunkt, Lizenzstand und Manifest binden; tatsächliche Mitgliedschaft separat nachweisen.'],
            ['Zugriff herstellen und zurücklesen', 'Erst nach diesen Prüfungen berechtigten Zugriff gewähren und unabhängig verifizieren.']
          ].map(([title, text], i) => h('div', {className:'workspace-step', key:title}, h('b', {'aria-hidden':true}, i + 1), h('p', null, h('strong', null, title), h('small', null, text)))),
          h('p', {className:'notice'}, 'Die vorhandene Runtime stellt noch keinen technisch abgenommenen Workspace-Mitgliedschafts- und Lizenzannahmedienst bereit. Eine allgemeine Workspace-Freigabe belegt keine vorherige Annahme.'),
          h('button', {disabled:true}, 'Workspace-Zugang noch nicht freigegeben')),
        h('section', {className:'panel workspace-section', 'aria-labelledby':'license-title'}, h('h2', {id:'license-title'}, 'Dokumente und Source-Code: getrennte Lizenzen'),
          h('div', {className:'table-scroll'}, h('table', {className:'workspace-licenses'}, h('caption', {className:'workspace-note'}, 'Es gilt die Kennzeichnung der jeweiligen Originaldatei.'),
            h('thead', null, h('tr', null, ['Material', 'Original-Lizenz', 'Nutzungsgrenze'].map(title => h('th', {scope:'col', key:title}, title)))),
            h('tbody', null, licenseRows.map(([material, name, boundary, url]) => h('tr', {key:name}, h('td', null, material), h('td', null, link(url, name)), h('td', null, boundary)))))),
          h('p', {className:'workspace-note'}, 'Dateiendung, Ordner und Katalogeintrag legen keine Lizenz fest. Gemischte Archive benötigen getrennte Zuordnungen; ungeklärte Rechte bleiben vor Freigabe offen.'),
          h('p', null, 'Lizenzgeber: Ingolf Lohmann. Mitgliedschaft und Lizenzannahme erteilen keine zusätzliche kommerzielle Lizenz. Bereits gewährte kommerzielle Rechte bleiben erhalten. Weitergehende schriftliche Rechte: ', link('mailto:ingolf.lohmann@live.com', 'ingolf.lohmann@live.com'), '.'),
          h('p', {className:'workspace-note'}, 'Required Notice: Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder.')),
        h('section', {className:'panel workspace-section'}, h('h2', null, 'Mit der Originalquelle beginnen'),
          h('p', null, 'Wissenschaftlicher Einstieg: „Von Softwarearchitektur zur Weltformel – Das Universum als Round Trip“, Versions-DOI 10.5281/zenodo.21888130. Formale Beweise, Softwaretests, Interpretation und empirische Bestätigung bleiben getrennt.'),
          h('div', {className:'workspace-sources'}, link('https://zenodo.org/records/21888130'), link(origin + 'AI'), link(origin + 'AI_CONTEXT.json')),
          h('p', null, 'Künstliche Kognitionen lesen /AI und AI_CONTEXT.json in der festgelegten Reihenfolge. Lesen, Workspace-Beitritt und Source-Verfügbarkeit verleihen keine Ausführungs-, Writer- oder kommerzielle Sonderberechtigung.'),
          h('details', null, h('summary', null, 'Rekonstruktion und Vertrauenspfad'), h('p', null, 'Seed/Root-Referenz → Resolver → Trustanker → TCP/IP-Transport → Manifest → Paketprüfung → Bootstrap → native Admission → Anwendung. Ein SHA-256-Digest adressiert vorhandene Information; Nutzdaten, Decoder, Rechte und ausführbarer Host benötigen eigene Nachweise.'))),
        h('div', {className:'workspace-terminal'}, h(globalThis.QikvrtNativeTerminal, {native, onRefresh:refresh})),
        h('section', {className:'panel workspace-section'}, h('h2', null, 'Herkunft und Prüfgrenze'),
          h('dl', {className:'workspace-provenance'}, h('dt', null, 'Vorlage'), h('dd', null, link('/workspace/original.html', 'QIKVRT_START_HIER.html · unverändertes Original vom 25. Oktober 2026')),
            h('dt', null, 'Runtime-Paket'), h('dd', null, runtime?.manifest_sha256 || 'ungeprüft'), h('dt', null, 'Replik-Digest'), h('dd', null, state.replica?.digest || 'ungeprüft'),
            h('dt', null, 'Prüfumfang'), h('dd', null, 'Quellen-/Runtime-Anschluss und dauerhaft zurückgelesene native Texteingabe. Workspace-, Repository-, Host- und Domain-Abnahmen benötigen ihre eigenen Nachweise.')),
          h('p', {className:'workspace-note'}, 'Grundlagen, Vorgaben und Urheberschaft: Ingolf Lohmann. React-Umsetzung: OpenAI Codex. Kein neuer wissenschaftlicher Beweis und keine neue kommerzielle Vereinbarung.')),
        h('footer', {className:'workspace-footer'}, link('/workspace/access.json', 'Maschinenlesbarer Zugangsstand'), link('/api/runtime', 'Runtime-Readback'), link('/.well-known/effect-ack', 'EAP-Vertrag'), h('p', null, 'EFFECT_ACK_DONE = false · Workspace-Freigabe und produktive Domain-Abnahme bleiben offen.'))));
  }
  ReactDOM.createRoot(document.getElementById('qikvrt-workspace')).render(h(Boundary, null, h(App)));
})();
