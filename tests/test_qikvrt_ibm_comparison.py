# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Protocol and negative controls only; no actual IBM inference or benefit claim."""
from __future__ import annotations

import copy
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from src import qikvrt_personal_assistant as p
from tools import qikvrt_browser_assistant_ab as ab

MODEL = "ibm-granite/granite-4.2-3b"
REV = "be9e7d995f2a6be22def5dd815f9f2bae98c8b6e"
LOCAL = {"endpoint": "http://127.0.0.1:8000", "model_revision": REV}
CLOUD = {"endpoint": "https://eu-de.ml.cloud.ibm.com", "project_id": "test-project", "api_version": "2026-03-05"}
KEY = "test-IBM-secret-" + "z" * 32
TOKEN = "test-local-pairing-" + "x" * 32
SOURCE = [{"id": "a", "revision": "1", "text": "Public synthetic fixture; no oracle."}]


def request():
    return {"model": MODEL, "messages": [{"role": "system", "content": p.INSTRUCTIONS},
            {"role": "user", "content": "Use the supplied public source."}],
            "temperature": 1.0, "top_p": 0.95, "max_tokens": 8192}


def response(cloud=False):
    return {"id": "chat-test-one", "model_id" if cloud else "model": MODEL,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": "Unverified technical test draft."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


class IBMTransportTests(unittest.TestCase):
    def test_actual_http_roundtrip_is_protocol_only_not_ibm_inference(self):
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                raw = json.dumps(response()).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        try:
            t = p.IBMChatTransport("", MODEL, "granite_local", dict(LOCAL, endpoint=f"http://127.0.0.1:{server.server_port}"))
            value, receipt = t.post("/responses", request())
            self.assertEqual(receipt["evidence_class"], "LOCAL_HTTP_MODEL_RESPONSE")
            self.assertEqual(receipt["http_status"], 200)
            self.assertEqual(seen, [("/v1/chat/completions", request())])
            self.assertFalse(receipt["model_revision_attested"])
        finally:
            server.shutdown(); server.server_close(); worker.join(timeout=3)

    def test_http_error_is_redacted_and_never_retried(self):
        t = p.IBMChatTransport(KEY, MODEL, "watsonx", CLOUD)
        with patch.object(t.opener, "open", side_effect=HTTPError(CLOUD["endpoint"], 401, KEY, {}, None)) as call:
            with self.assertRaisesRegex(p.CapabilityBlock, "PROVIDER_HTTP_401_NO_RETRY") as error:
                t.post("/responses", request())
            self.assertNotIn(KEY, str(error.exception))
            self.assertEqual(call.call_count, 1)
        with self.assertRaisesRegex(p.CapabilityBlock, "REDIRECT"):
            p.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid")

    def test_local_uses_exact_loopback_and_never_follows_proxy(self):
        t = p.IBMChatTransport("", MODEL, "granite_local", LOCAL)
        with patch.object(t, "_send", return_value=(response(), {"evidence_class": "TECHNICAL_TEST_DOUBLE"})) as send:
            value, receipt = t.post("/responses", request())
        req = send.call_args.args[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:8000/v1/chat/completions")
        self.assertIsNone(req.get_header("Authorization"))
        self.assertEqual(value["model"], MODEL)
        self.assertFalse(receipt["model_revision_attested"])

    def test_cloud_maps_project_version_and_bearer_without_key_exchange(self):
        t = p.IBMChatTransport(KEY, MODEL, "watsonx", CLOUD)
        with patch.object(t, "_send", return_value=(response(True), {"evidence_class": "TECHNICAL_TEST_DOUBLE"})) as send:
            t.post("/responses", request())
        req = send.call_args.args[0]; body = json.loads(req.data)
        self.assertEqual(req.full_url, CLOUD["endpoint"] + "/ml/v1/text/chat?version=2026-03-05")
        self.assertEqual(body["model_id"], MODEL)
        self.assertEqual(body["project_id"], CLOUD["project_id"])
        self.assertNotIn("model", body)
        self.assertNotIn(KEY.encode(), req.data)
        self.assertEqual(req.get_header("Authorization"), "Bearer " + KEY)

    def test_unbound_origins_and_revisions_are_rejected(self):
        for endpoint in ["http://localhost:8000", "http://127.0.0.1:80", "http://127.0.0.1:8000/", "http://10.0.0.1:8000", "http://127.0.0.1:8000?x=1", "http://user@127.0.0.1:8000"]:
            with self.subTest(endpoint=endpoint), self.assertRaises(p.CapabilityBlock):
                p.IBMChatTransport("", MODEL, "granite_local", dict(LOCAL, endpoint=endpoint))
        with self.assertRaises(p.CapabilityBlock):
            p.IBMChatTransport("", MODEL, "granite_local", dict(LOCAL, model_revision="main"))

    def test_cloud_origin_and_credentials_fail_closed(self):
        for endpoint in ["https://eu-de.ml.cloud.ibm.com.evil.example", "http://eu-de.ml.cloud.ibm.com", "https://eu-de.ml.cloud.ibm.com:443", "https://eu-de.ml.cloud.ibm.com/path"]:
            with self.subTest(endpoint=endpoint), self.assertRaises(p.CapabilityBlock):
                p.IBMChatTransport(KEY, MODEL, "watsonx", dict(CLOUD, endpoint=endpoint))
        with self.assertRaises(p.CapabilityBlock):
            p.IBMChatTransport("", MODEL, "watsonx", CLOUD)

    def test_unexpected_request_and_secret_are_not_sent(self):
        t = p.IBMChatTransport(KEY, MODEL, "watsonx", CLOUD)
        for req in [dict(request(), tools=[]), dict(request(), temperature=0),
                    dict(request(), model="different"), dict(request(), messages=[{"role": "user", "content": KEY}])]:
            with self.subTest(req_keys=list(req)), patch.object(t, "_send") as send:
                with self.assertRaises(p.CapabilityBlock):
                    t.post("/responses", req)
                send.assert_not_called()

    def test_incomplete_mismatched_and_tool_outputs_never_become_completed(self):
        values = []
        for finish in ["length", "tool_calls", "content_filter", None]:
            v = response(); v["choices"][0]["finish_reason"] = finish; values.append(v)
        v = response(); v["model"] = "substituted"; values.append(v)
        v = response(); v["choices"][0]["message"]["tool_calls"] = [{"name": "delete"}]; values.append(v)
        v = response(); v["choices"][0]["message"]["content"] = ""; values.append(v)
        t = p.IBMChatTransport("", MODEL, "granite_local", LOCAL)
        for value in values:
            with self.subTest(value=value), patch.object(t, "_send", return_value=(value, {})), self.assertRaises(p.CapabilityBlock):
                t.post("/responses", request())


class Double:
    def __init__(self):
        self.requests = []; self.fail = False

    def post(self, route, payload):
        self.requests.append((route, copy.deepcopy(payload)))
        if self.fail:
            raise p.CapabilityBlock("TEST_UNRESOLVED_NO_RETRY")
        return {"id": "test-response-" + str(len(self.requests)), "model": MODEL, "status": "completed",
            "output": [{"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": "Synthetic protocol draft."}]}]}, {"evidence_class": "TECHNICAL_TEST_DOUBLE"}


class IBMRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name) / "private"
        self.double = Double(); self.runtime = self.open()

    def open(self, config=LOCAL):
        return p.PersonalRuntime(self.root, MODEL, "", TOKEN, provider="granite_local", provider_config=config, transport=self.double)

    def tearDown(self):
        if self.runtime:
            self.runtime.close()
        self.tmp.cleanup()

    def test_same_model_settings_and_full_history_in_both_arms(self):
        created = [self.runtime.create(mode, "Read sources.", SOURCE) for mode in ["baseline", "qikvrt"]]
        self.assertEqual(self.double.requests[0], self.double.requests[1])
        for result in created:
            self.runtime.turn(result["session"]["id"], "Continue.")
            messages = self.double.requests[-1][1]["messages"]
            self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
            self.assertEqual(messages[2]["content"], "Synthetic protocol draft.")

    def test_resume_addition_is_source_bound_and_never_contains_oracle(self):
        result = self.runtime.create("qikvrt", "Read sources.", SOURCE)
        resumed = self.runtime.turn(result["session"]["id"], "Continue.", resume=True)
        context = json.loads(resumed["automatic_context"])
        self.assertEqual(context["checkpoint"]["sources"], {"a": p.digest(p.canonical(SOURCE[0]))})
        self.assertNotIn("oracle", context)
        self.assertFalse(resumed["product_claim_allowed"])

    def test_both_sessions_survive_reopen_without_auth_or_product_promotion(self):
        original = [self.runtime.create(mode, "Read sources.", SOURCE) for mode in ["baseline", "qikvrt"]]
        self.runtime.close(); self.runtime = self.open()
        for result in original:
            self.assertEqual(self.runtime.load(result["session"]["id"]), result["session"])
        self.assertFalse(self.runtime.capabilities()["authenticated_runtime_readback"])
        self.assertFalse(self.runtime.binding["model_revision_attested"])

    def test_ambiguous_response_remains_pending_across_reopen(self):
        result = self.runtime.create("qikvrt", "Read sources.", SOURCE)
        self.double.fail = True
        with self.assertRaises(p.CapabilityBlock):
            self.runtime.turn(result["session"]["id"], "Next.")
        count = len(self.double.requests)
        self.runtime.close(); self.runtime = self.open()
        with self.assertRaisesRegex(p.CapabilityBlock, "NO_RETRY"):
            self.runtime.turn(result["session"]["id"], "Next.")
        self.assertEqual(count, len(self.double.requests))

    def test_changed_model_revision_does_not_reuse_old_state(self):
        self.runtime.close(); self.runtime = None
        with self.assertRaisesRegex(p.CapabilityBlock, "MISMATCH"):
            self.open(dict(LOCAL, model_revision="a" * 40))

    def test_real_sigkill_restores_ibm_provider_history_in_both_arms(self):
        if os.name != "posix":
            self.skipTest("Actual SIGKILL witness requires POSIX")
        script = '''
import json, sys, time
from src import qikvrt_personal_assistant as p
from tests.test_qikvrt_ibm_comparison import Double, MODEL, LOCAL, TOKEN, SOURCE
r=p.PersonalRuntime(sys.argv[1], MODEL, "", TOKEN, provider="granite_local", provider_config=LOCAL, transport=Double())
ids=[r.create(m,"Synthetic IBM protocol restart test",SOURCE)["session"]["id"] for m in ["baseline","qikvrt"]]
print(json.dumps(ids),flush=True)
time.sleep(30)
'''
        root = Path(self.tmp.name) / "kill-ibm"
        child = subprocess.Popen([sys.executable, "-B", "-c", script, str(root)], cwd=p.ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ids = json.loads(child.stdout.readline())
            child.kill(); self.assertEqual(child.wait(timeout=5), -signal.SIGKILL)
            restored = p.PersonalRuntime(root, MODEL, "", TOKEN, provider="granite_local", provider_config=LOCAL, transport=Double())
            try:
                self.assertEqual([restored.load(i)["mode"] for i in ids], ["baseline", "qikvrt"])
                self.assertTrue(all(len(restored.load(i)["history"]) == 1 for i in ids))
                self.assertFalse(restored.capabilities()["authenticated_runtime_readback"])
            finally:
                restored.close()
        finally:
            if child.poll() is None:
                child.kill(); child.wait(timeout=5)
            child.stdout.close(); child.stderr.close()


class IBMPlanTests(unittest.TestCase):
    def test_balanced_identical_plans_have_no_fabricated_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = ab.prepare_ibm_comparison(Path(tmp) / "study", repeats=2)
            self.assertEqual(result["planned_trials"], 32)
            self.assertEqual(result["product_trials_executed"], 0)
            self.assertIsNone(result["product_metrics"])
            self.assertIsNone(result["winner"])
            self.assertFalse(result["effect_ack_done"])
            plans = []
            hashes = []
            for study in result["studies"]:
                run = Path(tmp) / "study" / study["id"]
                manifest, _, _ = ab.load_run(run); plans.append(manifest["pairs"])
                self.assertEqual(manifest["study_binding"]["id"], study["id"])
                hashes.append(study["manifest_sha256"])
                for task in ["research-costs", "document-recovery"]:
                    orders = [p["order"] for p in manifest["pairs"] if p["task_id"] == task]
                    self.assertEqual(sorted(orders), ["AB", "BA"])
                self.assertEqual(list((run / "events").iterdir()), [])
            self.assertTrue(all(plan == plans[0] for plan in plans))
            self.assertEqual(len(set(hashes)), 4)

    def test_invalid_counts_do_not_create_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "study"
            with self.assertRaises(ab.InvalidRun):
                ab.prepare_ibm_comparison(out, repeats=3)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
