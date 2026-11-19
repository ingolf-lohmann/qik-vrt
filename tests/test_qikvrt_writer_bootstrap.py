"""The original consumer must execute, preserve its response and read back in one call."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import qikvrt_autonomous_self_heal as controller
from tools import qikvrt_writer_fence as fence
from tests.test_qikvrt_writer_fence import FakeAPI, MAIN, SOURCE

PARENT = "e" * 40


class BootstrapAPI(FakeAPI):
    record_once = staticmethod(controller.GitHubREST.record_once)
    atomic_request = controller.GitHubREST.atomic_request

    def __init__(self):
        super().__init__()
        self.refs[fence.BOOTSTRAP_REF] = self.refs.pop("refs/heads/repair")
        self.commits[SOURCE]["parents"] = [{"sha": PARENT}]
        self.original_run = {"id": 123, "head_sha": SOURCE,
            "head_branch": fence.BOOTSTRAP_REF.removeprefix("refs/heads/"),
            "event": "push", "path": fence.BOOTSTRAP_WORKFLOW, "run_attempt": 1,
            "actor": {"id": 294949349}, "head_repository": {"id": 1273784147}}
        self.lost_ack = False
        self.crash_after_intent = False
        self.drift_before_atomic = False
        self.reservations = 0

    def call(self, method, path, payload=None):
        if method == "GET" and path == "":
            return {"node_id": "R_kgDOS-xnUw"}
        if method == "GET" and path.startswith("actions/runs/"):
            return self.original_run
        if method == "GET" and path == "pulls/756":
            return {"number": 756, "state": "open",
                "head": {"sha": SOURCE, "ref": fence.BOOTSTRAP_REF.removeprefix("refs/heads/"),
                         "repo": {"full_name": self.repository}},
                "base": {"ref": "main", "repo": {"full_name": self.repository}}}
        return super().call(method, path, payload)

    def create_once(self, ref, sha):
        self.reservations += 1
        if ref in self.refs:
            raise fence.FenceBlocked("CREATE_ONLY_CONFLICT")
        self.refs[ref] = sha
        if self.crash_after_intent:
            raise KeyboardInterrupt()
        return True

    def atomic_refs(self, changes, *, operation_id, journal=None, expected_request=None):
        request = self.atomic_request(changes, operation_id=operation_id)
        assert request == expected_request
        assert any("/bootstrap/" in ref for ref in self.refs), "remote intent must precede POST"
        self.record_once(journal / "request.json", request)
        if self.drift_before_atomic:
            self.refs[fence.BOOTSTRAP_REF] = "f" * 40
        try:
            super().atomic_refs(changes, operation_id=operation_id)
        except RuntimeError:
            self.record_once(journal / "response.json", {"returncode": 1, "stdout": '{"errors":[{"message":"CAS rejected"}]}'})
            raise
        if self.lost_ack:
            self.record_once(journal / "response.json", {"returncode": None, "transport_error": "TimeoutExpired"})
            raise controller.SelfHealBlock("ATOMIC_REF_TRANSPORT_UNCONFIRMED")
        response = {"data": {"updateRefs": {"clientMutationId": operation_id}}}
        self.record_once(journal / "response.json", {"returncode": 0, "stdout": json.dumps(response)})
        return response


class WriterBootstrapTEMDD(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for relative in fence.BOOTSTRAP_PIN_PATHS:
            file = self.root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("exact original source fixture\n")
        instructions = ["Owner authorizes this bounded bootstrap", "Execute and collect the response in this invocation"]
        self.request = {"schema": fence.BOOTSTRAP_SCHEMA,
            "repository": "ingolf-lohmann/qik-vrt", "pull_request": 756,
            "principal": {"name": "Ingolf Lohmann", "github_login": "ingolf-lohmann", "github_id": 294949349},
            "target_ref": fence.BOOTSTRAP_REF, "expected_main": MAIN, "expected_parent": PARENT,
            "scope": "INITIAL_CONTROL_EPOCH_AND_EXACT_HEAD_GUARDS", "effect_ack_done": False,
            "instructions": [{"source": "DIRECT_HUMAN_INSTRUCTION_IN_CURRENT_SESSION", "text": text,
                              "sha256": hashlib.sha256(text.encode()).hexdigest()} for text in instructions],
            "source_pins": {relative: hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
                            for relative in fence.BOOTSTRAP_PIN_PATHS}}
        self.api = BootstrapAPI()
        self.environment = patch.dict(os.environ, {"GITHUB_REPOSITORY": self.api.repository,
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_ACTOR": "ingolf-lohmann",
            "GITHUB_ACTOR_ID": "294949349", "GITHUB_SHA": SOURCE,
            "GITHUB_REF": fence.BOOTSTRAP_REF, "GITHUB_EVENT_NAME": "push"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        checked = patch.object(fence, "_checked_head", return_value=SOURCE)
        checked.start()
        self.addCleanup(checked.stop)

    def invoke(self, name="first"):
        return fence.bootstrap(self.api, self.request, root=self.root,
                               journal=self.root / "journal" / name)

    def test_same_invocation_executes_collects_response_and_reads_back(self):
        result = self.invoke()
        self.assertEqual("BOOTSTRAP_APPLIED", result["state"])
        self.assertTrue(result["readback_verified"])
        self.assertEqual(1, result["submission_count"])
        self.assertEqual(1, len(self.api.atomic_calls))
        self.assertEqual(4, len(self.api.atomic_calls[0][0]))
        self.assertEqual(MAIN, self.api.refs["refs/heads/main"])
        self.assertEqual(SOURCE, self.api.refs[fence.BOOTSTRAP_REF])
        self.assertEqual(self.api.refs[fence.CONTROL_REF], self.api.refs["refs/qikvrt/pr-continuation/epochs/1"])
        for file in ("intent.json", "request.json", "response.json", "readback.json", "result.json"):
            self.assertTrue((self.root / "journal/first" / file).is_file(), file)
        self.assertFalse(result["effect_ack_done"])
        self.assertFalse(result["active_writer_lease"])

    def test_reentry_only_reads_original_intent_without_another_post(self):
        self.invoke()
        count = len(self.api.commits)
        self.api.original_run["id"] = 124
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "124"}):
            result = self.invoke("reentry")
        self.assertEqual("BOOTSTRAP_READBACK_CONFIRMED", result["state"])
        self.assertEqual(0, result["submission_count"])
        self.assertEqual(1, len(self.api.atomic_calls))
        self.assertEqual(count, len(self.api.commits))

    def test_lost_response_is_read_back_now_and_never_replayed(self):
        self.api.lost_ack = True
        result = self.invoke()
        self.assertEqual("BOOTSTRAP_APPLIED_RESPONSE_UNCONFIRMED", result["state"])
        self.assertTrue(result["readback_verified"])
        self.assertIsNotNone(result["error"])
        again = self.invoke("lost-ack-reentry")
        self.assertEqual(0, again["submission_count"])
        self.assertEqual(1, len(self.api.atomic_calls))

    def test_rejected_atomic_update_preserves_response_and_all_original_refs(self):
        self.api.fail_atomic = True
        result = self.invoke()
        self.assertEqual("BOOTSTRAP_HOLD", result["state"])
        self.assertFalse(result["readback_verified"])
        self.assertNotIn(fence.CONTROL_REF, self.api.refs)
        self.assertNotIn("refs/qikvrt/pr-continuation/epochs/1", self.api.refs)
        self.assertEqual(SOURCE, self.api.refs[fence.BOOTSTRAP_REF])
        self.assertTrue((self.root / "journal/first/response.json").exists())
        again = self.invoke("rejected-reentry")
        self.assertEqual("BOOTSTRAP_PRIOR_INTENT_HOLD", again["state"])
        self.assertEqual(1, len(self.api.atomic_calls))

    def test_crash_after_durable_remote_intent_cannot_create_a_second_attempt(self):
        self.api.crash_after_intent = True
        with self.assertRaises(KeyboardInterrupt):
            self.invoke()
        self.api.crash_after_intent = False
        result = self.invoke("after-crash")
        self.assertEqual("BOOTSTRAP_PRIOR_INTENT_HOLD", result["state"])
        self.assertEqual(0, result["submission_count"])
        self.assertEqual([], self.api.atomic_calls)

    def test_concurrent_head_drift_rejects_control_and_epoch_together(self):
        self.api.drift_before_atomic = True
        result = self.invoke()
        self.assertFalse(result["readback_verified"])
        self.assertNotIn(fence.CONTROL_REF, self.api.refs)
        self.assertNotIn("refs/qikvrt/pr-continuation/epochs/1", self.api.refs)

    def test_existing_epoch_is_never_reset_even_without_control(self):
        self.api.refs["refs/qikvrt/pr-continuation/epochs/1"] = "f" * 40
        with self.assertRaisesRegex(fence.FenceBlocked, "ALREADY_EXISTS"):
            self.invoke()
        self.assertEqual([], self.api.atomic_calls)

    def test_mutated_source_never_reserves_or_submits(self):
        (self.root / "tools/qikvrt_writer_fence.py").write_text("changed")
        with self.assertRaisesRegex(fence.FenceBlocked, "PIN_DRIFT"):
            self.invoke()
        self.assertEqual(0, self.api.reservations)
        self.assertEqual([], self.api.atomic_calls)

    def test_untrusted_event_or_actor_never_reserves_or_submits(self):
        for changed in ({"GITHUB_ACTOR_ID": "1"}, {"GITHUB_EVENT_NAME": "pull_request"},
                        {"GITHUB_REF": "refs/heads/foreign"}):
            with self.subTest(changed=changed), patch.dict(os.environ, changed):
                with self.assertRaises(fence.FenceBlocked):
                    self.invoke()
        self.assertEqual(0, self.api.reservations)

    def test_authenticated_run_readback_must_match_source(self):
        self.api.original_run["head_sha"] = "f" * 40
        with self.assertRaisesRegex(fence.FenceBlocked, "RUN_READBACK_MISMATCH"):
            self.invoke()
        self.assertEqual([], self.api.atomic_calls)


class AtomicResponsePreservationTEMDD(unittest.TestCase):
    def test_transport_rejection_records_original_response_before_raising(self):
        api = controller.GitHubREST("ingolf-lohmann/qik-vrt")
        changes = [{"name": fence.CONTROL_REF, "beforeOid": fence.ZERO, "afterOid": SOURCE}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(api, "call", return_value={"node_id": "R_kgDOS-xnUw"}), patch.object(
                controller.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, '{"errors":[{"message":"rejected"}]}', "HTTP 422")) as run:
                with self.assertRaisesRegex(controller.SelfHealBlock, "REJECTED_OR_AMBIGUOUS"):
                    api.atomic_refs(changes, operation_id="bootstrap-test", journal=root)
            self.assertEqual(1, run.call_count)
            self.assertEqual("HTTP 422", json.loads((root / "response.json").read_text())["stderr"])
            self.assertTrue((root / "request.json").exists())

    def test_timeout_records_response_boundary_without_a_second_call(self):
        api = controller.GitHubREST("ingolf-lohmann/qik-vrt")
        changes = [{"name": fence.CONTROL_REF, "beforeOid": fence.ZERO, "afterOid": SOURCE}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(api, "call", return_value={"node_id": "R_kgDOS-xnUw"}), patch.object(
                controller.subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 120)) as run:
                with self.assertRaisesRegex(controller.SelfHealBlock, "TRANSPORT_UNCONFIRMED"):
                    api.atomic_refs(changes, operation_id="bootstrap-test", journal=root)
            self.assertEqual(1, run.call_count)
            self.assertEqual("TimeoutExpired", json.loads((root / "response.json").read_text())["transport_error"])


if __name__ == "__main__":
    unittest.main()
