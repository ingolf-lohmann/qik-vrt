# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Executable partial-failure regressions for the production materializer."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "materializer_under_test", ROOT / "tools/qikvrt_self_heal_pr_materializer.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
B, T, H, OTHER = (c * 40 for c in "abcd")
CANDIDATE = MODULE.Candidate("owner/repo", B, T, "e" * 64, ("SHA256SUMS.txt",), "f" * 64)
PAYLOAD = b"hash  file\n"
BLOB = hashlib.sha1(f"blob {len(PAYLOAD)}\0".encode() + PAYLOAD).hexdigest()


class FakeGit:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        if args[0] == "ls-tree":
            return f"100644 blob {BLOB}\tSHA256SUMS.txt"
        raise AssertionError(f"unexpected Git write/operation: {args}")

    def bytes(self, *args):
        self.calls.append(args)
        if args != ("cat-file", "blob", BLOB):
            raise AssertionError(args)
        return PAYLOAD


class FakeAPI:
    def __init__(self, branch=True, pr=False):
        self.head = H if branch else None
        self.base = B
        self.tree = T
        self.parents = [B]
        self.prs = [self.make_pr()] if pr else []
        self.calls = []
        self.create_mode = "ok"
        self.ref_mode = "ok"
        self.read_error = None
        self.commit_error = None
        self.bad_tree = False
        self.bad_blob = False
        self.after_pr_read = None
        self.patch_mode = "ok"
        self.runs = []
        if pr:
            self.add_run()

    def add_run(self):
        from tools import qikvrt_pipeline_contracts as pipeline
        self.runs.append({"id": 17, "event": "repository_dispatch", "status": "queued",
                          "conclusion": None, "display_title": pipeline.run_title(7, H, B),
                          "path": ".github/workflows/" + pipeline.WORKFLOW,
                          "html_url": "https://github.com/owner/repo/actions/runs/17"})

    def make_pr(self):
        return {"number": 7, "state": "open", "draft": True,
                "body": f"{MODULE.MARKER}\n{MODULE.CONTINUATION_MARKER}",
                "head": {"sha": H, "ref": CANDIDATE.branch,
                         "repo": {"full_name": CANDIDATE.repository}},
                "base": {"sha": B, "ref": "main",
                         "repo": {"full_name": CANDIDATE.repository}}}

    def __call__(self, method, path, data=None):
        self.calls.append((method, path, copy.deepcopy(data)))
        if method == "GET":
            if "/contents/.github/workflows/" in path:
                payload = (ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml").read_bytes()
                blob = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
                return {"type": "file", "path": ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
                        "encoding": "base64", "content": base64.b64encode(payload).decode(), "sha": blob}
            if "/actions/workflows/" in path and "/runs?" in path:
                return {"workflow_runs": copy.deepcopy(self.runs)}
            if "/statuses?" in path:
                return []
            if path.endswith("/git/ref/heads/main"):
                return {"object": {"type": "commit", "sha": self.base}}
            if "/git/ref/heads/" in path:
                if self.read_error:
                    raise MODULE.ApiFailure(self.read_error)
                if self.head is None:
                    raise MODULE.ApiFailure(404)
                return {"object": {"type": "commit", "sha": self.head}}
            if "/git/commits/" in path:
                if self.commit_error:
                    raise MODULE.ApiFailure(self.commit_error)
                sha = path.rsplit("/", 1)[1]
                if sha == B:
                    return {"sha": B, "tree": {"sha": OTHER}, "parents": []}
                return {"sha": sha, "tree": {"sha": self.tree},
                        "parents": [{"sha": p} for p in self.parents]}
            if "/pulls?" in path:
                if "state=all" not in path or "base=" in path:
                    raise AssertionError(path)
                return copy.deepcopy(self.prs)
            if path.endswith("/pulls/7"):
                value = copy.deepcopy(self.prs[0])
                if self.after_pr_read:
                    self.after_pr_read(self)
                return value
        if method == "POST":
            if path.endswith("/dispatches"):
                self.add_run()
                return None
            if path.endswith("/git/blobs"):
                if base64.b64decode(data["content"]) != PAYLOAD:
                    raise AssertionError("blob bytes differ")
                return {"sha": OTHER if self.bad_blob else BLOB}
            if path.endswith("/git/trees"):
                return {"sha": OTHER if self.bad_tree else T}
            if path.endswith("/git/commits"):
                if data["parents"] != [B] or data["tree"] != T:
                    raise AssertionError("commit binding differs")
                return {"sha": H}
            if path.endswith("/git/refs"):
                if data != {"ref": f"refs/heads/{CANDIDATE.branch}", "sha": H}:
                    raise AssertionError("ref binding differs")
                if self.ref_mode == "denied":
                    raise MODULE.ApiFailure(403)
                self.head = OTHER if self.ref_mode == "racing_wrong_tree" else H
                if self.ref_mode == "racing_wrong_tree":
                    self.tree = OTHER
                    raise MODULE.ApiFailure(422)
                if self.ref_mode == "lost":
                    raise MODULE.ApiFailure(None)
                return {"object": {"type": "commit", "sha": self.head}}
            if path.endswith("/pulls"):
                if data["draft"] is not True or data["base"] != "main":
                    raise AssertionError("PR boundary differs")
                if self.create_mode == "denied":
                    raise MODULE.ApiFailure(403)
                if self.create_mode == "lost_without_effect":
                    raise MODULE.ApiFailure(None)
                if self.create_mode != "false_success":
                    self.prs = [self.make_pr()]
                    self.prs[0]["body"] = data["body"]
                if self.create_mode == "lost_after_effect":
                    raise MODULE.ApiFailure(None)
                if self.create_mode == "race_after_effect":
                    raise MODULE.ApiFailure(422)
                return copy.deepcopy(self.prs[0]) if self.prs else {}
        if method == "PATCH" and path.endswith("/pulls/7"):
            if set(data) != {"body"}:
                raise AssertionError("continuation may only update the verified PR body")
            if self.patch_mode == "denied":
                raise MODULE.ApiFailure(403)
            if self.patch_mode != "false_success":
                self.prs[0]["body"] = data["body"]
            if self.patch_mode == "lost_after_effect":
                raise MODULE.ApiFailure(None)
            return copy.deepcopy(self.prs[0])
        raise AssertionError(f"unexpected API operation: {method} {path}")


class MaterializationTests(unittest.TestCase):
    def run_materializer(self, api):
        git = FakeGit()
        result = MODULE.materialize(CANDIDATE, api, git)
        self.assertFalse(result["EFFECT_ACK_DONE"])
        self.assertFalse(result["PREDECESSOR_EVIDENCE_TRANSFER"])
        self.assertFalse(result["transport_ack_is_effect_ack"])
        self.assertTrue(all(method in ("GET", "POST", "PATCH") for method, _, _ in api.calls))
        self.assertFalse(any("/reviews" in path or "/merge" in path or "/permissions" in path
                             for _, path, _ in api.calls))
        return result

    def test_branch_creation_then_permission_failure_then_resume_same_head(self):
        api = FakeAPI(branch=False)
        api.create_mode = "denied"
        first = self.run_materializer(api)
        self.assertEqual(first["first_blocker"], "PR_WRITER_CAPABILITY_UNAVAILABLE")
        self.assertEqual(api.head, H)
        self.assertEqual(len(api.prs), 0)
        ref_writes = sum(path.endswith("/git/refs") for m, path, _ in api.calls if m == "POST")
        api.create_mode = "ok"
        second = self.run_materializer(api)
        self.assertEqual(second["state"], "PR_MATERIALIZED")
        self.assertEqual(second["candidate_head"], first["candidate_head"])
        self.assertEqual(len(api.prs), 1)
        self.assertEqual(sum(path.endswith("/git/refs") for m, path, _ in api.calls if m == "POST"), ref_writes)
        before = len(api.calls)
        third = self.run_materializer(api)
        self.assertEqual(third["state"], "PR_ALREADY_MATERIALIZED")
        self.assertEqual(third["transition_fingerprint"], second["transition_fingerprint"])
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls[before:]))

    def test_existing_branch_without_pr_is_resumed_not_noop(self):
        result = self.run_materializer(FakeAPI())
        self.assertEqual(result["state"], "PR_MATERIALIZED")
        self.assertTrue(result["pr_create_attempted"])

    def test_created_repair_is_selectable_without_another_owner_interaction(self):
        from tools import qikvrt_pipeline_contracts as continuation
        api = FakeAPI()
        result = self.run_materializer(api)
        self.assertTrue(result["continuation_enabled"])
        self.assertEqual(continuation.select(api.prs, CANDIDATE.repository, 1)["number"], 7)
        self.assertIn(MODULE.MARKER, api.prs[0]["body"])
        self.assertFalse(result["continuation_bind_attempted"])

    def test_legacy_draft_continuation_gap_is_repaired_then_becomes_read_only(self):
        from tools import qikvrt_pipeline_contracts as continuation
        api = FakeAPI(pr=True)
        original = MODULE.MARKER + "\n\nExisting exact candidate text."
        api.prs[0]["body"] = original
        self.assertIsNone(continuation.select(api.prs, CANDIDATE.repository, 1))
        first = self.run_materializer(api)
        self.assertEqual(first["classification"], "WORK")
        self.assertTrue(first["continuation_enabled"])
        self.assertTrue(api.prs[0]["body"].startswith(original))
        self.assertEqual(continuation.select(api.prs, CANDIDATE.repository, 1)["number"], 7)
        writes = [(m, p, d) for m, p, d in api.calls if m != "GET"]
        self.assertEqual(writes, [("PATCH", "repos/owner/repo/pulls/7", {"body": api.prs[0]["body"]})])
        before = len(api.calls)
        second = self.run_materializer(api)
        self.assertEqual(second["classification"], "IDLE")
        self.assertEqual(second["transition_fingerprint"], first["transition_fingerprint"])
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls[before:]))

    def test_continuation_write_requires_readback_and_never_blindly_retries(self):
        for mode, blocker in (("denied", "PR_CONTINUATION_WRITER_CAPABILITY_UNAVAILABLE"),
                              ("false_success", "PR_CONTINUATION_BINDING_NOT_READ_BACK"),
                              ("lost_after_effect", None)):
            with self.subTest(mode=mode):
                api = FakeAPI(pr=True)
                api.prs[0]["body"] = MODULE.MARKER
                api.patch_mode = mode
                result = self.run_materializer(api)
                self.assertEqual(result["first_blocker"], blocker)
                self.assertEqual(sum(m == "PATCH" for m, _, _ in api.calls), 1)
                self.assertFalse(any(m == "POST" for m, _, _ in api.calls))
                self.assertEqual(result["state"] == "HOLD", blocker is not None)

    def test_ready_or_unbound_pr_never_receives_continuation_opt_in(self):
        for ready in (False, True):
            with self.subTest(ready=ready):
                api = FakeAPI(pr=True)
                api.prs[0]["body"] = MODULE.MARKER
                if ready:
                    api.prs[0]["draft"] = False
                else:
                    api.prs[0]["head"]["sha"] = OTHER
                result = self.run_materializer(api)
                self.assertFalse(result["continuation_enabled"])
                self.assertTrue(all(m == "GET" for m, _, _ in api.calls))
                self.assertEqual(result["state"], "HOLD")

    def test_continuation_metadata_drift_prevents_body_write(self):
        api = FakeAPI(pr=True)
        api.prs[0]["body"] = MODULE.MARKER
        def human_edit(value):
            value.prs[0]["body"] += "\nLater human correction."
            value.after_pr_read = None
        api.after_pr_read = human_edit
        result = self.run_materializer(api)
        self.assertEqual(result["first_blocker"], "PR_CONTINUATION_METADATA_DRIFT")
        self.assertIn("Later human correction.", api.prs[0]["body"])
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_existing_valid_pr_is_read_only(self):
        api = FakeAPI(pr=True)
        self.assertEqual(self.run_materializer(api)["classification"], "IDLE")
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_unchanged_permission_failure_has_stable_fingerprint(self):
        api = FakeAPI()
        api.create_mode = "denied"
        first = self.run_materializer(api)
        second = self.run_materializer(api)
        self.assertEqual(first["transition_fingerprint"], second["transition_fingerprint"])
        self.assertEqual(second["classification"], "BLOCKADE")

    def test_lost_or_racing_post_response_is_reobserved_not_retried(self):
        for mode in ("lost_after_effect", "race_after_effect"):
            with self.subTest(mode=mode):
                api = FakeAPI()
                api.create_mode = mode
                self.assertEqual(self.run_materializer(api)["state"], "PR_MATERIALIZED")
                self.assertEqual(sum(m == "POST" and p.endswith("/pulls") for m, p, _ in api.calls), 1)

    def test_successful_transport_without_pr_is_not_success(self):
        api = FakeAPI()
        api.create_mode = "false_success"
        self.assertEqual(self.run_materializer(api)["first_blocker"], "PR_CREATION_NOT_READ_BACK")

    def test_lost_post_without_effect_is_bounded_and_resumable(self):
        api = FakeAPI()
        api.create_mode = "lost_without_effect"
        self.assertEqual(self.run_materializer(api)["state"], "HOLD")
        self.assertEqual(sum(m == "POST" and p.endswith("/pulls") for m, p, _ in api.calls), 1)
        api.create_mode = "ok"
        self.assertEqual(self.run_materializer(api)["state"], "PR_MATERIALIZED")

    def test_lost_branch_create_response_is_read_back(self):
        api = FakeAPI(branch=False)
        api.ref_mode = "lost"
        self.assertEqual(self.run_materializer(api)["state"], "PR_MATERIALIZED")

    def test_permission_error_is_not_branch_absence(self):
        api = FakeAPI()
        api.read_error = 403
        self.assertEqual(self.run_materializer(api)["first_blocker"], "API_HTTP_403")
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_branch_write_denied_is_not_success(self):
        api = FakeAPI(branch=False)
        api.ref_mode = "denied"
        self.assertEqual(self.run_materializer(api)["first_blocker"], "BRANCH_WRITER_CAPABILITY_UNAVAILABLE")
        self.assertFalse(any(path.endswith("/pulls") for m, path, _ in api.calls if m == "POST"))

    def test_foreign_tree_or_parent_blocks_without_write(self):
        for field, value in (("tree", OTHER), ("parents", [OTHER]), ("parents", [B, OTHER])):
            with self.subTest(field=field, value=value):
                api = FakeAPI()
                setattr(api, field, value)
                self.assertEqual(self.run_materializer(api)["first_blocker"], "EXISTING_BRANCH_BINDING_MISMATCH")
                self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_concurrent_ref_create_is_not_overwritten(self):
        api = FakeAPI(branch=False)
        api.ref_mode = "racing_wrong_tree"
        self.assertEqual(self.run_materializer(api)["first_blocker"], "EXISTING_BRANCH_BINDING_MISMATCH")
        self.assertEqual(api.head, OTHER)
        self.assertFalse(any(m == "PATCH" for m, _, _ in api.calls))

    def test_main_drift_before_any_write(self):
        api = FakeAPI()
        api.base = OTHER
        self.assertEqual(self.run_materializer(api)["first_blocker"], "BASE_DRIFT")
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_main_or_head_drift_after_pr_readback(self):
        for field, expected in (("base", "BASE_DRIFT"), ("head", "CANDIDATE_HEAD_DRIFT")):
            with self.subTest(field=field):
                api = FakeAPI(pr=True)
                api.after_pr_read = lambda a: setattr(a, field, OTHER)
                self.assertEqual(self.run_materializer(api)["first_blocker"], expected)

    def test_closed_pr_is_not_duplicated_or_reopened(self):
        api = FakeAPI(pr=True)
        api.prs[0]["state"] = "closed"
        self.assertEqual(self.run_materializer(api)["first_blocker"], "CANDIDATE_PR_CLOSED")
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_late_branch_drift_cannot_leave_materialized_success_state(self):
        class LateDrift(FakeAPI):
            reads = 0
            def __call__(self, method, path, data=None):
                value = super().__call__(method, path, data)
                if method == "GET" and path.endswith("/git/commits/" + H):
                    self.reads += 1
                    if self.reads == 5:
                        self.head = OTHER
                return value
        value = self.run_materializer(LateDrift(pr=True))
        self.assertEqual(value["first_blocker"], "CANDIDATE_HEAD_DRIFT")
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["classification"], "BLOCKADE")

    def test_ready_pr_is_not_demoted(self):
        api = FakeAPI(pr=True)
        api.prs[0]["draft"] = False
        self.assertEqual(self.run_materializer(api)["first_blocker"], "READY_PR_REQUIRES_NATIVE_REVIEW_BOUNDARY")
        self.assertFalse(api.prs[0]["draft"])

    def test_missing_branch_with_existing_pr_is_not_recreated(self):
        api = FakeAPI(branch=False, pr=True)
        self.assertEqual(self.run_materializer(api)["first_blocker"], "PR_EXISTS_WITHOUT_CANDIDATE_BRANCH")
        self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_duplicate_or_incomplete_pr_enumeration_blocks(self):
        for count, expected in ((2, "DUPLICATE_CANDIDATE_PRS"), (100, "PR_ENUMERATION_INCOMPLETE")):
            with self.subTest(count=count):
                api = FakeAPI()
                api.prs = [api.make_pr()] * count
                self.assertEqual(self.run_materializer(api)["first_blocker"], expected)
                self.assertTrue(all(m == "GET" for m, _, _ in api.calls))

    def test_wrong_pr_bindings_and_marker_block(self):
        for side, field, value in (("head", "sha", OTHER), ("head", "ref", "foreign"),
                                   ("base", "sha", OTHER), ("base", "ref", "foreign"),
                                   ("head", "repo", {"full_name": "other/repo"})):
            with self.subTest(side=side, field=field):
                api = FakeAPI(pr=True)
                api.prs[0][side][field] = value
                self.assertEqual(self.run_materializer(api)["first_blocker"], "PR_EXACT_BINDING_MISMATCH")
        api = FakeAPI(pr=True)
        api.prs[0]["body"] = "unbound proposal"
        self.assertEqual(self.run_materializer(api)["first_blocker"], "PR_EXACT_BINDING_MISMATCH")

    def test_blob_and_tree_write_mismatch_stops_before_ref(self):
        for field in ("bad_blob", "bad_tree"):
            with self.subTest(field=field):
                api = FakeAPI(branch=False)
                setattr(api, field, True)
                self.assertEqual(self.run_materializer(api)["state"], "HOLD")
                self.assertIsNone(api.head)

    def test_malformed_readback_is_hold(self):
        api = FakeAPI(pr=True)
        api.prs[0]["head"]["repo"] = None
        self.assertEqual(self.run_materializer(api)["first_blocker"], "READBACK_SCHEMA_INVALID")


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous_cwd = os.getcwd()
        os.chdir(self.directory.name)
        self.git = MODULE.Git()
        self.git("init", "-q")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        pathlib.Path("SHA256SUMS.txt").write_bytes(b"old\n")
        self.git("add", "SHA256SUMS.txt")
        self.git("commit", "-qm", "fixture base")
        self.base = self.git("rev-parse", "HEAD")
        pathlib.Path("SHA256SUMS.txt").write_bytes(PAYLOAD)
        self.controller = types.ModuleType("tools.qikvrt_autonomous_self_heal")
        self.controller.SelfHealBlock = RuntimeError
        self.controller.load_contract = lambda: {"candidate_contract": {"materialization": {
            "completion_predicate": "EXACT_CURRENT_BASE_HEAD_TREE_PR_READBACK"}}}
        self.controller.allowed_paths = lambda _: {"SHA256SUMS.txt"}
        self.controller.semantic_fingerprint = lambda paths: hashlib.sha256(
            b"".join(pathlib.Path(p).read_bytes() for p in sorted(paths))).hexdigest()
        self.controller.candidate_identity = lambda base, fingerprint: hashlib.sha256(
            (base + "\0" + fingerprint).encode()).hexdigest()
        fingerprint = self.controller.semantic_fingerprint(["SHA256SUMS.txt"])
        self.receipt = {"observed_base_revision": self.base, "changed_paths": ["SHA256SUMS.txt"],
                        "state": "CANDIDATE_READY", "external_effect": "NONE",
                        "completion_claims": {"EFFECT_ACK_DONE": False},
                        "semantic_fingerprint": fingerprint,
                        "candidate_identity": self.controller.candidate_identity(self.base, fingerprint)}
        # Only the existing contract loader is stubbed here; Git/index/bytes are real.
        self.modules = mock.patch.dict(sys.modules, {
            "tools.qikvrt_autonomous_self_heal": self.controller})
        self.modules.start()
        import tools
        self.parent = mock.patch.object(tools, "qikvrt_autonomous_self_heal", self.controller, create=True)
        self.parent.start()

    def tearDown(self):
        self.parent.stop()
        self.modules.stop()
        os.chdir(self.previous_cwd)
        self.directory.cleanup()

    def test_real_git_staging_binds_exact_tree_without_commit_or_ref_change(self):
        c = MODULE.prepare(self.receipt, "owner/repo", self.git)
        self.assertEqual(c.tree, self.git("write-tree"))
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base)
        self.assertEqual(c.base, self.base)
        self.assertEqual(self.git.bytes("show", ":SHA256SUMS.txt"), PAYLOAD)

    def test_foreign_or_duplicate_paths_are_rejected(self):
        for paths in ([".github/workflows/foreign.yml"], ["SHA256SUMS.txt"] * 2, [17]):
            with self.subTest(paths=paths):
                self.receipt["changed_paths"] = paths
                with self.assertRaisesRegex(MODULE.Block, "CANDIDATE_PATHS_NOT_ALLOWLISTED"):
                    MODULE.prepare(self.receipt, "owner/repo", self.git)

    def test_existing_index_or_untracked_files_block(self):
        self.git("add", "SHA256SUMS.txt")
        with self.assertRaisesRegex(MODULE.Block, "LOCAL_CANDIDATE_BINDING_MISMATCH"):
            MODULE.prepare(self.receipt, "owner/repo", self.git)
        self.git("reset", "-q", "HEAD")
        pathlib.Path("foreign.txt").write_text("untracked")
        with self.assertRaisesRegex(MODULE.Block, "LOCAL_CANDIDATE_BINDING_MISMATCH"):
            MODULE.prepare(self.receipt, "owner/repo", self.git)

    def test_changed_bytes_after_receipt_block(self):
        pathlib.Path("SHA256SUMS.txt").write_bytes(b"different\n")
        with self.assertRaisesRegex(MODULE.Block, "CANDIDATE_FINGERPRINT_MISMATCH"):
            MODULE.prepare(self.receipt, "owner/repo", self.git)

    def test_bad_base_effect_or_repository_block(self):
        for key, value in (("observed_base_revision", 1), ("state", "NOOP"),
                           ("external_effect", "PUBLIC_RELEASE")):
            with self.subTest(key=key):
                bad = dict(self.receipt, **{key: value})
                with self.assertRaises(MODULE.Block):
                    MODULE.prepare(bad, "owner/repo", self.git)
        with self.assertRaises(MODULE.Block):
            MODULE.prepare(self.receipt, "https://foreign.invalid", self.git)

    def test_symlink_candidate_is_not_materialized(self):
        path = pathlib.Path("SHA256SUMS.txt")
        path.unlink()
        path.symlink_to(".git/HEAD")
        fp = self.controller.semantic_fingerprint([str(path)])
        self.receipt.update(semantic_fingerprint=fp,
                            candidate_identity=self.controller.candidate_identity(self.base, fp))
        with self.assertRaisesRegex(MODULE.Block, "CANDIDATE_FILE_MODE_INVALID"):
            MODULE.prepare(self.receipt, "owner/repo", self.git)

    def test_contract_failure_is_a_causal_block(self):
        self.controller.load_contract = mock.Mock(side_effect=RuntimeError("private detail"))
        with self.assertRaisesRegex(MODULE.Block, "CONTROLLER_CONTRACT_INVALID"):
            MODULE.prepare(self.receipt, "owner/repo", self.git)


