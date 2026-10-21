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
            expected = dict(request(), chat_template_kwargs={"enable_thinking": True,
                "low_effort": False, "truncate_history_thinking": True})
            self.assertEqual(seen, [("/v1/chat/completions", expected)])
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
        self.assertEqual(req.full_url, CLOUD["endpoint"] + "/ml/v1/chat/completions?version=2026-03-05")
        self.assertEqual(body["model_id"], MODEL)
        self.assertEqual(body["project_id"], CLOUD["project_id"])
        self.assertNotIn("model", body)
        self.assertNotIn("chat_template_kwargs", body)
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


@unittest.skipUnless(sys.platform.startswith("linux"), "Existing S1 Linux host admission")
class IBMAdmissionTests(unittest.TestCase):
    """Synthetic files exercise rejection gates; never real weights or inference."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name); self.model = self.root / "model"; self.model.mkdir()
        self.executable = self.root / "server"; self.executable.write_bytes(b"technical server fixture")
        self.metadata_path = self.root / "metadata.json"
        self.host_path = self.root / "host.json"
        self.binding_path = self.root / "binding.json"
        self.output = self.root / "admission"
        files = {"config.json": ab.canonical({"model_type": "granite", "torch_dtype": "bfloat16", "max_position_embeddings": 16384}),
            "generation_config.json": b"{}", "chat_template.jinja": b"synthetic template",
            "tokenizer.json": b"{}", "tokenizer_config.json": b"{}",
            "model.safetensors.index.json": ab.canonical({"weight_map": {
                "first": "model-00001-of-00002.safetensors", "second": "model-00002-of-00002.safetensors"}}),
            "model-00001-of-00002.safetensors": b"synthetic shard one",
            "model-00002-of-00002.safetensors": b"synthetic shard two"}
        siblings = []
        for name, raw in files.items():
            path = self.model / name; path.write_bytes(raw)
            observed = ab.ibm_file_binding(path)
            item = {"rfilename": name, "blobId": observed["git_blob_sha1"]}
            if name.endswith(".safetensors"):
                item["lfs"] = {"sha256": observed["sha256"], "size": observed["bytes"]}
            siblings.append(item)
        self.metadata = {"id": MODEL, "sha": REV, "cardData": {"license": "apache-2.0"}, "siblings": siblings}
        self.observed_host = {"machine_id_sha256": "1" * 64, "mount": {"filesystem": "ext4", "mount_point": "/owner-volume"}}
        self.host = dict(self.observed_host, schema="qikvrt-own-host-admission/v1", public_origin="https://raumzeitterminal.de")
        self.binding = {"schema": "qikvrt_ibm_model_admission_binding_v1", "model_repository": MODEL,
            "revision": REV, "quantization": "none", "dtype": "bfloat16", "served_model": MODEL,
            "endpoint": LOCAL["endpoint"], "server": {"name": "fixture", "version": "test-only",
                "image_digest": "sha256:" + "2" * 64, "offline": True, "model_mount_read_only": True,
                "trust_remote_code": False, "max_model_len": 16384, "max_input_tokens": 8192, "executable": str(self.executable),
                "executable_sha256": ab.digest(self.executable.read_bytes())},
            "settings": dict(p.IBMChatTransport("", MODEL, "granite_local", LOCAL).public_binding["parameters"],
                chat_template_kwargs={"enable_thinking": True, "low_effort": False, "truncate_history_thinking": True})}

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        self.metadata_path.write_bytes(ab.canonical(self.metadata))
        self.host_path.write_bytes(ab.canonical(self.host))
        self.binding.update(metadata_sha256=ab.digest(self.metadata_path.read_bytes()),
                            host_admission_sha256=ab.digest(self.host_path.read_bytes()))
        self.binding_path.write_bytes(ab.canonical(self.binding))
        return ab.digest(self.binding_path.read_bytes())

    def admit(self, pin=None):
        pin = self.freeze() if pin is None else pin
        with patch("tools.qikvrt_self_host.own_host_observation", return_value=self.observed_host), \
             patch.object(ab.platform, "system", return_value="Linux"):
            return ab.ibm_model_admission(self.model, self.metadata_path, self.host_path,
                                          self.binding_path, pin, self.output)

    def test_valid_files_produce_only_artifact_receipt_and_never_inference_acceptance(self):
        with patch.object(p.IBMChatTransport, "post", side_effect=AssertionError("no inference")):
            receipt = self.admit()
        self.assertEqual(receipt, ab.read_json(self.output / "MODEL_ADMISSION.json"))
        self.assertTrue(receipt["local_artifact_integrity_verified"])
        for key in ["model_revision_attested", "upstream_metadata_authenticity_attested",
                    "host_can_run_inference_verified", "actual_ibm_inference_executed", "product_claim_allowed"]:
            self.assertIs(receipt[key], False)
        self.assertEqual(receipt["product_trials_executed"], 0)
        self.assertIsNone(receipt["product_metrics"])
        self.assertIsNone(receipt["winner"])
        with self.assertRaisesRegex(ab.InvalidRun, "NEW_PRIVATE_OUTPUT"):
            self.admit()

    def test_tampered_shard_is_rejected_before_output(self):
        (self.model / "model-00001-of-00002.safetensors").write_bytes(b"substituted")
        with self.assertRaisesRegex(ab.InvalidRun, "WEIGHT_HASH"):
            self.admit()
        self.assertFalse(self.output.exists())

    def test_output_only_window_and_unknown_input_budget_are_rejected(self):
        # The predecessor accepted 8192 context + 8192 output, leaving zero input.
        for value in [None, False, 0, -1, 8193]:
            with self.subTest(max_input_tokens=value):
                self.binding["server"]["max_input_tokens"] = value
                with self.assertRaisesRegex(ab.InvalidRun, "CONTEXT_BUDGET"):
                    self.admit()
                self.assertFalse(self.output.exists())
        self.binding["server"].update(max_model_len=8192, max_input_tokens=1)
        with self.assertRaisesRegex(ab.InvalidRun, "CONTEXT_BUDGET"):
            self.admit()

    def test_server_window_cannot_exceed_the_bound_model_limit(self):
        self.binding["server"]["max_model_len"] = 32768
        with self.assertRaisesRegex(ab.InvalidRun, "CONTEXT_BUDGET"):
            self.admit()
        self.assertFalse(self.output.exists())

    def test_context_budget_receipt_does_not_attest_request_token_counting(self):
        value = self.admit()["context_budget"]
        self.assertEqual(value["max_input_tokens"], 8192)
        self.assertEqual(value["max_output_tokens"], 8192)
        self.assertEqual(value["server_context_tokens_declared"], 16384)
        self.assertIs(value["actual_request_token_counts_verified"], False)

    def test_binding_metadata_and_host_pins_are_independently_checked(self):
        pin = self.freeze()
        self.metadata_path.write_bytes(b"{}")
        with self.assertRaisesRegex(ab.InvalidRun, "INPUT_PIN"):
            self.admit(pin)
        self.freeze()
        with self.assertRaisesRegex(ab.InvalidRun, "BINDING_PIN"):
            self.admit("0" * 64)
        self.metadata["cardData"] = None
        with self.assertRaisesRegex(ab.InvalidRun, "METADATA_OBJECTS"):
            self.admit()

    def test_wrong_revision_license_host_sampling_and_server_are_rejected(self):
        for target, field, value, error in [
            (self.metadata, "sha", "a" * 40, "UPSTREAM_IDENTITY"),
            (self.metadata["cardData"], "license", "unknown", "LICENSE"),
            (self.host, "machine_id_sha256", "a" * 64, "ORIGINAL_HOST"),
            (self.binding, "quantization", "q4", "UNQUANTIZED"),
            (self.binding["settings"], "temperature", 0, "SAMPLING"),
            (self.binding["server"], "image_digest", "latest", "IMMUTABLE"),
            (self.binding["server"], "executable_sha256", "0" * 64, "EXECUTABLE")]:
            old = target[field]; target[field] = value
            try:
                with self.subTest(field=field), self.assertRaisesRegex(ab.InvalidRun, error):
                    self.admit()
                self.assertFalse(self.output.exists())
            finally:
                target[field] = old

    def test_missing_hash_or_index_shard_and_extra_code_are_rejected(self):
        weight = self.metadata["siblings"][-1]; lfs = weight.pop("lfs")
        with self.assertRaisesRegex(ab.InvalidRun, "UPSTREAM_WEIGHT_SHA256"):
            self.admit()
        weight["lfs"] = lfs
        extra = self.model / "unreviewed.py"; extra.write_text("never execute")
        with self.assertRaisesRegex(ab.InvalidRun, "UNBOUND_MODEL_FILES"):
            self.admit()
        extra.unlink()
        (self.model / "model-00001-of-00002.safetensors").unlink()
        with self.assertRaises(FileNotFoundError):
            self.admit()

    def test_symlinks_and_metadata_traversal_are_rejected(self):
        path = self.model / "tokenizer.json"; path.unlink(); path.symlink_to(self.executable)
        with self.assertRaisesRegex(ab.InvalidRun, "SYMLINK"):
            self.admit()
        path.unlink(); os.mkfifo(path)
        with self.assertRaisesRegex(ab.InvalidRun, "REGULAR_FILE"):
            self.admit()
        path.unlink(); path.write_bytes(b"{}")
        self.metadata["siblings"][0]["rfilename"] = "../server"
        with self.assertRaisesRegex(ab.InvalidRun, "UNSAFE_OR_DUPLICATE"):
            self.admit()


class IBMPlanTests(unittest.TestCase):
    def test_single_granite_pilot_is_stratified_and_remains_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pilot"
            result = ab.prepare_ibm_comparison(out, repeats=4, study="granite-continuity")
            self.assertEqual(result["planned_trials"], 16)
            self.assertEqual([s["id"] for s in result["studies"]], ["granite-continuity"])
            run = out / "granite-continuity"
            manifest, contract, tasks = ab.load_run(run)
            for task in tasks:
                for kind in contract["interruption_classes"]:
                    pairs = [p for p in manifest["pairs"] if p["task_id"] == task and p["interruption"] == kind]
                    self.assertEqual(sorted(p["order"] for p in pairs), ["AB", "BA"])
            template = ab.read_json(run / "EXECUTION_BINDING.template.json")
            self.assertEqual(template["manifest_sha256"], ab.digest((run / "manifest.json").read_bytes()))
            self.assertEqual(template["schedule"], manifest["pairs"])
            self.assertTrue(all(v is None for v in template["required_independent_evidence_sha256"].values()))
            self.assertFalse(template["observer"]["implemented_and_admitted"])
            self.assertFalse(template["actual_ibm_inference_executed"])
            self.assertIsNone(template["product_metrics"])
            analysis = ab.analyze(run)
            self.assertEqual(analysis["study_binding"], manifest["study_binding"])
            self.assertTrue(all(t["state"] == "NOT_EXECUTED" for t in analysis["trials"]))

    def test_changed_study_comparison_or_contract_cannot_be_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pilot"
            ab.prepare_ibm_comparison(out, repeats=4, study="granite-continuity")
            run = out / "granite-continuity"; path = run / "manifest.json"
            original = path.read_bytes()
            for key, value in [("id", "unrelated-study"), ("comparison", "changed"), ("contract_sha256", "0" * 64)]:
                with self.subTest(field=key):
                    manifest = json.loads(original); manifest["study_binding"][key] = value
                    path.write_bytes(ab.canonical(manifest))
                    with self.assertRaisesRegex(ab.InvalidRun, "study/contract binding"):
                        ab.analyze(run)
            path.write_bytes(original)
            manifest = json.loads(original)
            for pair in manifest["pairs"]:
                pair["interruption"] = "assistant_process_loss"
            path.write_bytes(ab.canonical(manifest))
            with self.assertRaisesRegex(ab.InvalidRun, "stratum"):
                ab.analyze(run)

    def test_unknown_study_or_unbalanced_granite_pilot_creates_no_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pilot"
            for study, repeats in [("unrelated-study", 4), ("granite-continuity", 2), ("granite-continuity", 6)]:
                with self.subTest(study=study, repeats=repeats):
                    with self.assertRaises(ab.InvalidRun):
                        ab.prepare_ibm_comparison(out, repeats=repeats, study=study)
                    self.assertFalse(out.exists())

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
