// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
"use strict";
const el = id => document.getElementById(id);
let token = "", sessionId = null, busy = false;
let loginPopup = null, loginState = null, oidcEnabled = false;
let terminalRequired = location.hash === "#terminal", terminalBound = false;
async function request(path, body, headers = {}) {
  if (terminalRequired && !terminalBound && !path.startsWith("auth/") && !path.startsWith("terminal/") && path !== "capabilities") {
    throw new Error("Zuerst den Personal-Modus ausdrücklich aktivieren");
  }
  const response = await fetch(`/personal/${path}`, {
    method: body ? "POST" : "GET", credentials: "omit", cache: "no-store",
    redirect: "error",
    headers: {"Authorization": `Bearer ${token}`, ...(body ? {"Content-Type": "application/json"} : {}), ...headers},
    ...(body ? {body: JSON.stringify({...body, confirmed: true})} : {})
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.reason || `HTTP ${response.status}`);
  return result;
}
function render(result) {
  const session = result.session;
  sessionId = session.id;
  el("session").textContent = `${session.mode} · ${session.id} · ${session.status}`;
  el("history").replaceChildren();
  for (const turn of session.history) {
    const input = document.createElement("pre"), output = document.createElement("pre");
    input.textContent = `Eingabe\n${turn.intent.input}`;
    output.textContent = `Entwurf · ${turn.resolved_model}\n${turn.text}`;
    el("history").append(input, output);
  }
}
async function loadSessions() {
  const result = await request("sessions");
  el("sessions").replaceChildren();
  for (const session of result.sessions) {
    const option = document.createElement("option");
    option.value = session.id;
    option.textContent = `${session.mode} · ${session.id} · ${session.turns} Antworten · ${session.status}`;
    el("sessions").append(option);
  }
}
async function action(fn) {
  if (busy) return;
  busy = true;
  for (const button of document.querySelectorAll("button")) button.disabled = true;
  el("status").textContent = "Anfrage läuft …";
  try { await fn(); } catch (error) {
    el("status").textContent = `BLOCK: ${error.message}. Bei ungeklärtem Provider-Ergebnis zuerst gespeicherten Stand prüfen.`;
  } finally {
    busy = false;
    for (const button of document.querySelectorAll("button")) button.disabled = false;
    el("sign-in").disabled = !oidcEnabled;
    el("renew").disabled = el("sign-out").disabled = !oidcEnabled || !token;
    el("token").disabled = el("connect").disabled = oidcEnabled;
    el("terminal-bind").disabled = el("terminal-readback").disabled = !oidcEnabled || !token;
  }
}
fetch("/personal/auth/info", {credentials: "omit", cache: "no-store"}).then(response => response.json()).then(info => {
  oidcEnabled = info.oidc_enabled === true;
  terminalRequired = terminalRequired || info.native_terminal_enabled === true;
  el("identity").textContent = oidcEnabled ? `Anmeldung über ${info.issuer}` : "Lokale Kopplung im bisherigen Speichermodus. Dauerhaftes SSO ist hier nicht konfiguriert.";
  el("sign-in").disabled = !oidcEnabled;
  el("token").disabled = el("connect").disabled = oidcEnabled;
}).catch(() => { el("identity").textContent = "Anmeldekonfiguration nicht erreichbar."; });
el("sign-in").addEventListener("click", () => {
  if (busy || !oidcEnabled) return;
  el("provider-sign-out").replaceChildren();
  loginPopup = window.open("about:blank", "qikvrt-personal-sign-in", "popup,width=560,height=720");
  if (!loginPopup) { el("status").textContent = "Bitte das Anmeldefenster für diese lokale Seite erlauben."; return; }
  action(async () => {
    const result = await request("auth/start", {});
    loginState = result.state;
    loginPopup.location = result.authorization_url;
    el("status").textContent = "Anmeldung im Identitätsanbieter abschließen.";
  });
});
window.addEventListener("message", event => {
  if (event.origin !== location.origin || event.source !== loginPopup || !loginState ||
      event.data?.type !== "qikvrt-oidc-result" || event.data.state !== loginState ||
      typeof event.data.token !== "string") return;
  loginState = null; loginPopup = null;
  token = event.data.token;
  terminalBound = false;
  action(async () => {
    await request("capabilities");
    if (!terminalRequired) await loadSessions();
    el("status").textContent = terminalRequired ? "Angemeldet. Jetzt Personal-Modus aktivieren; es wurde noch keine Aufgabe übertragen." :
      "Identität angemeldet. Modellzugang und Firefox-Produktabnahme bleiben getrennt prüfbar.";
  });
});
function sorted(value) {
  if (Array.isArray(value)) return value.map(sorted);
  return value && typeof value === "object" ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sorted(value[key])])) : value;
}
async function hash(value) {
  const bytes = new TextEncoder().encode(JSON.stringify(sorted(value)));
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), b => b.toString(16).padStart(2, "0")).join("");
}
async function verifyTransition(result, plan = null) {
  const event = result.native_event;
  if (!result.readback_verified || result.state !== "EFFECT_ACK_DONE" || result.ordinary_release !== true ||
      result.effect_scope !== "AUTHENTICATED_NATIVE_PERSONAL_BINDING_ONLY" || !event ||
      event.id !== result.event_id || `sha256:${event.ledger_digest}` !== result.ledger_digest ||
      JSON.stringify(sorted(event.subject)) !== JSON.stringify(sorted(result.subject)) ||
      event.payload?.product_acceptance !== false ||
      (plan && JSON.stringify(sorted(event.payload.transition)) !== JSON.stringify(sorted(plan)))) throw new Error("Übergangsbindung stimmt nicht überein");
  const {id, ledger_digest, ...body} = event;
  if (await hash(body) !== ledger_digest || !/^[0-9a-f]{32}:[1-9][0-9]*$/.test(id)) throw new Error("Nativer Readback ist nicht hashgebunden");
  terminalBound = true;
}
el("terminal-bind").addEventListener("click", event => {
  if (!event.isTrusted || !oidcEnabled || !token || busy) return;
  return action(async () => {
    terminalBound = false;
    const prepared = await request("terminal/prepare", {}, {"Effect-Ack-Request": "v=1, mode=prepare"});
    if (!prepared.plan || await hash(prepared.plan) !== prepared.record_hash ||
        !/^[A-Za-z0-9_-]{32,128}$/.test(prepared.commit_token || "")) throw new Error("Vorbereitung ist nicht hashgebunden");
    const bytes = prepared.record_hash.match(/../g).map(value => String.fromCharCode(parseInt(value, 16))).join("");
    // Dispatch exactly once; an ambiguous response requires explicit readback.
    const committed = await request("terminal/commit", {}, {"Effect-Ack-Request":
      `v=1, mode=commit, token=:${btoa(prepared.commit_token)}:, hash=:${btoa(bytes)}:`});
    const readback = await request("terminal/readback");
    if (committed.event_id !== readback.event_id || committed.ledger_digest !== readback.ledger_digest) throw new Error("Unabhängiger Readback fehlt");
    await verifyTransition(readback, prepared.plan);
    await loadSessions();
    el("status").textContent = "Personal-Übergang frisch gebunden und unabhängig gelesen. Modell, Firefox-Aktivierung und Auslieferung bleiben separat.";
  });
});
el("terminal-readback").addEventListener("click", event => {
  if (!event.isTrusted || !oidcEnabled || !token || busy) return;
  return action(async () => {
    await verifyTransition(await request("terminal/readback"));
    await loadSessions();
    el("status").textContent = "Vorhandener nativer Personal-Übergang unabhängig gelesen.";
  });
});
el("renew").addEventListener("click", () => action(async () => {
  await request("auth/renew", {});
  el("status").textContent = "Sitzung erneuert und geschützter Speicher zurückgelesen.";
}));
el("sign-out").addEventListener("click", () => action(async () => {
  let result;
  try { result = await request("auth/logout", {}); } finally {
    // The backend may already have invalidated admission before a lost ACK.
    // Always discard this page's bearer; never retry logout automatically.
    token = ""; sessionId = null; terminalBound = false;
    el("history").replaceChildren(); el("sessions").replaceChildren();
    el("provider-sign-out").replaceChildren();
    el("session").textContent = "Lokal getrennt. Anbieterstatus separat prüfen.";
  }
  el("status").textContent = result.remote_revocation === "ENDPOINT_ACKNOWLEDGED_NOT_INDEPENDENTLY_ATTESTED" ?
    "Lokal abgemeldet. Der Anbieter hat den Token-Widerruf bestätigt; die globale Anbieter-Sitzung bleibt separat." :
    result.remote_revocation === "PROVIDER_SESSION_MANAGEMENT_REQUIRED" ?
    "Lokal abgemeldet. Microsoft-Tokens müssen bei Bedarf zusätzlich über die Konto- oder Tenant-Sitzungsverwaltung widerrufen werden." :
    `Lokal abgemeldet. Anbieter-Widerruf: ${result.remote_revocation}.`;
  if (result.provider_logout_url) {
    const link = document.createElement("a");
    link.href = result.provider_logout_url;
    link.target = "_blank"; link.rel = "noopener noreferrer";
    link.textContent = "Zusätzlich beim Identitätsanbieter abmelden (kein Token-Widerruf)";
    el("provider-sign-out").append(link);
  }
}));
el("connect").addEventListener("click", () => action(async () => {
  token = el("token").value;
  el("token").value = "";
  const state = await request("capabilities");
  await loadSessions();
  el("status").textContent = state.authenticated_runtime_readback ? "Lokaler Client und frischer Modell-Runtime-Pfad belegt." : "Lokaler Client verbunden. Reale Modellantwort noch nicht belegt.";
}));
el("restore").addEventListener("click", () => action(async () => {
  render(await request(`session/${el("sessions").value}`));
  el("status").textContent = "Gespeicherter Verlauf geöffnet.";
}));
el("create").addEventListener("click", () => action(async () => {
  render(await request("create", {mode: el("mode").value, task: el("task").value, sources: JSON.parse(el("sources").value)}));
  await loadSessions();
  el("status").textContent = "Modellentwurf gespeichert; fachliche Prüfung offen.";
}));
for (const [button, route] of [["send", "turn"], ["resume", "resume"]]) {
  el(button).addEventListener("click", () => action(async () => {
    if (!sessionId) throw new Error("Zuerst ein Gespräch öffnen");
    const text = el("message").value || (route === "resume" ? "Bitte setze die offene Arbeit fort und benenne den belegten Arbeitsstand." : "");
    render(await request(route, {session_id: sessionId, text}));
    el("message").value = "";
    el("status").textContent = "Modellentwurf gespeichert; fachliche Prüfung offen.";
  }));
}

