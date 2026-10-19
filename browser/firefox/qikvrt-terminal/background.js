// Source: policy/CANONICAL_UPSTREAM_REMOTE_V1.json. Mirror entrypoints never select the observer source.
const AUTHORITY = "ingolf-lohmann/qik-vrt";
const DEFAULT_BACKEND = "http://127.0.0.1:8771";
const ALLOWED_BACKENDS = new Set(["http://127.0.0.1:8771", "http://localhost:8771"]);
const WATCHDOG_ALARM = "qikvrt-repository-watchdog";
const WATCHDOG_PERIOD_MINUTES = 5;
const STATE_MAP = new Map([
  ["nack", "EFFECT_NACK"],
  ["continue", "EFFECT_ACK_CONTINUE"],
  ["done", "EFFECT_ACK_DONE"],
  ["isolate", "EFFECT_ACK_ISOLATE"],
  ["block", "EFFECT_ACK_BLOCK"]
]);

function fail(reason) {
  return {ok: false, state: "HOLD", ordinary_release: false, reason};
}

// Opens the packaged frontend from any page, without additional host access.
browser.action.onClicked.addListener(() => {
  browser.tabs.create({url: browser.runtime.getURL("client.html")})
    .catch(error => console.error("QIKVRT client could not open:", error.message));
});

function canonicalValue(value) {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonicalValue(value[key])]));
  }
  return value;
}

async function contentHash(value) {
  const bytes = new TextEncoder().encode(JSON.stringify(canonicalValue(value)));
  return bytesToHex(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)));
}

