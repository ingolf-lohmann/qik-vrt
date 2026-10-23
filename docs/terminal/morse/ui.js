/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
'use strict';
const $ = id => document.getElementById(id), codec = globalThis.QikMorse;
let current = null, pending = null, urls = [], generation = 0;
const b64 = raw => btoa(Array.from(raw, b => String.fromCharCode(b)).join(''));
function status(text, error = false) { $('status').textContent = text; $('status').classList.toggle('error', error); }
function link(raw, name, label, type = 'application/octet-stream') {
  const url = URL.createObjectURL(new Blob([raw], {type})); urls.push(url);
  const a = document.createElement('a'); a.href = url; a.download = name; a.textContent = label; $('downloads').append(a);
}
function invalidate() {
  generation++; current = null; pending = null; $('persist').disabled = true; $('recover').disabled = true;
  $('receipt').textContent = ''; $('preview').textContent = ''; $('hash').textContent = '—'; $('length').textContent = '—';
  urls.forEach(url => URL.revokeObjectURL(url)); urls = []; $('downloads').replaceChildren();
}
async function display(raw, frame, operation, name, ticket) {
  const hash = await codec.sha256(raw);
  if (ticket !== generation) return;
  current = {raw, frame, operation, hash}; $('morse').value = frame; $('length').textContent = raw.length;
  $('hash').textContent = hash;
  try { $('preview').textContent = new TextDecoder('utf-8', {fatal: true}).decode(raw); }
  catch { $('preview').textContent = 'Binärdaten · unverändert als Datei verfügbar'; }
  link(raw, name, 'Originalbytes herunterladen'); link(frame, 'qikvrt-result.morse', 'Morse herunterladen', 'text/plain');
  link(JSON.stringify({schema:'qikvrt-morse-local-check/v1',bytes:raw.length,sha256:hash,
    byte_roundtrip_verified:true,durable_persisted:false,EFFECT_ACK_DONE:false},null,2), 'qikvrt-local-check.json', 'Prüfvermerk herunterladen', 'application/json');
  $('persist').disabled = !['127.0.0.1','localhost'].includes(location.hostname) || location.protocol !== 'http:';
  status('Bytegleich geprüft · noch nicht im Journal gespeichert.');
}
async function transcode(operation) {
  const text = $('text').value, frame = $('morse').value, file = $('file').files[0];
  invalidate(); const ticket = generation;
  try {
    let raw, encoded;
    if (operation === 'encode') {
      if (file && file.size > codec.MAX_BYTES) throw Error('Datei zu groß: maximal 16 KiB.');
      raw = file ? new Uint8Array(await file.arrayBuffer()) : new TextEncoder().encode(text);
      encoded = await codec.encode(raw);
    } else { raw = await codec.decode(frame); encoded = frame; }
    const roundtrip = await codec.decode(encoded);
    if (roundtrip.length !== raw.length || roundtrip.some((b,i) => b !== raw[i])) throw Error('Bytevergleich fehlgeschlagen.');
    await display(raw, encoded, operation, operation === 'encode' && file ? file.name : 'qikvrt-result.bin', ticket);
  } catch (error) { if (ticket === generation) status('Zurückgewiesen: ' + error.message, true); }
}
function headers() {
  return {'Content-Type':'application/json','Authorization':'Bearer ' + $('token').value,
    'QIKVRT-Owner':$('principal').value};
}
async function jsonFetch(url, init) {
  const r = await fetch(url,{cache:'no-store',...init}), data = await r.json();
  if (!r.ok) throw Error(data.reason || String(r.status)); return data;
}
async function recover() {
  const operation = pending, ticket = generation;
  if (!operation) throw Error('Kein gespeicherter Auftrag in dieser Seite.');
  const h = headers(); h['QIKVRT-Subject'] = JSON.stringify(operation.request.subject);
  const id = encodeURIComponent(operation.request.request_id);
  const receipt = await jsonFetch('/api/owner/morse/receipts/' + id, {headers:h});
  if (receipt.execution?.payload?.result?.payload_sha256 !== operation.hash) throw Error('Quittung gehört zu anderen Daten.');
  const download = await fetch('/api/owner/morse/download/' + id + '/data',{headers:h,cache:'no-store'});
  if (!download.ok) throw Error('Gespeicherte Daten sind nicht zurücklesbar.');
  const raw = new Uint8Array(await download.arrayBuffer());
  if (await codec.sha256(raw) !== operation.hash || raw.length !== operation.raw.length || raw.some((b,i)=>b!==operation.raw[i])) throw Error('Gespeicherte Bytes unterscheiden sich.');
  if (ticket !== generation || pending !== operation) return;
  $('receipt').textContent = JSON.stringify(receipt,null,2);
  link(raw, 'qikvrt-persisted-result.bin', 'Gespeicherte Bytes herunterladen');
  link(JSON.stringify(receipt,null,2), 'qikvrt-native-receipt.json', 'Server-Quittung herunterladen', 'application/json');
  status('Im nativen Journal gespeichert und unabhängig zurückgelesen.');
}
$('encode').addEventListener('click', () => transcode('encode'));
$('decode').addEventListener('click', () => transcode('decode'));
$('clear-file').addEventListener('click', () => { $('file').value = ''; invalidate(); });
for (const id of ['text','morse','file']) $(id).addEventListener('input', () => { invalidate(); status('Daten geändert · bitte erneut prüfen.'); });
$('frame-file').addEventListener('change', async () => {
  invalidate(); const ticket = generation, file = $('frame-file').files[0];
  if (!file) return;
  try {
    if (file.size > (codec.MAX_BYTES + 45) * 12) throw Error('Frame zu groß.');
    const text = await file.text(); if (ticket === generation) { $('morse').value = text; await transcode('decode'); }
  } catch (error) { status(error.message,true); }
});
$('persist').addEventListener('click', async () => {
  if (!current) return;
  const frozen = current, ticket = generation; $('persist').disabled = true;
  try {
    const health = await jsonFetch('/api/temdd/subject');
    const request = {schema:'qikvrt-morse-request/v1',request_id:'morse-' + crypto.randomUUID(),
      subject:health.subject,operation:frozen.operation,data:frozen.operation === 'encode' ? b64(frozen.raw) : frozen.frame};
    const h = headers(); h['Effect-Ack-Request'] = 'v=1, mode=prepare';
    const prepared = await jsonFetch('/api/owner/morse/prepare',{method:'POST',headers:h,body:JSON.stringify(request)});
    if (ticket !== generation) return;
    pending = {request,hash:frozen.hash,raw:frozen.raw}; $('recover').disabled = false;
    h['Effect-Ack-Request'] = 'v=1, mode=commit, hash=:' + btoa(String.fromCharCode(...Uint8Array.from(prepared.record_hash.match(/../g),x=>parseInt(x,16)))) + ':, token=:' + btoa(prepared.commit_token) + ':';
    await jsonFetch('/api/owner/morse/commit',{method:'POST',headers:h,body:JSON.stringify(request)});
    if (ticket === generation) await recover();
  } catch (error) {
    if (ticket !== generation) return;
    if (!pending) $('persist').disabled = false;
    status((pending ? 'Speicherantwort offen: ' : 'Nicht gespeichert: ') + error.message + (pending ? '. Vor einem neuen Auftrag die Quittung lesen.' : ''),true);
  }
});
$('recover').addEventListener('click', () => recover().catch(error => status(error.message,true)));
window.addEventListener('pagehide', () => urls.forEach(url => URL.revokeObjectURL(url)));
