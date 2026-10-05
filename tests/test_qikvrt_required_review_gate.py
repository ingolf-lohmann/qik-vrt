# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import json
import os
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_required_review_gate",
    ROOT / "tools/qikvrt_required_review_gate.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequiredCodeOwnerReviewGateTests(unittest.TestCase):
    head = "b" * 40

    def pr(self, **overrides):
        value = {"number": 641, "head": {"sha": self.head}, "user": {"login": "integration-author"}}
        value.update(overrides)
        return value

    def enforced_rules(self):
        return [{"type": "pull_request", "parameters": {
            "required_approving_review_count": 1,
            "require_code_owner_review": True,
            "dismiss_stale_reviews_on_push": True,
            "require_last_push_approval": True,
        }}]

    def approval(self, **overrides):
        value = {
            "id": 3,
            "submitted_at": "2026-08-16T16:00:00Z",
            "state": "APPROVED",
            "commit_id": self.head,
            "user": {"login": "Goldkelch"},
        }
        value.update(overrides)
        return value

    def evaluate(self, reviews, *, rules=None, pr=None):
        return MODULE.evaluate_required_review(
            self.pr() if pr is None else pr,
            self.enforced_rules() if rules is None else rules,
            reviews,
        )

    def test_native_rule_must_enforce_all_freshness_requirements(self):
        weak = self.enforced_rules(); weak[0]["parameters"]["require_code_owner_review"] = False
        result = self.evaluate([], rules=weak)
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_RULE_NOT_ENFORCED"))

    def test_native_rule_requires_stale_dismissal_and_last_push_approval(self):
        for field in ("dismiss_stale_reviews_on_push", "require_last_push_approval"):
            with self.subTest(field=field):
                weak = self.enforced_rules(); weak[0]["parameters"][field] = False
                result = self.evaluate([], rules=weak)
                self.assertEqual(result["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_no_review_is_pending_not_approval(self):
        result = self.evaluate([])
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("pending", "CODE_OWNER_REVIEW_MISSING"))

    def test_wrong_reviewer_cannot_satisfy_gate(self):
        result = self.evaluate([self.approval(user={"login": "someone-else"})])
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_MISSING")

    def test_old_head_approval_is_stale(self):
        result = self.evaluate([self.approval(commit_id="a" * 40)])
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_STALE")

    def test_exact_head_approval_passes(self):
        result = self.evaluate([self.approval()])
        self.assertEqual(result["gate_state"], "success")
        self.assertEqual(result["head_sha"], self.head)
        self.assertIsNone(result["first_blocker"])

    def test_current_head_changes_requested_supersedes_prior_approval(self):
        result = self.evaluate([
            self.approval(id=3, submitted_at="2026-08-16T16:00:00Z"),
            self.approval(id=4, submitted_at="2026-08-16T16:01:00Z", state="CHANGES_REQUESTED"),
        ])
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_REVIEW_CHANGES_REQUESTED"))

    def test_dismissed_exact_head_review_requires_new_approval(self):
        result = self.evaluate([self.approval(state="DISMISSED")])
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_DISMISSED")

    def test_pr_author_cannot_satisfy_independent_gate(self):
        result = self.evaluate([self.approval()], pr=self.pr(user={"login": "Goldkelch"}))
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_REVIEW_SELF_APPROVAL"))

    def statuses(self, state="success"):
        return [{"id": 4, "context": MODULE.GOVERNANCE_STATUS_CONTEXT, "state": state, "created_at": "2026-10-05T11:00:00Z"}]

    def projection(self, *, pr=None, rules=None, reviews=None, statuses=None):
        return MODULE.project_governance(
            self.pr() if pr is None else pr,
            self.enforced_rules() if rules is None else rules,
            [self.approval()] if reviews is None else reviews,
            self.statuses() if statuses is None else statuses,
        )

    def test_green_execution_or_status_cannot_supply_native_enforcement(self):
        result = self.projection(rules=[])
        self.assertEqual((result["acceptance"], result["first_blocker"]), ("BLOCKED", "CODE_OWNER_RULE_NOT_ENFORCED"))
        self.assertFalse(result["execution_success_implies_enforcement"])
        self.assertFalse(result["execution_success_implies_independent_approval"])
        self.assertFalse(any(result["completion_claims"].values()))

    def test_green_status_cannot_supply_a_missing_or_stale_review(self):
        for reviews, blocker in (([], "CODE_OWNER_REVIEW_MISSING"), ([self.approval(commit_id="a" * 40)], "CODE_OWNER_REVIEW_STALE")):
            with self.subTest(blocker=blocker):
                result = self.projection(reviews=reviews)
                self.assertEqual((result["acceptance"], result["first_blocker"]), ("BLOCKED", blocker))

    def test_self_approval_cannot_be_promoted_by_green_status(self):
        self.assertEqual(self.projection(pr=self.pr(user={"login": "Goldkelch"}))["first_blocker"], "CODE_OWNER_REVIEW_SELF_APPROVAL")

    def test_automated_approval_cannot_be_promoted_by_green_status(self):
        result = self.projection(reviews=[self.approval(user={"login": "Goldkelch", "type": "Bot"})])
        self.assertEqual((result["acceptance"], result["first_blocker"]), ("BLOCKED", "CODE_OWNER_REVIEW_AUTOMATED_APPROVAL"))

    def test_legacy_and_technical_success_do_not_replace_native_status(self):
        for context in (MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT, MODULE.REVIEW_DISPOSITION_STATUS_CONTEXT):
            with self.subTest(context=context):
                statuses = self.statuses(); statuses[0]["context"] = context
                self.assertEqual(self.projection(statuses=statuses)["first_blocker"], "NATIVE_GOVERNANCE_STATUS_MISSING")

    def test_newest_failed_native_status_supersedes_old_success(self):
        statuses = self.statuses() + [{"id": 5, "context": MODULE.GOVERNANCE_STATUS_CONTEXT, "state": "failure", "created_at": "2026-10-05T11:01:00Z"}]
        for order in (statuses, list(reversed(statuses))):
            self.assertEqual(self.projection(statuses=order)["first_blocker"], "NATIVE_GOVERNANCE_STATUS_NOT_SUCCESSFUL")

    def test_disagreeing_legacy_status_keeps_acceptance_closed(self):
        statuses = self.statuses() + [{"id": 5, "context": MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT, "state": "failure"}]
        self.assertEqual(self.projection(statuses=statuses)["first_blocker"], "GOVERNANCE_STATUS_DISAGREEMENT")

    def test_native_approval_and_matching_publication_satisfy_only_native_scope(self):
        result = self.projection()
        self.assertEqual(result["acceptance"], "NATIVE_GOVERNANCE_SATISFIED")
        self.assertFalse(any(result["completion_claims"].values()))

    def embedded_python(self, filename, start):
        source = (ROOT / ".github/workflows" / filename).read_text()
        return textwrap.dedent(source.split(start, 1)[1].split("\n          PY", 1)[0])

    def test_actual_publisher_writes_one_native_decision_to_both_contexts(self):
        source = self.embedded_python("qikvrt_required_review_gate.yml", "python3 -B - <<'PY'\n")
        posts = []
        pr = self.pr(base={"sha": "a" * 40, "ref": "main"}, state="open")
        def read(command, **kwargs):
            path = command[-1]
            if path.endswith("/pulls/641"): return json.dumps(pr)
            if path.endswith("/rules/branches/main"): return "[]"
            if "/reviews?" in path: return "[[]]"
            self.fail(f"unexpected API read: {command}")
        with tempfile.TemporaryDirectory() as directory:
            env = {"REPOSITORY": "example/qik-vrt", "REQUESTED_PR": "641", "EVENT_NAME": "workflow_dispatch", "EVENT_PRS": "[]", "REQUIRED_CODE_OWNER": "Goldkelch", "STATUS_CONTEXT": MODULE.GOVERNANCE_STATUS_CONTEXT, "LEGACY_STATUS_CONTEXT": MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT, "GITHUB_STEP_SUMMARY": str(pathlib.Path(directory) / "summary"), "GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "123"}
            with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read), patch("subprocess.check_call", side_effect=lambda command: posts.append(command)):
                exec(compile(source, "publisher-workflow", "exec"), {})
            self.assertEqual(len(posts), 2)
            for command in posts:
                self.assertIn("state=failure", command)
                self.assertIn("description=failure: CODE_OWNER_RULE_NOT_ENFORCED", command)
                self.assertTrue(command[4].endswith("/statuses/" + self.head))
                self.assertFalse(any("/reviews" in arg for arg in command))
            self.assertIn("CODE_OWNER_RULE_NOT_ENFORCED", pathlib.Path(env["GITHUB_STEP_SUMMARY"]).read_text())

    def test_actual_live_projection_reads_native_evidence_despite_green_telemetry(self):
        source = self.embedded_python("qikvrt_live_status_watch.yml", "python3 -B - <<'PY'\n")
        pr = self.pr(base={"sha": "a" * 40, "ref": "main"}, state="open")
        def read(command, **kwargs):
            path = command[-1]
            if path.endswith("/pulls/641"): return json.dumps(pr)
            if path.endswith("/rules/branches/main"): return "[]"
            if "/reviews?" in path: return "[[]]"
            if "/statuses?" in path: return json.dumps([self.statuses()])
            self.fail(f"unexpected API read: {command}")
        env = {"REPOSITORY": "example/qik-vrt", "PR_NUMBER": "641", "EXPECTED_HEAD": self.head}
        namespace = {}
        with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read):
            exec(compile(source, "live-projection-workflow", "exec"), namespace)
        self.assertEqual(namespace["projection"]["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")
        self.assertEqual(namespace["projection"]["acceptance"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
