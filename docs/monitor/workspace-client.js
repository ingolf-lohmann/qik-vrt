// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Read adapter for the original sealed S1, replica and EAP HTTP contracts.
(() => {
  'use strict';
  const sha40 = value => /^[a-f0-9]{40}$/.test(value || '');
  const sha64 = value => /^[a-f0-9]{64}$/.test(value || '');
  const authority = 'ingolf-lohmann/qik-vrt', mirror = 'Goldkelch/qik-vrt';
  function check(runtime, node, activity, native, version) {
    if (runtime?.schema !== 'qikvrt-self-host-runtime/v1' ||
        runtime.source_repository !== authority || runtime.repository_roles?.authority_repository !== authority ||
        runtime.repository_roles?.mirror_repository !== mirror || !sha40(runtime.source_head) || !sha40(runtime.source_tree) ||
        !sha64(runtime.manifest_sha256) || !sha64(runtime.config_sha256) || runtime.monitor_version !== version ||
        node?.schema !== 'qikvrt-monitor-binding/v1' || node.version !== version ||
        node.source_repository !== authority || node.node_id !== runtime.node_id ||
        node.source_head !== runtime.source_head || node.source_tree !== runtime.source_tree ||
        activity?.replication?.node_id !== node.node_id || activity.replication.epoch !== node.epoch ||
        activity.replication.source_head !== runtime.source_head || activity.replication.source_tree !== runtime.source_tree ||
        activity.replication.sequence !== node.sequence || activity.replication.digest !== node.digest) {
      throw Error('SOURCE_BINDING_MISMATCH');
    }
    const subject = native?.subject;
    if (native?.schema !== 'qikvrt_eap_http_status_v1' || native.state !== 'NATIVE_EAP_HTTP_READY' ||
        subject?.repository !== runtime.source_repository || subject.head !== runtime.source_head ||
        subject.tree !== runtime.source_tree || !Number.isSafeInteger(subject.pr) || subject.pr < 1 ||
        native.effect_ack_done !== false || native.ordinary_release !== false) {
      throw Error('NATIVE_SUBJECT_NOT_VERIFIED');
    }
    return true;
  }
  function create({version, onChange = () => {}, fetch: transport = globalThis.fetch,
                   EventSource: Stream = globalThis.EventSource, now = Date.now}) {
    const replica = globalThis.QikvrtReplica.create({version});
    let runtime = null, node = null, activity = null, native = null, stream = null;
    let observed = null, error = '', nativeError = '', connected = false, reading = false, stopped = false, generation = 0, lastGap = '';
    function view() {
      let verified = false, reason = error || nativeError;
      try {
        if (error) throw Error(error);
        if (!observed || now() - Date.parse(observed) > 45000 || now() < Date.parse(observed)) throw Error('READBACK_EXPIRED');
        check(runtime, node, activity, native, version);
        if (replica.error || replica.event_sequence !== node.event_sequence || replica.node_sequence !== replica.sequence ||
            replica.event_digest !== node.journal_head_digest) {
          throw Error(replica.error || 'EVENT_REPLAY_PENDING');
        }
        verified = true;
      } catch (e) {reason = reason || e.message;}
      return {runtime, node, activity:replica.snapshot, native:verified ? native : null, verified, reason,
        observed_at:observed, reading, transport:connected ? 'verbunden' : 'nicht bestätigt',
        replica:{epoch:replica.epoch, sequence:replica.sequence, digest:replica.digest, events:replica.event_sequence},
        workspace_membership:'UNVERIFIED', license_acceptance:'UNVERIFIED', access_release:'HOLD', effect_ack_done:false};
    }
    const emit = () => {if (!stopped) onChange(view());};
    async function get(path) {
      const response = await transport(path, {method:'GET', credentials:'same-origin', cache:'no-store', signal:AbortSignal.timeout(10000)});
      if (!/^application\/json(?:;|$)/i.test(response.headers.get('content-type') || '')) throw Error(path + ': JSON_READBACK_REQUIRED');
      const value = await response.json();
      if (!response.ok) throw Error(path + ': ' + (value.reason || value.error || 'HTTP ' + response.status));
      return value;
    }
    async function read() {
      if (stopped || reading) return;
      reading = true; error = 'READBACK_IN_PROGRESS'; native = null; emit();
      const current = ++generation;
      try {
        const first = await Promise.allSettled(['/api/runtime','/api/activity','/api/eap/state'].map(get));
        // Activity may create the next observation. Its independent node
        // checkpoint is a dependent read, never a concurrent predecessor.
        const [checkpoint] = await Promise.allSettled([get('/api/node')]);
        const values = [first[0], checkpoint, first[1], first[2]];
        if (stopped || current !== generation) return;
        error = ''; nativeError = '';
        if (values[0].status === 'fulfilled') runtime = values[0].value;
        if (values[1].status === 'fulfilled') {node = values[1].value; replica.observe(node);}
        if (values[2].status === 'fulfilled') {
          const accepted = await replica.accept(values[2].value);
          if (!accepted.accepted && !accepted.duplicate) throw Error(accepted.reason);
          activity = values[2].value;
        }
        for (let i=0; i<3; i++) if (values[i].status === 'rejected') throw values[i].reason;
        if (values[3].status === 'fulfilled') native = values[3].value;
        else nativeError = values[3].reason.message;
        observed = new Date(now()).toISOString();
      } catch (e) {error = e.message; native = null;}
      finally {reading = false; emit();}
    }
    function connect() {
      if (stopped) return;
      if (typeof Stream === 'function') {
        stream?.close();
        const cursor = replica.epoch ? '?epoch=' + encodeURIComponent(replica.epoch) + '&after=' + replica.event_sequence : '';
        stream = new Stream('/api/stream' + cursor);
        stream.onopen = () => {connected = true; replica.transport = 'connected'; emit();};
        stream.onerror = () => {connected = false; replica.transport = 'disconnected'; native = null; nativeError = 'STREAM_READBACK_UNAVAILABLE'; emit();};
        stream.addEventListener('node', event => {
          try {node = JSON.parse(event.data); replica.observe(node); emit();} catch {error = 'INVALID_NODE_EVENT'; native = null; emit();}
        });
        stream.addEventListener('snapshot', async event => {
          try {
            const value = JSON.parse(event.data), result = await replica.accept(value);
            if (!result.accepted && !result.duplicate) throw Error(result.reason);
            activity = value; emit();
          } catch (e) {error = e.message; native = null; emit();}
        });
        stream.addEventListener('delivery', async event => {
          try {
            const value = JSON.parse(event.data), result = await replica.acceptEvent(value);
            if (result.reason === 'EVENT_SEQUENCE_GAP') {
              error = result.reason; native = null;
              const gap = replica.epoch + ':' + replica.event_sequence + ':' + value.event_sequence;
              if (gap !== lastGap) {lastGap = gap; connect();}
            }
            if (!result.accepted && !result.duplicate) throw Error(result.reason);
            emit();
          } catch (e) {error = e.message; native = null; emit();}
        });
      }
    }
    function start() {
      if (stopped || stream) return;
      connect();
      return read();
    }
    function stop() {stopped = true; generation++; stream?.close(); native = null;}
    return {start, read, stop, view};
  }
  globalThis.QikvrtWorkspace = {create, check};
})();
