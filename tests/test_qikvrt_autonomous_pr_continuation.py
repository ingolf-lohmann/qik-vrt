# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tools.qikvrt_autonomous_self_heal import (
    SelfHealBlock, continuation_verification_decision, pipeline_binding,
    verify_pipeline_binding,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
CONTINUATION = ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml"
VERIFIER = ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"


class AutonomousPRContinuationTests(unittest.TestCase):
    def test_actual_artifact_receiver_executes_the_existing_consumer(self):
        import hashlib, zipfile
        from tests.test_qikvrt_autonomous_self_heal import RepairInputTests
        _, raw, envelope, source_run, jobs = RepairInputTests().fixture()
        source = CONTINUATION.read_text()
        block=source.split('      - name: Receive watchdog analysis in the existing repair consumer\n',1)[1].split('\n      - name:',1)[0]
        script=textwrap.dedent(block.split('        run: |\n',1)[1])
        for corrupt, expected in ((False,0),(True,1)):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as directory:
                root=pathlib.Path(directory); binary=root/'bin';binary.mkdir()
                archive=root/'source.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    z.writestr('repair-handoff.json',json.dumps(envelope))
                    z.writestr('../forbidden.py','raise Exception("never extract")')
                artifact={'id':9,'name':'qikvrt-reflexive-repository-watchdog-7-2','expired':False,
                          'digest':'sha256:'+hashlib.sha256(archive.read_bytes()).hexdigest()}
                if corrupt:artifact['digest']='sha256:'+'0'*64
                responses={
                    'repos/ingolf-lohmann/qik-vrt/actions/runs/7':source_run,
                    'repos/ingolf-lohmann/qik-vrt/actions/runs/7/attempts/2/jobs?per_page=100':[jobs],
                    'repos/ingolf-lohmann/qik-vrt/actions/runs/7/artifacts?per_page=100':[{'artifacts':[artifact]}],
                    'repos/ingolf-lohmann/qik-vrt/commits/'+'a'*40:{'sha':'a'*40,'commit':{'tree':{'sha':'b'*40}}},
                    'repos/ingolf-lohmann/qik-vrt/git/ref/heads/main':{'object':{'sha':'a'*40}},
                    'repos/ingolf-lohmann/qik-vrt/pulls?state=open&per_page=100':[[]]}
                (root/'responses.json').write_text(json.dumps(responses))
                gh=binary/'gh'
                gh.write_text('#!'+sys.executable+'\n'+textwrap.dedent(f'''
                    import json,sys,pathlib
                    endpoint=sys.argv[-1]
                    if endpoint.endswith('/artifacts/9/zip'):
                        sys.stdout.buffer.write(pathlib.Path({str(archive)!r}).read_bytes())
                    else:
                        print(json.dumps(json.load(open({str(root/'responses.json')!r}))[endpoint]))
                '''));gh.chmod(0o755)
                destination=str(root/'receiver')
                result=subprocess.run(['bash','-c',script.replace('/tmp/qikvrt-repair-input',destination)],
                    cwd=ROOT,text=True,capture_output=True,env={**os.environ,
                    'PATH':str(binary)+os.pathsep+os.environ['PATH'], 'GITHUB_REPOSITORY':'ingolf-lohmann/qik-vrt',
                    'SOURCE_RUN_ID':'7','SOURCE_ATTEMPT':'2','SOURCE_HEAD':'a'*40})
                self.assertEqual(result.returncode,expected,result.stderr)
                if not corrupt:
                    receipt=json.loads((root/'receiver/consumer-receipt.json').read_text())
                    self.assertEqual(receipt['state'],'ADMITTED_ANALYSIS_HOLD')
                    saved=json.loads(next((root/'receiver/inbox').glob('*.json')).read_text())
                    self.assertEqual(saved['analysis_utf8'].encode(),raw)
                self.assertFalse((root/'forbidden.py').exists())

    def test_completed_ci_selects_only_the_current_opted_in_subject(self):
        source = CONTINUATION.read_text()
        self.assertIn('  workflow_run:\n    workflows:\n      - "QIKVRT CI"', source)
        self.assertIn('      - "QIKVRT repository evidence materialization"\n    types: [completed]', source)
        self.assertNotIn("conclusion == 'success'", source)
        marker = "      - name: Select one exact opted-in same-repository draft PR\n"
        block = source.split(marker, 1)[1].split("\n      - name:", 1)[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        opt_in = "<!-- qikvrt-autonomous-self-heal:enabled -->"
        def pr(number, head, body=opt_in, repository="owner/repo"):
            return {"number": number, "draft": True, "body": body,
                    "head": {"sha": head, "ref": "work/candidate", "repo": {"full_name": repository}},
                    "base": {"sha": "c" * 40, "ref": "main"}}
        pages = [[pr(1, "a" * 40), pr(2, "b" * 40),
                  pr(3, "d" * 40, body=""), pr(4, "e" * 40, repository="other/repo")]]
        for subject, expected in (("a" * 40, 1), ("b" * 40, 2),
                                  ("f" * 40, None), ("d" * 40, None),
                                  ("e" * 40, None), ("", 1), ("invalid", "BLOCK")):
            with self.subTest(subject=subject), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw)
                binary = root / "bin"
                binary.mkdir()
                gh = binary / "gh"
                gh.write_text("#!" + sys.executable + "\nprint(" + repr(json.dumps(pages)) + ")\n")
                gh.chmod(0o755)
                output = root / "output"
                env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                           OPT_IN_MARKER=opt_in, GITHUB_REPOSITORY="owner/repo",
                           SOURCE_HEAD_SHA=subject, GITHUB_OUTPUT=str(output))
                result = subprocess.run(["bash"], input=script.replace(
                    "/tmp/qikvrt-open-pr-pages.json", str(root / "pages.json")),
                    env=env, text=True, capture_output=True, timeout=10)
                if expected == "BLOCK":
                    self.assertNotEqual(0, result.returncode)
                else:
                    self.assertEqual(0, result.returncode, result.stderr)
                    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
                    self.assertEqual("false" if expected is None else "true", values["found"])
                    if expected is not None:
                        self.assertEqual(str(expected), values["pr_number"])

    def test_contract_is_opt_in_same_repo_draft_and_one_at_a_time(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        value = contract["pull_request_continuation"]
        self.assertEqual(
            value["opt_in_marker"],
            "<!-- qikvrt-autonomous-self-heal:enabled -->",
        )
        self.assertTrue(value["same_repository_only"])
        self.assertTrue(value["draft_only"])
        self.assertEqual(value["maximum_pull_requests_per_run"], 1)
        self.assertEqual(value["history_rewrite"], "FORBIDDEN")
        self.assertEqual(
            value["automatic_promotion"],
            "TWO_PHASE_EXPECTED_HEAD_BOUND_ONLY",
        )

    def test_continuation_preserves_history_and_never_merges_or_force_pushes(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("git merge --no-ff --no-edit", source)
        self.assertIn("live_head_before_push", source)
        self.assertIn("refs/heads/${HEAD_REF}", source)
        self.assertNotIn("git push --force", source)
        self.assertNotIn("git push -f", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("refs/heads/main\"", source)
        self.assertIn("make test", source)
        self.assertIn("qikvrt_autonomous_exact_head_verify", source)

    def test_only_handler_owned_generated_conflicts_are_auto_resolved(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("git diff --name-only --diff-filter=U", source)
        self.assertIn(".allowlisted_handlers[].mutable_paths[]", source)
        self.assertIn("BLOCK: non-allowlisted merge conflicts", source)
        self.assertIn("git checkout --ours", source)
        self.assertIn("generated-output reset", source)
        self.assertNotIn("git checkout --theirs", source)
        self.assertNotIn("git merge --abort || true", source)

    def test_continuation_shell_block_is_syntax_valid(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        marker = "      - name: Continue exact draft head through deterministic repairs\n"
        marker_index = source.index(marker)
        run_marker = "        run: |\n"
        start = source.index(run_marker, marker_index) + len(run_marker)
        end = source.index("\n      - name:", start)
        script = textwrap.dedent(source[start:end])
        completed = subprocess.run(
            ["bash", "-n"],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_dispatch_verifier_binds_exact_head_and_posts_a_distinct_status(self) -> None:
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("repository_dispatch", source)
        self.assertIn("qikvrt_autonomous_exact_head_verify", source)
        self.assertIn("test \"$(git rev-parse --verify HEAD^{commit})\" = \"$TARGET_SHA\"", source)
        self.assertIn("make test", source)
        self.assertIn("verify_qce_package.py", source)
        self.assertIn("QIKVRT autonomous exact-head verification", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("zenodo", source.casefold())
        self.assertNotIn("ietf", source.casefold())

    def test_external_review_and_publication_gates_remain_distinct(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        gates = contract["pull_request_continuation"]["external_gates"]
        self.assertEqual(
            gates,
            [
                "IDENTIFIED_HUMAN_PHYSICS_REVIEW_WHEN_REQUIRED",
                "SEPARATE_EXPLICIT_ZENODO_AUTHORIZATION",
            ],
        )

    def make_pipeline_fixture(self, directory):
        root = pathlib.Path(directory) / "repository"
        root.mkdir()
        (root / "tools").mkdir()
        (root / "AGENTS.md").write_text("Independent review remains required.\n")
        (root / "Makefile").write_text("test:\n\ttrue\n")
        # Fixed local fixture controller, not a remote execution or real repair.
        (root / "tools/qikvrt_autonomous_self_heal.py").write_text(
            "import json\nprint(json.dumps({'state':'NOOP','changed_paths':[]}))\n")
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()
        git("init", "-b", "main")
        git("config", "user.name", "pipeline-test-fixture")
        git("config", "user.email", "pipeline-fixture@example.invalid")
        git("add", ".")
        git("commit", "-m", "fixed local pipeline fixture")
        return root, git, git("rev-parse", "HEAD")

    def test_pipeline_binds_bytes_modes_additions_deletions_and_trusted_ref(self):
        with tempfile.TemporaryDirectory() as directory:
            root, git, head = self.make_pipeline_fixture(directory)
            expected = pipeline_binding(root, head)
            verify_pipeline_binding(expected, pipeline_binding(root))
            changed = root / "Makefile"
            original = changed.read_bytes()
            for content in (b"test:\n\tfalse\n", b"test:\n\techo skipped\n"):
                changed.write_bytes(content)
                with self.assertRaisesRegex(SelfHealBlock, "INVARIANT_MISMATCH"):
                    verify_pipeline_binding(expected, pipeline_binding(root))
            changed.write_bytes(original)
            changed.chmod(0o755)
            with self.assertRaises(SelfHealBlock):
                verify_pipeline_binding(expected, pipeline_binding(root))
            changed.chmod(0o644)
            (root / "tests").mkdir()
            extra = root / "tests/new_admission.py"
            extra.write_text("weakened = True\n")
            with self.assertRaises(SelfHealBlock):
                verify_pipeline_binding(expected, pipeline_binding(root))
            extra.unlink()
            (root / "src").mkdir()
            source = root / "src/new_pipeline_dependency.py"
            source.write_text("replacement = True\n")
            with self.assertRaises(SelfHealBlock):
                verify_pipeline_binding(expected, pipeline_binding(root))
            source.unlink()
            changed.unlink()
            with self.assertRaises((SelfHealBlock, OSError)):
                pipeline_binding(root)
            changed.write_bytes(original)
            verify_pipeline_binding(expected, pipeline_binding(root))
            with self.assertRaises(SelfHealBlock):
                pipeline_binding(root, "HEAD")
            broken = {**expected, "sha256": "0" * 64}
            with self.assertRaisesRegex(SelfHealBlock, "digest"):
                verify_pipeline_binding(broken, expected)

    def test_scaled_feedback_preserves_the_bound_pipeline(self):
        from src.qikvrt_codec import BitFrame, FeedbackPolicy, feedback_step, local_refeed
        with tempfile.TemporaryDirectory() as directory:
            root, _, head = self.make_pipeline_fixture(directory)
            expected = pipeline_binding(root, head)
            for direction in ("left-to-right", "right-to-left"):
                for routes in ((), ((0, 0, -1),), ((0, 0, 100), (1, 100, 200))):
                    policy = FeedbackPolicy(routes=routes, max_hops=16)
                    frame = BitFrame(direction, 0, 0, bytes(range(256)) * 16)
                    step = feedback_step(frame, policy)
                    self.assertFalse(step.effect_ack.ordinary_release)
                    if len(routes) == 1:
                        for i in range(1, 17):
                            frame = local_refeed(step, policy, port=0, sequence=i, tick=i)
                            step = feedback_step(frame, policy)
                    verify_pipeline_binding(expected, pipeline_binding(root))

    def test_reference_binds_actual_crlf_checkout_and_attributes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, git, _ = self.make_pipeline_fixture(directory)
            attributes = root / ".gitattributes"
            attributes.write_text("* text=auto eol=lf\n*.ps1 text eol=crlf\n")
            script = root / "tools/portable.ps1"
            script.write_bytes(b"Write-Output 'same pipeline'\n")
            git("add", ".gitattributes", "tools/portable.ps1")
            git("commit", "-m", "fixed checkout normalization fixture")
            head = git("rev-parse", "HEAD")
            script.unlink()
            git("checkout", "--", "tools/portable.ps1")
            self.assertIn(b"\r\n", script.read_bytes())
            expected = pipeline_binding(root, head)
            verify_pipeline_binding(expected, pipeline_binding(root))
            script.write_bytes(b"Write-Output 'changed pipeline'\r\n")
            with self.assertRaises(SelfHealBlock):
                verify_pipeline_binding(expected, pipeline_binding(root))
            git("checkout", "--", "tools/portable.ps1")
            attributes.write_text("* text=auto eol=lf\n*.ps1 text eol=lf\n")
            with self.assertRaises(SelfHealBlock):
                verify_pipeline_binding(expected, pipeline_binding(root))

    def test_noop_requires_dedicated_verifier_not_ordinary_green_ci(self):
        for statuses in ([], [{"context": "test", "state": "success"}],
                         [{"context": "QIKVRT repository evidence", "state": "success"}]):
            self.assertEqual("DISPATCH_REQUIRED", continuation_verification_decision(statuses))
        for state in ("success", "pending", "failure", "error"):
            statuses = [{"context": "QIKVRT autonomous exact-head verification", "state": state}]
            self.assertEqual("EXISTING_VERIFICATION_REQUIRES_READBACK",
                             continuation_verification_decision(statuses))
        for statuses in (None, [None], [{"context": "QIKVRT autonomous exact-head verification", "state": "unknown"}],
                         [{"context": "QIKVRT autonomous exact-head verification", "state": "success"}] * 2):
            with self.assertRaises(SelfHealBlock):
                continuation_verification_decision(statuses)

    def test_dedicated_pr_contract_job_has_no_writer_capability(self):
        source = VERIFIER.read_text()
        job = source[source.index("  verify-pr-contract:"):source.index("\n  verify:")]
        self.assertIn("if: github.event_name == 'pull_request'", job)
        self.assertIn("permissions:\n      contents: read", job)
        self.assertIn("persist-credentials: false", job)
        self.assertIn("github.event.pull_request.head.sha", job)
        self.assertIn("make test", job)
        for writer in ("GH_TOKEN", "statuses: write", "pull-requests: write", "git push", "gh api"):
            self.assertNotIn(writer, job)

    def test_actual_noop_workflow_dispatches_once_and_suppresses_repeat(self):
        source = CONTINUATION.read_text()
        start = source.index("        run: |\n", source.index(
            "      - name: Continue exact draft head through deterministic repairs\n")) + len("        run: |\n")
        end = source.index("\n      - name:", start)
        script = textwrap.dedent(source[start:end])
        for has_status, incomplete in ((False, False), (True, False), (False, True)):
            with self.subTest(has_status=has_status, incomplete=incomplete), tempfile.TemporaryDirectory() as directory:
                temporary = pathlib.Path(directory)
                root, git, head = self.make_pipeline_fixture(directory)
                git("branch", "work/subject")
                provider = temporary / "provider.git"
                subprocess.check_call(["git", "clone", "--bare", str(root), str(provider)],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                git("remote", "add", "origin", str(provider))
                prefix = str(temporary / "qikvrt-")
                (temporary / "qikvrt-trusted-pipeline-controller.py").write_bytes(
                    (ROOT / "tools/qikvrt_autonomous_self_heal.py").read_bytes())
                (temporary / "qikvrt-trusted-pipeline-binding.json").write_text(json.dumps(pipeline_binding(root, head)))
                binary = temporary / "bin"
                binary.mkdir()
                mock_gh = binary / "gh"
                mock_gh.write_text("#!" + sys.executable + "\n" + textwrap.dedent('''
                    import json,os,sys
                    from pathlib import Path
                    args=sys.argv[1:];head=os.environ['EXPECTED_HEAD']
                    if '--method' in args and 'POST' in args:
                        with open(os.environ['CALL_LOG'],'a') as f:f.write(json.dumps(args)+'\\n')
                        print('{}')
                    elif args[:2]==['pr','comment']:print('{}')
                    elif any('/pulls/' in x for x in args):print(head)
                    elif any('/git/ref/heads/main' in x for x in args):print(head)
                    elif any('/commits/' in x for x in args):
                        statuses=[]
                        if os.environ['HAS_STATUS']=='true':
                            statuses=[{'context':'QIKVRT autonomous exact-head verification','state':'pending'}]
                        count=len(statuses)+(1 if os.environ['INCOMPLETE']=='true' else 0)
                        print(json.dumps({'statuses':statuses,'total_count':count}))
                    else:raise SystemExit('unexpected fixture command')
                '''))
                mock_gh.chmod(0o755)
                env = {**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                       "PR_NUMBER": "1", "HEAD_REF": "work/subject", "EXPECTED_HEAD": head,
                       "BASE_REF": "main", "OBSERVED_BASE": head, "GITHUB_REPOSITORY": "owner/repo",
                       "GITHUB_WORKSPACE": str(root), "GITHUB_SERVER_URL": "https://github.com",
                       "GITHUB_RUN_ID": "101", "CALL_LOG": str(temporary / "calls.jsonl"),
                       "HAS_STATUS": "true" if has_status else "false",
                       "INCOMPLETE": "true" if incomplete else "false"}
                result = subprocess.run(["bash"], input=script.replace("/tmp/qikvrt-", prefix),
                                        cwd=root, env=env, text=True, capture_output=True, timeout=30)
                self.assertEqual(2 if incomplete else 0, result.returncode, result.stderr + result.stdout)
                log = temporary / "calls.jsonl"
                calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
                dispatches = [call for call in calls if any(x.endswith('/dispatches') for x in call)]
                self.assertEqual(0 if has_status or incomplete else 1, len(dispatches))
                self.assertEqual(head, git("rev-parse", "HEAD"))
                self.assertEqual("", git("status", "--porcelain"))


if __name__ == "__main__":
    unittest.main()
