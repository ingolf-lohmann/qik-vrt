# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_expected_head_promotion",
    ROOT / "tools/qikvrt_expected_head_promotion.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ExpectedHeadPromotionTests(unittest.TestCase):
    def exact_head_verifier_status(self, **overrides):
        base = "a" * 40
        head = "b" * 40
        run_id = 31687778942
        run_url = f"https://github.com/ingolf-lohmann/qik-vrt/actions/runs/{run_id}"
        value = {
            "id": 910,
            "sha": head,
            "context": MODULE.EXACT_HEAD_VERIFIER,
            "state": "success",
            "description": MODULE.EXACT_HEAD_VERIFIER_SUCCESS_DESCRIPTION.format(
                pr=459, base=base
            ),
            "target_url": run_url,
            "workflow_run": {
                "id": run_id,
                "html_url": run_url,
                "name": MODULE.EXACT_HEAD_VERIFIER,
                "path": MODULE.EXACT_HEAD_VERIFIER_WORKFLOW_PATH,
                "event": "repository_dispatch",
                "status": "completed",
                "conclusion": "success",
                "head_sha": base,
                "head_branch": "main",
                "repository": "ingolf-lohmann/qik-vrt",
                "head_repository": "ingolf-lohmann/qik-vrt",
            },
        }
        value.update(overrides)
        return value

    def snapshot(self, **overrides):
        value = {
            "pr_number": 459,
            "repository": "ingolf-lohmann/qik-vrt",
            "github_server_url": "https://github.com",
            "current_main_sha": "a" * 40,
            "base_sha": "a" * 40,
            "expected_head_sha": "b" * 40,
            "current_head_sha": "b" * 40,
            "commit_status_sha": "b" * 40,
            "draft": True,
            "mergeable": True,
            "external_effect": "NONE",
            "same_repository": True,
            "marker_in_pr_body": True,
            "head_ref": "automation/self-heal-test-candidate",
            "candidate_files": [
                "qikvrt/runtime/onboarding/NODE_HEALTH.json",
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ],
            "allowed_paths": [
                "qikvrt/runtime/onboarding/NODE_HEALTH.json",
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ],
            "required_gates": [
                "QIKVRT CI",
                "QIKVRT repository evidence materialization",
                "QIKVRT Collective Proposal Review",
                "QIK-VRT global claim completion",
            ],
            "workflow_runs": [
                {"name": "QIKVRT CI", "status": "completed", "conclusion": "success", "run_number": 10},
                {"name": "QIKVRT repository evidence materialization", "status": "completed", "conclusion": "success", "run_number": 20},
                {"name": "QIKVRT Collective Proposal Review", "status": "completed", "conclusion": "success", "run_number": 30},
                {"name": "QIK-VRT global claim completion", "status": "completed", "conclusion": "success", "run_number": 40},
                {"name": "QIKVRT conditional probe", "status": "completed", "conclusion": "skipped", "run_number": 1},
            ],
            "exact_head_verifier_statuses": [self.exact_head_verifier_status()],
            "competing_writer_overlaps": [],
        }
        value.update(overrides)
        return value

    def test_terminal_green_exact_head_is_promotable(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot())
        self.assertEqual(result["state"], "PROMOTABLE")
        self.assertEqual(result["expected_head_sha"], "b" * 40)
        self.assertEqual(result["first_blocker"], None)

    def test_old_action_required_run_is_superseded_by_newer_success(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"].extend(
            [
                {"name": "QIKVRT CI", "status": "completed", "conclusion": "action_required", "run_number": 9},
                {"name": "QIKVRT repository evidence materialization", "status": "completed", "conclusion": "action_required", "run_number": 19},
            ]
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "PROMOTABLE")

    def test_missing_required_gate_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"] = [
            run for run in snapshot["workflow_runs"] if run["name"] != "QIKVRT Collective Proposal Review"
        ]
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_MISSING")

    def test_active_required_gate_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "in_progress", "conclusion": None, "run_number": 11}
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_NOT_TERMINAL")

    def test_failed_required_gate_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "completed", "conclusion": "failure", "run_number": 11}
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN")

    def test_head_drift_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(current_head_sha="c" * 40))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "HEAD_DRIFT")

    def test_base_drift_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(current_main_sha="c" * 40))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")

    def test_competing_writer_overlap_blocks(self) -> None:
        result = MODULE.evaluate_promotion(
            self.snapshot(competing_writer_overlaps=[{"pr_number": 452, "paths": ["REPOSITORY_FILE_MANIFEST.json"]}])
        )
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "COMPETING_WRITER_OVERLAP")

    def test_external_effect_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(external_effect="ZENODO"))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXTERNAL_EFFECT_BOUNDARY")

    def test_non_mergeable_candidate_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(mergeable=False))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "NOT_MERGEABLE")

    def test_fork_candidate_blocks_before_any_gate_interpretation(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(same_repository=False))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "CANDIDATE_NOT_SAME_REPOSITORY")

    def test_comment_only_or_missing_body_marker_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(marker_in_pr_body=False))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(
            result["first_blocker"], "CANDIDATE_NOT_EXPLICITLY_OPTED_IN"
        )

    def test_nonallowlisted_candidate_path_blocks(self) -> None:
        result = MODULE.evaluate_promotion(
            self.snapshot(
                candidate_files=[
                    "AI_STATUS.md",
                    "REPOSITORY_FILE_MANIFEST.json",
                    "REPOSITORY_FILE_MANIFEST.json.sha256",
                    "SHA256SUMS.txt",
                ]
            )
        )
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "CANDIDATE_DIFF_NOT_ALLOWLISTED")

    def test_exact_head_verifier_status_is_required(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"] = []
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXACT_HEAD_VERIFIER_MISSING")

    def test_head_filtered_dispatch_run_cannot_substitute_for_status_receipt(self) -> None:
        snapshot = self.snapshot(exact_head_verifier_statuses=[])
        snapshot["workflow_runs"].append(
            {
                "name": MODULE.EXACT_HEAD_VERIFIER,
                "event": "repository_dispatch",
                "status": "completed",
                "conclusion": "success",
                "run_number": 999,
            }
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXACT_HEAD_VERIFIER_MISSING")

    def test_legacy_unhyphenated_status_context_is_not_accepted(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["context"] = (
            "QIKVRT autonomous exact-head verification"
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXACT_HEAD_VERIFIER_MISSING")

    def test_verifier_status_must_target_the_candidate_head(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["sha"] = "c" * 40
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(
            result["first_blocker"], "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH"
        )

    def test_verifier_status_must_bind_current_pr_and_base(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["description"] = (
            "Exact-head verified: pr=458; base=" + "a" * 40
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(
            result["first_blocker"], "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH"
        )

    def test_verifier_status_must_link_to_its_exact_workflow_run(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["workflow_run"]["html_url"] = (
            "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/1"
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(
            result["first_blocker"], "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH"
        )

    def test_verifier_workflow_identity_and_main_binding_are_required(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["workflow_run"]["path"] = (
            ".github/workflows/untrusted.yml"
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(
            result["first_blocker"], "EXACT_HEAD_VERIFIER_UNTRUSTED_WORKFLOW"
        )

    def test_verifier_run_must_be_bound_to_main_at_candidate_base(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["workflow_run"]["head_sha"] = "c" * 40
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(
            result["first_blocker"], "EXACT_HEAD_VERIFIER_UNTRUSTED_WORKFLOW"
        )

    def test_non_dispatch_exact_head_verifier_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["workflow_run"]["event"] = "pull_request"
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXACT_HEAD_VERIFIER_UNTRUSTED_EVENT")

    def test_non_green_exact_head_verifier_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["exact_head_verifier_statuses"][0]["state"] = "failure"
        snapshot["exact_head_verifier_statuses"][0]["description"] = (
            "Exact-head blocked: pr=459; base=" + "a" * 40
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXACT_HEAD_VERIFIER_NOT_GREEN")

    def test_newest_canonical_verifier_status_supersedes_older_success(self) -> None:
        snapshot = self.snapshot()
        older = self.exact_head_verifier_status(id=910)
        newest = self.exact_head_verifier_status(
            id=911,
            state="failure",
            description="Exact-head blocked: pr=459; base=" + "a" * 40,
        )
        snapshot["exact_head_verifier_statuses"] = [older, newest]
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXACT_HEAD_VERIFIER_NOT_GREEN")


if __name__ == "__main__":
    unittest.main()
