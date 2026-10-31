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
class ReadbackGuardError extends Error {}
const require = (condition, code) => {if (!condition) throw new ReadbackGuardError(code);};
export function requireMeshWorkReadback(node) {
  require(node.mesh_work?.state==='PEER_BATCHES_DURABLE' && Number.isSafeInteger(node.mesh_work.admitted_peers) &&
    node.mesh_work.admitted_peers>0 && node.mesh_work.received_peers===node.mesh_work.admitted_peers &&
    node.mesh_work.proposal_execution==='NOT_EXECUTED' && node.mesh_work.effect_ack_done===false,
    'HOLD_PUBLIC_MESH_PEER_BATCH_REQUIRED');
}
export function readbackFailure(error) {
  return {state:'HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK',
    cause:error instanceof ReadbackGuardError ? error.message : 'READBACK_UNCLASSIFIED_ERROR',
    effect_ack_done:false};
}
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

function publicReader(plan, request, observations = [], maxBytes = 8*1024*1024) {
  return async function get(path, text = false) {
    const response = await request(plan.public_url + path, {redirect:'error', cache:'no-store', signal:AbortSignal.timeout(15000), headers:{'cache-control':'no-cache'}});
    require(response.status === 200, 'HOLD_PUBLIC_HTTP');
    const chunks = []; let size = 0;
    for await (const chunk of response.body) {
      size += chunk.length; require(size <= maxBytes, 'HOLD_PUBLIC_RESPONSE_TOO_LARGE'); chunks.push(chunk);
    }
    const bytes = Buffer.concat(chunks);
    observations.push({path, status:response.status, bytes:bytes.length, sha256:sha(bytes), observed_at:new Date().toISOString()});
    return text ? bytes.toString('utf8') : JSON.parse(bytes.toString('utf8'));
  };
}

export async function verifyEapPublic(plan, request = fetch) {
  require(plan?.public_url === 'https://raumzeitterminal.de', 'HOLD_EXACT_EAP_HTTPS_ORIGIN');
  const subject = plan.native_subject;
  require(subject?.repository === plan.source_repository && subject?.head === plan.source_head &&
    subject?.tree === plan.source_tree && /^[a-f0-9]{40}$/.test(subject.head || '') &&
    /^[a-f0-9]{40}$/.test(subject.tree || '') && Number.isSafeInteger(subject.pr) && subject.pr > 0,
    'HOLD_EXPECTED_EAP_NATIVE_SUBJECT');
  const observations = [];
  const get = publicReader(plan, request, observations, 32768);
  const discovery = await get('/.well-known/effect-ack');
  const capabilities = await get('/api/eap/capabilities');
  const state = await get('/api/eap/state');
  const supportsV1 = value => value?.message_type === 'effect-ack-capabilities' &&
    Array.isArray(value.supported_versions) && value.supported_versions.length === 1 && value.supported_versions[0] === 1;
  const specification = 'https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03';
  const effectScope = 'ORIGINAL_OWNER_REST_DURABLE_TERMINAL_INPUT';
  require(supportsV1(capabilities) && supportsV1(discovery?.core) &&
    JSON.stringify(discovery.versions) === '[1]' && JSON.stringify(discovery.modes) === '["prepare","commit"]' &&
    discovery.specification === specification && discovery.effect_scope === effectScope &&
    discovery.effect_endpoint === '/api/eap/effect' && discovery.record_template === '/api/eap/records/{sha256}' &&
    discovery.authentication === 'EXISTING_OWNER_REST_BEARER_AND_QIKVRT_OWNER' && discovery.ordinary_release === false,
    'HOLD_EAP_PUBLIC_DISCOVERY_CONTRACT');
  require(state?.schema === 'qikvrt_eap_http_status_v1' && state.state === 'NATIVE_EAP_HTTP_READY' &&
    state.specification === specification && state.effect_scope === effectScope &&
    state.ordinary_release === false && state.effect_ack_done === false &&
    Object.keys(subject).length === Object.keys(state.subject || {}).length &&
    Object.entries(subject).every(([key, value]) => state.subject?.[key] === value),
    'HOLD_EAP_PUBLIC_NATIVE_SUBJECT');
  return {state:'PUBLIC_EAP_DISCOVERY_AND_SUBJECT_VERIFIED', subject, observations,
    scope:'PUBLIC_GET_ONLY; NOT_AUTHENTICATED_PREPARE_COMMIT_RECEIPT_OR_PEER_DELIVERY',
    authenticated_input_acceptance_verified:false, effect_ack_done:false};
}

