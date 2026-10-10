#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Client-side transport-boundary tests for the local dispatch adapter."""
from __future__ import annotations

import contextlib
import ast
import base64
import copy
import io
import hashlib
import json
import os
import sys
import tempfile
import textwrap
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import qikvrt_api_client as client  # noqa: E402


class ApiClientTests(unittest.TestCase):
    def invoke(self, *arguments: str) -> int:
        argv = ["qikvrt_api_client.py", "--owner", "owner", "--repo", "repo", *arguments]
        with mock.patch.object(sys, "argv", argv):
            return client.main()

    def dispatch(self, status, document=None, *, raw=None, arguments=()):
        response = mock.MagicMock()
        response.status = status
        response.read.return_value = raw if raw is not None else json.dumps(document).encode()
        response.__enter__.return_value = response
        opener = mock.Mock()
        opener.open.return_value = response
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "fixture-bearer-not-to-be-persisted"}):
            with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = self.invoke("--request-id", "dispatch-one", *arguments)
        return code, stdout.getvalue(), stderr.getvalue(), opener

    def test_github_204_is_continuation_with_exact_request_receipt_and_one_post(self):
        code, output, error, opener = self.dispatch(
            204, raw=b"", arguments=("--base-url", "https://api.github.com"),
        )
        receipt = json.loads(output)
        request = opener.open.call_args.args[0]
        self.assertEqual(code, 20)
        self.assertEqual(error, "")
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["ordinary_release"])
        self.assertFalse(receipt["execution_verified"])
        self.assertIsNone(receipt["workflow_run_id"])
        self.assertEqual(receipt["repository"], "owner/repo")
        self.assertEqual(receipt["request_id"], "dispatch-one")
        self.assertEqual(receipt["request_sha256"], hashlib.sha256(request.data).hexdigest())
        self.assertEqual(receipt["retry_policy"], "REOBSERVE_BEFORE_ANY_NEW_DISPATCH")
        self.assertNotIn("fixture-bearer", output)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("X-github-api-version"), "2022-11-28")
        self.assertEqual(opener.open.call_count, 1)
        self.assertNotIn("return_run_details", json.loads(request.data))
        self.assertNotIn("state_run_id", json.loads(request.data)["inputs"])

    def test_github_run_receipt_remains_continuation_even_if_response_claims_done(self):
        document = {
            "workflow_run_id": 123,
            "run_url": "https://api.github.com/repos/owner/repo/actions/runs/123",
            "html_url": "https://github.com/owner/repo/actions/runs/123",
            "handler_result": {"effect_state": "EFFECT_ACK_DONE"},
        }
        code, output, error, opener = self.dispatch(
            200, document, arguments=("--base-url", "https://api.github.com", "--return-run-details"),
        )
        receipt = json.loads(output)
        self.assertEqual(code, 20)
        self.assertEqual(error, "")
        self.assertEqual(receipt["workflow_run_id"], 123)
        self.assertEqual(receipt["run_url"], document["run_url"])
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["ordinary_release"])
        self.assertTrue(json.loads(opener.open.call_args.args[0].data)["return_run_details"])
        self.assertEqual(opener.open.call_count, 1)

    def test_github_run_receipt_rejects_foreign_repository_and_invalid_run_ids(self):
        good = {
            "workflow_run_id": 123,
            "run_url": "https://api.github.com/repos/owner/repo/actions/runs/123",
            "html_url": "https://github.com/owner/repo/actions/runs/123",
        }
        invalid = [
            {**good, "run_url": "https://api.github.com/repos/other/repo/actions/runs/123"},
            {**good, "html_url": "https://github.com/owner/repo/actions/runs/124"},
            {**good, "workflow_run_id": True},
            {**good, "workflow_run_id": 0},
            {"handler_result": {"effect_state": "EFFECT_ACK_DONE"}},
        ]
        for document in invalid:
            with self.subTest(document=document):
                code, output, error, opener = self.dispatch(
                    200, document, arguments=("--base-url", "https://api.github.com"),
                )
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertIn("UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK", error)
                self.assertNotIn("fixture-bearer", error)
                self.assertEqual(opener.open.call_count, 1)

    def test_nonempty_204_and_nonobject_json_do_not_grant_an_effect(self):
        for status, raw in ((204, b"unexpected"), (202, b"[]"), (200, b"null"), (201, b"{}")):
            with self.subTest(status=status, raw=raw):
                code, output, error, opener = self.dispatch(status, raw=raw)
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertIn("BLOCK API request failed", error)
                self.assertEqual(opener.open.call_count, 1)

    def test_local_adapter_result_shape_and_exit_codes_remain_compatible(self):
        for effect, expected in (("EFFECT_ACK_DONE", 0), ("EFFECT_ACK_CONTINUE", 20), ("EFFECT_NACK", 1)):
            document = {"status": "fixture", "handler_result": {"effect_state": effect, "artifact_id": "legacy"}}
            with self.subTest(effect=effect):
                code, output, error, opener = self.dispatch(202, document)
                self.assertEqual(code, expected)
                self.assertEqual(json.loads(output), document)
                self.assertEqual(error, "")
                self.assertEqual(opener.open.call_count, 1)

    def test_github_cannot_masquerade_as_a_synchronous_adapter(self):
        code, output, error, opener = self.dispatch(
            202, {"handler_result": {"effect_state": "EFFECT_ACK_DONE"}},
            arguments=("--base-url", "https://api.github.com"),
        )
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("unexpected GitHub dispatch response status 202", error)
        self.assertEqual(opener.open.call_count, 1)

    def test_state_run_id_is_forwarded_to_existing_workflow_input(self):
        code, output, error, opener = self.dispatch(
            204, raw=b"", arguments=("--base-url", "https://api.github.com", "--operation", "verify", "--state-run-id", "123456789"),
        )
        self.assertEqual(code, 20)
        self.assertEqual(error, "")
        body = json.loads(opener.open.call_args.args[0].data)
        self.assertEqual(body["inputs"]["state_run_id"], "123456789")
        self.assertEqual(body["inputs"]["operation"], "verify")
        self.assertFalse(json.loads(output)["execution_verified"])

    def test_unsafe_state_run_id_is_rejected_before_network(self):
        for value in ("", "../123", "123?other=1", "1" * 33):
            with self.subTest(value=value), mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "fixture"}):
                with mock.patch.object(client.urllib.request, "build_opener") as build:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        self.invoke("--request-id", "invalid-state", "--state-run-id", value)
                build.assert_not_called()

    def test_non_loopback_cleartext_endpoint_is_rejected_before_network(self) -> None:
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    self.invoke(
                        "--base-url", "http://example.test:8766",
                        "--operation", "release_status",
                        "--request-id", "cleartext-rejected",
                    )
        self.assertEqual(raised.exception.code, 2)

    def test_transport_failure_returns_blocking_exit_without_traceback(self) -> None:
        opener = mock.Mock()
        opener.open.side_effect = urllib.error.URLError("connection refused")
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with mock.patch.object(
                client.urllib.request,
                "build_opener",
                return_value=opener,
            ):
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    result = self.invoke(
                        "--operation", "release_status",
                        "--request-id", "transport-failure",
                    )
        self.assertEqual(result, 1)
        self.assertIn("BLOCK API request failed", stderr.getvalue())
        self.assertIn("UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK", stderr.getvalue())
        self.assertIn("REOBSERVE_BEFORE_ANY_NEW_DISPATCH", stderr.getvalue())
        self.assertEqual(opener.open.call_count, 1)

    def test_redirects_are_never_followed(self) -> None:
        handler = client.NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(
                mock.Mock(), None, 302, "Found", {}, "https://other.invalid/"
            )
        )

    def test_file_reader_rejects_symlinks_and_oversize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.bin"
            target.write_bytes(b"12345")
            link = root / "link.bin"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(OSError):
                    client.read_regular_file(link, max_bytes=10)
            with self.assertRaisesRegex(OSError, "exceeds"):
                client.read_regular_file(target, max_bytes=4)


