# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Executable recovery, race, delivery and evidence regressions (no network)."""
from __future__ import annotations
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock
from urllib.parse import urlsplit

from tools import qikvrt_pipeline_contracts as c
from tools import qikvrt_contract_test_runner as runner

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "owner/repo"
H, T, B, BT = "a" * 40, "b" * 40, "c" * 40, "d" * 40
RUN_URL = "https://github.com/owner/repo/actions/runs/7"
OUTCOMES = {"envelope": "success", "checkout": "success", "contracts": "success",
            "qce_setup": "skipped", "qce_tools": "skipped", "qce": "skipped"}


def pull(number=101, base_ref="main"):
    return {"number": number, "draft": True, "state": "open", "body": c.MARKER,
            "head": {"sha": H, "ref": "fix/example", "repo": {"full_name": REPOSITORY}},
            "base": {"sha": B, "ref": base_ref, "repo": {"full_name": REPOSITORY}}}


class Server:
    def __init__(self):
        self.pr = pull()
        self.main, self.main_tree = B, BT
        self.head, self.tree = H, T
        self.runs, self.statuses, self.comments, self.calls = [], [], [], []
        self.dispatch_error = None
        self.lost_dispatch = False
        self.drop_dispatch = False
        self.comment_error = False
        self.status_error = False
        self.lost_status = False
        self.lost_comment = False
        self.drift_after_dispatch = False

    def add_run(self, status="queued", conclusion=None):
        self.runs.append({"id": 7, "event": "repository_dispatch", "status": status,
                          "conclusion": conclusion, "head_sha": B,
                          "display_title": c.run_title(101, H, B),
                          "path": ".github/workflows/" + c.WORKFLOW, "html_url": RUN_URL})

    def __call__(self, method, path, data=None):
        self.calls.append((method, path, copy.deepcopy(data)))
        path_only = urlsplit(path).path
        if method == "POST":
            if path_only.endswith("/dispatches"):
                if self.dispatch_error:
                    raise c.ApiError(self.dispatch_error)
                if not self.drop_dispatch:
                    self.add_run()
                if self.drift_after_dispatch:
                    self.main = "f" * 40
                if self.lost_dispatch:
                    raise c.ApiError(None)
                return None
            if "/statuses/" in path_only:
                if self.status_error:
                    raise c.ApiError(403)
                self.statuses.insert(0, dict(data))
                if self.lost_status:
                    raise c.ApiError(None)
                return {"id": 22}
            if path_only.endswith("/comments"):
                if self.comment_error:
                    raise c.ApiError(503)
                row = {"id": 2, "body": data["body"], "user": {"login": "github-actions[bot]"}}
                self.comments.append(row)
                if self.lost_comment:
                    raise c.ApiError(None)
                return row
            raise AssertionError((method, path))
        if path_only.endswith("/git/ref/heads/main"):
            return {"object": {"type": "commit", "sha": self.main}}
        if "/git/ref/heads/" in path_only:
            return {"object": {"type": "commit", "sha": self.head}}
        if "/git/commits/" in path_only:
            head = path_only.rsplit("/", 1)[1]
            return {"sha": head, "tree": {"sha": self.main_tree if head == self.main else self.tree}}
        if "/pulls/" in path_only:
            return copy.deepcopy(self.pr)
        if path_only.endswith("/runs"):
            return {"workflow_runs": copy.deepcopy(self.runs)}
        if path_only.endswith("/jobs"):
            return {"jobs": [{"id": 9, "status": "completed", "conclusion": "success"}]}
        if path_only.endswith("/statuses"):
            return copy.deepcopy(self.statuses)
        if path_only.endswith("/comments"):
            return copy.deepcopy(self.comments)
        raise AssertionError((method, path))

    def writes(self, suffix):
        return [x for x in self.calls if x[0] == "POST" and x[1].endswith(suffix)]


def resume(server):
    return c.resume(server, REPOSITORY, 101, H, T, B, "fix/example")


