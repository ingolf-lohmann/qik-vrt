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
import subprocess
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
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_dir = directory.name
        patch = mock.patch.dict(os.environ, {"QIKVRT_API_CLIENT_STATE_DIR": directory.name})
        patch.start()
        self.addCleanup(patch.stop)

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
        def respond(request, **_):
            if request.get_method() == "POST":
                return response
            closing = mock.MagicMock()
            closing.status = 200
            closing.geturl.return_value = request.full_url
            closing.read.return_value = (json.dumps({"sha": "a" * 40,
                "commit": {"tree": {"sha": "b" * 40}}}).encode()
                if request.full_url.startswith("https://api.github.com/") else b"delivery fixture")
            closing.__enter__.return_value = closing
            return closing
        opener.open.side_effect = respond
        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {
                "QIKVRT_API_TOKEN": "fixture-bearer-not-to-be-persisted",
                "QIKVRT_API_CLIENT_STATE_DIR": directory}):
            with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = self.invoke("--request-id", "dispatch-one", *arguments)
        return code, stdout.getvalue(), stderr.getvalue(), opener

    def post_calls(self, opener):
        return [call for call in opener.open.call_args_list
                if call.args[0].get_method() == "POST"]

    def test_github_204_is_continuation_with_exact_request_receipt_and_one_post(self):
        code, output, error, opener = self.dispatch(
            204, raw=b"", arguments=("--base-url", "https://api.github.com"),
        )
        receipt = json.loads(output)["dispatch"]
        request = self.post_calls(opener)[0].args[0]
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
        self.assertEqual(len(self.post_calls(opener)), 1)
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
        receipt = json.loads(output)["dispatch"]
        self.assertEqual(code, 20)
        self.assertEqual(error, "")
        self.assertEqual(receipt["workflow_run_id"], 123)
        self.assertEqual(receipt["run_url"], document["run_url"])
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["ordinary_release"])
        self.assertTrue(json.loads(self.post_calls(opener)[0].args[0].data)["return_run_details"])
        self.assertEqual(len(self.post_calls(opener)), 1)

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
                self.assertTrue(json.loads(output)["closing_verification"]["valid"])
                self.assertEqual(json.loads(output)["dispatch"]["dispatch_outcome"], "UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK")
                self.assertNotIn("fixture-bearer", error)
                self.assertEqual(len(self.post_calls(opener)), 1)

    def test_nonempty_204_and_nonobject_json_do_not_grant_an_effect(self):
        for status, raw in ((204, b"unexpected"), (202, b"[]"), (200, b"null"), (201, b"{}")):
            with self.subTest(status=status, raw=raw):
                code, output, error, opener = self.dispatch(status, raw=raw)
                self.assertEqual(code, 1)
                self.assertTrue(json.loads(output)["closing_verification"]["valid"])
                self.assertIn("BLOCK API request failed", error)
                self.assertEqual(len(self.post_calls(opener)), 1)

    def test_local_adapter_result_shape_and_exit_codes_remain_compatible(self):
        for effect, expected in (("EFFECT_ACK_DONE", 20), ("EFFECT_ACK_CONTINUE", 20), ("EFFECT_NACK", 1)):
            document = {"status": "fixture", "handler_result": {"effect_state": effect, "artifact_id": "legacy"}}
            with self.subTest(effect=effect):
                code, output, error, opener = self.dispatch(202, document)
                self.assertEqual(code, expected)
                self.assertEqual(json.loads(output)["dispatch"]["handler_result"], document["handler_result"])
                self.assertEqual(error, "")
                self.assertEqual(len(self.post_calls(opener)), 1)

    def test_github_cannot_masquerade_as_a_synchronous_adapter(self):
        code, output, error, opener = self.dispatch(
            202, {"handler_result": {"effect_state": "EFFECT_ACK_DONE"}},
            arguments=("--base-url", "https://api.github.com"),
        )
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(output)["closing_verification"]["valid"])
        self.assertIn("BLOCK API request failed: ValueError", error)
        self.assertEqual(len(self.post_calls(opener)), 1)

    def test_state_run_id_is_forwarded_to_existing_workflow_input(self):
        code, output, error, opener = self.dispatch(
            204, raw=b"", arguments=("--base-url", "https://api.github.com", "--operation", "verify", "--state-run-id", "123456789"),
        )
        self.assertEqual(code, 20)
        self.assertEqual(error, "")
        body = json.loads(self.post_calls(opener)[0].args[0].data)
        self.assertEqual(body["inputs"]["state_run_id"], "123456789")
        self.assertEqual(body["inputs"]["operation"], "verify")
        self.assertFalse(json.loads(output)["dispatch"]["execution_verified"])

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
                with contextlib.redirect_stderr(io.StringIO()) as stderr, contextlib.redirect_stdout(io.StringIO()) as stdout:
                    result = self.invoke(
                        "--operation", "release_status",
                        "--request-id", "transport-failure",
                    )
        self.assertEqual(result, 1)
        self.assertIn("BLOCK API request failed", stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["dispatch"]["dispatch_outcome"], "UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK")
        self.assertEqual(json.loads(stdout.getvalue())["dispatch"]["retry_policy"], "REOBSERVE_BEFORE_ANY_NEW_DISPATCH")
        self.assertEqual(len(self.post_calls(opener)), 1)

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


