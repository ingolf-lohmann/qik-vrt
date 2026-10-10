// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Separate read-only HTTP client; reuses the production replica implementation.
import {readFileSync, existsSync} from 'node:fs';
import {createHash, webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import https from 'node:https';
import {isIPv4} from 'node:net';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const require = (condition, code) => {if (!condition) throw new Error(code);};
const legacyContract = new URL('../state/deployments/MESH_MONITOR_RAILWAY_EXACT_674aa35.json', import.meta.url);
const contract = existsSync(legacyContract) ? JSON.parse(readFileSync(legacyContract)) : null;

// Optional provider-bound IPv4: reuse the same verifier without a second DNS
// resolution or inherited provider credentials. TLS CA/SNI checks stay enabled.
export function pinnedIPv4Request(origin, address) {
  const target = new URL(origin);
  require(target.protocol === 'https:' && isIPv4(address), 'HOLD_PROVIDER_HTTPS_IPV4_PIN');
  const agent = new https.Agent({lookup:(_name, options, callback) => {
    if (options.all) callback(null, [{address, family:4}]);
    else callback(null, address, 4);
  }});
  return async (url, options = {}) => {
    const next = new URL(url);
    require(next.origin === target.origin && !next.username && !next.password, 'HOLD_PINNED_READBACK_ORIGIN');
    return await new Promise((resolve, reject) => {
      const request = https.get(next, {agent, headers:options.headers, signal:options.signal}, response => {
        const chunks = []; let size = 0;
        response.on('data', chunk => {
          size += chunk.length;
          if (size > 8*1024*1024) request.destroy(new Error('HOLD_PUBLIC_RESPONSE_TOO_LARGE'));
          else chunks.push(chunk);
        });
        response.on('error', reject);
        response.on('end', () => resolve(new Response(Buffer.concat(chunks), {status:response.statusCode})));
      });
      request.setTimeout(15000, () => request.destroy(new Error('HOLD_PUBLIC_TIMEOUT')));
      request.on('error', reject);
    });
  };
}

export async function verifyClient(plan = contract, request = fetch) {
  require(plan, 'EXACT_READBACK_PLAN_REQUIRED');
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
      node.webhook_secret_configured === (plan.standalone ? plan.adapter === 'github' : true) && ['HEALTHY','DEGRADED','UNKNOWN'].includes(node.health?.state) &&
      Array.isArray(node.health?.checks), 'HOLD_PUBLIC_NODE_HEALTH_CONTRACT');
  }
  if (plan.standalone) {
    const runtime = await get('/api/runtime');
    require(runtime.schema === 'qikvrt-self-host-runtime/v1' && runtime.manifest_sha256 === plan.manifest_sha256 &&
      runtime.config_sha256 === plan.config_sha256 && runtime.node_id === plan.node_id &&
      runtime.source_head === plan.source_head && runtime.source_tree === plan.source_tree &&
      runtime.source_repository === plan.source_repository && runtime.package_version === plan.package_version &&
      runtime.monitor_version === plan.version && runtime.volume_binding_sha256 === plan.volume_binding_sha256 &&
      runtime.terminal_scope === plan.terminal_scope && runtime.public_routing_verified === false &&
      runtime.adapter === plan.adapter && JSON.stringify(runtime.runtime) === JSON.stringify(plan.runtime) &&
      JSON.stringify(Object.entries(runtime.artifact_files_sha256).sort()) === JSON.stringify(Object.entries(plan.package_files).sort()) &&
      ['reference','temdd','firefox'].includes(runtime.terminal_profile) &&
      runtime.native_terminal_daemon_available === (plan.native_terminal_daemon_included && ['temdd','firefox'].includes(runtime.terminal_profile)) && runtime.effect_ack_done === false,
      'HOLD_SELF_HOST_RUNTIME_BINDING');
    const terminal = await get('/api/terminal');
    require(terminal.manifest_sha256 === plan.manifest_sha256 && terminal.config_sha256 === plan.config_sha256 &&
      terminal.node_id === plan.node_id && terminal.public_effects === 'READ_ONLY' && terminal.effect_ack_done === false,
      'HOLD_SELF_HOST_TERMINAL_BINDING');
    if (runtime.native_terminal_daemon_available) require(terminal.state === 'NATIVE_TEMDD_READY' &&
      terminal.subject?.repository === plan.source_repository && terminal.subject?.head === plan.source_head &&
      terminal.subject?.tree === plan.source_tree && Number.isSafeInteger(terminal.subject?.pr) && terminal.subject.pr > 0 &&
      /^[a-f0-9]{32}$/.test(terminal.ledger_id || '') && terminal.public_event_bodies === false,
      'HOLD_SELF_HOST_NATIVE_SUBJECT');
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
  const local = plan.standalone ? readFileSync(resolve(plan.package_root, 'docs/monitor/client-replica.js'),'utf8') : execFileSync('git', ['show', plan.source_head + ':docs/monitor/client-replica.js'],
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
  try {
    let plan = contract;
    let request = fetch;
    if (process.argv[2] === '--self-host') {
      const [packageRoot, url, manifestPin, configPin, nodeId, adapter, ipv4Pin] = process.argv.slice(3);
      const raw = readFileSync(resolve(packageRoot, 'MANIFEST.json'));
      require(sha(raw) === manifestPin && /^[a-f0-9]{64}$/.test(configPin || '') &&
        /^[A-Za-z0-9_.:-]{1,100}$/.test(nodeId || '') && ['none','github'].includes(adapter), 'HOLD_EXPECTED_PINS_REQUIRED');
      const target = new URL(url);
      require(['http:','https:'].includes(target.protocol) && !target.username && !target.password &&
        target.pathname === '/' && !target.search && !target.hash, 'HOLD_EXACT_ORIGIN_REQUIRED');
      const m = JSON.parse(raw);
      require(m.schema === 'qikvrt-self-host-package/v1' && m.effect_ack_done === false, 'HOLD_MANIFEST_SCHEMA');
      const volume = {schema:'qikvrt-self-host-volume/v1',node_id:nodeId,manifest_sha256:manifestPin,
        config_sha256:configPin,source_head:m.source_head,source_tree:m.source_tree};
      plan = {standalone:true,package_root:packageRoot,public_url:target.origin,manifest_sha256:manifestPin,
        package_version:m.package_version,terminal_scope:m.terminal_scope,native_terminal_daemon_included:m.native_terminal_daemon_included === true,
        volume_binding_sha256:sha(JSON.stringify(volume,Object.keys(volume).sort(),2)+'\n'),
        config_sha256:configPin,node_id:nodeId,adapter,runtime:m.runtime,source_repository:m.source_repository,
        source_head:m.source_head,source_tree:m.source_tree,version:'2026-10-04.9',
        package_files:Object.fromEntries(Object.entries(m.files).map(([p,e])=>[p,e.sha256])),
        artifact_files_sha256:Object.fromEntries(['server.mjs','observer.mjs','index.html','client-replica.js','health-projection.js','package.json'].map(p=>[p,m.files['docs/monitor/'+p].sha256]))};
      if (ipv4Pin) request = pinnedIPv4Request(plan.public_url, ipv4Pin);
    }
    console.log(JSON.stringify(await verifyClient(plan, request)));
  }
  catch (_) { console.log(JSON.stringify({state:'HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK',effect_ack_done:false})); process.exitCode=20; }
}
