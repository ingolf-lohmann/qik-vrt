# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.infer import SYSTEM_PROMPT
from scripts.issue_agent.promote import promote
from scripts.issue_agent.validate import validate
from tools import qikvrt_integrity as integrity


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

    def test_terminal_closure_alone_promotes_to_done(self):
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
            self.assertEqual(promoted["status"], "DONE")
            self.assertTrue(promoted["automatic_merge"])
            self.assertTrue(promoted["automatic_issue_close"])
            self.assertTrue(promoted["mirror_sync_required"])
            self.assertTrue(promoted["common_tag_required"])
            validate(directory)

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

    def test_autofinish_requires_nonempty_successful_checks_on_both_repositories(self):
        source = (ROOT / ".github/workflows/issue-agent-autofinish.yml").read_text(
            encoding="utf-8"
        )
        for token in (
            'check_count="$(printf',
            'successful="$(printf',
            'mirror_check_count="$(printf',
            'mirror_successful="$(printf',
            '[ "$check_count" -eq 0 ] || [ "$successful" -eq 0 ]',
            '[ "$mirror_check_count" -eq 0 ] || [ "$mirror_successful" -eq 0 ]',
        ):
            self.assertIn(token, source)

        policy = json.loads((
            ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
        ).read_text(encoding="utf-8"))
        postconditions = policy["issue_agent_integration"]["autofinish_postconditions"]
        self.assertFalse(postconditions["empty_check_rollup_is_success"])
        self.assertEqual(postconditions["minimum_successful_check_before_merge"], 1)
        self.assertTrue(postconditions["authority_and_mirror_checks_are_independent"])

    def test_effect_ack_follows_confirmed_issue_closure(self):
        source = (ROOT / ".github/workflows/issue-agent-autofinish.yml").read_text(
            encoding="utf-8"
        )
        close = source.index('gh issue close "$issue"')
        readback = source.index('issue_state="$(gh issue view "$issue"', close)
        closed_gate = source.index('[ "$issue_state" != "CLOSED" ]', readback)
        effect_ack = source.index('**EFFECT_ACK_DONE**', closed_gate)
        self.assertLess(close, readback)
        self.assertLess(readback, closed_gate)
        self.assertLess(closed_gate, effect_ack)

        policy = json.loads((
            ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
        ).read_text(encoding="utf-8"))
        self.assertTrue(
            policy["issue_agent_integration"]["autofinish_postconditions"]
            ["effect_ack_comment_requires_closed_readback"]
        )


