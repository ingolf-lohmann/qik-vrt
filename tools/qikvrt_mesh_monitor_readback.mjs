// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Separate read-only HTTP client; reuses the production replica implementation.
import {readFileSync} from 'node:fs';
import {createHash, webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const require = (condition, code) => {if (!condition) throw new Error(code);};
const contract = JSON.parse(readFileSync(new URL('../state/deployments/MESH_MONITOR_RAILWAY_EXACT_674aa35.json', import.meta.url)));

export async function verifyClient(plan = contract, request = fetch) {
  async function get(path, text = false) {
    const response = await request(plan.public_url + path, {redirect:'error', cache:'no-store', signal:AbortSignal.timeout(15000), headers:{'cache-control':'no-cache'}});
    require(response.status === 200, 'HOLD_PUBLIC_HTTP');
    const chunks = []; let size = 0;
    for await (const chunk of response.body) {
      size += chunk.length; require(size <= 8*1024*1024, 'HOLD_PUBLIC_RESPONSE_TOO_LARGE'); chunks.push(chunk);
    }
    const bytes = Buffer.concat(chunks);
    return text ? bytes.toString('utf8') : JSON.parse(bytes.toString('utf8'));
  }
  function binding(node) {
    const observed = Date.parse(node.observed_at);
    require(Number.isFinite(observed) && Math.abs(Date.now()-observed) <= 120000, 'HOLD_PUBLIC_OBSERVATION_NOT_FRESH');
    require(node.schema === 'qikvrt-monitor-binding/v1' && node.node_id === plan.node_id &&
      node.source_repository === plan.source_repository && node.source_head === plan.source_head &&
      node.source_tree === plan.source_tree && node.version === plan.version, 'HOLD_PUBLIC_SOURCE_BINDING');
    require(JSON.stringify(Object.entries(node.artifact_files_sha256).sort()) === JSON.stringify(Object.entries(plan.artifact_files_sha256).sort()), 'HOLD_PUBLIC_ARTIFACT_BINDING');
    require(node.snapshot_durable === true && node.operation_error === null && node.periodic_polling === false &&
      node.webhook_secret_configured === true && ['HEALTHY','DEGRADED','UNKNOWN'].includes(node.health?.state) &&
      Array.isArray(node.health?.checks), 'HOLD_PUBLIC_NODE_HEALTH_CONTRACT');
  }
  const health = await get('/health'); binding(health);
  const node = await get('/api/node'); binding(node);
  require(health.epoch === node.epoch, 'HOLD_PUBLIC_EPOCH_CHANGED');
  const code = await get('/client-replica.js', true);
  const projection = await get('/health-projection.js', true);
  require(sha(code) === plan.artifact_files_sha256['client-replica.js'] &&
    sha(projection) === plan.artifact_files_sha256['health-projection.js'], 'HOLD_PUBLIC_CLIENT_BYTES');
  // The executor can advance while the owner-authorized runtime stays pinned.
  // Resolve that runtime's original client from its Git object, not from HEAD.
  require(/^[a-f0-9]{40}$/.test(plan.source_head), 'HOLD_CLIENT_SOURCE_COMMIT');
  const local = execFileSync('git', ['show', plan.source_head + ':docs/monitor/client-replica.js'],
    {cwd:fileURLToPath(new URL('../',import.meta.url)),encoding:'utf8',timeout:30000,maxBuffer:1024*1024});
  require(sha(local) === plan.artifact_files_sha256['client-replica.js'], 'HOLD_LOCAL_CLIENT_BYTES');
  const storage = new Map();
  const context = {crypto:webcrypto, TextEncoder, Uint8Array, atob, Date,
    sessionStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)}};
  vm.createContext(context); vm.runInContext(local, context);
  const replica = context.QikvrtReplica.create({version:plan.version});
  replica.observe(node);
  const snapshot = await get('/api/activity');
  require(snapshot.replication?.source_head === plan.source_head && snapshot.replication?.source_tree === plan.source_tree, 'HOLD_SNAPSHOT_SOURCE_BINDING');
  require((await replica.accept(snapshot)).accepted, 'HOLD_CLIENT_SNAPSHOT_REJECTED');
  const replay = await get('/api/events?after=0');
  require(replay.epoch === replica.epoch && replay.after === 0 && replay.event_sequence === replay.events.length, 'HOLD_CLIENT_REPLAY_SHAPE');
  for (const event of replay.events) require((await replica.acceptEvent({...event,epoch:replay.epoch})).accepted, 'HOLD_CLIENT_EVENT_REJECTED');
  const after = await get('/api/node'); binding(after);
  require(after.epoch === replica.epoch && after.node_id === replica.node_id && after.sequence === replica.sequence &&
    after.digest === replica.digest && after.event_sequence === replica.event_sequence && after.journal_head_digest === replica.event_digest,
    'HOLD_READBACK_CHANGED_OR_CLIENT_DIFFERS');
  return {schema:'qikvrt-monitor-independent-client-readback/v1', state:'CLIENT_BYTE_READBACK_VERIFIED',
    public_url:plan.public_url, source_head:after.source_head, source_tree:after.source_tree,
    node_observed_at:after.observed_at, readback_observed_at:new Date().toISOString(),
    artifact_files_sha256:after.artifact_files_sha256, client_id:replica.id, epoch:after.epoch,
    sequence:replica.sequence, digest:replica.digest, event_sequence:replica.event_sequence,
    journal_head_digest:replica.event_digest, health_state:after.health.state,
    health_checks:after.health.checks.map(check=>({id:check.id,state:check.state})),
    webhook_registration:after.webhook_registration,
    scope:'Fresh HTTP health/source and snapshot/full-journal validation by a separate client process. No provider delivery, streaming continuity or whole-system-health inference.',
    effect_ack_done:false};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { console.log(JSON.stringify(await verifyClient())); }
  catch (_) { console.log(JSON.stringify({state:'HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK',effect_ack_done:false})); process.exitCode=20; }
}
