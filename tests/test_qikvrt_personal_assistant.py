# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Technical doubles only: persistence, authenticated routing and negative controls.

These are not product trials, actual model responses, or customer observations.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src import qikvrt_effect_ack_http_terminal as terminal
from src import qikvrt_personal_assistant as personal


TOKEN = "test-local-client-secret-" + "x" * 32
KEY = "test-provider-secret-" + "y" * 32
SOURCES = [{"id": "source-a", "revision": "1", "text": "A supplied source; no evaluation oracle."}]


class TransportDouble:
    def __init__(self):
        self.requests = []
        self.fail = False

    def post(self, path, payload):
        self.requests.append((path, payload))
        if self.fail:
            raise personal.CapabilityBlock("TEST_AMBIGUOUS_RESULT")
        receipt = {"evidence_class": "TECHNICAL_TEST_DOUBLE", "request_id": "fake-request"}
        if path == "/conversations":
            return {"id": "conv_test_" + str(len(self.requests))}, receipt
        return {"id": "resp_test_" + str(len(self.requests)), "model": "explicit-test-model",
                "status": "completed", "output": [{"type": "message", "role": "assistant",
                "content": [{"type": "output_text", "text": "Unverified technical draft."}]}]}, receipt


class PersonalAssistantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "private-state"
        self.transport = TransportDouble()
        self.runtime = personal.PersonalRuntime(self.root, "explicit-test-model", KEY, TOKEN, transport=self.transport)

    def tearDown(self):
        if self.runtime:
            self.runtime.close()
        self.tmp.cleanup()

    def create(self, mode="qikvrt"):
        return self.runtime.create(mode, "Research supplied sources and produce a documentation draft.", SOURCES)

    def test_normal_baseline_has_identical_provider_settings_and_full_retention(self):
        baseline, enhanced = self.create("baseline"), self.create("qikvrt")
        a, b = [payload for path, payload in self.transport.requests if path == "/responses"]
        self.assertEqual({k: v for k, v in a.items() if k != "conversation"}, {k: v for k, v in b.items() if k != "conversation"})
        self.assertNotEqual(a["conversation"], b["conversation"])
        for result in [baseline, enhanced]:
            self.assertEqual(len(result["session"]["history"]), 1)
            self.assertEqual(result["binding"]["parameters"], {"store": True})
        self.assertIsNone(baseline["session"]["checkpoint"])
        self.assertIsNotNone(enhanced["session"]["checkpoint"])
        continued = self.runtime.turn(baseline["session"]["id"], "Continue.", resume=True)
        self.assertIsNone(continued["automatic_context"])
        self.assertEqual(self.transport.requests[-1][1]["conversation"], a["conversation"])
        self.assertEqual(len(continued["session"]["history"]), 2)

    def test_restart_restores_both_modes_without_history_or_draft_loss(self):
        original = [self.create(mode) for mode in ["baseline", "qikvrt"]]
        self.runtime.close()
        self.runtime = personal.PersonalRuntime(self.root, "explicit-test-model", KEY, TOKEN, transport=self.transport)
        for result in original:
            restored = self.runtime.readback(self.runtime.load(result["session"]["id"]))
            self.assertEqual(restored, {k: v for k, v in result.items() if k != "automatic_context"})
        self.assertFalse(self.runtime.capabilities()["authenticated_runtime_readback"])

    def test_checkpoint_resume_uses_actual_output_and_source_hashes_without_oracle(self):
        result = self.create()
        resumed = self.runtime.turn(result["session"]["id"], "Continue.", resume=True)
        context = json.loads(resumed["automatic_context"])
        self.assertEqual(context["checkpoint"]["draft"], result["session"]["history"][-1]["text"])
        self.assertEqual(context["checkpoint"]["sources"]["source-a"], personal.digest(personal.canonical(SOURCES[0])))
        self.assertNotIn("oracle", context)
        self.assertFalse(context["checkpoint"]["independent_acceptance"])
        self.assertFalse(resumed["ordinary_release"])

    def test_corrupt_checkpoint_cannot_be_used_as_resume_evidence(self):
        result = self.create()
        session = result["session"]
        session["checkpoint"]["history_sha256"] = "0" * 64
        self.runtime.save(session)
        n = len(self.transport.requests)
        with self.assertRaisesRegex(personal.CapabilityBlock, "CHECKPOINT_HISTORY_BINDING_INVALID"):
            self.runtime.turn(session["id"], "Continue.", resume=True)
        self.assertEqual(n, len(self.transport.requests))

    def test_changed_draft_cannot_borrow_valid_history_hash(self):
        result = self.create()
        session = result["session"]
        session["checkpoint"]["draft"] = "Invented replacement completion"
        self.runtime.save(session)
        with self.assertRaisesRegex(personal.CapabilityBlock, "CHECKPOINT_HISTORY_BINDING_INVALID"):
            self.runtime.turn(session["id"], "Continue.", resume=True)

    def test_durable_pending_prevents_blind_retry_after_restart(self):
        result = self.create("baseline")
        self.transport.fail = True
        with self.assertRaisesRegex(personal.CapabilityBlock, "TEST_AMBIGUOUS_RESULT"):
            self.runtime.turn(result["session"]["id"], "Next step.")
        self.runtime.close()
        self.runtime = personal.PersonalRuntime(self.root, "explicit-test-model", KEY, TOKEN, transport=self.transport)
        session = self.runtime.load(result["session"]["id"])
        self.assertEqual(session["status"], "TURN_PENDING")
        self.assertEqual(len(session["history"]), 1)
        n = len(self.transport.requests)
        with self.assertRaisesRegex(personal.CapabilityBlock, "NO_RETRY"):
            self.runtime.turn(session["id"], "Next step.")
        self.assertEqual(n, len(self.transport.requests))

    def test_no_credential_persistence_or_double_attestation(self):
        result = self.create()
        for secret in [TOKEN, KEY]:
            with self.assertRaisesRegex(personal.CapabilityBlock, "CONTAINS_RUNTIME_SECRET"):
                self.runtime.turn(result["session"]["id"], secret)
        for file in self.root.iterdir():
            data = file.read_bytes()
            self.assertNotIn(KEY.encode(), data)
            self.assertNotIn(TOKEN.encode(), data)
        state = self.runtime.capabilities()
        self.assertTrue(state["local_client_authentication_required"])
        self.assertNotIn("local_client_authenticated", state)
        self.assertFalse(state["authenticated_runtime_readback"])
        self.assertFalse(state["firefox_execution_observed"])
        self.assertIsNone(state["product_metrics"])
        self.assertEqual(state["product_trials_executed"], 0)

    def test_model_change_and_competing_writer_fail_closed(self):
        with self.assertRaises(OSError):
            personal.PersonalRuntime(self.root, "explicit-test-model", KEY, TOKEN, transport=self.transport)
        self.runtime.close(); self.runtime = None
        with self.assertRaisesRegex(personal.CapabilityBlock, "MISMATCH"):
            personal.PersonalRuntime(self.root, "another-model", KEY, TOKEN, transport=self.transport)

    def test_invalid_source_and_repository_state_directory_are_rejected(self):
        with self.assertRaisesRegex(personal.CapabilityBlock, "SOURCES|SOURCE"):
            self.runtime.create("baseline", "Task", [{"id": "a", "text": "data", "oracle": "answers"}])
        with self.assertRaisesRegex(personal.CapabilityBlock, "OUTSIDE_REPOSITORY"):
            personal.PersonalRuntime(personal.ROOT / ".qikvrt/runtime/personal", "explicit-test-model", KEY, TOKEN, transport=self.transport)
        with self.assertRaisesRegex(personal.CapabilityBlock, "OUTSIDE_REPOSITORY"):
            personal.PersonalRuntime(Path("/tmp/..") / str(personal.ROOT).lstrip("/") / "private", "explicit-test-model", KEY, TOKEN, transport=self.transport)
        with self.assertRaises(personal.CapabilityBlock):
            self.runtime.load("../../secret")

    def test_provider_is_fixed_https_no_redirect_or_automatic_retry(self):
        transport = personal.OpenAITransport(KEY)
        with self.assertRaisesRegex(personal.CapabilityBlock, "NOT_ALLOWED"):
            transport.post("/admin", {})
        with self.assertRaisesRegex(personal.CapabilityBlock, "REDIRECT"):
            personal.NoRedirect().redirect_request(None, None, 302, "", {}, "https://foreign.invalid")
        with patch.object(transport.opener, "open", side_effect=HTTPError("https://api.openai.com", 401, KEY, {}, None)) as call:
            with self.assertRaises(personal.CapabilityBlock) as result:
                transport.post("/responses", {"model": "explicit-test-model"})
            self.assertNotIn(KEY, str(result.exception))
            self.assertEqual(call.call_count, 1)
            request = call.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertEqual(request.get_header("Authorization"), "Bearer " + KEY)

    def test_existing_terminal_and_personal_authenticated_http_paths_share_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), personal.personal_handler(terminal.Handler, self.runtime))
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        def query(path, body=None, token=TOKEN, origin=None):
            headers = {"Authorization": "Bearer " + token}
            if body is not None: headers["Content-Type"] = "application/json"
            if origin: headers["Origin"] = origin
            with urlopen(Request(base + path, data=personal.canonical(body) if body is not None else None, headers=headers), timeout=3) as response:
                return json.load(response)
        try:
            with urlopen(base + "/personal/", timeout=3) as response:
                self.assertIn(b"ui.js", response.read())
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            self.assertIn("versions", query("/.well-known/effect-ack"))
            with self.assertRaises(HTTPError): query("/personal/capabilities", token="wrong")
            with self.assertRaises(HTTPError): query("/personal/capabilities", origin="https://github.com")
            with self.assertRaises(HTTPError): query("/personal/create", {"mode": "baseline", "task": "Task", "sources": SOURCES, "confirmed": False})
            self.assertEqual(self.transport.requests, [])
            result = query("/personal/create", {"mode": "baseline", "task": "Task", "sources": SOURCES, "confirmed": True}, origin=base)
            readback = query("/personal/session/" + result["session"]["id"])
            self.assertEqual(result["session_sha256"], readback["session_sha256"])
            self.assertEqual(query("/personal/sessions")["sessions"][0]["turns"], 1)
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=3)

    def test_actual_sigkill_after_checkpoint_restores_baseline_and_qikvrt(self):
        if os.name != "posix": self.skipTest("SIGKILL witness is POSIX-specific")
        script = r'''
import json,sys,time
from src import qikvrt_personal_assistant as p
from tests.test_qikvrt_personal_assistant import TransportDouble,TOKEN,KEY,SOURCES
r=p.PersonalRuntime(sys.argv[1],"explicit-test-model",KEY,TOKEN,transport=TransportDouble())
ids=[r.create(m,"Technical restart task",SOURCES)["session"]["id"] for m in ["baseline","qikvrt"]]
print(json.dumps(ids),flush=True)
time.sleep(30)
'''
        root = Path(self.tmp.name) / "kill-state"
        process = subprocess.Popen([sys.executable, "-B", "-c", script, str(root)], cwd=personal.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ids = json.loads(process.stdout.readline())
            process.kill(); process.wait(timeout=5)
            restored = personal.PersonalRuntime(root, "explicit-test-model", KEY, TOKEN, transport=TransportDouble())
            try:
                self.assertEqual([restored.load(i)["mode"] for i in ids], ["baseline", "qikvrt"])
                self.assertTrue(all(restored.load(i)["status"] == "READY" and len(restored.load(i)["history"]) == 1 for i in ids))
                self.assertFalse(restored.capabilities()["authenticated_runtime_readback"])
            finally: restored.close()
        finally:
            if process.poll() is None: process.kill(); process.wait(timeout=5)
            process.stdout.close(); process.stderr.close()

    def test_terminal_cli_refuses_missing_credentials_without_network(self):
        env = dict(os.environ)
        env.pop("OPENAI_API_KEY", None); env.pop("QIKVRT_PERSONAL_LOCAL_TOKEN", None)
        result = subprocess.run([sys.executable, "-B", "src/qikvrt_effect_ack_http_terminal.py", "--personal-state-dir", str(Path(self.tmp.name) / "missing"), "--personal-model", "explicit-test-model"], cwd=personal.ROOT, env=env, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LOCAL_PAIRING_SECRET_REQUIRED", result.stderr)
        self.assertFalse((Path(self.tmp.name) / "missing").exists())


if __name__ == "__main__":
    unittest.main()