class FirefoxAmoClientTests(unittest.TestCase):
    """Provider-shaped transport fixtures; no live signing or secret-store proof."""

    def setUp(self):
        state = tempfile.TemporaryDirectory()
        self.addCleanup(state.cleanup)
        self.state_dir = state.name
        self.head, self.tree = "a" * 40, "b" * 40
        self.token = "amo-client-fixture-token-never-real"
        self.prefix = "https://api.github.com/repos/ingolf-lohmann/qik-vrt/"
        self.workflow = b"on:\n  workflow_dispatch:\n"
        self.blob = hashlib.sha1(b"blob " + str(len(self.workflow)).encode() + b"\0" + self.workflow).hexdigest()
        self.subject = {"source_head": self.head, "source_tree": self.tree,
                        "unsigned_xpi_sha256": "d" * 64,
                        "extension_id": "qikvrt-ai-terminal@goldkelch.local", "extension_version": "1.0.0"}

    def invoke(self, operation="firefox_amo_dispatch", *, arguments=(), overrides=None,
               status=200, post_error=None, request_id="amo-one"):
        repo = {"full_name": "ingolf-lohmann/qik-vrt"}
        pr = {"state": "open", "head": {"sha": self.head, "ref": "integration/test", "repo": repo},
              "base": {"ref": "main", "repo": repo}}
        metadata = {"created_at": "2026-10-17T00:00:00Z", "updated_at": "2026-10-17T01:00:00Z"}
        documents = {"pulls/523": pr, "git/commits/" + self.head: {"sha": self.head, "tree": {"sha": self.tree}},
            "contents/" + client.AMO_WORKFLOW_PATH + "?ref=" + self.head: {
                "type": "file", "path": client.AMO_WORKFLOW_PATH, "sha": self.blob,
                "encoding": "base64", "size": len(self.workflow),
                "content": base64.b64encode(self.workflow).decode()},
            "commits/integration%2Ftest": {"sha": self.head, "commit": {"tree": {"sha": self.tree}}},
            **{"actions/secrets/" + name: {"name": name, **metadata} for name in client.AMO_SECRET_NAMES},
            **(overrides or {})}
        def respond(request, **_):
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.geturl.return_value = request.full_url
            if request.get_method() == "POST":
                self.assertEqual(request.full_url, self.prefix + "actions/workflows/qikvrt_ci.yml/dispatches")
                # Observe the on-disk original intent before the transport can
                # return or time out; a later response is not crash safety.
                journals = list(Path(self.state_dir).glob("*.json"))
                self.assertEqual(len(journals), 1)
                intent = json.loads(journals[0].read_bytes())
                self.assertEqual(intent["status"], "in_flight")
                self.assertEqual(intent["operation_binding"]["request_body"], json.loads(request.data))
                self.assertEqual(intent["operation_binding"]["source_head"], self.head)
                self.assertEqual(intent["operation_binding"]["source_tree"], self.tree)
                self.assertEqual(intent["operation_binding"]["request_sha256"], hashlib.sha256(request.data).hexdigest())
                if post_error:
                    raise post_error
                response.status = status
                response.read.return_value = (b"" if status == 204 else json.dumps({"workflow_run_id": 123,
                    "run_url": self.prefix + "actions/runs/123",
                    "html_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/123"}).encode())
            elif request.full_url.startswith(self.prefix):
                self.assertEqual(request.get_header("Authorization"), "Bearer " + self.token)
                value = documents[request.full_url[len(self.prefix):]]
                if callable(value):
                    value = value()
                if isinstance(value, Exception):
                    raise value
                response.status = 200
                response.read.return_value = json.dumps(value).encode()
            else:
                self.assertEqual(request.full_url, "https://raumzeitterminal.de/")
                self.assertIsNone(request.get_header("Authorization"))
                response.status = 200
                response.read.return_value = b"public closing fixture"
            return response
        opener = mock.Mock()
        opener.open.side_effect = respond
        argv = ["qikvrt_api_client.py", "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                "--base-url", "https://api.github.com", "--ref", "integration/test",
                "--state-dir", self.state_dir, "--request-id", request_id, "--operation", operation]
        if operation == "firefox_amo_dispatch":
            argv += ["--dry-run", "false", "--accept-effect", "--amo-expected-head", self.head,
                     "--amo-expected-tree", self.tree, "--amo-workflow-blob", self.blob]
        argv += list(arguments)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": self.token}), mock.patch.object(sys, "argv", argv), \
                mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch("tools.qikvrt_self_host.firefox_amo_input", return_value=(b"xpi", self.subject)), \
                mock.patch("tools.qikvrt_workflow_executor.amo_request", return_value={"unsigned_xpi_sha256": "d" * 64}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = client.main()
        self.assertNotIn(self.token, out.getvalue() + err.getvalue())
        for path in Path(self.state_dir).glob("*"):
            if path.is_file():
                self.assertNotIn(self.token.encode(), path.read_bytes())
        return code, json.loads(out.getvalue()), err.getvalue(), opener

    def posts(self, opener):
        return [call.args[0] for call in opener.open.call_args_list if call.args[0].get_method() == "POST"]

    def test_exact_owner_dispatch_reuses_real_workflow_and_is_transport_only(self):
        code, output, error, opener = self.invoke()
        request, = self.posts(opener)
        body = json.loads(request.data)
        self.assertEqual(code, 20)
        self.assertEqual(error, "")
        self.assertEqual(body["ref"], "integration/test")
        self.assertEqual(body["inputs"], {"amo_sign_unlisted": True, "amo_expected_head": self.head,
            "amo_expected_tree": self.tree, "amo_previous_run_id": "0", "amo_executor_run_id": "0",
            "amo_readback_only": False})
        self.assertEqual(output["dispatch"]["workflow_run_id"], 123)
        for key in ("execution_verified", "signing_verified", "native_independent_review", "main_merge_verified"):
            self.assertFalse(output["dispatch"][key])
        self.assertFalse(output["effect_ack_done"])
        self.assertTrue(output["closing_verification"]["valid"])

    def test_legacy_204_remains_pending_without_invented_run(self):
        code, output, _, opener = self.invoke(status=204)
        self.assertEqual(code, 20)
        self.assertEqual(len(self.posts(opener)), 1)
        self.assertIsNone(output["dispatch"]["workflow_run_id"])
        self.assertFalse(output["effect_ack_done"])

    def test_metadata_only_is_not_job_delivery_or_authentication(self):
        code, output, _, opener = self.invoke("firefox_amo_access")
        self.assertEqual(code, 0)
        self.assertEqual(self.posts(opener), [])
        r = output["dispatch"]
        self.assertEqual([s["name"] for s in r["secrets"]], list(client.AMO_SECRET_NAMES))
        self.assertEqual(r["configuration_status"], "REPOSITORY_METADATA_OBSERVED")
        self.assertEqual(r["job_credential_delivery"], "NOT_OBSERVED")
        self.assertFalse(r["amo_authentication_verified"])
        self.assertFalse(r["credential_values_read"])

    def test_metadata_denial_is_not_secret_absence_and_never_leaks_provider_errors(self):
        for status in (401, 403, 404):
            with self.subTest(status=status):
                error = urllib.error.HTTPError(self.prefix, status, self.token, {}, None)
                code, output, _, opener = self.invoke("firefox_amo_access",
                    overrides={"actions/secrets/AMO_JWT_ISSUER": error})
                self.assertEqual(code, 1)
                self.assertEqual(output["dispatch"]["configuration_status"], "NOT_INSPECTED")
                self.assertEqual(self.posts(opener), [])

    def test_wrong_metadata_identity_is_refused(self):
        code, output, _, opener = self.invoke("firefox_amo_access", overrides={
            "actions/secrets/AMO_JWT_ISSUER": {"name": "OTHER", "created_at": "bad", "updated_at": "bad"}})
        self.assertEqual(code, 1)
        self.assertEqual(self.posts(opener), [])
        self.assertEqual(output["dispatch"]["configuration_status"], "NOT_INSPECTED")

    def test_foreign_closed_or_changed_head_pr_never_posts(self):
        for pr in ({"state": "closed"}, {"state": "open", "head": {"sha": "e" * 40}},
                   {"state": "open", "head": {"sha": self.head, "ref": "integration/test",
                       "repo": {"full_name": "foreign/qik-vrt"}}}):
            with self.subTest(pr=pr):
                code, _, _, opener = self.invoke(overrides={"pulls/523": pr})
                self.assertEqual(code, 1)
                self.assertEqual(self.posts(opener), [])

    def test_wrong_tree_and_forged_workflow_bytes_never_post(self):
        for override in ({"git/commits/" + self.head: {"sha": self.head, "tree": {"sha": "e" * 40}}},
            {"contents/" + client.AMO_WORKFLOW_PATH + "?ref=" + self.head: {
                "type": "file", "path": client.AMO_WORKFLOW_PATH, "sha": self.blob,
                "encoding": "base64", "size": len(self.workflow),
                "content": base64.b64encode(b"x" * len(self.workflow)).decode()}}):
            with self.subTest(override=override):
                code, _, _, opener = self.invoke(overrides=override)
                self.assertEqual(code, 1)
                self.assertEqual(self.posts(opener), [])

    def test_head_drift_during_journal_admission_never_posts(self):
        repo = {"full_name": "ingolf-lohmann/qik-vrt"}
        observations = iter([{"state": "open", "head": {"sha": self.head, "ref": "integration/test", "repo": repo},
            "base": {"ref": "main", "repo": repo}}, {"state": "closed"}])
        code, _, _, opener = self.invoke(overrides={"pulls/523": lambda: next(observations)})
        self.assertEqual(code, 1)
        self.assertEqual(self.posts(opener), [])

    def test_ambiguous_post_survives_restart_and_changed_request_or_head_without_replay(self):
        code, _, _, opener = self.invoke(post_error=TimeoutError(self.token))
        self.assertEqual(code, 1)
        self.assertEqual(len(self.posts(opener)), 1)
        self.head, self.tree = "e" * 40, "f" * 40
        code, output, _, opener = self.invoke(request_id="different-request")
        self.assertEqual(code, 1)
        self.assertEqual(self.posts(opener), [])
        self.assertEqual(output["dispatch"]["reason"], "UNCHANGED_FAILURE_OR_UNRESOLVED_DISPATCH")

    def test_acknowledged_async_run_is_not_replayed_after_restart(self):
        self.invoke()
        code, output, _, opener = self.invoke(request_id="changed")
        self.assertEqual(code, 1)
        self.assertEqual(self.posts(opener), [])
        self.assertEqual(output["dispatch"]["previous_transport_receipt"]["workflow_run_id"], 123)

    def test_invalid_scope_acceptance_and_binding_arguments_fail_before_network(self):
        for arguments in (("--base-url", "https://other.invalid"), ("--owner", "foreign"),
                          ("--dry-run", "true"), ("--amo-expected-tree", "wrong"),
                          ("--amo-previous-run-id", "-1"), ("--payload-file", "unrelated")):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                self.invoke(arguments=arguments)

    def test_metadata_mode_cannot_carry_effect_acceptance(self):
        with self.assertRaises(SystemExit):
            self.invoke("firefox_amo_access", arguments=("--dry-run", "false", "--accept-effect"))


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
        path = {"legacy-v1": "tests/fixtures/ruleset_writer_legacy_v1.yml",
                "lifecycle-v2": "tests/fixtures/ruleset_writer_lifecycle_v2.yml",
                "app-renewal-v3": "tests/fixtures/ruleset_writer_app_renewal_v3.yml",
                "principal-review-v4": client.RULESET_WORKFLOW_PATH}[self.version]
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
               overrides=None, post_status=204, post_raw=b"", post_error=None,
               before_post=None):
        documents = {**self.documents, **(overrides or {})}
        def open_request(request, timeout):
            if request.full_url == "https://raumzeitterminal.de/":
                response = self.response(200, raw=b"public observation fixture")
                response.geturl.return_value = request.full_url
                return response
            self.assertTrue(request.full_url.startswith(self.prefix))
            self.assertEqual(request.get_header("Authorization"), "Bearer " + self.token)
            self.assertEqual(timeout, 10)
            path = request.full_url[len(self.prefix):]
            if request.get_method() == "POST":
                self.assertEqual(path, f"actions/workflows/{client.RULESET_WORKFLOW}/dispatches")
                if before_post:
                    before_post(request)
                if post_error:
                    raise post_error
                return self.response(post_status, raw=post_raw)
            self.assertEqual(request.get_method(), "GET")
            if path == "commits/main":
                response = self.response(200, document={"sha": self.sha,
                    "commit": {"tree": {"sha": "b" * 40}}})
                response.geturl.return_value = request.full_url
                return response
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
        with tempfile.TemporaryDirectory() as state, mock.patch.dict(os.environ, {
                "QIKVRT_API_TOKEN": self.token, "QIKVRT_API_CLIENT_STATE_DIR": state}), mock.patch.object(sys, "argv", argv):
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
        self.assertEqual(receipt["observed_ruleset_sha256"], client.RULESET_WRITER_VERSIONS[self.version][1])
        self.assertEqual(receipt["readback_state"], "RULESET_POSTCONDITION_VERIFIED")
        self.assertFalse(receipt["mutation_attribution_verified"])
        self.assertFalse(receipt["native_review_verified"])
        self.assertFalse(receipt["ordinary_release"])
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")

    def test_green_run_without_canonical_ruleset_or_branch_protection_is_not_effect(self):
        changed = copy.deepcopy(self.documents["rulesets/17"])
        changed["rules"][0]["parameters"]["require_code_owner_review"] = not changed["rules"][0]["parameters"]["require_code_owner_review"]
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
    """Preserve every original regression against the frozen lifecycle writer."""
    writer_version = "lifecycle-v2"


