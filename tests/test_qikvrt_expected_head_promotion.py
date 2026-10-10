# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import copy
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
    def snapshot(self, **overrides):
        value = {
            "pr_number": 459,
            "repository": "ingolf-lohmann/qik-vrt",
            "expected_tree_sha": "d" * 40,
            "target_ref_cas": {
                "state": "VERIFIED",
                "repository": "ingolf-lohmann/qik-vrt",
                "ref": "refs/heads/main",
                "operation": "SERVER_ATOMIC_REF_COMPARE_AND_SWAP",
                "comparison_scope": "TARGET_REF",
                "expected_old_sha": "a" * 40,
                "candidate_head_sha": "b" * 40,
                "server_atomic_compare_and_update": True,
                "force_update": False,
                "evidence_sha256": "e" * 64,
            },
            "current_main_sha": "a" * 40,
            "base_sha": "a" * 40,
            "expected_head_sha": "b" * 40,
            "current_head_sha": "b" * 40,
            "draft": True,
            "mergeable": True,
            "external_effect": "NONE",
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

    def test_green_gates_without_server_ref_cas_hold(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(target_ref_cas=None))
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "ATOMIC_TARGET_REF_CAS_UNVERIFIED")

    def test_pr_head_sha_precondition_is_not_main_ref_cas(self) -> None:
        value = self.snapshot()
        value["target_ref_cas"]["comparison_scope"] = "PR_HEAD"
        self.assertEqual(MODULE.evaluate_promotion(value)["state"], "HOLD")

    def test_cas_subject_capability_and_evidence_must_all_match(self) -> None:
        for key, wrong in [("repository", "Goldkelch/qik-vrt"), ("ref", "refs/heads/other"),
                           ("expected_old_sha", "f" * 40), ("candidate_head_sha", "f" * 40),
                           ("server_atomic_compare_and_update", False), ("force_update", True),
                           ("evidence_sha256", None), ("state", "UNAVAILABLE")]:
            with self.subTest(key=key):
                value = self.snapshot()
                value["target_ref_cas"][key] = wrong
                self.assertEqual(MODULE.evaluate_promotion(value)["state"], "HOLD")


class PublicationReadbackTests(unittest.TestCase):
    # VERIFICATION FIXTURE ONLY: this simulated capability is not live GitHub evidence.
    def publication(self):
        value = ExpectedHeadPromotionTests().snapshot()
        value["merge_response"] = {"merged": True, "sha": "c" * 40}
        return value

    def observations(self):
        ref = {"ref": "refs/heads/main", "object": {"type": "commit", "sha": "c" * 40}}
        commit = {"sha": "c" * 40, "tree": {"sha": "d" * 40},
                  "parents": [{"sha": "a" * 40}, {"sha": "b" * 40}]}
        return [copy.deepcopy(ref), commit, copy.deepcopy(ref)]

    def verify(self, values, snapshot=None):
        reads = []
        iterator = iter(values)
        def read(path):
            reads.append(path)
            return next(iterator)
        return MODULE.verify_publication_readback(snapshot or self.publication(), read), reads

    def test_ref_commit_ref_reads_bind_exact_tree_and_parents(self) -> None:
        result, reads = self.verify(self.observations())
        self.assertEqual(result["state"], "CONTINUE")
        self.assertEqual(reads, ["repos/ingolf-lohmann/qik-vrt/git/ref/heads/main",
                                "repos/ingolf-lohmann/qik-vrt/git/commits/" + "c" * 40,
                                "repos/ingolf-lohmann/qik-vrt/git/ref/heads/main"])
        self.assertFalse(result["completion_claims"]["PASS"])
        self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])

    def test_different_main_head_is_not_promotion_readback(self) -> None:
        for index in (0, 2):
            with self.subTest(index=index):
                values = self.observations()
                values[index]["object"]["sha"] = "f" * 40
                result, _ = self.verify(values)
                self.assertEqual(result["first_blocker"], "PUBLISHED_REF_HEAD_DRIFT")
                self.assertEqual(result["state"], "HOLD")

    def test_tag_or_wrong_ref_does_not_satisfy_commit_readback(self) -> None:
        for key, wrong in [("ref", "refs/heads/other"), ("object", {"type": "tag", "sha": "c" * 40})]:
            values = self.observations()
            values[2][key] = wrong
            result, _ = self.verify(values)
            self.assertEqual(result["state"], "HOLD")

    def test_changed_tree_and_wrong_parents_hold(self) -> None:
        values = self.observations()
        values[1]["tree"]["sha"] = "f" * 40
        result, _ = self.verify(values)
        self.assertEqual(result["first_blocker"], "PUBLISHED_COMMIT_TREE_MISMATCH")
        values = self.observations()
        values[1]["parents"][0]["sha"] = "f" * 40
        result, _ = self.verify(values)
        self.assertEqual(result["first_blocker"], "PUBLISHED_MERGE_PARENT_MISMATCH")

    def test_transport_ack_and_capability_failure_cannot_continue(self) -> None:
        value = self.publication()
        value["merge_response"] = {"merged": False, "sha": "c" * 40}
        result, reads = self.verify([], value)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(reads, [])
        value = self.publication()
        value["target_ref_cas"]["state"] = "UNAVAILABLE"
        result, reads = self.verify([], value)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(reads, [])

    def test_lost_readback_preserves_effect_identity_without_retry(self) -> None:
        calls = []
        def failed_read(path):
            calls.append(path)
            raise TimeoutError("injected readback outage")
        result = MODULE.verify_publication_readback(self.publication(), failed_read)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["published_head_sha"], "c" * 40)
        self.assertFalse(result["automatic_retry"])
        self.assertEqual(len(calls), 1)

    def test_malformed_provider_readback_holds(self) -> None:
        result, _ = self.verify([None, {}, {}])
        self.assertEqual(result["state"], "HOLD")


if __name__ == "__main__":
    unittest.main()
