// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
"use strict";
// Offline controls use a simulated DOM and WebExtension APIs. No native Firefox,
// model, Mesh authentication, external website or signed add-on is exercised.
const assert = require("node:assert/strict"), vm = require("node:vm"), fs = require("node:fs");
const {webcrypto} = require("node:crypto"), path = require("node:path");
const sourcePath = path.join(__dirname, "../browser/firefox/qikvrt-terminal/options.js");
const source = fs.readFileSync(sourcePath, "utf8");
const {parseSource, normalizeField, planFill, formOperation} = require(sourcePath);
let count = 0;
function test(name, fn) { fn(); count++; process.stdout.write(`PASS ${name}\n`); }

test("JSON and labelled Unicode facts, without a provider or region", () => {
  assert.deepEqual(parseSource('{"名前":"小林", "المدينة":"تونس", "Code postal":75001}'),
    [{key: "名前", value: "小林"}, {key: "المدينة", value: "تونس"}, {key: "Code postal", value: "75001"}]);
  assert.deepEqual(parseSource("Nom: Test\r\nAdresse: https://example.test/a:b"),
    [{key: "Nom", value: "Test"}, {key: "Adresse", value: "https://example.test/a:b"}]);
  assert.equal(normalizeField("ＮＡＭＥ"), "name");
});
test("reject free prose, nested objects, executable structures, empty and oversized facts", () => {
  for (const text of ["unstructured prose", "{}", '{"nested":{"x":"y"}}', '{"x":null}', '{"x":true}',
    '{"x":["y"]}', '{"x":""}', '{"x":1e999}', '{"Name":"one","Name":"two"}',
    '{"N\\u0061me":"one","Name":"two"}', "Name: one\nＮＡＭＥ: two", "x:" + "a".repeat(4097),
    "x:" + "é".repeat(20000), JSON.stringify(Object.fromEntries(Array.from({length:65}, (_, i) => [i,"x"])))]) {
    assert.throws(() => parseSource(text), text.slice(0, 40));
  }
});
const facts = (id, text) => ({id, revision: id.repeat(64).slice(0, 64), locator: `fixture:${id}`, facts: parseSource(text)});
test("exact names only; conflicts remain visible instead of choosing a winner", () => {
  const fields = [{id:"0",keys:["full-name"],label:"Name"}, {id:"1",keys:["名前"]}, {id:"2",keys:["missing"]}];
  const a = facts("a", '{"full name":"First", "名前":"小林"}');
  const b = facts("b", '{"full_name":"Other", "名前":"小林"}');
  const planned = planFill(fields, [a,b]);
  assert.equal(planned[0].disposition, "CONFLICT"); assert.equal(planned[0].value, "");
  assert.equal(planned[1].disposition, "MATCH"); assert.equal(planned[1].value, "小林");
  assert.equal(planned[1].matches.length, 2); assert.equal(planned[2].disposition, "NO_MATCH");
  assert.equal(planFill(fields, [a])[0].value, "First");
});

function fixture(config = {}) {
  const document = {elements: [], querySelectorAll() { return this.elements; }};
  class Input {
    constructor(options = {}) {
      Object.assign(this, {localName:"input", type:"text", name:"name", id:"name", value:"", maxLength:-1,
        disabled:false, readOnly:false, isConnected:true, ownerDocument:document,
        labels:[], form:{action:"https://target.example.test/send"}, attrs:{}, events:[],
        visible:true, opacity:"1", visibility:"visible"}, options);
    }
    get value() { return this.currentValue || ""; }
    set value(value) { this.currentValue = String(value); }
    getAttribute(key) { return this.attrs[key] || null; }
    getClientRects() { return this.visible ? [{}] : []; }
    checkVisibility(options) {
      assert(options.opacityProperty && options.visibilityProperty && options.contentVisibilityAuto);
      return !this.cssHiddenAncestor;
    }
    closest() { return this.hiddenAncestor ? {} : null; }
    matches() { return this.disabledAncestor || this.disabled; }
    dispatchEvent(event) { this.events.push(event.type); if (this.handler) this.handler(event); return true; }
  }
  const location = new URL(config.url || "https://target.example.test/form");
  let now = 1000;
  const ctx = vm.createContext({document, location, URL, crypto:webcrypto, HTMLInputElement:Input,
    HTMLTextAreaElement:Input, HTMLSelectElement:Input, Event:class { constructor(type) { this.type = type; } },
    getComputedStyle:element => ({opacity:element.opacity, visibility:element.visibility}), Date:{now:() => now}});
  // Re-serialize exactly as executeScript does: no helper closure is supplied.
  vm.runInContext(`operation = (${formOperation.toString()})`, ctx);
  function add(options) { const input = new Input(options); document.elements.push(input); return input; }
  return {add, document, location, advance:ms => { now += ms; }, call:request => ctx.operation(request)};
}
const edit = (nonce, edits = [{id:"0",value:"Proven value"}], confirmed = true) =>
  ({operation:"apply", nonce, confirmed, edits});

