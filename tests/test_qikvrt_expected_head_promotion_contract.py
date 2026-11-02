# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import contextlib
import io
import os
import pathlib
import subprocess
import unittest
from unittest import mock

from tools import qikvrt_self_heal_pr_materializer as materializer

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
PROMOTION_WORKFLOW = ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml"
SELF_HEAL_WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_self_heal.yml"
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
        self.assertIsNone(executor["schedule_fallback"])
        self.assertEqual(
            executor["two_phase_promotion"],
            ["DRAFT_TO_READY", "STOP_AND_REOBSERVE", "EXPECTED_HEAD_BOUND_MERGE"],
        )
        self.assertEqual(
            executor["merge_binding"],
            "GITHUB_GRAPHQL_UPDATE_REFS_BEFORE_OID",
        )
        self.assertFalse(executor["same_head_verification_proxy_is_competing_writer"])
        self.assertFalse(executor["stale_base_pull_request_is_current_competing_writer"])
        self.assertTrue(executor["current_base_overlapping_pull_request_is_competing_writer"])
        self.assertEqual(executor["external_effect"], "FORBIDDEN")

    def test_self_heal_candidates_opt_in_to_executor(self) -> None:
        workflow = SELF_HEAL_WORKFLOW.read_text(encoding="utf-8")
        # #502 moved PR body construction from inline YAML into the existing
        # REST materializer. Bind the active producer; the behavioral suite
        # separately checks the actual newly created Draft PR body.
        self.assertEqual(materializer.MARKER, MARKER)
        self.assertIn("python3 -B -m tools.qikvrt_self_heal_pr_materializer", workflow)
        self.assertIn("tests.test_qikvrt_expected_head_promotion", workflow)
        self.assertIn("tests.test_qikvrt_self_heal_pr_materializer", workflow)
        self.assertIn("It never merges, approves", materializer.__doc__)

    def test_executor_is_bounded_and_sha_bound(self) -> None:
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn('  schedule:', workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("READY_RECLASSIFIED_REOBSERVATION_REQUIRED", workflow)
        self.assertIn('exit 0', workflow)
        self.assertIn("publish-graphql", workflow)
        self.assertIn("--attempt-file /tmp/qikvrt-promotion-cas-attempt.json", workflow)
        self.assertNotIn("repos/${REPOSITORY}/pulls/${PR_NUMBER}/merge", workflow)
        self.assertNotIn("--method PUT", workflow)
        self.assertIn("other.get('base',{}).get('sha') != current_main", workflow)
        self.assertIn("other.get('head',{}).get('sha') == head", workflow)

    def test_missing_main_ref_cas_is_an_explicit_hold_boundary(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        boundary = contract["promotion_executor"]["target_ref_publication"]
        self.assertTrue(boundary["atomic_expected_old_head_required"])
        self.assertEqual(boundary["current_target_ref_cas_capability"], "UNAVAILABLE")
        self.assertEqual(boundary["unverified_cas_disposition"], "HOLD")
        self.assertFalse(boundary["covers_other_writers"])
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("qualify_target_ref_cas(snapshot,qualification)", workflow)
        self.assertIn('CAS_AUTOMATIC_MAIN_PROMOTION: "false"', workflow)
        self.assertIn("env.CAS_AUTOMATIC_MAIN_PROMOTION == 'true'", workflow)
        self.assertFalse(contract["promotion_executor"]["automatic_main_promotion_enabled"])
        qualification = json.loads((ROOT / boundary["qualification_path"]).read_text())
        self.assertEqual(qualification["state"], "UNAVAILABLE")
        self.assertFalse(qualification["native_governance_independently_verified"])
        self.assertNotIn('test "$promoted_main" != "$EXPECTED_BASE"', workflow)

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

    def embedded_python(self):
        lines = PROMOTION_WORKFLOW.read_text().splitlines()
        blocks = []
        current = None
        for line in lines:
            if "<<'PY'" in line:
                current = []
            elif current is not None and line.strip() == "PY":
                blocks.append("\n".join(x[10:] for x in current) + "\n")
                current = None
            elif current is not None:
                current.append(line)
        self.assertIsNone(current)
        return blocks

    def test_every_embedded_workflow_python_block_compiles(self):
        blocks = self.embedded_python()
        self.assertEqual(len(blocks), 8)
        for index, code in enumerate(blocks):
            compile(code, f"workflow-block-{index}", "exec")

    def test_workflow_snapshot_executes_with_unavailable_trusted_qualification(self):
        code = next(c for c in self.embedded_python() if "snapshot={" in c)
        pr = {"number": 459, "head": {"sha": "b" * 40}, "base": {"sha": "a" * 40},
              "draft": True, "mergeable": True, "user": {"login": "fixture-integration-author"}}
        def read(command, **kwargs):
            path = command[-1]
            if "--paginate" in command:
                return json.dumps([{"workflow_runs": []}] if "/actions/runs?" in path else [[]])
            if path.endswith("/pulls/459"):
                return json.dumps(pr)
            if path.endswith("/commits/main"):
                return json.dumps({"sha": "a" * 40})
            if "/rules/branches/main" in path:
                return json.dumps([])
            if "/git/commits/" in path:
                return json.dumps({"tree": {"sha": "d" * 40}})
            raise AssertionError("unexpected snapshot read " + path)
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"REPOSITORY": "ingolf-lohmann/qik-vrt", "PR_NUMBER": "459",
                "REQUIRED_GATES_JSON": '["QIKVRT CI"]', "REVIEW_STATUS_CONTEXT": "QIKVRT required code-owner review"}), \
                mock.patch.object(subprocess, "check_output", side_effect=read), contextlib.redirect_stdout(output):
            exec(compile(code, "workflow-snapshot", "exec"), {})
        snapshot = json.loads(output.getvalue())
        self.assertEqual(snapshot["target_ref_cas"]["state"], "UNAVAILABLE")
        self.assertEqual(snapshot["expected_tree_sha"], "d" * 40)
        self.assertFalse(snapshot["target_ref_cas"]["server_atomic_compare_and_update"])
        self.assertEqual(snapshot["governance_projection"]["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")


if __name__ == "__main__":
    unittest.main()