class RulesetClientFixture(unittest.TestCase):
    """Real request construction and independent provider-shaped readbacks."""
    sha = "a" * 40
    run_id = 321
    token = "ruleset-fixture-token-never-real"
    prefix = f"https://api.github.com/repos/{client.RULESET_REPOSITORY}/"
    runs_path = f"actions/workflows/{client.RULESET_WORKFLOW}/runs?branch=main&per_page=100"
    writer_path = f"contents/{client.RULESET_WORKFLOW_PATH}?ref={sha}"
    rulesets_path = "rulesets?per_page=100&includes_parents=true"
    writer_version = None

    def setUp(self):
        self.version = self.writer_version or "legacy-v1"
        path = (client.RULESET_WORKFLOW_PATH if self.version == "lifecycle-v2"
                else "tests/fixtures/ruleset_writer_legacy_v1.yml")
        self.writer_bytes = (REPOSITORY_ROOT / path).read_bytes()
        self.writer_blob = hashlib.sha1(
            b"blob " + str(len(self.writer_bytes)).encode() + b"\0" + self.writer_bytes,
        ).hexdigest()
        source = self.writer_bytes.decode("utf-8")
        script = textwrap.dedent(source.split("          python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
        node = next(node for node in ast.parse(script).body
                    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                       and target.id == "desired" for target in node.targets))
        self.desired = ast.literal_eval(node.value)
        self.run = {"id": self.run_id, "repository": {"full_name": client.RULESET_REPOSITORY},
                    "head_repository": {"full_name": client.RULESET_REPOSITORY},
                    "head_sha": self.sha, "head_branch": "main", "run_attempt": 1,
                    "path": client.RULESET_WORKFLOW_PATH, "event": "workflow_dispatch",
                    "workflow_id": 42, "status": "completed", "conclusion": "success"}
        self.job = {"id": 123, "run_id": self.run_id, "head_sha": self.sha,
                    "run_attempt": 1, "name": "reconcile", "status": "completed", "conclusion": "success"}
        self.documents = {
            "branches/main": {"name": "main", "commit": {"sha": self.sha}, "protected": True},
            self.writer_path: {"type": "file", "path": client.RULESET_WORKFLOW_PATH,
                               "sha": self.writer_blob, "size": len(self.writer_bytes),
                               "encoding": "base64",
                               "content": base64.encodebytes(self.writer_bytes).decode("ascii")},
            self.runs_path: {"total_count": 0, "workflow_runs": []},
            f"actions/runs/{self.run_id}": self.run,
            f"actions/runs/{self.run_id}/attempts/1/jobs?per_page=100": {"total_count": 1, "jobs": [self.job]},
            self.rulesets_path: [{"id": 17, "name": self.desired["name"]}],
            "rulesets/17": {**self.desired, "id": 17, "source": client.RULESET_REPOSITORY},
        }

    def response(self, status, *, document=None, raw=None):
        response = mock.MagicMock()
        response.status = status
        response.read.return_value = raw if raw is not None else json.dumps(document).encode()
        response.__enter__.return_value = response
        return response

    def invoke(self, *, operation="ruleset_authority_dispatch", arguments=(),
               overrides=None, post_status=204, post_raw=b"", post_error=None):
        documents = {**self.documents, **(overrides or {})}
        def open_request(request, timeout):
            self.assertTrue(request.full_url.startswith(self.prefix))
            self.assertEqual(request.get_header("Authorization"), "Bearer " + self.token)
            self.assertEqual(timeout, 10)
            path = request.full_url[len(self.prefix):]
            if request.get_method() == "POST":
                self.assertEqual(path, f"actions/workflows/{client.RULESET_WORKFLOW}/dispatches")
                if post_error:
                    raise post_error
                return self.response(post_status, raw=post_raw)
            self.assertEqual(request.get_method(), "GET")
            value = documents[path]
            if callable(value):
                value = value()
            if isinstance(value, Exception):
                raise value
            if isinstance(value, bytes):
                return self.response(200, raw=value)
            return self.response(200, document=value)
        opener = mock.Mock()
        opener.open.side_effect = open_request
        argv = ["qikvrt_api_client.py", "--base-url", "https://api.github.com",
                "--owner", "ingolf-lohmann", "--repo", "qik-vrt", "--request-id", "ruleset-one",
                "--operation", operation, "--expected-main-sha", self.sha]
        if operation == "ruleset_authority_dispatch":
            argv += ["--dry-run", "false", "--accept-effect"]
        else:
            argv += ["--ruleset-run-id", str(self.run_id)]
        if self.writer_version is not None:
            argv += ["--ruleset-writer-version", self.writer_version]
        argv += list(arguments)
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": self.token}), mock.patch.object(sys, "argv", argv):
            with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = client.main()
        self.assertNotIn(self.token, stdout.getvalue() + stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue(), opener

    def posts(self, opener):
        return [call.args[0] for call in opener.open.call_args_list
                if call.args[0].get_method() == "POST"]


class RulesetClientTests(RulesetClientFixture):
    def test_exact_github_post_main_204_is_transport_only(self):
        code, output, error, opener = self.invoke()
        receipt = json.loads(output)
        self.assertEqual(code, 20)
        self.assertEqual(error, "")
        posts = self.posts(opener)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].full_url, self.prefix + f"actions/workflows/{client.RULESET_WORKFLOW}/dispatches")
        self.assertEqual(posts[0].data, b'{"ref":"main"}')
        self.assertEqual(posts[0].get_header("X-github-api-version"), "2022-11-28")
        self.assertEqual(receipt["request_sha256"], hashlib.sha256(posts[0].data).hexdigest())
        self.assertEqual(receipt["http_status"], 204)
        self.assertEqual(receipt["ruleset_writer_version"], self.version)
        self.assertEqual(receipt["workflow_blob_sha"], self.writer_blob)
        self.assertTrue(receipt["writer_bytes_verified"])
        self.assertTrue(receipt["transport_acknowledged"])
        self.assertFalse(receipt["execution_verified"])
        self.assertFalse(receipt["ruleset_effect_verified"])
        self.assertFalse(receipt["ordinary_release"])
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertIsNone(receipt["workflow_run_id"])
        self.assertIn("LOCAL_CORRELATION_ONLY", receipt["request_id_scope"])
        self.assertNotIn("ARTIFACT", " ".join(receipt["next_checks"]))

    def test_unreviewed_main_or_writer_never_posts(self):
        invalid = [{"branches/main": {"name": "main", "commit": {"sha": "b" * 40}}},
                   {self.writer_path: {**self.documents[self.writer_path], "sha": "b" * 40}}]
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                code, output, error, opener = self.invoke(overrides=overrides)
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])
                self.assertEqual(json.loads(error.splitlines()[-1])["dispatch_count"], 0)

    def test_main_drift_between_preflight_and_post_is_blocked(self):
        branches = iter([self.documents["branches/main"], {"name": "main", "commit": {"sha": "b" * 40}}])
        code, _, _, opener = self.invoke(overrides={"branches/main": lambda: next(branches)})
        self.assertEqual(code, 1)
        self.assertEqual(self.posts(opener), [])

    def test_active_or_terminal_exact_head_writer_never_dispatches_again(self):
        for run in ({"head_sha": self.sha, "status": "completed"},
                    {"head_sha": "b" * 40, "status": "in_progress"},
                    {"head_sha": "b" * 40, "status": "action_required"}):
            with self.subTest(run=run):
                code, _, _, opener = self.invoke(overrides={self.runs_path: {"total_count": 1, "workflow_runs": [run]}})
                self.assertEqual(code, 1)
                self.assertEqual(self.posts(opener), [])

    def test_denied_get_or_post_never_retries_or_echoes_provider_credentials(self):
        for status in (401, 403, 404, 429):
            for stage in ("get", "post"):
                with self.subTest(status=status, stage=stage):
                    failure = urllib.error.HTTPError(self.prefix, status, self.token, {}, io.BytesIO(self.token.encode()))
                    kwargs = {"post_error": failure} if stage == "post" else {"overrides": {"branches/main": failure}}
                    code, output, error, opener = self.invoke(**kwargs)
                    self.assertEqual(code, 1)
                    self.assertEqual(output, "")
                    self.assertEqual(len(self.posts(opener)), int(stage == "post"))
                    receipt = json.loads(error.splitlines()[-1])
                    self.assertEqual(receipt["http_status"], status)
                    if status in (401, 403) and stage == "post":
                        self.assertEqual(receipt["dispatch_outcome"], "DENIED")

    def test_ambiguous_response_never_retries_or_claims_effect(self):
        cases = [dict(post_raw=b"unexpected"), dict(post_status=200, post_raw=b'{}'),
                 dict(post_status=202, post_raw=b'{"effect_state":"EFFECT_ACK_DONE"}'),
                 dict(post_error=TimeoutError(self.token)),
                 dict(post_error=urllib.error.URLError(self.token)),
                 dict(post_error=urllib.error.HTTPError(self.prefix, 307, self.token, {"Location": "https://foreign.invalid"}, None))]
        for kwargs in cases:
            with self.subTest(kwargs=list(kwargs)):
                code, output, error, opener = self.invoke(**kwargs)
                receipt = json.loads(error.splitlines()[-1])
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(len(self.posts(opener)), 1)
                self.assertEqual(receipt["dispatch_outcome"], "UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK")
                self.assertFalse(receipt["ruleset_effect_verified"])
                self.assertEqual(receipt["retry_policy"], "REOBSERVE_BEFORE_ANY_NEW_DISPATCH")

    def test_independent_readback_matches_existing_writer_digest_without_post(self):
        code, output, error, opener = self.invoke(operation="ruleset_authority_readback")
        receipt = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(self.posts(opener), [])
        self.assertEqual(receipt["dispatch_count"], 0)
        self.assertFalse(receipt["transport_acknowledged"])
        self.assertTrue(receipt["execution_verified"])
        self.assertTrue(receipt["ruleset_effect_verified"])
        self.assertEqual(receipt["observed_ruleset_sha256"], client.RULESET_POST_SHA256)
        self.assertEqual(receipt["readback_state"], "RULESET_POSTCONDITION_VERIFIED")
        self.assertFalse(receipt["mutation_attribution_verified"])
        self.assertFalse(receipt["native_review_verified"])
        self.assertFalse(receipt["ordinary_release"])
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")

    def test_green_run_without_canonical_ruleset_or_branch_protection_is_not_effect(self):
        changed = copy.deepcopy(self.documents["rulesets/17"])
        changed["rules"][0]["parameters"]["require_code_owner_review"] = False
        for overrides in ({self.rulesets_path: []}, {"rulesets/17": changed},
                          {"branches/main": {**self.documents["branches/main"], "protected": False}}):
            with self.subTest(overrides=list(overrides)):
                code, output, _, opener = self.invoke(operation="ruleset_authority_readback", overrides=overrides)
                self.assertEqual(code, 20)
                self.assertFalse(json.loads(output)["ruleset_effect_verified"])
                self.assertEqual(self.posts(opener), [])

    def test_matching_ruleset_without_successful_native_jobs_is_not_effect(self):
        job_path = f"actions/runs/{self.run_id}/attempts/1/jobs?per_page=100"
        for overrides in ({f"actions/runs/{self.run_id}": {**self.run, "conclusion": "failure"}},
                          {f"actions/runs/{self.run_id}": {**self.run, "status": "action_required"}},
                          {job_path: {"total_count": 0, "jobs": []}},
                          {job_path: {"total_count": 1, "jobs": [{**self.job, "conclusion": "skipped"}]}}):
            with self.subTest(overrides=list(overrides)):
                code, output, _, opener = self.invoke(operation="ruleset_authority_readback", overrides=overrides)
                self.assertEqual(code, 20)
                self.assertFalse(json.loads(output)["execution_verified"])
                self.assertFalse(json.loads(output)["ruleset_effect_verified"])
                self.assertEqual(self.posts(opener), [])

    def test_foreign_stale_or_wrong_event_run_is_rejected(self):
        for change in ({"head_sha": "b" * 40}, {"head_branch": "other"}, {"id": 322},
                       {"path": ".github/workflows/other.yml"}, {"event": "push"},
                       {"repository": {"full_name": "foreign/repo"}},
                       {"head_repository": {"full_name": "foreign/repo"}}):
            with self.subTest(change=change):
                code, output, _, opener = self.invoke(operation="ruleset_authority_readback",
                    overrides={f"actions/runs/{self.run_id}": {**self.run, **change}})
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])

    def test_run_attempt_drift_and_wrong_job_binding_are_rejected(self):
        run_path = f"actions/runs/{self.run_id}"
        runs = iter([self.run, {**self.run, "conclusion": "failure"}])
        cases = [{run_path: lambda: next(runs)}]
        for change in ({"head_sha": "b" * 40}, {"run_id": 322}, {"run_attempt": 2}):
            cases.append({f"{run_path}/attempts/1/jobs?per_page=100": {"total_count": 1, "jobs": [{**self.job, **change}]}})
        for overrides in cases:
            with self.subTest(overrides=list(overrides)):
                code, output, _, opener = self.invoke(operation="ruleset_authority_readback", overrides=overrides)
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])

    def test_foreign_duplicate_or_unreadable_ruleset_does_not_grant_effect(self):
        for overrides in ({"rulesets/17": {**self.documents["rulesets/17"], "source": "foreign/repo"}},
                          {self.rulesets_path: self.documents[self.rulesets_path] * 2},
                          {self.rulesets_path: {"effect_state": "EFFECT_ACK_DONE"}},
                          {"rulesets/17": urllib.error.HTTPError(self.prefix, 403, self.token, {}, None)}):
            with self.subTest(overrides=list(overrides)):
                code, output, _, opener = self.invoke(operation="ruleset_authority_readback", overrides=overrides)
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])

    def test_incomplete_inventory_fails_closed_before_post(self):
        code, _, _, opener = self.invoke(overrides={self.runs_path: {"total_count": 101, "workflow_runs": []}})
        self.assertEqual(code, 1)
        self.assertEqual(self.posts(opener), [])

    def test_invalid_readback_json_is_bounded_and_never_posts(self):
        for raw in (b'{"name":"main","name":"main"}', b'{"x":NaN}', b'\xff',
                    b'x' * (client.MAX_RESPONSE_BYTES + 1)):
            with self.subTest(size=len(raw)):
                code, output, _, opener = self.invoke(overrides={"branches/main": raw})
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])

    def test_arbitrary_workflow_ref_host_repository_and_inputs_rejected_before_network(self):
        invalid = [("--workflow", "other.yml"), ("--ref", "other"), ("--owner", "foreign"),
                   ("--base-url", "http://127.0.0.1:8766"), ("--base-url", "https://foreign.invalid"),
                   ("--base-url", "https://api.github.com:444"), ("--payload-file", "not-read"),
                   ("--return-run-details",), ("--state-run-id", "123"),
                   ("--expected-main-sha", "../main"), ("--dry-run", "true")]
        for arguments in invalid:
            with self.subTest(arguments=arguments), mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": self.token}):
                argv = ["client", "--base-url", "https://api.github.com", "--owner", "ingolf-lohmann",
                        "--repo", "qik-vrt", "--request-id", "ruleset-one", "--operation", "ruleset_authority_dispatch",
                        "--expected-main-sha", self.sha, "--dry-run", "false", "--accept-effect", *arguments]
                with mock.patch.object(sys, "argv", argv), mock.patch.object(client.urllib.request, "build_opener") as build:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        client.main()
                    self.assertEqual(error.exception.code, 2)
                    build.assert_not_called()

    def test_explicit_effect_acceptance_is_required_and_readback_cannot_mutate(self):
        for operation, extra in (("ruleset_authority_dispatch", []),
                                 ("ruleset_authority_dispatch", ["--dry-run", "false"]),
                                 ("ruleset_authority_readback", ["--ruleset-run-id", "321", "--dry-run", "false", "--accept-effect"])):
            argv = ["client", "--base-url", "https://api.github.com", "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                    "--request-id", "ruleset-one", "--operation", operation, "--expected-main-sha", self.sha, *extra]
            with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": self.token}), mock.patch.object(sys, "argv", argv):
                with mock.patch.object(client.urllib.request, "build_opener") as build:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        client.main()
                    build.assert_not_called()


class LifecycleRulesetClientTests(RulesetClientTests):
    """Run every original Ruleset regression on the actual integrated writer."""
    writer_version = "lifecycle-v2"


class RulesetWriterVersionTests(RulesetClientFixture):
    """Version transitions are explicit and fail closed, including real bytes."""

    def test_both_source_pins_and_unchanged_protection_projection(self):
        blobs = {"legacy-v1": "1202d24c2f23eb8fa52ab7c562a583e79f9e8444",
                 "lifecycle-v2": "ab47a8ec98c39b39bda420050cb7c970a9da6165"}
        projections = []
        for version, blob in blobs.items():
            path = (client.RULESET_WORKFLOW_PATH if version == "lifecycle-v2"
                    else "tests/fixtures/ruleset_writer_legacy_v1.yml")
            data = (REPOSITORY_ROOT / path).read_bytes()
            self.assertEqual(hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(), blob)
            source = data.decode()
            script = textwrap.dedent(source.split("          python3 - <<'PY'\n", 1)[1].rsplit("          PY", 1)[0])
            desired = next(ast.literal_eval(node.value) for node in ast.parse(script).body
                           if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
                              and t.id == "desired" for t in node.targets))
            projected = {key: desired[key] for key in (
                "name", "target", "enforcement", "conditions", "bypass_actors", "rules")}
            projected["rules"] = sorted(projected["rules"], key=lambda r: r["type"])
            for rule in projected["rules"]:
                if rule["type"] == "required_status_checks":
                    rule["parameters"]["required_status_checks"].sort(key=lambda x: x["context"])
            canonical = (json.dumps(projected, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
            self.assertEqual(hashlib.sha256(canonical).hexdigest(), "45da27f3608b38f04b8252d7fc709a6337bff49d40fa2cf9baa4425dd36ec0dd")
            self.assertEqual(client.RULESET_WRITER_VERSIONS[version], (blob, hashlib.sha256(canonical).hexdigest()))
            projections.append(projected)
        self.assertEqual(projections[0], projections[1])
        desired = projections[0]
        self.assertEqual(desired["enforcement"], "active")
        self.assertEqual(desired["bypass_actors"], [])
        rules = {r["type"]: r for r in desired["rules"]}
        self.assertIn("non_fast_forward", rules)
        review = rules["pull_request"]["parameters"]
        self.assertTrue(review["require_code_owner_review"])
        self.assertTrue(review["require_last_push_approval"])
        self.assertEqual(review["required_approving_review_count"], 1)
        self.assertEqual({c["context"] for c in rules["required_status_checks"]["parameters"]["required_status_checks"]},
                         {"test", "QIKVRT required code-owner review"})

    def test_known_other_version_never_becomes_an_automatic_fallback(self):
        other = (REPOSITORY_ROOT / client.RULESET_WORKFLOW_PATH).read_bytes()
        document = {**self.documents[self.writer_path],
                    "sha": "ab47a8ec98c39b39bda420050cb7c970a9da6165",
                    "size": len(other), "content": base64.b64encode(other).decode()}
        for operation in ("ruleset_authority_dispatch", "ruleset_authority_readback"):
            with self.subTest(operation=operation):
                code, output, error, opener = self.invoke(operation=operation, overrides={self.writer_path: document})
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])
                self.assertFalse(json.loads(error.splitlines()[-1])["writer_bytes_verified"])
        code, _, _, opener = self.invoke(arguments=("--ruleset-writer-version", "lifecycle-v2"))
        self.assertEqual(code, 1)
        self.assertEqual(self.posts(opener), [])

    def test_forged_metadata_or_altered_bytes_never_pass_the_pin(self):
        good = self.documents[self.writer_path]
        altered = self.writer_bytes + b"\n# changed writer\n"
        invalid = [{**good, "content": base64.b64encode(altered).decode(), "size": len(altered)},
                   {**good, "content": "not+base64!"}, {**good, "encoding": "utf-8"},
                   {**good, "size": good["size"] + 1}, {**good, "size": True},
                   {**good, "size": client.MAX_RULESET_WRITER_BYTES + 1},
                   {**good, "content": "A" * (client.MAX_RULESET_WRITER_BYTES * 2 + 1)},
                   {k: v for k, v in good.items() if k != "content"},
                   {**good, "path": ".github/workflows/unapproved.yml"}]
        for document in invalid:
            with self.subTest(keys=list(document)):
                code, output, error, opener = self.invoke(overrides={self.writer_path: document})
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])
                receipt = json.loads(error.splitlines()[-1])
                self.assertEqual(receipt["dispatch_count"], 0)
                self.assertFalse(receipt["writer_bytes_verified"])

    def test_unknown_version_and_version_flag_on_mesh_are_rejected_before_network(self):
        for extra in (("--ruleset-writer-version", "unapproved-v3"),
                      ("--operation", "ingest", "--ruleset-writer-version", "legacy-v1")):
            argv = ["client", "--base-url", "https://api.github.com", "--owner", "ingolf-lohmann",
                    "--repo", "qik-vrt", "--request-id", "version-rejected",
                    "--operation", "ruleset_authority_dispatch", "--expected-main-sha", self.sha,
                    "--dry-run", "false", "--accept-effect", *extra]
            with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": self.token}), mock.patch.object(sys, "argv", argv):
                with mock.patch.object(client.urllib.request, "build_opener") as build:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        client.main()
                    self.assertEqual(error.exception.code, 2)
                    build.assert_not_called()

    def test_concurrent_integration_before_post_and_during_readback_never_grants_effect(self):
        for operation in ("ruleset_authority_dispatch", "ruleset_authority_readback"):
            branches = iter([self.documents["branches/main"],
                             {"name": "main", "commit": {"sha": "b" * 40}, "protected": True}])
            with self.subTest(operation=operation):
                code, output, _, opener = self.invoke(operation=operation,
                    overrides={"branches/main": lambda: next(branches)})
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertEqual(self.posts(opener), [])

    def test_post_204_cannot_lease_main_and_raced_run_is_rejected_by_fresh_readback(self):
        code, output, _, opener = self.invoke()
        self.assertEqual(code, 20)
        self.assertTrue(json.loads(output)["transport_acknowledged"])
        self.assertFalse(json.loads(output)["ruleset_effect_verified"])
        self.assertEqual(len(self.posts(opener)), 1)
        # Ref-only POST cannot prevent integration after the last preflight GET.
        # Even a green run on that successor cannot satisfy the original head.
        code, output, _, opener = self.invoke(operation="ruleset_authority_readback",
            overrides={f"actions/runs/{self.run_id}": {**self.run, "head_sha": "b" * 40}})
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertEqual(self.posts(opener), [])

    def test_version_mapping_cannot_be_expanded_in_place(self):
        with self.assertRaises(TypeError):
            client.RULESET_WRITER_VERSIONS["unapproved-v3"] = ("b" * 40, "c" * 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