test("inspect only visible empty safe fields, including multilingual labels", () => {
  const f = fixture();
  f.add({id:"名前",name:"名前"});
  for (const options of [{type:"password"}, {attrs:{autocomplete:"section-a billing cc-number"}},
    {name:"otp",id:"otp"}, {type:"hidden"}, {type:"file"}, {type:"checkbox"}, {readOnly:true},
    {disabled:true}, {disabledAncestor:true}, {value:"Existing"}, {visible:false}, {opacity:"0"},
    {visibility:"hidden"}, {hiddenAncestor:true}, {cssHiddenAncestor:true}, {type:"number"}, {localName:"select",multiple:true}]) f.add(options);
  const preview = f.call({operation:"inspect"});
  assert.equal(preview.fields.length, 1); assert.equal(preview.fields[0].label, "名前");
  assert(f.document.elements.every(element => element.events.length === 0));
});
test("explicit apply writes, emits input/change and observes DOM values only; replay is rejected", () => {
  const f = fixture(), field = f.add();
  const preview = f.call({operation:"inspect"});
  assert.equal(field.value, "");
  const result = f.call(edit(preview.nonce));
  assert.equal(result.state, "DOM_VALUES_OBSERVED"); assert.equal(result.written, 1);
  assert.equal(result.ordinary_release, false); assert.equal(result.siteEffectsVerified, false);
  assert.equal(result.submittedByExtension, false); assert.equal(field.value, "Proven value");
  assert.deepEqual(field.events, ["input","change"]);
  assert.throws(() => f.call(edit(preview.nonce)));
});
test("confirmation, nonce, timeout, URL and a new preview invalidate the old application", () => {
  for (const scenario of ["confirmation", "nonce", "timeout", "url", "superseded"]) {
    const f = fixture(), field = f.add(), preview = f.call({operation:"inspect"});
    if (scenario === "timeout") f.advance(600001);
    if (scenario === "url") f.location.pathname = "/other";
    if (scenario === "superseded") f.call({operation:"inspect"});
    assert.throws(() => f.call(edit(scenario === "nonce" ? "wrong" : preview.nonce, undefined, scenario !== "confirmation")), scenario);
    assert.equal(field.value, ""); assert.equal(field.events.length, 0);
  }
});
test("revalidate all bindings before the first write; no overwrite or replacement", () => {
  for (const mutation of [field => {field.value = "user edit";}, field => {field.isConnected = false;},
    field => {field.name = "new-name";}, field => {field.attrs.autocomplete = "one-time-code";},
    field => {field.form.action = "https://other.example.test/send";}, field => {field.maxLength = 2;},
    field => {field.hiddenAncestor = true;}, field => {field.cssHiddenAncestor = true;}, field => {field.disabled = true;}]) {
    const f = fixture(), first = f.add(), second = f.add({id:"second",name:"second"});
    const preview = f.call({operation:"inspect"}); mutation(second);
    assert.throws(() => f.call(edit(preview.nonce, [{id:"0",value:"A"},{id:"1",value:"BBBB"}])));
    assert.equal(first.value, ""); assert.equal(first.events.length, 0);
  }
});
test("reject duplicate targets, excessive length and disabled/missing select values", () => {
  const f = fixture(), field = f.add({maxLength:2});
  assert.throws(() => f.call(edit(f.call({operation:"inspect"}).nonce, [{id:"0",value:"long"}])));
  assert.throws(() => f.call(edit(f.call({operation:"inspect"}).nonce, [{id:"0",value:"a"},{id:"0",value:"b"}])));
  assert.equal(field.value, "");
  const select = fixture(); select.add({localName:"select",type:"select-one", options:[{value:"",disabled:false},
    {value:"FR",disabled:false}, {value:"US",disabled:true}]});
  for (const value of ["US", "CA"]) assert.throws(() => select.call(edit(select.call({operation:"inspect"}).nonce, [{id:"0",value}])));
  assert.equal(select.call(edit(select.call({operation:"inspect"}).nonce, [{id:"0",value:"FR"}])).state, "DOM_VALUES_OBSERVED");
});
test("page mutation during an event is partial, never an external-effect success", () => {
  const f = fixture(), first = f.add(), second = f.add({id:"second",name:"second"});
  first.handler = () => {second.value = "site mutation";};
  const result = f.call(edit(f.call({operation:"inspect"}).nonce, [{id:"0",value:"A"},{id:"1",value:"B"}]));
  assert.equal(result.state, "PARTIAL_OR_CHANGED"); assert.equal(result.siteEffectsVerified, false);
  assert.equal(result.ordinary_release, false); assert.equal(second.events.length, 0);
});
test("only HTTPS or loopback HTTP targets; never privileged or credential-bearing URLs", () => {
  for (const url of ["http://remote.example.test", "file:///tmp/form.html", "about:config", "https://user:secret@example.test/"]) {
    assert.throws(() => fixture({url}).call({operation:"inspect"}));
  }
  assert.equal(fixture({url:"http://127.0.0.1:8771/test"}).call({operation:"inspect"}).fields.length, 0);
});

