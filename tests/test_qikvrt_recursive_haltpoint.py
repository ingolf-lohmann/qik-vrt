# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_recursive_haltpoint",
    ROOT / "tools/qikvrt_recursive_haltpoint.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def observation(**updates):
    value = {
        "exact_subject_bound": True,
        "final_idle": False,
        "effect_ack_done": False,
        "first_blocker": "EXAMPLE_BLOCKER",
        "productive_edge": "REPAIR_EXAMPLE_BLOCKER",
        "edge_authorized": True,
        "edge_callable": True,
        "requires_external_capability": False,
        "external_capability_available": True,
        "requires_exact_human_authorization": False,
        "exact_human_authorization_available": True,
        "transport_ack": False,
        "predecessor_evidence_transfer": False,
    }
    value.update(updates)
    return value


class RecursiveHaltpointTests(unittest.TestCase):
    def test_policy_is_active_and_preserves_effect_boundary(self):
        policy = MODULE.load_policy()
        self.assertEqual(policy["state"], "ACTIVE")
        self.assertFalse(policy["exact_subject"]["predecessor_evidence_transfer"])
        self.assertFalse(policy["effect_boundary"]["transport_ack_is_effect_ack"])

    def test_local_blocker_with_callable_edge_is_work_not_halt(self):
        result = MODULE.classify(observation())
        self.assertEqual(result["classification"], "WORK")
        self.assertFalse(result["halt"])
        self.assertEqual(result["next_action"], "REPAIR_EXAMPLE_BLOCKER")

    def test_blocker_without_derived_edge_recurses_instead_of_halting(self):
        result = MODULE.classify(observation(productive_edge=None, edge_authorized=False, edge_callable=False))
        self.assertEqual(result["classification"], "WORK")
        self.assertFalse(result["halt"])
        self.assertEqual(result["next_action"], "DERIVE_FIRST_PRODUCTIVE_EDGE")

    def test_quiescence_is_idle_but_not_final_halt(self):
        result = MODULE.classify(observation(first_blocker=None, productive_edge=None, edge_authorized=False, edge_callable=False))
        self.assertEqual(result["classification"], "IDLE")
        self.assertFalse(result["halt"])
        self.assertTrue(result["recursive_continuation"])

    def test_final_idle_is_a_valid_haltpoint(self):
        result = MODULE.classify(observation(
            final_idle=True,
            first_blocker=None,
            productive_edge=None,
            edge_authorized=False,
            edge_callable=False,
        ))
        self.assertEqual(result["classification"], "IDLE")
        self.assertTrue(result["halt"])
        self.assertEqual(result["reason"], "FINAL_IDLE")

    def test_unavailable_external_capability_is_a_valid_haltpoint(self):
        result = MODULE.classify(observation(
            first_blocker="AUTHORITY_NODE_CONNECTION_SCOPE_UNAVAILABLE",
            productive_edge="RESTORE_AUTHORITY_NODE_CONNECTION_SCOPE",
            edge_authorized=False,
            edge_callable=False,
            requires_external_capability=True,
            external_capability_available=False,
        ))
        self.assertEqual(result["classification"], "BLOCKADE")
        self.assertTrue(result["halt"])
        self.assertEqual(result["reason"], "REQUIRED_EXTERNAL_CAPABILITY_UNAVAILABLE")

    def test_missing_exact_human_authorization_is_a_valid_haltpoint(self):
        result = MODULE.classify(observation(
            productive_edge="OBTAIN_EXACT_HUMAN_AUTHORIZATION",
            edge_authorized=False,
            edge_callable=False,
            requires_exact_human_authorization=True,
            exact_human_authorization_available=False,
        ))
        self.assertTrue(result["halt"])
        self.assertEqual(result["reason"], "REQUIRED_EXACT_HUMAN_AUTHORIZATION_UNAVAILABLE")

    def test_transport_success_never_changes_effect_ack(self):
        result = MODULE.classify(observation(transport_ack=True, effect_ack_done=False))
        self.assertFalse(result["halt"])
        self.assertFalse(result["transport_ack_is_effect_ack"])

    def test_drift_requires_rebind_not_halt(self):
        result = MODULE.classify(observation(exact_subject_bound=False))
        self.assertEqual(result["classification"], "WORK")
        self.assertFalse(result["halt"])
        self.assertEqual(result["next_action"], "REBIND_EXACT_HEAD_TREE")

    def test_predecessor_evidence_transfer_is_rejected(self):
        with self.assertRaises(MODULE.HaltpointBlock):
            MODULE.classify(observation(predecessor_evidence_transfer=True))


if __name__ == "__main__":
    unittest.main()
