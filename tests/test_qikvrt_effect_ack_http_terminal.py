from __future__ import annotations

import base64
import contextlib
import importlib.util
import http.client
import json
import os
import sys
import subprocess
import socket
import threading
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest import mock
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "qikvrt_effect_ack_http_terminal.py"
sys.path.insert(0, str(ROOT / 'src'))
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
        self.assertIn("http://127.0.0.1/*", manifest["host_permissions"])
        self.assertNotIn("http://127.0.0.1:8771/*", manifest["host_permissions"])
        csp = manifest["content_security_policy"]["extension_pages"]
        self.assertIn("script-src 'self'", csp)
        self.assertIn("http://127.0.0.1:8771", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertEqual(policy["http"]["request_field"], "Effect-Ack-Request")
        self.assertEqual(policy["http"]["response_field"], "Effect-Ack")
        self.assertEqual(policy["http"]["link_relation"], "effect-ack")
        self.assertEqual(schema["properties"]["schema"]["const"], "qikvrt_terminal_frame_v1")

    def test_firefox_source_preserves_terminal_boundaries(self) -> None:
        background = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
        content = (ROOT / "browser/firefox/qikvrt-terminal/content.js").read_text(encoding="utf-8")
        manifest = (ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8")
        self.assertIn("browser.alarms", background)
        self.assertIn("WATCHDOG_PERIOD_MINUTES = 5", background)
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

    def test_late_repository_observation_cannot_replace_prepared_effect(self):
        # Execute the actual content script with deferred browser responses.
        # This controls the native failing ordering, not a second implementation.
        script = r'''
        const fs = require('fs'), vm = require('vm'), assert = require('assert');
        const elements = new Map();
        function element() { return {textContent:'', value:'nonce', disabled:true,
            dataset:{}, style:{setProperty(){}}, setAttribute(){},
            classList:{toggle(){}}, querySelector(selector) {
                if (!elements.has(selector)) elements.set(selector, element());
                return elements.get(selector);
            }, addEventListener(name, handler){this.handler=handler;}}; }
        const host=element(); let finishObservation;
        const prepared={effect_ack:{state:'EFFECT_ACK_DONE'},record_validated:true,tag:'exact-prepared'};
        const context={document:{getElementById(){return null;},createElement(){return host;},
              body:{appendChild(){}}},location:{href:'https://goldkelch.github.io/qik-vrt/'},
              browser:{storage:{local:{get:async()=>({})}},runtime:{sendMessage(message){
                if(message.kind==='OBSERVE_AUTHORITY') return new Promise(resolve=>finishObservation=resolve);
                if(message.kind==='PREPARE_EFFECT') return Promise.resolve(prepared);
                throw new Error('unexpected message');}}}};
        vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
        setImmediate(async()=>{try {
            assert.equal(typeof finishObservation,'function');
            await host.handler({target:{closest(){return {dataset:{act:'prepare'}};}}});
            const output=host.querySelector('[data-role=output]');
            assert.equal(JSON.parse(output.textContent).tag,'exact-prepared');
            assert.equal(host.querySelector('[data-act=commit]').disabled,false);
            finishObservation({ok:false,state:'HOLD',reason:'github 404'});
            await new Promise(resolve=>setImmediate(resolve));
            assert.equal(JSON.parse(output.textContent).tag,'exact-prepared',
                'late read-only observer overwrote exact prepared effect');
            assert.equal(host.querySelector('[data-role=status]').dataset.state,'PREPARED_DONE');
        } catch(error) { console.error(error);process.exitCode=1;}});
        '''
        result = subprocess.run(['node', '-e', script,
                                 str(ROOT / 'browser/firefox/qikvrt-terminal/content.js')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

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
        terminal.STATE.close()

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


class SeedBoundTerminalE2ETests(LoopbackTerminalE2ETests):
    def setUp(self):
        super().setUp()
        self.seed = ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin'
        terminal.STATE = terminal.State(self.seed)

    def test_altered_truncated_absent_seed_cannot_admit(self):
        original = self.seed.read_bytes()
        self.assertEqual(len(original), 400)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'seed.bin'
            for data in (bytes([original[0] ^ 1]) + original[1:], original[:-1], original + b'x'):
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    terminal.State(path)
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'SEED_UNAVAILABLE'):
                terminal.State(path)

    def test_changed_seed_between_prepare_and_commit_has_no_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'seed.bin'
            original = self.seed.read_bytes()
            path.write_bytes(original)
            terminal.STATE = terminal.State(path)
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'stale-seed'}
            prepared = self.prepare(payload)
            path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            status, _, _ = self.request('/terminal/commit', method='POST', body=payload,
                                        headers=self.commit_headers(prepared))
            self.assertEqual(status, 400)
            self.assertEqual(self.request('/terminal/state')[2]['events'], 0)

    def test_seed_binds_full_record_and_event_and_export(self):
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'bound-seed'}
        prepared = self.prepare(payload)
        record = self.request(prepared['record_url'])[2]
        claimed = record.pop('record_hash')
        self.assertEqual(claimed, 'sha256:' + terminal.sha256(terminal.canonical_json(record)))
        self.assertEqual(record['seed_binding'], terminal.STATE.seed_binding)
        status, _, _ = self.request('/terminal/commit', method='POST', body=payload,
                                    headers=self.commit_headers(prepared))
        self.assertEqual(status, 200)
        snapshot = self.request('/terminal/events')[2]
        self.assertEqual(snapshot['events'][0]['seed_binding'], record['seed_binding'])
        self.assertEqual(snapshot['events_sha256'], terminal.sha256(terminal.canonical_json(snapshot['events'])))
        self.assertEqual(snapshot['persistence_scope'], 'PROCESS_LIFETIME_ONLY')

    def test_shared_token_concurrent_commit_has_exactly_one_effect(self):
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'same-token-race'}
        prepared = self.prepare(payload)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.request('/terminal/commit', method='POST',
                body=payload, headers=self.commit_headers(prepared))[0], range(8)))
        self.assertEqual(sorted(results), [200] + [409] * 7)
        self.assertEqual(self.request('/terminal/state')[2]['events'], 1)


    def test_durable_records_events_survive_restart_and_replay_stays_closed(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as cleanup:
            cleanup.callback(lambda: terminal.STATE.close())
            state_path = Path(directory) / 'effect-ack-state.json'
            terminal.STATE.close()
            terminal.STATE = terminal.State(self.seed, state_path)
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'durable-restart'}
            prepared = self.prepare(payload)
            status, _, committed = self.request(
                '/terminal/commit', method='POST', body=payload,
                headers=self.commit_headers(prepared))
            self.assertEqual(status, 200)
            record_url = prepared['record_url']
            before = self.request('/terminal/events')[2]
            self.assertEqual(before['persistence_scope'], 'FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE')
            self.assertTrue(state_path.is_file())

            terminal.STATE.close()
            terminal.STATE = terminal.State(self.seed, state_path)
            after = self.request('/terminal/events')[2]
            self.assertEqual(after, before)
            self.assertEqual(self.request(record_url)[0], 200)
            self.assertEqual(self.request('/terminal/state')[2]['events'], 1)
            status, _, replay = self.request(
                '/terminal/commit', method='POST', body=payload,
                headers=self.commit_headers(prepared))
            self.assertEqual(status, 409)
            self.assertIn('invalid', replay['reason'])
            self.assertEqual(self.request('/terminal/events')[2], before)
            self.assertEqual(committed['post_effect']['event_id'], 1)


    def test_durable_state_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'effect-ack-state.json'
            terminal.STATE.close()
            terminal.STATE = terminal.State(self.seed, state_path)
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'tamper-check'}
            prepared = self.prepare(payload)
            self.assertEqual(self.request(
                '/terminal/commit', method='POST', body=payload,
                headers=self.commit_headers(prepared))[0], 200)
            value = json.loads(state_path.read_text())
            value['events'][0]['text'] = 'tampered'
            state_path.write_text(json.dumps(value))
            terminal.STATE.close()
            with self.assertRaises(terminal.PersistenceError):
                terminal.State(self.seed, state_path)


    def test_durable_state_truncation_and_restart_seed_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'effect-ack-state.json'
            terminal.STATE.close()
            terminal.STATE = terminal.State(self.seed, state_path)
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'restart-binding'}
            prepared = self.prepare(payload)
            self.assertEqual(self.request(
                '/terminal/commit', method='POST', body=payload,
                headers=self.commit_headers(prepared))[0], 200)
            durable = state_path.read_bytes()
            terminal.STATE.close()
            with self.assertRaises(terminal.PersistenceError):
                terminal.State(None, state_path)
            state_path.write_bytes(durable[: max(1, len(durable) // 2)])
            with self.assertRaises(terminal.PersistenceError):
                terminal.State(self.seed, state_path)


    def test_real_process_restart_preserves_events_records_and_consumed_token(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'effect-ack-state.json'
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            base = f'http://127.0.0.1:{port}'

            def start():
                process = subprocess.Popen(
                    [sys.executable, '-B', str(MODULE_PATH), '--host', '127.0.0.1',
                     '--port', str(port), '--seed', str(self.seed), '--state', str(state_path)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertIsNotNone(process.stdout)
                ready = process.stdout.readline()
                self.assertIn('"state": "READY"', ready)
                return process

            def request(path, *, method='GET', body=None, field=None):
                data = None if body is None else json.dumps(
                    body, sort_keys=True, separators=(',', ':')).encode()
                headers = {'Content-Type': 'application/json'}
                if field is not None:
                    headers['Effect-Ack-Request'] = field
                req = urllib.request.Request(base + path, method=method, data=data, headers=headers)
                try:
                    response = urllib.request.urlopen(req, timeout=5)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    return response.code, json.load(response)

            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'real-process-restart'}
            first = start()
            try:
                status, prepared = request(
                    '/terminal/prepare', method='POST', body=payload, field='v=1, mode=prepare')
                self.assertEqual(status, 200)
                field = commit_field(prepared['commit_token'], prepared['record_hash'])
                self.assertEqual(request(
                    '/terminal/commit', method='POST', body=payload, field=field)[0], 200)
                before = request('/terminal/events')[1]
                self.assertEqual(before['persistence_scope'], 'FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE')
                self.assertEqual(request(prepared['record_url'])[0], 200)
            finally:
                first.terminate()
                first.wait(timeout=5)
                first.stdout.close()
                first.stderr.close()

            second = start()
            try:
                after = request('/terminal/events')[1]
                self.assertEqual(after, before)
                self.assertEqual(request(prepared['record_url'])[0], 200)
                status, replay = request(
                    '/terminal/commit', method='POST', body=payload, field=field)
                self.assertEqual(status, 409)
                self.assertIn('invalid', replay['reason'])
                self.assertEqual(request('/terminal/events')[1], before)
            finally:
                second.terminate()
                second.wait(timeout=5)
                second.stdout.close()
                second.stderr.close()


    def test_persisted_effect_survives_response_path_crash_without_duplicate(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as cleanup:
            cleanup.callback(lambda: terminal.STATE.close())
            state_path = Path(directory) / 'effect-ack-state.json'
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            wrapper = """
import os
import sys
sys.path.insert(0, sys.argv[1])
import qikvrt_effect_ack_http_terminal as m
from http.server import ThreadingHTTPServer
from pathlib import Path
original = m.State.persist
def crash_after_persist(self):
    original(self)
    if self.events:
        os._exit(73)
m.State.persist = crash_after_persist
m.STATE = m.State(Path(sys.argv[2]), Path(sys.argv[3]))
server = ThreadingHTTPServer(('127.0.0.1', int(sys.argv[4])), m.Handler)
print('READY', flush=True)
server.serve_forever()
"""
            process = subprocess.Popen(
                [sys.executable, '-B', '-c', wrapper, str(ROOT / 'src'),
                 str(self.seed), str(state_path), str(port)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(process.stdout.readline().strip(), 'READY')
            base = f'http://127.0.0.1:{port}'
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'persist-before-response'}
            data = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
            prepare = urllib.request.Request(
                base + '/terminal/prepare', data=data,
                headers={'Content-Type': 'application/json',
                         'Effect-Ack-Request': 'v=1, mode=prepare'})
            with urllib.request.urlopen(prepare, timeout=5) as response:
                prepared = json.load(response)
            field = commit_field(prepared['commit_token'], prepared['record_hash'])
            commit = urllib.request.Request(
                base + '/terminal/commit', data=data,
                headers={'Content-Type': 'application/json', 'Effect-Ack-Request': field})
            with self.assertRaises((OSError, http.client.RemoteDisconnected)):
                urllib.request.urlopen(commit, timeout=5).read()
            process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()
            self.assertEqual(process.returncode, 73)

            restored = terminal.State(self.seed, state_path)
            self.assertEqual(len(restored.events), 1)
            self.assertEqual(restored.events[0]['text'], payload['text'])
            self.assertIn(prepared['record_hash'], restored.records)
            terminal.STATE = restored
            status, _, replay = self.request(
                '/terminal/commit', method='POST', body=payload,
                headers={'Effect-Ack-Request': field})
            self.assertEqual(status, 409)
            self.assertIn('invalid', replay['reason'])
            self.assertEqual(len(terminal.STATE.events), 1)


    def test_parallel_unique_commits_remain_lossless_after_durable_reload(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as cleanup:
            cleanup.callback(lambda: terminal.STATE.close())
            state_path = Path(directory) / 'effect-ack-state.json'
            terminal.STATE.close()
            terminal.STATE = terminal.State(self.seed, state_path)
            payloads = [
                {'schema': 'qikvrt_terminal_input_v1', 'text': f'durable-parallel-{index}'}
                for index in range(8)
            ]
            prepared = [self.prepare(payload) for payload in payloads]
            with ThreadPoolExecutor(max_workers=8) as pool:
                statuses = list(pool.map(
                    lambda pair: self.request(
                        '/terminal/commit', method='POST', body=pair[0],
                        headers=self.commit_headers(pair[1]))[0],
                    zip(payloads, prepared)))
            self.assertEqual(statuses, [200] * 8)
            before = self.request('/terminal/events')[2]
            terminal.STATE.close()
            terminal.STATE = terminal.State(self.seed, state_path)
            after = self.request('/terminal/events')[2]
            self.assertEqual(after, before)
            self.assertEqual([event['event_id'] for event in after['events']], list(range(1, 9)))


class BoundedSeedRingControlsTests(unittest.TestCase):
    def test_real_http_fanout_race_and_lossless_snapshot(self):
        from tools.qikvrt_firefox_windows_witness import bounded_ring_controls
        terminal.STATE = terminal.State(ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')
        server = ThreadingHTTPServer(('127.0.0.1', 8771), terminal.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = bounded_ring_controls(terminal)
            self.assertEqual([x['parallel_clients'] for x in result['fanout']], [1, 2, 4, 8])
            self.assertEqual(result['event_snapshot']['event_count'], 17)
            self.assertFalse(result['authority_mirror_live_nodes_tested'])
            self.assertFalse(result['unbounded_scalability_proved'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class DurableTerminalE2ETests(LoopbackTerminalE2ETests):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.seed = ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin'
        terminal.STATE = terminal.State(self.seed, state_root=self.root)

    def tearDown(self):
        super().tearDown()
        terminal.STATE.close()
        self.directory.cleanup()

    def restart(self):
        terminal.STATE.close()
        terminal.STATE = terminal.State(self.seed, state_root=self.root)

    def commit(self, payload, prepared):
        return self.request('/terminal/commit', method='POST', body=payload,
                            headers=self.commit_headers(prepared))

    def test_prepare_survives_restart_but_payload_substitution_does_not(self):
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'prepared-before-restart'}
        prepared = self.prepare(payload)
        record = self.request(prepared['record_url'])[2]
        self.restart()
        self.assertEqual(self.request(prepared['record_url'])[2], record)
        self.assertEqual(self.commit(dict(payload, text='substitution'), prepared)[0], 409)
        self.assertEqual(self.commit(payload, prepared)[0], 200)
        snapshot = self.request('/terminal/events')[2]
        self.restart()
        self.assertEqual(self.request('/terminal/events')[2], snapshot)
        self.assertEqual(self.commit(payload, prepared)[0], 409)
        self.assertEqual(self.request('/terminal/events')[2], snapshot)

    def test_expiry_remains_enforced_after_restart(self):
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'expires'}
        with mock.patch.object(terminal, 'TOKEN_TTL_SECONDS', -1):
            prepared = self.prepare(payload)
        self.restart()
        self.assertEqual(self.commit(payload, prepared)[0], 409)
        self.assertEqual(self.request('/terminal/events')[2]['event_count'], 0)

    def test_parallel_durable_commits_keep_order_and_single_use_after_restart(self):
        payloads = [{'schema': 'qikvrt_terminal_input_v1', 'text': 'parallel-' + str(n)} for n in range(8)]
        prepared = [self.prepare(payload) for payload in payloads]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda pair: self.commit(*pair), zip(payloads, prepared)))
        self.assertEqual([status for status, _, _ in results], [200] * 8)
        shared = self.prepare(payloads[0])
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.commit(payloads[0], shared)[0], range(8)))
        self.assertEqual(sorted(results), [200] + [409] * 7)
        before = self.request('/terminal/events')[2]
        self.assertEqual([e['event_id'] for e in before['events']], list(range(1, 10)))
        self.restart()
        self.assertEqual(self.request('/terminal/events')[2], before)
        for payload, value in zip(payloads + [payloads[0]], prepared + [shared]):
            self.assertEqual(self.commit(payload, value)[0], 409)
        self.assertEqual(self.request('/terminal/events')[2], before)

    def test_capacity_is_preserved_across_restart_without_eviction(self):
        with mock.patch.object(terminal, 'MAX_EVENTS', 2):
            for n in range(2):
                payload = {'schema': 'qikvrt_terminal_input_v1', 'text': str(n)}
                self.assertEqual(self.commit(payload, self.prepare(payload))[0], 200)
            before = self.request('/terminal/events')[2]
            self.restart()
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'over-capacity'}
            self.assertEqual(self.commit(payload, self.prepare(payload))[0], 409)
            self.assertEqual(self.request('/terminal/events')[2], before)
            self.restart()
            self.assertEqual(self.request('/terminal/events')[2], before)

    def test_corrupt_truncated_duplicate_and_reordered_state_fail_closed(self):
        for n in range(2):
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': str(n)}
            self.assertEqual(self.commit(payload, self.prepare(payload))[0], 200)
        path = terminal.STATE.store
        valid = path.read_bytes()
        terminal.STATE.close()
        reordered = json.loads(valid)
        reordered['events'].reverse()
        reordered.pop('state_sha256')
        reordered['state_sha256'] = terminal.sha256(terminal.canonical_json(reordered))
        corruptions = [b'', valid[:-1], valid[:len(valid)//2], valid.replace(b'TERMINAL_INPUT_ACCEPTED', b'TERMINAL_INPUT_ALTERED_'),
                       valid.replace(b'{', b'{"schema":"duplicate",', 1),
                       terminal.canonical_json(reordered) + b'\n']
        for raw in corruptions:
            with self.subTest(bytes=len(raw)):
                path.write_bytes(raw)
                with self.assertRaises(terminal.PersistenceError):
                    terminal.State(self.seed, state_root=self.root)
                self.assertEqual(path.read_bytes(), raw)  # No auto-reset or partial salvage.
        path.write_bytes(valid)
        terminal.STATE = terminal.State(self.seed, state_root=self.root)
        self.assertEqual(len(terminal.STATE.events), 2)

    def test_restart_seed_mismatch_and_unseeded_downgrade_do_not_rewrite_state(self):
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'seed-bound'}
        self.assertEqual(self.commit(payload, self.prepare(payload))[0], 200)
        path = terminal.STATE.store
        valid = path.read_bytes()
        terminal.STATE.close()
        bad = self.root / 'bad-seed.bin'
        bad.write_bytes(self.seed.read_bytes()[:-1])
        with self.assertRaises(ValueError):
            terminal.State(bad, state_root=self.root)
        with self.assertRaises(terminal.PersistenceError):
            terminal.State(None, state_root=self.root)
        self.assertEqual(path.read_bytes(), valid)
        terminal.STATE = terminal.State(self.seed, state_root=self.root)

    def test_competing_process_store_owner_and_symlink_are_refused(self):
        with self.assertRaises(BlockingIOError):
            terminal.State(self.seed, state_root=self.root)
        result = subprocess.run([sys.executable, '-B', str(MODULE_PATH), '--state-root', str(self.root),
                                 '--seed', str(self.seed), '--port', '0'],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('READY', result.stdout)
        if os.name == 'nt':
            # Junction creation needs no symbolic-link privilege on Windows.
            # Exercise a native reparse root rather than claiming a POSIX symlink test.
            junction = self.root / 'junction'
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(self.root / '.qikvrt')],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            try:
                with self.assertRaises(terminal.PersistenceError):
                    terminal.State(self.seed, state_root=junction)
            finally:
                junction.rmdir()
            return
        path = terminal.STATE.store
        terminal.STATE.close()
        outside = self.root / 'outside.json'
        path.rename(outside)
        path.symlink_to(outside)
        valid = outside.read_bytes()
        with self.assertRaises(terminal.PersistenceError):
            terminal.State(self.seed, state_root=self.root)
        self.assertEqual(outside.read_bytes(), valid)
        path.unlink()
        outside.rename(path)
        terminal.STATE = terminal.State(self.seed, state_root=self.root)

    def test_missing_initialized_snapshot_cannot_silently_reset_confirmed_effects(self):
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'must-not-disappear'}
        self.assertEqual(self.commit(payload, self.prepare(payload))[0], 200)
        path = terminal.STATE.store
        if os.name == 'posix':
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        valid = path.read_bytes()
        terminal.STATE.close()
        path.unlink()
        with self.assertRaisesRegex(terminal.PersistenceError, 'MISSING_NO_AUTOMATIC_RESET'):
            terminal.State(self.seed, state_root=self.root)
        self.assertFalse(path.exists())
        path.write_bytes(valid)
        terminal.STATE = terminal.State(self.seed, state_root=self.root)

    def test_write_or_directory_fsync_failure_never_acknowledges_or_retries(self):
        for fail_after_replace in (False, True):
            persistence = terminal.STATE.persistence
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': str(fail_after_replace)}
            prepared = self.prepare(payload)
            original = persistence.atomic_write_bytes
            def fail(path, data):
                if fail_after_replace:
                    original(path, data)
                raise OSError('injected persistence failure')
            with mock.patch.object(persistence, 'atomic_write_bytes', side_effect=fail):
                self.assertEqual(self.commit(payload, prepared)[0], 503)
            self.assertEqual(self.commit(payload, prepared)[0], 503)
            self.assertEqual(self.request('/terminal/events')[0], 503)
            self.restart()
            if fail_after_replace:
                self.assertEqual(self.commit(payload, prepared)[0], 409)
            else:
                self.assertEqual(self.request('/terminal/events')[2]['event_count'], 0)
                self.assertEqual(self.commit(payload, prepared)[0], 200)


class DurableTerminalProcessTests(unittest.TestCase):
    def test_witness_seed_policy_substitution_is_refused_before_state_creation(self):
        from tools.qikvrt_firefox_windows_witness import initialize_seeded_terminal
        policy = json.loads((ROOT / 'policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            contract = dict(policy['windows_acceptance'], seed_sha256='0' * 64)
            with self.assertRaisesRegex(RuntimeError, 'WITNESS_CANONICAL_SEED_BINDING_MISMATCH'):
                initialize_seeded_terminal(terminal, contract, output)
            self.assertFalse((output / 'terminal-state').exists())

    def test_both_witnesses_bind_canonical_seed_and_real_persistent_root(self):
        from tools.qikvrt_firefox_windows_witness import initialize_seeded_terminal
        policy = json.loads((ROOT / 'policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json').read_text())
        for profile in ('linux_ring_acceptance', 'windows_acceptance'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                terminal.STATE.close()
                seed, root = initialize_seeded_terminal(terminal, policy[profile], Path(directory))
                try:
                    self.assertEqual(seed.read_bytes(), (ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin').read_bytes())
                    self.assertEqual(terminal.STATE.seed_binding['bytes'], 400)
                    self.assertEqual(terminal.STATE.persistence_scope, 'FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE')
                    self.assertEqual(terminal.STATE.store, root / '.qikvrt/api/terminal.json')
                finally:
                    terminal.STATE.close()

    def test_real_cli_negative_starts_preserve_durable_bytes(self):
        from tools.qikvrt_firefox_windows_witness import durable_restart_controls, durable_state_rejection_controls
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin'
            result = durable_restart_controls(terminal, root, seed)
            store = root / '.qikvrt/api/terminal.json'
            before = store.read_bytes()
            rejected = durable_state_rejection_controls(terminal, root, seed, store)
            self.assertEqual(store.read_bytes(), before)
            self.assertEqual(len(rejected['controls']), 10)
            self.assertTrue(all(control['startup_refused'] for control in rejected['controls'].values()))
            self.assertEqual(result['persistent_state_sha256_before'], rejected['valid_state_sha256'])

    def test_real_transport_reset_truncated_readback_and_concurrent_retries(self):
        from tools.qikvrt_firefox_windows_witness import network_loss_controls
        with tempfile.TemporaryDirectory() as directory:
            result = network_loss_controls(terminal, Path(directory),
                ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')
        self.assertTrue(result['network_loss_injected'])
        self.assertTrue(result['server_alive_after_faults'])
        self.assertEqual(result['probe_effects'], 1)
        faults = result['transport_faults']
        self.assertIn(faults[0]['client_error'], ('ConnectionResetError', 'RemoteDisconnected'))
        self.assertEqual(faults[0]['downstream_body_bytes_sent'], 0)
        self.assertEqual([fault['client_error'] for fault in faults[1:]], ['IncompleteRead'] * 2)
        for fault in faults:
            self.assertTrue(fault['network_loss_injected'])
            self.assertFalse(fault['client_complete_response'])
            self.assertEqual(fault['upstream_http_status'], 200)
            self.assertEqual(fault['persisted_snapshot_sha256_before_cut'], result['persisted_snapshot_sha256'])
        for fault in faults[1:]:
            self.assertGreater(fault['client_partial_bytes'], 0)
            self.assertGreater(fault['client_missing_bytes'], 0)
            self.assertEqual(fault['client_partial_bytes'] + fault['client_missing_bytes'], fault['upstream_body_bytes'])
        self.assertEqual(result['concurrent_retry'],
                         {'clients': 4, 'http_statuses': [409] * 4, 'refusals': 4, 'second_effects': 0})
        self.assertEqual(result['replay_http_status'], 409)
        self.assertEqual(result['restart_replay_http_status'], 409)
        self.assertNotEqual(result['first_process_pid'], result['restarted_process_pid'])
        self.assertTrue(result['persisted_snapshot_unchanged'])
        self.assertEqual(result['event_snapshot_after_fault']['event_count'], 1)
        self.assertEqual(result['event_snapshot_after_fault'], result['event_snapshot_after_retry'])
        self.assertEqual(result['event_snapshot_after_fault'], result['event_snapshot_after_restart'])
        self.assertEqual(result['effect_records_after_fault'], result['effect_records_after_retry'])
        self.assertEqual(result['effect_records_after_fault'], result['effect_records_after_restart'])
        self.assertEqual(len(result['effect_records_after_fault']), 2)
        self.assertEqual(result['replay_second_effects'], 0)
        for flag in ('authority_mirror_live_nodes_tested', 'unbounded_scalability_proved',
                     'predecessor_evidence_transfer', 'personal_release_effect_ack_done', 'private_state_uploaded'):
            self.assertFalse(result[flag])
        exported = json.dumps(result)
        self.assertNotIn('"secret"', exported)
        self.assertNotIn('"commit_token"', exported)

    def test_transport_cut_of_refused_replay_is_not_post_commit_loss_evidence(self):
        from tools.qikvrt_firefox_windows_witness import TerminalProcess, interrupted_http_response
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = TerminalProcess(root, ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')
            try:
                payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'refusal-is-not-lost-commit'}
                status, prepared = first.request('/terminal/prepare', payload, 'v=1, mode=prepare')
                self.assertEqual(status, 200)
                field = commit_field(prepared['commit_token'], prepared['record_hash'])
                self.assertEqual(first.request('/terminal/commit', payload, field)[0], 200)
                snapshot = first.request('/terminal/events')[1]
                store = root / '.qikvrt/api/terminal.json'
                persisted = store.read_bytes()
                with self.assertRaisesRegex(RuntimeError, 'TRANSPORT_PROXY_UPSTREAM_NOT_COMPLETE_200'):
                    interrupted_http_response(first, store, '/terminal/commit', payload, field,
                                              mode='TCP_RST_BEFORE_RESPONSE')
                self.assertIsNone(first.process.poll())
                self.assertEqual(first.request('/terminal/events')[1], snapshot)
                self.assertEqual(store.read_bytes(), persisted)
            finally:
                first.close()

    def test_real_sigkill_restart_and_fresh_record_readback(self):
        from tools.qikvrt_firefox_windows_witness import durable_restart_controls
        with tempfile.TemporaryDirectory() as directory:
            result = durable_restart_controls(terminal, Path(directory),
                ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')
        self.assertTrue(result['actual_process_restart'])
        self.assertNotEqual(result['first_process_pid'], result['restarted_process_pid'])
        self.assertEqual(result['event_snapshot_before'], result['event_snapshot_after'])
        self.assertEqual(result['effect_records_before'], result['effect_records_after'])
        self.assertEqual(result['replay_second_effects'], 0)
        self.assertEqual(result['persistent_state_sha256_before'], result['persistent_state_sha256_after'])
        self.assertEqual(result['termination'], 'WINDOWS_TERMINATE_PROCESS_WITHOUT_SHUTDOWN_HOOK'
                         if sys.platform == 'win32' else 'SIGKILL_WITHOUT_SHUTDOWN_HOOK')
        for flag in ('authority_mirror_live_nodes_tested', 'network_loss_injected', 'unbounded_scalability_proved'):
            self.assertFalse(result[flag])

    def test_crash_after_fsync_before_response_cannot_duplicate_effect(self):
        from tools.qikvrt_firefox_windows_witness import TerminalProcess
        script = '''
import os,sys
sys.path.insert(0,'src')
import qikvrt_effect_ack_http_terminal as terminal
persist=terminal.State.persist
def crash(self):
    persist(self)
    if self.events:
        os._exit(86)
terminal.State.persist=crash
terminal.main()
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin'
            first = TerminalProcess(root, seed, command=[sys.executable, '-B', '-c', script])
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'fsync-before-reply'}
            try:
                status, prepared = first.request('/terminal/prepare', payload, 'v=1, mode=prepare')
                self.assertEqual(status, 200)
                field = commit_field(prepared['commit_token'], prepared['record_hash'])
                with self.assertRaises((OSError, http.client.RemoteDisconnected)):
                    first.request('/terminal/commit', payload, field)
                self.assertEqual(first.process.wait(timeout=15), 86)
            finally:
                first.close()
            second = TerminalProcess(root, seed)
            try:
                status, snapshot = second.request('/terminal/events')
                self.assertEqual(status, 200)
                self.assertEqual(snapshot['event_count'], 1)
                self.assertEqual(snapshot['events'][0]['text'], payload['text'])
                effect = snapshot['events'][0]['effect_record_hash']
                status, record = second.request('/effect-ack/records/' + effect)
                self.assertEqual(status, 200)
                self.assertEqual(record['input_hash'], 'sha256:' + terminal.sha256(terminal.canonical_json(payload)))
                self.assertEqual(second.request('/terminal/commit', payload, field)[0], 409)
                self.assertEqual(second.request('/terminal/events')[1], snapshot)
            finally:
                second.close()


@unittest.skipUnless(sys.platform == 'linux', 'comparable CPU accounting requires Linux process CPU clocks')
class LinuxComparableScaleBenchmarkTests(unittest.TestCase):
    def test_identical_preload_workload_and_clients_survive_every_run_and_replay(self):
        from tools.qikvrt_firefox_windows_witness import comparable_scale_benchmark, digest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'benchmark'
            receipt = comparable_scale_benchmark(terminal, root,
                ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin',
                repetitions=3, workload=4, preload_per_origin=1)
            self.assertEqual(receipt['state'], 'PASS')
            self.assertEqual(len(receipt['measurements']), 9)
            for row in receipt['measurements']:
                self.assertEqual(row['initial_snapshot_sha256'], receipt['initial_snapshot_sha256'])
                self.assertEqual(row['workload_sha256'], receipt['workload_sha256'])
                self.assertEqual((row['requests'], row['parallel_clients']), (4, 4))
                self.assertEqual((row['effects'], row['referenced_records']), (8, 16))
                self.assertEqual(len(set(row['process_ids'])), row['processes'])
                self.assertGreater(row['wall_seconds'], 0)
                self.assertGreater(row['total_cpu_seconds'], 0)
                self.assertEqual(len(row['effect_latency_seconds']), 4)
                self.assertEqual(row['invariants']['replay_refusals'], 8)
                self.assertEqual(row['invariants']['concurrent_replay_statuses'], [409] * 4)
                evidence = root / row['evidence']['path']
                self.assertEqual(digest(evidence), row['evidence']['sha256'])
                detail = json.loads(evidence.read_text())
                self.assertEqual(detail['readback_after'], detail['readback_after_restart_and_replay'])
            self.assertFalse(receipt['unbounded_scalability_proved'])
            self.assertFalse(receipt['private_state_exported'])
            before = (root / 'private-rings/template/node-0/.qikvrt/api/terminal.json').read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'NEW_BENCHMARK_ROOT_REQUIRED'):
                comparable_scale_benchmark(terminal, root, ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')
            self.assertEqual((root / 'private-rings/template/node-0/.qikvrt/api/terminal.json').read_bytes(), before)

    def test_speedup_claim_requires_comparable_repeated_advantage(self):
        from tools.qikvrt_firefox_windows_witness import benchmark_speedup, benchmark_distribution
        self.assertTrue(benchmark_speedup([2.] * 6, [1.] * 6)['speedup_supported'])
        self.assertFalse(benchmark_speedup([2.] * 3, [1.] * 3)['speedup_supported'])
        self.assertFalse(benchmark_speedup([1., 3., 1.], [2., 1., 2.])['speedup_supported'])
        self.assertFalse(benchmark_speedup([1., 1., 1.], [1., 1., 1.])['speedup_supported'])
        with self.assertRaises(ValueError):
            benchmark_speedup([1., 1., 1.], [0., 1., 1.])
        with self.assertRaises(ValueError):
            benchmark_distribution([float('nan')])


@unittest.skipUnless(os.name == 'posix', 'POSIX durable ownership contract')
class LinuxRingScaleConsolidationTests(unittest.TestCase):
    seed = ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin'

    def initialize_origins(self, root):
        for node in ('node-0', 'node-1'):
            state = terminal.State(self.seed, state_root=root / node)
            state.close()

    def test_real_process_scale_and_consolidation_preserve_every_effect_and_token(self):
        from tools.qikvrt_firefox_windows_witness import lossless_scale_consolidation_controls
        with tempfile.TemporaryDirectory() as directory:
            receipt = lossless_scale_consolidation_controls(terminal, Path(directory) / 'ring', self.seed, workload=4)
        self.assertEqual(receipt['process_scale'], [1, 2, 4])
        self.assertEqual(len(set(receipt['source_process_ids'])), 4)
        self.assertEqual(receipt['consolidated_process_count'], 1)
        self.assertNotIn(receipt['consolidated_process_id'], receipt['source_process_ids'])
        self.assertEqual(receipt['confirmed_events_before'], 13)
        self.assertEqual(receipt['confirmed_events_after_new_work'], 17)
        self.assertEqual(receipt['readback_before'], receipt['readback_after'])
        self.assertEqual(receipt['retained_preparations_committed_once'], 4)
        self.assertEqual(receipt['concurrent_retry_statuses'], [409] * 8)
        self.assertEqual(receipt['external_service_requests'], 0)
        self.assertEqual(receipt['replay_second_effects'], 0)
        self.assertFalse(receipt['comparative_speedup_proved'])

    def test_missing_corrupt_and_symlinked_origin_block_without_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'ring'
            self.initialize_origins(root)
            store = root / 'node-1/.qikvrt/api/terminal.json'
            original = store.read_bytes()
            for raw in (b'', original[:-1], b'{'):
                with self.subTest(raw=raw[:10]):
                    store.write_bytes(raw)
                    with self.assertRaises(terminal.PersistenceError):
                        terminal.load_ring_states(root, self.seed, expected_nodes=2)
                    self.assertEqual(store.read_bytes(), raw)
                    # The earlier origin's ownership was released on failure.
                    state = terminal.State(self.seed, state_root=root / 'node-0')
                    state.close()
            store.unlink()
            with self.assertRaises(terminal.PersistenceError):
                terminal.load_ring_states(root, self.seed, expected_nodes=2)
            self.assertFalse(store.exists())
            store.write_bytes(original)
            saved = (root / 'node-0/.qikvrt/api/terminal.json').read_bytes()
            store.write_bytes(saved)
            with self.assertRaises(terminal.PersistenceError):
                terminal.load_ring_states(root, self.seed, expected_nodes=2)
            store.write_bytes(original)
            (root / 'node-1').rename(Path(directory) / 'saved-origin')
            with self.assertRaises(terminal.PersistenceError):
                terminal.load_ring_states(root, self.seed, expected_nodes=2)
            (root / 'node-1').symlink_to(root / 'node-0', target_is_directory=True)
            with self.assertRaises(terminal.PersistenceError):
                terminal.load_ring_states(root, self.seed, expected_nodes=2)

    def test_live_origin_owner_and_wrong_seed_block_consolidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'ring'
            self.initialize_origins(root)
            state = terminal.State(self.seed, state_root=root / 'node-1')
            try:
                with self.assertRaises(terminal.PersistenceError):
                    terminal.load_ring_states(root, self.seed, expected_nodes=2)
            finally:
                state.close()
            with self.assertRaises(terminal.PersistenceError):
                terminal.load_ring_states(root, None, expected_nodes=2)
            bad_seed = Path(directory) / 'seed.bin'
            bad_seed.write_bytes(self.seed.read_bytes()[:-1])
            before = [(root / node / '.qikvrt/api/terminal.json').read_bytes() for node in ('node-0', 'node-1')]
            with self.assertRaises(terminal.PersistenceError):
                terminal.load_ring_states(root, bad_seed, expected_nodes=2)
            self.assertEqual(before, [(root / node / '.qikvrt/api/terminal.json').read_bytes() for node in ('node-0', 'node-1')])

    def test_aggregate_readback_fails_closed_if_one_origin_is_poisoned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'ring'
            self.initialize_origins(root)
            states = terminal.load_ring_states(root, self.seed, expected_nodes=2)
            server = ThreadingHTTPServer(('127.0.0.1', 0), terminal.RingHandler)
            server.ring_states = states
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                states['node-1'].persistence_failed = True
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen('http://127.0.0.1:' + str(server.server_port) + '/terminal/events', timeout=5)
                self.assertEqual(error.exception.code, 503)
                with error.exception as response:
                    self.assertNotIn('events', json.load(response))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                for state in states.values():
                    state.close()


if __name__ == "__main__":
    unittest.main()