class IssueWriterIntegrityTest(unittest.TestCase):
    """Execute production shell with real Git and the canonical integrity tool."""

    def git(self, root, *args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE,
            timeout=20,
        ).strip()

    def script(self, name):
        source = (ROOT / ".github/workflows/issue-autonomous-processing.yml").read_text()
        step = source.split("      - name: " + name + "\n", 1)[1].split("\n      - ", 1)[0]
        return textwrap.dedent(step.split("        run: |\n", 1)[1])

    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix="qikvrt-issue-writer-")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        root, remote, runner = base / "source", base / "remote.git", base / "runner"
        root.mkdir(); runner.mkdir()
        self.git(base, "init", "--bare", "-q", str(remote))
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.name", "Issue regression")
        self.git(root, "config", "user.email", "issue-regression@example.invalid")
        self.git(root, "remote", "add", "origin", str(remote))
        (root / ".gitignore").write_text("__pycache__/\n*.pyc\n.qikvrt-integrity.lock\n")
        (root / "tools").mkdir()
        for name in ("qikvrt_integrity.py", "qikvrt_subprocess.py", "qikvrt_pipeline_contracts.py"):
            shutil.copyfile(ROOT / "tools" / name, root / "tools" / name)
        (root / "LEGACY_INTEGRITY_INVENTORIES.md").write_text("legacy inventories\n")
        (root / "source.txt").write_text("trusted source\n")
        self.assertTrue(integrity.generate(root).ok)
        self.git(root, "add", ".")
        self.git(root, "commit", "-qm", "trusted fixture")
        self.git(root, "push", "-q", "origin", "main")
        self.git(root, "switch", "-qc", "issue-agent/76")
        environment = dict(os.environ, ISSUE_NUMBER="76", RUNNER_TEMP=str(runner),
                           PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
        return root, remote, runner, environment

    def make_bundle(self, root):
        directory = root / "evidence/issues/76"
        directory.mkdir(parents=True, exist_ok=True)
        ValidateIssueAgentBundleTest().make_bundle(directory)

    def commit_script(self):
        # The existing shared helper has its own real-Git/API response tests.
        # Exercise the complete production prefix before that remote boundary.
        script = self.script("Create or update issue work branch and pull request")
        return script.split('python3 -B "$RUNNER_TEMP/qikvrt-issue-pipeline-contracts.py" publish-writer', 1)[0]

    def run_script(self, root, environment, script):
        return subprocess.run(["bash", "-c", script], cwd=root, env=environment,
                              text=True, capture_output=True, timeout=30)

    def test_legacy_omission_fails_exact_commit_then_repaired_writer_passes(self):
        root, remote, runner, environment = self.fixture()
        self.make_bundle(root)
        self.git(root, "add", "evidence/issues/76")
        self.git(root, "commit", "-qm", "legacy evidence-only writer")
        self.assertFalse(integrity.verify(root).ok)
        legacy = self.git(root, "rev-parse", "HEAD")
        self.git(root, "push", "-q", "origin", "issue-agent/76")
        (runner / "qikvrt-issue-input.json").write_text('{"raw_transport":true}\n')
        result = self.run_script(root, environment, self.commit_script())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        changed = set(self.git(root, "diff", "--name-only", legacy, "HEAD").splitlines())
        self.assertEqual(changed, integrity.INTEGRITY_PATHS)
        self.assertTrue(integrity.verify(root).ok)
        self.git(root, "push", "-q", "origin", "issue-agent/76")
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/issue-agent/76"),
                         self.git(root, "rev-parse", "HEAD"))
        clone = runner / "readback"
        self.git(runner, "clone", "-q", "--branch", "issue-agent/76", str(remote), str(clone))
        self.assertTrue(integrity.verify(clone).ok)
        self.assertFalse((clone / "issue.json").exists())
        self.assertFalse((clone / "qikvrt-issue-input.json").exists())

    def test_two_successors_preserve_manual_repair_history_and_canonical_trio(self):
        root, remote, _, environment = self.fixture()
        self.make_bundle(root)
        manual = root / "evidence/issues/76/MANUAL_REPAIR.md"
        manual.write_text("preserved manual repair\n")
        self.git(root, "add", "evidence/issues/76")
        self.git(root, "commit", "-qm", "manual repair")
        predecessor = self.git(root, "rev-parse", "HEAD")
        self.git(root, "push", "-q", "origin", "issue-agent/76")
        for generation in (1, 2):
            (root / "evidence/issues/76/CONTEXT.md").write_text(f"context {generation}\n")
            result = self.run_script(root, environment, self.commit_script())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.git(root, "rev-parse", "HEAD^"), predecessor)
            changed = set(self.git(root, "diff", "--name-only", predecessor, "HEAD").splitlines())
            self.assertTrue(integrity.INTEGRITY_PATHS.issubset(changed))
            self.assertEqual(manual.read_text(), "preserved manual repair\n")
            self.assertTrue(integrity.verify(root).ok)
            self.git(root, "push", "-q", "origin", "issue-agent/76")
            predecessor = self.git(root, "rev-parse", "HEAD")
            self.assertEqual(self.git(remote, "rev-parse", "refs/heads/issue-agent/76"), predecessor)

    def test_generation_failure_never_commits_or_reaches_remote_effect(self):
        root, remote, runner, environment = self.fixture()
        self.make_bundle(root)
        before = self.git(root, "rev-parse", "HEAD")
        (root / "unsafe-source.txt").symlink_to(runner / "not-a-source")
        reached = runner / "publish-called"
        script = self.commit_script() + '\nprintf reached > "$RUNNER_TEMP/publish-called"\n'
        result = self.run_script(root, environment, script)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCK", result.stderr)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), before)
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/main"), before)
        self.assertFalse(reached.exists())

    def test_corruption_between_generate_and_verify_never_commits(self):
        root, _, runner, environment = self.fixture()
        self.make_bundle(root)
        before = self.git(root, "rev-parse", "HEAD")
        binary = runner / "bin"; binary.mkdir()
        wrapper = binary / "python3"
        wrapper.write_text(
            '#!' + sys.executable + '\nimport os,pathlib,sys\n'
            'if sys.argv[-1] == "verify":\n'
            '    pathlib.Path("SHA256SUMS.txt").write_text("corrupt\\n")\n'
            'os.execv(sys.executable, [sys.executable] + sys.argv[1:])\n'
        )
        wrapper.chmod(0o755)
        environment["PATH"] = str(binary) + os.pathsep + environment["PATH"]
        result = self.run_script(root, environment, self.commit_script())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCK", result.stderr)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), before)

    def test_unstaged_or_untracked_integrity_input_cannot_escape_commit(self):
        for tracked in (False, True):
            with self.subTest(tracked=tracked):
                root, _, _, environment = self.fixture()
                self.make_bundle(root)
                before = self.git(root, "rev-parse", "HEAD")
                name = "source.txt" if tracked else "unexpected.json"
                (root / name).write_text("outside declared issue write\n")
                result = self.run_script(root, environment, self.commit_script())
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.git(root, "rev-parse", "HEAD"), before)

    def test_transport_input_is_resolved_outside_tree_and_invalid_number_stops(self):
        root, _, runner, environment = self.fixture()
        binary = runner / "bin"; binary.mkdir()
        (binary / "gh").write_text('#!/bin/sh\nprintf \'{"number":76,"title":"request"}\\n\'\n')
        (binary / "gh").chmod(0o755)
        environment.update(PATH=str(binary) + os.pathsep + environment["PATH"],
                           EVENT_NAME="workflow_dispatch", EVENT_ISSUE_NUMBER="",
                           INPUT_ISSUE_NUMBER="76", REPOSITORY="fixture/qik-vrt",
                           GITHUB_OUTPUT=str(runner / "output"))
        result = self.run_script(root, environment, self.script("Resolve issue"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((runner / "qikvrt-issue-input.json").is_file())
        self.assertEqual(self.git(root, "status", "--porcelain"), "")
        (runner / "qikvrt-issue-input.json").unlink()
        environment["INPUT_ISSUE_NUMBER"] = "76/../../source"
        result = self.run_script(root, environment, self.script("Resolve issue"))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((runner / "qikvrt-issue-input.json").exists())

    def test_existing_branch_binding_keeps_history_and_uses_trusted_reporter(self):
        root, remote, runner, environment = self.fixture()
        trusted = self.git(root, "rev-parse", "HEAD")
        self.make_bundle(root)
        # A pre-activation issue branch does not contain the new reporter.
        (root / "tools/qikvrt_pipeline_contracts.py").unlink()
        self.git(root, "add", ".")
        self.git(root, "commit", "-qm", "existing issue work")
        predecessor = self.git(root, "rev-parse", "HEAD")
        predecessor_tree = self.git(root, "rev-parse", "HEAD^{tree}")
        self.git(root, "push", "-q", "origin", "issue-agent/76")
        self.git(root, "checkout", "-q", "--detach", trusted)
        self.git(root, "branch", "-D", "issue-agent/76")
        binary = runner / "bin"; binary.mkdir()
        helper = binary / "gh"
        helper.write_text(
            '#!' + sys.executable + '\nimport json,os,sys\n'
            'path=next(p for p in sys.argv if p.startswith("repos/"))\n'
            'if "/git/ref/heads/" in path:\n'
            '    head=os.environ["TEST_ISSUE_HEAD"] if path.endswith("issue-agent/76") else os.environ["TEST_MAIN_HEAD"]\n'
            '    value={"object":{"sha":head,"type":"commit"}}\n'
            'elif "/git/commits/" in path:\n'
            '    head=path.rsplit("/",1)[1]\n'
            '    tree=os.environ["TEST_ISSUE_TREE"] if head==os.environ["TEST_ISSUE_HEAD"] else os.environ["TEST_MAIN_TREE"]\n'
            '    value={"sha":head,"tree":{"sha":tree}}\n'
            'else: raise SystemExit("unexpected API path")\n'
            'print(json.dumps(value))\n'
        )
        helper.chmod(0o755)
        environment.update(PATH=str(binary) + os.pathsep + environment["PATH"],
                           GITHUB_REPOSITORY="fixture/qik-vrt", TEST_ISSUE_HEAD=predecessor,
                           TEST_ISSUE_TREE=predecessor_tree, TEST_MAIN_HEAD=trusted,
                           TEST_MAIN_TREE=self.git(root, "rev-parse", "HEAD^{tree}"))
        result = self.run_script(root, environment,
            self.script("Bind resumable issue work branch without history rewrite"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git(root, "rev-parse", "HEAD"), predecessor)
        self.assertFalse((root / "tools/qikvrt_pipeline_contracts.py").exists())
        self.assertEqual((runner / "qikvrt-issue-pipeline-contracts.py").read_bytes(),
                         (ROOT / "tools/qikvrt_pipeline_contracts.py").read_bytes())
        observed = json.loads((runner / "qikvrt-issue-writer-input.json").read_text())
        self.assertEqual(observed["state"], "WRITER_INPUT_BOUND")
        self.assertEqual((observed["head"], observed["tree"], observed["base"]),
                         (predecessor, predecessor_tree, trusted))
        self.assertFalse(observed["EFFECT_ACK_DONE"])
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/issue-agent/76"), predecessor)


if __name__ == "__main__":
    unittest.main()