class AppRenewalRulesetClientTests(RulesetClientTests):
    """Verify the new writer's transport, admission and exact-effect boundaries."""
    writer_version = "app-renewal-v3"


class PrincipalReviewRulesetClientTests(RulesetClientTests):
    """Verify exact source, transport and effect boundaries of the Owner rule."""
    writer_version = "principal-review-v4"


class RulesetWriterVersionTests(RulesetClientFixture):
    """Version transitions are explicit and fail closed, including real bytes."""

    def test_versioned_source_pins_and_explicit_principal_review_projection(self):
        blobs = {"legacy-v1": "1202d24c2f23eb8fa52ab7c562a583e79f9e8444",
                 "lifecycle-v2": "ab47a8ec98c39b39bda420050cb7c970a9da6165",
                 "app-renewal-v3": "05066f6fb83a7f3ba8799677db35647e06942fd2",
                 "principal-review-v4": "3b9396f4b6415baff047526bd6ecb193f606863e"}
        projections = []
        for version, blob in blobs.items():
            path = {"legacy-v1": "tests/fixtures/ruleset_writer_legacy_v1.yml",
                    "lifecycle-v2": "tests/fixtures/ruleset_writer_lifecycle_v2.yml",
                    "app-renewal-v3": "tests/fixtures/ruleset_writer_app_renewal_v3.yml",
                    "principal-review-v4": client.RULESET_WORKFLOW_PATH}[version]
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
            expected_post = "59b80123aee14fd0f82a0af8a7e3265a2a5782f786785cf09be35f251b9c6999" if version == "principal-review-v4" else "45da27f3608b38f04b8252d7fc709a6337bff49d40fa2cf9baa4425dd36ec0dd"
            self.assertEqual(hashlib.sha256(canonical).hexdigest(), expected_post)
            self.assertEqual(client.RULESET_WRITER_VERSIONS[version], (blob, hashlib.sha256(canonical).hexdigest()))
            contract = (REPOSITORY_ROOT / 'api/qikvrt_github_api.openapi.yaml').read_text()
            self.assertIn(f'        {version}:\n          workflow_blob_sha: {blob}', contract)
            projections.append(projected)
        self.assertEqual(projections[0], projections[1])
        self.assertEqual(projections[0], projections[2])
        principal = copy.deepcopy(projections[3])
        pull = next(r for r in principal["rules"] if r["type"] == "pull_request")["parameters"]
        for field in ("require_code_owner_review", "require_last_push_approval", "require_extra_approval_for_unattributed_changes"):
            self.assertFalse(pull[field])
            pull[field] = True
        self.assertEqual(pull["required_approving_review_count"], 0)
        pull["required_approving_review_count"] = 1
        self.assertEqual(principal, projections[0])
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
                    "sha": "05066f6fb83a7f3ba8799677db35647e06942fd2",
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

