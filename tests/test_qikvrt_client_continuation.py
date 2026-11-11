#!/usr/bin/env python3
"""Fail-closed continuation contract regression tests."""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "tools" / "qikvrt_client_continuation.py"
HEAD = "a" * 40


def receipt(**changes):
    base = {
        "schema": "qikvrt_client_continuation_v1",
        "repository": "ingolf-lohmann/qik-vrt",
        "work_unit_id": "unit-1",
        "writer_id": "writer-1",
        "head_sha": HEAD,
        "state": "RUNNING",
        "next_action": "READBACK",
        "effect_ack_done": False,
    }
    base.update(changes)
    return base


def invoke(data):
    result = subprocess.run(
        [sys.executable, "-B", str(PROGRAM)],
        input=json.dumps(data), text=True, capture_output=True,
        timeout=10, check=False,
    )
    return result.returncode, json.loads(result.stdout)


class ContinuationContractTests(unittest.TestCase):
    def test_repository_wide_continuation_standard(self):
        policy = json.loads((ROOT / "policy" /
            "REPOSITORY_CONTINUATION_STANDARD_V1.json").read_text())
        self.assertEqual(policy["authority_repository"], "ingolf-lohmann/qik-vrt")
        self.assertEqual(policy["default_behavior"], "REENTER_SAME_WRITER")
        self.assertEqual(policy["admission"], "BLOCKED")
        self.assertIn("all repository work units", policy["scope"])
        self.assertGreaterEqual(len(policy["invariants"]), 7)

    def test_running_continues_same_writer(self):
        code, result = invoke(receipt())
        self.assertEqual(code, 0)
        self.assertEqual(result["disposition"], "CONTINUE")
        self.assertEqual(result["writer_id"], "writer-1")
        self.assertEqual(result["next_action"], "READBACK")

    def test_internal_blockers_continue_diagnosis(self):
        for blocker in ("CI", "INTEGRITY", "REVIEW", "HOST", "RUNTIME", "UNKNOWN"):
            with self.subTest(blocker=blocker):
                code, result = invoke(receipt(state="BLOCKED", blocker=blocker))
                self.assertEqual(code, 0)
                self.assertEqual(result["disposition"], "CONTINUE_DIAGNOSIS")
                self.assertFalse(result["effect_ack_done"])

    def test_blocked_internal_effect_actions_become_readback(self):
        for action in ("MERGE", "DEPLOY", "REPAIR"):
            with self.subTest(action=action):
                code, result = invoke(receipt(
                    state="BLOCKED", blocker="CI", next_action=action))
                self.assertEqual(code, 0)
                self.assertEqual(result["disposition"], "CONTINUE_DIAGNOSIS")
                self.assertEqual(result["next_action"], "READBACK")
                self.assertFalse(result["effect_ack_done"])

    def test_external_gates_never_execute(self):
        for blocker in ("AUTHORIZATION", "WORKFLOW_APPROVAL"):
            with self.subTest(blocker=blocker):
                code, result = invoke(receipt(state="BLOCKED", blocker=blocker))
                self.assertEqual(code, 0)
                self.assertEqual(result["disposition"], "HOLD_EXTERNAL")
                self.assertIsNone(result["next_action"])
                self.assertEqual(result["blocked_on"], blocker)

    def test_unverified_done_rejected(self):
        for ack in (False, True):
            with self.subTest(ack=ack):
                code, result = invoke(receipt(state="DONE", effect_ack_done=ack))
                self.assertEqual(code, 2)
                self.assertFalse(result["effect_ack_done"])

    def test_malformed_json_is_diagnostic_not_completion(self):
        process = subprocess.run(
            [sys.executable, "-B", str(PROGRAM)],
            input='{"state":', text=True, capture_output=True,
            timeout=10, check=False,
        )
        self.assertEqual(process.returncode, 2)
        result = json.loads(process.stdout)
        self.assertEqual(result["disposition"], "CONTINUE_DIAGNOSIS")
        self.assertEqual(result["blocker"], "INVALID_RECEIPT")
        self.assertIsNone(result["next_action"])
        self.assertFalse(result["effect_ack_done"])

    def test_invalid_receipts_do_not_crash_or_ack(self):
        for changes in ({"head_sha": "bad"}, {"state": []},
                        {"next_action": {}}, {"effect_ack_done": "true"},
                        {"repository": "other/repo"}):
            with self.subTest(changes=changes):
                code, result = invoke(receipt(**changes))
                self.assertEqual(code, 2)
                self.assertEqual(result["disposition"], "CONTINUE_DIAGNOSIS")
                self.assertIsNone(result["next_action"])
                self.assertFalse(result["effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
