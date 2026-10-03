import json
import copy
from unittest.mock import patch
from tools import ai_runtime_bootloader as boot
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json"
MATRIX = ROOT / "state/interface_adaptation/EVALUATION_MATRIX.json"
CONTEXT = ROOT / "AI_CONTEXT.json"
ENTRYPOINT = ROOT / "AI"
BOOTLOADER = ROOT / "tools/ai_runtime_bootloader.py"


class TestHumanMachineInterfaceAdaptation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        cls.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        cls.ai = ENTRYPOINT.read_text(encoding="utf-8")
        cls.boot = BOOTLOADER.read_text(encoding="utf-8")

    def test_reuse_before_create_and_fastest_verified_path(self):
        self.assertTrue(self.policy["reuse_before_create"])
        self.assertEqual(self.policy["adaptive_routing"]["strategy"], "FASTEST_VERIFIED_PATH")
        self.assertEqual(self.policy["adaptation_mode"], "MEASURE_CACHE_RANK_PROPOSE_REVIEW")

    def test_four_distinct_cache_layers_are_locked(self):
        ids = {row["id"] for row in self.policy["cache_layers"]}
        self.assertEqual(ids, {
            "L0_SESSION",
            "L1_PERSONAL_WORKING_MEMORY",
            "L2_RUNTIME_TOOLCHAIN",
            "L3_DERIVED_KNOWLEDGE",
        })

    def test_speed_may_not_reduce_quality_or_gates(self):
        selection = self.matrix["selection"]
        self.assertFalse(selection["quality_regression_allowed"])
        self.assertFalse(selection["mandatory_gate_reduction_allowed"])
        forbidden = set(self.policy["never_optimize_by"])
        self.assertIn("skipping mandatory gates", forbidden)
        self.assertIn("weakening exact-head binding", forbidden)
        self.assertIn("dropping provenance", forbidden)
        self.assertIn("treating cached output as proof authority", forbidden)

    def test_preference_requires_comparable_evidence(self):
        contract = self.policy["evaluation_matrix"]
        self.assertGreaterEqual(contract["minimum_observations_before_preference"], 3)
        self.assertTrue(contract["quality_must_not_regress"])
        self.assertEqual(self.matrix["selection"]["preferred_path"], "UNSET_UNTIL_COMPARABLE_EVIDENCE_EXISTS")

    def test_audio_and_incremental_processing_are_hash_bound(self):
        incremental = self.policy["incremental_processing"]
        self.assertTrue(incremental["prefer_changed_bytes_over_full_reprocessing"])
        self.assertTrue(incremental["content_addressed_chunks"])
        self.assertTrue(incremental["audio"]["transcript_key_includes_audio_sha256"])
        self.assertTrue(incremental["audio"]["cache_per_chunk_transcript"])

    def test_context_entrypoint_and_bootloader_bind_contract(self):
        adaptation = self.context["human_machine_interface_adaptation"]
        self.assertEqual(adaptation["policy"], "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json")
        self.assertEqual(adaptation["evaluation_matrix"], "state/interface_adaptation/EVALUATION_MATRIX.json")
        self.assertIn("policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json", self.context["required_read_order"])
        self.assertIn("state/interface_adaptation/EVALUATION_MATRIX.json", self.context["required_read_order"])
        self.assertIn("ADAPTIVE HUMAN-MACHINE INTERFACE", self.ai)
        self.assertIn("FASTEST_VERIFIED_PATH", self.ai)
        self.assertIn("load_interface_adaptation", self.boot)
        self.assertIn("INTERFACE_ADAPTATION_MODE", self.boot)

    def test_external_effects_and_secrets_remain_fail_closed(self):
        self.assertFalse(self.policy["privacy_and_security"]["secrets_in_cache"])
        self.assertFalse(self.policy["privacy_and_security"]["credentials_in_cache"])
        self.assertIn("performing external effects without authorization", self.policy["never_optimize_by"])
        self.assertFalse(self.policy["release_claims"]["PASS"])
        self.assertFalse(self.policy["release_claims"]["FINAL_PASS"])
        self.assertFalse(self.policy["release_claims"]["EFFECT_ACK_DONE"])

    def test_startup_resolves_existing_review_delegation(self):
        authority = boot.load_requested_review_authority(self.context, "ingolf-lohmann/qik-vrt")
        self.assertTrue(authority["authorization_established"])
        self.assertEqual(authority["route"]["state"], "CAPABILITY_AND_ADMISSION_UNVERIFIED")
        self.assertFalse(authority["merge_authorized"])
        self.assertFalse(authority["independent_account_approval"])

    def test_missing_discovery_binding_fails_closed(self):
        context = copy.deepcopy(self.context)
        context["required_read_order"].remove("state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json")
        with self.assertRaises(boot.BootBlock):
            boot.load_requested_review_authority(context, "ingolf-lohmann/qik-vrt")

    def test_revoked_delegation_is_not_reused(self):
        real = boot.load_json_object
        def revoked(path, label):
            data = real(path, label)
            if "OWNER_REQUESTED_REVIEW" in str(path):
                data["state"] = "REVOKED"
            return data
        with patch.object(boot, "load_json_object", side_effect=revoked):
            self.assertFalse(boot.load_requested_review_authority(self.context, "ingolf-lohmann/qik-vrt")["authorization_established"])

    def test_foreign_repository_cannot_inherit_scoped_authority(self):
        self.assertFalse(boot.load_requested_review_authority(self.context, "other/project")["authorization_established"])

    def test_reviewer_422_and_write_preserve_authority_as_conflicting_evidence(self):
        route = boot.classify_review_route(True, "REJECTED", "WRITE")
        self.assertEqual(route["state"], "CONFLICTING_PLATFORM_EVIDENCE")
        self.assertTrue(route["authorization_established"])
        self.assertFalse(route["review_accepted"])
        self.assertFalse(route["effect_ack_done"])
        self.assertNotIn("RESOLVE_SCOPED_OWNER_AUTHORITY", route["next_action"])

    def test_request_receipt_never_becomes_review_or_effect(self):
        route = boot.classify_review_route(True, "RECORDED", "WRITE")
        self.assertEqual(route["state"], "REQUEST_RECORDED_REVIEW_NOT_ESTABLISHED")
        self.assertFalse(route["review_accepted"])
        self.assertFalse(route["effect_ack_done"])

    def test_permission_never_creates_owner_authorization(self):
        route = boot.classify_review_route(False, "RECORDED", "WRITE")
        self.assertEqual(route["state"], "AUTHORIZATION_NOT_ESTABLISHED")
        self.assertFalse(route["authorization_established"])

    def test_invalid_route_observation_is_rejected(self):
        for arguments in [(1, "UNVERIFIED", "WRITE"), (True, "APPROVED", "WRITE"), (True, "REJECTED", "admin")]:
            with self.assertRaises(boot.BootBlock):
                boot.classify_review_route(*arguments)


if __name__ == "__main__":
    unittest.main()
