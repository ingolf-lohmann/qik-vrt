// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Independent browser verification of the revision-03 wire representation.
(() => {
  'use strict';
  const bools=['transport_ack','origin_checked','context_checked','semantics_reconstructed','effect_anticipated','risk_classified','responsibility_assigned','connection_decided','policy_allows_release','ordinary_release','deadline_exceeded'];
  const sets=['reasons','evidence_refs','required_evidence_refs','open_questions','next_required_checks'];
  const fields=[...bools,...sets,'wire_version','message_type','protocol_root_id','protocol_version','protocol_id','previous_protocol_id','previous_protocol_hash','protocol_hash','input_id','input_hash','state','risk_level','responsibility_owner','connection_decision','policy_id','policy_version','policy_hash','evaluation_timeout_ms','created_utc'].sort();
  const sha=/^sha256:[a-f0-9]{64}$/;
  const trustedPolicyHash='sha256:bfb3b022eb47c370bbb2f0de78cd829d73987ab7e91bf31e17fd48b8021a0a60';
  const fail = reason => {throw Error(reason);};
  function norm(v){
    if(typeof v==='string'){for(let i=0;i<v.length;i++){const c=v.charCodeAt(i);if(c>=0xd800&&c<=0xdbff){const n=v.charCodeAt(++i);if(!(n>=0xdc00&&n<=0xdfff))fail('Ungültiger Unicode-Skalarwert.');}else if(c>=0xdc00&&c<=0xdfff)fail('Ungültiger Unicode-Skalarwert.');}return v.normalize('NFC');}
    if(v===null||typeof v==='boolean'||typeof v==='number'&&Number.isSafeInteger(v))return v;
    if(Array.isArray(v))return v.map(norm);
    if(v&&typeof v==='object'){const out=Object.create(null);for(const key of Object.keys(v)){const n=norm(key);if(Object.hasOwn(out,n))fail('Doppelter normalisierter Schlüssel.');out[n]=norm(v[key]);}return out;}
    return fail('I-JSON-Wert erforderlich.');
  }
  function canonical(v){v=norm(v);if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';if(v&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
  async function digest(value){if(!crypto.subtle)fail('SHA-256 ist in diesem Ursprung nicht verfügbar.');const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(value)));return 'sha256:'+Array.from(new Uint8Array(d),b=>b.toString(16).padStart(2,'0')).join('');}
  function parse(text){
    if(typeof text!=='string'||text.length>65536||text.charCodeAt(0)===0xfeff)fail('Begrenztes UTF-8-JSON erforderlich.');
    let i=0;const ws=()=>{while(/[\x20\t\r\n]/.test(text[i]||'!'))i++;};
    function string(){const start=i++;let escaped=false;while(i<text.length){const c=text[i++];if(c==='"'&&!escaped)return JSON.parse(text.slice(start,i));if(c==='\\'&&!escaped)escaped=true;else escaped=false;}fail('Unvollständiger JSON-String.');}
    function value(depth){if(depth>64)fail('JSON-Verschachtelung überschritten.');ws();const c=text[i];
      if(c==='{'){i++;ws();const keys=new Set();if(text[i]==='}'){i++;return;}while(true){ws();if(text[i]!=='"')fail('JSON-Schlüssel erforderlich.');const key=norm(string());if(keys.has(key))fail('Doppelter JSON-Schlüssel.');keys.add(key);ws();if(text[i++]!==':')fail('Ungültiges JSON.');value(depth+1);ws();const end=text[i++];if(end==='}')return;if(end!==',')fail('Ungültiges JSON-Objekt.');}}
      if(c==='['){i++;ws();if(text[i]===']'){i++;return;}while(true){value(depth+1);ws();const end=text[i++];if(end===']')return;if(end!==',')fail('Ungültiges JSON-Array.');}}
      if(c==='"'){string();return;}const token=/^(?:true|false|null|-?(?:0|[1-9][0-9]*))/.exec(text.slice(i));if(!token)fail('I-JSON-Wert erforderlich.');i+=token[0].length;
    }
    value(0);ws();if(i!==text.length)fail('Ungültiges oder nicht ganzzahliges JSON.');return norm(JSON.parse(text));
  }
  function scalar(a,b){const x=Array.from(a,c=>c.codePointAt(0)),y=Array.from(b,c=>c.codePointAt(0));for(let i=0;i<Math.min(x.length,y.length);i++)if(x[i]!==y[i])return x[i]-y[i];return x.length-y.length;}
  function projection(record){return Object.fromEntries(Object.entries(record).filter(([k])=>!['protocol_hash','created_utc'].includes(k)));}
  function state(r){
    if(r.deadline_exceeded||r.reasons.includes('PREVIOUS_PROTOCOL_INTEGRITY_FAILURE'))return 'EFFECT_ACK_BLOCK';
    if(!r.transport_ack||r.input_hash==='UNAVAILABLE')return 'EFFECT_NACK';
    if(r.reasons.some(x=>['PAYLOAD_EXCEEDS_SYNCHRONOUS_LIMIT','DECLARED_INPUT_HASH_MALFORMED','INPUT_HASH_MISMATCH'].includes(x))||r.connection_decision==='BLOCK')return 'EFFECT_ACK_BLOCK';
    if(r.connection_decision==='ISOLATE')return 'EFFECT_ACK_ISOLATE';
    return ['origin_checked','context_checked','semantics_reconstructed','effect_anticipated','risk_classified','responsibility_assigned','connection_decided','policy_allows_release'].every(k=>r[k])&&sha.test(r.input_hash)&&r.risk_level!=='UNKNOWN'&&r.responsibility_owner!==''&&r.connection_decision==='RELEASE'&&!r.open_questions.length&&!r.next_required_checks.length&&r.required_evidence_refs.every(x=>r.evidence_refs.includes(x))?'EFFECT_ACK_DONE':'EFFECT_ACK_CONTINUE';
  }
  async function verify(context,expected){
    if(!context||!Array.isArray(context.chain)||context.chain.length<1||context.chain.length>128)fail('Unvollständige Protokollkette.');
    let previous=null;
    for(const raw of context.chain){
      const r=norm(raw);
      if(Object.keys(r).sort().join('|')!==fields.join('|')||r.wire_version!==1||r.message_type!=='effect-ack-record')fail('Geschlossenes Wire-Version-1-Format erforderlich.');
      if(bools.some(k=>typeof r[k]!=='boolean'))fail('Boolesche Protokollfelder erforderlich.');
      for(const [name,limit,min]of [['protocol_root_id',256,1],['protocol_id',512,1],['input_id',256,1],['policy_id',256,1],['responsibility_owner',256,0]])if(typeof r[name]!=='string'||Array.from(r[name]).length<min||Array.from(r[name]).length>limit)fail('Protokollbezeichner außerhalb der Grenzen.');
      if(!Number.isSafeInteger(r.protocol_version)||r.protocol_version<1||!Number.isSafeInteger(r.policy_version)||r.policy_version<1||!Number.isInteger(r.evaluation_timeout_ms)||r.evaluation_timeout_ms<1||r.evaluation_timeout_ms>2147483647)fail('Ungültige Protokollversion oder Zeitgrenze.');
      if(!['UNKNOWN','LOW','MEDIUM','HIGH','CRITICAL'].includes(r.risk_level)||!['UNDECIDED','CONTINUE','RELEASE','ISOLATE','BLOCK'].includes(r.connection_decision))fail('Unbekannter Entscheidungswert.');
      if(r.connection_decided!==(r.connection_decision!=='UNDECIDED'))fail('Widersprüchliche Verbindungsentscheidung.');
      if(!sha.test(r.protocol_hash)||!sha.test(r.policy_hash)||r.input_hash!=='UNAVAILABLE'&&!sha.test(r.input_hash)||r.input_hash==='UNAVAILABLE'&&r.state!=='EFFECT_NACK')fail('Ungültiger Hash.');
      if(typeof r.created_utc!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(r.created_utc)||!Number.isFinite(Date.parse(r.created_utc))||Number(r.created_utc.slice(0,4))<1||new Date(r.created_utc).toISOString().slice(0,19)!==r.created_utc.slice(0,19))fail('Ungültige UTC-Protokollzeit.');
      for(const key of sets){if(!Array.isArray(r[key])||r[key].length>128||r[key].some(x=>typeof x!=='string'||Array.from(x).length>1024))fail('Ungültige Belegmenge.');r[key]=[...new Set(r[key].filter(Boolean))].sort(scalar);if(key.endsWith('evidence_refs')&&r[key].some(x=>!sha.test(x)))fail('Ungültiger Belegdigest.');}
      if(r.deadline_exceeded&&!r.next_required_checks.length)fail('Timeout ohne Fortsetzungspfad.');
      if(r.protocol_id!==r.protocol_root_id+':v'+r.protocol_version||r.state!==state(r)||r.ordinary_release!==(r.state==='EFFECT_ACK_DONE')||await digest(projection(r))!==r.protocol_hash)fail('Protokollhash oder Zustandsableitung stimmt nicht.');
      if(!previous){if(r.protocol_version!==1||r.previous_protocol_id!==null||r.previous_protocol_hash!==null)fail('Kettenanfang fehlt.');}
      else if(r.protocol_version!==previous.protocol_version+1||r.previous_protocol_id!==previous.protocol_id||r.previous_protocol_hash!==previous.protocol_hash||['protocol_root_id','input_id','input_hash'].some(k=>r[k]!==previous[k]))fail('Vorgängerbindung stimmt nicht.');
      previous=r;
    }
    const r=previous,p=context.policy;
    if(p?.policy_id!=='QIKVRT_ADMITTED_NATIVE_TERMINAL_INPUT_V1'||p.policy_version!==1||r.policy_hash!==trustedPolicyHash||await digest(p)!==r.policy_hash||r.policy_id!==p.policy_id||r.policy_version!==p.policy_version)fail('Policy-Bindung stimmt nicht.');
    if(context.latest_hash!==r.protocol_hash||r.protocol_hash!==expected.recordHash||r.input_id!==expected.request.request_id||r.input_hash!==await digest(expected.request.input)||r.responsibility_owner!==expected.principal)fail('Vorbereitung ist veraltet oder gehört zu einem anderen Auftrag.');
    const evidence=context.evidence||{};
    if(Object.keys(evidence).sort().join('|')!==r.required_evidence_refs.join('|'))fail('Policy-Belegmenge stimmt nicht.');
    let subject=false,authority=false;
    for(const ref of r.required_evidence_refs){const value=evidence[ref];if(!r.evidence_refs.includes(ref)||await digest(value)!==ref)fail('Belegdigest stimmt nicht.');
      if(value.schema==='qikvrt_eap_subject_v1')subject=canonical(value.subject)===canonical(expected.request.subject)&&/^[a-f0-9]{32}$/.test(value.ledger_id);
      if(value.schema==='qikvrt_eap_authority_v1')authority=value.principal===expected.principal&&Array.isArray(value.permissions)&&value.permissions.includes('commit');}
    if(!subject||!authority||r.state!=='EFFECT_ACK_DONE'||r.ordinary_release!==true||expected.expiresAt*1000<=Date.now())fail('Keine frische Freigabe für diese native Eingabe.');
    return r;
  }
  globalThis.QikvrtDevopsWire={canonical,digest,verify,projection,parse};
})();
