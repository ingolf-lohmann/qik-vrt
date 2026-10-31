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
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_executor",
    ROOT / "tools/qikvrt_requested_review_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequestedReviewExecutorTests(unittest.TestCase):
    def snapshot(self, **overrides):
        value = {
            "repository": "ingolf-lohmann/qik-vrt",
            "pr_number": 349,
            "current_main_sha": "a" * 40,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "observed_head_sha": "b" * 40,
            "tree_sha": "c" * 40,
            "draft": False,
            "requested_reviewers": ["ingolf-lohmann"],
            "requested_team_reviewers": [],
            "changed_paths": ["src/a.py", "tests/test_a.py"],
            "unresolved_review_threads": 0,
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
                {"name": "QIKVRT requested review executor", "status": "in_progress", "conclusion": None, "run_number": 1},
            ],
        }
        value.update(overrides)
        return value

    def test_terminal_green_requested_review_approves(self):
        result = MODULE.evaluate(self.snapshot())
        self.assertEqual(result["state"], "APPROVE")
        self.assertIsNone(result["first_blocker"])
        self.assertEqual(result["status_scope"], "TECHNICAL_DISPOSITION_ONLY")
        self.assertFalse(result["completion_claims"]["INDEPENDENT_CODE_OWNER_APPROVAL"])
        self.assertFalse(result["completion_claims"]["NATIVE_RULE_ENFORCEMENT"])

    def test_nonterminal_gate_waits_without_false_review(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "in_progress", "conclusion": None, "run_number": 11}
        )
        result = MODULE.evaluate(snap)
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_NOT_TERMINAL")

    def test_failed_gate_requests_changes(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "completed", "conclusion": "failure", "run_number": 11}
        )
        result = MODULE.evaluate(snap)
        self.assertEqual(result["state"], "REQUEST_CHANGES")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_FAILED")

    def test_head_drift_blocks(self):
        result = MODULE.evaluate(self.snapshot(observed_head_sha="d" * 40))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "HEAD_DRIFT")

    def test_base_drift_blocks(self):
        result = MODULE.evaluate(self.snapshot(current_main_sha="d" * 40))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")

    def test_unresolved_thread_blocks(self):
        result = MODULE.evaluate(self.snapshot(unresolved_review_threads=1))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "UNRESOLVED_REVIEW_THREADS")

    def test_draft_waits(self):
        result = MODULE.evaluate(self.snapshot(draft=True))
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "DRAFT")

    def test_no_active_request_is_noop_wait(self):
        result = MODULE.evaluate(self.snapshot(requested_reviewers=[]))
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "NO_ACTIVE_REVIEW_REQUEST")

    def test_native_route_reviews_without_copilot_or_requested_reviewers(self):
        result = MODULE.evaluate(self.snapshot(requested_reviewers=[], review_route="QIKVRT_NATIVE"))
        self.assertEqual(result["state"], "APPROVE")
        self.assertFalse(result["semantic_ai_review_performed"])
        self.assertFalse(result["completion_claims"]["INDEPENDENT_CODE_OWNER_APPROVAL"])
        self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])

    def test_native_route_preserves_required_checks_and_thread_unknown(self):
        snap = self.snapshot(requested_reviewers=[], review_route="QIKVRT_NATIVE")
        snap["workflow_runs"][0]["conclusion"] = "failure"
        self.assertEqual(MODULE.evaluate(snap)["first_blocker"], "REQUIRED_GATE_FAILED")
        snap["review_threads_complete"] = False
        self.assertEqual(MODULE.evaluate(snap)["first_blocker"], "REVIEW_THREAD_STATE_UNAVAILABLE")
        snap["draft"] = True
        self.assertEqual(MODULE.evaluate(snap)["first_blocker"], "DRAFT")

    def technical_review(self, head="b" * 40, actor="github-actions[bot]"):
        return {"commit_id": head, "user": {"login": actor},
                "body": f"<!-- fixture-review head={head} disposition=REQUEST_CHANGES -->\nOriginal failed evidence"}

    def status_for(self, plan):
        return {"id": 1, "created_at": "2026-10-26T15:00:00Z", "creator": {"login": "github-actions[bot]"},
                "context": MODULE.TECHNICAL_STATUS_CONTEXT, "state": plan["status_state"],
                "description": plan["status_description"]}

    def test_failed_review_recovery_updates_only_technical_status(self):
        plan = MODULE.technical_update_plan(self.snapshot(), [self.technical_review()], [], "fixture-review")
        self.assertEqual(plan["action"], "STATUS_ONLY")
        self.assertEqual(plan["status_state"], "success")
        self.assertFalse(plan["review_required"])
        self.assertFalse(plan["decision"]["completion_claims"]["INDEPENDENT_CODE_OWNER_APPROVAL"])
        self.assertLessEqual(len(plan["status_description"]), 140)

    def test_unchanged_evidence_and_unrelated_run_counters_are_noop(self):
        snapshot = self.snapshot()
        plan = MODULE.technical_update_plan(snapshot, [self.technical_review()], [], "fixture-review")
        for run in snapshot["workflow_runs"]: run["run_number"] += 100
        status = self.status_for(plan)
        status["created_at"] = "2026-10-27T00:00:00Z"
        again = MODULE.technical_update_plan(snapshot, [self.technical_review()], [status], "fixture-review")
        self.assertEqual(again["action"], "NOOP")
        self.assertEqual(again["evidence_sha256"], plan["evidence_sha256"])

    def test_regression_and_unavailable_execution_do_not_keep_stale_success(self):
        snapshot = self.snapshot(); reviews = [self.technical_review()]
        good = MODULE.technical_update_plan(snapshot, reviews, [], "fixture-review")
        snapshot["workflow_runs"][0]["conclusion"] = "failure"
        bad = MODULE.technical_update_plan(snapshot, reviews, [self.status_for(good)], "fixture-review")
        self.assertEqual((bad["action"], bad["status_state"]), ("STATUS_ONLY", "failure"))
        snapshot["workflow_runs"][0]["status"] = "in_progress"
        waiting = MODULE.technical_update_plan(snapshot, reviews, [self.status_for(good)], "fixture-review")
        self.assertEqual(waiting["status_state"], "pending")
        self.assertFalse(waiting["review_required"])

    def test_other_subject_or_untrusted_history_cannot_suppress_review(self):
        plan = MODULE.technical_update_plan(self.snapshot(), [self.technical_review()], [], "fixture-review")
        old_status = self.status_for(plan)
        for review in [self.technical_review("d" * 40), self.technical_review(actor="foreign")]:
            result = MODULE.technical_update_plan(self.snapshot(), [review], [old_status], "fixture-review")
            self.assertEqual(result["action"], "REVIEW_AND_STATUS")
        old_status["creator"] = {"login": "foreign"}
        self.assertEqual(MODULE.technical_update_plan(self.snapshot(), [self.technical_review()], [old_status], "fixture-review")["action"], "STATUS_ONLY")

    def test_drift_and_checker_failure_remain_blocked(self):
        snapshot = self.snapshot(observed_head_sha="d" * 40)
        plan = MODULE.technical_update_plan(snapshot, [self.technical_review()], [], "fixture-review")
        self.assertEqual(plan["status_state"], "failure")
        self.assertEqual(plan["decision"]["first_blocker"], "HEAD_DRIFT")
        with self.assertRaises(MODULE.ReviewSnapshotError):
            MODULE.technical_update_plan(self.snapshot(), None, [], "fixture-review")
        with self.assertRaises(MODULE.ReviewSnapshotError):
            MODULE.technical_update_plan(self.snapshot(workflow_runs=None), [], [], "fixture-review")
        with self.assertRaises(MODULE.ReviewSnapshotError):
            MODULE.technical_update_plan(self.snapshot(), [dict(self.technical_review(), user=None)], [], "fixture-review")

    def test_candidate_workflow_does_not_import_unpromoted_selector(self):
        from tools import qikvrt_requested_review_executor as core
        workflow = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text()
        step = workflow.split("      - name: Detect trusted-main activation", 1)[1].split("      - name:", 1)[0]
        source = textwrap.dedent(step.split("python3 -B - <<'PY'\n", 1)[1].split("          PY", 1)[0])
        with patch.object(core, "native_review_candidate", None), self.assertRaises(SystemExit) as result:
            exec(compile(source, "trusted-main-before-routing-promotion", "exec"), {})
        self.assertEqual(result.exception.code, 2)

    def test_actual_selection_admits_native_pr_without_review_request(self):
        workflow = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text()
        step = workflow.split("      - name: Select one requested review", 1)[1].split("      - name:", 1)[0]
        source = textwrap.dedent(step.split("          python3 -B - <<'PY' > /tmp/qikvrt-review-selection.json\n", 1)[1].split("          PY", 1)[0])
        pr = {"number": 586, "state": "open", "draft": False, "base": {"ref": "main"},
              "head": {"sha": "b" * 40}, "requested_reviewers": [], "requested_teams": []}
        calls = []
        def read(command, **kwargs):
            calls.append(command)
            path = command[-1]
            if "/pulls?" in path: return json.dumps([[pr]])
            if "/reviews?" in path: return "[[]]"
            self.fail(str(command))
        env = {"REPOSITORY": "ingolf-lohmann/qik-vrt", "REQUESTED_PR": "", "EVENT_PR": "", "EVENT_HEAD": "", "REVIEW_MARKER": "fixture-only"}
        output = StringIO()
        with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read), redirect_stdout(output):
            exec(compile(source, "actual-native-review-selection", "exec"), {})
        self.assertEqual(json.loads(output.getvalue())["pr_number"], 586)
        self.assertFalse(any("graphql" in arg for command in calls for arg in command))
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        self.assertFalse(MODULE.native_review_candidate(pr, policy, "foreign/qik-vrt"))
        for override in ({"draft": True}, {"state": "closed"}, {"base": {"ref": "other"}}):
            self.assertFalse(MODULE.native_review_candidate({**pr, **override}, policy, env["REPOSITORY"]))
        policy["review_executor"]["provider_routing"]["enabled"] = False
        self.assertFalse(MODULE.native_review_candidate(pr, policy, env["REPOSITORY"]))

    def test_actual_selection_reenters_recovered_review_and_then_is_noop(self):
        workflow = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text()
        step = workflow.split("      - name: Select one requested review", 1)[1].split("      - name:", 1)[0]
        source = textwrap.dedent(step.split("          python3 -B - <<'PY' > /tmp/qikvrt-review-selection.json\n", 1)[1].split("          PY", 1)[0])
        pr = {"number": 586, "state": "open", "draft": False, "base": {"ref": "main", "sha": "a" * 40},
              "head": {"sha": "b" * 40}, "requested_reviewers": [], "requested_teams": []}
        statuses = []
        def read(command, **kwargs):
            path = command[-1]
            if "/pulls?" in path: value = [[pr]]
            elif path.endswith("/pulls/586"): value = pr
            elif "/reviews?" in path: value = [[self.technical_review()]]
            elif "/statuses?" in path: value = [statuses]
            elif path.endswith("/commits/main"): value = {"sha": "a" * 40}
            elif "/git/commits/" in path: value = {"tree": {"sha": "c" * 40}}
            elif "/files?" in path: value = [[{"filename": p} for p in self.snapshot()["changed_paths"]]]
            elif "/comments?" in path: value = [[]]
            elif "/actions/runs?" in path: value = [{"workflow_runs": self.snapshot()["workflow_runs"]}]
            else: self.fail(path)
            return json.dumps(value)
        env = {"REPOSITORY": "ingolf-lohmann/qik-vrt", "REQUESTED_PR": "", "EVENT_PR": "", "EVENT_HEAD": "",
               "REVIEW_MARKER": "fixture-review", "REQUIRED_GATES_JSON": json.dumps(self.snapshot()["required_gates"])}
        with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read):
            output = StringIO()
            with redirect_stdout(output): exec(compile(source, "actual-recovered-selection", "exec"), {})
            self.assertEqual(json.loads(output.getvalue())["pr_number"], 586)
            snapshot = self.snapshot(pr_number=586, requested_reviewers=[], review_route="QIKVRT_NATIVE", review_threads_complete=True)
            plan = MODULE.technical_update_plan(snapshot, [self.technical_review()], [], "fixture-review")
            statuses.append(self.status_for(plan))
            output = StringIO()
            with redirect_stdout(output): exec(compile(source, "actual-unchanged-selection", "exec"), {})
            self.assertEqual(json.loads(output.getvalue())["state"], "NOOP")

    def exercise_actual_publication(self, plan, expected_reviews, ambiguous=None):
        workflow = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text()
        step = workflow.split("      - name: Persist substantive review disposition", 1)[1].split("      - name:", 1)[0]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for filename in ("decision.json", "plan.json", "body.md", "write.json", "write.err", "readback.json"):
                original = "/tmp/qikvrt-review-" + filename
                script = script.replace(original, str(root / filename))
            decision = plan["decision"]
            (root / "decision.json").write_text(json.dumps(decision))
            (root / "plan.json").write_text(json.dumps(plan))
            mock = root / "gh"
            mock.write_text(f"#!{sys.executable}\n" + textwrap.dedent('''\
                import json, os, sys
                args=sys.argv[1:]
                with open(os.environ['MOCK_API_LOG'],'a') as stream:
                    stream.write(json.dumps(args)+'\\n')
                if '--method' not in args:
                    if '/reviews?' in args[-1]:
                        body=open(os.environ['MOCK_REVIEW_BODY']).read().rstrip('\\n')
                        record={'commit_id':os.environ['EXPECTED_HEAD'],'body':body,'user':{'login':'github-actions[bot]'}}
                        print(json.dumps([[record]] if os.environ.get('MOCK_AMBIGUOUS')=='applied' else [[]]))
                    else: print(os.environ['EXPECTED_HEAD'])
                else:
                    if any(a.endswith('/reviews') for a in args) and os.environ.get('MOCK_AMBIGUOUS'): sys.exit(1)
                    print('{}')
            '''))
            mock.chmod(0o755)
            context = workflow.split("      STATUS_CONTEXT: ", 1)[1].splitlines()[0]
            env = {**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"], "PR_NUMBER": "349", "REPOSITORY": "ingolf-lohmann/qik-vrt", "EXPECTED_HEAD": "b" * 40, "EXPECTED_TREE": "c" * 40, "DISPOSITION": "APPROVE", "REVIEW_MARKER": "fixture-review", "STATUS_CONTEXT": context, "GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": "ingolf-lohmann/qik-vrt", "GITHUB_RUN_ID": "123", "MOCK_API_LOG": str(root / "api.jsonl")}
            env.update(MOCK_REVIEW_BODY=str(root / "body.md"), MOCK_AMBIGUOUS=ambiguous or "")
            result = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, ambiguous != "unapplied", result.stderr)
            calls = [json.loads(line) for line in (root / "api.jsonl").read_text().splitlines()]
            reviews = [call for call in calls if "--method" in call and any(path.endswith("/reviews") for path in call)]
            statuses = [call for call in calls if "--method" in call and any("/statuses/" in path for path in call)]
            self.assertEqual(len(reviews), expected_reviews)
            if reviews:
                self.assertIn("event=COMMENT", reviews[0])
                self.assertNotIn("event=APPROVE", reviews[0])
            self.assertEqual(context, "QIKVRT requested review disposition")
            self.assertEqual(len(statuses), 0 if ambiguous == "unapplied" else 1)
            if statuses:
                self.assertIn("context=" + context, statuses[0])
                self.assertFalse(any("context=QIKVRT required code-owner review" == arg or "context=QIKVRT requested review execution" == arg for arg in statuses[0]))

    def test_actual_automated_approve_disposition_is_comment_in_separate_context(self):
        self.exercise_actual_publication(MODULE.technical_update_plan(self.snapshot(), [], [], "fixture-review"), 1)

    def test_actual_recovered_status_makes_no_second_review(self):
        plan = MODULE.technical_update_plan(self.snapshot(), [self.technical_review()], [], "fixture-review")
        self.exercise_actual_publication(plan, 0)

    def test_actual_lost_review_response_is_resolved_by_readback_only(self):
        plan = MODULE.technical_update_plan(self.snapshot(), [], [], "fixture-review")
        self.exercise_actual_publication(plan, 1, ambiguous="applied")
        self.exercise_actual_publication(plan, 1, ambiguous="unapplied")


if __name__ == "__main__":
    unittest.main()
