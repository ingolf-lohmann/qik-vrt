# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
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
from tools.qikvrt_required_review_gate import project_governance, GOVERNANCE_STATUS_CONTEXT


class ExpectedHeadPromotionTests(unittest.TestCase):
    def snapshot(self, **overrides):
        native_pr = {"number": 459, "head": {"sha": "b" * 40}, "base": {"sha": "a" * 40}, "user": {"login": "integration-author"}}
        rules = [{"type": "pull_request", "parameters": {"required_approving_review_count": 1, "require_code_owner_review": True, "dismiss_stale_reviews_on_push": True, "require_last_push_approval": True}}]
        reviews = [{"id": 7, "submitted_at": "2026-10-05T11:00:00Z", "state": "APPROVED", "commit_id": "b" * 40, "user": {"login": "ingolf-lohmann"}}]
        statuses = [{"id": 8, "context": GOVERNANCE_STATUS_CONTEXT, "state": "success"}]
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
            "governance_projection": project_governance(native_pr, rules, reviews, statuses),
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

    def test_green_observer_executor_and_legacy_status_do_not_replace_native_evidence(self):
        snapshot = self.snapshot()
        snapshot.pop("governance_projection")
        snapshot["workflow_runs"].extend([
            {"name": name, "status": "completed", "conclusion": "success", "run_number": 99}
            for name in ("QIKVRT code-owner review observer", "QIKVRT requested review executor", "QIKVRT requested review execution")
        ])
        self.assertEqual(MODULE.evaluate_promotion(snapshot)["first_blocker"], "NATIVE_GOVERNANCE_EVIDENCE_MISSING")

    def test_blocked_native_evidence_remains_blocked_when_execution_is_green(self):
        snapshot = self.snapshot()
        snapshot["governance_projection"].update(gate_state="failure", acceptance="BLOCKED", first_blocker="CODE_OWNER_RULE_NOT_ENFORCED")
        self.assertEqual(MODULE.evaluate_promotion(snapshot)["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_predecessor_governance_evidence_cannot_transfer(self):
        for field, value in (("head_sha", "c" * 40), ("base_sha", "c" * 40), ("pr_number", 448)):
            with self.subTest(field=field):
                snapshot = self.snapshot(); snapshot["governance_projection"][field] = value
                self.assertEqual(MODULE.evaluate_promotion(snapshot)["first_blocker"], "NATIVE_GOVERNANCE_EVIDENCE_MISMATCH")

    def test_actual_promotion_shell_stops_before_ready_or_merge_when_native_evidence_changes(self):
        workflow = (ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml").read_text()
        step = workflow.split("      - name: Reobserve exact unchanged head and advance one promotion phase", 1)[1].split("      - name:", 1)[0]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        for draft in (True, False):
            with self.subTest(draft=draft), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                pr = {"number": 459, "head": {"sha": "b" * 40}, "base": {"sha": "a" * 40}, "user": {"login": "integration-author"}, "draft": draft, "merged": False}
                (root / "pr.json").write_text(json.dumps(pr))
                mock = root / "gh"
                mock.write_text(f"#!{sys.executable}\n" + textwrap.dedent('''\
                    import json, os, sys
                    from pathlib import Path
                    args=sys.argv[1:]
                    with open(os.environ['MOCK_API_LOG'],'a') as stream:
                        stream.write(json.dumps(args)+'\\n')
                    if '--method' in args or args[:1] == ['pr']:
                        raise SystemExit('unexpected promotion mutation')
                    path=args[-1] if '--slurp' in args else args[1]
                    if path.endswith('/commits/main'):
                        value={'sha':'a'*40}
                    elif path.endswith('/pulls/459'):
                        value=json.loads(Path(os.environ['MOCK_PR']).read_text())
                    elif '/rules/branches/' in path:
                        value=[]
                    elif '/reviews?' in path:
                        value=[[]]
                    elif '/statuses?' in path:
                        value=[[{'id':8,'state':'success','context':'QIKVRT required code-owner review'}]]
                    else:
                        raise SystemExit('unexpected API read '+path)
                    if '--jq' in args:
                        for key in args[args.index('--jq')+1].strip('.').split('.'):
                            value=value[key]
                    if isinstance(value,str): print(value)
                    else: print(json.dumps(value))
                '''))
                mock.chmod(0o755)
                env = {**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"], "REPOSITORY": "ingolf-lohmann/qik-vrt", "PR_NUMBER": "459", "EXPECTED_BASE": "a" * 40, "EXPECTED_HEAD": "b" * 40, "MOCK_PR": str(root / "pr.json"), "MOCK_API_LOG": str(root / "api.jsonl")}
                result = subprocess.run(["bash", "-c", script], env=env, cwd=ROOT, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("CODE_OWNER_RULE_NOT_ENFORCED", result.stderr)
                calls = [json.loads(line) for line in (root / "api.jsonl").read_text().splitlines()]
                self.assertFalse(any('--method' in call or call[:1] == ['pr'] for call in calls))


if __name__ == "__main__":
    unittest.main()
