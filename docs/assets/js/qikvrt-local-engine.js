/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

(function(){
  const KB_URL='assets/data/qikvrt_knowledge_base.json';
  let KB=null;
  async function loadKB(){ if(!KB){ KB=await fetch(KB_URL).then(r=>r.json()).catch(()=>null);} return KB; }
  function esc(s){return String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
  function classify(text){
    const t=(text||'').toLowerCase();
    const tags=[];
    if(/recht|ai act|pflicht|audit|nachweis|compliance|cra|nis2/.test(t)) tags.push('Rechts-/Nachweiskontext');
    if(/produkt|preis|kunde|verkauf|monetaris|pilot/.test(t)) tags.push('Produkt/Monetarisierung');
    if(/kognition|ontologie|unterschied|information|kausal|qik|vrt/.test(t)) tags.push('Künstliche Kognition');
    if(/node|seed|mesh|github|repository|workflow|registry/.test(t)) tags.push('Technische Architektur');
    if(!tags.length) tags.push('Allgemeine QIK-VRT-Einordnung');
    return tags;
  }
  function qikMap(text){
    const t=text.trim();
    return [
      'Q — Quantität: Welche Zustände, Risiken, Zählungen, Artefakte oder Nachweise sind betroffen?',
      'I — Information: Welche Unterschiede, Kontexte, Rollen, Quellen und Evidenzen müssen sichtbar werden?',
      'K — Kausalität: Welche Wirkung entsteht, wer trägt Verantwortung, und welcher nächste prüfbare Anschluss folgt?',
      'VRT — Realitätsprüfung: Welche Grenze verhindert Überbehauptung, blinde Automatisierung oder nicht belegte Freigabe?'
    ].join('\n');
  }
  function answerLocal(text,kb){
    const tags=classify(text);
    const lines=[];
    lines.push('QIK-VRT Kognitionskonsole — lokale Analyse');
    lines.push('');
    lines.push('Erkannter Fokus: '+tags.join(', '));
    lines.push('');
    lines.push(qikMap(text));
    lines.push('');
    if(tags.includes('Rechts-/Nachweiskontext')){
      lines.push('Einordnung: Für KI-, Software- und Lieferkettenprozesse sind technische Dokumentation, Transparenz, Logging, Risikokontrolle, menschliche Aufsicht und Cybersecurity wichtige Prüfgegenstände. QIK-VRT erprobt dafür run-id-spezifische Evidenz, Audit-Export und Wirkungshaltepunkte.');
      lines.push('Grenze: Die Artefakte können eine weitere rechtliche oder organisatorische Prüfung unterstützen; sie sind keine Rechtsberatung, Zertifizierung oder Konformitätsfeststellung.');
      lines.push('');
    }
    if(tags.includes('Technische Architektur')){
      lines.push('Referenzarchitektur: Seed und Node tauschen ausdrücklich autorisierte Repository-Artefakte aus. Der Seed validiert eine Allowlist, erzeugt lokalen Index, Status, Revalidierung und Audit/Dashboard-Artefakte. Die aktiven Workflows schreiben keine fremden Repositories.');
      lines.push('Schutzgrenzen: kein globales Scanning, keine Selbstverbreitung, strikte URL-/Repo-Bindung und fail-closed Fehlerstatus. Produktions- und Mehrknotenbetrieb sind gesondert zu validieren.');
      lines.push('');
    }
    if(tags.includes('Künstliche Kognition')){
      lines.push('Kognitionslesart: QIK-VRT behandelt Kognition als geordnete Verarbeitung von Unterschieden mit Wirkung und Verantwortungsgrenze. Der initiale Unterschied ist der kleinste anschlussfähige Ausgangspunkt: Ohne Unterschied keine Information, ohne Information keine gerichtete Wirkung, ohne Wirkung keine verantwortbare Prüfung.');
      lines.push('');
    }
    if(tags.includes('Produkt/Monetarisierung')){
      lines.push('Moeglicher Nutzen: Der Forschungsprototyp zeigt, wie Repository-Evidenz, Provenienz, Wirkungsgates und Auditdaten fuer konkrete Pilotpruefungen strukturiert werden koennen. Produkt- und Compliance-Reife werden damit nicht behauptet.');
      lines.push('');
    }
    lines.push('Nächster sinnvoller Anschluss: Formuliere den konkreten Fall als Repository, Artefakt, Risiko, gewünschte Entscheidung und benötigten Nachweis. Die Konsole kann daraus eine QIK/VRT-Prüfstruktur ableiten.');
    lines.push('');
    lines.push('Basis: '+(kb&&kb.product?kb.product:'QIK-VRT Forschungsprototyp')+' | Verbindliche Grenze: '+(kb&&kb.authoritative_status?kb.authoritative_status:'STATUS.md'));
    return lines.join('\n');
  }
  window.QIKVRTLocalEngine={loadKB, answerLocal, classify};
})();
