#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Client-side transport-boundary tests for the local dispatch adapter."""
from __future__ import annotations

import contextlib
import io
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


class ApiClientEndOfActionConformanceTests(unittest.TestCase):
    """Direct CLI obligations; an expected failure is OPEN, never client PASS.

    These execute the actual client with a recorded, deterministic transport.
    They do not execute a vendor AI session or prove public product delivery.
    The Owner contract and shared receipt validator remain the sole authority.
    """

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

    def invoke_actual_client(self) -> int:
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return ApiClientTests.invoke(
                    self, "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                    "--operation", "verify", "--request-id", "same-causal-subject",
                    "--dry-run", "false", "--accept-effect",
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
            self.assertTrue(repository_reads, "OPEN: no fresh repository HEAD/TREE read after action")
        public_url = "https://" + client_end_of_action_domain() + "/"
        self.assertTrue(
            any(request.get_method() == "GET" and request.full_url == public_url
                for request in closing),
            "OPEN: no fresh exact-host public delivery read after action",
        )
        for request in closing:
            if request.full_url == public_url:
                self.assertIsNone(request.get_header("Authorization"))

    @unittest.expectedFailure
    def test_scoped_handler_done_does_not_replace_fresh_client_closure(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        self.assert_closing_reads(requests)

    @unittest.expectedFailure
    def test_http_error_still_requires_fresh_repository_and_delivery_readback(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
        self.assert_closing_reads(requests)

    @unittest.expectedFailure
    def test_success_still_requires_fresh_exact_host_public_delivery_readback(self) -> None:
        opener, requests = self.transport()
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.invoke_actual_client()
        self.assert_closing_reads(requests, repository=False)

    @unittest.expectedFailure
    def test_same_failed_subject_without_new_cause_does_not_post_again(self) -> None:
        opener, requests = self.transport(failure=True)
        with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(self.invoke_actual_client(), 1)
            self.assertEqual(self.invoke_actual_client(), 1)
        posts = [request for request in requests if request.get_method() == "POST"]
        self.assertEqual(len(posts), 1, "OPEN: unchanged failure submitted twice without new cause")


if __name__ == "__main__":
    unittest.main(verbosity=2)
