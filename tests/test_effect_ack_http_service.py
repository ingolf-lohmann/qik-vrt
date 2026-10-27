#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Real local HTTP/SQLite tests of the original Runtime and OwnerREST adapter.

Temporary Git fixtures are isolated local subjects, never VPS acceptance.
"""
import base64
import copy
import hmac
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
import qikvrt_effect_ack_wire as wire
import qikvrt_effect_ack_http_service as service
import qikvrt_effect_ack_http_terminal as terminal
import qikvrt_temdd_event_ledger as native
spec = importlib.util.spec_from_file_location("eap_self_host", ROOT / "tools/qikvrt_self_host.py")
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"; self.root.mkdir()
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()
        git("init", "-q"); git("config", "user.name", "Local EAP fixture"); git("config", "user.email", "fixture@example.invalid")
        git("config", "commit.gpgsign", "false")
        (self.root / "SOURCE.txt").write_text("Isolated original Runtime test subject.\n")
        git("add", "SOURCE.txt"); git("commit", "-qm", "Local fixture")
        self.state = Path(self.temp.name) / "state"; self.state.mkdir(mode=0o700)
        self.runtime = native.Runtime(self.root, self.state, "ingolf-lohmann/qik-vrt", 617)
        self.rest = host.OwnerREST(self.runtime, terminal, self.state)
        self.api = service.Service(self.rest)
        self.grant = {"principal": "fixture-owner", "token": "test-private-capability-" + "a" * 40,
                      "permissions": ["prepare", "commit", "readback"]}
        self.value = {"schema": "qikvrt_owner_rest_input_v1", "request_id": "local-eap-one", "subject": self.runtime.subject,
            "input": {"schema": "qikvrt_terminal_input_v1", "text": "Bounded native test input", "audio": None, "video": None}}
        self.addCleanup(lambda: self.runtime.ledger.close())

    def binding(self, prepared):
        return {"v": 1, "mode": "commit", "token": prepared["commit_token"], "hash": prepared["record"]["protocol_hash"][7:]}

    def inputs(self):
        return [e for e in self.runtime.ledger.replay(0) if e.get("payload", {}).get("adapter") == "QIKVRT_OWNER_REST_TERMINAL_V1"]

    def test_prepare_records_classification_but_not_protected_input(self):
        prepared = self.api.prepare(self.grant, self.value)
        self.assertEqual(prepared["state"], "EFFECT_ACK_DONE")
        self.assertFalse(prepared["ordinary_release"])
        self.assertEqual(self.inputs(), [])
        self.assertEqual(self.runtime.ledger.replay(0)[0]["kind"], "CLASSIFY")
        self.assertNotIn(self.grant["token"], json.dumps(self.runtime.ledger.replay(0)))
        context = self.api.record(self.grant, prepared["record"]["protocol_hash"][7:], True)
        self.assertEqual(context["latest_hash"], prepared["record"]["protocol_hash"])
        wire.verify_release(context["chain"], authenticated=True, latest_hash=context["latest_hash"],
            policy=service.POLICY, required_evidence=self.api._evidence(self.grant), observed_evidence=context["evidence"])

    def test_commit_independent_readback_and_replay_without_second_effect(self):
        p = self.api.prepare(self.grant, self.value)
        first = self.api.commit(self.grant, self.value, self.binding(p))
        replay = self.api.commit(self.grant, self.value, self.binding(p))
        self.assertTrue(first["independent_readback_verified"])
        self.assertFalse(first["native_receipt"]["replayed"])
        self.assertTrue(replay["native_receipt"]["replayed"])
        self.assertEqual(first["native_receipt"]["durable_readback"], replay["native_receipt"]["durable_readback"])
        self.assertEqual(len(self.inputs()), 1)
        self.assertFalse(first["effect_ack_done"])

    def test_changed_input_token_record_or_principal_cannot_commit(self):
        p = self.api.prepare(self.grant, self.value)
        for what in ("input", "token", "hash", "principal"):
            value, binding, grant = copy.deepcopy(self.value), self.binding(p), dict(self.grant)
            if what == "input": value["input"]["text"] += " changed"
            if what == "token": binding["token"] = "0" * 64
            if what == "hash": binding["hash"] = "0" * 64
            if what == "principal": grant["principal"] = "another-owner"
            with self.subTest(what=what), self.assertRaises(ValueError):
                self.api.commit(grant, value, binding)
        self.assertEqual(self.inputs(), [])

    def test_missing_permission_continues_without_commit_token(self):
        grant = {**self.grant, "permissions": ["prepare", "readback"]}
        p = self.api.prepare(grant, self.value)
        self.assertEqual(p["state"], "EFFECT_ACK_CONTINUE")
        self.assertNotIn("commit_token", p)
        self.assertEqual(self.inputs(), [])

    def test_expired_prepare_and_native_source_drift_prevent_effect(self):
        p = self.api.prepare(self.grant, self.value)
        with mock.patch.object(host.time, "time", return_value=p["expires_at"] + 1):
            with self.assertRaises(ValueError):
                self.api.commit(self.grant, self.value, self.binding(p))
        (self.root / "SOURCE.txt").write_text("Changed source without admission.\n")
        with self.assertRaises(ValueError):
            self.api.commit(self.grant, self.value, self.binding(p))
        self.assertEqual(self.inputs(), [])

    def test_same_original_store_recovers_after_process_adapter_restart(self):
        p = self.api.prepare(self.grant, self.value)
        first = self.api.commit(self.grant, self.value, self.binding(p))
        epoch = self.runtime.ledger.epoch
        self.runtime.ledger.close()
        self.runtime = native.Runtime(self.root, self.state, "ingolf-lohmann/qik-vrt", 617)
        rest = host.OwnerREST(self.runtime, terminal, self.state)
        restarted = service.Service(rest)
        result = restarted.commit(self.grant, self.value, self.binding(p))
        self.assertEqual(self.runtime.ledger.epoch, epoch)
        self.assertEqual(result["native_receipt"]["durable_readback"], first["native_receipt"]["durable_readback"])
        self.assertEqual(len(self.inputs()), 1)

    def test_corrupt_context_is_not_upgraded_to_done(self):
        p = self.api.prepare(self.grant, self.value)
        key = self.api._key(self.grant["principal"], self.value["request_id"])
        with self.runtime.ledger.db:
            value = self.api._read(key); value["chain"][-1]["origin_checked"] = False
            self.runtime.ledger.db.execute("UPDATE meta SET value=? WHERE key=?", (wire.canonical(value).decode(), key))
        with self.assertRaises(ValueError):
            self.api.commit(self.grant, self.value, self.binding(p))
        self.assertEqual(self.inputs(), [])

    def test_browser_independently_validates_real_native_preparation(self):
        p = self.api.prepare(self.grant, self.value)
        context = self.api.record(self.grant, p["record"]["protocol_hash"][7:], True)
        result = subprocess.run(["node", str(ROOT / "tests/test_devops_client.mjs")], input=json.dumps({
            "context": context, "expected": {"request": self.value, "recordHash": p["record"]["protocol_hash"],
                "principal": self.grant["principal"], "expiresAt": p["expires_at"]}}), text=True,
            capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DEVOPS_CLIENT_PASS", result.stdout)

    def test_real_http_discovery_auth_prepare_commit_and_receipt(self):
        grant = self.grant
        class Guarded(native.make_handler(self.runtime)):
            def owner_guard(handler, permission):
                # Isolated transport credential; production uses the original
                # S1 OwnerHTTP guard unchanged, not this fixture.
                if not hmac.compare_digest(handler.headers.get("Authorization", ""), "Bearer " + grant["token"]):
                    handler._hold("AUTHENTICATION_REQUIRED", 401); return None
                if handler.headers.get("QIKVRT-Owner") != grant["principal"] or permission not in grant["permissions"]:
                    handler._hold("PRINCIPAL_CAPABILITY_REQUIRED", 403); return None
                return grant
        server = ThreadingHTTPServer(("127.0.0.1", 0), service.make_handler(Guarded, self.rest))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(2)))
        origin = "http://127.0.0.1:" + str(server.server_port)
        def call(path, data=None, headers=None):
            req = urllib.request.Request(origin + path, data=wire.canonical(data) if data is not None else None,
                headers=headers or {}, method="POST" if data is not None else "GET")
            try: response = urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError as error: response = error
            return response.status, dict(response.headers), json.loads(response.read())
        self.assertEqual(call("/api/eap/capabilities")[2], service.CAPABILITIES)
        self.assertEqual(call("/api/eap/state")[2]["subject"], self.runtime.subject)
        headers = {"Authorization": "Bearer " + grant["token"], "QIKVRT-Owner": grant["principal"],
            "Content-Type": "application/json", "Effect-Ack-Request": "v=1, mode=prepare"}
        denied = call(service.ROUTE, self.value, {"Content-Type": "application/json", "Effect-Ack-Request": "v=1, mode=prepare"})
        self.assertEqual(denied[0], 401)
        status, fields, p = call(service.ROUTE, self.value, headers)
        self.assertEqual(status, 200); self.assertIn("state=done", fields["Effect-Ack"])
        self.assertEqual(call(p["record_url"], headers=headers)[2], p["record"])
        self.assertEqual(call("/api/owner/commit", self.value, headers)[0], 405)
        raw_hash = bytes.fromhex(p["record"]["protocol_hash"][7:])
        headers["Effect-Ack-Request"] = "v=1, mode=commit, token=" + terminal.sf_bytes(p["commit_token"].encode()) + ", hash=" + terminal.sf_bytes(raw_hash)
        status, _, result = call(service.ROUTE, self.value, headers)
        self.assertEqual(status, 200)
        self.assertTrue(result["independent_readback_verified"])
        receipt = call("/api/eap/receipts/" + self.value["request_id"], headers=headers)[2]
        self.assertEqual(receipt["durable_readback"], result["native_receipt"]["durable_readback"])
        self.assertEqual(len(self.inputs()), 1)


if __name__ == "__main__":
    unittest.main()
