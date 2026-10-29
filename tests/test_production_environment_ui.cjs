// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
'use strict';
// Simulated DOM/network only; no live user authentication or production effect.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../personal/ingolf-lohmann/firefox-assistant/authority.js'), 'utf8');
async function scenario(lost) {
  const nodes = new Map(), events = {}, calls = [], popup = {};
  const node = id => { if (!nodes.has(id)) nodes.set(id, {textContent: '', disabled: false}); return nodes.get(id); };
  let applyCount = 0;
  const tick = () => new Promise(resolve => setImmediate(resolve));
  const sandbox = {document: {getElementById: node}, location: {origin: 'http://127.0.0.1:8766'},
    window: {open: () => popup, addEventListener: (type, fn) => events[type] = fn},
    URLSearchParams, crypto: {randomUUID: () => 'fixture-request'},
    fetch: async (path, options) => {
      calls.push([path, options]);
      let value;
      if (path.endsWith('/start')) value = {state: 'fixture-state', authorization_url: 'https://idp.example.test/authorize'};
      else if (path.endsWith('/status')) value = {state: 'AUTHENTICATED'};
      else if (path.endsWith('/logout')) value = {local_logout: true};
      else if (options.method === 'POST') { applyCount++; if (lost) throw Error('LOST_REPLY'); value = {state: 'UPLOAD_ACKNOWLEDGED_METADATA_READBACK_VERIFIED'}; }
      else value = {request_id: 'fixture-request', expected_main_sha: '1'.repeat(40), binding_sha256: 'a'.repeat(64), implementation_source_verified: true, prior_attempt_state: lost && applyCount ? 'UNKNOWN_READBACK_REQUIRED' : 'NOT_ATTEMPTED'};
      return {ok: true, json: async () => value};
    }};
  vm.createContext(sandbox); vm.runInContext(source, sandbox);
  node('login').onclick(); await tick();
  for (const [origin, from, state] of [['https://evil.test', popup, 'fixture-state'], [sandbox.location.origin, {}, 'fixture-state'], [sandbox.location.origin, popup, 'wrong-state']]) {
    events.message({origin, source: from, data: {type: 'qikvrt-oidc-result', state, token: 'UNTRUSTED'}});
  }
  await tick(); assert(node('inspect').disabled, 'foreign origin/window/state cannot obtain an authenticated UI');
  events.message({origin: sandbox.location.origin, source: popup, data: {type: 'qikvrt-oidc-result', state: 'fixture-state', token: 'FIXTURE_ONLY_BEARER'}});
  await tick(); assert.equal(node('inspect').disabled, false);
  await node('inspect').onclick(); assert.equal(node('apply').disabled, false);
  await node('apply').onclick(); assert.equal(applyCount, 1); assert(node('apply').disabled);
  if (lost) { await node('inspect').onclick(); assert(node('apply').disabled, 'unresolved handoff remains readback-only'); }
  await node('logout').onclick(); assert(node('inspect').disabled);
  assert(calls.every(([path, options]) => path.startsWith('/') && !path.startsWith('//') && options.redirect === 'error'));
  const mutation = calls.find(([path, options]) => path.endsWith('/production-environment') && options.method === 'POST');
  assert(mutation); assert.deepEqual(Object.keys(JSON.parse(mutation[1].body)).sort(), ['binding_sha256', 'effect_accepted', 'expected_main_sha', 'request_id', 'schema']);
  assert(!source.includes('localStorage')); assert(!source.includes('setInterval'));
}
(async () => { await scenario(false); await scenario(true); console.log('PASS: Authority SSO UI origin/state/window binding, one upload, lost-reply readback, logout'); })().catch(error => {console.error(error); process.exitCode=1;});
