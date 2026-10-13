// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Runtime adaptation of one original SQLite image; no second execution ledger.
(function (root) {
  'use strict';
  const fail = code => { throw Error(code); };
  function checkOrigin() {
    const url = new URL(root.location.href);
    if (url.protocol === 'file:') fail('FILE_START_UNSUPPORTED');
    if (!root.isSecureContext || url.origin === 'null' || !(url.protocol === 'https:' ||
        url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))) fail('SECURE_ORIGIN_REQUIRED');
    if (!root.indexedDB || !root.crypto?.subtle || !root.navigator.serviceWorker || !root.Worker) fail('ORIGIN_RUNTIME_UNSUPPORTED');
  }
  function checkProfile(p) {
    if (p?.schema !== 'qikvrt-origin-bootstrap/v1' || !/^[a-f0-9]{64}$/.test(p.manifest_sha256 || '') ||
        !/^[a-f0-9]{64}$/.test(p.store_sha256 || '') || !/^[a-f0-9]{32}$/.test(p.ledger_id || '') ||
        !p.subject || !/^[a-f0-9]{40}$/.test(p.subject.head || '') || !/^[a-f0-9]{40}$/.test(p.subject.tree || '') ||
        !Number.isSafeInteger(p.subject.pr) || p.subject.pr < 1 || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(p.subject.repository || '') ||
        !Number.isSafeInteger(p.max_store_bytes) || p.max_store_bytes < 100 || p.max_store_bytes > 64*1024*1024 ||
        !Number.isSafeInteger(p.max_events) || p.max_events < 0 || p.max_events > 10000) fail('BOUND_BOOTSTRAP_PROFILE_REQUIRED');
  }
  const request = req => new Promise((resolve, reject) => {req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
  function database() {
    return new Promise((resolve, reject) => {
      const req = root.indexedDB.open('qikvrt-original-monolith-v1', 1);
      req.onupgradeneeded = () => req.result.createObjectStore('image');
      req.onsuccess = () => {const db=req.result;db.onversionchange=()=>db.close();resolve(db);};
      req.onerror = () => reject(Error('ORIGIN_STORAGE_UNAVAILABLE'));
      req.onblocked = () => reject(Error('ORIGIN_STORAGE_BUSY'));
    });
  }
  async function create(profile) {
    checkOrigin(); checkProfile(profile);
    profile = structuredClone(profile);
    const db = await database(), pending = new Map();
    const worker = new root.Worker(new URL('./store-worker.js', root.location.href));
    let serial = 0, closed = false;
    const rejectPending = code => {for (const p of pending.values()) {clearTimeout(p.timer);p.reject(Error(code));}pending.clear();};
    worker.onmessage = ({data}) => {
      const p = pending.get(data.id);if (!p) return;pending.delete(data.id);clearTimeout(p.timer);
      data.error ? p.reject(Error(data.error)) : p.resolve(data.value);
    };
    worker.onerror = () => rejectPending('SQLITE_WORKER_UNAVAILABLE');
    const inspect = (bytes, expected) => new Promise((resolve, reject) => {
      if (closed) return reject(Error('ORIGIN_STORE_CLOSED'));
      const id = ++serial;
      const timer = setTimeout(()=>{pending.delete(id);reject(Error('SQLITE_READBACK_TIMEOUT'));},30000);
      pending.set(id,{resolve,reject,timer});
      worker.postMessage({id, bytes, profile, expected_sha256:expected});
    });
    async function stored() {
      if (closed) fail('ORIGIN_STORE_CLOSED');
      return request(db.transaction('image','readonly').objectStore('image').get('monolith'));
    }
    async function read() {
      const record = await stored();if (!record) return null;
      if (record.origin !== root.location.origin || record.ledger_id !== profile.ledger_id ||
          record.manifest_sha256 !== profile.manifest_sha256 || !(record.bytes instanceof ArrayBuffer)) fail('STORE_IDENTITY_MISMATCH');
      const view = await inspect(record.bytes, record.file_sha256);
      // Cached metadata never replaces byte verification or original SQL readback.
      if (JSON.stringify(view.records) !== JSON.stringify(record.records)) fail('CACHED_READBACK_MISMATCH');
      return {record, view};
    }
    async function accept(bytes) {
      if (!(bytes instanceof ArrayBuffer)) fail('SQLITE_BYTES_REQUIRED');
      bytes = bytes.slice(0); // Freeze caller-owned bytes before validation and commit.
      const old = await read(), view = await inspect(bytes, profile.store_sha256);
      if (old && old.view.records.some((r,i)=>JSON.stringify(r)!==JSON.stringify(view.records[i]))) fail('STORE_ROLLBACK_OR_CONFLICT');
      const record = {origin:root.location.origin, ledger_id:view.ledger_id, manifest_sha256:view.manifest_sha256,
        file_sha256:view.file_sha256, records:view.records, bytes};
      await new Promise((resolve, reject) => {
        const tx = db.transaction('image','readwrite',{durability:'strict'}), store = tx.objectStore('image');
        let failure;
        tx.oncomplete = resolve;
        tx.onabort = tx.onerror = () => reject(Error(failure || (tx.error?.name === 'QuotaExceededError' ? 'ORIGIN_STORAGE_QUOTA' : 'ORIGIN_STORAGE_COMMIT_FAILED')));
        const get = store.get('monolith');
        get.onsuccess = () => {
          if ((get.result?.file_sha256 || null) !== (old?.record.file_sha256 || null)) {failure='CONCURRENT_STORE_CHANGE';tx.abort();return;}
          try {store.put(record,'monolith');}
          catch(error) {failure=error.name==='QuotaExceededError'?'ORIGIN_STORAGE_QUOTA':'ORIGIN_STORAGE_COMMIT_FAILED';tx.abort();}
        };
      });
      const after = await read();
      if (!after || after.view.file_sha256 !== view.file_sha256) fail('POST_COMMIT_READBACK_MISMATCH');
      let persistent = false;
      try {persistent=await root.navigator.storage?.persisted?.() || await root.navigator.storage?.persist?.() || false;} catch (_) { /* policy denial remains visible */ }
      return {...after.view, persistent_storage_granted:persistent === true};
    }
    return {read:async()=>{const result=await read();return result?.view || null;}, accept,
      exportBytes:async()=>{const result=await read();if(!result)fail('NO_ADMITTED_STORE');return result.record.bytes.slice(0);},
      close:()=>{closed=true;worker.terminate();rejectPending('ORIGIN_STORE_CLOSED');db.close();}};
  }
  root.QikvrtOriginStore = {create, checkOrigin};
})(globalThis);
