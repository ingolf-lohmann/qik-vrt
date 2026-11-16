"""Conformance and negative-control tests for the three-fixpoint contract."""
import unittest
from dataclasses import replace
from tools.qikvrt_three_fixpoint import Transition, admitted, acknowledged, inside


class ThreeFixpointTests(unittest.TestCase):
    def setUp(self):
        self.good = Transition(
            command_id="principal-command-1",
            principal_authorized=True,
            expected_head="a" * 40,
            observed_head="a" * 40,
            gates_passed=True,
            effect_id="effect-1",
            ack_command_id="principal-command-1",
            ack_effect_id="effect-1",
            ack_independent=True,
            ack_verified=True,
        )

    def test_authorized_verified_transition(self):
        self.assertTrue(admitted(self.good))
        self.assertTrue(acknowledged(self.good))
        self.assertTrue(inside(self.good))

    def test_every_gate_is_necessary(self):
        negative_controls = (
            {"principal_authorized": False},
            {"expected_head": "b" * 40},
            {"gates_passed": False},
            {"ack_command_id": "different-command"},
            {"ack_effect_id": "different-effect"},
            {"ack_independent": False},
            {"ack_verified": False},
            {"effect_id": ""},
        )
        for change in negative_controls:
            with self.subTest(change=change):
                self.assertFalse(inside(replace(self.good, **change)))

    def test_ack_cannot_override_denied_admission(self):
        denied = replace(self.good, principal_authorized=False)
        self.assertFalse(admitted(denied))
        self.assertFalse(acknowledged(denied))


if __name__ == "__main__":
    unittest.main()
