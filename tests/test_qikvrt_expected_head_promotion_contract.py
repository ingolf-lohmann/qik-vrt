# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
PROMOTION_WORKFLOW = ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml"
SELF_HEAL_WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_self_heal.yml"
VERIFIER_WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"
MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"


class ExpectedHeadPromotionContractTests(unittest.TestCase):
    def test_contract_binds_two_phase_executor(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        executor = contract["promotion_executor"]
        self.assertEqual(
            executor["decision_path"],
            "tools/qikvrt_expected_head_promotion.py",
        )
        self.assertEqual(
            executor["workflow_path"],
            ".github/workflows/qikvrt_expected_head_promotion.yml",
        )
        self.assertEqual(executor["opt_in_marker"], MARKER)
        self.assertEqual(executor["maximum_candidates_per_run"], 1)
        self.assertEqual(executor["schedule_fallback"], "*/10 * * * *")
        self.assertEqual(
            executor["two_phase_promotion"],
            ["DRAFT_TO_READY", "STOP_AND_REOBSERVE", "EXPECTED_HEAD_BOUND_MERGE"],
        )
        self.assertEqual(
            executor["merge_binding"],
            "GITHUB_PULL_MERGE_REST_SHA_PRECONDITION",
        )
        self.assertFalse(executor["same_head_verification_proxy_is_competing_writer"])
        self.assertFalse(executor["stale_base_pull_request_is_current_competing_writer"])
        self.assertTrue(executor["current_base_overlapping_pull_request_is_competing_writer"])
        self.assertEqual(executor["external_effect"], "FORBIDDEN")
        verifier_evidence = executor["exact_head_verifier_evidence"]
        self.assertEqual(
            verifier_evidence["canonical_status_context"],
            "QIK-VRT autonomous exact-head verification",
        )
        self.assertEqual(
            verifier_evidence["description_binding"],
            "Exact-head verified: pr={pr}; base={base}",
        )
        self.assertEqual(verifier_evidence["linked_run_event"], "repository_dispatch")
        self.assertEqual(
            verifier_evidence["linked_run_path"],
            ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
        )
        self.assertEqual(verifier_evidence["linked_run_default_branch"], "main")
        self.assertEqual(verifier_evidence["legacy_status_context"], "REJECTED")

    def test_self_heal_candidates_opt_in_to_executor(self) -> None:
        workflow = SELF_HEAL_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(MARKER, workflow)
        self.assertIn("tests.test_qikvrt_expected_head_promotion", workflow)
        self.assertIn("This proposal workflow never merges", workflow)

    def test_executor_is_bounded_and_sha_bound(self) -> None:
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "*/10 * * * *"', workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("READY_RECLASSIFIED_REOBSERVATION_REQUIRED", workflow)
        self.assertIn('exit 0', workflow)
        self.assertIn('-f sha="$EXPECTED_HEAD"', workflow)
        self.assertIn("repos/${REPOSITORY}/pulls/${PR_NUMBER}/merge", workflow)
        self.assertIn("if other.get('base', {}).get('sha') != current_main", workflow)
        self.assertIn("if other.get('head', {}).get('sha') == head", workflow)

    def test_executor_requires_same_repo_body_opt_in_allowlist_and_verifier(self) -> None:
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("head_repository != repository", workflow)
        self.assertIn("head_ref.startswith('automation/self-heal-')", workflow)
        self.assertIn("marker not in body", workflow)
        self.assertNotIn("issues/{pr['number']}/comments", workflow)
        for field in (
            "'same_repository'",
            "'marker_in_pr_body'",
            "'head_ref'",
            "'candidate_files'",
            "'allowed_paths'",
        ):
            self.assertIn(field, workflow)
        self.assertIn("QIK-VRT autonomous exact-head verification", workflow)
        self.assertIn("'event': run.get('event')", workflow)
        self.assertIn("statuses: read", workflow)
        self.assertIn("repos/{repository}/commits/{head}/statuses?per_page=100", workflow)
        self.assertIn("repos/{repository}/actions/runs/{run_id}", workflow)
        self.assertIn("workflow_run_from_status", workflow)
        self.assertIn("'exact_head_verifier_statuses'", workflow)

    def test_verifier_uses_one_canonical_status_context_and_pr_base_binding(self) -> None:
        workflow = VERIFIER_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            'VERIFIER_STATUS_CONTEXT: "QIK-VRT autonomous exact-head verification"',
            workflow,
        )
        self.assertEqual(workflow.count('-f context="$VERIFIER_STATUS_CONTEXT"'), 2)
        self.assertIn(
            '-f description="Exact-head verified: pr=${TARGET_PR}; base=${TARGET_BASE_SHA}"',
            workflow,
        )
        self.assertIn(
            '-f description="Exact-head blocked: pr=${TARGET_PR}; base=${TARGET_BASE_SHA}"',
            workflow,
        )
        self.assertNotIn("QIKVRT autonomous exact-head verification", workflow)

    def test_external_effect_claims_remain_fail_closed(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        claims = contract["promotion_executor"]["completion_claims"]
        self.assertFalse(claims["PASS"])
        self.assertFalse(claims["FINAL_PASS"])
        self.assertFalse(claims["EFFECT_ACK_DONE"])
        self.assertFalse(claims["AUTHORITY_MIRROR_EQUALITY"])
        forbidden = set(contract["forbidden_effects"])
        self.assertIn("zenodo_mutation", forbidden)
        self.assertIn("ietf_mutation", forbidden)
        self.assertIn("credentialed_external_write", forbidden)


if __name__ == "__main__":
    unittest.main()
