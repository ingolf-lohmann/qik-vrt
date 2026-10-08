// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Foreground lifecycle only. No background scheduler or repository synchronizer.
export const UPDATE_INTERVAL = 300000, UPDATE_COOLDOWN = 30000;
const namespace = '__qikvrt_release__/', source = new URL(import.meta.url);
export const release = source.pathname.split(namespace)[1]?.split('/')[0] || null;
export const scope = new URL(release ? '../../' : './', source);
const call = (worker, message, timeout = 10000) => new Promise((resolve, reject) => {
  const channel = new MessageChannel();
  const finish = (error, result) => { clearTimeout(timer); channel.port1.close(); error ? reject(error) : resolve(result); };
  const timer = setTimeout(() => finish(Error('OFFLINE_SHELL_NOT_READY')), timeout);
  channel.port1.onmessage = ({data}) => finish(null, data);
  try { worker.postMessage(message, [channel.port2]); } catch (error) { finish(error); }
});
export async function shell() {
  if (!isSecureContext || !navigator.serviceWorker) throw Error('SECURE_BROWSER_STORAGE_REQUIRED');
  const registration = await navigator.serviceWorker.register(new URL('service-worker.js', scope), {scope: scope.href, updateViaCache: 'none'});
  await navigator.serviceWorker.ready;
  if (!navigator.serviceWorker.controller) await new Promise((resolve, reject) => {
    const changed = () => { clearTimeout(timer); resolve(); };
    const timer = setTimeout(() => { navigator.serviceWorker.removeEventListener('controllerchange', changed); reject(Error('OFFLINE_SHELL_NOT_READY')); }, 15000);
    navigator.serviceWorker.addEventListener('controllerchange', changed, {once: true});
  });
  const result = await call(navigator.serviceWorker.controller, {type: 'QIKVRT_OFFLINE_READY'});
  if (!result?.ready) throw Error('OFFLINE_SHELL_NOT_READY');
  // A network-delivered first page has no release binding. Enable editing only
  // after a navigation through the verified worker, including all module imports.
  if (!release) { location.replace(scope.href); await new Promise(() => {}); }
  return registration;
}
export function automaticUpdates(registration, {prepare, unlock, status}) {
  let stopped = false, checking = false, last = -Infinity, retryAt = 0, failures = 0;
  let transition = null, recoveryTimer, advanceTimer, adopting = false;
  const resumeEditing = () => { clearTimeout(recoveryTimer); transition = null; unlock(); };
  const message = async event => {
    const data = event.data;
    if(data?.type==='QIKVRT_RECOVERY'&&event.source===navigator.serviceWorker.controller){await adopt();return;}
    if (data?.type === 'QIKVRT_UPDATE_ABORT' && transition?.attempt === data.attempt) { resumeEditing(); status('waiting'); }
    if (data?.type !== 'QIKVRT_UPDATE_PREPARE' || !event.ports[0] || event.source !== registration.waiting) return;
    // A different concurrent attempt must not release another attempt's lock.
    if (transition && transition.attempt !== data.attempt) { event.ports[0].postMessage({ready: false}); return; }
    transition = data; status('preparing');
    clearTimeout(recoveryTimer);
    recoveryTimer = setTimeout(() => { resumeEditing(); status('waiting'); }, 25000);
    try {
      const ready = await prepare(data.shell);
      if (transition?.attempt !== data.attempt) return;
      event.ports[0].postMessage({ready, shell: release, attempt: data.attempt});
      if (!ready) { resumeEditing(); status('waiting'); }
    } catch { event.ports[0].postMessage({ready: false}); resumeEditing(); status('failed'); }
    finally { event.ports[0].close(); }
  };
  const adopt = async () => {
    if (stopped || adopting) return;
    adopting = true;
    try {
      const next = await call(navigator.serviceWorker.controller, {type: 'QIKVRT_OFFLINE_READY'});
      if (!next.ready) throw Error('OFFLINE_SHELL_NOT_READY');
      if (next.shell === release) return;
      // Also protects against an unexpected controllerchange, e.g. a client
      // created between the last census and skipWaiting. Never reload busy work.
      if (!await prepare(next.shell)) { status('waiting'); return; }
      status('reloading'); location.replace(scope.href);
    } catch { resumeEditing(); status('failed'); }
    finally { adopting = false; }
  };
  const activate = async () => {
    if (!registration.waiting || stopped) return;
    status('waiting');
    const reply = await call(registration.waiting, {type: 'QIKVRT_UPDATE_REQUEST'}, 20000);
    if (reply?.state !== 'ACTIVATING') status('waiting');
  };
  // Retry only the already-staged handoff after an edit/action becomes quiet.
  // This does not add another download timer or a competing update path.
  const schedule = () => { clearTimeout(advanceTimer); if (!stopped) advanceTimer = setTimeout(async () => {
    if (document.hidden) return;
    try { await adopt(); await activate(); } catch { status('failed'); }
  }, 1200); };
  const check = async () => {
    if (stopped || checking || document.hidden || navigator.onLine === false) return;
    const now = Date.now();
    if (now - last < UPDATE_COOLDOWN || now < retryAt) return;
    last = now; checking = true; status('checking');
    try {
      await adopt(); await registration.update(); await activate();
      failures = 0; retryAt = 0;
      if (!registration.waiting && !transition) status('current');
    } catch {
      retryAt = Date.now() + Math.min(UPDATE_INTERVAL, 60000 * 2 ** Math.min(failures++, 3));
      status('failed');
    } finally { checking = false; }
  };
  const installed = () => { const worker = registration.installing; worker?.addEventListener('statechange', () => {
    if (worker.state === 'installed' && registration.waiting) activate().catch(() => status('failed'));
    if (worker.state === 'redundant') status('failed');
  }); };
  // A runtime failure must not discard work entered since the activation
  // checkpoint. The independent boot guard uses the same existing checkpoint.
  const recoveryCheckpoint=()=>prepare(null);
  globalThis.qikvrtRecoveryCheckpoint=recoveryCheckpoint;
  navigator.serviceWorker.addEventListener('message', message);
  navigator.serviceWorker.addEventListener('controllerchange', adopt);
  registration.addEventListener('updatefound', installed);
  for (const name of ['online', 'pageshow', 'focus']) window.addEventListener(name, check);
  document.addEventListener('visibilitychange', check);
  const interval = setInterval(check, UPDATE_INTERVAL);
  installed(); const initialized=check();
  const stop=() => { stopped = true; clearInterval(interval); clearTimeout(advanceTimer); resumeEditing(); registration.removeEventListener('updatefound', installed);
    if(globalThis.qikvrtRecoveryCheckpoint===recoveryCheckpoint)delete globalThis.qikvrtRecoveryCheckpoint;
    navigator.serviceWorker.removeEventListener('message', message); navigator.serviceWorker.removeEventListener('controllerchange', adopt);
    for (const name of ['online', 'pageshow', 'focus']) window.removeEventListener(name, check);
    document.removeEventListener('visibilitychange', check);
  };
  stop.initialized=initialized;stop.schedule=schedule;return stop;
}
