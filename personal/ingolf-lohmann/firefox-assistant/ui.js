// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
"use strict";
const el = id => document.getElementById(id);
let token = "", sessionId = null, busy = false;
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
  }
}
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
