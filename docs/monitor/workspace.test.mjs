// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {createHash, webcrypto} from 'node:crypto';
const hash = value => createHash('sha256').update(value).digest('hex');
const version = 'workspace-test-v1', head = 'a'.repeat(40), tree = 'b'.repeat(40);
function fixture() {
  const activity = {schema:'qikvrt-public-activity/v1', version, repositories:[], generated_at:new Date().toISOString()};
  const digest = hash(JSON.stringify(activity));
  activity.replication = {node_id:'fixture:node', epoch:'fixture-epoch', sequence:1, digest, source_head:head, source_tree:tree};
  const node = {schema:'qikvrt-monitor-binding/v1', node_id:'fixture:node', version, epoch:'fixture-epoch', sequence:1, digest,
    source_head:head, source_tree:tree, source_repository:'ingolf-lohmann/qik-vrt', event_sequence:0, journal_head_digest:'0'.repeat(64)};
  const runtime = {schema:'qikvrt-self-host-runtime/v1', source_repository:'ingolf-lohmann/qik-vrt', source_head:head, source_tree:tree,
    node_id:'fixture:node', monitor_version:version, manifest_sha256:'c'.repeat(64), config_sha256:'d'.repeat(64),
    repository_roles:{authority_repository:'ingolf-lohmann/qik-vrt', mirror_repository:'Goldkelch/qik-vrt'}};
  const native = {schema:'qikvrt_eap_http_status_v1', state:'NATIVE_EAP_HTTP_READY', subject:{repository:'ingolf-lohmann/qik-vrt', head, tree, pr:457}, ordinary_release:false, effect_ack_done:false};
  return {'/api/runtime':runtime, '/api/node':node, '/api/activity':activity, '/api/eap/state':native};
}
function setup(values = fixture(), onRequest = () => {}) {
  let clock = Date.now(), failure = null, stream;
  const calls = [];
  class Stream {
    constructor(path) {assert.match(path, /^\/api\/stream(?:\?epoch=[^&]+&after=[0-9]+)?$/); stream = this; this.path = path; this.listeners = {};}
    addEventListener(name, fn) {this.listeners[name] = fn;}
    emit(name, data) {return this.listeners[name]({data:JSON.stringify(data)});}
    close() {this.closed = true;}
  }
  const context = {crypto:webcrypto, TextEncoder, URL, atob, AbortSignal, Date, console};
  vm.createContext(context);
  for (const name of ['client-replica.js', 'workspace-client.js']) vm.runInContext(readFileSync(new URL('./' + name, import.meta.url), 'utf8'), context);
  const client = context.QikvrtWorkspace.create({version, now:() => clock, EventSource:Stream, fetch:async (path, options) => {
    calls.push({path, options});
    onRequest(path, values);
    if (failure === path) return new Response(JSON.stringify({error:'ORIGINAL_ROUTE_UNAVAILABLE'}), {status:503, headers:{'content-type':'application/json'}});
    return new Response(JSON.stringify(values[path]), {headers:{'content-type':'application/json'}});
  }});
  return {client, context, values, calls, stream:() => stream, fail:path => {failure=path;}, age:ms => {clock += ms;}};
}
test('same-subject S1, digest-checked replica and native EAP connect without granting workspace access', async () => {
  const s = setup(); await s.client.start();
  const v = s.client.view(); assert.equal(v.verified, true); assert.equal(v.native.subject.head, head);
  assert.equal(v.workspace_membership, 'UNVERIFIED'); assert.equal(v.license_acceptance, 'UNVERIFIED');
  assert.equal(v.access_release, 'HOLD'); assert.equal(v.effect_ack_done, false);
  assert.deepEqual(s.calls.map(c => c.path), ['/api/runtime','/api/activity','/api/eap/state','/api/node']);
  for (const c of s.calls) {assert.equal(c.options.method, 'GET'); assert.equal(c.options.credentials, 'same-origin'); assert.equal(c.options.cache, 'no-store');}
  s.client.stop(); assert.equal(s.stream().closed, true);
});
for (const [name, mutate] of [
  ['wrong Authority', v => {v['/api/runtime'].source_repository='Goldkelch/qik-vrt';}],
  ['wrong Mirror', v => {v['/api/runtime'].repository_roles.mirror_repository='ingolf-lohmann/qik-vrt';}],
  ['wrong head', v => {v['/api/eap/state'].subject.head='e'.repeat(40);}],
  ['wrong tree', v => {v['/api/node'].source_tree='e'.repeat(40);}],
  ['wrong node', v => {v['/api/node'].node_id='different:node';}],
  ['wrong version', v => {v['/api/activity'].version='different';}],
  ['corrupt snapshot', v => {v['/api/activity'].repositories.push({name:'altered'});}],
  ['missing manifest', v => {delete v['/api/runtime'].manifest_sha256;}],
  ['global DONE inflation', v => {v['/api/eap/state'].effect_ack_done=true;}],
  ['unreplayed events', v => {v['/api/node'].event_sequence=1;}],
  ['wrong journal checkpoint', v => {v['/api/node'].journal_head_digest='e'.repeat(64);}]
]) test(name + ' holds native work', async () => {
  const s = setup(); mutate(s.values); await s.client.read();
  assert.equal(s.client.view().verified, false); assert.equal(s.client.view().native, null); assert.ok(s.client.view().reason);
});
test('a failed checker revokes native readiness, retains its last observation and recovers after route repair', async () => {
  const s = setup(); await s.client.read(); const old = s.client.view();
  s.fail('/api/eap/state'); await s.client.read();
  assert.equal(s.client.view().verified, false); assert.equal(s.client.view().native, null);
  assert.equal(s.client.view().activity.generated_at, old.activity.generated_at);
  s.fail(null); await s.client.read(); assert.equal(s.client.view().verified, true);
});
test('a fresh SSE heartbeat never renews expired native readback or repairs failed verification', async () => {
  const s = setup(); await s.client.start(); const observed = s.client.view().observed_at;
  s.age(45001); await s.stream().emit('node', s.values['/api/node']);
  assert.equal(s.client.view().verified, false); assert.equal(s.client.view().reason, 'READBACK_EXPIRED');
  assert.equal(s.client.view().observed_at, observed);
  s.stream().onerror(); s.stream().onopen(); assert.equal(s.client.view().native, null);
  await s.client.read(); assert.equal(s.client.view().verified, true);
});
test('original event bytes must reach the declared journal checkpoint before native work', async () => {
  const s = setup(); const raw = Buffer.from('{"source":"fixture"}');
  const record = {event_sequence:1, previous_digest:'0'.repeat(64), payload_base64:raw.toString('base64'), payload_sha256:hash(raw)};
  const digest = hash(JSON.stringify(record));
  s.values['/api/node'].event_sequence = 1; s.values['/api/node'].journal_head_digest = digest;
  await s.client.start(); assert.equal(s.client.view().verified, false);
  const event = {...record, record_digest:digest, epoch:'fixture-epoch'};
  await s.stream().emit('delivery', event); assert.equal(s.client.view().verified, true);
  await s.stream().emit('delivery', {...event, payload_base64:Buffer.from('altered').toString('base64')});
  assert.equal(s.client.view().verified, false); assert.equal(s.client.view().native, null);
});
test('access declaration preserves original-byte identity and distinct license files', () => {
  const access = JSON.parse(readFileSync(new URL('./workspace-access.json', import.meta.url)));
  const original = readFileSync(new URL('./workspace-original.html', import.meta.url));
  assert.equal(original.length, access.original.bytes); assert.equal(hash(original), access.original.sha256);
  assert.equal(access.workspace.membership, 'UNVERIFIED'); assert.equal(access.workspace.access_release, 'HOLD');
  for (const l of access.licenses) assert.equal(hash(readFileSync(new URL('../../' + l.path, import.meta.url))), l.sha256);
  for (const name of ['workspace-react.js','workspace-client.js']) {
    const code = readFileSync(new URL('./' + name, import.meta.url), 'utf8'); new vm.Script(code);
    assert(!/setInterval\s*\(|setTimeout\s*\(|localStorage|sessionStorage|dangerouslySetInnerHTML/.test(code));
  }
});
test('a missing event reopens only the original cursor route and suppresses unchanged gap retries', async () => {
  const s = setup(); await s.client.start();
  const first = s.stream(), gap = {event_sequence:2, epoch:'fixture-epoch'};
  await first.emit('delivery', gap);
  const recovery = s.stream(); assert.notEqual(recovery, first); assert.equal(first.closed, true);
  assert.equal(recovery.path, '/api/stream?epoch=fixture-epoch&after=0');
  await recovery.emit('delivery', gap); assert.equal(s.stream(), recovery);
  assert.equal(s.client.view().verified, false);
});
test('cold activity observation precedes its independent node checkpoint', async () => {
  const values = fixture(); values['/api/node'].sequence = 0;
  const s = setup(values, (path, current) => {if (path === '/api/activity') current['/api/node'].sequence = 1;});
  await s.client.read(); assert.equal(s.client.view().verified, true, s.client.view().reason);
});
