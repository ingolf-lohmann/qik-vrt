import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import io
import os
import textwrap
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.infer import SYSTEM_PROMPT
from scripts.issue_agent.promote import promote
from scripts.issue_agent.validate import validate


class ValidateIssueAgentBundleTest(unittest.TestCase):
    def make_bundle(self, directory: Path) -> None:
        request = json.dumps({"issue_number": 76}, sort_keys=True) + "\n"
        (directory / "REQUEST.json").write_text(request, encoding="utf-8")
        digest = hashlib.sha256(request.encode()).hexdigest()
        (directory / "REQUEST.sha256").write_text(f"{digest}  REQUEST.json\n", encoding="utf-8")
        (directory / "CONTEXT.md").write_text("context\n", encoding="utf-8")
        (directory / "ANSWER.md").write_text(
            "## Issue disposition\n\nEXECUTE_NOW\n\n"
            "## Disposition reason\n\nThe request is clear and actionable.\n\n"
            "## Required next action\n\nExecute the smallest bounded work unit.\n\n"
            "## Gate result\n\nCONTINUE\n",
            encoding="utf-8",
        )
        (directory / "STATUS.json").write_text(json.dumps({
            "status": "CONTINUE",
            "model_inference_completed": True,
            "issue_disposition": "EXECUTE_NOW",
            "disposition_reason": "The request is clear and actionable.",
            "next_action": "Execute the smallest bounded work unit.",
            "closure_recommended": False,
            "automatic_issue_close": False,
            "automatic_merge": False,
            "no_false_pass": True,
        }), encoding="utf-8")

    def test_valid_bundle_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            validate(directory)

    def test_automatic_merge_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["automatic_merge"] = True
            status_path.write_text(json.dumps(status), encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate(directory)

    def test_missing_issue_disposition_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            del status["issue_disposition"]
            status_path.write_text(json.dumps(status), encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate(directory)

    def test_closure_disposition_may_use_none_next_action(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({
                "issue_disposition": "CLOSE_INVALID_OR_UNSUPPORTED",
                "disposition_reason": "The request is not reproducible from repository evidence.",
                "next_action": "NONE",
                "closure_recommended": True,
            })
            status_path.write_text(json.dumps(status), encoding="utf-8")
            validate(directory)

    def test_execute_now_remains_nonterminal_after_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            promote(directory)
            status = json.loads((directory / "STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "CONTINUE")
            self.assertFalse(status["automatic_merge"])
            self.assertFalse(status["automatic_issue_close"])
            self.assertFalse(status["mirror_sync_required"])
            self.assertFalse(status["common_tag_required"])
            validate(directory)

    def test_blocked_disposition_is_persisted_without_model_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            (directory / "ANSWER.md").write_text(
                "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
                "## Disposition reason\n\nMODEL_INFERENCE_UNAVAILABLE\n\n"
                "## Required next action\n\nRetry when trusted inference is available.\n\n"
                "## Gate result\n\nBLOCK\n",
                encoding="utf-8",
            )
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({
                "model_inference_completed": False,
                "issue_disposition": "BLOCKED_WITH_NEXT_ACTION",
                "disposition_reason": "MODEL_INFERENCE_UNAVAILABLE",
                "next_action": "Retry when trusted inference is available.",
                "closure_recommended": False,
            })
            status_path.write_text(json.dumps(status), encoding="utf-8")
            promote(directory)
            promoted = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(promoted["status"], "BLOCK")
            self.assertFalse(promoted["automatic_merge"])
            self.assertFalse(promoted["automatic_issue_close"])
            validate(directory)

    def test_terminal_closure_proposal_does_not_authorize_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            (directory / "ANSWER.md").write_text(
                "## Issue disposition\n\nCLOSE_COMPLETED\n\n"
                "## Disposition reason\n\nThe canonical successor fully evidences completion.\n\n"
                "## Required next action\n\nNONE\n\n"
                "## Gate result\n\nCONTINUE\n",
                encoding="utf-8",
            )
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({
                "issue_disposition": "CLOSE_COMPLETED",
                "disposition_reason": "The canonical successor fully evidences completion.",
                "next_action": "NONE",
                "closure_recommended": True,
            })
            status_path.write_text(json.dumps(status), encoding="utf-8")
            promote(directory)
            promoted = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(promoted["status"], "CONTINUE")
            self.assertFalse(promoted["automatic_merge"])
            self.assertFalse(promoted["automatic_issue_close"])
            self.assertFalse(promoted["mirror_sync_required"])
            self.assertFalse(promoted["common_tag_required"])
            validate(directory)

    def test_predecessor_done_is_not_current_effect_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            path = directory / "STATUS.json"
            status = json.loads(path.read_text(encoding="utf-8"))
            status.update(status="DONE", automatic_merge=True,
                          automatic_issue_close=True, mirror_sync_required=True,
                          common_tag_required=True)
            path.write_text(json.dumps(status), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "PROPOSAL_IS_NOT_AN_EFFECT_RECEIPT"):
                validate(directory)

    def test_review_gate_has_its_own_status_context(self):
        workflow = (ROOT / ".github/workflows/qikvrt_required_review_gate.yml").read_text()
        self.assertIn("STATUS_CONTEXT: QIKVRT required code-owner review", workflow)
        self.assertNotIn("STATUS_CONTEXT: QIKVRT requested review execution", workflow)

    def test_completion_observer_is_role_local_paginated_and_non_effecting(self):
        workflow = (ROOT / ".github/workflows/issue-agent-autofinish.yml").read_text()
        for forbidden in ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt",
                          ": write", "secrets.", "schedule:", "git push"):
            self.assertNotIn(forbidden, workflow)
        program = textwrap.dedent(workflow.split("<<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        for repository in ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt", "node/qik-vrt"):
            for pages in ([[]], [[{"number": 1}], [{"number": 2, "pull_request": {}}]]):
                with self.subTest(repository=repository, pages=pages), tempfile.TemporaryDirectory() as temp:
                    calls = []
                    def gh(arguments, **kwargs):
                        calls.append(arguments)
                        if "--paginate" in arguments:
                            self.assertIn("--slurp", arguments)
                            self.assertEqual(arguments[-1], f"repos/{repository}/issues?state=open&per_page=100")
                            return json.dumps(pages)
                        self.assertEqual(arguments, ["gh", "api", f"repos/{repository}/git/ref/heads/main"])
                        return json.dumps({"object": {"sha": "a" * 40}})
                    output = io.StringIO()
                    with patch.dict(os.environ, {"REPOSITORY": repository, "GITHUB_RUN_ID": "1",
                            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_STEP_SUMMARY": str(Path(temp) / "summary")}), \
                            patch("subprocess.check_output", side_effect=gh), contextlib.redirect_stdout(output):
                        exec(compile(program, "completion-observer", "exec"), {})
                    receipt = json.loads(output.getvalue())
                    self.assertEqual(len(calls), 2)
                    self.assertEqual(receipt["repository"], repository)
                    self.assertEqual(receipt["open_issues"], [1] if pages[0] else [])
                    self.assertEqual(receipt["open_pull_requests"], [2] if pages[0] else [])
                    self.assertFalse(receipt["completion_proven"])
                    self.assertFalse(receipt["cross_repository_evidence_reused"])
                    self.assertEqual(receipt["effects_performed"], [])

    def test_policy_and_owner_delegation_are_active_and_fail_closed(self):
        policy = json.loads((
            ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
        ).read_text(encoding="utf-8"))
        delegation = json.loads((
            ROOT / "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
        ).read_text(encoding="utf-8"))
        continuation = json.loads((
            ROOT / "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json"
        ).read_text(encoding="utf-8"))

        self.assertEqual(
            policy["schema"],
            "qikvrt_requested_review_and_issue_lifecycle_policy_v1",
        )
        self.assertEqual(policy["status"], "ACTIVE")
        self.assertEqual(
            policy["issue_lifecycle"]["unclassified_open_issue"],
            "FORBIDDEN",
        )
        self.assertEqual(
            set(policy["issue_lifecycle"]["allowed_dispositions"]),
            {
                "EXECUTE_NOW",
                "CLARIFICATION_REQUIRED",
                "BLOCKED_WITH_NEXT_ACTION",
                "CLOSE_COMPLETED",
                "CLOSE_NOT_PLANNED",
                "CLOSE_INVALID_OR_UNSUPPORTED",
            },
        )
        self.assertEqual(delegation["state"], "ACTIVE")
        self.assertEqual(
            delegation["combined_source_sha256"],
            "1f66e77ab105f24c95c4d275e1deab5cc97aa0dcc896a1c833fb12cafd06eec6",
        )
        self.assertTrue(
            delegation["authorization_scope"][
                "perform_requested_substantive_reviews_without_reinteraction"
            ]
        )
        self.assertTrue(
            delegation["authorization_scope"]["triage_every_observed_open_issue"]
        )
        self.assertFalse(
            policy["mandatory_boundaries"]["merge_or_promotion_implicitly_authorized"]
        )
        self.assertFalse(
            policy["mandatory_boundaries"]["external_publication_or_submission_authorized"]
        )
        self.assertIn(
            "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json",
            continuation["related_delegations"],
        )

    def test_issue_agent_prompt_requires_one_lifecycle_disposition(self):
        for token in (
            "EXECUTE_NOW",
            "CLARIFICATION_REQUIRED",
            "BLOCKED_WITH_NEXT_ACTION",
            "CLOSE_COMPLETED",
            "CLOSE_NOT_PLANNED",
            "CLOSE_INVALID_OR_UNSUPPORTED",
        ):
            self.assertIn(token, SYSTEM_PROMPT)
        self.assertIn("Do not leave an issue in an unclassified waiting state", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
