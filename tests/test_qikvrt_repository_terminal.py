#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Static security and accessibility regression checks for the Pages terminal."""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import unittest
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs/terminal/index.html"
SCRIPT = ROOT / "docs/assets/js/qikvrt-repository-terminal.js"
STYLE = ROOT / "docs/assets/css/qikvrt-terminal.css"

# Execute the actual client through its DOM events. HTTP is a deterministic
# fixture here; public browser readback is a separate evidence obligation.
ROUTING_HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() { this.children = []; this.dataset = {}; this.handlers = {}; this.value = ''; }
  append(...items) { this.children.push(...items); }
  replaceChildren() { this.children = []; }
  addEventListener(event, handler) { this.handlers[event] = handler; }
  setAttribute() {}
  focus() {}
}
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
const document = {
  documentElement: new Element(),
  getElementById: element,
  createElement: () => new Element(),
  querySelectorAll: () => [],
  addEventListener(event, handler) { this.handlers[event] = handler; },
  handlers: {},
};
const requests = [];
let denyMirror = false;
const encode = value => Buffer.from(JSON.stringify(value)).toString('base64');
const fetch = async (url, options) => {
  requests.push(url);
  assert.equal(options.method, 'GET');
  assert.equal(options.credentials, 'omit');
  assert.deepEqual(Object.keys(options.headers), ['Accept']);
  const denied = denyMirror && url.startsWith('https://api.github.com/repos/Goldkelch/qik-vrt');
  let payload = { visibility: 'public', updated_at: '2026-10-11T00:00:00Z' };
  if (url.endsWith('/commits/main')) payload = { sha: 'a'.repeat(40), commit: { tree: { sha: 'b'.repeat(40) } } };
  if (url.includes('/contents/')) {
    let content = Buffer.from('fixture document').toString('base64');
    if (url.includes('self-disclosure.json')) content = encode({ capabilities: ['read'], completion_claims: { pass: false, final_pass: false, effect_ack_done: false } });
    if (url.includes('publications/index.json')) content = encode({ publication_bundles: [{ title: 'Fixture publication', doi: 'fixture' }] });
    payload = { content, sha: 'c'.repeat(40) };
  }
  return { ok: !denied, status: denied ? 404 : 200, json: async () => payload };
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), {
  document, window: { atob: value => Buffer.from(value, 'base64').toString('binary') },
  fetch, localStorage: { getItem: () => null, setItem() {} },
  Intl, Date, Uint8Array, TextDecoder,
});
document.handlers.DOMContentLoaded();
const select = role => {
  element('repositorySelect').value = role;
  element('repositorySelect').handlers.change({ target: element('repositorySelect') });
};
const run = async command => {
  element('terminalInput').value = command;
  requests.length = 0;
  element('terminalForm').handlers.submit({ preventDefault() {} });
  await new Promise(resolve => setImmediate(resolve));
  return element('terminalOutput').children.at(-1).children[1].textContent;
};
const owners = { authority: 'ingolf-lohmann/qik-vrt', mirror: 'Goldkelch/qik-vrt' };
(async () => {
  for (const [role, repository] of Object.entries(owners)) {
    select(role);
    const base = `https://api.github.com/repos/${repository}`;
    for (const [command, paths] of [
      ['status', ['', '/commits/main']],
      ['capabilities', ['/contents/.well-known/qik-vrt-self-disclosure.json?ref=main']],
      ...['AI', 'STATUS', 'README', 'ARCHITECTURE', 'BOUNDARIES', 'PRIVACY'].map(name => {
        const path = { AI:'AI', STATUS:'STATUS.md', README:'README.md', ARCHITECTURE:'docs/ARCHITECTURE.md', BOUNDARIES:'docs/BOUNDARIES.md', PRIVACY:'docs/PRIVACY_PRESERVING_INTERACTION_ARCHIVE.md' }[name];
        return [`read ${name}`, [`/contents/${path}?ref=main`]];
      }),
      ['publications', ['/contents/docs/publications/index.json?ref=main']],
    ]) {
      const output = await run(command);
      assert.deepEqual(requests, paths.map(path => base + path), `${role}: ${command}`);
      assert.ok(output.includes(`Repository: ${repository}`));
      assert.ok(output.includes('OWNER_ROLE_ASSIGNMENT; native activation unverified'));
      assert.equal(element('terminalConnectionState').textContent, 'PUBLIC_READ_COMPLETE');
      const source = element('terminalOutput').children.at(-1).children.at(-1);
      assert.ok(source.href.startsWith(`https://github.com/${repository}/`));
    }
  }
  // Explicit targets override the selected context for that command only.
  select('authority');
  for (const command of ['status mirror', 'capabilities mirror']) {
    const output = await run(command);
    assert.ok(output.includes('Repository: Goldkelch/qik-vrt'));
    assert.ok(requests.every(url => url.startsWith('https://api.github.com/repos/Goldkelch/qik-vrt')));
  }
  const next = await run('read STATUS');
  assert.ok(next.includes('Repository: ingolf-lohmann/qik-vrt'));
  for (const command of ['status invalid', 'capabilities invalid', 'read https://example.com', 'execute shell']) {
    await run(command);
    assert.equal(requests.length, 0);
  }
  // A missing Mirror is visible and never silently replaced by Authority.
  denyMirror = true;
  select('mirror');
  for (const command of ['status', 'capabilities', 'read STATUS', 'publications']) {
    const output = await run(command);
    assert.ok(output.includes('HTTP 404'));
    assert.ok(output.includes('GET https://api.github.com/repos/Goldkelch/qik-vrt'));
    assert.ok(requests.every(url => url.startsWith('https://api.github.com/repos/Goldkelch/qik-vrt')));
    assert.equal(element('terminalConnectionState').textContent, 'CONTINUE');
  }
  console.log('PASS: both roles, selected/explicit commands, fixed documents, publications, public GETs and no Mirror fallback');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


class RepositoryTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = PAGE.read_text(encoding="utf-8")
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.style = STYLE.read_text(encoding="utf-8")

    def test_pages_navigation_and_production_sitemap_scope(self) -> None:
        homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn('href="terminal/"', homepage)
        disclosure = json.loads((ROOT / ".well-known/qik-vrt-self-disclosure.json").read_text(encoding="utf-8"))
        delivery = disclosure["bindings"]["public_delivery"]
        sitemap = ET.parse(ROOT / delivery["sitemap_path"])
        urls = [node.text for node in sitemap.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertEqual(urls, delivery["sitemap_urls"])
        self.assertIn(delivery["canonical_origin"] + delivery["article_path"], urls)
        # The historical Pages terminal remains linked in its own source tree.
        # It is not a prepared route of the separately bound production Site.
        self.assertNotIn("https://goldkelch.github.io/qik-vrt/terminal/", urls)
        self.assertNotIn(delivery["canonical_origin"] + "/terminal/", urls)

    def test_page_has_bilingual_accessible_terminal_controls(self) -> None:
        for marker in (
            'data-language="de"',
            'lang="en"',
            'id="terminalForm"',
            'id="terminalInput"',
            'id="repositorySelect"',
            'id="terminalOutput"',
            'role="log"',
            'aria-live="polite"',
            'id="startListening"',
            'id="speakOutput"',
            "ASR_DRAFT",
            "READ_ONLY",
            "EFFECT_ACK_CONTINUE",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.page)
        self.assertIn("prefers-reduced-motion", self.style)
        self.assertIn(":focus-visible", self.style)

    def test_script_has_fixed_read_only_repository_surface(self) -> None:
        for marker in (
            "Goldkelch/qik-vrt",
            "ingolf-lohmann/qik-vrt",
            'method: "GET"',
            'credentials: "omit"',
            ".well-known/qik-vrt-self-disclosure.json",
            "publication_bundles",
            "FIXED_DOCUMENTS",
            "SpeechRecognition",
            "webkitSpeechRecognition",
            "speechSynthesis",
            "ASR_DRAFT",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        for forbidden in (
            "Authorization",
            "localStorage.setItem(\"qikvrt-terminal",
            "sessionStorage",
            "innerHTML",
            "eval(",
            "Function(",
            'method: "POST"',
            'method: "PUT"',
            'method: "PATCH"',
            'method: "DELETE"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.script)

    def test_command_surface_is_explicit_and_bounded(self) -> None:
        for command in (
            'command === "help"',
            'command === "clear"',
            'command === "status"',
            'command === "capabilities"',
            'command === "read"',
            'command === "publications"',
            'command === "analyse"',
            'command === "analyze"',
        ):
            with self.subTest(command=command):
                self.assertIn(command, self.script)
        self.assertIn("no free-form commands or URLs", self.script)

    def test_owner_role_selection_and_status_links_agree(self) -> None:
        for role, repository in (("authority", "ingolf-lohmann/qik-vrt"), ("mirror", "Goldkelch/qik-vrt")):
            option = re.search(rf'<option value="{role}">([^<]+)</option>', self.page)
            self.assertIsNotNone(option)
            self.assertIn(repository, option.group(1))
            self.assertIn("Owner-Zuweisung", option.group(1))
        self.assertIn("kein Nachweis ihrer nativen Repository-Aktivierung", self.page)
        homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        status_url = 'https://github.com/ingolf-lohmann/qik-vrt/blob/main/STATUS.md'
        self.assertIn(status_url, homepage)
        self.assertIn(status_url, self.page)
        self.assertNotIn('https://github.com/Goldkelch/qik-vrt/blob/main/STATUS.md', homepage + self.page)

    def test_actual_client_routes_each_role_without_write_or_fallback(self) -> None:
        script = pathlib.Path(os.environ.get("QIKVRT_TERMINAL_SCRIPT", str(SCRIPT)))
        node = os.environ.get("CODEX_PRIMARY_RUNTIME_NODE", "node")
        result = subprocess.run([node, "-e", ROUTING_HARNESS, str(script)],
                                text=True, capture_output=True, timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: both roles", result.stdout)

    def test_script_and_test_have_current_source_license_notice(self) -> None:
        marker = "SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0"
        self.assertIn(marker, self.script)
        self.assertIn(marker, pathlib.Path(__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