class APIAdapterTests(unittest.TestCase):
    def test_rest_method_host_and_json_are_bound(self):
        process = subprocess.CompletedProcess([], 0, '{"number": 7}', "")
        with mock.patch.object(MODULE.subprocess, "run", return_value=process) as run:
            self.assertEqual(MODULE.GitHubAPI()("POST", "repos/owner/repo/pulls", {"draft": True}), {"number": 7})
        argv = run.call_args.args[0]
        self.assertEqual(argv[:6], ["gh", "api", "--hostname", "github.com", "--method", "POST"])
        self.assertEqual(json.loads(run.call_args.kwargs["input"]), {"draft": True})
        self.assertEqual(run.call_args.kwargs["timeout"], 60)

    def test_error_diagnostics_do_not_expose_stderr_credentials(self):
        process = subprocess.CompletedProcess([], 1, "", "private-secret HTTP 403")
        with mock.patch.object(MODULE.subprocess, "run", return_value=process):
            with self.assertRaises(MODULE.ApiFailure) as caught:
                MODULE.GitHubAPI()("GET", "repos/owner/repo/pulls")
        self.assertEqual(str(caught.exception), "API_HTTP_403")
        self.assertNotIn("private-secret", str(caught.exception))

    def test_timeout_is_not_success(self):
        with mock.patch.object(MODULE.subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 60)):
            with self.assertRaisesRegex(MODULE.ApiFailure, "API_TRANSPORT_UNCERTAIN"):
                MODULE.GitHubAPI()("POST", "repos/owner/repo/pulls", {"draft": True})

    def test_invalid_json_is_not_success(self):
        process = subprocess.CompletedProcess([], 0, "not json", "")
        with mock.patch.object(MODULE.subprocess, "run", return_value=process):
            with self.assertRaisesRegex(MODULE.Block, "API_RESPONSE_INVALID"):
                MODULE.GitHubAPI()("GET", "repos/owner/repo/pulls")


