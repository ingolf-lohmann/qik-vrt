// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
"use strict";
const el = id => document.getElementById(id);
let token = "", sessionId = null, busy = false;
let loginPopup = null, loginState = null, oidcEnabled = false;
async function request(path, body) {
  const response = await fetch(`/personal/${path}`, {
    method: body ? "POST" : "GET", credentials: "omit", cache: "no-store",
    headers: {"Authorization": `Bearer ${token}`, ...(body ? {"Content-Type": "application/json"} : {})},
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
  }
}
fetch("/personal/auth/info", {credentials: "omit", cache: "no-store"}).then(response => response.json()).then(info => {
  oidcEnabled = info.oidc_enabled === true;
  el("identity").textContent = oidcEnabled ? `Anmeldung über ${info.issuer}` : "Lokale Kopplung im bisherigen Speichermodus. Dauerhaftes SSO ist hier nicht konfiguriert.";
  el("sign-in").disabled = !oidcEnabled;
  el("token").disabled = el("connect").disabled = oidcEnabled;
}).catch(() => { el("identity").textContent = "Anmeldekonfiguration nicht erreichbar."; });
el("sign-in").addEventListener("click", () => {
  if (busy || !oidcEnabled) return;
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
  action(async () => {
    await request("capabilities");
    await loadSessions();
    el("status").textContent = "Identität angemeldet. Modellzugang und Firefox-Produktabnahme bleiben getrennt prüfbar.";
  });
});
el("renew").addEventListener("click", () => action(async () => {
  await request("auth/renew", {});
  el("status").textContent = "Sitzung erneuert und geschützter Speicher zurückgelesen.";
}));
el("sign-out").addEventListener("click", () => action(async () => {
  const result = await request("auth/logout", {});
  token = ""; sessionId = null;
  el("history").replaceChildren(); el("sessions").replaceChildren();
  el("session").textContent = "Abgemeldet.";
  el("status").textContent = result.remote_revocation === "ENDPOINT_ACKNOWLEDGED_NOT_INDEPENDENTLY_ATTESTED" ?
    "Lokal abgemeldet. Der Anbieter hat den Token-Widerruf bestätigt; die globale Anbieter-Sitzung bleibt separat." :
    `Lokal abgemeldet. Anbieter-Widerruf: ${result.remote_revocation}.`;
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