def deliver(server, outcomes=None):
    return c.deliver(server, REPOSITORY, 101, H, B, RUN_URL,
                     outcomes or dict(OUTCOMES), False, (H, T, True))


class PipelineContracts(unittest.TestCase):
    def test_resume_no_byte_change(self):
        server = Server()
        value = resume(server)
        self.assertEqual(value["state"], "VERIFIER_ACTIVE")
        self.assertEqual(len(server.writes("/dispatches")), 1)
        self.assertFalse(value["EFFECT_ACK_DONE"])

    def test_denied_dispatch_recovers_same_head(self):
        server = Server()
        server.dispatch_error = 403
        failed = resume(server)
        self.assertEqual(failed["first_blocker"], "API_HTTP_403")
        server.dispatch_error = None
        recovered = resume(server)
        self.assertEqual(recovered["state"], "VERIFIER_ACTIVE")
        self.assertEqual(recovered["head"], failed["head"])
        self.assertEqual(len(server.writes("/dispatches")), 2)
        resume(server)
        self.assertEqual(len(server.writes("/dispatches")), 2)

    def test_lost_dispatch_response_does_not_duplicate(self):
        server = Server()
        server.lost_dispatch = True
        self.assertEqual(resume(server)["state"], "VERIFIER_ACTIVE")
        self.assertEqual(resume(server)["state"], "VERIFIER_ACTIVE")
        self.assertEqual(len(server.writes("/dispatches")), 1)

    def test_transport_204_without_readback_is_blockade(self):
        server = Server()
        server.drop_dispatch = True
        value = resume(server)
        self.assertEqual(value["first_blocker"], "VERIFIER_DISPATCH_NOT_READ_BACK")
        self.assertEqual(value["classification"], "BLOCKADE")

    def test_terminal_failure_is_not_retried(self):
        server = Server()
        server.add_run("completed", "failure")
        server.statuses = [{"context": c.CONTEXT, "state": "failure", "target_url": RUN_URL}]
        self.assertEqual(resume(server)["first_blocker"], "EXACT_VERIFICATION_FAILED")
        self.assertFalse(server.writes("/dispatches"))

    def test_terminal_success_is_read_only_not_effect_ack(self):
        server = Server()
        server.add_run("completed", "success")
        server.statuses = [{"context": c.CONTEXT, "state": "success", "target_url": RUN_URL}]
        value = resume(server)
        self.assertEqual(value["classification"], "IDLE")
        self.assertFalse(value["PREDECESSOR_EVIDENCE_TRANSFER"])
        self.assertFalse(value["EFFECT_ACK_DONE"])
        self.assertFalse(server.writes("/dispatches"))

    def test_unadmitted_verifier_is_not_a_successful_terminal_result(self):
        server = Server()
        server.add_run("completed", "action_required")
        self.assertEqual(resume(server)["first_blocker"], "VERIFIER_NOT_ADMITTED_OR_UNEXECUTED")
        self.assertFalse(server.writes("/dispatches"))

    def test_duplicate_runs_are_explicitly_blocked(self):
        server = Server()
        server.add_run()
        server.add_run()
        self.assertEqual(resume(server)["first_blocker"], "DUPLICATE_EXACT_VERIFIER_RUNS")

    def test_legacy_status_requires_provenance_not_inheritance(self):
        server = Server()
        server.statuses = [{"context": c.CONTEXT, "state": "success"}]
        self.assertEqual(resume(server)["first_blocker"], "LEGACY_VERIFIER_REQUIRES_EXACT_RUN_EVIDENCE")
        self.assertFalse(server.writes("/dispatches"))

    def test_ref_and_base_drift_block_before_dispatch(self):
        for field in ("head", "tree", "main"):
            server = Server()
            setattr(server, field, "f" * 40)
            with self.subTest(field=field):
                self.assertEqual(resume(server)["classification"], "BLOCKADE")
                self.assertFalse(server.writes("/dispatches"))

    def test_drift_after_dispatch_never_claims_current_subject(self):
        server = Server()
        server.drift_after_dispatch = True
        value = resume(server)
        self.assertEqual(value["first_blocker"], "BASE_DRIFT")
        self.assertEqual(value["classification"], "BLOCKADE")

    def test_round_robin_stable_set(self):
        values = [pull(101), pull(102), pull(103)]
        self.assertEqual([c.select(values, REPOSITORY, n)["number"] for n in range(1, 7)],
                         [101, 102, 103, 101, 102, 103])
        # Historical selector is a negative control: it starves both successors.
        historical = [sorted(values, key=lambda p: p["number"])[0]["number"] for _ in range(3)]
        self.assertNotEqual(set(historical), {101, 102, 103})

    def test_staging_foreign_closed_and_ready_candidates_excluded(self):
        for change in ("staging", "foreign", "closed", "ready"):
            bad = pull(100)
            if change == "staging": bad["base"]["ref"] = "staging"
            if change == "foreign": bad["head"]["repo"]["full_name"] = "foreign/repo"
            if change == "closed": bad["state"] = "closed"
            if change == "ready": bad["draft"] = False
            with self.subTest(change=change):
                self.assertEqual(c.select([bad, pull(102)], REPOSITORY, 1)["number"], 102)

    def test_selector_requires_valid_identity_and_opportunity(self):
        with self.assertRaises(c.Block): c.select([pull()], REPOSITORY, 0)
        bad = pull()
        bad["head"]["ref"] = "fix/x\nfound=false"
        with self.assertRaises(c.Block): c.select([bad], REPOSITORY, 1)
        with self.assertRaises(c.Block): c.select([pull(), pull()], REPOSITORY, 1)
        self.assertIsNone(c.select([], REPOSITORY, 1))

    def test_incomplete_and_malformed_inventory_fails_closed(self):
        with self.assertRaisesRegex(c.Block, "BOUND_EXCEEDED"):
            c.listing(lambda *args: [{}] * 100, "repos/owner/repo/pulls")
        with self.assertRaisesRegex(c.Block, "SCHEMA_INVALID"):
            c.listing(lambda *args: [None], "repos/owner/repo/pulls")

    def test_comment_failure_cannot_overwrite_technical_success(self):
        server = Server()
        server.comment_error = True
        value = deliver(server)
        self.assertEqual(value["verification"], "success")
        self.assertEqual(value["first_blocker"], "COMMENT_DELIVERY_NOT_READ_BACK")
        self.assertEqual([x[2]["state"] for x in server.writes("/statuses/" + H)], ["success"])
        self.assertEqual(value["status_delivery"], "READ_BACK")

    def test_comment_failure_resumes_without_duplicate_comments(self):
        server = Server()
        server.comment_error = True
        deliver(server)
        server.comment_error = False
        self.assertEqual(deliver(server)["state"], "VERIFIED_AND_REPORTED")
        self.assertEqual(deliver(server)["state"], "VERIFIED_AND_REPORTED")
        self.assertEqual(len(server.comments), 1)

    def test_lost_status_and_comment_responses_require_readback(self):
        server = Server()
        server.lost_status = server.lost_comment = True
        self.assertEqual(deliver(server)["state"], "VERIFIED_AND_REPORTED")
        self.assertEqual(len(server.comments), 1)

    def test_status_denied_is_not_a_technical_failure(self):
        server = Server()
        server.status_error = True
        value = deliver(server)
        self.assertEqual(value["verification"], "success")
        self.assertEqual(value["first_blocker"], "STATUS_DELIVERY_NOT_READ_BACK")
        self.assertFalse(server.comments)

    def test_actual_technical_failure_is_preserved(self):
        server = Server()
        outcomes = {**OUTCOMES, "contracts": "failure"}
        value = deliver(server, outcomes)
        self.assertEqual(value["verification_first_blocker"], "CONTRACTS_FAILURE")
        self.assertEqual(server.statuses[0]["state"], "failure")
        self.assertFalse(server.comments)

    def test_unvalidated_envelope_never_writes_status(self):
        server = Server()
        value = deliver(server, {**OUTCOMES, "envelope": "failure"})
        self.assertEqual(value["first_blocker"], "ENVELOPE_NOT_VALIDATED_NO_STATUS_WRITE")
        self.assertFalse(server.writes("/statuses/" + H))

    def test_required_qce_skips_are_not_success(self):
        self.assertEqual(c.technical_result(OUTCOMES, True), ("failure", "QCE_SETUP_SKIPPED"))
        self.assertEqual(c.technical_result(OUTCOMES, False), ("success", None))

    def test_fingerprint_ignores_run_id_attempt_and_wall_clock(self):
        first = c.receipt("example", head=H, tree=T, base=B, first_blocker="DENIED")
        other = {**first, "run_id": 17, "created_at": "later", "attempt": 9}
        self.assertEqual(c.fingerprint(first), c.fingerprint(other))
        self.assertNotEqual(c.fingerprint(first), c.fingerprint({**other, "head": B}))
        self.assertNotEqual(c.fingerprint(first), c.fingerprint({**other, "first_blocker": None}))

    def test_successful_steps_with_wrong_final_checkout_never_publish_success(self):
        for binding in (None, (B, T, True), (H, BT, True), (H, T, False)):
            server = Server()
            value = c.deliver(server, REPOSITORY, 101, H, B, RUN_URL, dict(OUTCOMES), False, binding)
            with self.subTest(binding=binding):
                self.assertEqual(value["first_blocker"], "FINAL_CHECKOUT_NOT_BOUND")
                self.assertEqual(value["verification"], "UNVERIFIED")
                self.assertFalse(server.writes("/statuses/" + H))

    def test_continuation_failure_trap_writes_causal_receipt(self):
        source = (ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml").read_text()
        trap = next(line.strip() for line in source.splitlines() if line.strip().startswith("trap "))
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw) / "qikvrt-continuation"
            directory.mkdir()
            for failure, code in (("false", 1), ("exit 2", 2)):
                result = subprocess.run(["bash", "-ec", "phase=VERIFY_SUCCESSOR\n" + trap + "\n" + failure + "\n"],
                                        env=dict(os.environ, RUNNER_TEMP=raw), capture_output=True)
                self.assertEqual(result.returncode, code)
                value = json.loads((directory / "early-failure.json").read_text())
                self.assertEqual(value["first_blocker"], "VERIFY_SUCCESSOR")
                self.assertEqual(value["exit_code"], code)
                self.assertFalse(value["EFFECT_ACK_DONE"])

    def test_api_handles_empty_204_and_never_leaks_error_stderr(self):
        with mock.patch.object(c.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")):
            self.assertIsNone(c.api("POST", "repos/owner/repo/dispatches", {}))
        with mock.patch.object(c.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "secret sentinel HTTP 403")):
            with self.assertRaises(c.ApiError) as error:
                c.api("POST", "repos/owner/repo/dispatches", {})
            self.assertEqual(str(error.exception), "API_HTTP_403")

    def test_runner_rejects_skipped_missing_duplicate_and_incomplete_requirements(self):
        requirements = {"A": ["test.a"], "B": ["test.b"]}
        planned = ["test.a", "test.b"]
        good = [{"id": name, "outcome": "SUCCESS"} for name in planned]
        self.assertTrue(runner.coverage(requirements, planned, good))
        self.assertFalse(runner.coverage(requirements, planned, good[:1]))
        self.assertFalse(runner.coverage(requirements, planned, good + good[:1]))
        self.assertFalse(runner.coverage(requirements, planned, [good[0], {"id": "test.b", "outcome": "SKIPPED"}]))
        self.assertFalse(runner.coverage({"A": ["not.executed"]}, planned, good))

    def test_runner_records_failed_subtests_and_expected_failures(self):
        class Example(unittest.TestCase):
            def test_failed_subtest(self):
                with self.subTest(value=1): self.fail("injected")
            @unittest.expectedFailure
            def test_expected_failure(self): self.fail("injected")
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=runner.RecordedResult).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Example))
        self.assertEqual({v["outcome"] for v in result.executed}, {"FAILURE", "EXPECTED_FAILURE"})

    def test_production_workflow_wiring_has_no_byte_noop_early_exit(self):
        source = (ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml").read_text()
        start = source.index('if test "$merge_created" = false')
        block = source[start:source.index("\n      - name:", start)]
        self.assertNotIn("exit 0", block)
        self.assertIn('qikvrt-pipeline-contracts.py" resume', block)
        self.assertIn('qikvrt-pipeline-contracts.py" select', source)
        self.assertIn('git push origin "HEAD:refs/heads/${HEAD_REF}"', source)

    def test_runner_context_is_not_used_before_steps(self):
        # GitHub contexts reference: runner is unavailable in jobs.<id>.env.
        # Validate this specific contract before a workflow can be admitted.
        def valid(source):
            jobs = source.split("\njobs:\n", 1)[1]
            in_steps = False
            for line in jobs.splitlines():
                if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
                    in_steps = False
                if line == "    steps:":
                    in_steps = True
                if not in_steps and "${{" in line and "runner." in line:
                    return False
            return True
        for name in ("qikvrt_ci.yml", "qikvrt_autonomous_pr_continuation.yml", "qikvrt_autonomous_exact_head_verify.yml"):
            source = (ROOT / ".github/workflows" / name).read_text()
            self.assertTrue(valid(source), name)
            broken = source.replace("    steps:", "    env:\n      BAD: ${{ runner.temp }}\n    steps:", 1)
            self.assertFalse(valid(broken), name)

    def test_final_export_follows_checks_and_readback_and_excludes_history(self):
        source = (ROOT / ".github/workflows/qikvrt_ci.yml").read_text()
        self.assertLess(source.index("id: fixpoint"), source.index("id: final_evidence"))
        self.assertLess(source.index("id: final_evidence"), source.index("name: qikvrt-ci-final-"))
        block = source[source.index("      - name: Preserve final exact-subject evidence"):]
        self.assertNotIn("audit/**", block)
        self.assertIn("remote_final", source)

    def test_verifier_no_blanket_failure_rewrite_and_no_in_tree_qce_output(self):
        source = (ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml").read_text()
        self.assertNotIn("if: failure()", source)
        self.assertIn('STEPS_JSON: ${{ toJSON(steps) }}', source)
        self.assertIn('"$RUNNER_TEMP/qikvrt-verifier-reporter.py" deliver', source)
        self.assertIn('> "$RUNNER_TEMP/qce-autonomous-verification.json"', source)


class RealGitContracts(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="qikvrt-contract-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "source"
        self.root.mkdir()
        self.remote = Path(self.directory.name) / "remote.git"
        self.g("init", "--bare", str(self.remote), cwd=Path(self.directory.name))
        self.g("init")
        self.g("config", "user.name", "Contract fixture")
        self.g("config", "user.email", "fixture@example.invalid")
        (self.root / ".gitignore").write_text(".qikvrt/\n")
        (self.root / "source.txt").write_text("A\n")
        self.fixture_manifest = {"source_paths": ["source.txt"], "requirements": {"FIXTURE": ["fixture.test"]}}
        manifest = self.root / runner.MANIFEST
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps(self.fixture_manifest))
        self.g("add", ".")
        self.g("commit", "-m", "A")
        self.head = self.g("rev-parse", "HEAD")
        self.tree = self.g("rev-parse", "HEAD^{tree}")
        self.g("remote", "add", "origin", str(self.remote))
        self.g("push", "origin", "HEAD:refs/heads/fixture")
        self.evidence = Path(self.directory.name) / "evidence"
        (self.evidence / "tests").mkdir(parents=True)
        import hashlib
        self.test_receipt = {"schema": "qikvrt_executed_contract_tests_v1", "head": self.head,
                             "tree": self.tree, "committed_subject": True, "state": "TESTS_PASSED",
                             "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                             "executed": [{"id": "fixture.test", "outcome": "SUCCESS"}],
                             "requirements_satisfied": True,
                             "requirements": self.fixture_manifest["requirements"],
                             "planned_test_ids": ["fixture.test"],
                             "source_sha256": runner.source_digests(self.root, [runner.MANIFEST, "source.txt"])}
        self.write_receipts()
        self.outcomes = {"fixpoint_required": "false", "fixpoint": "skipped", "full_test": "success"}

    def g(self, *args, cwd=None):
        return subprocess.check_output(["git", *args], cwd=cwd or self.root,
                                       stderr=subprocess.DEVNULL, timeout=15).decode().strip()

    def read_api(self, method, path, data=None):
        self.assertEqual(method, "GET")
        if "/git/ref/" in path:
            head = self.g("rev-parse", "refs/heads/fixture", cwd=self.remote)
            return {"object": {"type": "commit", "sha": head}}
        head = path.rsplit("/", 1)[1]
        tree = self.g("rev-parse", head + "^{tree}", cwd=self.remote)
        return {"sha": head, "tree": {"sha": tree}}

    def write_receipts(self):
        for mode in ("normal", "optimized"):
            value = {**self.test_receipt, "optimization": mode == "optimized"}
            (self.evidence / "tests" / (mode + ".json")).write_text(json.dumps(value))

    def final(self):
        return c.final_ci(self.read_api, self.root, REPOSITORY, "heads/fixture", self.evidence, self.outcomes)

    def test_final_receipt_has_exact_current_head_tree_and_no_effect_ack(self):
        value = self.final()
        self.assertEqual(value["state"], "EXACT_TESTS_AND_READBACK_VERIFIED")
        self.assertEqual((value["head"], value["tree"]), (self.head, self.tree))
        self.assertFalse(value["EFFECT_ACK_DONE"])
        self.assertFalse(value["historical_evidence_imported"])

    def test_final_ci_rejects_remote_advanced_during_tests(self):
        (self.root / "source.txt").write_text("B\n")
        self.g("add", ".")
        self.g("commit", "-m", "B")
        self.g("push", "origin", "HEAD:refs/heads/fixture")
        self.g("checkout", "--detach", self.head)
        self.assertEqual(self.final()["first_blocker"], "FINAL_REMOTE_HEAD_TREE_DRIFT")

    def test_final_ci_rejects_missing_execution_not_substituted_by_historical_pass(self):
        (self.evidence / "tests/normal.json").unlink()
        (self.evidence / "HISTORICAL_PASS.json").write_text('{"state":"PASS"}')
        self.assertEqual(self.final()["first_blocker"], "FINAL_EVIDENCE_MISSING_OR_INVALID")

    def test_final_ci_rejects_wrong_head_tree_dirty_or_mode(self):
        for field, value in (("head", "e" * 40), ("tree", "f" * 40), ("committed_subject", False),
                             ("state", "PASS"), ("executed", []), ("requirements_satisfied", False)):
            old = copy.deepcopy(self.test_receipt)
            self.test_receipt[field] = value
            self.write_receipts()
            with self.subTest(field=field):
                self.assertEqual(self.final()["first_blocker"], "TEST_EXECUTION_EVIDENCE_UNBOUND")
            self.test_receipt = old
        self.write_receipts()
        path = self.evidence / "tests/optimized.json"
        raw = json.loads(path.read_text()); raw["optimization"] = False; path.write_text(json.dumps(raw))
        self.assertEqual(self.final()["first_blocker"], "TEST_EXECUTION_EVIDENCE_UNBOUND")

    def test_final_ci_rejects_changed_tested_source(self):
        (self.root / "source.txt").write_text("modified after tests\n")
        self.assertEqual(self.final()["first_blocker"], "TEST_EXECUTION_EVIDENCE_UNBOUND")

    def test_final_ci_cannot_upgrade_failed_make_or_unverified_fixpoint(self):
        for changes in ({"full_test": "failure"}, {"fixpoint": "success"},
                        {"fixpoint_required": "true", "fixpoint": "skipped"}):
            self.outcomes = {"fixpoint_required": "false", "fixpoint": "skipped", "full_test": "success", **changes}
            with self.subTest(changes=changes):
                self.assertEqual(self.final()["classification"], "BLOCKADE")

    def test_final_ci_rejects_forged_coverage_flag_or_omitted_source(self):
        original = copy.deepcopy(self.test_receipt)
        for field, value in (("executed", [{"id": "fixture.test", "outcome": "SKIPPED"}]),
                             ("requirements", {"FORGED": ["fixture.test"]}),
                             ("planned_test_ids", []), ("source_sha256", {})):
            self.test_receipt = {**original, field: value}
            self.write_receipts()
            with self.subTest(field=field):
                self.assertEqual(self.final()["first_blocker"], "TEST_EXECUTION_EVIDENCE_UNBOUND")

    def test_real_runner_executes_and_binds_exact_source_in_both_modes(self):
        import shutil
        destination = self.root / "tools/qikvrt_contract_test_runner.py"
        destination.parent.mkdir()
        shutil.copyfile(ROOT / "tools/qikvrt_contract_test_runner.py", destination)
        (self.root / "fixture_case.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n    def test_runs(self):\n        self.assertEqual(2 + 2, 4)\n")
        manifest = {"schema": "qikvrt_pipeline_contract_test_manifest_v1", "modules": ["fixture_case"],
                    "source_paths": ["fixture_case.py", "tools/qikvrt_contract_test_runner.py"],
                    "requirements": {"CASE": ["fixture_case.T.test_runs"]}}
        (self.root / runner.MANIFEST).write_text(json.dumps(manifest))
        self.g("add", "."); self.g("commit", "-m", "real runner fixture")
        self.head, self.tree = self.g("rev-parse", "HEAD"), self.g("rev-parse", "HEAD^{tree}")
        self.g("push", "origin", "HEAD:refs/heads/fixture")
        env = dict(os.environ, QIKVRT_CONTRACT_EVIDENCE_DIR=str(self.evidence / "tests"))
        import sys
        for flags in ([], ["-O"]):
            result = subprocess.run([sys.executable, "-S", "-B", *flags, str(destination)],
                                    cwd=self.root, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = self.final()
        self.assertEqual(value["state"], "EXACT_TESTS_AND_READBACK_VERIFIED")
        self.assertEqual(value["test_receipts"][0]["test_ids"], ["fixture_case.T.test_runs"])
        # An actually skipped required test remains HOLD even after historical success.
        (self.root / "fixture_case.py").write_text(
            "import unittest\nclass T(unittest.TestCase):\n    @unittest.skip('injected')\n    def test_runs(self):\n        pass\n")
        skipped = subprocess.run([sys.executable, "-S", "-B", str(destination)],
                                 cwd=self.root, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(skipped.returncode, 2)
        evidence = json.loads((self.evidence / "tests/normal.json").read_text())
        self.assertEqual(evidence["executed"][0]["outcome"], "SKIPPED")
        self.assertFalse(evidence["requirements_satisfied"])
        self.assertFalse(evidence["committed_subject"])

    def test_real_fixed_fixpoint_guard_rejects_race(self):
        source = (ROOT / ".github/workflows/qikvrt_ci.yml").read_text()
        start = source.index('              remote_final=')
        end = source.index('              echo "QIKVRT_FIXPOINT_REACHED', start)
        guard = textwrap.dedent(source[start:end])
        env = dict(os.environ, TARGET_REF="fixture", subject=self.head, tree=self.tree)
        stable = subprocess.run(["bash", "-ec", guard], cwd=self.root, env=env, capture_output=True)
        self.assertEqual(stable.returncode, 0)
        (self.root / "source.txt").write_text("B\n")
        self.g("add", "."); self.g("commit", "-m", "B")
        self.g("push", "origin", "HEAD:refs/heads/fixture")
        self.g("checkout", "--detach", self.head)
        drifted = subprocess.run(["bash", "-ec", guard], cwd=self.root, env=env, capture_output=True)
        self.assertNotEqual(drifted.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