async function textHash(value) {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value))),
    b => b.toString(16).padStart(2, "0")).join("");
}
el("search-local").addEventListener("click", event => {
  if (!event.isTrusted || !token || busy) return;
  return action(async () => {
    el("search-results").replaceChildren();
    const query = el("search-query").value;
    const original = JSON.parse(el("sources").value);
    if (!Array.isArray(original) || !original.length || original.length > 32) throw new Error("Bitte 1 bis 32 Quellenauszüge angeben");
    const sources = [];
    for (const row of original) {
      if (typeof row.id !== "string" || typeof row.text !== "string" || !row.text.trim() || row.text.length > 512) {
        throw new Error("Jeder Quellenauszug benötigt eine ID und höchstens 512 Zeichen Text");
      }
      sources.push({id: row.id, text: row.text, sha256: await textHash(row.text)});
    }
    const ordered = sources.slice().sort((a,b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
    const body = {query, sources, limit: 3};
    const result = await request("search", body);
    if (result.schema !== "qikvrt_local_source_ranking_v1" ||
        result.model !== "perplexity-ai/pplx-embed-v2-late-0.6b" ||
        result.model_revision !== "8fc2de24534aa3610d85fa59c463313a5f096455" ||
        result.evidence_class !== "LOCAL_MODEL_INFERENCE" ||
        result.scope !== "LOCAL_SOURCE_RANKING_ONLY" || result.productive_acceptance !== false ||
        result.field_values_extracted !== false || result.request_sha256 !== await hash({...body, sources: ordered}) ||
        !Array.isArray(result.results) || result.results.length > 3) throw new Error("Suchergebnis ist nicht an diese Anfrage gebunden");
    const verified = [], seen = new Set();
    for (const hit of result.results) {
      const source = sources.find(row => row.id === hit.source_id && row.sha256 === hit.source_sha256);
      if (!source || seen.has(source.id) || typeof hit.score !== "number" || !Number.isFinite(hit.score)) throw new Error("Quellenbindung stimmt nicht überein");
      seen.add(source.id); verified.push(source);
    }
    for (const source of verified) {
      const item = document.createElement("li");
      item.textContent = `${source.id}: ${source.text}`;
      el("search-results").append(item);
    }
    el("status").textContent = "Lokale Quellenvorschläge geladen. Herkunft und Inhalt vor Verwendung prüfen.";
  });
});
