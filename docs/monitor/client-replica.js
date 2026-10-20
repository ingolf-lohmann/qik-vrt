// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// A local, read-only replica. A matching digest is not EFFECT_ACK_DONE.
(function (root) {
  'use strict';
  function create(options) {
    var id;
    try {
      id = sessionStorage.getItem('qikvrt-monitor-instance');
      if (!id) {
        id = crypto.randomUUID();
        sessionStorage.setItem('qikvrt-monitor-instance', id);
      }
    } catch (_) { id = crypto.randomUUID(); }
    var replica = {
      id: id, version: options.version, node_id: null, node_version: null,
      epoch: null, sequence: 0, node_sequence: 0, digest: null,
      source_head: null, applied_at: null, transport: 'disconnected',
      error: null, snapshot: null, last_node_at: null,
      event_sequence: 0, node_event_sequence: 0, events: [], event_digest: '0'.repeat(64)
    };
    var tail = Promise.resolve();
    replica.observe = function (node) {
      if (replica.node_id && node.node_id !== replica.node_id) {
        replica.error = 'NODE_IDENTITY_MISMATCH'; return;
      }
      if (node.version !== replica.version) {
        replica.node_version = node.version;
        replica.error = 'CLIENT_VERSION_MISMATCH'; return;
      }
      replica.last_node_at = Date.now();
      replica.node_sequence = node.sequence;
      replica.node_event_sequence = node.event_sequence || 0;
      if (replica.epoch && replica.epoch !== node.epoch) replica.error = 'NODE_EPOCH_CHANGED';
    };
    replica.accept = function (envelope) {
      var task = tail.then(async function () {
        var binding = envelope && envelope.replication;
        function reject(reason) { replica.error = reason; return {accepted: false, reason: reason}; }
        if (!binding || !Number.isSafeInteger(binding.sequence) || binding.sequence < 1 ||
            typeof binding.epoch !== 'string' || !/^[a-f0-9]{64}$/.test(binding.digest || '') ||
            envelope.schema !== 'qikvrt-public-activity/v1' || !Array.isArray(envelope.repositories)) {
          return reject('INVALID_NODE_SNAPSHOT');
        }
        if (envelope.version !== replica.version) {
          replica.node_version = envelope.version; return reject('CLIENT_VERSION_MISMATCH');
        }
        if (replica.node_id && replica.node_id !== binding.node_id) return reject('NODE_IDENTITY_MISMATCH');
        if (replica.epoch && replica.epoch !== binding.epoch) return reject('NODE_EPOCH_CHANGED');
        var snapshot = Object.assign({}, envelope); delete snapshot.replication;
        var hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(snapshot)));
        var digest = Array.from(new Uint8Array(hash), function (b) { return b.toString(16).padStart(2, '0'); }).join('');
        if (digest !== binding.digest) return reject('SNAPSHOT_DIGEST_MISMATCH');
        if (replica.epoch === binding.epoch && binding.sequence < replica.sequence) return reject('OUT_OF_ORDER_SNAPSHOT');
        if (replica.epoch === binding.epoch && binding.sequence === replica.sequence && replica.digest !== digest) return reject('SEQUENCE_CONTENT_MISMATCH');
        replica.observe({node_id: binding.node_id, version: envelope.version, sequence: binding.sequence, epoch: binding.epoch, event_sequence: replica.node_event_sequence});
        if (replica.epoch === binding.epoch && binding.sequence === replica.sequence && replica.digest === digest) {
          if (!/^(EVENT_|INVALID_EVENT)/.test(replica.error || '')) replica.error = null;
          return {accepted: false, duplicate: true};
        }
        replica.node_id = binding.node_id; replica.node_version = envelope.version;
        replica.epoch = binding.epoch; replica.sequence = binding.sequence;
        replica.digest = digest; replica.source_head = binding.source_head;
        replica.snapshot = snapshot; replica.applied_at = new Date().toISOString();
        if (!/^(EVENT_|INVALID_EVENT)/.test(replica.error || '')) replica.error = null;
        return {accepted: true, snapshot: snapshot};
      });
      tail = task.catch(function () {});
      return task;
    };
    replica.acceptEvent = function (event) {
      var task = tail.then(async function () {
        function reject(reason) { replica.error = reason; return {accepted: false, reason: reason}; }
        if (replica.epoch && event.epoch !== replica.epoch) return reject('NODE_EPOCH_CHANGED');
        if (!Number.isSafeInteger(event.event_sequence) || event.event_sequence < 1) return reject('INVALID_EVENT_SEQUENCE');
        var old = replica.events[event.event_sequence - 1];
        if (old) return old.record_digest === event.record_digest && JSON.stringify(old) === JSON.stringify(event) ? {accepted: false, duplicate: true} : reject('EVENT_CONTENT_MISMATCH');
        if (event.event_sequence !== replica.event_sequence + 1) return reject('EVENT_SEQUENCE_GAP');
        var bytes = Uint8Array.from(atob(event.payload_base64), function(c){return c.charCodeAt(0)});
        var digest = await crypto.subtle.digest('SHA-256', bytes);
        var hex = Array.from(new Uint8Array(digest), function(b){return b.toString(16).padStart(2,'0')}).join('');
        if (hex !== event.payload_sha256 || event.previous_digest !== replica.event_digest) return reject('EVENT_DIGEST_MISMATCH');
        var record = Object.assign({}, event); delete record.epoch; delete record.record_digest;
        var hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(record)));
        var recordDigest = Array.from(new Uint8Array(hash), function(b){return b.toString(16).padStart(2,'0')}).join('');
        if (recordDigest !== event.record_digest) return reject('EVENT_DIGEST_MISMATCH');
        replica.events.push(event); replica.event_sequence = event.event_sequence;
        replica.event_digest = event.record_digest;
        if (/^(EVENT_|INVALID_EVENT)/.test(replica.error || '')) replica.error = null;
        return {accepted: true};
      });
      tail = task.catch(function(){}); return task;
    };
    replica.status = function () {
      var errors = {
        CLIENT_VERSION_MISMATCH: 'Client-Version weicht vom Node ab. Den Client neu laden.',
        SNAPSHOT_DIGEST_MISMATCH: 'Prüfsumme stimmt nicht. Dieser Stand wurde verworfen.',
        OUT_OF_ORDER_SNAPSHOT: 'Veraltete Ereignisfolge verworfen. Aktuellen Node-Stand übernehmen.',
        SEQUENCE_CONTENT_MISMATCH: 'Dieselbe Ereignisfolge enthält widersprüchliche Daten.',
        NODE_IDENTITY_MISMATCH: 'Die Antwort stammt von einem anderen Node.',
        NODE_EPOCH_CHANGED: 'Der Node wurde neu initialisiert. Ein vollständiger Stand wird benötigt.',
        INVALID_NODE_SNAPSHOT: 'Der Node hat keinen gültigen gebundenen Stand geliefert.'
        ,EVENT_SEQUENCE_GAP: 'Eine Ereignislücke wurde erkannt. Die fehlenden Ereignisse werden aus dem dauerhaften Journal erneut übertragen.'
        ,EVENT_DIGEST_MISMATCH: 'Ein Ereignis stimmt nicht mit seiner Prüfsumme oder der Journalfolge überein.'
        ,EVENT_CONTENT_MISMATCH: 'Eine bereits bekannte Ereignisnummer enthält widersprüchliche Bytes.'
      };
      if (replica.error) return {label: 'Abweichung erkannt', detail: errors[replica.error] || replica.error};
      if (!replica.snapshot) return {label: 'Noch nicht synchronisiert', detail: 'Noch kein geprüfter Node-Stand übernommen.'};
      if (replica.transport !== 'connected' || !replica.last_node_at || Date.now() - replica.last_node_at > 45000) {
        return {label: 'Verbindung unterbrochen / ungeprüft', detail: 'Der letzte Stand bleibt erhalten; die Übereinstimmung ist aktuell nicht bestätigt.'};
      }
      if (replica.sequence !== replica.node_sequence) return {label: 'Abweichung erkannt', detail: 'Der Node besitzt eine neuere Ereignisfolge. Der vollständige Stand wird über den Stream übernommen.'};
      if (replica.event_sequence !== replica.node_event_sequence) return {label: 'Ereignisse werden synchronisiert', detail: 'Der Node enthält noch nicht übernommene Ereignisse. Der Client prüft deren Reihenfolge und Originalbytes.'};
      return {label: 'Client und Node synchron', detail: 'Version, Node-Identität, Ereignisfolge und SHA-256 stimmen überein. Die Aktualität der GitHub-Daten wird separat geprüft.'};
    };
    return replica;
  }
  root.QikvrtReplica = {create: create};
})(globalThis);
