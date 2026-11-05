#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Isolated fixtures test shape checks, NOT actual behavioral conformance."""

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy" / "QIKVRT_BEHAVIORAL_COGNITION_AUDIT_V1.json"
VALIDATOR_PATH = ROOT / "tools" / "qikvrt_behavioral_cognition_audit_v1.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_behavioral_audit_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class BehavioralAuditStructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy_bytes = POLICY_PATH.read_bytes()
        self.policy = validator.load_json_no_duplicates(self.policy_bytes)
        self.policy_hash = validator.sha256(self.policy_bytes)
        criteria = [item["id"] for item in self.policy["criteria"]]
        checks = [
            {"id": identifier, "result": "PASS", "reviewer_id": "human-reviewer",
             "evidence_anchor": "turn-1/output", "rationale": "Fixture only; result is not an actual behavioral observation."}
            for identifier in criteria
        ]
        observations = []
        for index in (1, 2):
            payload = ("SYNTHETIC CAPTURE " + str(index)).encode("utf-8")
            name = f"session-{index}.txt"
            (self.root / name).write_bytes(payload)
            observations.append({
                "session_id": f"session-{index}", "turn_id": f"turn-{index}",
                "capture_path": name, "capture_sha256": validator.sha256(payload),
                "checks": copy.deepcopy(checks)
            })
        self.audit = {
            "schema": "qikvrt_behavioral_cognition_audit_v1",
            "policy_sha256": self.policy_hash,
            "subject": {"agent_id": "assessed-agent", "model_id": "test-model",
                        "runtime_id": "test-runtime", "environment": "sandbox",
                        "source_head": "1" * 40},
            "observations": observations
        }

    def result(self):
        return validator.validate(self.audit, self.root.resolve(), self.policy, self.policy_hash)

    def test_positive_fixture_is_review_only_not_done(self):
        result = self.result()
        self.assertEqual(result["decision"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(result["behavioral_truth"], "NOT_VERIFIED")
        self.assertEqual(result["runtime_admission"], "UNVERIFIED")
        self.assertFalse(result["EFFECT_ACK_DONE"])

    def test_one_session_is_hold(self):
        self.audit["observations"].pop()
        self.assertEqual(self.result()["decision"], "HOLD")

    def test_failure_is_block(self):
        self.audit["observations"][0]["checks"][0]["result"] = "FAIL"
        self.assertEqual(self.result()["decision"], "BLOCK")

    def test_unverified_is_hold(self):
        self.audit["observations"][0]["checks"][0]["result"] = "UNVERIFIED"
        self.assertEqual(self.result()["decision"], "HOLD")

    def test_changed_bytes_are_rejected(self):
        (self.root / "session-1.txt").write_text("ALTERED", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "capture digest mismatch"):
            self.result()

    def test_duplicate_criterion_is_rejected(self):
        checks = self.audit["observations"][0]["checks"]
        checks[0] = copy.deepcopy(checks[1])
        with self.assertRaisesRegex(ValueError, "missing/duplicate criterion"):
            self.result()

    def test_self_review_is_rejected(self):
        self.audit["observations"][0]["checks"][0]["reviewer_id"] = "assessed-agent"
        with self.assertRaisesRegex(ValueError, "self-review"):
            self.result()

    def test_policy_drift_is_rejected(self):
        self.audit["policy_sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "policy digest mismatch"):
            self.result()

    def test_path_traversal_is_rejected(self):
        self.audit["observations"][0]["capture_path"] = "../outside.txt"
        with self.assertRaisesRegex(ValueError, "unsafe capture path"):
            self.result()

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            validator.load_json_no_duplicates(b'{"session_id":"a","session_id":"b"}')


if __name__ == "__main__":
    unittest.main()
