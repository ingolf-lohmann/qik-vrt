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

    def test_owner_authored_pr_uses_explicit_independent_review_delegate(self):
        reviewer = MODULE.resolve_required_code_owner(
            "ingolf-lohmann/qik-vrt", pr_author="ingolf-lohmann"
        )
        self.assertEqual(reviewer, "Goldkelch")
        result = MODULE.evaluate_required_review(
            self.pr(user={"login": "ingolf-lohmann"}),
            self.enforced_rules(),
            [self.approval(user={"login": reviewer, "type": "User"})],
            required_code_owner=reviewer,
        )
        self.assertEqual(result["gate_state"], "success")

    def test_delegate_authored_pr_requires_the_owner_instead(self):
        reviewer = MODULE.resolve_required_code_owner(
            "ingolf-lohmann/qik-vrt", pr_author="Goldkelch"
        )
        self.assertEqual(reviewer, "ingolf-lohmann")
        result = MODULE.evaluate_required_review(
            self.pr(user={"login": "Goldkelch"}),
            self.enforced_rules(), [self.approval()],
            required_code_owner=reviewer,
        )
        self.assertEqual(result["gate_state"], "success")

    def test_unknown_or_former_repository_does_not_inherit_current_authority(self):
        for repository in ("Goldkelch/qik-vrt", "foreign/qik-vrt", ""):
            with self.subTest(repository=repository), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner(repository)

    def test_policy_codeowners_disagreement_never_falls_back_to_former_owner(self):
        for codeowners in ("* @Goldkelch", "* @ingolf-lohmann\n/runtime/ @Goldkelch", "", "* @ingolf-lohmann", "* @ingolf-lohmann @someone-else"):
            with self.subTest(codeowners=codeowners), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", codeowners=codeowners)

    def test_shared_codeowners_cannot_invent_a_review_delegation(self):
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        del policy["mesh_authority"]["code_owner_review_delegation"]
        with self.assertRaises(MODULE.ReviewGateInputError):
            MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", policy=policy, codeowners="* @ingolf-lohmann @Goldkelch", pr_author="ingolf-lohmann")

    def test_delegate_requires_the_exact_active_owner_record(self):
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        for field, value in (("source_sha256", "0" * 64), ("state", "REVOKED"), ("delegate_login", "someone-else"), ("self_approval_allowed", True), ("native_approval_required", False), ("native_approval_required", 1), ("owner_final_authority_retained", False), ("automated_approval_can_substitute", True)):
            candidate = copy.deepcopy(policy)
            candidate["mesh_authority"]["code_owner_review_delegation"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", policy=candidate, pr_author="ingolf-lohmann")

    def test_delegate_does_not_replace_enforcement_freshness_or_native_approval(self):
        reviewer = MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", pr_author="ingolf-lohmann")
        pr = self.pr(user={"login": "ingolf-lohmann"})
        cases = [
            ([], [self.approval(user={"login": reviewer, "type": "User"})], "CODE_OWNER_RULE_NOT_ENFORCED"),
            (self.enforced_rules(), [self.approval()], "CODE_OWNER_REVIEW_MISSING"),
            (self.enforced_rules(), [self.approval(user={"login": reviewer}, state="COMMENTED")], "CODE_OWNER_REVIEW_NOT_APPROVED"),
            (self.enforced_rules(), [self.approval(user={"login": reviewer}, commit_id="a" * 40)], "CODE_OWNER_REVIEW_STALE"),
            (self.enforced_rules(), [self.approval(user={"login": reviewer, "type": "Bot"})], "CODE_OWNER_REVIEW_AUTOMATED_APPROVAL"),
            (self.enforced_rules(), [self.approval(user={"login": reviewer}, state="CHANGES_REQUESTED")], "CODE_OWNER_REVIEW_CHANGES_REQUESTED"),
        ]
        for rules, reviews, blocker in cases:
            with self.subTest(blocker=blocker):
                result = MODULE.evaluate_required_review(pr, rules, reviews, required_code_owner=reviewer)
                self.assertEqual(result["first_blocker"], blocker)

    def test_revoked_owner_record_blocks_even_with_an_updated_source_digest(self):
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        source = ROOT / policy["owner_delegation"]
        record = json.loads(source.read_bytes())
        record["state"] = "REVOKED"
        revoked = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode()
        import hashlib
        policy["mesh_authority"]["code_owner_review_delegation"]["source_sha256"] = hashlib.sha256(revoked).hexdigest()
        with patch.object(pathlib.Path, "read_bytes", return_value=revoked), self.assertRaises(MODULE.ReviewGateInputError):
            MODULE.resolve_required_code_owner("ingolf-lohmann/qik-vrt", policy=policy, pr_author="ingolf-lohmann")

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

    def test_authority_cannot_disable_review_without_explicit_owner_decision_or_assign_bot(self):
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        candidate = copy.deepcopy(policy)
        candidate["mesh_authority"]["independent_native_code_owner_review_required"] = False
        del candidate["mesh_authority"]["principal_review"]
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

    def test_actual_live_projection_closes_transition_with_old_trusted_main_core(self):
        from tools import qikvrt_required_review_gate as native_gate
        source = self.embedded_python("qikvrt_live_status_watch.yml", "python3 -B - <<'PY'\n")
        pr = self.pr(base={"sha": "a" * 40, "ref": "main"}, state="open")
        def read(command, **kwargs):
            path = command[-1]
            if path.endswith("/pulls/641"): return json.dumps(pr)
            if path.endswith("/rules/branches/main"): return json.dumps(self.enforced_rules())
            if "/reviews?" in path: return json.dumps([[self.approval()]])
            if "/statuses?" in path: return json.dumps([self.statuses()])
            self.fail(f"unexpected API read: {command}")
        env = {"REPOSITORY": "ingolf-lohmann/qik-vrt", "PR_NUMBER": "641", "EXPECTED_HEAD": self.head}
        namespace = {}
        with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read), patch.object(native_gate, "resolve_required_code_owner", None):
            exec(compile(source, "live-bootstrap-transition", "exec"), namespace)
        self.assertEqual(namespace["projection"]["first_blocker"], "AUTHORITY_BINDING_NOT_PROMOTED")
        self.assertEqual(namespace["projection"]["acceptance"], "BLOCKED")

    def test_actual_executor_bootstraps_without_native_effect_before_role_adoption(self):
        from tools import qikvrt_required_review_gate as native_gate
        source = self.embedded_python("qikvrt_requested_review_executor.yml", "python3 -B - <<'PY'\n")
        with patch.dict(os.environ, {"REPOSITORY": "ingolf-lohmann/qik-vrt"}), patch.object(native_gate, "resolve_required_code_owner", None), self.assertRaises(SystemExit) as result:
            exec(compile(source, "executor-bootstrap-transition", "exec"), {})
        self.assertEqual(result.exception.code, 2)

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

    def test_actual_publisher_accepts_delegate_for_owner_authored_pr(self):
        source = self.embedded_python("qikvrt_required_review_gate.yml", "python3 -B - <<'PY'\n")
        pr = self.pr(user={"login": "ingolf-lohmann"}, base={"sha": "a" * 40, "ref": "main"}, state="open")
        review = self.approval(user={"login": "Goldkelch", "type": "User"})
        posts = []
        def read(command, **kwargs):
            path = command[-1]
            if path.endswith("/pulls/641"): return json.dumps(pr)
            if path.endswith("/rules/branches/main"): return json.dumps(self.enforced_rules())
            if "/reviews?" in path: return json.dumps([[review]])
            self.fail(f"unexpected API read: {command}")
        with tempfile.TemporaryDirectory() as directory:
            env = {"REPOSITORY": "ingolf-lohmann/qik-vrt", "REQUESTED_PR": "641", "EVENT_NAME": "workflow_dispatch", "EVENT_PRS": "[]", "STATUS_CONTEXT": MODULE.GOVERNANCE_STATUS_CONTEXT, "LEGACY_STATUS_CONTEXT": MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT, "GITHUB_STEP_SUMMARY": str(pathlib.Path(directory) / "summary"), "GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "123"}
            with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read), patch("subprocess.check_call", side_effect=lambda command: posts.append(command)):
                namespace = {}
                exec(compile(source, "publisher-delegated-owner-review", "exec"), namespace)
            self.assertEqual(namespace["decision"]["gate_state"], "success")
            self.assertEqual(namespace["decision"]["required_code_owner"], "Goldkelch")
            self.assertEqual(len(posts), 2)
            self.assertTrue(all("state=success" in post for post in posts))
            self.assertTrue(all(not any("/reviews" in arg for arg in post) for post in posts))


