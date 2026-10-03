# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import copy
import itertools
import contextlib
import io
import json
import os
import textwrap
from unittest import mock
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
    def legacy_snapshot(self, **overrides):
        value = {
            "pr_number": 459,
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

    def snapshot(self, **overrides):
        value = self.bound_snapshot()
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

    def bound_snapshot(self):
        value = self.legacy_snapshot()
        value.update(repository="ingolf-lohmann/qik-vrt",
                     expected_tree_sha="d" * 40, current_tree_sha="d" * 40)
        value["review_observation"] = {
            "pr": {"number": 459, "head": {"sha": "b" * 40,
                    "repo": {"full_name": value["repository"]}},
                    "base": {"sha": "a" * 40}, "user": {"login": "proposal-writer"}},
            "rules": [{"type": "pull_request", "parameters": {
                "required_approving_review_count": 1, "require_code_owner_review": True,
                "dismiss_stale_reviews_on_push": True, "require_last_push_approval": True}}],
            "reviews": [{"id": 7, "submitted_at": "2026-10-01T13:00:00Z",
                "state": "APPROVED", "commit_id": "b" * 40,
                "user": {"login": "Goldkelch"}}],
        }
        for index, run in enumerate(value["workflow_runs"], 1):
            run.update(id=index, run_attempt=1, head_sha="b" * 40,
                       repository={"full_name": value["repository"]}, event="pull_request",
                       pull_requests=[{"number": 459}],
                       jobs=[{"id": index, "run_id": index, "run_attempt": 1,
                              "head_sha": "b" * 40, "status": "completed",
                              "conclusion": "success", "steps": [{"number": 1,
                              "status": "completed", "conclusion": "success"}]}])
        return value

    def test_foreign_green_run_cannot_release_candidate(self):
        value = self.bound_snapshot()
        for field, foreign in (("head_sha", "c" * 40),
                ("repository", {"full_name": "other/repository"}),
                ("pull_requests", [{"number": 460}])):
            with self.subTest(field=field):
                probe = copy.deepcopy(value); probe["workflow_runs"][0][field] = foreign
                self.assertEqual(MODULE.evaluate_promotion(probe)["state"], "BLOCK")

    def test_zero_job_success_cannot_release_candidate(self):
        value = self.bound_snapshot(); value["workflow_runs"][0]["jobs"] = []
        self.assertEqual(MODULE.evaluate_promotion(value)["state"], "BLOCK")

    def test_self_approval_cannot_release_candidate(self):
        value = self.bound_snapshot(); value["review_observation"]["pr"]["user"]["login"] = "Goldkelch"
        self.assertEqual(MODULE.evaluate_promotion(value)["state"], "BLOCK")

    def test_unenforced_review_boundary_cannot_release_candidate(self):
        value = self.bound_snapshot(); value["review_observation"]["rules"] = []
        self.assertEqual(MODULE.evaluate_promotion(value)["state"], "BLOCK")

    def test_stale_review_cannot_release_candidate(self):
        value = self.bound_snapshot(); value["review_observation"]["reviews"][0]["commit_id"] = "c" * 40
        self.assertEqual(MODULE.evaluate_promotion(value)["state"], "BLOCK")

    def test_missing_binding_is_not_a_legacy_success(self):
        value = self.legacy_snapshot()
        try:
            result = MODULE.evaluate_promotion(value)
        except MODULE.PromotionBlock:
            return
        self.assertEqual(result["state"], "BLOCK")

    def test_new_attempt_cannot_borrow_old_attempt_success(self):
        value = self.snapshot()
        failed = copy.deepcopy(value["workflow_runs"][0])
        failed.update(run_attempt=2, conclusion="failure")
        value["workflow_runs"].insert(0, failed)
        self.assertEqual(MODULE.evaluate_promotion(value)["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN")

    def test_jobs_and_steps_cannot_borrow_another_execution(self):
        for field, invalid in (("run_id", 9), ("run_attempt", 2), ("head_sha", "c" * 40),
                               ("conclusion", "failure"), ("steps", [])):
            with self.subTest(field=field):
                value = self.snapshot(); value["workflow_runs"][0]["jobs"][0][field] = invalid
                self.assertEqual(MODULE.evaluate_promotion(value)["state"], "BLOCK")

    def test_duplicate_and_all_skipped_jobs_do_not_prove_execution(self):
        for duplicate in (True, False):
            value = self.snapshot(); job = value["workflow_runs"][0]["jobs"][0]
            if duplicate:
                value["workflow_runs"][0]["jobs"].append(copy.deepcopy(job))
            else:
                job["conclusion"] = "skipped"
            self.assertEqual(MODULE.evaluate_promotion(value)["state"], "BLOCK")

    def test_fresh_validation_rejects_changed_successor_tree(self):
        value = self.snapshot()
        self.assertEqual(MODULE.evaluate_promotion(value)["state"], "PROMOTABLE")
        value["current_tree_sha"] = "e" * 40
        self.assertEqual(MODULE.evaluate_promotion(value)["first_blocker"], "TREE_DRIFT")

    def test_all_1024_boundary_combinations_fail_closed(self):
        # Exhaustive finite experiment over ten declared perturbations of the
        # production evaluator. This is not a kernel proof or a live GitHub write.
        for bits in itertools.product((False, True), repeat=10):
            with self.subTest(bits=bits):
                value = self.snapshot()
                if bits[0]: value["current_head_sha"] = "c" * 40
                if bits[1]: value["current_main_sha"] = "c" * 40
                if bits[2]: value["current_tree_sha"] = "e" * 40
                if bits[3]: value["review_observation"]["pr"]["user"]["login"] = "Goldkelch"
                if bits[4]: value["review_observation"]["reviews"][0]["commit_id"] = "c" * 40
                if bits[5]: value["review_observation"]["rules"] = []
                if bits[6]: value["workflow_runs"][0]["jobs"] = []
                if bits[7]: value["workflow_runs"][0]["head_sha"] = "c" * 40
                if bits[8]: value["competing_writer_overlaps"] = [{"pr_number": 460, "paths": ["tools/example.py"]}]
                if bits[9]: value["workflow_runs"][0]["conclusion"] = "action_required"
                result = MODULE.evaluate_promotion(value)
                self.assertEqual(result["state"], "BLOCK" if any(bits) else "PROMOTABLE")
                self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])

    def test_actual_workflow_observer_preserves_raw_execution_and_review(self):
        source = (ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml").read_text()
        start = source.index("          cat > /tmp/qikvrt-promotion-observe.py <<'PY'\n")
        start = source.index("\n", start) + 1
        end = source.index("\n          PY", start)
        script = textwrap.dedent(source[start:end])
        bound = self.snapshot(); review = bound["review_observation"]
        review["pr"].update(draft=True, mergeable=True)
        calls = []

        def api(arguments, **kwargs):
            path = arguments[-1]; calls.append(path)
            prefix = "repos/ingolf-lohmann/qik-vrt/"
            self.assertTrue(path.startswith(prefix))
            relative = path[len(prefix):]
            if relative == "pulls/459": value = review["pr"]
            elif relative == "commits/main": value = {"sha": bound["base_sha"]}
            elif relative.startswith("git/commits/"): value = {"tree": {"sha": bound["expected_tree_sha"]}}
            elif relative.startswith("actions/runs?"): value = {"workflow_runs": bound["workflow_runs"]}
            elif relative.startswith("actions/runs/"):
                run_id = int(relative.split("/")[2])
                self.assertIn("/attempts/1/jobs?", relative)
                value = {"jobs": next(r["jobs"] for r in bound["workflow_runs"] if r["id"] == run_id)}
            elif relative == "rules/branches/main": value = review["rules"]
            elif relative.startswith("pulls/459/reviews?"): value = review["reviews"]
            elif relative.startswith("pulls/459/files?"): value = [{"filename": "tools/qikvrt_expected_head_promotion.py"}]
            elif relative.startswith("pulls?"): value = [review["pr"]]
            else: self.fail(f"unexpected API read: {relative}")
            return json.dumps([value] if "--slurp" in arguments else value)

        output = io.StringIO()
        with mock.patch.dict(os.environ, {
            "REPOSITORY": bound["repository"], "PR_NUMBER": "459",
            "REQUIRED_GATES_JSON": json.dumps(bound["required_gates"])}), \
                mock.patch("subprocess.check_output", side_effect=api), \
                contextlib.redirect_stdout(output):
            exec(compile(script, "actual-workflow-observer", "exec"), {})
        observed = json.loads(output.getvalue())
        self.assertEqual(MODULE.evaluate_promotion(observed)["state"], "PROMOTABLE")
        self.assertIn("repos/ingolf-lohmann/qik-vrt/rules/branches/main", calls)
        self.assertEqual(observed["workflow_runs"][0]["jobs"], bound["workflow_runs"][0]["jobs"])
        # Revocation on the same head invalidates fresh semantic validation.
        observed["review_observation"]["reviews"] = []
        self.assertEqual(MODULE.evaluate_promotion(observed)["first_blocker"], "CODE_OWNER_REVIEW_MISSING")

    def test_workflow_shell_including_second_observation_is_valid(self):
        import subprocess
        source = (ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml").read_text()
        chunks = source.split("        run: |\n")[1:]
        for index, chunk in enumerate(chunks):
            script = textwrap.dedent(chunk.split("\n      - name:", 1)[0])
            result = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, f"step {index}: {result.stderr}")

    def test_malformed_observation_is_rejected(self):
        for field, invalid in (("repository", None), ("pull_requests", "459"), ("jobs", None)):
            value = self.snapshot(); value["workflow_runs"][0][field] = invalid
            self.assertEqual(MODULE.evaluate_promotion(value)["state"], "BLOCK")

    def test_merge_ack_needs_independent_exact_effect_readback(self):
        value = {
            "expected_head_sha": "b" * 40, "expected_base_sha": "a" * 40,
            "repository": "ingolf-lohmann/qik-vrt", "pr_number": 459,
            "expected_tree_sha": "d" * 40,
            "merge_response": {"merged": True, "sha": "e" * 40},
            "pull_request": {"number": 459, "merged": True, "merge_commit_sha": "e" * 40,
                             "head": {"sha": "b" * 40, "repo": {"full_name": "ingolf-lohmann/qik-vrt"}}},
            "main_commit": {"sha": "e" * 40, "tree": {"sha": "d" * 40},
                            "parents": [{"sha": "a" * 40}, {"sha": "b" * 40}]},
        }
        valid = MODULE.verify_promotion_readback(value)
        self.assertEqual(valid["state"], "PROMOTION_EFFECT_BOUND_REVALIDATION_PENDING")
        self.assertFalse(valid["completion_claims"]["EFFECT_ACK_DONE"])
        for subject, field, wrong in (("merge_response", "sha", "f" * 40),
                ("pull_request", "merged", False), ("pull_request", "merge_commit_sha", "f" * 40),
                ("pull_request", "number", 460),
                ("main_commit", "sha", "f" * 40), ("main_commit", "parents", [{"sha": "c" * 40}, {"sha": "b" * 40}])):
            with self.subTest(subject=subject, field=field):
                changed = copy.deepcopy(value); changed[subject][field] = wrong
                self.assertEqual(MODULE.verify_promotion_readback(changed)["state"], "HOLD")
        value["main_commit"]["tree"]["sha"] = "f" * 40
        changed_tree = MODULE.verify_promotion_readback(value)
        self.assertFalse(changed_tree["candidate_tree_matches"])
        self.assertEqual(changed_tree["fresh_main_validation"], "REQUIRED_NOT_ESTABLISHED_BY_MERGE")


if __name__ == "__main__":
    unittest.main()
