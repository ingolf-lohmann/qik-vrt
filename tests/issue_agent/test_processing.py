# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.compile import (
    ARTIFACTS, PROCESSOR_PATHS, admission, compile_issue, preserve_previous, record_attempt,
)
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


class WorkflowEnvironmentTest(unittest.TestCase):
    def test_runner_paths_are_exported_at_step_scope(self):
        # GitHub rejects runner context in jobs.<job_id>.env before creating a job.
        self.assertNotIn("${{ runner.", WORKFLOW.split("    steps:\n", 1)[0])
        with tempfile.TemporaryDirectory(prefix="issue processor ") as directory:
            environment_file = Path(directory) / "github env"
            result = subprocess.run(
                ["bash", "-c", step_script("Set transient processor paths")],
                env=dict(os.environ, RUNNER_TEMP=directory, GITHUB_ENV=str(environment_file)),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            exported = dict(line.split("=", 1) for line in environment_file.read_text().splitlines())
            self.assertEqual(exported, {
                "ISSUE_JSON": str(Path(directory) / "qikvrt-issue.json"),
                "TRUSTED_PROCESSOR_ROOT": str(Path(directory) / "qikvrt-issue-processor"),
                "HANDOFF_DIRECTORY": str(Path(directory) / "qikvrt-issue-handoff"),
                "PREPARED_INPUT_DIRECTORY": str(Path(directory) / "qikvrt-issue-input"),
            })


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
            elif self.mode == 'empty-pr-response':
                stdout = ''
            elif self.mode == 'invalid-pr-json':
                stdout = '{broken'
            else:
                stdout = json.dumps(self.prs)
        elif args[:4] == ["gh", "api", "--method", "POST"] and args[4].endswith("/pulls"):
            payload = json.loads(Path(args[-1]).read_text())
            assert payload["draft"] is True and payload["head"] == "issue-agent/458"
            if self.mode == "denied":
                code, stderr = 1, "GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)"
            elif self.mode == "ambiguous-success":
                self.prs = [self.pr()]
                code, stderr = 1, "connection closed after write"
            else:
                self.prs = [self.pr("f" * 40 if self.mode == "wrong-head" else None)]
                stdout = self.prs[0]["html_url"]
        elif args[:4] == ["gh", "api", "--method", "POST"] and args[4].endswith("/comments"):
            body = json.loads(Path(args[-1]).read_text())["body"]
            self.comments.append(body)
            if self.mode in {"comment-denied", "comment-ambiguous-success"}:
                code = 1
            else:
                stdout = "https://github.com/ingolf-lohmann/qik-vrt/issues/458#issuecomment-1000"
        elif args[:2] == ["gh", "api"] and "/issues/458/comments?" in args[2]:
            stdout = json.dumps([] if self.mode == "comment-denied" else [
                {"body": body, "html_url": "https://github.com/ingolf-lohmann/qik-vrt/issues/458#issuecomment-1000"}
                for body in self.comments
            ])
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
        self.assertEqual(len([args for args in stub.calls if args[:4] == ["gh", "api", "--method", "POST"] and args[4].endswith("/pulls")]), 1)

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

    def test_empty_pr_response_is_a_controlled_block_without_a_write(self):
        receipt, stub = self.transact('empty-pr-response')
        self.assertEqual(receipt['failure_class'], 'HANDOFF_VALIDATION_FAILED')
        self.assertEqual(receipt['pr_create_attempts'], 0)
        self.assertEqual(receipt['notification_status'], 'ISSUE_COMMENT_READBACK_VERIFIED')

    def test_invalid_pr_json_is_a_controlled_block_without_a_write(self):
        receipt, stub = self.transact('invalid-pr-json')
        self.assertEqual(receipt['failure_class'], 'HANDOFF_VALIDATION_FAILED')
        self.assertEqual(receipt['pr_create_attempts'], 0)
        self.assertEqual(receipt['notification_status'], 'ISSUE_COMMENT_READBACK_VERIFIED')

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

    def test_repeated_handoff_reuses_pr_and_comment_without_a_second_write(self):
        stub = GitHubStub(self.head)
        output = self.base / 'resume-handoff'
        arguments = dict(root=self.root, output=output, repository='ingolf-lohmann/qik-vrt',
                         issue_number=458, commit=self.head, tree=self.tree,
                         source_commit=self.source, run_id='12345', run_attempt='1')
        with patch('scripts.issue_agent.handoff.command', side_effect=stub.run):
            first = handoff(**arguments)
            second = handoff(**arguments)
        self.assertEqual(first['pull_request'], second['pull_request'])
        self.assertEqual(second['notification_status'], 'ISSUE_COMMENT_READBACK_VERIFIED')
        self.assertEqual(len(stub.comments), 1)
        self.assertEqual(len([a for a in stub.calls if a[:4] == ['gh', 'api', '--method', 'POST']
                              and a[4].endswith('/pulls')]), 1)

    def test_repeated_denied_handoff_requires_new_capability_evidence(self):
        stub = GitHubStub(self.head, 'denied')
        arguments = dict(root=self.root, output=self.base / 'resume-denied',
                         repository='ingolf-lohmann/qik-vrt', issue_number=458,
                         commit=self.head, tree=self.tree, source_commit=self.source,
                         run_id='12345', run_attempt='1')
        with patch('scripts.issue_agent.handoff.command', side_effect=stub.run):
            handoff(**arguments)
            second = handoff(**arguments)
        self.assertEqual(second['failure_class'], 'PR_CREATE_RETRY_REQUIRES_NEW_CAPABILITY_EVIDENCE')
        self.assertEqual(second['pr_create_attempts'], 1)

    def test_ambiguous_comment_is_observed_without_repeating_write(self):
        receipt, stub = self.transact('comment-ambiguous-success')
        self.assertEqual(receipt['notification_status'], 'ISSUE_COMMENT_READBACK_VERIFIED')
        self.assertEqual(receipt['issue_comment_attempts'], 1)
        self.assertEqual(len(stub.comments), 1)

    def test_empty_and_invalid_legacy_model_answers_remain_blocked(self):
        for answer in ('', '   \n', '{invalid JSON'):
            with self.subTest(answer=answer):
                (self.directory / 'ANSWER.md').write_text(answer)
                self.finalize('--inference-outcome', 'success')
                promote(self.directory)
                validate(self.directory)
                status = json.loads((self.directory / 'STATUS.json').read_text())
                self.assertEqual(status['status'], 'BLOCK')
                self.assertEqual(status['disposition_reason'], 'MODEL_INFERENCE_UNAVAILABLE')
                self.assertFalse(status['model_inference_completed'])

    def test_compiler_handles_bad_issue_json_without_a_traceback(self):
        for raw in ('', '   ', '{broken', 'null', '[]'):
            with self.subTest(raw=raw):
                self.issue.write_text(raw)
                result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/issue_agent/compile.py'),
                    '--issue', str(self.issue), '--context', str(self.directory / 'CONTEXT.md'),
                    '--output', str(self.directory / 'ANSWER.md')], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('INVALID_ISSUE_JSON', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_empty_compiler_output_cannot_reuse_a_completion_claim(self):
        (self.directory / 'ANSWER.md').write_text('   \n')
        self.finalize('--processing-outcome', 'success')
        promote(self.directory)
        validate(self.directory)
        status = json.loads((self.directory / 'STATUS.json').read_text())
        self.assertEqual(status['disposition_reason'], 'DETERMINISTIC_COMPILER_FAILED')
        self.assertFalse(status['deterministic_compilation_completed'])

    def test_current_main_integrity_conflicts_preserve_issue_evidence(self):
        previous = self.head
        request = (self.directory / 'REQUEST.json').read_bytes()
        self.git('checkout', 'main')
        (self.root / 'README.md').write_text('Current Main fixture.\n')
        generate(self.root)
        self.git('add', '.')
        self.git('commit', '-m', 'changed Main context')
        current = self.git('rev-parse', 'HEAD')
        self.git('push', 'origin', 'HEAD:refs/heads/main')
        self.git('checkout', '--detach', current)
        self.git('branch', '-D', 'issue-agent/458')
        self.env['GITHUB_SHA'] = current
        self.run_step('Prepare history-preserving issue branch')
        generate(self.root)
        self.run_step('Persist issue work branch')
        self.git('merge-base', '--is-ancestor', previous, 'HEAD')
        self.git('merge-base', '--is-ancestor', current, 'HEAD')
        self.assertEqual((self.directory / 'REQUEST.json').read_bytes(), request)


class CausalAdmissionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repository'
        self.root.mkdir()
        for name in PROCESSOR_PATHS:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.git('init', '--initial-branch=main')
        self.git('config', 'user.name', 'Local test fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.hooksPath', '/dev/null')
        self.directory = self.root / 'evidence/issues/458'
        self.directory.mkdir(parents=True)
        self.issue = self.base / 'issue.json'
        self.issue.write_text(json.dumps({'number': 458, 'title': 'Unimplemented request',
                                         'body': '', 'updated_at': '2026-10-10T00:00:00Z'}))
        self.context = self.base / 'context.md'
        self.context.write_text('Bound repository context.\n')
        self.receipt_path = self.base / 'ADMISSION.json'
        self.ref = 'refs/remotes/origin/issue-agent/458'
        self.build_bundle()
        self.commit()

    def git(self, *args):
        result = subprocess.run(['git', *args], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def check(self, previous=True):
        return admission(issue_path=self.issue, context_path=self.context,
                         repository='ingolf-lohmann/qik-vrt', previous_ref=self.ref if previous else None,
                         root=self.root, processor_root=self.root)

    def build_bundle(self):
        raw = json.loads(self.issue.read_text())
        request = {'repository': 'ingolf-lohmann/qik-vrt', 'issue_number': 458,
                   'title': raw['title'], 'body': raw['body']}
        data = (json.dumps(request, sort_keys=True) + '\n').encode()
        (self.directory / 'REQUEST.json').write_bytes(data)
        (self.directory / 'REQUEST.sha256').write_text(hashlib.sha256(data).hexdigest() + '  REQUEST.json\n')
        shutil.copyfile(self.context, self.directory / 'CONTEXT.md')
        compile_issue(self.issue, self.context, self.directory / 'ANSWER.md')
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/issue_agent/finalize.py'),
            '--directory', str(self.directory), '--processing-outcome', 'success'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        promote(self.directory)
        self.receipt_path.write_text(json.dumps(self.check(previous=False)))
        record_attempt(self.directory, self.receipt_path)
        validate(self.directory)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '--allow-empty', '-m', 'fixture evidence')
        self.git('update-ref', self.ref, self.git('rev-parse', 'HEAD'))

    def test_unchanged_block_does_not_admit_reprocessing(self):
        receipt = self.check()
        self.assertFalse(receipt['execute'])
        self.assertEqual(receipt['reason'], 'NOOP_UNCHANGED_CAUSAL_INPUT')

    def test_timestamp_and_unrelated_lifecycle_commit_do_not_admit_retry(self):
        issue = json.loads(self.issue.read_text())
        issue['updated_at'] = '2026-10-11T00:00:00Z'
        self.issue.write_text(json.dumps(issue))
        (self.root / 'heartbeat.json').write_text('{}\n')
        self.commit()
        self.assertFalse(self.check()['execute'])

    def test_changed_request_admits_one_new_attempt(self):
        issue = json.loads(self.issue.read_text())
        issue['body'] = 'Materially changed request.'
        self.issue.write_text(json.dumps(issue))
        self.assertTrue(self.check()['execute'])
        self.build_bundle()
        self.commit()
        self.assertFalse(self.check()['execute'])

    def test_changed_context_admits_retry(self):
        self.context.write_text('New relevant repository evidence.\n')
        self.assertTrue(self.check()['execute'])

    def test_changed_processor_capability_admits_retry(self):
        with (self.root / 'scripts/issue_agent/compile.py').open('a') as f:
            f.write('\n# Reviewed successor fixture.\n')
        self.assertTrue(self.check()['execute'])

    def test_legacy_inference_state_admits_one_repair_migration(self):
        (self.directory / 'ATTEMPT.json').unlink()
        self.commit()
        self.assertEqual(self.check()['reason'], 'LEGACY_PROCESSOR_MIGRATION')

    def test_corrupt_prior_json_blocks_without_blind_retry(self):
        (self.directory / 'ATTEMPT.json').write_text('{broken')
        self.commit()
        with self.assertRaisesRegex(SystemExit, 'PREVIOUS_ATTEMPT_INVALID'):
            self.check()

    def test_prior_artifact_tampering_blocks_without_blind_retry(self):
        (self.directory / 'ANSWER.md').write_text('tampered')
        self.commit()
        with self.assertRaisesRegex(SystemExit, 'PREVIOUS_ATTEMPT_INVALID'):
            self.check()

    def test_prior_evidence_is_archived_exactly_and_idempotently(self):
        before = {name: (self.directory / name).read_bytes() for name in (*ARTIFACTS, 'ATTEMPT.json')}
        preserve_previous(self.directory)
        preserve_previous(self.directory)
        archives = list((self.directory / 'history').iterdir())
        self.assertEqual(len(archives), 1)
        self.assertEqual({name: (archives[0] / name).read_bytes() for name in before}, before)

    def test_symlink_evidence_is_not_followed(self):
        (self.directory / 'ANSWER.md').unlink()
        (self.directory / 'ANSWER.md').symlink_to(self.issue)
        with self.assertRaisesRegex(SystemExit, 'UNSAFE_EVIDENCE_ARTIFACT'):
            preserve_previous(self.directory)

    def test_attempt_cannot_bind_different_input_bytes(self):
        (self.directory / 'CONTEXT.md').write_text('changed after admission')
        with self.assertRaisesRegex(SystemExit, 'ATTEMPT_INPUT_MISMATCH'):
            record_attempt(self.directory, self.receipt_path)

    def test_workflow_noop_precedes_every_repository_effect(self):
        self.assertLess(WORKFLOW.index('Evaluate causal retry admission'),
                        WORKFLOW.index('Prepare history-preserving issue branch'))
        for name in ('Prepare history-preserving issue branch', 'Materialize request and repository context',
                     'Compile deterministic repository-grounded disposition', 'Enforce truthful status',
                     'Validate evidence and materialize canonical integrity', 'Persist issue work branch'):
            step = WORKFLOW.split('      - name: ' + name + '\n', 1)[1].split('\n      - ', 1)[0]
            self.assertIn("if: steps.admission.outputs.execute == 'true'", step)
        backlog = (ROOT / '.github/workflows/issue-agent-backlog-resume.yml').read_text()
        self.assertNotIn('minimum_age_seconds', backlog)
        self.assertLess(backlog.index('--check-admission'), backlog.index('gh api --method POST'))

    def test_actual_admission_shell_skips_unchanged_subject(self):
        prepared = self.base / 'prepared'
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/issue_agent/materialize.py'),
            '--issue', str(self.issue), '--repository', 'ingolf-lohmann/qik-vrt',
            '--output-dir', str(prepared)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        shutil.copyfile(prepared / 'CONTEXT.md', self.context)
        self.build_bundle()
        self.commit()
        remote = self.base / 'remote.git'
        self.git('init', '--bare', str(remote))
        self.git('remote', 'add', 'origin', str(remote))
        self.git('push', 'origin', 'HEAD:refs/heads/issue-agent/458')
        before = self.git('ls-remote', '--heads', 'origin', 'refs/heads/issue-agent/458')
        output = self.base / 'outputs'
        summary = self.base / 'summary'
        env = dict(os.environ, TRUSTED_PROCESSOR_ROOT=str(self.root),
            PREPARED_INPUT_DIRECTORY=str(prepared), ISSUE_JSON=str(self.issue),
            HANDOFF_DIRECTORY=str(self.base / 'handoff'), ISSUE_NUMBER='458',
            REPOSITORY='ingolf-lohmann/qik-vrt', GITHUB_OUTPUT=str(output),
            GITHUB_STEP_SUMMARY=str(summary))
        result = subprocess.run(['bash', '-c', step_script('Evaluate causal retry admission')],
                                cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('execute=false', output.read_text())
        self.assertEqual(before, self.git('ls-remote', '--heads', 'origin', 'refs/heads/issue-agent/458'))

    def test_actual_prepare_rejects_branch_change_after_admission(self):
        remote = self.base / 'remote.git'
        self.git('init', '--bare', str(remote))
        self.git('remote', 'add', 'origin', str(remote))
        self.git('push', 'origin', 'HEAD:refs/heads/issue-agent/458')
        admitted = self.git('rev-parse', 'HEAD')
        (self.root / 'competitor.txt').write_text('New competing evidence.\n')
        self.commit()
        competitor = self.git('rev-parse', 'HEAD')
        self.git('push', 'origin', 'HEAD:refs/heads/issue-agent/458')
        env = dict(os.environ, ISSUE_NUMBER='458', PREVIOUS_BRANCH_HEAD=admitted, GITHUB_SHA=admitted)
        result = subprocess.run(['bash', '-c', step_script('Prepare history-preserving issue branch')],
                                cwd=self.root, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ISSUE_BRANCH_CHANGED_AFTER_ADMISSION', result.stderr)
        self.assertTrue(self.git('ls-remote', '--heads', 'origin', 'refs/heads/issue-agent/458').startswith(competitor))


if __name__ == "__main__":
    unittest.main()