class PrincipalReviewGateTests(unittest.TestCase):
    head = "b" * 40
    base = "a" * 40
    repository = "ingolf-lohmann/qik-vrt"

    def policy(self):
        return json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())

    def pr(self):
        return {"number": 523, "head": {"sha": self.head}, "user": {"login": "ingolf-lohmann"},
                "state": "open", "base": {"ref": "main", "sha": self.base, "repo": {"full_name": self.repository}}}

    def review(self, *, decision="APPROVE", payload_changes=None, **changes):
        configured = self.policy()["mesh_authority"]["principal_review"]
        payload = {"schema": MODULE.PRINCIPAL_REVIEW_SCHEMA, "decision": decision,
                   "repository": self.repository, "pull_request": 523, "head_sha": self.head,
                   "base_sha": self.base, "owner_record_sha256": configured["source_sha256"],
                   "instruction_sha256": configured["instruction_sha256"]}
        payload.update(payload_changes or {})
        review = {"id": 7, "submitted_at": "2026-10-18T04:20:00Z", "state": "COMMENTED",
                  "commit_id": self.head, "user": {"login": "ingolf-lohmann", "id": 294949349, "type": "User"},
                  "body": MODULE.PRINCIPAL_REVIEW_MARKER + "\n```json\n" + json.dumps(payload) + "\n```"}
        review.update(changes)
        return review

    def evaluate(self, reviews, pr=None):
        return MODULE.evaluate_required_review(pr or self.pr(), [], reviews, required_code_owner="Goldkelch")

    def test_considered_principal_approval_is_review_for_own_pr_without_independent_rule(self):
        value = self.evaluate([self.review()])
        self.assertEqual((value["gate_state"], value["review_basis"]), ("success", "OWNER_PRINCIPAL_REVIEW"))
        self.assertEqual(value["required_code_owner"], "ingolf-lohmann")
        self.assertEqual(value["platform_review_state"], "COMMENTED")
        self.assertFalse(value["independent_native_approval"])
        self.assertFalse(value["native_code_owner_rule_enforced"])

    def test_missing_or_plain_comment_does_not_invent_principal_review(self):
        for reviews in ([], [self.review(body="Freigabe erteilt")]):
            self.assertEqual(self.evaluate(reviews)["first_blocker"], "OWNER_PRINCIPAL_REVIEW_MISSING")

    def test_wrong_account_bot_and_unbound_account_id_cannot_supply_principal_review(self):
        for actor in ({"login": "someone-else", "id": 294949349, "type": "User"},
                      {"login": "ingolf-lohmann", "id": 294949349, "type": "Bot"},
                      {"login": "ingolf-lohmann", "id": 1, "type": "User"},
                      {"login": "ingolf-lohmann", "type": "User"},
                      {"login": "ingolf-lohmann", "id": 294949349}):
            with self.subTest(actor=actor):
                self.assertNotEqual(self.evaluate([self.review(user=actor)])["gate_state"], "success")

    def test_every_subject_and_instruction_binding_is_required(self):
        for field, value in (("repository", "foreign/qik-vrt"), ("pull_request", 524),
                             ("head_sha", "c" * 40), ("base_sha", "c" * 40),
                             ("owner_record_sha256", "0" * 64), ("instruction_sha256", "0" * 64),
                             ("schema", "ordinary-comment"), ("pull_request", True)):
            with self.subTest(field=field, value=value):
                self.assertEqual(self.evaluate([self.review(payload_changes={field: value})])["first_blocker"], "OWNER_PRINCIPAL_REVIEW_INVALID")

    def test_head_and_base_drift_invalidate_the_record_without_new_permission_request(self):
        pr = self.pr(); pr["head"]["sha"] = "c" * 40
        self.assertEqual(self.evaluate([self.review()], pr)["first_blocker"], "OWNER_PRINCIPAL_REVIEW_STALE")
        pr = self.pr(); pr["base"]["sha"] = "c" * 40
        self.assertEqual(self.evaluate([self.review()], pr)["first_blocker"], "OWNER_PRINCIPAL_REVIEW_INVALID")

    def test_other_repository_does_not_inherit_principal_authority(self):
        pr = self.pr(); pr["base"]["repo"]["full_name"] = "Goldkelch/qik-vrt"
        with self.assertRaises(MODULE.ReviewGateInputError):
            self.evaluate([self.review()], pr)

    def test_latest_revocation_changes_request_and_dismissal_supersede_approval(self):
        for changes, blocker in (({"decision": "REVOKE"}, "OWNER_PRINCIPAL_REVIEW_REVOKED"),
                                 ({"state": "CHANGES_REQUESTED"}, "OWNER_PRINCIPAL_REVIEW_CHANGES_REQUESTED"),
                                 ({"state": "DISMISSED"}, "OWNER_PRINCIPAL_REVIEW_DISMISSED")):
            later = self.review(id=8, submitted_at="2026-10-18T04:21:00Z", **changes)
            for reviews in ([self.review(), later], [later, self.review()]):
                with self.subTest(blocker=blocker):
                    self.assertEqual(self.evaluate(reviews)["first_blocker"], blocker)

    def test_unrelated_later_comment_does_not_revoke_principal_decision(self):
        value = self.evaluate([self.review(), self.review(id=8, submitted_at="2026-10-18T04:21:00Z", body="Additional context")])
        self.assertEqual(value["gate_state"], "success")
        self.assertEqual(value["review_id"], 7)

    def test_historical_unsubmitted_and_ambiguous_json_events_do_not_approve(self):
        duplicate = self.review()["body"].replace('"decision": "APPROVE"', '"decision": "REVOKE", "decision": "APPROVE"')
        for changes in ({"submitted_at": "2026-10-17T04:20:00Z"}, {"submitted_at": "invalid"},
                        {"submitted_at": "2026-10-18T04:20:00"}, {"id": None},
                        {"body": duplicate}, {"state": "PENDING"}, {"state": "APPROVED"}):
            with self.subTest(changes=changes):
                self.assertNotEqual(self.evaluate([self.review(**changes)])["gate_state"], "success")

    def test_green_status_cannot_create_review_and_principal_success_retains_its_basis(self):
        status = [{"id": 9, "state": "success", "context": MODULE.GOVERNANCE_STATUS_CONTEXT}]
        missing = MODULE.project_governance(self.pr(), [], [], status, required_code_owner="Goldkelch")
        self.assertEqual(missing["acceptance"], "BLOCKED")
        actual = MODULE.project_governance(self.pr(), [], [self.review()], status, required_code_owner="Goldkelch")
        self.assertEqual(actual["acceptance"], "OWNER_PRINCIPAL_REVIEW_SATISFIED")
        self.assertFalse(actual["independent_native_approval"])
        self.assertFalse(any(actual["completion_claims"].values()))
        unpublished = MODULE.project_governance(self.pr(), [], [self.review()], [], required_code_owner="Goldkelch")
        self.assertEqual(unpublished["first_blocker"], "NATIVE_GOVERNANCE_STATUS_MISSING")

    def test_principal_policy_cannot_be_replaced_with_unbound_or_automated_approval(self):
        for field, value in (("source_sha256", "0" * 64), ("state", "REVOKED"),
                             ("principal_github_id", 1), ("approval_is_review", False),
                             ("github_platform_protections_may_be_bypassed", True),
                             ("automated_disposition_can_substitute", True),
                             ("instruction_sha256", "0" * 64)):
            policy = self.policy(); policy["mesh_authority"]["principal_review"][field] = value
            with self.subTest(field=field), self.assertRaises(MODULE.ReviewGateInputError):
                MODULE.resolve_required_code_owner(self.repository, policy=policy)

    def test_principal_policy_enforcement_requires_the_actual_trusted_fresh_review_check(self):
        rules = [{"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": True,
            "required_status_checks": [{"context": MODULE.GOVERNANCE_STATUS_CONTEXT, "integration_id": 15368}]}}]
        self.assertTrue(MODULE.code_owner_review_policy_is_enforced(rules))
        self.assertFalse(MODULE.native_code_owner_rule_is_enforced(rules))
        for changes in ({"context": MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT}, {"integration_id": None}, {"integration_id": 1}):
            candidate = copy.deepcopy(rules)
            candidate[0]["parameters"]["required_status_checks"][0].update(changes)
            self.assertFalse(MODULE.code_owner_review_policy_is_enforced(candidate))
        rules[0]["parameters"]["strict_required_status_checks_policy"] = False
        self.assertFalse(MODULE.code_owner_review_policy_is_enforced(rules))
        self.assertFalse(MODULE.code_owner_review_policy_is_enforced([]))

    def test_revoked_owner_decision_remains_invalid_even_when_rehashed(self):
        import hashlib
        policy = self.policy()
        record = json.loads((ROOT / MODULE.OWNER_RECORD).read_bytes())
        record["principal_review_decision"]["state"] = "REVOKED"
        revoked = (json.dumps(record) + "\n").encode()
        policy["mesh_authority"]["principal_review"]["source_sha256"] = hashlib.sha256(revoked).hexdigest()
        with patch.object(pathlib.Path, "read_bytes", return_value=revoked), self.assertRaises(MODULE.ReviewGateInputError):
            MODULE.resolve_required_code_owner(self.repository, policy=policy)

    def test_actual_publisher_records_principal_success_without_review_or_rules_mutation(self):
        source = RequiredCodeOwnerReviewGateTests.embedded_python(self, "qikvrt_required_review_gate.yml", "python3 -B - <<'PY'\n")
        posts = []
        def read(command, **kwargs):
            path = command[-1]
            if path.endswith("/pulls/523"): return json.dumps(self.pr())
            if path.endswith("/rules/branches/main"): return "[]"
            if "/reviews?" in path: return json.dumps([[self.review()]])
            self.fail(f"unexpected API read: {command}")
        with tempfile.TemporaryDirectory() as directory:
            env = {"REPOSITORY": self.repository, "REQUESTED_PR": "523", "EVENT_NAME": "workflow_dispatch", "EVENT_PRS": "[]",
                   "STATUS_CONTEXT": MODULE.GOVERNANCE_STATUS_CONTEXT, "LEGACY_STATUS_CONTEXT": MODULE.LEGACY_GOVERNANCE_STATUS_CONTEXT,
                   "GITHUB_STEP_SUMMARY": str(pathlib.Path(directory) / "summary"), "GITHUB_SERVER_URL": "https://github.com", "GITHUB_RUN_ID": "123"}
            with patch.dict(os.environ, env), patch("subprocess.check_output", side_effect=read), patch("subprocess.check_call", side_effect=lambda command: posts.append(command)):
                namespace = {}; exec(compile(source, "publisher-principal-review", "exec"), namespace)
            self.assertEqual(namespace["decision"]["review_basis"], "OWNER_PRINCIPAL_REVIEW")
            self.assertEqual(len(posts), 2)
            self.assertTrue(all("state=success" in post and any("/statuses/" in part for part in post) for post in posts))


if __name__ == "__main__":
    unittest.main()
