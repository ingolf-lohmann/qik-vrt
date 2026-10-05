// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Extends the existing docs/monitor carrier; no repository mutation route.
import http from 'node:http';
import {createHash, createHmac, timingSafeEqual, randomUUID} from 'node:crypto';
import {readFileSync, mkdirSync, openSync, closeSync, writeFileSync, renameSync, fsyncSync, existsSync, unlinkSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import observer, {snapshot, configureRepositories, invalidateRepository, SECURITY} from './observer.mjs';
import './health-projection.js';

export const VERSION = '2026-10-04.9';
const MAX_BODY = 2 * 1024 * 1024;
const MAX_REPLICATION_BODY = 8 * MAX_BODY;
const ZERO_DIGEST = '0'.repeat(64);
const sha256 = value => createHash('sha256').update(value).digest('hex');
const iso = () => new Date().toISOString();

function validateEvent(event, sequence, previous) {
  const record = {...event}; delete record.record_digest;
  if (event.event_sequence !== sequence || event.previous_digest !== previous ||
      typeof event.payload_base64 !== 'string' ||
      Buffer.from(event.payload_base64, 'base64').toString('base64') !== event.payload_base64 ||
      sha256(Buffer.from(event.payload_base64, 'base64')) !== event.payload_sha256 ||
      sha256(JSON.stringify(record)) !== event.record_digest) throw new Error('DURABLE_EVENT_JOURNAL_MISMATCH');
}

// Bind the HMAC to the operation as well as the exact wire bytes. Secrets never
// enter the journal. This authenticates configured peers, not natural persons.
export function replicationSignature(raw, method, path, secret) {
  return 'sha256=' + createHmac('sha256', secret).update(method + '\n' + path + '\n').update(raw).digest('hex');
}
function verifyReplication(raw, signature, method, path, secret) {
  if (!secret || !/^sha256=[a-f0-9]{64}$/.test(signature || '')) return false;
  return timingSafeEqual(Buffer.from(signature.slice(7), 'hex'),
    Buffer.from(replicationSignature(raw, method, path, secret).slice(7), 'hex'));
}

async function readBody(request, limit) {
  const chunks = []; let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > limit) throw new Error('PAYLOAD_TOO_LARGE');
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

export class MonitorStore {
  constructor(path, nodeId) {
    this.path = path; this.nodeId = nodeId;
    this.state = {schema: 'qikvrt-monitor-node/v1', node_id: nodeId, epoch: randomUUID(), sequence: 0, snapshot: null, digest: null, deliveries: [], last_delivery: null};
    if (existsSync(path)) {
      const prior = JSON.parse(readFileSync(path, 'utf8'));
      if (prior.schema !== this.state.schema || prior.node_id !== nodeId || !Number.isSafeInteger(prior.sequence) ||
          (prior.snapshot && sha256(JSON.stringify(prior.snapshot)) !== prior.digest)) throw new Error('DURABLE_MONITOR_STATE_MISMATCH');
      if (!Array.isArray(prior.deliveries) || prior.sequence < 0 || typeof prior.epoch !== 'string') throw new Error('DURABLE_MONITOR_STATE_MISMATCH');
      let previous = ZERO_DIGEST; const ids = new Set();
      for (const [index, event] of prior.deliveries.entries()) {
        validateEvent(event, index + 1, previous);
        if (ids.has(event.id)) throw new Error('DURABLE_EVENT_JOURNAL_MISMATCH');
        ids.add(event.id);
        previous = event.record_digest;
      }
      if (prior.confirmed && (!Number.isSafeInteger(prior.confirmed.event_sequence) || prior.confirmed.event_sequence < 0 ||
          prior.confirmed.event_sequence > prior.deliveries.length ||
          (prior.deliveries[prior.confirmed.event_sequence - 1]?.record_digest || ZERO_DIGEST) !== prior.confirmed.journal_head_digest ||
          (prior.confirmed.snapshot && sha256(JSON.stringify(prior.confirmed.snapshot)) !== prior.confirmed.digest) ||
          !Number.isSafeInteger(prior.confirmed.sequence) || prior.confirmed.sequence < 0 || prior.confirmed.sequence > prior.sequence)) throw new Error('DURABLE_REPLICA_RECEIPT_MISMATCH');
      this.state = prior;
    }
  }
  persist() {
    mkdirSync(dirname(this.path), {recursive: true, mode: 0o700});
    const temporary = this.path + '.tmp-' + randomUUID();
    try {
      const fd = openSync(temporary, 'wx', 0o600);
      try { writeFileSync(fd, JSON.stringify(this.state) + '\n'); fsyncSync(fd); }
      finally { closeSync(fd); }
      renameSync(temporary, this.path);
      const directory = openSync(dirname(this.path), 'r');
      try { fsyncSync(directory); } finally { closeSync(directory); }
    } catch (error) {
      // A rename followed by failed directory fsync has an ambiguous durable
      // outcome. No more writes/positive receipts until disk is re-read.
      this.storageFailed = true;
      try { unlinkSync(temporary); } catch (_) {}
      throw error;
    }
  }
  update(value, delivery = null) {
    if (this.state.journal_source_node_id) throw new Error('REPLICA_READ_ONLY');
    if (this.storageFailed) throw new Error('STORAGE_RESTART_REQUIRED');
    if (delivery) {
      const existing = this.state.deliveries.find(item => item.id === delivery.id);
      if (existing) {
        if (existing.payload_sha256 !== delivery.payload_sha256) throw new Error('DUPLICATE_DELIVERY_CONTENT_MISMATCH');
        return false;
      }
    }
    const digest = sha256(JSON.stringify(value));
    if (digest === this.state.digest && !delivery) return false;
    const previous = this.state;
    let record = null;
    if (delivery) {
      record = {...delivery, event_sequence: previous.deliveries.length + 1,
        previous_digest: previous.deliveries.at(-1)?.record_digest || ZERO_DIGEST};
      record.record_digest = sha256(JSON.stringify(record));
    }
    this.state = {...previous, snapshot: value, digest, sequence: previous.sequence + 1,
      deliveries: record ? [...previous.deliveries, record] : previous.deliveries,
      last_delivery: record ? {id: record.id, event: record.event, repository: record.repository,
        event_sequence: record.event_sequence, payload_sha256: record.payload_sha256, record_digest: record.record_digest, observed_at: record.observed_at} : previous.last_delivery};
    try { this.persist(); } catch (error) { this.state = previous; throw error; }
    return true;
  }
  checkpoint() {
    return {sequence: this.state.sequence, snapshot: this.state.snapshot, digest: this.state.digest,
      event_sequence: this.state.deliveries.length, journal_head_digest: this.state.deliveries.at(-1)?.record_digest || ZERO_DIGEST};
  }
  visible() {
    if (!this.requiresReplica && !this.state.required_replica_node_id && !this.state.journal_source_node_id) return this.state;
    const confirmed = this.state.confirmed || {snapshot: null, digest: null, sequence: 0, event_sequence: 0};
    return {...this.state, ...confirmed, deliveries: this.state.deliveries.slice(0, confirmed.event_sequence)};
  }
  confirm() {
    if (this.storageFailed) throw new Error('STORAGE_RESTART_REQUIRED');
    const previous = this.state;
    this.state = {...previous, confirmed: this.checkpoint()};
    try { this.persist(); } catch (error) { this.state = previous; throw error; }
  }
  importBatch(packet, expectedSource, repositories) {
    if (this.storageFailed) throw new Error('STORAGE_RESTART_REQUIRED');
    const prior = this.state;
    if (!packet || Object.keys(packet).sort().join(',') !== 'after,checkpoint,epoch,events,previous_digest,schema,source_node_id,version' ||
        packet.schema !== 'qikvrt-monitor-replication/v1' || packet.version !== VERSION ||
        packet.source_node_id !== expectedSource || typeof packet.epoch !== 'string' || !packet.epoch ||
        !Number.isSafeInteger(packet.after) || packet.after < 0 || !Array.isArray(packet.events) ||
        !/^[a-f0-9]{64}$/.test(packet.previous_digest || '')) throw new Error('INVALID_REPLICATION_BINDING');
    if (prior.journal_source_node_id && (prior.journal_source_node_id !== expectedSource || prior.epoch !== packet.epoch)) throw new Error('REPLICA_EPOCH_CONFLICT');
    if (!prior.journal_source_node_id && (prior.sequence || prior.deliveries.length)) throw new Error('REPLICA_NOT_EMPTY');
    if (packet.after > prior.deliveries.length) throw new Error('REPLICA_EVENT_GAP');
    if ((prior.deliveries[packet.after - 1]?.record_digest || ZERO_DIGEST) !== packet.previous_digest) throw new Error('REPLICA_PREFIX_CONFLICT');
    const events = prior.deliveries.slice(); const ids = new Set(events.map(event => event.id));
    let previous = packet.previous_digest;
    for (const [index, event] of packet.events.entries()) {
      const sequence = packet.after + index + 1;
      validateEvent(event, sequence, previous);
      const payload = JSON.parse(Buffer.from(event.payload_base64, 'base64').toString('utf8'));
      if (!repositories.some(repo => repo.name === event.repository) || payload.repository?.full_name !== event.repository ||
          payload.repository.private !== false || event.verification !== 'HMAC_SHA256') throw new Error('PUBLIC_REPOSITORY_SCOPE_REQUIRED');
      if (events[sequence - 1]) {
        if (JSON.stringify(events[sequence - 1]) !== JSON.stringify(event)) throw new Error('REPLICA_EVENT_CONFLICT');
      } else {
        if (ids.has(event.id)) throw new Error('REPLICA_DELIVERY_CONFLICT');
        ids.add(event.id); events.push(event);
      }
      previous = event.record_digest;
    }
    const checkpoint = packet.checkpoint;
    if (checkpoint && (Object.keys(checkpoint).sort().join(',') !== 'digest,event_sequence,journal_head_digest,sequence,snapshot' ||
        !Number.isSafeInteger(checkpoint.sequence) || checkpoint.sequence < prior.sequence ||
        checkpoint.event_sequence !== packet.after + packet.events.length || checkpoint.event_sequence !== events.length ||
        checkpoint.journal_head_digest !== (events.at(-1)?.record_digest || ZERO_DIGEST) ||
        (checkpoint.snapshot ? checkpoint.snapshot.version !== VERSION || checkpoint.snapshot.schema !== 'qikvrt-public-activity/v1' ||
          sha256(JSON.stringify(checkpoint.snapshot)) !== checkpoint.digest || checkpoint.sequence < 1 : checkpoint.sequence !== 0 || checkpoint.digest !== null) ||
        (checkpoint.sequence === prior.sequence && checkpoint.digest !== prior.digest))) throw new Error('REPLICA_CHECKPOINT_CONFLICT');
    const next = {...prior, journal_source_node_id: expectedSource, epoch: packet.epoch, deliveries: events};
    if (checkpoint) {
      Object.assign(next, {sequence: checkpoint.sequence, snapshot: checkpoint.snapshot, digest: checkpoint.digest, confirmed: checkpoint});
      const last = events.at(-1);
      next.last_delivery = last ? {id: last.id, event: last.event, repository: last.repository, event_sequence: last.event_sequence,
        payload_sha256: last.payload_sha256, record_digest: last.record_digest, observed_at: last.observed_at} : null;
    }
    this.state = next;
    try { this.persist(); } catch (error) { this.state = prior; throw error; }
  }
  envelope(sourceHead = null, sourceTree = null) {
    const state = this.visible();
    if (!state.snapshot) return null;
    return {...state.snapshot, replication: {
      node_id: state.journal_source_node_id || this.nodeId, epoch: state.epoch, sequence: state.sequence,
      digest: state.digest, source_head: sourceHead, source_tree: sourceTree
    }};
  }
}

export function verifyWebhook(raw, signature, secret) {
  if (!secret || !/^sha256=[a-f0-9]{64}$/.test(signature || '')) return false;
  const expected = createHmac('sha256', secret).update(raw).digest();
  const supplied = Buffer.from(signature.slice(7), 'hex');
  return supplied.length === expected.length && timingSafeEqual(supplied, expected);
}

export function createMonitor(options = {}) {
  const env = options.env || process.env;
  const repos = options.repositories || JSON.parse(env.QIKVRT_MONITOR_REPOSITORIES || '[{"name":"ingolf-lohmann/qik-vrt","role":"Mirror","branch":"main"},{"name":"Goldkelch/qik-vrt","role":"Authority","branch":"main"}]');
  configureRepositories(repos);
  const nodeId = env.QIKVRT_MONITOR_NODE_ID || 'mirror:ingolf-lohmann/qik-vrt';
  const role = env.QIKVRT_MONITOR_ROLE || 'primary';
  const primaryId = env.QIKVRT_MONITOR_PRIMARY_NODE_ID;
  const replicaId = env.QIKVRT_MONITOR_REPLICA_NODE_ID;
  const replicaUrl = env.QIKVRT_MONITOR_REPLICA_URL;
  const replicationSecret = env.QIKVRT_MONITOR_REPLICATION_SECRET;
  if (!['primary','replica'].includes(role) ||
      (role === 'replica' && (!primaryId || primaryId === nodeId || replicaUrl || !replicationSecret)) ||
      (role === 'primary' && ((!!replicaUrl !== !!replicaId) || (replicaUrl && (!replicationSecret || replicaId === nodeId))))) throw new Error('INVALID_REPLICATION_CONFIGURATION');
  if (replicaUrl) {
    const target = new URL(replicaUrl);
    if (!['http:','https:'].includes(target.protocol) || target.username || target.password || target.search || target.hash || target.pathname !== '/') throw new Error('INVALID_REPLICA_URL');
  }
  const sourceHead = /^[a-f0-9]{40}$/.test(env.RAILWAY_GIT_COMMIT_SHA || env.QIKVRT_MONITOR_SOURCE_HEAD || '') ? (env.RAILWAY_GIT_COMMIT_SHA || env.QIKVRT_MONITOR_SOURCE_HEAD) : null;
  const sourceTree = /^[a-f0-9]{40}$/.test(env.QIKVRT_MONITOR_SOURCE_TREE || '') ? env.QIKVRT_MONITOR_SOURCE_TREE : null;
  const artifacts = Object.fromEntries(['server.mjs','observer.mjs','index.html','client-replica.js','health-projection.js','package.json'].map(name=>[name,sha256(readFileSync(new URL('./'+name,import.meta.url)))]));
  const statePath = options.statePath || resolve(env.QIKVRT_MONITOR_STATE_DIR || '/var/lib/qikvrt/monitor', 'node.json');
  const store = new MonitorStore(statePath, nodeId);
  if ((role === 'primary' && store.state.journal_source_node_id) ||
      (role === 'replica' && store.state.journal_source_node_id && store.state.journal_source_node_id !== primaryId) ||
      (store.state.required_replica_node_id && store.state.required_replica_node_id !== replicaId)) throw new Error('DURABLE_REPLICATION_CONFIGURATION_MISMATCH');
  if (role === 'replica' && !store.state.journal_source_node_id && (store.state.sequence || store.state.deliveries.length)) throw new Error('REPLICA_NOT_EMPTY');
  store.requiresReplica = !!replicaUrl;
  if (replicaUrl) store.state = {...store.state, required_replica_node_id: replicaId};
  const clients = new Set();
  let operations = Promise.resolve(), operationError = null;
  const enqueue = task => {
    const result = operations.then(task);
    operations = result.catch(() => {});
    return result;
  };
  const journalHead = () => ({schema: 'qikvrt-monitor-replica-head/v1', version: VERSION, role,
    node_id: nodeId, source_node_id: role === 'replica' ? primaryId : nodeId,
    epoch: role === 'replica' && !store.state.journal_source_node_id ? null : store.state.epoch,
    ...Object.fromEntries(Object.entries(store.checkpoint()).filter(([key]) => key !== 'snapshot'))});
  function nativeStatus() {
    if (!env.QIKVRT_NATIVE_STATE_FILE) return {state:'UNKNOWN', cause:'Native Laufzeit noch nicht an diese Monitor-Instanz gebunden.', whole_transputer_verified:false};
    try {
      const status = JSON.parse(readFileSync(env.QIKVRT_NATIVE_STATE_FILE,'utf8'));
      if (status.schema !== 'qikvrt-native-runtime/v1') throw new Error('NATIVE_RUNTIME_SCHEMA_MISMATCH');
      // Cache receipts describe compiled artifacts; they never prove the whole live terminal.
      return {...status, whole_transputer_verified:false};
    } catch (error) { return {state:'BLOCK', cause:error.message, whole_transputer_verified:false}; }
  }
  const metadata = () => {
    const visible = store.visible();
    const binding = {schema: 'qikvrt-monitor-binding/v1', node_id: role === 'replica' ? primaryId : nodeId, serving_node_id: nodeId, epoch: visible.epoch,
    version: VERSION, sequence: visible.sequence, digest: visible.digest, source_head: sourceHead, source_tree: sourceTree, artifact_files_sha256: artifacts,
    source_repository: env.QIKVRT_MONITOR_SOURCE_REPOSITORY || 'ingolf-lohmann/qik-vrt', observed_at: iso(),
    webhook_secret_configured: !!env.QIKVRT_GITHUB_WEBHOOK_SECRET,
    webhook_registration: env.QIKVRT_GITHUB_WEBHOOK_ID ? 'CONFIGURED_NOT_INDEPENDENTLY_VERIFIED' : 'MISSING',
    last_verified_delivery: visible.deliveries.at(-1) || null, periodic_polling: false,
    event_sequence: visible.deliveries.length,
    journal_head_digest: visible.deliveries.at(-1)?.record_digest || ZERO_DIGEST,
    journal_replication: {role, required_replica_node_id: replicaId || null, source_node_id: role === 'replica' ? primaryId : nodeId,
      locally_stored_events: store.state.deliveries.length, confirmed_events: visible.deliveries.length,
      pending_events: store.state.deliveries.length - visible.deliveries.length,
      checkpoint_confirmed: role === 'replica' || replicaUrl ? !!store.state.confirmed && store.state.confirmed.sequence === store.state.sequence : false,
      write_failover: 'FORBIDDEN_WITHOUT_FENCING', deployed_failover_verified: false},
    losslessness_scope: replicaUrl ? 'Configured two-node durable receipt and confirmed-prefix replay; independently deployed failover remains unverified.' :
      'Single-node durable receipt or read-only replicated checkpoint. Deployed Mesh failover remains a separate gate.',
    snapshot_durable: !!visible.snapshot, connected_clients: clients.size,
    operation_error: operationError,
    runtime_health: options.runtimeHealth?.() || {state:'UNKNOWN', cause:'SYSTEM_RUNTIME_HEALTH_NOT_BOUND'},
    native_runtime: nativeStatus(), workflow_success_is_effect_ack_done: false};
    binding.health = globalThis.QikvrtHealth.project(visible.snapshot,binding,null,Date.now());
    return binding;
  };
  function frame(response, name, value, id = null) {
    if (response.destroyed || response.writableLength > MAX_BODY * 2) { response.destroy(); clients.delete(response); return; }
    response.write((id ? 'id: ' + id + '\n' : '') + 'event: ' + name + '\ndata: ' + JSON.stringify(value) + '\n\n');
  }
  function publish() {
    const value = store.envelope(sourceHead,sourceTree);
    if (value) for (const client of clients) frame(client, 'snapshot', value);
  }
  function publishConfirmed(after) {
    for (const event of store.visible().deliveries.slice(after)) for (const client of clients)
      frame(client, 'delivery', {...event, epoch: store.state.epoch}, store.state.epoch + ':' + event.event_sequence);
    publish();
  }
  async function peerRequest(path, packet = null) {
    const method = packet ? 'POST' : 'GET', raw = packet ? Buffer.from(JSON.stringify(packet)) : Buffer.alloc(0);
    if (raw.length > MAX_REPLICATION_BODY) throw new Error('REPLICATION_BATCH_TOO_LARGE');
    const response = await (options.replicationFetch || fetch)(new URL(path, replicaUrl), {method, redirect: 'error',
      signal: AbortSignal.timeout(options.replicationTimeoutMs || 5000),
      headers: {'content-type': 'application/json', 'x-qikvrt-replication-signature': replicationSignature(raw, method, path, replicationSecret)},
      body: packet ? raw : undefined});
    const bytes = await readBody(response.body, MAX_REPLICATION_BODY);
    if (!verifyReplication(bytes, response.headers.get('x-qikvrt-replication-signature'), 'RESPONSE', path, replicationSecret)) throw new Error('INVALID_REPLICA_READBACK_SIGNATURE');
    const head = JSON.parse(bytes);
    if (!response.ok) throw new Error(head.error || 'REPLICA_REQUEST_FAILED');
    if (head.schema !== 'qikvrt-monitor-replica-head/v1' || head.role !== 'replica' || head.version !== VERSION || head.node_id !== replicaId ||
        head.source_node_id !== nodeId || !Number.isSafeInteger(head.event_sequence) || head.event_sequence < 0 ||
        head.event_sequence > store.state.deliveries.length || !Number.isSafeInteger(head.sequence) || head.sequence < 0 ||
        head.sequence > store.state.sequence || (head.epoch !== null && head.epoch !== store.state.epoch) ||
        (head.epoch === null && (head.event_sequence || head.sequence)) ||
        head.journal_head_digest !== (store.state.deliveries[head.event_sequence - 1]?.record_digest || ZERO_DIGEST)) throw new Error('REPLICA_PREFIX_CONFLICT');
    return head;
  }
  async function synchronize() {
    if (!replicaUrl) return;
    if (store.storageFailed) throw new Error('STORAGE_RESTART_REQUIRED');
    let head = await peerRequest('/api/replication/head');
    const checkpoint = store.checkpoint();
    // Bounded suffix batches permit restart at any durably verified prefix.
    // Only the final checkpoint becomes visible to ordinary clients.
    do {
      const after = head.event_sequence;
      const packet = {schema: 'qikvrt-monitor-replication/v1', version: VERSION, source_node_id: nodeId,
        epoch: store.state.epoch, after, previous_digest: head.journal_head_digest, events: [], checkpoint: null};
      for (const event of store.state.deliveries.slice(after)) {
        packet.events.push(event);
        if (Buffer.byteLength(JSON.stringify(packet)) > MAX_REPLICATION_BODY / 2) {
          packet.events.pop(); break;
        }
      }
      const through = after + packet.events.length;
      if (through === checkpoint.event_sequence) packet.checkpoint = checkpoint;
      if (!packet.events.length && !packet.checkpoint) throw new Error('REPLICATION_EVENT_TOO_LARGE');
      head = await peerRequest('/api/replication/append', packet);
      if (head.epoch !== store.state.epoch || head.event_sequence !== through ||
          (packet.checkpoint && (head.sequence !== checkpoint.sequence || head.digest !== checkpoint.digest))) throw new Error('REPLICA_READBACK_MISMATCH');
    } while (head.event_sequence !== checkpoint.event_sequence || head.sequence !== checkpoint.sequence || head.digest !== checkpoint.digest);
    store.confirm();
  }
  function syncReplica() {
    return enqueue(async () => {
      const before = store.visible().deliveries.length;
      await synchronize(); operationError = null; publishConfirmed(before);
      return journalHead();
    });
  }
  function observeLatest(reason = 'manual', delivery = null) {
    if (role === 'replica') return Promise.reject(new Error('REPLICA_READ_ONLY'));
    return enqueue(async () => {
      const before = store.visible().deliveries.length;
      const value = await (options.observe || snapshot)();
      value.delivery = {...value.delivery, mode: 'node_stream', periodic_polling: false,
        webhook_registered: false, push_verified: false,
        webhook_receiver_configured: !!env.QIKVRT_GITHUB_WEBHOOK_SECRET,
        last_verified_delivery_at: delivery?.observed_at || store.state.last_delivery?.observed_at || null};
      value.node_observation = {reason, node_id: nodeId, source_repository: env.QIKVRT_MONITOR_SOURCE_REPOSITORY || 'ingolf-lohmann/qik-vrt'};
      const changed = store.update(value, delivery);
      await synchronize();
      operationError = null;
      if (changed || store.visible().deliveries.length !== before) publishConfirmed(before);
      return store.envelope(sourceHead,sourceTree);
    });
  }
  function json(response, status, value, method = 'GET', signedPath = null) {
    const raw = JSON.stringify(value);
    const signature = signedPath && replicationSecret ? {'x-qikvrt-replication-signature': replicationSignature(raw, 'RESPONSE', signedPath, replicationSecret)} : {};
    response.writeHead(status, {...SECURITY, ...signature, 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store'});
    response.end(method === 'HEAD' ? undefined : raw);
  }
  const server = http.createServer(async (request, response) => {
    try {
      const url = new URL(request.url, 'http://monitor.invalid');
      if (url.pathname.startsWith('/api/replication/')) {
        const path = url.pathname;
        if (!replicationSecret) return json(response, 503, {error: 'REPLICATION_SECRET_NOT_CONFIGURED'});
        const raw = await readBody(request, MAX_REPLICATION_BODY);
        if (!verifyReplication(raw, request.headers['x-qikvrt-replication-signature'], request.method, path, replicationSecret)) return json(response, 401, {error: 'INVALID_REPLICATION_SIGNATURE'}, 'GET', path);
        if (path === '/api/replication/head' && request.method === 'GET' && !raw.length) return json(response, 200, journalHead(), 'GET', path);
        if (path === '/api/replication/append' && request.method === 'POST' && role === 'replica') {
          if (!/^application\/json(?:;|$)/i.test(request.headers['content-type'] || '')) return json(response, 415, {error: 'JSON_REQUIRED'}, 'GET', path);
          const packet = JSON.parse(raw);
          await enqueue(() => {
            const before = store.visible().deliveries.length;
            store.importBatch(packet, primaryId, repos); operationError = null;
            publishConfirmed(before);
          });
          return json(response, 200, journalHead(), 'GET', path);
        }
        if (path === '/api/replication/sync' && request.method === 'POST' && role === 'primary' && !raw.length) {
          return json(response, 200, await syncReplica(), 'GET', path);
        }
        return json(response, 405, {error: 'REPLICATION_OPERATION_NOT_ALLOWED'}, 'GET', path);
      }
      if (url.pathname === '/api/webhooks/github' && request.method === 'POST') {
        if (role === 'replica') return json(response, 409, {error: 'REPLICA_READ_ONLY'});
        if (!env.QIKVRT_GITHUB_WEBHOOK_SECRET) return json(response, 503, {error: 'GITHUB_WEBHOOK_SECRET_NOT_CONFIGURED'});
        if (!/^application\/json(?:;|$)/i.test(request.headers['content-type'] || '')) return json(response, 415, {error: 'JSON_REQUIRED'});
        const chunks = []; let size = 0;
        for await (const chunk of request) {
          size += chunk.length;
          if (size > MAX_BODY) { json(response, 413, {error: 'PAYLOAD_TOO_LARGE'}); return; }
          chunks.push(chunk);
        }
        const raw = Buffer.concat(chunks);
        if (!verifyWebhook(raw, request.headers['x-hub-signature-256'], env.QIKVRT_GITHUB_WEBHOOK_SECRET)) return json(response, 401, {error: 'INVALID_WEBHOOK_SIGNATURE'});
        const body = JSON.parse(raw), repo = body.repository?.full_name;
        if (!repos.some(item => item.name === repo) || body.repository.private !== false) return json(response, 403, {error: 'PUBLIC_REPOSITORY_SCOPE_REQUIRED'});
        const id = request.headers['x-github-delivery'], event = request.headers['x-github-event'];
        if (!/^[a-zA-Z0-9-]{8,80}$/.test(id || '') || !['ping','push','workflow_run','workflow_job','pull_request','pull_request_review','issue_comment','issues','release','create','delete','check_run','check_suite'].includes(event)) return json(response, 400, {error: 'INVALID_DELIVERY'});
        const receipt = {id, event, repository: repo, payload_sha256: sha256(raw), payload_base64: raw.toString('base64'), observed_at: iso(), verification: 'HMAC_SHA256'};
        const old = store.state.deliveries.find(item => item.id === id);
        if (old) {
          if (old.payload_sha256 !== receipt.payload_sha256) return json(response, 409, {error: 'DUPLICATE_DELIVERY_CONTENT_MISMATCH'});
          // A prior local write may have outlived an interrupted peer receipt.
          // Retry verifies the peer rather than inheriting the earlier ACK.
          await syncReplica();
          return json(response, 200, {duplicate: true, durable: true, cross_node_durable: !!replicaUrl,
            event_sequence: old.event_sequence, payload_sha256: old.payload_sha256, sequence: store.visible().sequence, effect_ack_done: false});
        }
        invalidateRepository(repo);
        const envelope = await observeLatest('github_webhook', receipt);
        const committed = store.state.deliveries.find(item => item.id === id);
        if (!committed || committed.payload_sha256 !== receipt.payload_sha256) throw new Error('DELIVERY_READBACK_MISMATCH');
        return json(response, 200, {received: true, durable: true, cross_node_durable: !!replicaUrl,
          replica_node_id: replicaId || null, event_sequence: committed.event_sequence, payload_sha256: committed.payload_sha256, sequence: envelope.replication.sequence, digest: envelope.replication.digest, effect_ack_done: false});
      }
      if (!['GET','HEAD'].includes(request.method)) return json(response, 405, {error: 'METHOD_NOT_ALLOWED'});
      if (url.pathname === '/health' || url.pathname === '/api/node') return json(response, 200, metadata(), request.method);
      if (url.pathname === '/api/directory') return json(response, 200, JSON.parse(readFileSync(new URL('./URL_DIRECTORY.json',import.meta.url),'utf8')), request.method);
      if (url.pathname === '/api/activity') {
        const value = role === 'replica' ? store.envelope(sourceHead,sourceTree) : await observeLatest();
        return json(response, value ? 200 : 503, value || {error: 'REPLICA_CHECKPOINT_NOT_AVAILABLE'}, request.method);
      }
      if (role === 'replica' && url.pathname === '/api/run') return json(response, 503, {error: 'LIVE_SOURCE_DETAILS_UNAVAILABLE_ON_READ_ONLY_REPLICA'}, request.method);
      if (url.pathname === '/api/events') {
        const state = store.visible();
        const after = Number(url.searchParams.get('after') || 0);
        if (!Number.isSafeInteger(after) || after < 0 || after > state.deliveries.length) return json(response, 400, {error: 'INVALID_REPLAY_CURSOR'});
        return json(response, 200, {epoch: state.epoch, after, event_sequence: state.deliveries.length, events: state.deliveries.slice(after)}, request.method);
      }
      if (url.pathname === '/api/stream') {
        if (request.method === 'HEAD') { response.writeHead(200, {'content-type':'text/event-stream'}); response.end(); return; }
        const cursor = request.headers['last-event-id'] || (url.searchParams.has('epoch') ? url.searchParams.get('epoch') + ':' + (url.searchParams.get('after') || '0') : null);
        const parts = cursor?.split(':');
        const after = parts && parts[0] === store.state.epoch ? Number(parts[1]) : 0;
        const state = store.visible();
        if (!Number.isSafeInteger(after) || after < 0 || after > state.deliveries.length) return json(response, 409, {error: 'REPLAY_CURSOR_OUTSIDE_DURABLE_JOURNAL'});
        response.writeHead(200, {...SECURITY, 'content-type':'text/event-stream; charset=utf-8', 'cache-control':'no-store', 'connection':'keep-alive', 'x-accel-buffering':'no'});
        response.write('retry: 3000\n\n'); clients.add(response);
        frame(response, 'node', metadata());
        for (const event of state.deliveries.slice(after)) frame(response, 'delivery', {...event, epoch: state.epoch}, state.epoch + ':' + event.event_sequence);
        const value = store.envelope(sourceHead,sourceTree);
        if (value) frame(response, 'snapshot', value);
        const heartbeat = setInterval(() => frame(response, 'node', metadata()), 20000);
        heartbeat.unref(); request.on('close', () => {clearInterval(heartbeat); clients.delete(response);});
        return;
      }
      if (['/client-replica.js','/health-projection.js'].includes(url.pathname)) {
        response.writeHead(200, {...SECURITY, 'content-type':'text/javascript; charset=utf-8', 'cache-control':'no-cache'});
        response.end(request.method === 'HEAD' ? undefined : readFileSync(new URL('.'+url.pathname, import.meta.url))); return;
      }
      const page = ['/', '/mesh', '/node', '/client'].includes(url.pathname) ? '/' : url.pathname;
      const reply = await observer.fetch(new Request('http://monitor.invalid' + page + url.search, {method: request.method}), env);
      response.writeHead(reply.status, Object.fromEntries(reply.headers));
      response.end(request.method === 'HEAD' ? undefined : Buffer.from(await reply.arrayBuffer()));
    } catch (error) {
      operationError = error.message;
      for (const client of clients) frame(client,'node',metadata());
      const signedPath = new URL(request.url, 'http://monitor.invalid').pathname;
      const peerOperation = signedPath.startsWith('/api/replication/');
      const conflict = /REPLICA_(EVENT_GAP|PREFIX_CONFLICT|EVENT_CONFLICT|DELIVERY_CONFLICT|EPOCH_CONFLICT|CHECKPOINT_CONFLICT)|INVALID_REPLICATION_BINDING|DURABLE_EVENT_JOURNAL_MISMATCH/.test(error.message);
      if (!response.headersSent) json(response, error.message === 'PAYLOAD_TOO_LARGE' ? 413 : conflict || error.message === 'DUPLICATE_DELIVERY_CONTENT_MISMATCH' ? 409 : replicaUrl ? 503 : 500,
        {error: peerOperation ? error.message : 'MONITOR_OPERATION_FAILED', cause: error.message, effect_ack_done: false}, 'GET', peerOperation ? signedPath : null);
      else response.destroy();
      console.error(JSON.stringify({at: iso(), stage: 'MONITOR_REQUEST', cause: error.message}));
    }
  });
  server.on('close', () => {for (const client of clients) client.destroy(); clients.clear();});
  return {server, store, metadata, observeLatest, syncReplica};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const monitor = createMonitor();
  monitor.server.listen(Number(process.env.PORT || 8080), '0.0.0.0', () => {
    console.log(JSON.stringify({at: iso(), stage: 'MONITOR_READY', version: VERSION, node_id: monitor.metadata().node_id, periodic_polling: false}));
    if (monitor.metadata().journal_replication.role === 'primary') monitor.observeLatest('startup').catch(error => console.error(JSON.stringify({at: iso(), stage: 'STARTUP_OBSERVATION_FAILED', cause: error.message})));
  });
}
