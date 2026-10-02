# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
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


def authority_routing_observation(**updates):
    reference = MODULE.load_policy()["current_reference_case"]
    value = observation(
        first_blocker=reference["first_blocker"],
        productive_edge=reference["productive_edge"],
        edge_authorized=True,
        edge_callable=False,
        requires_external_capability=True,
        external_capability_available=False,
    )
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
        reference = MODULE.load_policy()["current_reference_case"]
        result = MODULE.classify(authority_routing_observation())
        self.assertEqual(result["classification"], "BLOCKADE")
        self.assertTrue(result["halt"])
        self.assertEqual(result["reason"], "REQUIRED_EXTERNAL_CAPABILITY_UNAVAILABLE")
        self.assertEqual(result["first_blocker"], reference["first_blocker"])
        self.assertEqual(result["productive_edge"], reference["productive_edge"])

    def test_reference_binds_installation_listing_without_global_failure_claim(self):
        reference = MODULE.load_policy()["current_reference_case"]
        self.assertEqual(
            reference["first_blocker"],
            "AUTHORITY_INSTALLATION_CONTENT_ROUTING_CARRIER_UNAVAILABLE",
        )
        self.assertEqual(
            reference["productive_edge"],
            "EXPOSE_AND_USE_INSTALLATION_147849532_BOUND_AUTHORITY_CONTENT_READ",
        )
        evidence = reference["authority_capability_evidence"]
        self.assertEqual(
            evidence["classification"],
            "INSTALLATION_LISTED_AUTHORITY_WITH_CONTENT_ROUTING_CARRIER_BOUNDARY",
        )
        installation = evidence["installation"]
        self.assertEqual(installation["installation_id"], 147849532)
        self.assertEqual(installation["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(installation["repository_id"], 1271407206)
        self.assertEqual(installation["repository_selection"], "all")
        self.assertTrue(installation["listed"])
        self.assertTrue(installation["permissions_as_reported"]["pull"])
        self.assertTrue(installation["permissions_as_reported"]["push"])
        self.assertEqual(set(evidence["generic_read_http_status"].values()), {404})
        self.assertFalse(evidence["installation_bound_content_read_exposed"])
        self.assertFalse(evidence["repository_global_absence_inferred"])
        self.assertFalse(evidence["authority_global_failure_inferred"])
        self.assertFalse(evidence["routing_root_cause_established"])
        self.assertEqual(evidence["source"]["pr_number"], 444)
        self.assertEqual(evidence["source"]["head"], "380fb965a184ee6137bc98ea58868eb8b59ecbce")
        self.assertEqual(evidence["source"]["tree"], "6724c1efeb6242b37aab48c9e6e836f849c773df")

    def test_listed_pull_and_push_do_not_supply_a_callable_content_carrier(self):
        reference = MODULE.load_policy()["current_reference_case"]
        self.assertTrue(reference["authority_capability_evidence"]["installation"]["listed"])
        result = MODULE.classify(authority_routing_observation())
        self.assertTrue(result["halt"])
        self.assertFalse(result["recursive_continuation"])

    def test_authorized_callable_content_carrier_resumes_recursive_work(self):
        result = MODULE.classify(authority_routing_observation(
            edge_callable=True,
            external_capability_available=True,
        ))
        self.assertEqual(result["classification"], "WORK")
        self.assertFalse(result["halt"])
        self.assertTrue(result["recursive_continuation"])
        self.assertEqual(result["reason"], "AUTHORIZED_CALLABLE_PRODUCTIVE_EDGE")

    def test_routing_boundary_requires_exact_subject_rebind_before_halt(self):
        result = MODULE.classify(authority_routing_observation(exact_subject_bound=False))
        self.assertFalse(result["halt"])
        self.assertEqual(result["next_action"], "REBIND_EXACT_HEAD_TREE")

    def test_work_unit_and_policy_share_the_same_bound_reference(self):
        work_unit = json.loads((ROOT / "state/work_units/RECURSIVE_HALTPOINT_V1.json").read_text())
        reference = MODULE.load_policy()["current_reference_case"]
        self.assertEqual(work_unit["reference_blocker"], reference)
        self.assertFalse(work_unit["boundaries"]["predecessor_evidence_transfer"])
        self.assertFalse(work_unit["boundaries"]["effect_ack_done"])
        self.assertFalse(work_unit["capability_synchronization"]["source_pr_gates_transferred"])

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
