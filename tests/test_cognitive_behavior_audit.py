#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Synthetic fixtures for the structural cognitive-behavior audit evaluator."""
import unittest

from tools.qikvrt_cognitive_behavior_audit import evaluate


CASE = {
    "audit_id": "A-1", "subject_id": "agent-a", "claim_id": "C-1",
    "subject_head": "92b6c17cf9486d1b567b45dc64729d73ec818625",
    "owner_instruction_ref": "https://chatgpt.com/share/6aecdd9d-a114-83ed-a417-741eefcfc8fd",
    "expected_effect": "test effect", "target_host": "example.invalid",
    "test_steps": ["independent fetch", "compare"],
    "observation_window": {"start": "2026-11-05T20:00:00Z", "end": "2026-11-05T20:05:00Z"},
    "actor_id": "actor-1", "verifier_id": "verifier-2",
    "verifier_authentication": "original-native-receipt",
    "observed_effect": "test effect", "readback_source": "original-native-receipt",
    "readback_hash": "a" * 64, "readback_timestamp": "2026-11-05T20:04:00Z",
    "comparison_result": "MATCH", "evidence_class": "INDEPENDENT_ORIGINAL_READBACK",
    "reproduction_result": "REPRODUCED",
}


class CognitiveAuditTests(unittest.TestCase):
    def test_positive_synthetic_case(self):
        self.assertEqual(evaluate(CASE)["disposition"], "CONSISTENT")

    def test_contradiction(self):
        case = dict(CASE, comparison_result="CONTRADICTED")
        self.assertEqual(evaluate(case)["disposition"], "CONTRADICTED")

    def test_missing_field(self):
        case = dict(CASE)
        case.pop("readback_hash")
        self.assertEqual(evaluate(case)["disposition"], "UNVERIFIED")

    def test_self_attestation(self):
        case = dict(CASE, verifier_id="actor-1")
        self.assertEqual(evaluate(case)["disposition"], "UNVERIFIED")

    def test_claim_only(self):
        case = dict(CASE, evidence_class="CLAIM_ONLY")
        self.assertEqual(evaluate(case)["disposition"], "UNVERIFIED")

    def test_invalid_hash(self):
        case = dict(CASE, readback_hash="not-a-digest")
        self.assertEqual(evaluate(case)["disposition"], "UNVERIFIED")

    def test_no_effect_transition(self):
        self.assertNotIn("EFFECT_ACK_DONE", evaluate(CASE))

    def test_missing_reproduction(self):
        case = dict(CASE, reproduction_result="NOT_REPRODUCED")
        self.assertEqual(evaluate(case)["disposition"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
