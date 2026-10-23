# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Technical controls use explicit doubles; real model receipts are separate."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from src import qikvrt_local_llm as local
from src import qikvrt_personal_assistant as personal
from tools.qikvrt_restore_local_llm import restore

TOKEN = "test-local-only-client-" + "z" * 40


class LocalDouble:
    def __init__(self):
        self.credential = "technical-double-key-" + "x" * 40
        self.binding = {"provider": "TECHNICAL_TEST_DOUBLE", "model": local.MODEL_ID,
                        "parameters": local.PARAMETERS.copy(), "normal_retention": "TEST_DOUBLE_PRIVATE_TRANSCRIPT"}
        self.requests = []
        self.fail = False
        self.closed = False

    def post(self, path, payload):
        self.requests.append((path, payload))
        if self.fail:
            raise personal.CapabilityBlock("TEST_DOUBLE_AMBIGUOUS_NO_RETRY")
        return {"id": "double-" + str(len(self.requests)), "model": local.MODEL_ID, "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "Unverified double output"}]}]}, {
                    "evidence_class": "LOCAL_CPU_MODEL_HTTP_RESPONSE"}  # Even this forged label cannot attest.

    def close(self):
        self.closed = True


class LocalLLMTests(unittest.TestCase):
    def test_actual_artifact_pins_and_capability_boundary(self):
        lock = json.loads(local.LOCK.read_text())
        self.assertEqual(lock["model"]["sha256"], "8334b850b7bd46238c16b0c550df2138f0889bf433809008cc17a8b05761863e")
        self.assertEqual(lock["model"]["bytes"], 1915305312)
        self.assertFalse(lock["automatic_download"])
        self.assertFalse(lock["external_provider_required"])
        self.assertFalse(lock["model_output_is_independent_verification"])
        self.assertFalse(lock["proprietary_chatgpt_runtime_exported"])

    def test_same_verified_inode_is_retained_and_corrupt_bytes_fail_before_execution(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); path = root / "model.gguf"; path.write_bytes(b"original")
            item = {"file": path.name, "bytes": 8, "sha256": hashlib.sha256(b"original").hexdigest()}
            fd = local.verified_fd(root, item)
            try:
                path.rename(root / "old"); path.write_bytes(b"replaced")
                self.assertEqual(os.read(fd, 8), b"original")
            finally:
                os.close(fd)
            with self.assertRaisesRegex(personal.CapabilityBlock, "SHA256_MISMATCH"):
                local.verified_fd(root, item)
            path.write_bytes(b"bad")
            with self.assertRaisesRegex(personal.CapabilityBlock, "SIZE_MISMATCH"):
                local.verified_fd(root, item)

    def test_traversal_symlink_fifo_and_writable_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); file = root / "model"; file.write_bytes(b"x")
            item = {"file": "model", "bytes": 1, "sha256": hashlib.sha256(b"x").hexdigest()}
            alias = root / "alias"; alias.symlink_to(file)
            for artifact in [{**item, "file": "../escape"}, {**item, "file": "alias"}]:
                with self.assertRaises(personal.CapabilityBlock): local.verified_fd(root, artifact)
            file.chmod(0o666)
            with self.assertRaisesRegex(personal.CapabilityBlock, "PERMISSIONS"):
                local.verified_fd(root, item)
            file.unlink(); os.mkfifo(file)
            with self.assertRaises(personal.CapabilityBlock): local.verified_fd(root, item)

    def test_redirects_proxy_inheritance_and_error_body_are_not_used(self):
        with self.assertRaisesRegex(personal.CapabilityBlock, "REDIRECT_REFUSED"):
            local.NoLocalRedirect().redirect_request(None, None, 302, "", {}, "https://outside.invalid")
        transport = local.LocalModelTransport.__new__(local.LocalModelTransport)
        transport.base = "http://127.0.0.1:12345"; transport.credential = "private-key"
        transport.opener = unittest.mock.Mock()
        transport.opener.open.side_effect = HTTPError(transport.base, 401, "private-key", {}, io.BytesIO(b"private-key"))
        with self.assertRaisesRegex(personal.CapabilityBlock, "^LOCAL_MODEL_HTTP_401_NO_RETRY$"):
            transport._request("/v1/chat/completions", {"model": local.MODEL_ID})
        self.assertEqual(transport.opener.open.call_count, 1)
        with self.assertRaisesRegex(personal.CapabilityBlock, "CONTAINS_SECRET"):
            transport._request("/v1/chat/completions", {"input": "private-key"})
        with self.assertRaises(personal.CapabilityBlock): transport._request("/props", {})
        source = Path(local.__file__).read_text()
        self.assertIn("ProxyHandler({})", source)

    def test_response_model_truncation_and_tool_calls_fail_closed(self):
        transport = local.LocalModelTransport.__new__(local.LocalModelTransport)
        payload = {"model": local.MODEL_ID, "messages": [], **local.PARAMETERS}
        good = {"id": "response-1", "model": local.MODEL_ID, "choices": [
            {"finish_reason": "stop", "message": {"content": "Draft"}}]}
        with patch.object(transport, "alive", return_value=True), patch.object(transport, "_request") as request:
            for bad in [{**good, "model": "other"}, {**good, "choices": [{"finish_reason": "length"}]},
                        {**good, "choices": [{"finish_reason": "stop", "message": {"content": "Draft", "tool_calls": ["x"]}}]}]:
                request.return_value = (bad, {})
                with self.assertRaises(personal.CapabilityBlock): transport.post("/responses", payload)
            request.return_value = (good, {"evidence_class": "TECHNICAL_TEST_DOUBLE"})
            self.assertEqual(transport.post("/responses", payload)[0]["output"][0]["content"][0]["text"], "Draft")
            with self.assertRaises(personal.CapabilityBlock): transport.post("/responses", {**payload, "max_tokens": 999999})

    def test_local_conversation_restart_and_pending_intent_cannot_attest_a_model(self):
        with tempfile.TemporaryDirectory() as root:
            double = LocalDouble()
            runtime = personal.PersonalRuntime(Path(root)/"state", local.MODEL_ID, "", TOKEN, provider="local", transport=double)
            try:
                first = runtime.create("qikvrt", "Task", [])
                self.assertEqual([p for p, _ in double.requests], ["/responses"])
                self.assertFalse(runtime.capabilities()["local_model_runtime_readback"])
                self.assertFalse(runtime.capabilities()["authenticated_runtime_readback"])
                runtime.close()
                runtime = personal.PersonalRuntime(Path(root)/"state", local.MODEL_ID, "", TOKEN, provider="local", transport=double)
                self.assertEqual(runtime.readback(runtime.load(first["session"]["id"]))["session_sha256"], first["session_sha256"])
                runtime.turn(first["session"]["id"], "Next", resume=True)
                messages = double.requests[-1][1]["messages"]
                self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
                self.assertEqual(messages[2]["content"], first["session"]["history"][0]["text"])
                double.fail = True
                with self.assertRaises(personal.CapabilityBlock): runtime.turn(first["session"]["id"], "Ambiguous")
                runtime.close()
                runtime = personal.PersonalRuntime(Path(root)/"state", local.MODEL_ID, "", TOKEN, provider="local", transport=double)
                count = len(double.requests)
                with self.assertRaisesRegex(personal.CapabilityBlock, "NO_RETRY"): runtime.turn(first["session"]["id"], "Again")
                self.assertEqual(len(double.requests), count)
                for path in (Path(root)/"state").iterdir():
                    self.assertNotIn(TOKEN.encode(), path.read_bytes())
                    self.assertNotIn(double.credential.encode(), path.read_bytes())
            finally:
                runtime.close()

    def test_missing_bundle_starts_no_process_and_cli_cannot_bypass_personal_auth(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(local.subprocess, "Popen") as spawn:
            with self.assertRaises(OSError): local.LocalModelTransport(directory)
            spawn.assert_not_called()
        script = Path(personal.__file__).with_name("qikvrt_effect_ack_http_terminal.py")
        result = subprocess.run([sys.executable, str(script), "--personal-provider", "local", "--personal-local-model-dir", "/not/admitted"], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--personal-state-dir", result.stderr)

    def test_restore_rejects_corruption_atomically_and_preserves_existing_targets(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / "parts"; source.mkdir()
            data = [b"first", b"second"]
            parts = []
            for i, raw in enumerate(data):
                path = source / str(i); path.write_bytes(raw)
                parts.append({"file": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
            expected = {"bytes": 11, "sha256": hashlib.sha256(b"firstsecond").hexdigest()}
            target = root / "restored" / "model"
            restore(source, target, parts, expected)
            self.assertEqual(target.read_bytes(), b"firstsecond")
            with self.assertRaisesRegex(ValueError, "ALREADY_EXISTS"): restore(source, target, parts, expected)
            bad = root / "restored" / "bad"
            (source / "1").write_bytes(b"broken")
            with self.assertRaises(personal.CapabilityBlock): restore(source, bad, parts, expected)
            self.assertFalse(bad.exists())
            self.assertEqual(list(target.parent.glob(".qikvrt-restore-*")), [])
            (source / "1").write_bytes(b"second")
            with self.assertRaisesRegex(ValueError, "WHOLE_ARTIFACT_MISMATCH"):
                restore(source, bad, list(reversed(parts)), expected)
            self.assertFalse(bad.exists())


if __name__ == "__main__": unittest.main()
