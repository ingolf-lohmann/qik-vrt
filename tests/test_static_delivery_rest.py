# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Real loopback HTTP + original installer in temporary directories; no live VPS."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import qikvrt_github_api_shim as shim
import qikvrt_api_client as client
from tools import qikvrt_self_host_provider as provider
from tests import test_self_host_static as static_tests


class StaticRestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.web = self.root / "web"
        self.web.mkdir()
        self.page = self.root / "index.html"
        self.page.write_bytes(b"<!doctype html><h1>Hello World</h1>\n")
        self.page_pin = provider.sha(self.page.read_bytes())
        fixture = static_tests.SSHBindingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.value["webroot"] = str(self.web)
        fixture.bind()
        self.binding_pin = provider.sha(fixture.binding.read_bytes())
        self.receipts = self.root / "receipts"
        self.receipts.mkdir(mode=0o700)
        import base64
        self.token = "b64url:" + base64.urlsafe_b64encode(b"isolated-rest-fixture-token-32bytes").rstrip(b"=").decode()
        self.env = {"QIKVRT_API_TOKEN": self.token, "QIKVRT_API_TOKEN_EXPIRES_UTC": "2099-01-01T00:00:00Z",
                    "QIKVRT_ALLOWED_REPOSITORY": "ingolf-lohmann/qik-vrt", "QIKVRT_API_PRINCIPAL": "ingolf-lohmann",
                    "QIKVRT_STATIC_DELIVERY_ENABLED": "1", "QIKVRT_STATIC_BINDING_FILE": str(fixture.binding),
                    "QIKVRT_STATIC_BINDING_SHA256": self.binding_pin, "QIKVRT_STATIC_FILE": str(self.page),
                    "QIKVRT_STATIC_FILE_SHA256": self.page_pin, "QIKVRT_STATIC_RECEIPTS_DIR": str(self.receipts),
                    "QIKVRT_RATE_LIMIT_PER_MINUTE": "100000"}
        patch = mock.patch.dict(os.environ, self.env)
        patch.start()
        self.addCleanup(patch.stop)
        self.transport = static_tests.LocalTransport()
        patch = mock.patch.object(provider, "static_ssh", self.transport)
        patch.start()
        self.addCleanup(patch.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), shim.QikvrtGitHubApiShim)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.close_server, thread)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.path = "/repos/ingolf-lohmann/qik-vrt/qikvrt/static-delivery"

    def close_server(self, thread):
        self.server.shutdown()
        self.server.server_close()
        thread.join(timeout=5)

    def value(self, mode="upload", request_id="original-request"):
        value = {"schema": shim.STATIC_REST_SCHEMA, "mode": mode, "request_id": request_id,
                 "expected_implementation_sha256": shim.STATIC_BOOT_BINDING,
                 "binding_sha256": self.binding_pin, "static_file_sha256": self.page_pin}
        if mode == "upload":
            value.update(expected_static_sha256="ABSENT", effect_accepted=True)
        return value

    def request(self, value, *, write=False, token=True, path=None):
        url = self.base + (path or self.path)
        headers = {"Authorization": f"Bearer {self.token}"} if token else {}
        data = None
        if write:
            data = json.dumps(value).encode()
            headers["Content-Type"] = "application/json"
        else:
            url += "?" + urllib.parse.urlencode(value)
        request = urllib.request.Request(url, data=data, headers=headers, method="POST" if write else "GET")
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def test_http_actual_install_fresh_read_and_private_backup(self):
        status, read = self.request(self.value("readback"))
        self.assertEqual(status, 200)
        self.assertIsNone(read["handler_result"]["sha256"])
        self.assertNotIn("body", read["handler_result"])
        self.assertEqual(list(self.web.iterdir()), [])
        status, receipt = self.request(self.value(), write=True)
        self.assertEqual(status, 200)
        self.assertEqual((self.web / "index.html").read_bytes(), self.page.read_bytes())
        self.assertEqual(receipt["handler_result"]["sha256"], self.page_pin)
        self.assertFalse(receipt["effect_ack_done"])
        self.assertFalse(receipt["handler_result"]["public_https_verified"])
        for private in (str(self.root), "identity_file", "known_hosts_file", "static-backup"):
            self.assertNotIn(private, json.dumps(receipt))

    def test_lost_ack_and_repeated_post_never_reinstall(self):
        self.transport.lost_reply = True
        self.assertEqual(self.request(self.value(), write=True)[0], 200)
        self.assertEqual(self.request(self.value(), write=True)[0], 409)
        self.assertEqual(self.request(self.value("reconcile"))[0], 200)
        self.assertEqual(self.transport.calls.count("install"), 1)

    def test_method_confusion_unknown_paths_and_caller_paths_never_write(self):
        for value, write in ((self.value(), False), (self.value("readback"), True),
                             (dict(self.value(), webroot="/etc"), True),
                             (dict(self.value(), effect_accepted="true"), True)):
            self.assertNotEqual(self.request(value, write=write)[0], 200)
        self.assertEqual(self.transport.calls, [])

    def test_authentication_repository_principal_and_enable_guard(self):
        self.assertEqual(self.request(self.value(), write=True, token=False)[0], 401)
        path = self.path.replace("ingolf-lohmann", "other")
        self.assertEqual(self.request(self.value(), write=True, path=path)[0], 403)
        with mock.patch.dict(os.environ, {"QIKVRT_API_PRINCIPAL": "other"}):
            self.assertEqual(self.request(self.value(), write=True)[0], 403)
        with mock.patch.dict(os.environ, {"QIKVRT_STATIC_DELIVERY_ENABLED": "0"}):
            self.assertEqual(self.request(self.value(), write=True)[0], 404)
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN_EXPIRES_UTC": "2020-01-01T00:00:00Z"}):
            self.assertEqual(self.request(self.value(), write=True)[0], 401)
        self.assertEqual(self.transport.calls, [])

    def test_target_source_implementation_and_predecessor_drift_refuse(self):
        for key in ("binding_sha256", "static_file_sha256", "expected_implementation_sha256"):
            self.assertEqual(self.request(dict(self.value(), **{key: "f" * 64}), write=True)[0], 409)
        with mock.patch.object(shim, "static_implementation_binding", return_value="f" * 64):
            self.assertEqual(self.request(self.value(), write=True)[0], 503)
        (self.web / "index.html").write_bytes(b"new external predecessor")
        self.assertEqual(self.request(self.value(), write=True)[0], 409)
        self.assertNotIn("install", self.transport.calls)

    def test_missing_protected_binding_does_not_become_success(self):
        with mock.patch.dict(os.environ, {"QIKVRT_STATIC_BINDING_FILE": str(self.root / "missing")}):
            self.assertEqual(self.request(self.value(), write=True)[0], 503)
        self.assertEqual(self.transport.calls, [])

    def test_original_client_real_http_upload_and_reconcile(self):
        args = SimpleNamespace(operation="static_upload", owner="ingolf-lohmann", repo="qik-vrt",
            base_url=self.base, request_id="client-request", static_implementation_sha256=shim.STATIC_BOOT_BINDING,
            static_binding_sha256=self.binding_pin, expected_sha256=self.page_pin, static_previous_sha256="ABSENT")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client.static_mesh_operation(args, self.token), 0)
            self.assertEqual(client.static_mesh_operation(args, self.token), 2)
            args.operation = "static_reconcile"
            self.assertEqual(client.static_mesh_operation(args, self.token), 0)
        self.assertEqual(self.transport.calls.count("install"), 1)

    def test_unavailable_public_checker_is_not_file_or_domain_acceptance(self):
        with mock.patch.object(provider, "static_public_readback", return_value={
                "state": "HOLD_PUBLIC_STATIC_READBACK", "effect_ack_done": False}):
            self.assertEqual(self.request(self.value("public-readback"))[0], 409)
        self.assertEqual(self.transport.calls, [])

    def test_cli_requires_explicit_acceptance_and_rejects_caller_file(self):
        argv = ["qikvrt_api_client.py", "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                "--base-url", self.base, "--operation", "static_upload", "--request-id", "cli-request",
                "--static-implementation-sha256", shim.STATIC_BOOT_BINDING,
                "--static-binding-sha256", self.binding_pin, "--expected-sha256", self.page_pin,
                "--static-previous-sha256", "ABSENT"]
        for extra in ([], ["--dry-run", "false"],
                      ["--dry-run", "false", "--accept-effect", "--payload-file", "/etc/passwd"]):
            with mock.patch.object(sys, "argv", argv + extra), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    client.main()
                self.assertEqual(raised.exception.code, 2)
        self.assertEqual(self.transport.calls, [])

    def test_original_cli_complete_upload_and_readback(self):
        argv = ["qikvrt_api_client.py", "--owner", "ingolf-lohmann", "--repo", "qik-vrt",
                "--base-url", self.base, "--request-id", "full-cli-request",
                "--static-implementation-sha256", shim.STATIC_BOOT_BINDING,
                "--static-binding-sha256", self.binding_pin, "--expected-sha256", self.page_pin]
        with contextlib.redirect_stdout(io.StringIO()):
            with mock.patch.object(sys, "argv", argv + ["--operation", "static_upload", "--dry-run", "false",
                                   "--accept-effect", "--static-previous-sha256", "ABSENT"]):
                self.assertEqual(client.main(), 0)
            with mock.patch.object(sys, "argv", argv + ["--operation", "static_reconcile"]):
                self.assertEqual(client.main(), 0)
        self.assertEqual(self.transport.calls.count("install"), 1)

    def test_duplicate_query_field_does_not_read_or_write_host(self):
        query = urllib.parse.urlencode(self.value("readback")) + "&mode=upload"
        request = urllib.request.Request(self.base + self.path + "?" + query,
                                        headers={"Authorization": f"Bearer {self.token}"})
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()
        self.assertEqual(self.transport.calls, [])


if __name__ == "__main__":
    unittest.main()
