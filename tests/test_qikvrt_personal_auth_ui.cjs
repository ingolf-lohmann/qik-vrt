// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
"use strict";
// Simulated DOM/fetch control tests. No browser, vault or person signs in.
const fs = require("node:fs"), vm = require("node:vm"), assert = require("node:assert/strict");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../personal/ingolf-lohmann/firefox-assistant/ui.js"), "utf8");

async function scenario(lostAck) {
  const nodes = new Map(), events = {}, calls = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {textContent: "", children: [], disabled: false,
      addEventListener(type, fn) { events[id + ":" + type] = fn; },
      replaceChildren() { this.children = []; }, append(...items) { this.children.push(...items); }});
    return nodes.get(id);
  }
  let opens = 0;
  const sandbox = {
    document: {getElementById: node, querySelectorAll: () => [], createElement: () => ({})},
    location: {origin: "http://127.0.0.1:8771"},
    window: {addEventListener() {}, open() { opens++; }},
    fetch: async url => {
      calls.push(url);
      if (url.endsWith("/info")) return {json: async () => ({oidc_enabled: true, issuer: "https://identity.example.test"})};
      if (lostAck) throw Error("SIMULATED_LOST_ACK");
      return {ok: true, json: async () => ({remote_revocation: "PROVIDER_SESSION_MANAGEMENT_REQUIRED",
        provider_logout_url: "https://identity.example.test/logout?client_id=SIMULATED_APP"})};
    }
  };
  vm.createContext(sandbox); vm.runInContext(source, sandbox);
  await new Promise(resolve => setImmediate(resolve));
  vm.runInContext("token='SIMULATED_BROWSER_BEARER';sessionId='SIMULATED_SESSION'", sandbox);
  await events["sign-out:click"]();
  assert.equal(vm.runInContext("token", sandbox), "");
  assert.equal(vm.runInContext("sessionId", sandbox), null);
  assert.equal(opens, 0, "provider-wide sign-out must require another explicit action");
  assert.equal(calls.filter(url => url.endsWith("/logout")).length, 1, "never repeat an ambiguous logout");
  assert(calls.every(url => url.startsWith("/personal/")));
  if (lostAck) {
    assert.equal(node("provider-sign-out").children.length, 0);
    assert(node("status").textContent.includes("SIMULATED_LOST_ACK"));
  } else {
    const link = node("provider-sign-out").children[0];
    assert.equal(link.href, "https://identity.example.test/logout?client_id=SIMULATED_APP");
    assert.equal(link.rel, "noopener noreferrer");
    assert(link.textContent.includes("kein Token-Widerruf"));
    assert(node("status").textContent.includes("Microsoft-Tokens"));
  }
}

(async () => {
  await scenario(false); await scenario(true);
  process.stdout.write("PASS: 2 Personal logout controller scenarios; simulated DOM/fetch, no actual browser or authenticated session.\n");
})().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
