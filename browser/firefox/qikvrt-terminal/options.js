// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann.
"use strict";

// No provider SDK, credential, fetch, region routing or automatic submission.
const FILL_SESSION_KEY = "qikvrtFillSourcesV1";
const MAX_SOURCE_BYTES = 32768;

function normalizeField(value) {
  return String(value).normalize("NFKC").toLowerCase().replace(/[\s_\-:]+/gu, " ").trim();
}

function parseSource(text) {
  if (typeof text !== "string" || new TextEncoder().encode(text).length > MAX_SOURCE_BYTES) {
    throw new Error("Quelle fehlt oder überschreitet 32 KiB.");
  }
  const value = text.trim();
  let entries;
  if (value.startsWith("{")) {
    const object = JSON.parse(value);
    if (!object || Array.isArray(object) || typeof object !== "object") throw new Error("JSON-Objekt erforderlich.");
    // Preserve duplicate keys (including escaped spellings) instead of letting
    // JSON.parse silently choose the last value before conflict detection.
    entries = [];
    const member = /\s*("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*"|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\s*([,}])/uy;
    let position = 1;
    while (position < value.length - 1) {
      member.lastIndex = position;
      const match = member.exec(value);
      if (!match) throw new Error("Nur flaches JSON mit Zeichenfolgen oder Zahlen zulässig.");
      entries.push([JSON.parse(match[1]), JSON.parse(match[2])]);
      position = member.lastIndex;
      if (match[3] === "}") break;
    }
    if (entries.length && position !== value.length) throw new Error("Ungültiges Quellenobjekt.");
  } else {
    entries = value.split(/\r?\n/u).filter(line => line.trim()).map(line => {
      const index = line.indexOf(":");
      if (index <= 0) throw new Error("Nur JSON oder Feld: Wert; Freitext benötigt einen geprüften Adapter.");
      return [line.slice(0, index).trim(), line.slice(index + 1).trim()];
    });
  }
  if (!entries.length || entries.length > 64) throw new Error("1 bis 64 Quellenfelder erforderlich.");
  const seen = new Set();
  return entries.map(([key, raw]) => {
    const normalized = normalizeField(key);
    if (!normalized || key.length > 160 || seen.has(normalized)) throw new Error("Leerer oder mehrdeutiger Quellenname.");
    if ((typeof raw !== "string" && typeof raw !== "number") || !String(raw).trim() ||
        (typeof raw === "number" && !Number.isFinite(raw)) || String(raw).length > 4096) {
      throw new Error("Quellenwerte müssen nichtleere Zeichenfolgen oder endliche Zahlen (max. 4096 Zeichen) sein.");
    }
    seen.add(normalized);
    return {key, value: String(raw)};
  });
}

function planFill(targetFields, sources) {
  return targetFields.map(field => {
    const keys = new Set(field.keys.map(normalizeField).filter(Boolean));
    const matches = sources.flatMap(source => source.facts
      .filter(fact => keys.has(normalizeField(fact.key)))
      .map(fact => ({source: source.id, revision: source.revision, locator: source.locator,
        key: fact.key, value: fact.value})));
    const values = [...new Set(matches.map(match => match.value))];
    return {...field, value: values.length === 1 ? values[0] : "", matches,
      disposition: values.length > 1 ? "CONFLICT" : values.length === 1 ? "MATCH" : "NO_MATCH"};
  });
}

