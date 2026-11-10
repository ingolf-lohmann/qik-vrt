"""Digital Twin safety and lifecycle regression tests."""
import unittest
from dataclasses import replace

from tools.qikvrt_digital_twin_policy import Evidence, Phase, can_claim_effect, phase


class DigitalTwinPolicyTests(unittest.TestCase):
    def setUp(self):
        self.valid = Evidence(
            command_id="cmd-001",
            principal_id="ingolf-lohmann",
            authenticated_principal=True,
            scope_authorized=True,
            expected_head="a" * 40,
            observed_head="a" * 40,
            expected_tree="b" * 40,
            observed_tree="b" * 40,
            governance_admitted=True,
            execution_started=True,
            effect_id="effect-001",
            ack_command_id="cmd-001",
            ack_effect_id="effect-001",
            ack_independent=True,
            ack_verified=True,
        )

    def test_acknowledged_only_with_complete_evidence(self):
        self.assertEqual(phase(self.valid), Phase.ACKNOWLEDGED)
        self.assertTrue(can_claim_effect(self.valid))

    def test_no_execution_is_authorized_not_complete(self):
        pending = replace(self.valid, execution_started=False, ack_verified=False)
        self.assertEqual(phase(pending), Phase.AUTHORIZED)
        self.assertFalse(can_claim_effect(pending))

    def test_running_without_ack_is_not_complete(self):
        running = replace(self.valid, ack_verified=False)
        self.assertEqual(phase(running), Phase.EXECUTING)
        self.assertFalse(can_claim_effect(running))

    def test_missing_or_forged_evidence_fails_closed(self):
        failures = (
            {"authenticated_principal": False},
            {"scope_authorized": False},
            {"principal_id": ""},
            {"expected_head": "c" * 40},
            {"expected_tree": "d" * 40},
            {"governance_admitted": False},
            {"execution_started": False},
            {"effect_id": ""},
            {"ack_command_id": "other-command"},
            {"ack_effect_id": "other-effect"},
            {"ack_independent": False},
        )
        for delta in failures:
            with self.subTest(delta=delta):
                self.assertFalse(can_claim_effect(replace(self.valid, **delta)))

    def test_unverified_ack_cannot_be_claimed(self):
        self.assertFalse(can_claim_effect(replace(self.valid, ack_verified=False)))


if __name__ == "__main__":
    unittest.main()