async function controller() {
  const nodes = new Map(), events = {}, sessions = {}, localWrites = [], calls = [];
  function node(id = "") {
    if (id && nodes.has(id)) return nodes.get(id);
    const element = {id,value:"",textContent:"",children:[],disabled:false,checked:false,dataset:{},
      addEventListener(type, fn) { if (id) events[id + ":" + type] = fn; },
      append(...items) { this.children.push(...items); }, replaceChildren() { this.children = []; }, setAttribute() {},
      querySelectorAll() { return this.children.map(label => label.children[0]).filter(box => box.checked); }};
    if (id) nodes.set(id, element);
    return element;
  }
  let activeId = 1;
  let lockTail = Promise.resolve(), lockCalls = 0;
  const locks = {request: (name, options, action) => {
    assert.equal(name, "qikvrt-fill-sources-v1"); assert.equal(options.mode, "exclusive"); lockCalls++;
    const result = lockTail.then(action); lockTail = result.catch(() => undefined); return result;
  }};
  const ctx = vm.createContext({URL, TextEncoder, crypto:webcrypto,
    navigator:{locks},
    document:{getElementById:node,createElement:() => node(),querySelectorAll:() => [
      ...["fill-capture","fill-add","fill-clear","fill-inspect","fill-apply","fill-text","fill-label"].map(node),
      ...node("fill-sources").children.map(label => label.children[0]),
      ...node("fill-preview").children.flatMap(row => [row.children[0].children[0],row.children[1]])]},
    browser:{tabs:{query:async () => [{id:activeId}]},
      storage:{local:{get:async () => ({}),set:async value => localWrites.push(value)}, session:{
        get:async key => structuredClone({[key]:sessions[key]}),
        set:async data => Object.assign(sessions,structuredClone(data)),remove:async key => {delete sessions[key];}}},
      scripting:{executeScript:async request => {
        calls.push(request);
        return [{frameId:0,result:request.args[0]?.operation === "inspect" ?
          {nonce:"fixture-nonce",origin:"https://fixture.test",fields:[{id:"0",keys:["名前"],label:"名前"}]} :
          {state:"DOM_VALUES_OBSERVED",written:1}}];
      }}}});
  vm.runInContext(source, ctx); await new Promise(resolve => setImmediate(resolve));
  node("fill-text").value = '{"名前":"小林"}';
  await events["fill-add:click"]();
  assert.equal(localWrites.length, 0, "source facts must not persist to disk storage");
  const saved = sessions.qikvrtFillSourcesV1;
  assert.equal(saved.length, 1); assert.match(saved[0].revision, /^[0-9a-f]{64}$/u);
  await events["fill-inspect:click"]();
  activeId = 2; await events["fill-apply:click"]();
  assert.equal(calls.length, 1, "changed tab must not execute apply");
  activeId = 1; await events["fill-inspect:click"]();
  delete sessions.qikvrtFillSourcesV1; await events["fill-apply:click"]();
  assert.equal(calls.length, 2, "revoked sources must not execute apply");
  assert.equal(node("fill-apply").disabled, true);
  sessions.qikvrtFillSourcesV1 = saved;
  await events["fill-inspect:click"]();
  assert.equal(node("fill-apply").disabled, false);
  await events["fill-apply:click"]();
  assert.equal(calls.length, 4);
  assert.equal(calls[3].args[0].edits[0].value, "小林", "locking controls must not remove confirmed edits");
  assert.equal(calls[3].args[0].confirmed, true);
  await events["fill-clear:click"]();
  assert.equal(sessions.qikvrtFillSourcesV1, undefined);
  assert.equal(localWrites.length, 0);
  assert(calls.every(call => call.target.frameIds.length === 1 && call.target.frameIds[0] === 0));
  assert(calls.every(call => call.world === "ISOLATED"));
  assert(lockCalls >= 5, "add, clear and apply must share the same exclusive lock");
  const order = [];
  await Promise.all([
    ctx.withSourceLock(async () => {order.push("add:start"); await new Promise(resolve => setImmediate(resolve)); order.push("add:end");}),
    ctx.withSourceLock(async () => {order.push("clear");})
  ]);
  assert.deepEqual(order, ["add:start","add:end","clear"], "clear must not race an unfinished source addition");
  vm.runInContext("navigator.locks = null", ctx);
  await assert.rejects(ctx.withSourceLock(async () => {throw new Error("must never execute");}), /Sitzungssperre/u);
  count++; process.stdout.write("PASS simulated popup uses session-only sources and rejects changed tab or revoked sources\n");
}
controller().then(() => process.stdout.write(`PASS: ${count} offline Fill from Sources control groups; simulated DOM/APIs, NOT native Firefox acceptance.\n`))
  .catch(error => {process.stderr.write(error.stack + "\n"); process.exitCode = 1;});
