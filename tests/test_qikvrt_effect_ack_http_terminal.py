from __future__ import annotations

import base64
import importlib.util
import json
import sys
import subprocess
import threading
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
import urllib.error
import urllib.request
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
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'effect-ack-state.json'
            terminal.STATE = terminal.State(self.seed, state_path)
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'durable-restart'}
            prepared = self.prepare(payload)
            status, _, committed = self.request(
                '/terminal/commit', method='POST', body=payload,
                headers=self.commit_headers(prepared))
            self.assertEqual(status, 200)
            record_url = prepared['record_url']
            before = self.request('/terminal/events')[2]
            self.assertEqual(before['persistence_scope'], 'DURABLE_ATOMIC_FILE')
            self.assertTrue(state_path.is_file())

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
            terminal.STATE = terminal.State(self.seed, state_path)
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'tamper-check'}
            prepared = self.prepare(payload)
            self.assertEqual(self.request(
                '/terminal/commit', method='POST', body=payload,
                headers=self.commit_headers(prepared))[0], 200)
            value = json.loads(state_path.read_text())
            value['events'][0]['text'] = 'tampered'
            state_path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'PERSISTENT_STATE_BINDING_MISMATCH'):
                terminal.State(self.seed, state_path)


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


if __name__ == "__main__":
    unittest.main()
