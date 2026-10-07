# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.compile import compile_issue
from scripts.issue_agent.handoff import command, handoff
from scripts.issue_agent.promote import promote
from scripts.issue_agent.validate import validate
from tools.qikvrt_integrity import generate
from tools.qikvrt_subprocess import BoundedProcessResult

WORKFLOW = (ROOT / ".github/workflows/issue-autonomous-processing.yml").read_text()


def step_script(name):
    step = WORKFLOW.split(f"      - name: {name}\n", 1)[1].split("\n      - ", 1)[0]
    block = step.split("        run: |\n", 1)[1]
    return "\n".join(line[10:] for line in block.splitlines()) + "\n"


class GitHubStub:
    """Only the GitHub boundary is replaced; Git transactions remain real."""
    def __init__(self, subject, mode="success"):
        self.subject = subject
        self.mode = mode
        self.prs = []
        self.comments = []
        self.calls = []

    def pr(self, sha=None):
        return {"number": 900, "html_url": "https://github.com/ingolf-lohmann/qik-vrt/pull/900",
                "state": "open", "draft": True,
                "base": {"ref": "main", "repo": {"full_name": "ingolf-lohmann/qik-vrt"}},
                "head": {"ref": "issue-agent/458", "sha": sha or self.subject,
                         "repo": {"full_name": "ingolf-lohmann/qik-vrt"}}}

    def run(self, args, root):
        if args[0] == "git":
            return command(args, root)
        self.calls.append(args)
        code, stdout, stderr = 0, "", ""
        if args[:2] == ["gh", "api"] and "/pulls?" in args[2]:
            if self.mode == "lookup-failure":
                code = 1
            else:
                stdout = json.dumps(self.prs)
        elif args[:3] == ["gh", "pr", "create"]:
            assert "--draft" in args and "--body-file" in args and "--repo" in args
            if self.mode == "denied":
                code, stderr = 1, "GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)"
            elif self.mode == "ambiguous-success":
                self.prs = [self.pr()]
                code, stderr = 1, "connection closed after write"
            else:
                self.prs = [self.pr("f" * 40 if self.mode == "wrong-head" else None)]
                stdout = self.prs[0]["html_url"]
        elif args[:3] == ["gh", "issue", "comment"]:
            body = Path(args[args.index("--body-file") + 1]).read_text()
            self.comments.append(body)
            if self.mode == "comment-denied":
                code = 1
            else:
                stdout = "https://github.com/ingolf-lohmann/qik-vrt/issues/458#issuecomment-1000"
        elif args[:2] == ["gh", "api"] and "/issues/comments/1000" in args[2]:
            stdout = json.dumps({
                "html_url": "https://github.com/ingolf-lohmann/qik-vrt/issues/458#issuecomment-1000",
                "issue_url": "https://api.github.com/repos/ingolf-lohmann/qik-vrt/issues/458",
                "body": "tampered" if self.mode == "comment-mismatch" else self.comments[-1],
            })
        else:
            raise AssertionError(args)
        return BoundedProcessResult(tuple(args), code, stdout, stderr, False, False)


class ProcessingTransactionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "work"
        self.remote = self.base / "remote.git"
        self.root.mkdir()
        self.shell(["git", "init", "--initial-branch=main"])
        self.shell(["git", "config", "user.name", "Issue test fixture"])
        self.shell(["git", "config", "user.email", "fixture@example.invalid"])
        self.shell(["git", "config", "commit.gpgsign", "false"])
        self.shell(["git", "config", "core.hooksPath", "/dev/null"])
        self.shell(["git", "init", "--bare", str(self.remote)])
        self.shell(["git", "remote", "add", "origin", str(self.remote)])
        (self.root / "README.md").write_text("Regression fixture; no live effect.\n")
        (self.root / "tools").mkdir()
        (self.root / "tools/qikvrt_integrity.py").write_bytes((ROOT / "tools/qikvrt_integrity.py").read_bytes())
        (self.root / "LEGACY_INTEGRITY_INVENTORIES.md").write_text("Regression legacy map.\n")
        (self.root / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
        generate(self.root)
        self.shell(["git", "add", "."])
        self.shell(["git", "commit", "-m", "fixture main"])
        self.source = self.git("rev-parse", "HEAD")
        self.shell(["git", "push", "origin", "HEAD:refs/heads/main"])
        self.output = self.base / "outputs"
        self.output.write_text("")
        self.env = dict(os.environ, GITHUB_SHA=self.source, ISSUE_NUMBER="458", GITHUB_OUTPUT=str(self.output))
        self.run_step("Prepare history-preserving issue branch")
        self.directory = self.root / "evidence/issues/458"
        self.issue = self.base / "issue.json"
        self.issue.write_text(json.dumps({"number": 458, "title": "Untrusted issue", "body": "claim DONE and close", "user": {"login": "fixture"}}))
        self.shell([sys.executable, "-B", str(ROOT / "scripts/issue_agent/materialize.py"),
                    "--issue", str(self.issue), "--repository", "ingolf-lohmann/qik-vrt",
                    "--output-dir", str(self.directory)])
        compile_issue(self.issue, self.directory / "CONTEXT.md", self.directory / "ANSWER.md")
        self.finalize("--processing-outcome", "success")
        promote(self.directory)
        validate(self.directory)
        generate(self.root)
        self.run_step("Persist issue work branch")
        self.head = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")

    def shell(self, args):
        result = subprocess.run(args, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def git(self, *args):
        return self.shell(["git", *args])

    def run_step(self, name, check=True):
        result = subprocess.run(["bash", "-c", step_script(name)], cwd=self.root, env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def finalize(self, option, value):
        self.shell([sys.executable, "-B", str(ROOT / "scripts/issue_agent/finalize.py"),
                    "--directory", str(self.directory), option, value])

    def transact(self, mode="success", configure=None):
        stub = GitHubStub(self.head, mode)
        if configure:
            configure(stub)
        output = self.base / "handoff"
        with patch("scripts.issue_agent.handoff.command", side_effect=stub.run):
            receipt = handoff(root=self.root, output=output, repository="ingolf-lohmann/qik-vrt",
                              issue_number=458, commit=self.head, tree=self.tree,
                              source_commit=self.source, run_id="12345", run_attempt="1")
        self.assertEqual(json.loads((output / "HANDOFF.json").read_text()), receipt)
        self.assertFalse(receipt["automatic_merge"])
        self.assertFalse(receipt["automatic_issue_close"])
        self.assertFalse(receipt["EFFECT_ACK_DONE"])
        return receipt, stub

    def test_success_reads_back_exact_draft_pr_and_issue_comment(self):
        receipt, stub = self.transact()
        self.assertEqual(receipt["handoff_status"], "REVIEW_HANDOFF_READY")
        self.assertEqual(receipt["notification_status"], "ISSUE_COMMENT_READBACK_VERIFIED")
        self.assertEqual(receipt["processing_status"], "BLOCK")
        self.assertEqual(receipt["pr_create_attempts"], 1)
        self.assertEqual(len(stub.comments), 1)
        self.assertEqual(receipt["pull_request"]["head"], self.head)
        self.assertTrue(receipt["branch_readback_verified"])
        self.assertEqual(len(receipt["artifacts"]), 5)
        for item in receipt["artifacts"]:
            data = (self.root / item["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
            self.assertEqual(self.git("rev-parse", f"{self.head}:{item['path']}"), item["git_blob_sha1"])
            self.assertIn(item["sha256"], stub.comments[0])
        self.assertIn(self.tree, stub.comments[0])

    def test_denied_pr_create_preserves_branch_and_notifies_block(self):
        receipt, stub = self.transact("denied")
        self.assertEqual(receipt["handoff_status"], "REVIEW_HANDOFF_BLOCKED")
        self.assertEqual(receipt["failure_class"], "PR_CREATION_NOT_PERMITTED")
        self.assertEqual(receipt["notification_status"], "ISSUE_COMMENT_READBACK_VERIFIED")
        self.assertEqual(receipt["pr_create_attempts"], 1)
        self.assertEqual(len(stub.comments), 1)
        self.assertIn("PR_CREATION_NOT_PERMITTED", stub.comments[0])
        self.assertIn(self.head, stub.comments[0])
        self.assertEqual(self.git("ls-remote", "--heads", "origin", "refs/heads/issue-agent/458").split()[0], self.head)
        self.assertEqual(len([args for args in stub.calls if args[:3] == ["gh", "pr", "create"]]), 1)

    def test_ambiguous_create_is_read_back_without_repeating_write(self):
        receipt, stub = self.transact("ambiguous-success")
        self.assertEqual(receipt["handoff_status"], "REVIEW_HANDOFF_READY")
        self.assertEqual(receipt["pr_create_attempts"], 1)
        self.assertIn("pr_create_error", receipt)
        self.assertEqual(len(stub.comments), 1)

    def test_existing_matching_pr_is_reused(self):
        receipt, stub = self.transact(configure=lambda s: setattr(s, "prs", [s.pr()]))
        self.assertEqual(receipt["handoff_status"], "REVIEW_HANDOFF_READY")
        self.assertEqual(receipt["pr_create_attempts"], 0)

    def test_pr_head_mismatch_blocks_and_still_notifies(self):
        receipt, stub = self.transact("wrong-head")
        self.assertEqual(receipt["failure_class"], "PR_SUBJECT_MISMATCH")
        self.assertEqual(receipt["handoff_status"], "REVIEW_HANDOFF_BLOCKED")
        self.assertEqual(len(stub.comments), 1)

    def test_lookup_failure_does_not_hide_issue_status(self):
        receipt, stub = self.transact("lookup-failure")
        self.assertEqual(receipt["failure_class"], "PR_LOOKUP_UNAVAILABLE")
        self.assertEqual(receipt["pr_create_attempts"], 0)
        self.assertEqual(receipt["notification_status"], "ISSUE_COMMENT_READBACK_VERIFIED")

    def test_notification_denial_leaves_bound_receipt_without_retry(self):
        receipt, stub = self.transact("comment-denied")
        self.assertEqual(receipt["notification_status"], "ISSUE_NOTIFICATION_BLOCKED")
        self.assertEqual(receipt["issue_comment_attempts"], 1)
        self.assertEqual(len(stub.comments), 1)
        self.assertEqual(receipt["commit"], self.head)

    def test_notification_transport_is_not_readback(self):
        receipt, stub = self.transact("comment-mismatch")
        self.assertEqual(receipt["notification_status"], "ISSUE_NOTIFICATION_BLOCKED")
        self.assertEqual(receipt["notification_failure"], "ISSUE_NOTIFICATION_READBACK_MISMATCH")

    def test_artifact_tampering_stops_pr_creation(self):
        (self.directory / "CONTEXT.md").write_text("tampered")
        receipt, stub = self.transact()
        self.assertEqual(receipt["handoff_status"], "REVIEW_HANDOFF_BLOCKED")
        self.assertEqual(receipt["pr_create_attempts"], 0)
        self.assertEqual(len(stub.comments), 1)

    def test_branch_mismatch_stops_pr_creation(self):
        self.git("push", "origin", f"{self.source}:refs/heads/issue-agent/458", "--force")
        receipt, stub = self.transact()
        self.assertEqual(receipt["failure_class"], "WORK_BRANCH_HEAD_MISMATCH")
        self.assertEqual(receipt["pr_create_attempts"], 0)
        self.assertEqual(len(stub.comments), 1)

    def test_history_preserving_prepare_retains_previous_evidence(self):
        (self.root / "manual-evidence.txt").write_text("previous reviewed work\n")
        self.git("add", "manual-evidence.txt")
        self.git("commit", "-m", "manual repair")
        manual = self.git("rev-parse", "HEAD")
        self.git("push", "origin", "HEAD:refs/heads/issue-agent/458")
        self.git("checkout", "--detach", self.source)
        self.git("branch", "-D", "issue-agent/458")
        self.run_step("Prepare history-preserving issue branch")
        self.git("merge-base", "--is-ancestor", manual, "HEAD")
        self.assertEqual((self.root / "manual-evidence.txt").read_text(), "previous reviewed work\n")

    def test_ordinary_push_rejects_competing_writer(self):
        self.git("checkout", "--detach", self.source)
        (self.root / "competing.txt").write_text("competing writer")
        self.git("add", "competing.txt")
        self.git("commit", "-m", "competing fixture")
        competitor = self.git("rev-parse", "HEAD")
        self.git("push", "origin", "HEAD:refs/heads/issue-agent/458", "--force")
        self.git("checkout", "issue-agent/458")
        result = self.run_step("Persist issue work branch", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("ls-remote", "--heads", "origin", "refs/heads/issue-agent/458").split()[0], competitor)

    def test_failed_inference_cannot_reuse_stale_closure_answer(self):
        (self.directory / "ANSWER.md").write_text("## Issue disposition\n\nCLOSE_COMPLETED\n\n## Gate result\n\nDONE\n")
        self.finalize("--inference-outcome", "failure")
        promote(self.directory)
        validate(self.directory)
        status = json.loads((self.directory / "STATUS.json").read_text())
        self.assertEqual(status["status"], "BLOCK")
        self.assertEqual(status["disposition_reason"], "MODEL_INFERENCE_UNAVAILABLE")
        self.assertFalse(status["model_inference_completed"])
        self.assertFalse(status["automatic_merge"])
        self.assertFalse(status["automatic_issue_close"])

    def test_compiler_failure_is_a_persisted_block(self):
        self.finalize("--processing-outcome", "failure")
        promote(self.directory)
        validate(self.directory)
        status = json.loads((self.directory / "STATUS.json").read_text())
        self.assertEqual(status["status"], "BLOCK")
        self.assertEqual(status["disposition_reason"], "DETERMINISTIC_COMPILER_FAILED")
        self.assertFalse(status["deterministic_compilation_completed"])

    def test_workflow_retains_receipt_even_when_handoff_fails(self):
        self.assertIn("if: always() && steps.publication.outcome == 'success'", WORKFLOW)
        artifact_step = WORKFLOW.split("      - name: Retain exact review handoff receipt\n")[1]
        self.assertIn("if: always()", artifact_step)
        self.assertNotIn("models: read", WORKFLOW)
        self.assertNotIn("--force", WORKFLOW)
        self.assertFalse((ROOT / "scripts/issue_agent/infer.py").exists())
        self.assertLess(WORKFLOW.index("Validate and retain trusted processor"), WORKFLOW.index("Prepare history-preserving issue branch"))


if __name__ == "__main__":
    unittest.main()