// Self-contained: executeScript serializes this function without its closure.
// State lives in the extension's isolated world, not page attributes or storage.
function formOperation(request) {
  const slot = "__qikvrtFillPreviewV1";
  const types = new Set(["text", "email", "tel", "url", "search"]);
  const url = new URL(location.href);
  if (!["https:", "http:"].includes(url.protocol) || url.username || url.password ||
      (url.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))) {
    throw new Error("Nur HTTPS oder lokale HTTP-Testseiten zulässig.");
  }
  function describe(element) {
    const tag = element.localName;
    const autocomplete = (element.getAttribute("autocomplete") || "").toLowerCase();
    const keys = [element.name, element.id, element.getAttribute("aria-label"),
      ...(element.labels ? Array.from(element.labels, label => label.textContent) : []),
      autocomplete.split(/\s+/u).at(-1)].filter(Boolean).map(key => String(key).trim());
    const denied = /(?:password|passwort|mot.de.passe|contrase[ñn]a|парол|密码|暗証|credit|card|karte|carte|cvv|cvc|iban|otp|token|secret|(?:^|[\s_-])pin(?:$|[\s_-])|one.time|cc-|transaction)/iu;
    if ((tag !== "input" && tag !== "textarea" && tag !== "select") ||
        (tag === "input" && !types.has(element.type)) ||
        (tag === "select" && element.multiple) ||
        element.disabled || element.readOnly || element.matches(":disabled") ||
        element.closest("[inert],[hidden],[aria-hidden='true']") ||
        typeof element.checkVisibility !== "function" ||
        !element.checkVisibility({opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true}) ||
        !element.getClientRects().length ||
        ["hidden", "collapse"].includes(getComputedStyle(element).visibility) ||
        Number(getComputedStyle(element).opacity) === 0 ||
        denied.test(keys.join(" ")) || !keys.length) return null;
    return {keys, type: element.type, tag,
      formAction: element.form ? element.form.action : null,
      maxLength: element.maxLength,
      options: tag === "select" ? Array.from(element.options, option => ({value: option.value,
        disabled: option.disabled || Boolean(option.parentElement && option.parentElement.disabled)})) : null};
  }
  if (request.operation === "inspect") {
    delete globalThis[slot];
    const bindings = [];
    const fields = [];
    for (const element of document.querySelectorAll("input,textarea,select")) {
      const descriptor = describe(element);
      if (!descriptor || element.value !== "") continue;
      if (fields.length >= 100) throw new Error("Mehr als 100 geeignete Felder; Ziel eingrenzen.");
      const id = String(fields.length);
      fields.push({id, keys: descriptor.keys, label: descriptor.keys[0], type: descriptor.type});
      bindings.push({element, descriptor: JSON.stringify(descriptor), original: element.value});
    }
    const nonce = crypto.randomUUID();
    globalThis[slot] = {nonce, href: location.href, at: Date.now(), bindings};
    return {nonce, origin: location.origin, fields};
  }
  const preview = globalThis[slot];
  // Consume even a rejected application; there is no automatic retry.
  delete globalThis[slot];
  if (request.operation !== "apply" || request.confirmed !== true || !preview ||
      request.nonce !== preview.nonce || preview.href !== location.href ||
      Date.now() - preview.at > 600000 || !Array.isArray(request.edits) ||
      !request.edits.length || request.edits.length > 100) throw new Error("Vorschau fehlt, ist abgelaufen oder unbestätigt.");
  const seen = new Set();
  const edits = request.edits.map(edit => {
    if (!edit || typeof edit.id !== "string" || !/^(0|[1-9][0-9]?)$/u.test(edit.id) ||
        seen.has(edit.id) || typeof edit.value !== "string" || !edit.value || edit.value.length > 4096) {
      throw new Error("Ungültige oder doppelte Zielzuordnung.");
    }
    seen.add(edit.id);
    const bound = preview.bindings[Number(edit.id)];
    if (!bound || !bound.element.isConnected || bound.element.ownerDocument !== document ||
        JSON.stringify(describe(bound.element)) !== bound.descriptor ||
        bound.element.value !== bound.original) throw new Error("Zielfeld wurde geändert; neue Vorschau erforderlich.");
    const descriptor = JSON.parse(bound.descriptor);
    if (descriptor.maxLength >= 0 && edit.value.length > descriptor.maxLength) throw new Error("Wert überschreitet Feldlänge.");
    if (descriptor.options && !descriptor.options.some(option => option.value === edit.value && !option.disabled)) {
      throw new Error("Wert ist keine zulässige Auswahl.");
    }
    return {element: bound.element, value: edit.value, descriptor: bound.descriptor};
  });
  let written = 0;
  try {
    // Check the complete batch before the first write. Set values before events.
    for (const edit of edits) {
      const prototype = edit.element.localName === "textarea" ? HTMLTextAreaElement.prototype :
        edit.element.localName === "select" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(prototype, "value").set.call(edit.element, edit.value);
      written++;
    }
    for (const edit of edits) {
      if (!edit.element.isConnected || edit.element.value !== edit.value ||
          JSON.stringify(describe(edit.element)) !== edit.descriptor) break;
      edit.element.dispatchEvent(new Event("input", {bubbles: true}));
      edit.element.dispatchEvent(new Event("change", {bubbles: true}));
    }
    const readback = edits.map(edit => ({connected: edit.element.isConnected,
      unchangedBinding: JSON.stringify(describe(edit.element)) === edit.descriptor,
      matches: edit.element.value === edit.value}));
    return {state: readback.every(item => item.connected && item.unchangedBinding && item.matches) ?
      "DOM_VALUES_OBSERVED" : "PARTIAL_OR_CHANGED", written, readback, submittedByExtension: false,
      siteEffectsVerified: false, ordinary_release: false};
  } catch (_) {
    // No rollback: page events may already have caused non-reversible effects.
    return {state: "PARTIAL_OR_CHANGED", written, submittedByExtension: false,
      siteEffectsVerified: false, ordinary_release: false};
  }
}