class WorkflowIntegrationTests(unittest.TestCase):
    def test_contract_scopes_noop_without_expanding_repair_authority(self):
        contract = json.loads((ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json").read_text())
        self.assertEqual(contract["execution_model"]["unchanged_semantic_fingerprint_scope"],
                         "CANDIDATE_BYTES_ONLY_NOT_PENDING_MATERIALIZATION")
        boundary = contract["candidate_contract"]["materialization"]
        self.assertEqual(boundary["completion_predicate"], "EXACT_CURRENT_BASE_HEAD_TREE_PR_READBACK")
        self.assertFalse(boundary["automatic_permission_change"])
        self.assertFalse(boundary["self_approval"])
        self.assertFalse(boundary["requires_repeated_chat_authorization"])
        self.assertEqual(boundary["draft_continuation_opt_in"], MODULE.CONTINUATION_MARKER)
        allowed = {p for h in contract["allowlisted_handlers"] for p in h["mutable_paths"]}
        self.assertNotIn("tools/qikvrt_self_heal_pr_materializer.py", allowed)
        self.assertNotIn(".github/workflows/qikvrt_autonomous_self_heal.yml", allowed)

    def test_historical_early_exit_is_a_reproducible_negative_control(self):
        # Exact defective guard from workflow blob 3bc666cd2164cf24828d195eed89c1d6e1fefcd3.
        guard = """set -euo pipefail
branch="automation/self-heal-${CANDIDATE_ID:0:24}"
if gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/${branch}" >/dev/null 2>&1; then
  exit 0
fi
gh pr create
"""
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            shim = root / "gh"
            shim.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\nexit 0\n')
            shim.chmod(0o700)
            calls = root / "calls"
            result = subprocess.run(["bash", "-c", guard], capture_output=True, text=True, timeout=10,
                                    env={"PATH": f"{root}:/usr/bin:/bin", "CALLS": str(calls),
                                         "CANDIDATE_ID": CANDIDATE.identity, "GITHUB_REPOSITORY": "owner/repo"})
            self.assertEqual(result.returncode, 0)
            self.assertIn("git/ref/heads/automation/self-heal-", calls.read_text())
            self.assertNotIn("pr create", calls.read_text())

    def test_production_workflow_executes_helper_and_preserves_failure_receipt(self):
        source = (ROOT / ".github/workflows/qikvrt_autonomous_self_heal.yml").read_text()
        self.assertIn("python3 -B -m tools.qikvrt_self_heal_pr_materializer", source)
        self.assertIn("tests.test_qikvrt_self_heal_pr_materializer", source)
        self.assertIn("qikvrt-self-heal-materialization.json", source)
        self.assertIn("secrets.QIKVRT_MESH_TOKEN || github.token", source)
        self.assertNotIn('if gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/${branch}"', source)
        self.assertNotIn("gh pr create", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("gh pr review", source)
        self.assertIn("if: always()", source)


if __name__ == "__main__":
    unittest.main()
