# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Model predicate, mutation and claim-boundary tests; no native effect claim."""
import json
import unittest
from pathlib import Path
from tools.qikvrt_cognitive_effect_learning import (
    POLICY, REQUIRED, evaluate, validate_policy,
)


class CognitiveEffectLearningTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_contract_valid(self):
        self.assertEqual(validate_policy(self.policy), self.policy)

    def test_all_true_is_model_only_not_productive_eap(self):
        result = evaluate(dict.fromkeys(REQUIRED, True))
        self.assertTrue(result["abstract_model_satisfies_gates"])
        self.assertEqual(result["state"], "HOLD")
        self.assertFalse(result["effect_ack_done"])
        self.assertFalse(result["external_effect_authenticated"])
        self.assertEqual(result["release_admission"], "BLOCKED")

    def test_every_missing_gate_fails_closed(self):
        for key in REQUIRED:
            with self.subTest(key=key):
                evidence = dict.fromkeys(REQUIRED, True)
                evidence[key] = False
                result = evaluate(evidence)
                self.assertFalse(result["abstract_model_satisfies_gates"])
                self.assertEqual(result["missing_model_gates"], [key])
                self.assertFalse(result["effect_ack_done"])

    def test_missing_or_extra_gate_rejected(self):
        with self.assertRaisesRegex(ValueError, "MISSING_OR_UNKNOWN_GATE"):
            evaluate({"observationBound": True})
        with self.assertRaisesRegex(ValueError, "MISSING_OR_UNKNOWN_GATE"):
            evaluate(dict.fromkeys(REQUIRED, True) | {"ready": True})

    def test_non_boolean_gate_rejected(self):
        for value in (1, "true", None):
            with self.subTest(value=value):
                record = dict.fromkeys(REQUIRED, True)
                record["writerFenced"] = value
                with self.assertRaisesRegex(ValueError, "NON_BOOLEAN_GATE"):
                    evaluate(record)

    def test_claim_escalation_rejected(self):
        for key, value in (("effect_ack_done", True),
                           ("release_admission", "ADMITTED"),
                           ("workflow_purpose", "DEPLOY"),
                           ("competitive_superiority_over_all_systems", "PROVEN")):
            with self.subTest(key=key):
                changed = dict(self.policy)
                changed[key] = value
                with self.assertRaisesRegex(ValueError, "UNADMITTED_EFFECT_OR_COMPARATIVE_CLAIM"):
                    validate_policy(changed)

    def test_authority_and_roundtrip_bound(self):
        changed = dict(self.policy)
        changed["authority"] = "other/repo"
        with self.assertRaisesRegex(ValueError, "WRONG_AUTHORITY"):
            validate_policy(changed)
        changed = dict(self.policy)
        changed["roundtrip"] = self.policy["roundtrip"][:-1]
        with self.assertRaisesRegex(ValueError, "ROUNDTRIP_CHANGED"):
            validate_policy(changed)

    def test_proof_source_has_no_gaps_or_native_promotion(self):
        source = (Path(__file__).resolve().parents[1] /
                  "formalization/cognition_effect_learning_20261110/EffectLearning.lean").read_text()
        import re
        self.assertFalse(re.search(r"(?m)^\s*(sorry|admit|axiom)\b", source))
        self.assertIn("DecisionSufficiency.factorization_implies_sufficiency", source)
        self.assertIn("WorldFormula.every_stage_has_a_successor", source)
        self.assertIn("missing_independent_readback_blocks_learning", source)
        self.assertIn("missing_writer_fence_blocks_learning", source)
        frozen = (Path(__file__).resolve().parents[1] / "formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Cognition/EffectLearning.lean")
        self.assertFalse(frozen.exists(), "FROZEN_V2_PACKAGE_MUTATED")


if __name__ == "__main__":
    unittest.main()
