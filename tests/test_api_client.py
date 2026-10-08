#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Client-side transport-boundary tests for the local dispatch adapter."""
from __future__ import annotations

import contextlib
import io
import hashlib
import json
import os
import sys
import tempfile
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
