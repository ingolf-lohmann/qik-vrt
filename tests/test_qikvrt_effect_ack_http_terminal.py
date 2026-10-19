from __future__ import annotations

import base64
import fnmatch
import importlib.util
import json
import socket
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "qikvrt_effect_ack_http_terminal.py"
_spec = importlib.util.spec_from_file_location("qikvrt_effect_ack_http_terminal", MODULE_PATH)
assert _spec and _spec.loader
terminal = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = terminal
_spec.loader.exec_module(terminal)


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def commit_field(token: str, digest: str) -> str:
    return f"v=1, mode=commit, token={sf_bytes(token.encode('ascii'))}, hash={sf_bytes(bytes.fromhex(digest))}"


class EffectAckHttpTerminalContractTests(unittest.TestCase):
    def test_repository_contract_files_parse(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "docs/terminal/QIKVRT_TERMINAL_FRAME_V1.schema.json").read_text(encoding="utf-8"))
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-03.xml")
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml")
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("alarms", manifest["permissions"])
        self.assertIn("http://127.0.0.1:8771/*", manifest["host_permissions"])
        self.assertEqual(policy["http"]["request_field"], "Effect-Ack-Request")
        self.assertEqual(policy["http"]["response_field"], "Effect-Ack")
        self.assertEqual(policy["http"]["link_relation"], "effect-ack")
        self.assertEqual(schema["properties"]["schema"]["const"], "qikvrt_terminal_frame_v1")

    def test_firefox_source_preserves_terminal_boundaries(self) -> None:
        background = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
        content = (ROOT / "browser/firefox/qikvrt-terminal/content.js").read_text(encoding="utf-8")
        manifest = (ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8")
        self.assertIn("browser.alarms", background)
        self.assertNotIn("browser.alarms.create", background)
        self.assertNotIn("browser.alarms.onAlarm", background)
        self.assertIn("browser.alarms.clear(WATCHDOG_ALARM)", background)
        self.assertIn("validated DONE prepare result required", background)
        self.assertIn("record_validated", background)
        self.assertIn("compact/full record hash mismatch", background)
        self.assertIn("Effect-Ack-Request", background)
        self.assertNotIn("X-QIKVRT-Commit-Token", background)
        self.assertNotIn("X-QIKVRT-Record-Hash", background)
        self.assertIn("getUserMedia({audio: true", content)
        self.assertIn("getUserMedia({audio: false, video:", content)
        self.assertIn("preparedRequest", content)
        self.assertIn("Prepare ≠ effect", content)
        self.assertNotIn('"service_worker"', manifest)
        self.assertNotIn("8766", background + manifest)

    def test_http_draft_defines_backward_compatible_two_phase_profile(self) -> None:
        text = (ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml").read_text(encoding="utf-8")
        for value in (
            "Effect-Ack-Request",
            "Effect-Ack",
            "effect-ack",
            "mode=prepare",
            "mode=commit",
            "single-use",
            "Backward Compatibility",
            "HTML Integration",
        ):
            self.assertIn(value, text)
        self.assertIn("MUST NOT execute the protected effect", text)

    def test_structured_request_parser_is_closed_and_exact(self) -> None:
        parsed = terminal.parse_effect_ack_request("v=1, mode=prepare")
        self.assertEqual(parsed, {"v": 1, "mode": "prepare"})
        token = "abc_DEF-123"
        digest = "00" * 32
        parsed = terminal.parse_effect_ack_request(commit_field(token, digest))
        self.assertEqual(parsed["token"], token)
        self.assertEqual(parsed["hash"], digest)
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=1, mode=prepare, token=:YQ==:")
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=1, mode=commit")
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=2, mode=prepare")


class FirefoxAuthorityRegressionTests(unittest.TestCase):
    """Run the real adapter with bounded browser/HTTP fixtures, without effects."""

    def test_content_script_entrypoints_are_policy_bound_and_closed(self) -> None:
        binding = json.loads((ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json").read_text())
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text())
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text())
        authority = binding["canonical_upstream"]
        mirror = binding["mirror"]
        owner_match = f'https://github.com/{authority["repository"]}/blob/{authority["default_branch"]}/AI*'
        mirror_match = f'https://github.com/{mirror["repository"]}/blob/{mirror["default_branch"]}/AI*'
        owner_pages = f'https://{authority["repository"].lower().split("/")[0]}.github.io/qik-vrt/*'
        mirror_pages = f'https://{mirror["repository"].lower().split("/")[0]}.github.io/qik-vrt/*'
        self.assertEqual(policy["authority_repository"], authority["repository"])
        self.assertEqual(policy["terminal"]["entrypoint_match"], owner_match)
        self.assertEqual(len(manifest["content_scripts"]), 1)
        script = manifest["content_scripts"][0]
        self.assertCountEqual(script["matches"], [owner_match, owner_pages, mirror_match, mirror_pages])
        self.assertEqual(script["js"], ["content.js"])
        self.assertEqual(script["css"], ["terminal.css"])
        self.assertEqual(script["run_at"], "document_idle")
        for key in ("all_frames", "match_about_blank", "match_origin_as_fallback"):
            self.assertFalse(script.get(key, False))

        def allowed(url: str) -> bool:
            # Fixed HTTPS hosts; match paths include query strings but exclude fragments.
            parts = urlsplit(url)
            return any(
                parts.scheme == urlsplit(pattern).scheme
                and parts.netloc == urlsplit(pattern).netloc
                and fnmatch.fnmatchcase(parts.path + ("?" + parts.query if parts.query else ""), urlsplit(pattern).path)
                for pattern in script["matches"]
            )

        for url in (
            f'https://github.com/{authority["repository"]}/blob/main/AI',
            f'https://github.com/{authority["repository"]}/blob/main/AI_CONTEXT.json?raw=1#context',
            f'https://github.com/{mirror["repository"]}/blob/main/AI',
            owner_pages.replace("*", "mesh/live/?view=terminal"),
            mirror_pages.replace("*", "AI/"),
        ):
            with self.subTest(allowed=url):
                self.assertTrue(allowed(url))
        for url in (
            f'https://github.com/{authority["repository"]}/pull/523',
            f'https://github.com/{authority["repository"]}/blob/main/README.md',
            f'https://github.com/{authority["repository"]}/blob/other/AI',
            f'https://github.com/{authority["repository"]}-other/blob/main/AI',
            'https://github.com/unrelated/qik-vrt/blob/main/AI',
            'https://github.com.evil.example/ingolf-lohmann/qik-vrt/blob/main/AI',
            'http://github.com/ingolf-lohmann/qik-vrt/blob/main/AI',
            'https://ingolf-lohmann.github.io/unrelated/',
            'https://goldkelch.github.io/unrelated/',
            'https://other.github.io/qik-vrt/',
            'https://raumzeitterminal.de/',
            'http://127.0.0.1:8771/',
        ):
            with self.subTest(rejected=url):
                self.assertFalse(allowed(url))

    def test_host_permissions_add_only_owner_pages_origin(self) -> None:
        binding = json.loads((ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json").read_text())
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text())
        authority = binding["canonical_upstream"]["repository"]
        self.assertCountEqual(manifest["host_permissions"], [
            "https://api.github.com/*",
            f"https://github.com/{authority}/*",
            "https://ingolf-lohmann.github.io/qik-vrt/*",
            "https://goldkelch.github.io/qik-vrt/*",
            "http://127.0.0.1:8771/*",
            "http://localhost:8771/*",
        ])
        self.assertCountEqual(manifest["permissions"], ["storage", "alarms"])
        self.assertFalse(manifest.get("optional_host_permissions"))
        self.assertEqual(manifest["browser_specific_settings"]["gecko"]["strict_min_version"], "158.0")

    def run_adapter(self, assertions: str, *, clear_failure: bool = False) -> None:
        native_input = {"schema": "qikvrt_terminal_input_v1", "text": "test",
                        "page": "https://github.com/Goldkelch/qik-vrt/blob/main/AI"}
        state = terminal.State()
        digest, record = state.record(state="EFFECT_ACK_DONE",
            input_hash=terminal.sha256(terminal.canonical_json(native_input)),
            ordinary_release=True, reason="loopback terminal input satisfies bounded local policy")
        successor_digest, successor = state.record(state="EFFECT_ACK_DONE",
            input_hash=terminal.sha256(terminal.canonical_json(native_input)),
            ordinary_release=True, reason="single-use exact-bound loopback commit executed")
        harness = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const policy = JSON.parse(fs.readFileSync('policy/CANONICAL_UPSTREAM_REMOTE_V1.json', 'utf8'));
const source = fs.readFileSync('browser/firefox/qikvrt-terminal/background.js', 'utf8');
const calls = [];
let listener;
let response = async () => { throw new Error('unexpected fetch'); };
const stored = {qikvrtAuthority: policy.mirror.repository};
const fixture = __NATIVE_FIXTURE__;
let openClient;
const opened = [];
const clearedAlarms = [];
const lifecycle = {};
let clearFailure = __CLEAR_FAILURE__;
const sandbox = {
  console, URL, Uint8Array, atob, btoa, TextEncoder, crypto: require('node:crypto').webcrypto,
  location: {href: `https://github.com/${policy.mirror.repository}/blob/main/AI`},
  fetch: async (url, init) => { calls.push({url, init}); return response(url, init); },
  browser: {
    action: {onClicked: {addListener(value) { openClient = value; }}},
    tabs: {create: async value => { opened.push(value); }},
    storage: {local: {get: async () => stored, set: async value => Object.assign(stored, value)}},
    // Timer APIs are forbidden; the finite migration must clear the old alarm.
    alarms: {clear: async name => { clearedAlarms.push(name); if (clearFailure) throw Error("clear refused"); return true; },
      create() { throw Error("client timer forbidden"); },
      onAlarm: {addListener() { throw Error("alarm continuation forbidden"); }}},
    runtime: {getURL: path => 'moz-extension://qikvrt-test/' + path,
      onInstalled: {addListener(fn) { lifecycle.installed = fn; }}, onStartup: {addListener(fn) { lifecycle.startup = fn; }},
      onMessage: {addListener(value) { listener = value; }}},
  },
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox, {filename: 'background.js'});
function http(body, ack = null, status = 200) {
  return {ok: status >= 200 && status < 300, status,
    headers: {get: name => name === 'Effect-Ack' ? ack : name === 'content-type' ? 'application/json' : null},
    json: async () => body};
}
const digest = fixture.digest;
const token = 'exact-bound-single-use-token';
function ack(state = 'done', hash = digest, commitToken = token) {
  return `v=1, state=${state}, hash=:${Buffer.from(hash, 'hex').toString('base64')}:, token=:${Buffer.from(commitToken).toString('base64')}:`;
}
const input = fixture.input;
const preparedBody = {record_hash: digest, commit_token: token, record_url: '/effect-ack/records/' + digest};
const fullRecord = fixture.record;
async function prepare({prepareAck = ack(), body = preparedBody, record = fullRecord} = {}) {
  calls.length = 0;
  response = async url => {
    if (url.endsWith('/.well-known/effect-ack')) return http({});
    if (url.endsWith('/terminal/prepare')) return http(body, prepareAck);
    if (url.includes('/effect-ack/records/')) return http(record, ack());
    throw new Error('unexpected prepare route');
  };
  return listener({kind: 'PREPARE_EFFECT', payload: input});
}
"""
        harness = harness.replace("__CLEAR_FAILURE__", json.dumps(clear_failure))
        harness = harness.replace("__NATIVE_FIXTURE__", json.dumps({
            "input": native_input, "digest": digest, "record": record,
            "successor_digest": successor_digest, "successor": successor}))
        result = subprocess.run(
            ["node", "-e", harness + "\n(async () => {\n" + assertions + "\n})().catch(error => { console.error(error); process.exitCode = 1; });"],
            cwd=ROOT, text=True, capture_output=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_personal_navigation_is_explicit_packaged_tab_only_and_has_no_data_exchange(self):
        self.run_adapter(r'''
sandbox.browser.runtime.id = 'qikvrt-test';
const sender = {id:'qikvrt-test', url:sandbox.browser.runtime.getURL('client.html')};
for (const [payload, origin] of [[null,sender], [{confirmed:false},sender], [{confirmed:true},{}],
  [{confirmed:true},{id:'other',url:sender.url}], [{confirmed:true},{id:sender.id,url:'https://github.com/ingolf-lohmann/qik-vrt/blob/main/AI'}]]) {
  const result = await listener({kind:'OPEN_PERSONAL',payload}, origin);
  assert.equal(result.ok, false);
}
assert.equal(opened.length, 0);
const result = await listener({kind:'OPEN_PERSONAL',payload:{confirmed:true}}, sender);
assert.equal(opened.length, 1);
assert.equal(opened[0].url, 'http://127.0.0.1:8771/personal/#terminal');
assert.equal(Object.keys(opened[0]).length, 1);
assert.equal(result.state, 'EFFECT_ACK_CONTINUE');
assert.equal(result.ordinary_release, false);
assert.equal(calls.length, 0, 'navigation must not fetch protected data');
assert.equal(JSON.stringify(stored).includes('token'), false);
''')

    def test_event_only_startup_clears_legacy_alarm_without_network_poll(self) -> None:
        self.run_adapter(r"""
await Promise.resolve();
assert.deepEqual(clearedAlarms, ['qikvrt-repository-watchdog']);
assert.equal(calls.length, 0);
assert.equal(typeof lifecycle.installed, 'function');
assert.equal(typeof lifecycle.startup, 'function');
""")

    def test_failed_alarm_cleanup_holds_before_any_network_or_commit(self) -> None:
        self.run_adapter(r"""
// The initial finite migration fails before any user request.
for (const kind of ['OBSERVE_AUTHORITY', 'PREPARE_EFFECT', 'COMMIT_EFFECT']) {
  const result = await listener({kind, payload: fixture.input});
  assert.equal(result.ok, false);
  assert.equal(result.reason, 'legacy client alarm cleanup failed');
}
assert.equal(calls.length, 0);
""", clear_failure=True)

    def test_observation_uses_authority_even_from_mirror_entrypoint(self) -> None:
        self.run_adapter(r"""
const head = '1'.repeat(40), tree = '2'.repeat(40);
const base = policy.canonical_upstream.canonical_api_repository;
response = async url => {
  assert.ok(url.startsWith(base + '/'));
  if (url.endsWith('/git/ref/heads/main')) return http({object: {sha: head}});
  if (url.endsWith('/git/commits/' + head)) return http({tree: {sha: tree}});
  if (url.endsWith('/actions/runs?branch=main&per_page=30')) return http({workflow_runs: []});
  throw new Error('unexpected repository route');
};
const frame = await listener({kind: 'OBSERVE_AUTHORITY', payload: {repository: policy.mirror.repository}});
assert.equal(frame.ok, true);
assert.equal(frame.source.repository, policy.canonical_upstream.repository);
assert.equal(frame.source.ref, 'refs/heads/' + policy.canonical_upstream.default_branch);
assert.equal(frame.source.head, head); assert.equal(frame.source.tree, tree);
assert.equal(frame.terminal_semantics.rendering_is_authorization, false);
assert.equal(frame.terminal_semantics.ordinary_release_requires, 'VALID_EFFECT_ACK_DONE');
assert.notEqual(frame.ordinary_release, true);
assert.equal(stored.qikvrtWatchdogFrame.source.repository, policy.canonical_upstream.repository);
assert.equal(calls.length, 3);
for (const call of calls) {
  assert.equal(call.init.method, 'GET'); assert.equal(call.init.credentials, 'omit');
  assert.equal(call.init.cache, 'no-store');
  assert.equal(call.init.headers['X-GitHub-Api-Version'], '2022-11-28');
}
""")

    def test_authority_failure_and_invalid_binding_never_fall_back_to_mirror(self) -> None:
        self.run_adapter(r"""
const base = policy.canonical_upstream.canonical_api_repository;
for (const status of [403, 404, 503]) {
  calls.length = 0; response = async () => http({}, null, status);
  const frame = await listener({kind: 'OBSERVE_AUTHORITY'});
  assert.equal(frame.ok, false); assert.equal(frame.state, 'HOLD');
  assert.equal(frame.ordinary_release, false); assert.equal(calls.length, 1);
  assert.ok(calls[0].url.startsWith(base + '/'));
}
calls.length = 0;
response = async () => http({object: {sha: 'not-a-head'}});
let frame = await listener({kind: 'OBSERVE_AUTHORITY'});
assert.equal(frame.state, 'HOLD'); assert.equal(calls.length, 1);
calls.length = 0;
response = async url => url.endsWith('/git/ref/heads/main')
  ? http({object: {sha: '1'.repeat(40)}}) : http({tree: {sha: 'not-a-tree'}});
frame = await listener({kind: 'OBSERVE_AUTHORITY'});
assert.equal(frame.state, 'HOLD'); assert.equal(calls.length, 2);
assert.ok(calls.every(call => call.url.startsWith(base + '/')));
""")

    def test_prepare_requires_compact_and_full_done_binding_without_release(self) -> None:
        self.run_adapter(r"""
for (const options of [
  {prepareAck: null}, {prepareAck: 'malformed'},
  {prepareAck: ack('continue')}, {prepareAck: ack('block')},
  {body: {...preparedBody, record_hash: 'cd'.repeat(32)}},
  {body: {...preparedBody, commit_token: 'different-token'}},
  {body: {...preparedBody, record_url: 'https://evil.example/record'}},
  {record: {...fullRecord, state: 'EFFECT_ACK_CONTINUE'}},
  {record: {...fullRecord, ordinary_release: false}},
  {record: {...fullRecord, record_hash: 'sha256:' + 'cd'.repeat(32)}},
]) {
  const result = await prepare(options);
  assert.notEqual(result.record_validated, true); assert.equal(result.ordinary_release, false);
  assert.ok(calls.every(call => !call.url.endsWith('/terminal/commit')));
}
const result = await prepare();
assert.equal(result.record_validated, true); assert.equal(result.ordinary_release, false);
assert.equal(calls.length, 3);
assert.ok(calls.every(call => call.url.startsWith('http://127.0.0.1:8771/')));
""")

    def test_commit_confirmation_validation_and_effect_ack_boundaries(self) -> None:
        self.run_adapter(r"""
for (const payload of [null, {}, {confirmed: false},
  {confirmed: true, prepared: {record_validated: false, effect_ack: {state: 'EFFECT_ACK_DONE'}}},
  {confirmed: true, prepared: {record_validated: true, effect_ack: {state: 'EFFECT_ACK_CONTINUE'}}},
]) {
  calls.length = 0;
  const result = await listener({kind: 'COMMIT_EFFECT', payload});
  assert.equal(result.state, 'HOLD'); assert.equal(result.ordinary_release, false);
  assert.equal(calls.length, 0);
}
const prepared = await prepare();
for (const [header, body, released] of [
  [null, {ordinary_release: true}, false],
  [ack('continue'), {ordinary_release: true}, false],
  [ack('done'), {ordinary_release: false}, false],
  [ack('done', fixture.successor_digest), {ordinary_release: true}, false],
]) {
  calls.length = 0;
  response = async url => url.endsWith('/effect-ack/records/' + digest)
    ? http(fullRecord, ack()) : http(body, header);
  const result = await listener({kind: 'COMMIT_EFFECT', payload: {confirmed: true, prepared, request: input}});
  assert.equal(result.ordinary_release, released);
  const call = calls.find(item => item.url.endsWith('/terminal/commit'));
  assert.ok(call);
  assert.equal(call.url, 'http://127.0.0.1:8771/terminal/commit');
  assert.equal(call.init.method, 'POST');
  assert.equal(call.init.headers['Effect-Ack-Request'],
    `v=1, mode=commit, token=:${Buffer.from(token).toString('base64')}:, hash=:${Buffer.from(digest, 'hex').toString('base64')}:`);
  assert.equal(call.init.headers['X-QIKVRT-Commit-Token'], undefined);
  assert.equal(call.init.headers['X-QIKVRT-Record-Hash'], undefined);
  assert.deepEqual(JSON.parse(call.init.body), input);
}
""")

    def test_standalone_action_opens_packaged_client_without_page_or_network(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text())
        self.assertEqual(manifest["action"]["default_title"], "Universales Raumzeit-Terminal")
        html = (ROOT / "browser/firefox/qikvrt-terminal/client.html").read_text()
        self.assertIn('src="content.js"', html)
        self.assertIn('href="terminal.css"', html)
        self.assertNotIn("<iframe", html)
        self.assertNotIn("https://", html)
        self.run_adapter(r"""
openClient();
assert.equal(opened.length, 1);
assert.equal(opened[0].url, 'moz-extension://qikvrt-test/client.html');
assert.equal(calls.length, 0);
""")

    def test_prepare_rejects_record_tampering_wrong_input_and_record_route(self) -> None:
        self.run_adapter(r"""
for (const options of [
  {record: {...fullRecord, reason: 'tampered content'}},
  {record: {...fullRecord, input_hash: 'sha256:' + '01'.repeat(32)}},
  {body: {...preparedBody, record_url: '/effect-ack/records/../terminal/commit'}},
  {body: {...preparedBody, record_url: preparedBody.record_url + '?redirect=other'}},
]) {
  const result = await prepare(options);
  assert.notEqual(result.record_validated, true);
  assert.equal(result.ordinary_release, false);
}
""")

    def test_commit_requires_successor_and_exact_independent_event_with_no_retry(self) -> None:
        self.run_adapter(r"""
const event = {event_id: 1, kind: 'TERMINAL_INPUT_ACCEPTED',
  record_hash: digest, input_hash: fullRecord.input_hash.slice(7),
  text: input.text, audio_present: false, video_present: false,
  observed_at: '2026-10-19T09:00:00Z', external_effect: 'NONE'};
const prepared = await prepare();
for (const fault of ['none', 'record', 'event', 'missing', 'lost', 'prepare-as-effect', 'unavailable']) {
  calls.length = 0;
  response = async url => {
    if (url.endsWith('/effect-ack/records/' + digest)) return http(fullRecord, ack());
    if (url.endsWith('/terminal/commit')) {
      if (fault === 'lost') throw new Error('reply lost');
      return http({ordinary_release: true, post_effect: event},
        ack('done', fault === 'prepare-as-effect' ? digest : fixture.successor_digest));
    }
    if (url.endsWith('/effect-ack/records/' + fixture.successor_digest)) {
      return http(fault === 'record' ? {...fixture.successor, reason: 'tampered'} : fixture.successor,
        ack('done', fixture.successor_digest), fault === 'unavailable' ? 503 : 200);
    }
    if (url.endsWith('/terminal/state')) return http({
      last_event: fault === 'missing' ? null : fault === 'event' ? {...event, text: 'different'} : event});
    throw new Error('unexpected route');
  };
  const result = await listener({kind: 'COMMIT_EFFECT', payload: {confirmed: true, prepared, request: input}});
  assert.equal(result.ordinary_release, fault === 'none', fault);
  assert.equal(result.readback_verified === true, fault === 'none', fault);
  assert.equal(result.retry_allowed, false);
  assert.equal(calls.filter(call => call.url.endsWith('/terminal/commit')).length, 1);
  assert.ok(calls.every(call => call.init.redirect === 'error'));
  if (fault === 'none') {
    assert.equal(result.effect_scope, 'LOOPBACK_TERMINAL_INPUT_ONLY');
    assert.equal(result.productive_effect_verified, false);
    assert.equal(calls.length, 4);
  }
}
calls.length = 0;
response = async url => { assert.ok(url.includes('/effect-ack/records/')); return http(fullRecord, ack()); };
const changed = await listener({kind: 'COMMIT_EFFECT', payload: {
  confirmed: true, prepared, request: {...input, text: 'changed after prepare'}}});
assert.equal(changed.ordinary_release, false);
assert.equal(calls.filter(call => call.url.endsWith('/terminal/commit')).length, 0);
""")

    def test_backend_allowlist_and_unrecognized_messages_remain_closed(self) -> None:
        self.run_adapter(r"""
for (const backend of ['https://evil.example', 'http://127.0.0.1:8772', 'http://localhost:8771/']) {
  stored.qikvrtBackend = backend; calls.length = 0;
  const result = await listener({kind: 'DISCOVER_EFFECT_ACK'});
  assert.equal(result.state, 'HOLD'); assert.equal(result.ordinary_release, false);
  assert.equal(calls.length, 0);
}
for (const message of [null, {}, {kind: 'OBSERVE_MIRROR'}, {kind: 'UNKNOWN', ordinary_release: true}]) {
  calls.length = 0;
  const result = await listener(message);
  assert.equal(result.state, 'HOLD'); assert.equal(result.ordinary_release, false);
  assert.equal(calls.length, 0);
}
""")


class FirefoxClientInteractionTests(unittest.TestCase):
    """UI state-machine checks; DOM fixture is not Firefox installation proof."""

    def run_ui(self, assertions: str) -> None:
        harness = r"""
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
function node() {
  return {listeners: {}, dataset: {}, style: {setProperty() {}}, disabled: false, value: '',
    textContent: '', setAttribute() {}, classList: {toggle() {}},
    addEventListener(name, action) { this.listeners[name] = action; }};
}
const host = node(), output = node(), status = node(), command = node(), commit = node();
const elements = {'[data-role=output]': output, '[data-role=status]': status,
  '[data-role=command]': command, '[data-role=video]': node(),
  '[data-role=media-state]': node(), '[data-act=commit]': commit, '[data-act=snapshot]': node()};
host.querySelector = selector => elements[selector] || node();
const calls = [];
let answer = async () => ({ok: true});
const sandbox = {console, location: {href: 'moz-extension://fixture/client.html'},
  document: {getElementById: () => null, createElement: () => host, body: {appendChild() {}}},
  browser: {storage: {local: {get: async () => ({})}},
    runtime: {sendMessage: async message => { calls.push(message); return answer(message); }, openOptionsPage() {}}}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('browser/firefox/qikvrt-terminal/content.js', 'utf8'), sandbox);
const tick = () => new Promise(resolve => setImmediate(resolve));
const click = act => host.listeners.click({target: {closest: () => ({dataset: {act}})}});
const prepared = {record_validated: true, effect_ack: {state: 'EFFECT_ACK_DONE'}};
"""
        result = subprocess.run(["node", "-e", harness + "\n(async () => {\nawait tick();\n" +
            assertions + "\n})().catch(error => { console.error(error); process.exitCode = 1; });"],
            cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_edit_during_prepare_and_double_click_cannot_release_stale_input(self):
        self.run_ui(r"""
command.value = 'original';
let resolve;
answer = message => message.kind === 'PREPARE_EFFECT' ? new Promise(r => { resolve = r; }) : {ok: true};
const pending = click('prepare');
await tick();
await click('prepare');
assert.equal(calls.filter(c => c.kind === 'PREPARE_EFFECT').length, 1);
command.value = 'edited';
command.listeners.input();
resolve(prepared);
await pending;
assert.equal(commit.disabled, true);
assert.equal(status.dataset.state, 'HOLD');
await click('commit');
assert.equal(calls.filter(c => c.kind === 'COMMIT_EFFECT').length, 0);
""")

    def test_prepare_requires_full_validation_and_commit_preserves_actual_readback(self):
        self.run_ui(r"""
answer = async () => ({effect_ack: {state: 'EFFECT_ACK_DONE'}, record_validated: false});
await click('prepare'); assert.equal(commit.disabled, true);
answer = async message => message.kind === 'PREPARE_EFFECT' ? prepared
  : {ordinary_release: true, readback_verified: true, effect_scope: 'LOOPBACK_TERMINAL_INPUT_ONLY'};
await click('prepare'); assert.equal(commit.disabled, false);
calls.length = 0;
await click('commit');
assert.equal(status.dataset.state, 'EFFECT_ACK_DONE');
assert.match(status.textContent, /local terminal input only/);
assert.match(output.textContent, /readback_verified/);
assert.equal(calls.filter(c => c.kind === 'OBSERVE_AUTHORITY').length, 0);
await click('commit');
assert.equal(calls.filter(c => c.kind === 'COMMIT_EFFECT').length, 1);
answer = async message => message.kind === 'PREPARE_EFFECT' ? prepared : {ordinary_release: true};
await click('prepare'); await click('commit');
assert.equal(status.dataset.state, 'HOLD');
""")


class LoopbackTerminalE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        terminal.STATE = terminal.State()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), terminal.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None):
        data = None if body is None else json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        request_headers = dict(headers or {})
        if data is not None:
            request_headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(self.base + path, method=method, data=data, headers=request_headers)
        try:
            response = urllib.request.urlopen(req, timeout=3)
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, response.headers, payload
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            return exc.code, exc.headers, payload

    def prepare(self, payload: dict):
        status, headers, body = self.request(
            "/terminal/prepare",
            method="POST",
            body=payload,
            headers={"Effect-Ack-Request": "v=1, mode=prepare"},
        )
        self.assertEqual(status, 200)
        self.assertIn("state=done", headers["Effect-Ack"])
        self.assertIn("token=:", headers["Effect-Ack"])
        self.assertFalse(body["ordinary_release"])
        self.assertEqual(body["external_effect"], "NONE")
        return body

    def commit_headers(self, prepared: dict) -> dict[str, str]:
        return {"Effect-Ack-Request": commit_field(prepared["commit_token"], prepared["record_hash"])}

    def test_discovery_prepare_commit_reobserve_and_replay_block(self) -> None:
        status, headers, capability = self.request("/.well-known/effect-ack")
        self.assertEqual(status, 200)
        self.assertIn('rel="effect-ack"', headers["Link"])
        self.assertEqual(capability["external_effects"], "NONE")

        payload = {
            "schema": "qikvrt_terminal_input_v1",
            "submitted_at": "2026-08-16T21:00:00Z",
            "page": "https://github.com/Goldkelch/qik-vrt/blob/main/AI",
            "text": "eins und nicht keins",
            "audio": None,
            "video": None,
        }
        prepared = self.prepare(payload)

        status, record_headers, record = self.request(prepared["record_url"])
        self.assertEqual(status, 200)
        self.assertEqual(record["state"], "EFFECT_ACK_DONE")
        self.assertEqual(record["external_effect"], "NONE")
        self.assertIn("state=done", record_headers["Effect-Ack"])
        self.assertNotIn("token=:", record_headers["Effect-Ack"])

        wrong = dict(payload)
        wrong["text"] = "different"
        status, _, rejected = self.request(
            "/terminal/commit", method="POST", body=wrong, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertIn("differs", rejected["reason"])

        status, _, committed = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 200)
        self.assertTrue(committed["ordinary_release"])
        self.assertEqual(committed["post_effect"]["external_effect"], "NONE")
        self.assertEqual(committed["post_effect"]["text"], "eins und nicht keins")

        status, _, replay = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertIn("used", replay["reason"])

        status, _, observed = self.request("/terminal/state")
        self.assertEqual(status, 200)
        self.assertEqual(observed["events"], 1)
        self.assertEqual(observed["last_event"]["kind"], "TERMINAL_INPUT_ACCEPTED")

    def test_expired_token_fails_closed(self) -> None:
        payload = {
            "schema": "qikvrt_terminal_input_v1",
            "submitted_at": "2026-08-16T21:00:00Z",
            "page": "AI",
            "text": "x",
            "audio": None,
            "video": None,
        }
        prepared = self.prepare(payload)
        terminal.STATE.prepared[prepared["commit_token"]].expires_at = time.time() - 1
        status, _, body = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertFalse(body["ordinary_release"])

    def test_missing_or_malformed_effect_ack_request_fails_closed(self) -> None:
        payload = {"schema": "qikvrt_terminal_input_v1", "text": "x"}
        status, _, body = self.request("/terminal/prepare", method="POST", body=payload)
        self.assertEqual(status, 400)
        self.assertFalse(body["ordinary_release"])
        status, _, body = self.request(
            "/terminal/commit",
            method="POST",
            body=payload,
            headers={"Effect-Ack-Request": "v=1, mode=commit"},
        )
        self.assertEqual(status, 400)
        self.assertFalse(body["ordinary_release"])

    def test_durable_writer_is_not_exposed_over_http(self) -> None:
        payload = {"schema": "qikvrt_terminal_input_v1", "text": "owner-only"}
        for path in ("/terminal/durable-prepare", "/terminal/durable-commit", "/api/temdd/events"):
            status, _, _ = self.request(path, method="POST", body=payload,
                                        headers={"Effect-Ack-Request": "v=1, mode=prepare"})
            self.assertEqual(status, 404)
        self.assertEqual(terminal.STATE.events, [])


@unittest.skipUnless(hasattr(socket, "SO_PEERCRED"), "owner Unix peer credentials require Linux")
class DurableOwnerTerminalTests(unittest.TestCase):
    """Real Unix/SQLite contract fixture; not an execution of the deployed daemon.

    The carrier ledger is absent from this Mirror tree. This independent fixture
    follows the observed native-event/SQLite contract, including deduplication,
    commit-before-reply, denial of foreign subjects, and corrupt/ambiguous replies.
    """

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.state_dir = str(Path(self.temp.name) / "state")
        self.directory = Path(self.state_dir) / "temdd"
        self.directory.mkdir(parents=True, mode=0o700)
        self.subject = {"repository": "ingolf-lohmann/qik-vrt", "pr": 454, "head": "a" * 40, "tree": "b" * 40}
        self.body = {"schema": "qikvrt_terminal_input_v1", "text": "Geprüfter Modellbeweis; Produktabschluss offen.", "audio": None, "video": None}
        self.reply_mode = "normal"
        self.calls = 0
        self.start_fixture()

    def start_fixture(self) -> None:
        self.db = sqlite3.connect(self.directory / "events.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            self.db.executemany("INSERT OR IGNORE INTO meta VALUES (?,?)", (("schema", "1"), ("epoch", "c" * 32)))
            self.db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, binding TEXT NOT NULL, source TEXT NOT NULL, native_id TEXT NOT NULL, native_digest TEXT NOT NULL, body TEXT NOT NULL, body_digest TEXT NOT NULL, UNIQUE(source,native_id))")
        fixture = self
        class Ingress(socketserver.StreamRequestHandler):
            def handle(self):
                fixture.calls += 1
                raw = self.rfile.readline(65538)
                if not raw:
                    return
                native = json.loads(raw)
                if native["subject"] != fixture.subject:
                    self.wfile.write(b'{"state":"HOLD","reason":"EXACT_SUBJECT_MISMATCH","dod":false}\n')
                    return
                body = dict(native, schema="qikvrt_temdd_event_v1", recorded_at="2026-10-04T07:30:00Z",
                            payload_digest=terminal.sha256(terminal.canonical_json(native["payload"])), evidence_transfer="DENY", dod=False)
                digest = terminal.sha256(terminal.canonical_json(body))
                provenance = native["provenance"]
                if fixture.reply_mode == "ack_without_persistence":
                    event = dict(body, id="c" * 32 + ":1", ledger_digest=digest)
                else:
                    with fixture.db:
                        old = fixture.db.execute("SELECT seq,native_digest FROM events WHERE source=? AND native_id=?", (provenance["source"], provenance["native_event_id"])).fetchone()
                        if old:
                            if old[1] != terminal.sha256(terminal.canonical_json(native)):
                                self.wfile.write(b'{"state":"HOLD","reason":"NATIVE_EVENT_ID_CONFLICT","dod":false}\n')
                                return
                            seq = old[0]
                        else:
                            seq = fixture.db.execute("INSERT INTO events(binding,source,native_id,native_digest,body,body_digest) VALUES (?,?,?,?,?,?)",
                                (terminal.sha256(terminal.canonical_json(native["subject"])), provenance["source"], provenance["native_event_id"],
                                 terminal.sha256(terminal.canonical_json(native)), terminal.canonical_json(body).decode(), digest)).lastrowid
                    event = dict(body, id="c" * 32 + ":" + str(seq), ledger_digest=digest)
                if fixture.reply_mode == "drop_after_persistence":
                    return
                if fixture.reply_mode == "non_object_reply":
                    self.wfile.write(b"[]\n")
                    return
                if fixture.reply_mode == "wrong_reply":
                    event["ledger_digest"] = "0" * 64
                self.wfile.write(terminal.canonical_json({"state": "PERSISTED", "event": event, "authority_effect": False, "dod": False}) + b"\n")
        path = self.directory / "ingress.sock"
        if path.exists():
            path.unlink()
        self.server = socketserver.UnixStreamServer(str(path), Ingress)
        path.chmod(0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop_fixture(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.db.close()

    def tearDown(self) -> None:
        self.stop_fixture()
        self.temp.cleanup()

    def prepare(self):
        return terminal.durable_prepare(self.body, self.subject, self.state_dir)

    def commit(self, prepared):
        return terminal.durable_commit(prepared, prepared["prepare_hash"], self.body, self.subject, self.state_dir)

    def readback(self, prepared):
        return terminal.durable_readback(prepared, prepared["prepare_hash"], self.body, self.subject, self.state_dir)

    def count(self):
        return self.db.execute("SELECT count(*) FROM events").fetchone()[0]

    def test_prepare_has_no_ledger_write(self):
        prepared = self.prepare()
        self.assertFalse(prepared["EFFECT_ACK_DONE"])
        self.assertEqual((self.calls, self.count()), (0, 0))

    def test_commit_and_restart_have_fresh_durable_readback(self):
        prepared = self.prepare()
        receipt = self.commit(prepared)
        self.assertTrue(receipt["durable_persisted"])
        self.assertFalse(receipt["EFFECT_ACK_DONE"])
        self.assertFalse(receipt["public_readback_verified"])
        self.assertEqual(receipt["durable_readback"]["subject"], self.subject)
        self.stop_fixture()
        self.start_fixture()
        self.assertEqual(self.readback(prepared), receipt)

    def test_repeat_commit_is_readback_only_and_single_effect(self):
        prepared = self.prepare()
        receipt = self.commit(prepared)
        with self.assertRaisesRegex(terminal.DurableHold, "ALREADY_COMMITTED"):
            self.commit(prepared)
        self.assertEqual(self.readback(prepared), receipt)
        self.assertEqual((self.calls, self.count()), (1, 1))

    def test_concurrent_commits_share_one_native_effect(self):
        prepared = self.prepare()
        results = []
        def commit():
            try:
                results.append(self.commit(prepared))
            except terminal.DurableHold as exc:
                results.append(str(exc))
        threads = [threading.Thread(target=commit) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertTrue(any(isinstance(x, dict) and x["durable_persisted"] for x in results))
        self.assertEqual(self.count(), 1)
        self.assertLessEqual(self.calls, 2)

    def test_wrong_prepare_hash_cannot_write(self):
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "HASH_MISMATCH"):
            terminal.durable_commit(prepared, "sha256:" + "0" * 64, self.body, self.subject, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_changed_preparation_cannot_write(self):
        prepared = self.prepare()
        prepared["preparation"]["event"]["message"] += "tampered"
        with self.assertRaisesRegex(terminal.DurableHold, "HASH_MISMATCH"):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_changed_payload_cannot_write(self):
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "INPUT_MISMATCH"):
            terminal.durable_commit(prepared, prepared["prepare_hash"], dict(self.body, text="changed"), self.subject, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_changed_head_or_tree_cannot_write(self):
        prepared = self.prepare()
        for key in ("head", "tree", "repository", "pr"):
            other = dict(self.subject)
            other[key] = 455 if key == "pr" else "f" * 40
            with self.assertRaisesRegex(terminal.DurableHold, "SUBJECT_OR_ROUTE_MISMATCH"):
                terminal.durable_commit(prepared, prepared["prepare_hash"], self.body, other, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_expired_preparation_cannot_write(self):
        prepared = self.prepare()
        prepared["preparation"]["expires_at"] = int(time.time()) - 1
        prepared["prepare_hash"] = "sha256:" + terminal.sha256(terminal.canonical_json(prepared["preparation"]))
        with self.assertRaisesRegex(terminal.DurableHold, "EXPIRED"):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_ledger_epoch_change_blocks_commit(self):
        prepared = self.prepare()
        with self.db:
            self.db.execute("UPDATE meta SET value=? WHERE key='epoch'", ("d" * 32,))
        with self.assertRaisesRegex(terminal.DurableHold, "LEDGER_CHANGED"):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_socket_permissions_never_widened(self):
        prepared = self.prepare()
        path = self.directory / "ingress.sock"
        path.chmod(0o666)
        with self.assertRaises(terminal.DurableHold):
            self.commit(prepared)
        self.assertEqual(path.stat().st_mode & 0o777, 0o666)
        self.assertEqual(self.calls, 0)

    def test_socket_symlink_rejected(self):
        prepared = self.prepare()
        path = self.directory / "ingress.sock"
        real = self.directory / "real.sock"
        path.rename(real)
        path.symlink_to(real)
        with self.assertRaises(terminal.DurableHold):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_parent_symlink_and_non_owner_directory_rejected(self):
        alias = Path(self.temp.name) / "alias"
        alias.symlink_to(self.state_dir)
        with self.assertRaises(terminal.DurableHold):
            terminal.durable_prepare(self.body, self.subject, str(alias))
        self.directory.chmod(0o755)
        with self.assertRaises(terminal.DurableHold):
            self.prepare()
        self.assertEqual(self.calls, 0)

    def test_media_and_unbounded_input_not_admitted(self):
        for body in (dict(self.body, audio="data"), dict(self.body, video="data"), dict(self.body, text="x" * 4097), dict(self.body, command="id")):
            with self.assertRaises(terminal.DurableHold):
                terminal.durable_prepare(body, self.subject, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_foreign_peer_uid_cannot_write(self):
        prepared = self.prepare()
        with mock.patch.object(terminal.struct, "unpack", return_value=(1, terminal.os.geteuid() + 1, 1)):
            with self.assertRaisesRegex(terminal.DurableHold, "PEER_OWNER_MISMATCH"):
                self.commit(prepared)
        self.assertEqual(self.count(), 0)

    def test_ingress_subject_mismatch_not_success(self):
        other = dict(self.subject, head="f" * 40)
        prepared = terminal.durable_prepare(self.body, other, self.state_dir)
        with self.assertRaises(terminal.DurableHold):
            terminal.durable_commit(prepared, prepared["prepare_hash"], self.body, other, self.state_dir)
        self.assertEqual(self.count(), 0)

    def test_ack_without_sqlite_effect_cannot_succeed(self):
        self.reply_mode = "ack_without_persistence"
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "NOT_OBSERVED"):
            self.commit(prepared)
        self.assertEqual((self.calls, self.count()), (1, 0))

    def test_spoofed_ack_cannot_replace_exact_readback(self):
        self.reply_mode = "wrong_reply"
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "REPLY_DIFFERS"):
            self.commit(prepared)
        self.assertEqual((self.calls, self.count()), (1, 1))

    def test_non_object_reply_is_hold_then_readback_only(self):
        self.reply_mode = "non_object_reply"
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "REPLY_OBJECT_REQUIRED"):
            self.commit(prepared)
        self.assertTrue(self.readback(prepared)["durable_persisted"])
        self.assertEqual((self.calls, self.count()), (1, 1))

    def test_ambiguous_commit_recovers_by_readback_without_resubmission(self):
        self.reply_mode = "drop_after_persistence"
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "DO_NOT_RESUBMIT"):
            self.commit(prepared)
        self.stop_fixture()
        self.start_fixture()
        self.assertTrue(self.readback(prepared)["durable_persisted"])
        self.assertEqual((self.calls, self.count()), (1, 1))

    def test_corrupt_ledger_readback_fails_closed(self):
        prepared = self.prepare()
        self.commit(prepared)
        with self.db:
            self.db.execute("UPDATE events SET body_digest=?", ("0" * 64,))
        with self.assertRaisesRegex(terminal.DurableHold, "READBACK_MISMATCH"):
            self.readback(prepared)

    def test_non_object_ledger_body_is_a_hold(self):
        prepared = self.prepare()
        self.commit(prepared)
        with self.db:
            self.db.execute("UPDATE events SET body='[]',body_digest=?", (terminal.sha256(b"[]"),))
        with self.assertRaisesRegex(terminal.DurableHold, "BODY_OBJECT_REQUIRED"):
            self.readback(prepared)

    def test_cli_roundtrip_and_dirty_checkout_rejection(self):
        root = Path(self.temp.name) / "checkout"
        root.mkdir()
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()
        git("init", "-q")
        git("remote", "add", "origin", "https://github.com/ingolf-lohmann/qik-vrt.git")
        (root / "source").write_text("fixture\n")
        git("add", "source")
        git("-c", "user.name=Contract Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        self.subject.update(head=git("rev-parse", "HEAD"), tree=git("rev-parse", "HEAD^{tree}"))
        input_file = Path(self.temp.name) / "input.json"
        input_file.write_bytes(terminal.canonical_json(self.body))
        args = ["--root", str(root), "--repository", self.subject["repository"], "--pr", "454", "--expected-head", self.subject["head"],
                "--expected-tree", self.subject["tree"], "--input", str(input_file), "--state-dir", self.state_dir]
        def cli(operation, *extra):
            p = subprocess.run([sys.executable, "-B", str(MODULE_PATH), operation, *args, *extra], capture_output=True, text=True, timeout=10)
            return p.returncode, json.loads(p.stdout)
        code, prepared = cli("durable-prepare")
        self.assertEqual(code, 0)
        prepared_file = Path(self.temp.name) / "prepared.json"
        prepared_file.write_bytes(terminal.canonical_json(prepared))
        extra = ("--prepared", str(prepared_file), "--prepare-hash", prepared["prepare_hash"])
        code, receipt = cli("durable-commit", *extra)
        self.assertEqual(code, 0)
        self.assertTrue(receipt["durable_persisted"])
        code, readback = cli("durable-readback", *extra)
        self.assertEqual((code, readback), (0, receipt))
        (root / "source").write_text("dirty\n")
        code, hold = cli("durable-prepare")
        self.assertEqual(code, 2)
        self.assertFalse(hold["EFFECT_ACK_DONE"])
        self.assertEqual((self.calls, self.count()), (1, 1))


if __name__ == "__main__":
    unittest.main()
