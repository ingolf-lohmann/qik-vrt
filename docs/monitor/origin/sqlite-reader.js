// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Runs in a Worker. Fixed, read-only SQL; embedded carrier code is never executed.
(function (root) {
  'use strict';
  const encoder = new TextEncoder();
  const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
  const hash = async bytes => hex(await root.crypto.subtle.digest('SHA-256', bytes));
  const fail = code => { throw Error(code); };
  const rows = (db, sql) => db.exec(sql)[0]?.values || [];
  const sameSubject = (a, b) => a && ['repository', 'pr', 'head', 'tree'].every(k => a[k] === b[k]) && Object.keys(a).length === 4;
  async function inspect(SQL, bytes, profile, expectedHash) {
    const raw = new Uint8Array(bytes);
    if (raw.byteLength < 100 || raw.byteLength > profile.max_store_bytes) fail('STORE_SIZE_UNSUPPORTED');
    if (await hash(raw) !== expectedHash) fail('STORE_BYTES_DIGEST_MISMATCH');
    const header = new DataView(raw.buffer, raw.byteOffset, raw.byteLength);
    if (new TextDecoder().decode(raw.slice(0, 16)) !== 'SQLite format 3\0' ||
        header.getUint32(68) !== 0x51495654 || header.getUint32(60) !== 1 || raw[18] !== 1 || raw[19] !== 1) {
      fail('CHECKPOINTED_SQLITE_MONOLITH_REQUIRED');
    }
    let db;
    try {
      db = new SQL.Database(raw);
      db.run('PRAGMA trusted_schema=OFF; PRAGMA query_only=ON;');
      if (rows(db, 'PRAGMA integrity_check').map(r => r[0]).join() !== 'ok') fail('CORRUPT_STORE');
      const allowed = new Set(['carrier', 'meta', 'events', 'sqlite_sequence']);
      const tables = new Set();
      for (const [kind, name, table, sql] of rows(db, 'SELECT type,name,tbl_name,sql FROM sqlite_master')) {
        if (kind === 'table' && allowed.has(name) && !/VIRTUAL/i.test(sql || '')) tables.add(name);
        else if (kind === 'index' && (name === 'events_binding' && table === 'events' ||
            name.startsWith('sqlite_autoindex_') && allowed.has(table))) { /* native indexes */ }
        else fail('MONOLITH_UNADMITTED_SCHEMA');
      }
      if (!['carrier', 'meta', 'events'].every(n => tables.has(n))) fail('EXISTING_CARRIER_AND_LEDGER_REQUIRED');
      const inventory = rows(db, 'SELECT path,length(body) FROM carrier ORDER BY path');
      if (!inventory.length || inventory.length > 4096 || inventory.some(([p, n]) =>
          typeof p !== 'string' || p.startsWith('/') || p.split('/').some(c => !c || c === '.' || c === '..') ||
          !Number.isSafeInteger(n) || n < 1 || n > 16 * 1024 * 1024)) fail('BOUNDED_CARRIER_REQUIRED');
      const manifestBytes = rows(db, "SELECT body FROM carrier WHERE path='MANIFEST.json'")[0]?.[0];
      if (!(manifestBytes instanceof Uint8Array) || await hash(manifestBytes) !== profile.manifest_sha256) fail('PACKAGE_MANIFEST_PIN_MISMATCH');
      const manifest = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(manifestBytes));
      if (manifest.source_head !== profile.subject.head || manifest.source_tree !== profile.subject.tree ||
          manifest.source_repository !== profile.subject.repository) fail('EXACT_SUBJECT_MISMATCH');
      const names = Object.keys(manifest.files).concat('MANIFEST.json').sort();
      if (JSON.stringify(names) !== JSON.stringify(inventory.map(r => r[0]).sort())) fail('CARRIER_INVENTORY_MISMATCH');
      const statement = db.prepare('SELECT path,body FROM carrier ORDER BY path');
      try {
        while (statement.step()) {
          const [path, body] = statement.get();
          if (!(body instanceof Uint8Array)) fail('CARRIER_BLOB_REQUIRED');
          if (path === 'MANIFEST.json') continue;
          const entry = manifest.files[path];
          if (!['100644', '100755'].includes(entry.mode) || body.length !== entry.bytes || await hash(body) !== entry.sha256) fail('CARRIER_BYTES_MISMATCH');
        }
      } finally { statement.free(); }
      const meta = Object.fromEntries(rows(db, 'SELECT key,value FROM meta'));
      if (meta.schema !== '1' || meta.epoch !== profile.ledger_id) fail('STORE_IDENTITY_MISMATCH');
      const count = rows(db, 'SELECT COUNT(*) FROM events')[0][0];
      if (!Number.isSafeInteger(count) || count > profile.max_events) fail('LEDGER_SIZE_UNSUPPORTED');
      const records = [], events = [];
      let previous = 0;
      for (const [seq, binding, source, nativeId, text, digest] of rows(db,
          'SELECT seq,binding,source,native_id,body,body_digest FROM events ORDER BY seq')) {
        if (!Number.isSafeInteger(seq) || seq <= previous || typeof text !== 'string' || encoder.encode(text).length > 65536 ||
            await hash(encoder.encode(text)) !== digest) fail('LEDGER_READBACK_MISMATCH');
        const body = JSON.parse(text), subject = body.subject;
        if (!subject || Object.keys(subject).sort().join() !== 'head,pr,repository,tree' ||
            !Number.isSafeInteger(subject.pr) || subject.pr < 1 || !/^[a-f0-9]{40}$/.test(subject.head) ||
            !/^[a-f0-9]{40}$/.test(subject.tree) || typeof subject.repository !== 'string') fail('LEDGER_SUBJECT_INVALID');
        // This fixed integer/string subject has the original Python canonical encoding.
        const canonicalSubject = JSON.stringify({head:subject.head,pr:subject.pr,repository:subject.repository,tree:subject.tree});
        if (await hash(encoder.encode(canonicalSubject)) !== binding || body.schema !== 'qikvrt_temdd_event_v1' ||
            body.evidence_transfer !== 'DENY' || body.dod !== false || body.provenance?.source !== source ||
            body.provenance?.native_event_id !== nativeId || !['repository', 'transputer'].includes(source)) fail('LEDGER_READBACK_MISMATCH');
        records.push({seq, binding, body_digest:digest});
        if (sameSubject(subject, profile.subject)) events.push({...body, id:meta.epoch+':'+seq, ledger_digest:digest});
        previous = seq;
      }
      return {schema:'qikvrt-origin-store-readback/v1', ledger_id:meta.epoch, file_sha256:expectedHash,
        manifest_sha256:profile.manifest_sha256, subject:profile.subject, bytes:raw.length,
        ledger_records:count, last_sequence:previous, records, events, sqlite_version:rows(db, 'SELECT sqlite_version()')[0][0],
        storage_scope:'ORIGIN_PRIVATE_INDEXEDDB', native_execution:false, mobile_runtime_verified:false, effect_ack_done:false};
    } catch (error) {
      if (/^[A-Z][A-Z0-9_]+$/.test(error.message || '')) throw error;
      throw Error('CORRUPT_OR_UNSUPPORTED_STORE');
    } finally { db?.close(); }
  }
  root.QikvrtSQLiteReader = {inspect};
})(globalThis);
