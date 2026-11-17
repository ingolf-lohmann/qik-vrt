// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Browser adapter bytes executed against the real cold-exported local S1 process.
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {webcrypto, createHash} from 'node:crypto';
const base = process.argv[2];
assert.match(base || '', /^http:\/\/127\.0\.0\.1:[0-9]+$/);
const calls = [], hash = bytes => createHash('sha256').update(bytes).digest('hex');
const runtime = await (await fetch(base + '/api/runtime')).json();
const sandbox = {crypto:webcrypto, TextEncoder, URL, atob, AbortSignal, Date};
vm.createContext(sandbox);
for (const [url, path] of [['/client-replica.js','docs/monitor/client-replica.js'], ['/assets/js/qikvrt-workspace-client.js','docs/monitor/workspace-client.js']]) {
  const response = await fetch(base + url); assert.equal(response.status, 200);
  const bytes = Buffer.from(await response.arrayBuffer());
  assert.equal(hash(bytes), runtime.artifact_files_sha256[path]);
  vm.runInContext(bytes.toString('utf8'), sandbox);
}
const client = sandbox.QikvrtWorkspace.create({version:runtime.monitor_version, EventSource:null, fetch:async (path, options) => {
  calls.push({path, method:options.method}); return fetch(base + path, options);
}});
await client.start(); const state = client.view();
assert.equal(state.verified, true, state.reason);
assert.equal(state.native.subject.head, runtime.source_head);
assert.equal(state.native.subject.tree, runtime.source_tree);
assert.equal(state.workspace_membership, 'UNVERIFIED'); assert.equal(state.license_acceptance, 'UNVERIFIED');
assert.equal(state.access_release, 'HOLD'); assert.equal(state.effect_ack_done, false);
assert.equal(calls.length, 4); assert(calls.every(c => c.method === 'GET'));
const original = Buffer.from(await (await fetch(base + '/workspace/original.html')).arrayBuffer());
const access = await (await fetch(base + '/workspace/access.json')).json();
assert.equal(hash(original), access.original.sha256);
assert.equal(hash(original), runtime.artifact_files_sha256['docs/monitor/workspace-original.html']);
client.stop();
console.log('WORKSPACE_EXPORTED_CLIENT_PASS: exact served adapter bytes, real four-route S1/EAP readback, source binding, preserved original, workspace HOLD. No desktop-browser or public-host claim.');
