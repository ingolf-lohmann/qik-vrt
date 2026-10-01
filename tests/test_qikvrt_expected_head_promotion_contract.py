# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import ast
import json
import pathlib
import re
import unittest

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
        programs = re.findall(r"<<'PY'[^\\n]*\\n(.*?)\\n\\s*PY(?:\\n|$)", workflow, re.DOTALL)
        trees = [ast.parse(program) for program in programs]

        def call_chain(node, names):
            current = node
            for name in reversed(names):
                if not (
                    isinstance(current, ast.Call)
                    and isinstance(current.func, ast.Attribute)
                    and current.func.attr == "get"
                    and current.args
                    and isinstance(current.args[0], ast.Constant)
                    and current.args[0].value == name
                ):
                    return False
                current = current.func.value
            return isinstance(current, ast.Name) and current.id == "other"

        def has_guard(names, operator, rhs):
            return any(
                isinstance(node, ast.Compare)
                and len(node.ops) == 1
                and isinstance(node.ops[0], operator)
                and call_chain(node.left, names)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Name)
                and node.comparators[0].id == rhs
                for tree in trees
                for node in ast.walk(tree)
            )

        self.assertTrue(has_guard(("base", "sha"), ast.NotEq, "current_main"))
        self.assertTrue(has_guard(("head", "sha"), ast.Eq, "head"))

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