async function github(path) {
  const response = await fetch(`https://api.github.com/repos/${AUTHORITY}${path}`, {
    method: "GET",
    credentials: "omit",
    headers: {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    cache: "no-store"
  });
  if (!response.ok) throw new Error(`github ${response.status}`);
  return response.json();
}

async function observeAuthority() {
  const ref = await github("/git/ref/heads/main");
  const head = ref && ref.object && ref.object.sha;
  if (!/^[0-9a-f]{40}$/.test(head || "")) return fail("main head unavailable");
  const commit = await github(`/git/commits/${head}`);
  const tree = commit && commit.tree && commit.tree.sha;
  if (!/^[0-9a-f]{40}$/.test(tree || "")) return fail("main tree unavailable");
  const runs = await github("/actions/runs?branch=main&per_page=30");
  const wanted = [
    "QIK-VRT autonomous bounded self-heal",
    "QIKVRT reflexive repository watchdog",
    "QIKVRT self-heal terminal monitor"
  ];
  const latest = {};
  for (const name of wanted) {
    const run = (runs.workflow_runs || []).find(item => item.name === name);
    latest[name] = run ? {
      id: run.id,
      status: run.status,
      conclusion: run.conclusion,
      head_sha: run.head_sha,
      html_url: run.html_url
    } : null;
  }
  return {
    ok: true,
    schema: "qikvrt_terminal_frame_v1",
    observed_at: new Date().toISOString(),
    source: {repository: AUTHORITY, ref: "refs/heads/main", head, tree},
    workflows: latest,
    terminal_semantics: {
      rendering_is_authorization: false,
      ordinary_release_requires: "VALID_EFFECT_ACK_DONE"
    }
  };
}

async function persistWatchdogFrame() {
  let frame;
  try {
    frame = await observeAuthority();
  } catch (error) {
    frame = fail(error.message);
    frame.observed_at = new Date().toISOString();
  }
  const previous = await browser.storage.local.get("qikvrtWatchdogFrame");
  const prior = previous.qikvrtWatchdogFrame || null;
  const materialChange = !prior || !frame.ok || !prior.ok ||
    !prior.source || !frame.source ||
    prior.source.head !== frame.source.head ||
    prior.source.tree !== frame.source.tree ||
    JSON.stringify(prior.workflows || {}) !== JSON.stringify(frame.workflows || {});
  await browser.storage.local.set({
    qikvrtWatchdogFrame: frame,
    qikvrtWatchdogMaterialChange: Boolean(materialChange)
  });
  return frame;
}

async function ensureWatchdog() {
  const current = await browser.alarms.get(WATCHDOG_ALARM);
  if (!current) await browser.alarms.create(WATCHDOG_ALARM, {periodInMinutes: WATCHDOG_PERIOD_MINUTES});
  return persistWatchdogFrame();
}

function decodeSfBytes(value) {
  if (typeof value !== "string" || value.length < 2 || value[0] !== ":" || value[value.length - 1] !== ":") return null;
  try {
    const binary = atob(value.slice(1, -1));
    return Uint8Array.from(binary, ch => ch.charCodeAt(0));
  } catch (_) {
    return null;
  }
}

function bytesToHex(bytes) {
  return Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
}

function asciiFromBytes(bytes) {
  if (!bytes || bytes.some(byte => byte > 0x7f)) return null;
  return String.fromCharCode(...bytes);
}

function sfBytesFromAscii(value) {
  if (typeof value !== "string" || !/^[\x20-\x7e]+$/.test(value)) throw new Error("non-ASCII commit token");
  return `:${btoa(value)}:`;
}

function sfBytesFromHex(hex) {
  if (!/^[0-9a-f]{64}$/.test(hex || "")) throw new Error("invalid record hash");
  let binary = "";
  for (let i = 0; i < hex.length; i += 2) binary += String.fromCharCode(parseInt(hex.slice(i, i + 2), 16));
  return `:${btoa(binary)}:`;
}

function parseStructuredDictionary(raw) {
  if (typeof raw !== "string" || !raw.trim()) return null;
  const members = new Map();
  for (const part of raw.split(",")) {
    const index = part.indexOf("=");
    if (index <= 0) return null;
    const key = part.slice(0, index).trim().toLowerCase();
    const value = part.slice(index + 1).trim();
    if (!/^[a-z*][a-z0-9_.*-]*$/.test(key) || members.has(key)) return null;
    members.set(key, value);
  }
  return members;
}

function parseEffectAck(raw) {
  const members = parseStructuredDictionary(raw);
  if (!members) return null;
  const v = Number(members.get("v"));
  const stateToken = (members.get("state") || "").toLowerCase();
  const state = STATE_MAP.get(stateToken);
  const hashBytes = decodeSfBytes(members.get("hash"));
  const tokenBytes = members.has("token") ? decodeSfBytes(members.get("token")) : null;
  if (v !== 1 || !state || !hashBytes || hashBytes.length !== 32) return null;
  const commitToken = tokenBytes ? asciiFromBytes(tokenBytes) : null;
  if (members.has("token") && !commitToken) return null;
  return {v, state, record_hash: bytesToHex(hashBytes), commit_token: commitToken, raw};
}

async function backendBase() {
  const stored = await browser.storage.local.get("qikvrtBackend");
  const value = stored.qikvrtBackend || DEFAULT_BACKEND;
  if (!ALLOWED_BACKENDS.has(value)) throw new Error("backend outside allowlist");
  return value;
}

async function backendRequest(path, init) {
  const base = await backendBase();
  const response = await fetch(`${base}${path}`, {credentials: "omit", cache: "no-store", redirect: "error", ...init});
  const effect = parseEffectAck(response.headers.get("Effect-Ack"));
  const type = response.headers.get("content-type") || "";
  const body = type.includes("application/json") ? await response.json() : {text: await response.text()};
  return {http_status: response.status, effect_ack: effect, body};
}

async function discover() {
  const result = await backendRequest("/.well-known/effect-ack", {method: "GET"});
  return {...result, discovered: result.http_status >= 200 && result.http_status < 300};
}

async function validateRecord(recordResult, hash, inputHash) {
  const record = recordResult.body;
  const ack = recordResult.effect_ack;
  if (recordResult.http_status !== 200 || !ack || ack.state !== "EFFECT_ACK_DONE" ||
      ack.record_hash !== hash || !record ||
      record.schema !== "qikvrt_effect_ack_http_terminal_record_v1" ||
      record.state !== "EFFECT_ACK_DONE" || record.ordinary_release !== true ||
      record.policy_allows_release !== true || record.external_effect !== "NONE" ||
      record.record_hash !== `sha256:${hash}` || record.input_hash !== `sha256:${inputHash}`) {
    return false;
  }
  const {record_hash, ...bytes} = record;
  return await contentHash(bytes) === hash;
}

async function validatePreparedRecord(result, inputHash) {
  const effect = result.effect_ack;
  const body = result.body;
  if (!effect || effect.state !== "EFFECT_ACK_DONE") return fail("prepare is not DONE");
  if (!body || typeof body.record_hash !== "string" || !/^[0-9a-f]{64}$/.test(body.record_hash)) return fail("prepare record hash unavailable");
  if (body.record_hash !== effect.record_hash) return fail("compact/full record hash mismatch");
  if (!effect.commit_token || body.commit_token !== effect.commit_token) return fail("compact/full commit token mismatch");
  if (body.record_url !== `/effect-ack/records/${body.record_hash}`) return fail("bound record URL unavailable");
  const recordResult = await backendRequest(body.record_url, {method: "GET"});
  const record = recordResult.body;
  if (!await validateRecord(recordResult, body.record_hash, inputHash)) return fail("full record digest, input or release binding mismatch");
  return {...result, record_validated: true, full_record: record, ordinary_release: false};
}

async function prepareEffect(payload) {
  const discovery = await discover();
  if (!discovery.discovered) return fail("effect-ack capability not discovered");
  const result = await backendRequest("/terminal/prepare", {
    method: "POST",
    headers: {"Content-Type": "application/json", "Effect-Ack-Request": "v=1, mode=prepare"},
    body: JSON.stringify(payload)
  });
  if (!result.effect_ack) return fail("missing or malformed Effect-Ack response");
  if (result.effect_ack.state !== "EFFECT_ACK_DONE") return {...result, record_validated: false, ordinary_release: false};
  return validatePreparedRecord(result, await contentHash(payload));
}

async function commitEffect(payload) {
  if (!payload || payload.confirmed !== true) return fail("explicit commit confirmation required");
  const prepared = payload.prepared;
  if (!prepared || prepared.record_validated !== true || !prepared.effect_ack || prepared.effect_ack.state !== "EFFECT_ACK_DONE") return fail("validated DONE prepare result required");
  const token = prepared.effect_ack.commit_token;
  const hash = prepared.effect_ack.record_hash;
  if (typeof token !== "string" || typeof hash !== "string") return fail("prepare binding unavailable");
  const inputHash = await contentHash(payload.request || {});
  const revalidated = await validatePreparedRecord(prepared, inputHash);
  if (revalidated.record_validated !== true) return revalidated;
  const effectAckRequest = `v=1, mode=commit, token=${sfBytesFromAscii(token)}, hash=${sfBytesFromHex(hash)}`;
  // A dispatched commit is never automatically retried, including lost replies.
  try {
  const result = await backendRequest("/terminal/commit", {
    method: "POST",
    headers: {"Content-Type": "application/json", "Effect-Ack-Request": effectAckRequest},
    body: JSON.stringify(payload.request || {})
  });
  const done = result.http_status === 200 && result.effect_ack &&
    result.effect_ack.state === "EFFECT_ACK_DONE" && result.body && result.body.ordinary_release === true;
  if (!done) return {...result, ordinary_release: false, commit_attempted: true, retry_allowed: false};
  const successorHash = result.effect_ack.record_hash;
  if (successorHash === hash) {
    return {...fail("prepare record cannot attest the committed effect"), commit_attempted: true, retry_allowed: false};
  }
  const record = await backendRequest(`/effect-ack/records/${successorHash}`, {method: "GET"});
  if (!await validateRecord(record, successorHash, inputHash)) {
    return {...fail("commit successor record failed independent readback"), commit_attempted: true, retry_allowed: false};
  }
  const state = await backendRequest("/terminal/state", {method: "GET"});
  const event = state.body && state.body.last_event;
  if (state.http_status !== 200 || !event || event.kind !== "TERMINAL_INPUT_ACCEPTED" ||
      event.input_hash !== inputHash || event.record_hash !== hash || event.external_effect !== "NONE" ||
      JSON.stringify(canonicalValue(event)) !== JSON.stringify(canonicalValue(result.body.post_effect))) {
    return {...fail("committed input failed independent state readback"), commit_attempted: true, retry_allowed: false};
  }
  return {...result, ordinary_release: true, readback_verified: true,
    readback_record: record.body, readback_event: event, commit_attempted: true, retry_allowed: false,
    effect_scope: "LOOPBACK_TERMINAL_INPUT_ONLY", productive_effect_verified: false};
  } catch (error) {
    return {...fail(error.message), commit_attempted: true, retry_allowed: false};
  }
}

browser.runtime.onInstalled.addListener(() => { ensureWatchdog().catch(() => undefined); });
browser.runtime.onStartup.addListener(() => { ensureWatchdog().catch(() => undefined); });
browser.alarms.onAlarm.addListener(alarm => { if (alarm.name === WATCHDOG_ALARM) persistWatchdogFrame().catch(() => undefined); });
ensureWatchdog().catch(() => undefined);

browser.runtime.onMessage.addListener(message => {
  if (!message || typeof message.kind !== "string") return Promise.resolve(fail("invalid message"));
  if (message.kind === "OBSERVE_AUTHORITY") return persistWatchdogFrame().catch(error => fail(error.message));
  if (message.kind === "DISCOVER_EFFECT_ACK") return discover().catch(error => fail(error.message));
  if (message.kind === "PREPARE_EFFECT") return prepareEffect(message.payload).catch(error => fail(error.message));
  if (message.kind === "COMMIT_EFFECT") return commitEffect(message.payload).catch(error => fail(error.message));
  return Promise.resolve(fail("unknown message kind"));
});
