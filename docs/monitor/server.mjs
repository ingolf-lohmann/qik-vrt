// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Extends the existing docs/monitor carrier; no repository mutation route.
import http from 'node:http';
import {createHash, createHmac, timingSafeEqual, randomUUID} from 'node:crypto';
import {readFileSync, mkdirSync, openSync, closeSync, writeFileSync, renameSync, fsyncSync, existsSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import observer, {snapshot, configureRepositories, invalidateRepository, SECURITY} from './observer.mjs';
import './health-projection.js';

export const VERSION = '2026-10-04.8';
const MAX_BODY = 2 * 1024 * 1024;
const sha256 = value => createHash('sha256').update(value).digest('hex');
const iso = () => new Date().toISOString();

export class MonitorStore {
  constructor(path, nodeId) {
    this.path = path; this.nodeId = nodeId;
    this.state = {schema: 'qikvrt-monitor-node/v1', node_id: nodeId, epoch: randomUUID(), sequence: 0, snapshot: null, digest: null, deliveries: [], last_delivery: null};
    if (existsSync(path)) {
      const prior = JSON.parse(readFileSync(path, 'utf8'));
      if (prior.schema !== this.state.schema || prior.node_id !== nodeId || !Number.isSafeInteger(prior.sequence) ||
          (prior.snapshot && sha256(JSON.stringify(prior.snapshot)) !== prior.digest)) throw new Error('DURABLE_MONITOR_STATE_MISMATCH');
      let previous = '0'.repeat(64);
      for (const [index, event] of prior.deliveries.entries()) {
        const record = {...event}; delete record.record_digest;
        if (event.event_sequence !== index + 1 || event.previous_digest !== previous ||
            sha256(Buffer.from(event.payload_base64, 'base64')) !== event.payload_sha256 ||
            sha256(JSON.stringify(record)) !== event.record_digest) throw new Error('DURABLE_EVENT_JOURNAL_MISMATCH');
        previous = event.record_digest;
      }
      this.state = prior;
    }
  }
  persist() {
    mkdirSync(dirname(this.path), {recursive: true, mode: 0o700});
    const temporary = this.path + '.tmp-' + randomUUID();
    const fd = openSync(temporary, 'wx', 0o600);
    try { writeFileSync(fd, JSON.stringify(this.state) + '\n'); fsyncSync(fd); }
    finally { closeSync(fd); }
    renameSync(temporary, this.path);
    const directory = openSync(dirname(this.path), 'r');
    try { fsyncSync(directory); } finally { closeSync(directory); }
  }
  update(value, delivery = null) {
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
        previous_digest: previous.deliveries.at(-1)?.record_digest || '0'.repeat(64)};
      record.record_digest = sha256(JSON.stringify(record));
    }
    this.state = {...previous, snapshot: value, digest, sequence: previous.sequence + 1,
      deliveries: record ? [...previous.deliveries, record] : previous.deliveries,
      last_delivery: record ? {id: record.id, event: record.event, repository: record.repository,
        event_sequence: record.event_sequence, payload_sha256: record.payload_sha256, record_digest: record.record_digest, observed_at: record.observed_at} : previous.last_delivery};
    try { this.persist(); } catch (error) { this.state = previous; throw error; }
    return true;
  }
  envelope(sourceHead = null, sourceTree = null) {
    if (!this.state.snapshot) return null;
    return {...this.state.snapshot, replication: {
      node_id: this.nodeId, epoch: this.state.epoch, sequence: this.state.sequence,
      digest: this.state.digest, source_head: sourceHead, source_tree: sourceTree
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
  const sourceHead = /^[a-f0-9]{40}$/.test(env.RAILWAY_GIT_COMMIT_SHA || env.QIKVRT_MONITOR_SOURCE_HEAD || '') ? (env.RAILWAY_GIT_COMMIT_SHA || env.QIKVRT_MONITOR_SOURCE_HEAD) : null;
  const sourceTree = /^[a-f0-9]{40}$/.test(env.QIKVRT_MONITOR_SOURCE_TREE || '') ? env.QIKVRT_MONITOR_SOURCE_TREE : null;
  const artifacts = Object.fromEntries(['server.mjs','observer.mjs','index.html','client-replica.js','health-projection.js','package.json'].map(name=>[name,sha256(readFileSync(new URL('./'+name,import.meta.url)))]));
  const statePath = options.statePath || resolve(env.QIKVRT_MONITOR_STATE_DIR || '/var/lib/qikvrt/monitor', 'node.json');
  const store = new MonitorStore(statePath, nodeId);
  const clients = new Set();
  let observation = null, operationError = null;
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
    const binding = {schema: 'qikvrt-monitor-binding/v1', node_id: nodeId, epoch: store.state.epoch,
    version: VERSION, sequence: store.state.sequence, digest: store.state.digest, source_head: sourceHead, source_tree: sourceTree, artifact_files_sha256: artifacts,
    source_repository: env.QIKVRT_MONITOR_SOURCE_REPOSITORY || 'ingolf-lohmann/qik-vrt', observed_at: iso(),
    webhook_secret_configured: !!env.QIKVRT_GITHUB_WEBHOOK_SECRET,
    webhook_registration: env.QIKVRT_GITHUB_WEBHOOK_ID ? 'CONFIGURED_NOT_INDEPENDENTLY_VERIFIED' : 'MISSING',
    last_verified_delivery: store.state.last_delivery, periodic_polling: false,
    event_sequence: store.state.deliveries.length,
    journal_head_digest: store.state.deliveries.at(-1)?.record_digest || '0'.repeat(64),
    losslessness_scope: 'Accepted public webhook bytes: fsync before acknowledgment, full ordered replay, no truncation. Provider registration and multi-node replication remain separate gates.',
    snapshot_durable: !!store.state.snapshot, connected_clients: clients.size,
    operation_error: operationError,
    runtime_health: options.runtimeHealth?.() || {state:'UNKNOWN', cause:'SYSTEM_RUNTIME_HEALTH_NOT_BOUND'},
    native_runtime: nativeStatus(), workflow_success_is_effect_ack_done: false};
    binding.health = globalThis.QikvrtHealth.project(store.state.snapshot,binding,null,Date.now());
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
  async function observeLatest(reason = 'manual', delivery = null) {
    if (observation) { await observation; if (!delivery) return store.envelope(sourceHead,sourceTree); }
    const task = (async () => {
      const value = await (options.observe || snapshot)();
      value.delivery = {...value.delivery, mode: 'node_stream', periodic_polling: false,
        webhook_registered: false, push_verified: false,
        webhook_receiver_configured: !!env.QIKVRT_GITHUB_WEBHOOK_SECRET,
        last_verified_delivery_at: delivery?.observed_at || store.state.last_delivery?.observed_at || null};
      value.node_observation = {reason, node_id: nodeId, source_repository: env.QIKVRT_MONITOR_SOURCE_REPOSITORY || 'ingolf-lohmann/qik-vrt'};
      const changed = store.update(value, delivery);
      operationError = null;
      if (changed && delivery) for (const client of clients) frame(client, 'delivery', {...store.state.deliveries.at(-1), epoch: store.state.epoch}, store.state.epoch + ':' + store.state.deliveries.length);
      publish();
      return store.envelope(sourceHead,sourceTree);
    })();
    observation = task;
    try { return await task; } finally { if (observation === task) observation = null; }
  }
  function json(response, status, value, method = 'GET') {
    response.writeHead(status, {...SECURITY, 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store'});
    response.end(method === 'HEAD' ? undefined : JSON.stringify(value));
  }
  const server = http.createServer(async (request, response) => {
    try {
      const url = new URL(request.url, 'http://monitor.invalid');
      if (url.pathname === '/api/webhooks/github' && request.method === 'POST') {
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
        if (old) return json(response, old.payload_sha256 === receipt.payload_sha256 ? 200 : 409, {duplicate: true, sequence: store.state.sequence});
        invalidateRepository(repo);
        const envelope = await observeLatest('github_webhook', receipt);
        const committed = store.state.deliveries.find(item => item.id === id);
        if (!committed || committed.payload_sha256 !== receipt.payload_sha256) throw new Error('DELIVERY_READBACK_MISMATCH');
        return json(response, 200, {received: true, durable: true, event_sequence: committed.event_sequence, payload_sha256: committed.payload_sha256, sequence: envelope.replication.sequence, digest: envelope.replication.digest, effect_ack_done: false});
      }
      if (!['GET','HEAD'].includes(request.method)) return json(response, 405, {error: 'METHOD_NOT_ALLOWED'});
      if (url.pathname === '/health' || url.pathname === '/api/node') return json(response, 200, metadata(), request.method);
      if (url.pathname === '/api/directory') return json(response, 200, JSON.parse(readFileSync(new URL('./URL_DIRECTORY.json',import.meta.url),'utf8')), request.method);
      if (url.pathname === '/api/activity') return json(response, 200, await observeLatest(), request.method);
      if (url.pathname === '/api/events') {
        const after = Number(url.searchParams.get('after') || 0);
        if (!Number.isSafeInteger(after) || after < 0 || after > store.state.deliveries.length) return json(response, 400, {error: 'INVALID_REPLAY_CURSOR'});
        return json(response, 200, {epoch: store.state.epoch, after, event_sequence: store.state.deliveries.length, events: store.state.deliveries.slice(after)}, request.method);
      }
      if (url.pathname === '/api/stream') {
        if (request.method === 'HEAD') { response.writeHead(200, {'content-type':'text/event-stream'}); response.end(); return; }
        const cursor = request.headers['last-event-id'] || (url.searchParams.has('epoch') ? url.searchParams.get('epoch') + ':' + (url.searchParams.get('after') || '0') : null);
        const parts = cursor?.split(':');
        const after = parts && parts[0] === store.state.epoch ? Number(parts[1]) : 0;
        if (!Number.isSafeInteger(after) || after < 0 || after > store.state.deliveries.length) return json(response, 409, {error: 'REPLAY_CURSOR_OUTSIDE_DURABLE_JOURNAL'});
        response.writeHead(200, {...SECURITY, 'content-type':'text/event-stream; charset=utf-8', 'cache-control':'no-store', 'connection':'keep-alive', 'x-accel-buffering':'no'});
        response.write('retry: 3000\n\n'); clients.add(response);
        frame(response, 'node', metadata());
        for (const event of store.state.deliveries.slice(after)) frame(response, 'delivery', {...event, epoch: store.state.epoch}, store.state.epoch + ':' + event.event_sequence);
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
      if (!response.headersSent) json(response, error.message === 'DUPLICATE_DELIVERY_CONTENT_MISMATCH' ? 409 : 500, {error: 'MONITOR_OPERATION_FAILED', cause: error.message});
      else response.destroy();
      console.error(JSON.stringify({at: iso(), stage: 'MONITOR_REQUEST', cause: error.message}));
    }
  });
  server.on('close', () => {for (const client of clients) client.destroy(); clients.clear();});
  return {server, store, metadata, observeLatest};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const monitor = createMonitor();
  monitor.server.listen(Number(process.env.PORT || 8080), '0.0.0.0', () => {
    console.log(JSON.stringify({at: iso(), stage: 'MONITOR_READY', version: VERSION, node_id: monitor.metadata().node_id, periodic_polling: false}));
    monitor.observeLatest('startup').catch(error => console.error(JSON.stringify({at: iso(), stage: 'STARTUP_OBSERVATION_FAILED', cause: error.message})));
  });
}
