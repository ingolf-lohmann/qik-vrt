# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Technical transport controls; no live Gemini inference or product trial."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from src import qikvrt_personal_assistant as p

KEY = "synthetic-gemini-key-for-test-only"
TOKEN = "synthetic-local-token-" + "x" * 32


class GeminiAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "private"
        self.transport = p.GeminiTransport(KEY)
        self.calls = []
        self.raw = {"id": "interaction_test_1", "model": "gemini-4-argon", "status": "completed",
                    "steps": [{"type": "thought", "signature": "not-a-user-answer"},
                              {"type": "model_output", "content": [{"type": "text", "text": "Technical draft."}]}]}
        def send(request):
            self.calls.append(request)
            return self.raw, {"evidence_class": "TECHNICAL_TEST_DOUBLE"}
        self.mock = patch.object(self.transport, "_send", side_effect=send)
        self.mock.start()
        self.runtime = p.PersonalRuntime(self.root, "gemini-4-argon", KEY, TOKEN,
                                        transport=self.transport, provider="gemini")

    def tearDown(self):
        if self.runtime:
            self.runtime.close()
        self.mock.stop()
        self.tmp.cleanup()

    def create(self, mode="qikvrt"):
        return self.runtime.create(mode, "Summarize this supplied source.",
                                   [{"id": "a", "revision": "1", "text": "A source."}])

    def test_fixed_endpoint_and_explicit_stateless_bounded_request(self):
        result = self.create()
        self.assertEqual(len(self.calls), 1)
        request = self.calls[0]
        self.assertEqual(request.full_url, "https://generativelanguage.googleapis.com/v1beta/interactions")
        self.assertNotIn(KEY, request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), KEY)
        payload = json.loads(request.data)
        self.assertIs(payload["store"], False)
        self.assertIs(payload["background"], False)
        self.assertEqual(payload["generation_config"]["max_output_tokens"], 4096)
        self.assertNotIn("tools", payload)
        self.assertNotIn("previous_interaction_id", payload)
        self.assertIsNone(result["session"]["conversation_id"])
        self.assertFalse(self.runtime.capabilities()["authenticated_runtime_readback"])
        self.assertFalse(result["ordinary_release"])

    def test_checkpoint_and_local_history_survive_restart(self):
        first = self.create()
        self.runtime.close()
        self.runtime = p.PersonalRuntime(self.root, "gemini-4-argon", KEY, TOKEN,
                                        transport=self.transport, provider="gemini")
        result = self.runtime.turn(first["session"]["id"], "Continue.", resume=True)
        envelope = json.loads(json.loads(self.calls[-1].data)["input"])
        self.assertEqual(len(envelope["history"]), 1)
        self.assertEqual(envelope["history"][0]["draft"], "Technical draft.")
        self.assertEqual(len(result["session"]["history"]), 2)
        self.assertIsNotNone(result["automatic_context"])

    def test_baseline_and_qikvrt_use_same_provider_parameters(self):
        self.create("baseline"); self.create("qikvrt")
        a, b = [json.loads(r.data) for r in self.calls]
        self.assertEqual(a, b)

    def test_tool_output_or_wrong_model_cannot_become_completed_draft(self):
        self.raw["steps"] = [{"type": "function_call", "name": "unrequested_write"}]
        with self.assertRaisesRegex(p.CapabilityBlock, "UNEXPECTED_TOOL"):
            self.create()
        pending = self.runtime.sessions()[0]
        self.assertEqual(pending["status"], "TURN_PENDING")
        with self.assertRaisesRegex(p.CapabilityBlock, "NO_RETRY"):
            self.runtime.turn(pending["id"], "Again")
        self.assertEqual(len(self.calls), 1)

    def test_wrong_resolved_model_is_rejected(self):
        self.raw["model"] = "another-model"
        with self.assertRaisesRegex(p.CapabilityBlock, "MODEL_MISMATCH"):
            self.create()

    def test_credentials_do_not_enter_state(self):
        self.create()
        for f in self.root.iterdir():
            if f.is_file():
                self.assertNotIn(KEY.encode(), f.read_bytes())
                self.assertNotIn(TOKEN.encode(), f.read_bytes())

    def test_provider_change_cannot_reuse_existing_database(self):
        self.create(); self.runtime.close(); self.runtime = None
        with self.assertRaisesRegex(p.CapabilityBlock, "MISMATCH"):
            p.PersonalRuntime(self.root, "gemini-4-argon", KEY, TOKEN, transport=self.transport)

    def test_storage_or_tool_override_is_rejected_before_transport(self):
        self.create()
        payload = json.loads(self.calls[0].data)
        payload["store"] = True
        with self.assertRaisesRegex(p.CapabilityBlock, "OUTSIDE_BOUND_CONTRACT"):
            self.transport.post("/responses", payload)
        self.assertEqual(len(self.calls), 1)

    def test_missing_credential_and_unknown_provider_fail_closed(self):
        with self.assertRaisesRegex(p.CapabilityBlock, "GEMINI_RUNTIME_CREDENTIAL_UNAVAILABLE"):
            p.GeminiTransport("")
        with self.assertRaisesRegex(p.CapabilityBlock, "PROVIDER_NOT_ALLOWLISTED"):
            p.PersonalRuntime(Path(self.tmp.name) / "other", "gemini-4-argon", KEY, TOKEN, provider="unknown")

    def test_http_failure_is_sanitized_and_not_retried(self):
        transport = p.GeminiTransport(KEY)
        self.create()
        payload = json.loads(self.calls[0].data)
        with patch.object(transport.opener, "open", side_effect=HTTPError("https://generativelanguage.googleapis.com", 401, KEY, {}, None)) as call:
            with self.assertRaisesRegex(p.CapabilityBlock, "HTTP_401_NO_RETRY") as failure:
                transport.post("/responses", payload)
            self.assertNotIn(KEY, str(failure.exception))
            self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
