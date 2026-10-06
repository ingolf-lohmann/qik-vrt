# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import copy
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
            "user": {"login": "ingolf-lohmann"},
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

    def test_former_authority_review_cannot_replace_current_human_owner(self):
        result = self.evaluate([self.approval(user={"login": "Goldkelch"})])
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_MISSING")

    def test_actual_policy_and_codeowners_resolve_current_mesh_human(self):
        self.assertEqual(MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt"), "ingolf-lohmann")

    def test_unknown_or_former_repository_does_not_inherit_current_authority(self):
        for repository in ("Goldkelch/qik-vrt", "foreign/qik-vrt", ""):
            with self.subTest(repository=repository), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner(repository)

    def test_policy_codeowners_disagreement_never_falls_back_to_former_owner(self):
        for codeowners in ("* @Goldkelch", "* @ingolf-lohmann\n/runtime/ @Goldkelch", "", "* @ingolf-lohmann @Goldkelch"):
            with self.subTest(codeowners=codeowners), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", codeowners=codeowners)

    def test_missing_or_collapsed_authority_roles_fail_closed(self):
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        for field in ("human", "executor", "repository"):
            candidate = copy.deepcopy(policy)
            del candidate["mesh_authority"][field]
            with self.subTest(field=field), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", policy=candidate)
        for role in ("executor", "repository"):
            candidate = copy.deepcopy(policy)
            candidate["mesh_authority"][role]["may_submit_native_approve"] = True
            with self.subTest(role=role), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", policy=candidate)

    def test_authority_cannot_disable_independence_or_assign_bot_owner(self):
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        candidate = copy.deepcopy(policy)
        candidate["mesh_authority"]["independent_native_code_owner_review_required"] = False
        with self.assertRaises(MODULE.ReviewGateInputError):
            MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", policy=candidate)
        candidate = copy.deepcopy(policy)
        candidate["mesh_authority"]["human"]["github_login"] = "github-actions[bot]"
        with self.assertRaises(MODULE.ReviewGateInputError):
            MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", policy=candidate, codeowners="* @github-actions[bot]")

    def test_owner_comment_is_authorization_without_native_approval(self):
        self.assertEqual(self.projection(reviews=[self.approval(state="COMMENTED")])["first_blocker"], "CODE_OWNER_REVIEW_NOT_APPROVED")

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
        result = self.evaluate([self.approval()], pr=self.pr(user={"login": "ingolf-lohmann"}))
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
        self.assertEqual(self.projection(pr=self.pr(user={"login": "ingolf-lohmann"}))["first_blocker"], "CODE_OWNER_REVIEW_SELF_APPROVAL")

    def test_automated_approval_cannot_be_promoted_by_green_status(self):
        result = self.projection(reviews=[self.approval(user={"login": "ingolf-lohmann", "type": "Bot"})])
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
            env = {"REPOSITORY": "ingolf-lohmann/qik-vrt", "REQUESTED_PR": "641", "EVENT_NAME": "workflow_dispatch", "EVENT_PRS": "[]", "REQUIRED_CODE_OWNER": "ingolf-lohmann", "STATUS_CONTEXT": MODULE.GOVERNANCE_STATUS_CONTEXT, "LEGACY_STATUS_CONTEXT": MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT, "GITHUB_STEP_SUMMARY": str(pathlib.Path(directory) / "summary"), "GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "123"}
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
        env = {"REPOSITORY": "ingolf-lohmann/qik-vrt", "PR_NUMBER": "641", "EXPECTED_HEAD": self.head}
        namespace = {}
        with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read):
            exec(compile(source, "live-projection-workflow", "exec"), namespace)
        self.assertEqual(namespace["projection"]["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")
        self.assertEqual(namespace["projection"]["acceptance"], "BLOCKED")

    def test_actual_writer_binds_current_authority_before_any_admin_effect(self):
        source = self.embedded_python("qikvrt_goldkelch_ruleset_authority_effect.yml", "python3 -B - <<'PY'\n")
        with patch.dict(os.environ, {"TARGET_REPOSITORY": "ingolf-lohmann/qik-vrt"}), patch("subprocess.check_call") as write:
            namespace = {}
            exec(compile(source, "writer-authority-binding", "exec"), namespace)
            self.assertEqual(namespace["owner"], "ingolf-lohmann")
            write.assert_not_called()
        with patch.dict(os.environ, {"TARGET_REPOSITORY": "foreign/qik-vrt"}), self.assertRaisesRegex(ValueError, "outside the current Mesh Authority binding"):
            exec(compile(source, "writer-authority-binding", "exec"), {})

    def test_actual_executor_rejects_foreign_authority_before_repository_reads(self):
        source = self.embedded_python("qikvrt_requested_review_executor.yml", "python3 -B - <<'PY' > /tmp/qikvrt-review-selection.json\n")
        env = {"REPOSITORY": "foreign/qik-vrt", "REQUESTED_PR": "", "EVENT_PR": "", "EVENT_HEAD": "", "REVIEW_MARKER": "fixture-only"}
        with patch.dict(os.environ, env), patch("subprocess.check_output") as read, self.assertRaisesRegex(ValueError, "outside the current Mesh Authority binding"):
            exec(compile(source, "executor-authority-binding", "exec"), {})
        read.assert_not_called()

    def test_actual_publisher_accepts_current_owner_independent_native_review(self):
        source = self.embedded_python("qikvrt_required_review_gate.yml", "python3 -B - <<'PY'\n")
        posts = []
        pr = self.pr(base={"sha": "a" * 40, "ref": "main"}, state="open")
        def read(command, **kwargs):
            path = command[-1]
            if path.endswith("/pulls/641"): return json.dumps(pr)
            if path.endswith("/rules/branches/main"): return json.dumps(self.enforced_rules())
            if "/reviews?" in path: return json.dumps([[self.approval()]])
            self.fail(f"unexpected API read: {command}")
        with tempfile.TemporaryDirectory() as directory:
            env = {"REPOSITORY": "ingolf-lohmann/qik-vrt", "REQUESTED_PR": "641", "EVENT_NAME": "workflow_dispatch", "EVENT_PRS": "[]", "STATUS_CONTEXT": MODULE.GOVERNANCE_STATUS_CONTEXT, "LEGACY_STATUS_CONTEXT": MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT, "GITHUB_STEP_SUMMARY": str(pathlib.Path(directory) / "summary"), "GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "123"}
            with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read), patch("subprocess.check_call", side_effect=lambda command: posts.append(command)):
                namespace = {}
                exec(compile(source, "publisher-current-owner", "exec"), namespace)
            self.assertEqual(len(posts), 2)
            self.assertTrue(all("state=success" in post for post in posts))
            self.assertEqual(namespace['decision']['required_code_owner'], 'ingolf-lohmann')


if __name__ == "__main__":
    unittest.main()