export async function verifyClient(plan = contract, request = fetch) {
  require(plan, 'EXACT_READBACK_PLAN_REQUIRED');
  const get = publicReader(plan, request);
  let nativeSubject;
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
    if (plan.standalone && new URL(plan.public_url).hostname==='raumzeitterminal.de') requireMeshWorkReadback(node);
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
    if (plan.repository_roles) require(JSON.stringify(runtime.repository_roles) === JSON.stringify(plan.repository_roles),
      'HOLD_PUBLIC_REPOSITORY_ROLE_BINDING');
    if (plan.owner_identity) require(runtime.network_name === plan.owner_identity.network_name &&
      runtime.principal === plan.owner_identity.principal && JSON.stringify(runtime.owner_roles) === JSON.stringify(plan.owner_identity.owner_roles),
      'HOLD_PUBLIC_OWNER_IDENTITY_BINDING');
    const terminal = await get('/api/terminal');
    require(terminal.manifest_sha256 === plan.manifest_sha256 && terminal.config_sha256 === plan.config_sha256 &&
      terminal.node_id === plan.node_id && terminal.public_effects === 'READ_ONLY' && terminal.effect_ack_done === false,
      'HOLD_SELF_HOST_TERMINAL_BINDING');
    if (runtime.native_terminal_daemon_available) require(terminal.state === 'NATIVE_TEMDD_READY' &&
      terminal.subject?.repository === plan.source_repository && terminal.subject?.head === plan.source_head &&
      terminal.subject?.tree === plan.source_tree && Number.isSafeInteger(terminal.subject?.pr) && terminal.subject.pr > 0 &&
      /^[a-f0-9]{32}$/.test(terminal.ledger_id || '') && terminal.public_event_bodies === false,
      'HOLD_SELF_HOST_NATIVE_SUBJECT');
    nativeSubject = terminal.subject;
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
  const eapPublic = plan.require_eap_http ? await verifyEapPublic({...plan, native_subject:nativeSubject}, request) : null;
  return {schema:'qikvrt-monitor-independent-client-readback/v1', state:'CLIENT_BYTE_READBACK_VERIFIED',
    public_url:plan.public_url, source_head:after.source_head, source_tree:after.source_tree,
    node_observed_at:after.observed_at, readback_observed_at:new Date().toISOString(),
    artifact_files_sha256:after.artifact_files_sha256, client_id:replica.id, epoch:after.epoch,
    sequence:replica.sequence, digest:replica.digest, event_sequence:replica.event_sequence,
    journal_head_digest:replica.event_digest, health_state:after.health.state,
    health_checks:after.health.checks.map(check=>({id:check.id,state:check.state})),
    webhook_registration:after.webhook_registration,
    ...(eapPublic ? {eap_public:eapPublic} : {}),
    scope:'Fresh HTTP health/source and snapshot/full-journal validation by a separate client process. No provider delivery, streaming continuity or whole-system-health inference.',
    effect_ack_done:false};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    let plan = contract;
    let request = fetch;
    if (process.argv[2] === '--self-host') {
      const arguments_ = process.argv.slice(3);
      const requireEapHttp = arguments_.includes('--require-eap-http');
      const positional = arguments_.filter(value => value !== '--require-eap-http');
      require(positional.length >= 6 && positional.length <= 7 &&
        arguments_.length === positional.length + Number(requireEapHttp), 'HOLD_READBACK_ARGUMENTS');
      const [packageRoot, url, manifestPin, configPin, nodeId, adapter, ipv4Pin] = positional;
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
      plan = {standalone:true,require_eap_http:requireEapHttp,package_root:packageRoot,public_url:target.origin,manifest_sha256:manifestPin,
        package_version:m.package_version,terminal_scope:m.terminal_scope,native_terminal_daemon_included:m.native_terminal_daemon_included === true,
        volume_binding_sha256:sha(JSON.stringify(volume,Object.keys(volume).sort(),2)+'\n'),
        config_sha256:configPin,node_id:nodeId,adapter,runtime:m.runtime,source_repository:m.source_repository,
        source_head:m.source_head,source_tree:m.source_tree,version:'2026-10-04.9',
        package_files:Object.fromEntries(Object.entries(m.files).map(([p,e])=>[p,e.sha256])),
        artifact_files_sha256:Object.fromEntries(['server.mjs','observer.mjs','index.html','client-replica.js','health-projection.js','package.json'].map(p=>[p,m.files['docs/monitor/'+p].sha256]))};
      if (ipv4Pin) request = pinnedIPv4Request(plan.public_url, ipv4Pin);
      if (m.files['policy/CANONICAL_UPSTREAM_REMOTE_V1.json']) {
        const bytes=readFileSync(resolve(packageRoot,'policy/CANONICAL_UPSTREAM_REMOTE_V1.json'));
        require(sha(bytes)===m.files['policy/CANONICAL_UPSTREAM_REMOTE_V1.json'].sha256,'HOLD_ROLE_POLICY_BYTES');
        const roles=JSON.parse(bytes);
        require(roles.canonical_upstream.role==='AUTHORITY' && roles.mirror.role==='MIRROR' &&
          roles.canonical_upstream.repository===m.source_repository,'HOLD_ROLE_POLICY_CONTRACT');
        plan.repository_roles={authority_repository:roles.canonical_upstream.repository,mirror_repository:roles.mirror.repository,
          role_policy_sha256:sha(bytes),native_activation_inferred:false};
        const ownerBytes=readFileSync(resolve(packageRoot,'policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json'));
        require(sha(ownerBytes)===m.files['policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json'].sha256,'HOLD_OWNER_POLICY_BYTES');
        const owner=JSON.parse(ownerBytes).mesh_authority;
        require(owner.authority_repository===roles.canonical_upstream.repository,'HOLD_OWNER_ROLE_PROJECTION');
        plan.owner_identity={network_name:owner.network_name,principal:owner.human.name,owner_roles:owner.human.roles};
      }
    }
    console.log(JSON.stringify(await verifyClient(plan, request)));
  }
  catch (error) { console.log(JSON.stringify({state:'HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK',
    reason:/^[A-Z][A-Z0-9_]{1,120}$/.test(error.message || '') ? error.message : 'INDEPENDENT_READBACK_EXECUTION_ERROR',
    effect_ack_done:false})); process.exitCode=20; }
}