if (typeof module !== "undefined" && module.exports) module.exports = {normalizeField, parseSource, planFill, formOperation};

if (typeof document !== "undefined" && typeof browser !== "undefined") {
  const preferenceFields = ["accent", "fontScale", "density", "position"];
  let sources = [], preview = null, capturedLocator = "user-provided", busy = false;
  const byId = id => document.getElementById(id);
  const status = text => { byId("fill-status").textContent = text; };
  function invalidate() {
    preview = null;
    byId("fill-preview").replaceChildren();
    byId("fill-apply").disabled = true;
  }
  async function activeTab() {
    const tabs = await browser.tabs.query({active: true, currentWindow: true});
    if (tabs.length !== 1 || !Number.isInteger(tabs[0].id)) throw new Error("Aktiver Web-Tab fehlt.");
    return tabs[0].id;
  }
  async function execute(tabId, func, args) {
    const results = await browser.scripting.executeScript({target: {tabId, frameIds: [0]}, world: "ISOLATED", func, args});
    if (results.length !== 1 || results[0].frameId !== 0 || results[0].error || !results[0].result) {
      throw new Error("Zugriff nicht erteilt oder Hauptdokument nicht lesbar. Symbol im Zieltab erneut öffnen.");
    }
    return results[0].result;
  }
  function showSources() {
    const container = byId("fill-sources");
    container.replaceChildren();
    for (const source of sources) {
      const label = document.createElement("label"), box = document.createElement("input"), text = document.createElement("span");
      box.type = "checkbox"; box.checked = true; box.dataset.source = source.id;
      box.addEventListener("change", invalidate);
      text.textContent = `${source.label} · ${source.locator} · SHA-256 ${source.revision.slice(0, 12)}`;
      label.append(box, text); container.append(label);
    }
  }
  function chosenSources() {
    const ids = new Set(Array.from(byId("fill-sources").querySelectorAll("input:checked"), box => box.dataset.source));
    return sources.filter(source => ids.has(source.id));
  }
  async function capture() {
    const result = await execute(await activeTab(), () => {
      const url = new URL(location.href);
      if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) throw new Error("Web-Quelle erforderlich.");
      const text = String(window.getSelection() || "");
      if (!text || new TextEncoder().encode(text).length > 32768) throw new Error("1 bis 32768 Bytes markieren.");
      return {text, locator: url.origin + url.pathname};
    }, []);
    byId("fill-text").value = result.text;
    capturedLocator = result.locator;
    invalidate();
    status("Markierung lokal gelesen. Daten prüfen und als Quelle übernehmen.");
  }
  async function addSource() {
    invalidate();
    const current = await browser.storage.session.get(FILL_SESSION_KEY);
    if (JSON.stringify(current[FILL_SESSION_KEY] || []) !== JSON.stringify(sources)) {
      throw new Error("Quellen in einer anderen Ansicht geändert; Symbol erneut öffnen.");
    }
    if (sources.length >= 8) throw new Error("Maximal acht Quellen pro Sitzung; Quellen zunächst löschen.");
    const text = byId("fill-text").value;
    const facts = parseSource(text);
    const bytes = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)));
    const revision = Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
    const source = {id: crypto.randomUUID(), label: byId("fill-label").value.trim().slice(0, 160) || "Ausgewählte Quelle",
      revision, locator: capturedLocator, facts};
    const next = [...sources, source];
    await browser.storage.session.set({[FILL_SESSION_KEY]: next});
    sources = next; showSources();
    byId("fill-text").value = ""; byId("fill-label").value = ""; capturedLocator = "user-provided";
    status("Quelle im Browser-Sitzungsspeicher. Im Zieltab das Symbol öffnen und Vorschau erstellen.");
  }
  async function inspect() {
    invalidate();
    const selected = chosenSources();
    if (!selected.length) throw new Error("Mindestens eine Quelle auswählen.");
    const tabId = await activeTab();
    const target = await execute(tabId, formOperation, [{operation: "inspect"}]);
    const planned = planFill(target.fields, selected);
    preview = {tabId, nonce: target.nonce, sourceBinding: JSON.stringify(sources), rows: []};
    for (const item of planned) {
      const row = document.createElement("div"), label = document.createElement("label"), box = document.createElement("input");
      const title = document.createElement("span"), input = document.createElement("input"), provenance = document.createElement("small");
      box.type = "checkbox"; box.checked = item.disposition === "MATCH"; box.disabled = item.disposition !== "MATCH";
      title.textContent = `${item.label} · ${item.disposition}`;
      input.type = "text"; input.value = item.value; input.disabled = item.disposition !== "MATCH";
      input.setAttribute("aria-label", `${item.label} – vorgeschlagener Wert`);
      provenance.textContent = item.matches.map(match => `${match.locator} · ${match.key} · SHA-256 ${match.revision}`).join("; ") || "Kein Quellenbezug; bleibt unverändert.";
      input.addEventListener("input", () => {
        provenance.textContent = "Manuell bearbeitet; Quellenbeleg gilt nicht für den geänderten Wert.";
      });
      label.append(box, title); row.append(label, input, provenance); byId("fill-preview").append(row);
      preview.rows.push({id: item.id, box, input, eligible: item.disposition === "MATCH"});
    }
    byId("fill-apply").disabled = !planned.some(item => item.disposition === "MATCH");
    status(`Ziel: ${target.origin}. Vorschläge und Quellen prüfen. Konflikte werden nicht übernommen. Kein Absenden durch die Erweiterung.`);
  }
  async function apply() {
    const bound = preview;
    const current = await browser.storage.session.get(FILL_SESSION_KEY);
    if (!bound || preview !== bound || await activeTab() !== bound.tabId || JSON.stringify(current[FILL_SESSION_KEY] || []) !== bound.sourceBinding) {
      invalidate(); throw new Error("Zieltab oder Quellen geändert; neue Vorschau erforderlich.");
    }
    const edits = bound.rows.filter(row => row.box.checked && row.eligible).map(row => ({id: row.id, value: row.input.value}));
    invalidate();
    const result = await execute(bound.tabId, formOperation, [{operation: "apply", nonce: bound.nonce, confirmed: true, edits}]);
    status(`${result.state}: ${result.written} DOM-Einträge. Keine Bestätigung externer Wirkungen und kein EFFECT_ACK_DONE. Vor weiterem Handeln Zielseite prüfen.`);
  }
  function handle(id, action) {
    byId(id).addEventListener("click", async () => {
      if (busy) return;
      busy = true;
      const locked = document.querySelectorAll("#fill-capture,#fill-add,#fill-clear,#fill-inspect,#fill-apply,#fill-text,#fill-label,#fill-sources input,#fill-preview input");
      const states = Array.from(locked, element => [element, element.disabled]);
      for (const [element] of states) element.disabled = true;
      try { await action(); } catch (error) { invalidate(); status(error.message); }
      finally {
        for (const [element, disabled] of states) if (element.id !== "fill-apply") element.disabled = disabled;
        // New preview controls may have replaced the locked old controls.
        byId("fill-apply").disabled = !preview || !preview.rows.some(row => row.box.checked && row.eligible);
        busy = false;
      }
    });
  }
  handle("fill-capture", capture); handle("fill-add", addSource); handle("fill-inspect", inspect); handle("fill-apply", apply);
  handle("fill-clear", async () => {
    invalidate(); await browser.storage.session.remove(FILL_SESSION_KEY);
    sources = []; showSources(); byId("fill-text").value = ""; capturedLocator = "user-provided";
    status("Quellen gelöscht.");
  });
  byId("fill-text").addEventListener("input", () => { capturedLocator = "user-provided/edited"; });
  byId("save").addEventListener("click", async () => {
    try {
      const preferences = Object.fromEntries(preferenceFields.map(id => [id, byId(id).value]));
      preferences.fontScale = Number(preferences.fontScale);
      await browser.storage.local.set({qikvrtTerminalPreferences: preferences});
      byId("status").textContent = "gespeichert";
    } catch (error) { byId("status").textContent = error.message; }
  });
  (async () => {
    const stored = await browser.storage.local.get("qikvrtTerminalPreferences");
    const preferences = stored.qikvrtTerminalPreferences || {};
    for (const id of preferenceFields) if (preferences[id] !== undefined) byId(id).value = preferences[id];
    const session = await browser.storage.session.get(FILL_SESSION_KEY);
    sources = session[FILL_SESSION_KEY] || []; showSources();
  })().catch(error => { invalidate(); status(error.message); });
}
