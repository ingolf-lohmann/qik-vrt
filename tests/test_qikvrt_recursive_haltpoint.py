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


class CapabilityPathLearningTests(unittest.TestCase):
    """Synthetic path tests, not a live failover or independent review."""

    def setUp(self):
        self.context = {key: 'fixture' for key in MODULE.CONTEXT_FIELDS}
        self.context.update(repository='ingolf-lohmann/qik-vrt', head='a'*40,
                            tree='b'*40, input_contract='c'*64, output_contract='d'*64)
        self.request = dict(context=self.context, now=1000, intent_state='NOT_STARTED',
                            routes=[], negative_cache=[])

    def route(self, name='mirror', cost=10, count=1):
        steps = []
        for i in range(count):
            steps.append(dict(component='existing/step'+str(i), source_blob='e'*40,
                              input_contract='c'*64 if i == 0 else 'f'*64,
                              output_contract='d'*64 if i == count-1 else 'f'*64,
                              checks={key: True for key in MODULE.CAPABILITY_CHECKS}))
        value = dict(id=name, steps=steps, measured_latency_ms=cost)
        self.bind(value)
        return value

    def bind(self, route):
        key = MODULE.route_key(self.context, route)
        for step in route['steps']:
            step['evidence'] = dict(key=key, observed_at=1000, receipt_sha256='1'*64)

    def resolve(self, *routes):
        self.request['routes'] = list(routes)
        return MODULE.resolve_capability_routes(self.request)

    def test_existing_compatible_components_form_a_plan_not_an_effect(self):
        result = self.resolve(self.route(count=3))
        self.assertEqual(result['state'], 'PLAN_CANDIDATE')
        self.assertEqual(len(result['planned_steps']), 3)
        self.assertFalse(result['effect_permission'])
        self.assertFalse(result['effect_ack_done'])

    def test_every_capability_is_separate_and_unknown_is_not_success(self):
        for check in MODULE.CAPABILITY_CHECKS:
            for value in (False, None):
                with self.subTest(check=check, value=value):
                    route = self.route()
                    route['steps'][0]['checks'][check] = value
                    result = self.resolve(route)
                    self.assertIsNone(result['selected_route'])
                    self.assertIn(check, result['blocked_routes'][0]['reason'])

    def test_owner_admin_does_not_override_integration_denial(self):
        route = self.route()
        route['user_permission'] = 'admin'
        route['steps'][0]['checks']['effective_permission'] = False
        self.assertIsNone(self.resolve(route)['selected_route'])

    def test_failed_primary_selects_live_alternative_without_global_halt(self):
        primary, alternate = self.route('authority', 1), self.route('mirror', 2)
        primary['steps'][0]['checks']['node_live'] = False
        result = self.resolve(primary, alternate)
        self.assertEqual(result['selected_route'], 'mirror')
        self.assertEqual(result['scope'], 'SUPPLIED_INVENTORY_ONLY')

    def test_faster_valid_route_and_deterministic_tie_break(self):
        self.assertEqual(self.resolve(self.route('z', 3), self.route('a', 3))['selected_route'], 'a')
        self.assertEqual(self.resolve(self.route('a', 3), self.route('z', 1))['selected_route'], 'z')

    def test_interface_mismatch_cannot_be_patched_over_by_presence(self):
        route = self.route(count=2)
        route['steps'][1]['input_contract'] = '2'*64
        self.bind(route)
        self.assertIn('INTERFACE', self.resolve(route)['blocked_routes'][0]['reason'])

    def test_goal_and_initial_contracts_are_bound(self):
        for position, field in ((0, 'input_contract'), (-1, 'output_contract')):
            route = self.route(count=2)
            route['steps'][position][field] = '2'*64
            self.bind(route)
            self.assertIsNone(self.resolve(route)['selected_route'])

    def test_future_expired_and_wrong_receipts_require_reobservation(self):
        for timestamp in (1001, 940):
            route = self.route()
            route['steps'][0]['evidence']['observed_at'] = timestamp
            self.assertIn('REOBSERVE', self.resolve(route)['blocked_routes'][0]['reason'])
        route = self.route()
        route['steps'][0]['evidence']['key'] = '2'*64
        self.assertIsNone(self.resolve(route)['selected_route'])

    def test_negative_cache_suppresses_unchanged_denial_without_retry(self):
        route = self.route()
        route['steps'][0]['checks']['credential_delivered'] = False
        first = self.resolve(route)
        self.request['negative_cache'] = first['negative_cache']
        route['steps'][0]['checks']['credential_delivered'] = True
        self.assertEqual(self.resolve(route)['blocked_routes'][0]['reason'], 'UNCHANGED_DENIAL_NO_RETRY')

    def test_changed_binding_invalidates_cache_but_not_freshness_gate(self):
        route = self.route()
        key = MODULE.route_key(self.context, route)
        self.request['negative_cache'] = [dict(key=key, observed_at=1000, receipt_sha256='1'*64)]
        self.context['credential_epoch'] = 'changed'
        self.assertIn('REOBSERVE', self.resolve(route)['blocked_routes'][0]['reason'])
        self.bind(route)
        self.assertEqual(self.resolve(route)['selected_route'], 'mirror')

    def test_each_binding_field_invalidates_observed_authority(self):
        route = self.route()
        key = MODULE.route_key(self.context, route)
        for field in MODULE.CONTEXT_FIELDS:
            old = self.context[field]
            self.context[field] = ('2'*len(old)) if field in ('head','tree','input_contract','output_contract') else 'changed'
            self.assertNotEqual(MODULE.route_key(self.context, route), key, field)
            self.assertIsNone(self.resolve(route)['selected_route'])
            self.context[field] = old

    def test_source_change_invalidates_receipt(self):
        route = self.route()
        route['steps'][0]['source_blob'] = '2'*40
        self.assertIsNone(self.resolve(route)['selected_route'])

    def test_expired_negative_observation_does_not_authorize_retry(self):
        route = self.route()
        self.request['negative_cache'] = [dict(key=MODULE.route_key(self.context, route),
                                                observed_at=940, receipt_sha256='1'*64)]
        route['steps'][0]['evidence']['observed_at'] = 940
        self.assertIsNone(self.resolve(route)['selected_route'])

    def test_unknown_or_acknowledged_effect_is_readback_only_not_replay(self):
        for state in ('UNKNOWN_EFFECT', 'ACKNOWLEDGED'):
            self.request.update(intent_state=state, intent_receipt_sha256='2'*64)
            result = self.resolve(self.route())
            self.assertEqual(result['state'], 'READBACK_ONLY')
            self.assertIsNone(result['selected_route'])
            self.assertFalse(result['effect_permission'])

    def test_malformed_checks_and_missing_fence_fail_closed(self):
        for value in ('true', 1, [], {}):
            route = self.route()
            route['steps'][0]['checks']['node_live'] = value
            with self.assertRaises(MODULE.HaltpointBlock):
                self.resolve(route)
        route = self.route()
        del route['steps'][0]['checks']['role_fence_valid']
        with self.assertRaises(MODULE.HaltpointBlock):
            self.resolve(route)

    def test_bounded_inventory_duplicate_ids_and_empty_paths(self):
        route = self.route()
        with self.assertRaises(MODULE.HaltpointBlock):
            self.resolve(route, route)
        with self.assertRaises(MODULE.HaltpointBlock):
            self.resolve(*[self.route(str(i)) for i in range(MODULE.MAX_ROUTES+1)])
        route['steps'] = []
        with self.assertRaises(MODULE.HaltpointBlock):
            self.resolve(route)
        self.assertEqual(self.resolve()['state'], 'CAPABILITY_PATH_UNRESOLVED')

    def test_existing_classifier_uses_supplied_alternative(self):
        self.request['routes'] = [self.route()]
        result = MODULE.classify(authority_routing_observation(
            subject={k:self.context[k] for k in ('repository','head','tree')},
            capability_routes=self.request))
        self.assertFalse(result['halt'])
        self.assertFalse(result['effect_permission'])
        self.assertEqual(result['capability_resolution']['selected_route'], 'mirror')

    def test_no_generic_consent_or_route_selection_bypasses_exact_authorization(self):
        self.request['routes'] = [self.route()]
        result = MODULE.classify(observation(
            subject={k:self.context[k] for k in ('repository','head','tree')},
            capability_routes=self.request,
            requires_exact_human_authorization=True, exact_human_authorization_available=False))
        self.assertEqual(result['reason'], 'REQUIRED_EXACT_HUMAN_AUTHORIZATION_UNAVAILABLE')
        self.assertFalse(result['effect_permission'])

    def test_legacy_observers_cannot_turn_a_boolean_into_effect_permission(self):
        result = MODULE.classify(observation())
        self.assertEqual(result['capability_resolution']['state'], 'UNOBSERVED_NOT_EXECUTION_AUTHORITY')
        self.assertFalse(result['effect_permission'])
        self.assertEqual(result['capability_contract'], MODULE.LESSONS_PATH)

    def test_wrong_subject_cannot_select_route(self):
        self.request['routes'] = [self.route()]
        with self.assertRaises(MODULE.HaltpointBlock):
            MODULE.classify(observation(subject={}, capability_routes=self.request))
        result = MODULE.classify(observation(exact_subject_bound=False, capability_routes=self.request))
        self.assertEqual(result['next_action'], 'REBIND_EXACT_HEAD_TREE')

    def test_learning_contract_remains_explicitly_unverified_for_live_failover(self):
        learning = MODULE.load_policy()['capability_path_learning']
        self.assertEqual(learning['max_routes'], MODULE.MAX_ROUTES)
        self.assertEqual(learning['max_steps'], MODULE.MAX_STEPS)
        self.assertEqual(learning['observation_max_age_seconds'], MODULE.MAX_AGE_SECONDS)
        self.assertFalse(learning['runtime_failover_verified'])
        self.assertFalse(learning['application_invisibility_verified'])
        self.assertFalse(learning['owner_admin_is_integration_permission'])
        self.assertFalse(learning['component_presence_is_end_to_end_readiness'])


if __name__ == "__main__":
    unittest.main()
