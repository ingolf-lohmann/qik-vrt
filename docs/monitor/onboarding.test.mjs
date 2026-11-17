// Copyright 2026 Ingolf Lohmann. Test implementation: OpenAI Codex.
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const manifest = JSON.parse(readFileSync(new URL('../../interfaces/cognition-onboarding-v1.json', import.meta.url)));
const locales = ['de', 'en', 'fr', 'ru', 'tr', 'ro', 'it', 'es', 'pt-BR'];
const payload = html.match(/<script type="application\/json" id="qikvrt-public-entry">([\s\S]*?)<\/script>/);
const renderer = html.match(/<script id="qikvrt-public-entry-renderer">([\s\S]*?)<\/script>/);

function view(entry) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {textContent: '', value: 'de', lang: '', listeners: {},
      addEventListener(event, callback) { this.listeners[event] = callback; }});
    return elements.get(id);
  };
  element('qikvrt-public-entry').textContent = JSON.stringify(entry);
  const forbidden = () => { throw Error('PUBLIC_READING_MUST_HAVE_NO_EXTERNAL_EFFECT'); };
  const context = vm.createContext({document: {getElementById: element},
    fetch: forbidden, localStorage: {setItem: forbidden}, sessionStorage: {setItem: forbidden},
    setInterval: forbidden, setTimeout: forbidden});
  vm.runInContext(renderer[1], context, {timeout: 1000});
  return {element, select(locale) {const input = element('entry-language'); input.value = locale; input.listeners.change();}};
}

test('the existing monitor contains the same complete nine-language public entry as its machine manifest', () => {
  assert.ok(payload, 'PUBLIC_ENTRY_MISSING');
  assert.ok(renderer, 'PUBLIC_ENTRY_RENDERER_MISSING');
  const entry = JSON.parse(payload[1]);
  assert.deepEqual(entry, manifest.public_entry);
  assert.deepEqual(Object.keys(entry.translations), locales);
  assert.deepEqual(manifest.language, locales);
  assert.equal(entry.authority_repository, 'ingolf-lohmann/qik-vrt');
  assert.equal(entry.mirror_repository, 'Goldkelch/qik-vrt');
  assert.equal(entry.opening_grants_membership, false);
  assert.equal(entry.licence_acceptance_alone_grants_write, false);
  assert.equal(entry.submission_is_automatic_adoption, false);
  const keys = Object.keys(entry.translations.de).sort();
  for (const locale of locales) {
    assert.deepEqual(Object.keys(entry.translations[locale]).sort(), keys);
    for (const value of Object.values(entry.translations[locale])) assert.ok(typeof value === 'string' && value.trim());
    assert.ok(html.includes(`<option value="${locale}">`));
  }
});

test('every selected language renders all rights, attribution and evidence boundaries without network or storage effects', () => {
  assert.ok(payload && renderer, 'PUBLIC_ENTRY_MISSING');
  const entry = JSON.parse(payload[1]);
  const page = view(entry);
  for (const locale of locales) {
    page.select(locale);
    assert.equal(page.element('entry-copy').lang, locale);
    for (const [key, value] of Object.entries(entry.translations[locale])) {
      if (key !== 'name') assert.equal(page.element('entry-' + key).textContent, value);
    }
  }
  for (const unsupported of ['pt', 'pt-PT', 'constructor', '__proto__', '<img src=x onerror=alert(1)>']) {
    page.select(unsupported);
    assert.equal(page.element('entry-copy').lang, 'de');
    assert.equal(page.element('entry-title').textContent, entry.translations.de.title);
  }
  const hostile = structuredClone(entry);
  hostile.translations.en.purpose = '<img src=x onerror=alert(1)>';
  const escaped = view(hostile); escaped.select('en');
  assert.equal(escaped.element('entry-purpose').textContent, hostile.translations.en.purpose);
  assert.doesNotMatch(renderer[1], /innerHTML|insertAdjacentHTML|document\.write/);
  assert.match(html, /href="https:\/\/github\.com\/ingolf-lohmann\/qik-vrt\/blob\/main\/api\/qikvrt_github_api\.openapi\.yaml"/);
});