class ApiClientEndOfActionConformanceTests(unittest.TestCase):
    """Direct CLI obligations executed as ordinary assertions after repair.

    These execute the actual client with a recorded, deterministic transport.
    They do not execute a vendor AI session or prove public product delivery.
    The Owner contract and shared receipt validator remain the sole authority.
    """

    setUp = ApiClientTests.setUp

    class Response:
        def __init__(self, raw: bytes, url: str) -> None:
            self.raw, self.url = raw, url
            self.status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self, limit: int) -> bytes:
            return self.raw[:limit]

        def geturl(self) -> str:
            return self.url

    def transport(self, *, failure: bool = False):
        requests = []

        def open_request(request, **_):
            requests.append(request)
            url = request.full_url
            if request.get_method() == "POST":
                if failure:
                    raise urllib.error.HTTPError(
                        url, 403, "Forbidden", {},
                        io.BytesIO(b'{"error":"unchanged admission denied"}'),
                    )
                raw = b'{"handler_result":{"effect_state":"EFFECT_ACK_DONE"}}'
            elif url.startswith("https://api.github.com/"):
                raw = json.dumps({
                    "sha": "a" * 40, "commit": {"tree": {"sha": "b" * 40}},
                }).encode("utf-8")
            else:
                raw = b"fixture: public response, not productive delivery proof"
            return self.Response(raw, url)

        opener = mock.Mock()
        opener.open.side_effect = open_request
        return opener, requests

    def invoke_actual_client(self, *arguments: str) -> int:
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return ApiClientTests.invoke(
                    self, "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                    "--operation", "verify", "--request-id", "same-causal-subject",
                    "--dry-run", "false", "--accept-effect",
                    *arguments,
                )

    def assert_closing_reads(self, requests, *, repository: bool = True) -> None:
        from tools.ai_handoff import client_end_of_action_domain
        post = next(i for i, request in enumerate(requests)
                    if request.get_method() == "POST")
        closing = requests[post + 1:]
        repository_reads = [request for request in closing
                            if request.get_method() == "GET"
                            and request.full_url ==
                            "https://api.github.com/repos/ingolf-lohmann/qik-vrt/commits/main"]
        if repository:
            self.assertTrue(repository_reads, "no fresh repository HEAD/TREE read after action")
        public_url = "https://" + client_end_of_action_domain() + "/"
        self.assertTrue(
            any(request.get_method() == "GET" and request.full_url == public_url
                for request in closing),
            "no fresh exact-host public delivery read after action",
        )
        for request in closing:
            if request.full_url == public_url:
                self.assertIsNone(request.get_header("Authorization"))

    def test_scoped_handler_done_does_not_replace_fresh_client_closure(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        self.assert_closing_reads(requests)

    def test_run_receipt_remains_pending_and_survives_a_client_continuation(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect
        document = {
            "workflow_run_id": 123,
            "run_url": "https://api.github.com/repos/ingolf-lohmann/qik-vrt/actions/runs/123",
            "html_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/123",
            "handler_result": {"effect_state": "EFFECT_ACK_DONE"},
        }
        def read(request, **kwargs):
            if request.get_method() == "POST":
                requests.append(request)
                return self.Response(json.dumps(document).encode(), request.full_url)
            return original(request, **kwargs)
        opener.open.side_effect = read
        arguments = ("--base-url", "https://api.github.com", "--return-run-details")
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(*arguments), 20)
            journal = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
            self.assertEqual(journal["status"], "pending")
            self.assertEqual(journal["completed_requests"], {})
            self.assertEqual(journal["transport_receipt"]["workflow_run_id"], 123)
            self.assertFalse(journal["transport_receipt"]["execution_verified"])
            self.assertEqual(self.invoke_actual_client(*arguments), 1)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 1)
        self.assert_closing_reads(requests)
        work = json.loads((Path(self.state_dir) / "CONTINUATION.data").read_text())
        self.assertEqual(work["attempt_record"]["transport_receipt"]["workflow_run_id"], 123)
        self.assertEqual(work["effect_state"], "EFFECT_ACK_CONTINUE")

    def test_http_error_still_requires_fresh_repository_and_delivery_readback(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)

    def test_success_still_requires_fresh_exact_host_public_delivery_readback(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        self.assert_closing_reads(requests, repository=False)

    def test_same_failed_subject_without_new_cause_does_not_post_again(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            self.assertEqual(self.invoke_actual_client(), 1)
        posts = [request for request in requests if request.get_method() == "POST"]
        self.assertEqual(len(posts), 1, "unchanged failure submitted twice without new cause")

    def test_same_completed_request_closes_freshly_without_repeating_post(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 20)
            first_count = len(requests)
            self.assertEqual(self.invoke_actual_client(), 20)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 1,
                         "the same completed stable request was submitted twice")
        repeated = requests[first_count:]
        self.assertEqual([request.get_method() for request in repeated], ["GET", "GET"])
        work = json.loads((Path(self.state_dir) / "CONTINUATION.data").read_text())
        api = [task for task in work["work"] if task["id"].startswith("api:")]
        self.assertEqual(len(api), 1)
        self.assertEqual(api[0]["state"], "VERIFIED")
        self.assertTrue(api[0]["evidence"])
        self.assertEqual(work["effect_state"], "EFFECT_ACK_CONTINUE")

    def test_completed_request_cannot_repost_after_lost_work_cursor(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 20)
            journal_path = next(Path(self.state_dir).glob("*.json"))
            legacy = json.loads(journal_path.read_text())
            legacy.pop("completed_requests")
            journal_path.write_text(json.dumps(legacy))
            (Path(self.state_dir) / "CONTINUATION.data").unlink()
            self.assertEqual(self.invoke_actual_client(), 20)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 1,
                         "completed journal was replayed after losing the projection")

    def test_completed_request_is_not_forgotten_after_another_completed_id(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client("--request-id", "first-completed"), 20)
            self.assertEqual(self.invoke_actual_client("--request-id", "second-completed"), 20)
            self.assertEqual(self.invoke_actual_client("--request-id", "first-completed"), 20)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2,
                         "a later completed ID erased the earlier idempotency witness")

    def test_old_completion_does_not_close_a_later_failed_request(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect

        def fail_later_request(request, **kwargs):
            if (request.get_method() == "POST"
                    and json.loads(request.data)["inputs"]["request_id"] == "later-failed"):
                requests.append(request)
                raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, io.BytesIO(b"denied"))
            return original(request, **kwargs)

        opener.open.side_effect = fail_later_request
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client("--request-id", "earlier-completed"), 20)
            self.assertEqual(self.invoke_actual_client("--request-id", "later-failed"), 1)
            journal_path = next(Path(self.state_dir).glob("*.json"))
            before = journal_path.read_bytes()
            self.assertEqual(self.invoke_actual_client("--request-id", "earlier-completed"), 20)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)
        self.assertEqual(journal_path.read_bytes(), before)
        api = [task for task in self.continuation_work()["work"] if task["id"].startswith("api:")]
        self.assertEqual(len(api), 1)
        self.assertEqual(api[0]["state"], "OPEN")

    def test_full_completion_memory_blocks_new_post_without_forgetting_old_ids(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "MAX_COMPLETED_REQUESTS", 2):
            self.assertEqual(self.invoke_actual_client("--request-id", "first-completed"), 20)
            self.assertEqual(self.invoke_actual_client("--request-id", "second-completed"), 20)
            self.assertEqual(self.invoke_actual_client("--request-id", "third-unreserved"), 1)
            self.assertEqual(self.invoke_actual_client("--request-id", "first-completed"), 20)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)
        journal = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
        self.assertEqual(set(journal["completed_requests"]), {"first-completed", "second-completed"})

    def test_repository_parser_recursion_failure_cannot_skip_public_closing_readback(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect

        def deeply_nested_repository(request, **kwargs):
            response = original(request, **kwargs)
            if request.full_url.startswith("https://api.github.com/"):
                response.raw = b'[' * 2500 + b'0' + b']' * 2500
            return response

        opener.open.side_effect = deeply_nested_repository
        parse = client.unique_json

        def exhausted_decoder(raw):
            if raw.startswith(b'['):
                raise RecursionError("fixture: decoder recursion limit")
            return parse(raw)

        # Decoder limits vary between supported Python builds. Inject the
        # parser's resource failure to verify the actual closing control path.
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "unique_json", side_effect=exhausted_decoder):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)
        self.assertEqual(sum(request.get_method() == "GET" for request in requests), 2)

    def test_scoped_done_remains_continue_and_reuses_shared_closure_validator(self) -> None:
        opener, requests = self.transport()
        validate = client.validate_client_readback
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "validate_client_readback", wraps=validate) as gate:
            self.assertEqual(self.invoke_actual_client(), 20)
        gate.assert_called_once()
        readback, subject, window = gate.call_args.args
        self.assertEqual(subject["head"], "a" * 40)
        self.assertEqual(subject["tree"], "b" * 40)
        self.assertEqual(readback["delivery"]["state"], "PENDING")
        self.assertFalse(readback["delivery"]["working_software"])
        self.assertGreater(readback["repository"]["observed_at"], window["completed_at"])
        self.assert_closing_reads(requests)

    def test_repository_read_failure_still_gets_public_origin_and_never_done(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect

        def broken_repository(request, **kwargs):
            if request.get_method() == "GET" and request.full_url.startswith("https://api.github.com/"):
                requests.append(request)
                raise urllib.error.URLError("unavailable")
            return original(request, **kwargs)

        opener.open.side_effect = broken_repository
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)

    def test_other_origin_final_url_and_duplicate_repository_json_are_rejected(self) -> None:
        for kind in ("delivery", "repository"):
            with self.subTest(kind=kind):
                opener, requests = self.transport()
                original = opener.open.side_effect

                def invalid_readback(request, **kwargs):
                    response = original(request, **kwargs)
                    if request.get_method() == "GET":
                        if kind == "delivery" and request.full_url == "https://raumzeitterminal.de/":
                            response.url = "https://other.invalid/"
                        elif kind == "repository" and request.full_url.startswith("https://api.github.com/"):
                            response.raw = b'{"sha":"a","sha":"b"}'
                    return response

                opener.open.side_effect = invalid_readback
                with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                    self.assertEqual(self.invoke_actual_client("--artifact-id", "invalid-closure-" + kind), 1)
                self.assert_closing_reads(requests)

    def test_adapter_token_is_never_forwarded_to_closing_origins(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        for request in requests:
            if request.get_method() == "GET":
                self.assertIsNone(request.get_header("Authorization"))

    def test_failure_survives_new_process_and_new_request_id(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        program = '''
import json
from unittest import mock
from tests.test_api_client import ApiClientEndOfActionConformanceTests
from scripts import qikvrt_api_client as client
fixture = ApiClientEndOfActionConformanceTests()
opener, requests = fixture.transport(failure=True)
with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
    result = fixture.invoke_actual_client("--request-id", "new-clock-and-request-id")
print(json.dumps({"exit": result, "posts": sum(r.get_method() == "POST" for r in requests),
                  "gets": sum(r.get_method() == "GET" for r in requests)}))
'''
        completed = subprocess.run([sys.executable, "-B", "-c", program], cwd=REPOSITORY_ROOT,
                                   env=dict(os.environ), capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"exit": 1, "posts": 0, "gets": 2})
        journal = next(Path(self.state_dir).glob("*.json")).read_text()
        self.assertNotIn("test-token", journal)
        self.assertNotIn("payload_b64", journal)
        self.assertEqual(os.stat(next(Path(self.state_dir).glob("*.json"))).st_mode & 0o777, 0o600)

    def test_new_cause_admits_one_attempt_but_clocks_do_not(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            path = next(Path(self.state_dir).glob("*.json"))
            previous = json.loads(path.read_text())["current"]
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(previous, observed_at="later", repository_head="c" * 40)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
            self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)
            evidence.write_text(json.dumps(dict(previous, cause="f" * 64)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
            self.assertEqual(sum(r.get_method() == "POST" for r in requests), 2)
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
            self.assertEqual(sum(r.get_method() == "POST" for r in requests), 2)

    def test_successful_and_changed_subject_requests_are_not_suppressed(self) -> None:
        for failure in (False, True):
            with self.subTest(failure=failure):
                opener, requests = self.transport(failure=failure)
                with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                    self.invoke_actual_client("--artifact-id", "first" + str(failure))
                    arguments = (("--artifact-id", "second" + str(failure)) if failure
                                 else ("--artifact-id", "firstFalse", "--request-id", "new-accepted-request"))
                    self.invoke_actual_client(*arguments)
                self.assertEqual(sum(r.get_method() == "POST" for r in requests), 2)

    def test_timeout_is_ambiguous_and_new_cause_does_not_hide_missing_effect_readback(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect

        def timeout(request, **kwargs):
            if request.get_method() == "POST":
                requests.append(request)
                raise TimeoutError()
            return original(request, **kwargs)

        opener.open.side_effect = timeout
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            previous = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())["current"]
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(previous, cause="f" * 64)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)
        self.assertEqual(sum(r.get_method() == "GET" for r in requests), 4)

    def test_state_write_failure_after_post_preserves_count_and_still_closes(self) -> None:
        opener, requests = self.transport()
        writer = client.atomic_write_bytes
        writes = 0

        def fail_second_write(*args, **kwargs):
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError("disk unavailable")
            return writer(*args, **kwargs)

        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "atomic_write_bytes", side_effect=fail_second_write):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)
        journal = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
        self.assertEqual(journal["status"], "in_flight")
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)

    def test_new_cause_cannot_bypass_explicit_effect_acceptance(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            current = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())["current"]
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(current, cause="f" * 64)))
            argv = ["qikvrt_api_client.py", "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                    "--operation", "verify", "--request-id", "same-causal-subject", "--dry-run", "false",
                    "--retry-evidence-file", str(evidence)]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    client.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)

    def test_corrupt_or_symlink_state_blocks_before_post_and_still_closes(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            path = next(Path(self.state_dir).glob("*.json"))
            path.write_text("corrupt")
            self.assertEqual(self.invoke_actual_client(), 1)
            victim = Path(self.state_dir) / "victim.data"
            victim.write_text("untouched")
            path.unlink()
            path.symlink_to(victim)
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assertEqual(sum(r.get_method() == "POST" for r in requests), 1)
        self.assertEqual(sum(r.get_method() == "GET" for r in requests), 6)
        self.assertEqual(victim.read_text(), "untouched")

    def continuation_work(self) -> dict:
        return json.loads((Path(self.state_dir) / "CONTINUATION.data").read_text())

    def assert_original_attempt_is_retained(self, original: dict) -> None:
        def dictionaries(value):
            if isinstance(value, dict):
                yield value
                for child in value.values():
                    yield from dictionaries(child)
            elif isinstance(value, list):
                for child in value:
                    yield from dictionaries(child)

        histories = [json.loads(path.read_text()) for path in Path(self.state_dir).glob("work-*.data")]
        self.assertTrue(any(item == original for history in histories for item in dictionaries(history)),
                        "admitted successor erased the original durable failure metadata")

    def test_admitted_retry_retains_original_failure_evidence(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            original = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(original["current"], cause="f" * 64)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)
        self.assert_original_attempt_is_retained(original)

    def test_legacy_retry_without_work_history_preserves_original_attempt(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            original = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
            (Path(self.state_dir) / "CONTINUATION.data").unlink()
            for path in Path(self.state_dir).glob("work-*.data"):
                path.unlink()
            evidence = Path(self.state_dir) / "retry-evidence.data"
            evidence.write_text(json.dumps(dict(original["current"], capability="e" * 64)))
            self.assertEqual(self.invoke_actual_client("--retry-evidence-file", str(evidence)), 1)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)
        self.assert_original_attempt_is_retained(original)

    def test_interrupted_intent_is_inherited_even_when_next_request_changes(self) -> None:
        opener, requests = self.transport()
        original = opener.open.side_effect
        interrupt = True

        def interrupted(request, **kwargs):
            if interrupt and request.get_method() == "POST":
                requests.append(request)
                raise KeyboardInterrupt()
            return original(request, **kwargs)

        opener.open.side_effect = interrupted
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(KeyboardInterrupt):
                self.invoke_actual_client("--artifact-id", "interrupted-task")
            intent = next(Path(self.state_dir).glob("*.json"))
            old_key = json.loads(intent.read_text())["subject_key"]
            self.assertEqual(json.loads(intent.read_text())["status"], "in_flight")
            interrupt = False
            self.invoke_actual_client("--artifact-id", "new-task-after-interruption")
        tasks = self.continuation_work()["work"]
        old = next((task for task in tasks if task["id"] == "api:" + old_key), None)
        self.assertIsNotNone(old, "Interrupted predecessor intent was silently dropped")
        self.assertEqual(old["state"], "OPEN")
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)
        self.assertEqual(json.loads(intent.read_text())["status"], "in_flight")

    def test_history_write_failure_does_not_drop_failed_work_on_changed_request(self) -> None:
        opener, _ = self.transport(failure=True)
        writer = client.atomic_write_bytes
        writes = 0

        def fail_history(*args, **kwargs):
            nonlocal writes
            writes += 1
            if writes == 3:
                raise OSError("fixture:history write unavailable")
            return writer(*args, **kwargs)

        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener), \
                mock.patch.object(client, "atomic_write_bytes", side_effect=fail_history):
            self.assertEqual(self.invoke_actual_client("--artifact-id", "failed-history-task"), 1)
        record = json.loads(next(Path(self.state_dir).glob("*.json")).read_text())
        old_key = record["subject_key"]
        self.assertEqual(record["status"], "failed")
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client("--artifact-id", "changed-after-history-failure")
        old = next((task for task in self.continuation_work()["work"] if task["id"] == "api:" + old_key), None)
        self.assertIsNotNone(old, "Failed predecessor was dropped after work persistence failed")
        self.assertEqual(old["state"], "OPEN")

    def test_failed_run_open_work_is_inherited_by_noop_successor(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            first = self.continuation_work()
            self.invoke_actual_client()
        second = self.continuation_work()
        self.assertEqual(second["previous_run"]["execution_id"], first["execution_id"])
        self.assertEqual(set(second["previous_run"]["open_work"]),
                         {task["id"] for task in first["work"] if task["state"] == "OPEN"})
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 1)
        self.assertEqual(sum(request.get_method() == "GET" for request in requests), 4)
        self.assertEqual(len(list(Path(self.state_dir).glob("work-*.data"))), 2)

    def test_changed_request_keeps_previous_unrepaired_operation(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client("--artifact-id", "previous-task")
            first = self.continuation_work()
            old_api = next(task["id"] for task in first["work"] if task["id"].startswith("api:"))
            self.invoke_actual_client("--artifact-id", "different-task")
        tasks = self.continuation_work()["work"]
        self.assertEqual(next(task["state"] for task in tasks if task["id"] == old_api), "OPEN")
        self.assertEqual(sum(task["id"].startswith("api:") for task in tasks), 2)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 2)

    def test_open_repository_gap_closes_only_after_fresh_readback(self) -> None:
        opener, _ = self.transport()
        original = opener.open.side_effect
        broken = True

        def repository_gap(request, **kwargs):
            response = original(request, **kwargs)
            if broken and request.full_url.startswith("https://api.github.com/"):
                response.raw = b'{}'
            return response

        opener.open.side_effect = repository_gap
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            first = self.continuation_work()
            identifier = "repository:ingolf-lohmann/qik-vrt@main"
            self.assertEqual(next(task["state"] for task in first["work"] if task["id"] == identifier), "OPEN")
            broken = False
            self.invoke_actual_client("--artifact-id", "successor-subject")
        second = self.continuation_work()
        task = next(task for task in second["work"] if task["id"] == identifier)
        self.assertEqual(task["state"], "VERIFIED")
        self.assertTrue(task["evidence"])
        self.assertIn(identifier, second["previous_run"]["open_work"])

    def test_scoped_success_leaves_public_delivery_as_next_run_task(self) -> None:
        opener, _ = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        receipt = self.continuation_work()
        self.assertEqual(next(task["state"] for task in receipt["work"] if task["id"] == "delivery:raumzeitterminal.de"), "OPEN")
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["ordinary_release"])
        self.assertNotIn("test-token", json.dumps(receipt))

    def test_corrupt_continuation_cannot_erase_previous_obligations_or_post(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
            path = Path(self.state_dir) / "CONTINUATION.data"
            path.write_text("corrupt")
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assertEqual(sum(request.get_method() == "POST" for request in requests), 1)
        self.assertEqual(path.read_text(), "corrupt")
        self.assertEqual(len(list(Path(self.state_dir).glob("work-*.data"))), 1)


class GitHubShellWrapperTests(unittest.TestCase):
    """Exercise the real wrapper and current parser with transport disabled."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.capture = self.directory / "capture.json"
        self.payload = self.directory / "payload with spaces.json"
        self.payload.write_bytes(b'{"fixture":true}\n')
        # This is an inert test marker, never a GitHub credential or auth test.
        self.marker = "shell-wrapper-fixture-not-a-credential"
        launcher = self.bin / "python3"
        launcher.write_text("#!" + sys.executable + "\n" + textwrap.dedent(r'''
            import atexit
            import hashlib
            import json
            import os
            import runpy
            import sys
            import urllib.request
            from pathlib import Path

            marker = os.environ.get("WRAPPER_TEST_MARKER", "")
            report = {"credential_in_argv": bool(marker) and marker in sys.argv,
                      "obsolete_token_option": "--token" in sys.argv,
                      "environment_matches": os.environ.get("QIKVRT_API_TOKEN") == marker,
                      "calls": []}

            @atexit.register
            def save_report():
                Path(os.environ["WRAPPER_TEST_CAPTURE"]).write_text(json.dumps(report))

            class Response:
                def __init__(self, url, status, body):
                    self.url, self.status, self.body = url, status, body
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self, size=-1):
                    return self.body if size < 0 else self.body[:size]
                def geturl(self):
                    return self.url

            class OfflineTransport:
                def open(self, request, **kwargs):
                    method, url = request.get_method(), request.full_url
                    call = {"method": method, "url": url,
                            "authorization_matches": request.get_header("Authorization") == "Bearer " + marker}
                    report["calls"].append(call)
                    if method == "POST":
                        assert url == "https://api.github.com/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches"
                        body = json.loads(request.data)
                        call["inputs"] = body["inputs"]
                        if os.environ.get("WRAPPER_TEST_FAIL_POST") == "true":
                            raise OSError("isolated transport failure")
                        return Response(url, 204, b"")
                    assert method == "GET"
                    if url == "https://api.github.com/repos/owner/repo/commits/main":
                        return Response(url, 200, json.dumps({"sha": "a" * 40,
                            "commit": {"tree": {"sha": "b" * 40}}}).encode())
                    assert url == "https://raumzeitterminal.de/"
                    return Response(url, 200, b"isolated delivery fixture")

            urllib.request.build_opener = lambda *args: OfflineTransport()
            script, *arguments = sys.argv[1:]
            sys.argv = [script, *arguments]
            runpy.run_path(script, run_name="__main__")
        '''))
        launcher.chmod(0o700)

    def invoke(self, *, request_id="wrapper-one", token=True, extra=(), fail_post=False):
        environment = os.environ.copy()
        environment.pop("GITHUB_TOKEN", None)
        environment.pop("QIKVRT_API_TOKEN", None)
        if token:
            environment["GITHUB_TOKEN"] = self.marker
        environment.update({
            "PATH": str(self.bin) + os.pathsep + environment.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "WRAPPER_TEST_MARKER": self.marker,
            "WRAPPER_TEST_CAPTURE": str(self.capture),
            "WRAPPER_TEST_FAIL_POST": str(fail_post).lower(),
            "QIKVRT_API_CLIENT_STATE_DIR": str(self.directory / "state"),
        })
        arguments = ["sh", "scripts/qikvrt_github_api_client.sh", "owner", "repo", str(self.payload)]
        if request_id is not None:
            arguments.append(request_id)
        result = subprocess.run(arguments + list(extra), cwd=REPOSITORY_ROOT,
                                env=environment, text=True, capture_output=True, timeout=10)
        report = json.loads(self.capture.read_text()) if self.capture.exists() else None
        self.assertNotIn(self.marker, result.stdout + result.stderr)
        return result, report

    def test_current_parser_receives_environment_and_exact_stable_request(self):
        result, report = self.invoke()
        self.assertEqual(result.returncode, 20, result.stderr)
        self.assertTrue(report["environment_matches"])
        self.assertFalse(report["credential_in_argv"])
        self.assertFalse(report["obsolete_token_option"])
        posts = [call for call in report["calls"] if call["method"] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertTrue(posts[0]["authorization_matches"])
        inputs = posts[0]["inputs"]
        self.assertEqual(inputs["request_id"], "wrapper-one")
        self.assertEqual(inputs["dry_run"], "true")
        self.assertFalse(inputs["effect_accepted"])
        self.assertEqual(base64.b64decode(inputs["payload_b64"]), self.payload.read_bytes())
        self.assertEqual(inputs["expected_sha256"], hashlib.sha256(self.payload.read_bytes()).hexdigest())
        self.assertEqual([call["method"] for call in report["calls"]], ["POST", "GET", "GET"])
        self.assertFalse(report["calls"][-1]["authorization_matches"])

    def test_missing_credential_stops_before_python(self):
        result, report = self.invoke(token=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)

    def test_missing_stable_request_stops_before_python(self):
        result, report = self.invoke(request_id=None)
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(report)

    def test_extra_effect_options_cannot_change_dry_run(self):
        result, report = self.invoke(extra=("--dry-run", "false", "--accept-effect"))
        self.assertEqual(result.returncode, 2)
        self.assertIsNone(report)

    def test_original_parser_rejects_invalid_request_without_transport(self):
        result, report = self.invoke(request_id="invalid request id")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["calls"], [])
        self.assertFalse(report["credential_in_argv"])
        self.assertIn("--request-id", result.stderr)

    def test_original_client_transport_failure_exit_is_preserved(self):
        result, report = self.invoke(fail_post=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(report["credential_in_argv"])
        self.assertEqual([call["method"] for call in report["calls"]], ["POST", "GET", "GET"])


class RulesetRestBootstrapTests(RulesetClientFixture):
    writer_version = "principal-review-v4"

    def test_current_provider_200_retains_original_run_identity(self):
        body = {"workflow_run_id": 321, "run_url": self.prefix + "actions/runs/321",
                "html_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/321"}
        code, out, error, opener = self.invoke(post_status=200, post_raw=json.dumps(body).encode())
        self.assertEqual(code, 20, error)
        receipt = json.loads(out)
        self.assertEqual(receipt["workflow_run_id"], 321)
        self.assertTrue(receipt["transport_acknowledged"])
        self.assertFalse(receipt["ruleset_effect_verified"])
        self.assertEqual(len(self.posts(opener)), 1)

    def test_original_intent_is_on_disk_before_provider_post(self):
        with tempfile.TemporaryDirectory() as state:
            def before(_request):
                attempts = list(Path(state).glob("*.json"))
                self.assertEqual(len(attempts), 1)
                record = json.loads(attempts[0].read_bytes())
                self.assertEqual(record["status"], "in_flight")
                self.assertEqual(record["operation_binding"]["main_sha"], self.sha)
                self.assertEqual(record["operation_binding"]["workflow_blob_sha"], self.writer_blob)
                self.assertNotIn(self.token, attempts[0].read_text())
            code, _, error, _ = self.invoke(arguments=("--state-dir", state), before_post=before)
            self.assertEqual(code, 20, error)

    def test_lost_response_cannot_be_replayed_with_a_new_request_identifier(self):
        with tempfile.TemporaryDirectory() as state:
            args = ("--state-dir", state)
            first, _, _, p1 = self.invoke(arguments=args, post_error=TimeoutError("private detail"))
            second, out, error, p2 = self.invoke(arguments=(*args, "--request-id", "changed-id"))
            self.assertEqual(first, 1)
            self.assertEqual(len(self.posts(p1)), 1)
            self.assertEqual(len(self.posts(p2)), 0, error + out)
            self.assertNotEqual(second, 0)
            self.assertEqual(json.loads(out)["dispatch_count"], 0)


class RulesetAuthorityHTTPTests(RulesetClientFixture):
    """Real REST wire and original controller; GitHub alone is a fixture."""
    writer_version = "principal-review-v4"

    def setUp(self):
        super().setUp()
        import qikvrt_github_api_shim as shim
        import threading
        from datetime import datetime, timedelta, timezone
        from http.server import ThreadingHTTPServer
        self.shim = shim
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caller = "b64url:" + base64.urlsafe_b64encode(b"r" * 32).decode().rstrip("=")
        self.env = mock.patch.dict(os.environ, {
            "QIKVRT_RULESET_AUTHORITY_ENABLED": "1", "QIKVRT_ALLOWED_REPOSITORY": client.RULESET_REPOSITORY,
            "QIKVRT_API_PRINCIPAL": "ingolf-lohmann", "QIKVRT_API_TOKEN": self.caller,
            "QIKVRT_API_TOKEN_EXPIRES_UTC": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "QIKVRT_RULESET_ADMIN_TOKEN": self.token, "QIKVRT_GITHUB_ADMIN_TOKEN": "",
            "QIKVRT_MESH_TOKEN": "", "QIKVRT_AUTHORITY_APP_TOKEN": "", "GITHUB_TOKEN": "",
            "QIKVRT_API_CLIENT_STATE_DIR": self.temp.name, "QIKVRT_RATE_LIMIT_PER_MINUTE": "10000"})
        self.env.start(); self.addCleanup(self.env.stop)
        self.provider_calls, self.provider_failure = [], None
        self.real_opener = client.urllib.request.build_opener(client.NoRedirectHandler())
        def provider(request, timeout):
            if request.full_url.startswith("http://127.0.0.1:"):
                return self.real_opener.open(request, timeout=timeout)
            self.provider_calls.append(request)
            self.assertNotIn(self.caller, str(request.headers))
            if request.full_url == "https://raumzeitterminal.de/":
                response = self.response(200, raw=b"public fixture")
            else:
                self.assertTrue(request.full_url.startswith(self.prefix))
                path = request.full_url[len(self.prefix):]
                if not (path == "commits/main" and request.get_header("Authorization") is None):
                    self.assertEqual(request.get_header("Authorization"), "Bearer " + self.token)
                if request.get_method() == "POST":
                    self.assertEqual(path, f"actions/workflows/{client.RULESET_WORKFLOW}/dispatches")
                    if self.provider_failure: raise self.provider_failure
                    response = self.response(200, document={"workflow_run_id": self.run_id,
                        "run_url": self.prefix + f"actions/runs/{self.run_id}",
                        "html_url": f"https://github.com/{client.RULESET_REPOSITORY}/actions/runs/{self.run_id}"})
                elif path == "commits/main":
                    response = self.response(200, document={"sha": self.sha, "commit": {"tree": {"sha": "b" * 40}}})
                else:
                    self.assertEqual(request.get_method(), "GET")
                    response = self.response(200, document=self.documents[path])
            response.geturl.return_value = request.full_url
            return response
        opener = mock.Mock(); opener.open.side_effect = provider
        patch = mock.patch.object(client.urllib.request, "build_opener", return_value=opener)
        patch.start(); self.addCleanup(patch.stop)
        with shim._RATE_LOCK: shim._RATE_WINDOWS.clear()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), shim.QikvrtGitHubApiShim)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start(); self.addCleanup(self.stop_server)
        self.route = f"/repos/{client.RULESET_REPOSITORY}/qikvrt/ruleset-authority"

    def stop_server(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3)

    def wire(self, *, method="POST", body=None, path=None, token=None):
        import http.client
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        headers = {"Authorization": "Bearer " + (self.caller if token is None else token),
                   "Content-Type": "application/json"}
        if body is None and method == "POST":
            body = {"schema": "qikvrt-ruleset-authority-rest/v1", "request_id": "rest-one",
                    "expected_main_sha": self.sha, "writer_version": self.version, "effect_accepted": True}
        try:
            connection.request(method, path or self.route,
                body=None if body is None else json.dumps(body), headers=headers)
            response = connection.getresponse(); raw = response.read()
            self.assertNotIn(self.token, raw.decode())
            self.assertNotIn(self.caller, raw.decode())
            return response.status, json.loads(raw)
        finally: connection.close()

    def test_post_uses_original_controller_and_keeps_transport_separate(self):
        self.documents["branches/main"]["protected"] = False
        status, data = self.wire()
        self.assertEqual(status, 202, data)
        self.assertEqual(data["handler_result"]["workflow_run_id"], self.run_id)
        self.assertFalse(data["handler_result"]["execution_verified"])
        self.assertFalse(data["effect_ack_done"])
        posts = [r for r in self.provider_calls if r.get_method() == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].data, b'{"ref":"main"}')
        attempts = list((Path(self.temp.name) / "ruleset-authority-server").glob("*.json"))
        self.assertEqual(json.loads(attempts[0].read_bytes())["status"], "pending")

    def test_get_independently_verifies_run_jobs_ruleset_and_protected_main(self):
        from urllib.parse import urlencode
        query = urlencode({"request_id": "read-one", "expected_main_sha": self.sha,
                           "writer_version": self.version, "run_id": self.run_id})
        status, data = self.wire(method="GET", path=self.route + "?" + query)
        self.assertEqual(status, 200, data)
        self.assertTrue(data["handler_result"]["ruleset_effect_verified"])
        self.assertFalse(data["handler_result"]["mutation_attribution_verified"])
        self.assertFalse(data["effect_ack_done"])
        self.assertTrue(all(r.get_method() == "GET" for r in self.provider_calls))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_disabled_route_and_read_credential_cannot_dispatch(self):
        with mock.patch.dict(os.environ, {"QIKVRT_RULESET_AUTHORITY_ENABLED": "0"}):
            self.assertEqual(self.wire()[0], 404)
        self.assertEqual(self.wire(token="separate-read-only-token")[0], 401)
        self.assertEqual(self.provider_calls, [])

    def test_foreign_principal_or_repository_cannot_use_authority(self):
        with mock.patch.dict(os.environ, {"QIKVRT_API_PRINCIPAL": "another-owner"}):
            self.assertEqual(self.wire()[0], 403)
        self.assertEqual(self.wire(path="/repos/foreign/repo/qikvrt/ruleset-authority")[0], 403)
        self.assertEqual(self.provider_calls, [])

    def test_missing_provider_binding_never_reuses_generic_or_caller_tokens(self):
        with mock.patch.dict(os.environ, {"QIKVRT_RULESET_ADMIN_TOKEN": "", "GITHUB_TOKEN": "unscoped"}):
            self.assertEqual(self.wire()[0], 503)
        with mock.patch.dict(os.environ, {"QIKVRT_RULESET_ADMIN_TOKEN": self.caller}):
            self.assertEqual(self.wire()[0], 503)
        self.assertEqual(self.provider_calls, [])

    def test_exact_effect_and_field_validation_precedes_all_provider_requests(self):
        original = {"schema": "qikvrt-ruleset-authority-rest/v1", "request_id": "rest-one",
                    "expected_main_sha": self.sha, "writer_version": self.version, "effect_accepted": True}
        for patch in ({"effect_accepted": "true"}, {"ref": "other"}, {"expected_main_sha": "../main"},
                      {"writer_version": "unknown"}, {"request_id": 1}, {"schema": "other"}):
            with self.subTest(patch=patch): self.assertEqual(self.wire(body={**original, **patch})[0], 400)
        self.assertEqual(self.provider_calls, [])

    def test_lost_response_through_http_does_not_admit_second_provider_post(self):
        self.provider_failure = TimeoutError("provider-private-detail")
        self.assertEqual(self.wire()[0], 409)
        self.provider_failure = None
        status, data = self.wire()
        self.assertEqual(status, 409, data)
        self.assertEqual(data["handler_result"]["dispatch_count"], 0)
        self.assertEqual(len([r for r in self.provider_calls if r.get_method() == "POST"]), 1)

    def test_duplicate_readback_query_and_post_query_are_rejected(self):
        self.assertEqual(self.wire(method="GET", path=self.route + "?run_id=1&run_id=2")[0], 400)
        self.assertEqual(self.wire(path=self.route + "?run_id=1")[0], 400)
        self.assertEqual(self.provider_calls, [])

    def test_recorded_run_survives_client_loss_and_get_does_not_rewrite_journal(self):
        from urllib.parse import urlencode
        self.assertEqual(self.wire()[0], 202)
        path = next((Path(self.temp.name) / "ruleset-authority-server").glob("*.json"))
        before = path.read_bytes()
        query = urlencode({"request_id": "rest-one", "expected_main_sha": self.sha, "writer_version": self.version})
        status, data = self.wire(method="GET", path=self.route + "?" + query)
        self.assertEqual(status, 200, data)
        self.assertEqual(data["handler_result"]["workflow_run_id"], self.run_id)
        self.assertTrue(data["handler_result"]["ruleset_effect_verified"])
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(len([r for r in self.provider_calls if r.get_method() == "POST"]), 1)

    def test_unknown_provider_outcome_retains_original_intent_for_get_only(self):
        from urllib.parse import urlencode
        self.provider_failure = TimeoutError("private")
        self.assertEqual(self.wire()[0], 409)
        query = urlencode({"request_id": "rest-one", "expected_main_sha": self.sha, "writer_version": self.version})
        status, data = self.wire(method="GET", path=self.route + "?" + query)
        self.assertEqual(status, 202, data)
        self.assertEqual(data["handler_result"]["readback_state"], "ORIGINAL_INTENT_RETAINED_RUN_ID_UNRESOLVED")
        self.assertFalse(data["handler_result"]["ruleset_effect_verified"])
        self.assertEqual(data["handler_result"]["dispatch_count"], 0)
        self.assertEqual(len([r for r in self.provider_calls if r.get_method() == "POST"]), 1)

    def test_repository_client_can_dispatch_and_recover_over_mesh_rest(self):
        base = ["client", "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                "--base-url", f"http://127.0.0.1:{self.server.server_port}", "--ruleset-via-mesh",
                "--expected-main-sha", self.sha, "--ruleset-writer-version", self.version,
                "--request-id", "cli-rest", "--state-dir", str(Path(self.temp.name) / "caller")]
        for operation, extra, expected in [
            ("ruleset_authority_dispatch", ["--dry-run", "false", "--accept-effect"], 20),
            ("ruleset_authority_readback", [], 0)]:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", [*base, "--operation", operation, *extra]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = client.main()
            self.assertEqual(code, expected, err.getvalue() + out.getvalue())
            result = json.loads(out.getvalue())
            self.assertFalse(result["ordinary_release"])
            self.assertNotIn(self.token, out.getvalue())
            self.assertNotIn(self.caller, out.getvalue())
        self.assertTrue(result["result"]["remote_readback"]["handler_result"]["ruleset_effect_verified"])
        self.assertEqual(len([r for r in self.provider_calls if r.get_method() == "POST"]), 1)

    def test_client_rejects_foreign_subjects_and_incomplete_remote_effect_claims(self):
        from types import SimpleNamespace
        from urllib.parse import urlencode
        query = urlencode({"request_id": "read-one", "expected_main_sha": self.sha,
                           "writer_version": self.version, "run_id": self.run_id})
        status, data = self.wire(method="GET", path=self.route + "?" + query)
        self.assertEqual(status, 200, data)
        args = SimpleNamespace(operation="ruleset_authority_readback", request_id="read-one",
            expected_main_sha=self.sha, ruleset_writer_version=self.version, ruleset_run_id=str(self.run_id))
        for patch in ({"main_sha": "f" * 40}, {"request_id": "foreign"}, {"workflow_blob_sha": "f" * 40},
                      {"effect_state": "EFFECT_ACK_DONE"}, {"execution_verified": False},
                      {"main_protected": False}, {"observed_ruleset_sha256": "f" * 64}):
            with self.subTest(patch=patch):
                changed = copy.deepcopy(data); changed["handler_result"].update(patch)
                with self.assertRaises(ValueError): client.bound_ruleset_rest_response(changed, args)
        self.assertTrue(all(r.get_method() == "GET" for r in self.provider_calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
