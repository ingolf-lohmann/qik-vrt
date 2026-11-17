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

async function transitionScenario(mode) {
  const nodes = new Map(), events = {}, calls = [];
  const crypto = require('node:crypto');
  const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object' ?
    Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
  const hash = value => crypto.createHash('sha256').update(JSON.stringify(stable(value))).digest('hex');
  const subject = {repository:'ingolf-lohmann/qik-vrt',pr:542,head:'a'.repeat(40),tree:'b'.repeat(40)};
  const plan = {schema:'qikvrt_personal_terminal_transition_v1',subject,from:'standard',to:'personal'};
  const body = {schema:'qikvrt_temdd_event_v1',kind:'ACTION',subject,
    payload:{product_acceptance:false,transition:plan}};
  const event = {...body,id:'c'.repeat(32)+':1',ledger_digest:hash(body)};
  const result = {state:'EFFECT_ACK_DONE',ordinary_release:true,readback_verified:true,subject,
    effect_scope:'AUTHENTICATED_NATIVE_PERSONAL_BINDING_ONLY',event_id:event.id,ledger_digest:'sha256:'+event.ledger_digest,native_event:event};
  const node = id => {
    if (!nodes.has(id)) nodes.set(id,{textContent:'',children:[],disabled:false,
      addEventListener(type,fn){events[id+':'+type]=fn;}, replaceChildren(){this.children=[];}, append(...items){this.children.push(...items);}});
    return nodes.get(id);
  };
  const sandbox = {console,TextEncoder,Uint8Array,btoa,crypto:crypto.webcrypto,
    document:{getElementById:node,querySelectorAll:()=>[],createElement:()=>({})},
    location:{origin:'http://127.0.0.1:8771',hash:'#terminal'},window:{addEventListener(){},open(){throw Error('no implicit login');}},
    fetch:async (url,init={})=>{
      calls.push({url,init});
      if(url.endsWith('/info'))return {json:async()=>({oidc_enabled:true,native_terminal_enabled:true})};
      let data;
      if(url.endsWith('/prepare')) data={plan,record_hash:mode==='bad-plan'?'0'.repeat(64):hash(plan),commit_token:'T'.repeat(40)};
      else if(url.endsWith('/commit')) {
        if(mode==='lost-ack')throw Error('SIMULATED_LOST_COMMIT_ACK');
        assert(init.headers['Effect-Ack-Request'].includes('mode=commit'));
        data=result;
      } else if(url.endsWith('/readback')) {
        data=mode==='tampered-readback'?{...result,native_event:{...event,payload:{...body.payload,product_acceptance:true}}}:result;
      } else if(url.endsWith('/sessions')) data={sessions:[]};
      else throw Error('unexpected request '+url);
      return {ok:true,json:async()=>data};
    }};
  vm.createContext(sandbox);vm.runInContext(source,sandbox);
  await new Promise(resolve=>setImmediate(resolve));
  vm.runInContext("token='SIMULATED_PERSONAL_ONLY_BEARER'",sandbox);
  await events['terminal-bind:click']({isTrusted:mode!=='synthetic'});
  const count = suffix => calls.filter(x=>x.url.endsWith(suffix)).length;
  if(mode==='synthetic') {assert.equal(count('/prepare'),0);return;}
  if(mode==='bad-plan') {assert.equal(count('/commit'),0);return;}
  assert.equal(count('/commit'),1);
  if(mode==='lost-ack') {
    assert.equal(count('/readback'),0);
    assert.equal(vm.runInContext('terminalBound',sandbox),false);
    await events['terminal-readback:click']({isTrusted:true});
    assert.equal(count('/commit'),1);
    assert.equal(count('/readback'),1);
  }
  assert.equal(vm.runInContext('terminalBound',sandbox),mode!=='tampered-readback');
  assert.equal(count('/sessions'),mode==='tampered-readback'?0:1);
  assert(calls.every(x=>x.url.startsWith('/personal/')));
}

(async () => {
  await scenario(false); await scenario(true);
  for(const mode of ['success','synthetic','bad-plan','tampered-readback','lost-ack']) await transitionScenario(mode);
  process.stdout.write("PASS: 7 Personal controller scenarios; simulated DOM/fetch, no actual browser or authenticated session.\n");
})().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
