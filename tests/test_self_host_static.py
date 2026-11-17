# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Run the actual remote installer in isolated directories, never a live VPS."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools import qikvrt_self_host_provider as p


class LocalTransport:
    def __init__(self):
        self.calls = []
        self.lost_reply = False
        self.before_install = None

    def __call__(self, binding, payload):
        self.calls.append(payload["mode"])
        if payload["mode"] == "install" and self.before_install:
            self.before_install()
        encoded = base64.b64encode(p.wire(payload)).decode()
        result = subprocess.run([sys.executable, "-B", "-c", p.STATIC_REMOTE, encoded],
                                capture_output=True, text=True, timeout=5)
        if result.returncode:
            raise ValueError("REMOTE_FIXTURE_REFUSED")
        if payload["mode"] == "install" and self.lost_reply:
            raise ValueError("ACK_LOST_AFTER_REAL_LOCAL_INSTALL")
        return json.loads(result.stdout)


class StaticHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.web = self.root / "web root ' $"
        self.web.mkdir()
        self.receipts = self.root / "receipts"
        self.receipts.mkdir(mode=0o700)
        self.store = p.Receipts(self.receipts)
        self.page = self.root / "candidate.html"
        self.page.write_bytes(b"<!doctype html><h1>Hello World</h1>\n")
        self.page_pin = p.sha(self.page.read_bytes())
        self.value = {"webroot": str(self.web)}
        self.transport = LocalTransport()
        self.binding_pin = "1" * 64

    def upload(self, previous="ABSENT", operation="fixture-operation"):
        return p.static_upload(self.value, self.binding_pin, self.page,
                               self.page_pin, previous, operation,
                               self.store, self.transport)

    def test_actual_install_and_separate_readback_match_original_bytes(self):
        result = self.upload()
        self.assertEqual(result["state"], "FILE_BYTES_VERIFIED")
        self.assertEqual((self.web / "index.html").read_bytes(), self.page.read_bytes())
        self.assertEqual(self.transport.calls, ["readback", "install", "readback"])
        self.assertFalse(result["public_https_verified"])
        self.assertFalse(result["effect_ack_done"])
        self.assertEqual((self.web / "index.html").stat().st_mode & 0o777, 0o644)

    def test_readback_does_not_create_webroot_files(self):
        result = p.static_read(self.value, self.transport)
        self.assertIsNone(result["sha256"])
        self.assertEqual(list(self.web.iterdir()), [])

    def test_old_bytes_are_backed_up_privately_before_replacement(self):
        old = b"<h1>Previous site</h1>"
        (self.web / "index.html").write_bytes(old)
        self.upload(p.sha(old))
        backup = self.store.get("fixture-operation", "static-backup")
        self.assertEqual(base64.b64decode(backup["body"]), old)
        self.assertEqual(self.store.path("fixture-operation", "static-backup").stat().st_mode & 0o777, 0o600)

    def test_lost_upload_reply_is_recovered_without_second_install(self):
        self.transport.lost_reply = True
        self.assertEqual(self.upload()["state"], "FILE_BYTES_VERIFIED")
        self.assertEqual(self.transport.calls.count("install"), 1)
        self.assertEqual(self.store.get("fixture-operation", "static-transport")["outcome"],
                         "SSH_OUTCOME_UNKNOWN")

    def test_same_operation_never_replays_install(self):
        self.upload()
        calls = self.transport.calls[:]
        with self.assertRaisesRegex(ValueError, "READBACK_REQUIRED"):
            self.upload()
        self.assertEqual(self.transport.calls, calls)
        result = p.static_reconcile(self.value, self.binding_pin, "fixture-operation",
                                    self.store, self.transport)
        self.assertEqual(result["state"], "FILE_BYTES_VERIFIED")
        self.assertEqual(self.transport.calls.count("install"), 1)

    def test_concurrent_predecessor_change_preserves_other_writers_bytes(self):
        old = b"old"
        (self.web / "index.html").write_bytes(old)
        self.transport.before_install = lambda: (self.web / "index.html").write_bytes(b"other writer")
        result = self.upload(p.sha(old))
        self.assertEqual(result["state"], "HOLD_STATIC_REMOTE_BYTES_MISMATCH")
        self.assertEqual((self.web / "index.html").read_bytes(), b"other writer")

    def test_wrong_source_digest_has_no_network_or_file_effect(self):
        self.page.write_bytes(b"changed after authorization")
        with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED"):
            self.upload()
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(list(self.web.iterdir()), [])

    def test_wrong_predecessor_has_no_install(self):
        (self.web / "index.html").write_bytes(b"not absent")
        with self.assertRaisesRegex(ValueError, "PREDECESSOR_CHANGED"):
            self.upload()
        self.assertEqual(self.transport.calls, ["readback"])

    def test_index_symlink_and_hardlink_are_never_overwritten(self):
        outside = self.root / "unrelated"
        outside.write_bytes(b"preserve")
        target = self.web / "index.html"
        target.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.upload()
        target.unlink()
        os.link(outside, target)
        with self.assertRaises(ValueError):
            self.upload()
        self.assertEqual(outside.read_bytes(), b"preserve")
        self.assertNotIn("install", self.transport.calls)

    def test_webroot_symlink_is_rejected_even_for_readback(self):
        alias = self.root / "alias"
        alias.symlink_to(self.web, target_is_directory=True)
        with self.assertRaises(ValueError):
            p.static_read({"webroot": str(alias)}, self.transport)

    def test_reconcile_rejects_another_host_binding_without_network(self):
        self.upload()
        calls = self.transport.calls[:]
        with self.assertRaisesRegex(ValueError, "ORIGINAL_INTENT"):
            p.static_reconcile(self.value, "2" * 64, "fixture-operation", self.store, self.transport)
        self.assertEqual(calls, self.transport.calls)

    def test_source_limit_has_no_network(self):
        self.page.write_bytes(b"x" * (p.STATIC_MAX_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "BOUNDED_REGULAR"):
            self.upload()
        self.assertEqual(self.transport.calls, [])


class SSHBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = self.root / "protected-key-reference"
        self.key.write_text("fixture only, never a real private key")
        self.key.chmod(0o600)
        self.known = self.root / "known-hosts"
        self.known.write_text("fixture independently pinned host key")
        self.known.chmod(0o600)
        self.value = {"schema": p.STATIC_BINDING, "provider": "ionos", "product": "vps",
                      "contract_id": "fixture-contract", "server_id": "fixture-server",
                      "host": "212.227.147.105", "port": 22, "user": "root",
                      "domain": "raumzeitterminal.de", "webroot": "/var/www/fixture",
                      "identity_file": str(self.key), "known_hosts_file": str(self.known),
                      "known_hosts_sha256": p.sha(self.known.read_bytes()),
                      "authorization_reference": "isolated fixture only"}
        self.binding = self.root / "binding.json"

    def bind(self, value=None):
        self.binding.write_bytes(p.wire(value or self.value))
        self.binding.chmod(0o600)
        return p.static_binding(self.binding, p.sha(self.binding.read_bytes()))

    def test_existing_binding_is_read_without_reading_private_key_contents(self):
        self.assertEqual(self.bind()["host"], self.value["host"])

    def test_wrong_product_private_ip_missing_identity_and_wrong_domain_refuse(self):
        for field, value in (("product", "ionos-cloud-v6"), ("host", "127.0.0.1"),
                             ("server_id", ""), ("domain", "elsewhere.invalid"),
                             ("user", "-oProxyCommand=bad")):
            with self.subTest(field=field):
                changed = dict(self.value, **{field: value})
                with self.assertRaises(ValueError):
                    self.bind(changed)

    def test_key_permissions_and_host_key_drift_refuse(self):
        self.key.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "OWNER_ONLY"):
            self.bind()
        self.key.chmod(0o600)
        self.known.write_text("changed")
        with self.assertRaisesRegex(ValueError, "HOST_KEY_BINDING_CHANGED"):
            self.bind()

    def test_ssh_command_pins_key_disables_fallbacks_and_never_retries(self):
        value = self.bind()
        calls = []
        def runner(argv, **kwargs):
            calls.append(argv)
            return SimpleNamespace(returncode=255, timed_out=False, output_limit_exceeded=False,
                                   stdout="", stderr="must not be published")
        with mock.patch.object(p.shutil, "which", return_value="/usr/bin/ssh"):
            with self.assertRaisesRegex(ValueError, "OUTCOME_UNVERIFIED"):
                p.static_ssh(value, {"mode": "readback", "webroot": value["webroot"]}, runner)
        self.assertEqual(len(calls), 1)
        self.assertIn("StrictHostKeyChecking=yes", calls[0])
        self.assertIn("ConnectionAttempts=1", calls[0])
        self.assertIn("BatchMode=yes", calls[0])
        self.assertNotIn(self.key.read_text(), " ".join(calls[0]))

    def test_host_key_drift_between_calls_prevents_next_ssh(self):
        value = self.bind()
        self.known.write_text("changed since binding")
        calls = []
        with self.assertRaisesRegex(ValueError, "HOST_KEY_BINDING_CHANGED"):
            p.static_ssh(value, {}, lambda *a, **kw: calls.append(a))
        self.assertEqual(calls, [])


class PublicReadbackTests(unittest.TestCase):
    def test_a_redirected_success_response_cannot_verify_the_requested_host(self):
        body = b"<h1>Hello World</h1>"
        class Reply:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return body
            def geturl(self): return "https://old-site.invalid/"
        class Opener:
            def open(self, *args, **kwargs): return Reply()
        result = p.static_public_readback("raumzeitterminal.de", p.sha(body), Opener())
        self.assertEqual(result["state"], "HOLD_PUBLIC_STATIC_READBACK")

    def test_original_s1_cli_exposes_static_operations_before_runtime_admission(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, "-B", str(root / "tools/qikvrt_self_host.py"),
                                 "host-static-readback", "--production-binding",
                                 "/qikvrt-fixture-not-a-real-binding", "--binding-sha256", "1" * 64],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["state"], "HOLD")
        self.assertNotIn("invalid choice", result.stderr)

    def test_exact_bytes_for_apex_and_www_are_required(self):
        body = b"<h1>Hello World</h1>"
        class Reply:
            status = 200
            def __init__(self, url): self.url = url
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return body
            def geturl(self): return self.url
        class Opener:
            def open(self, request, timeout): return Reply(request.full_url)
        result = p.static_public_readback("raumzeitterminal.de", p.sha(body), Opener())
        self.assertEqual(result["state"], "PUBLIC_STATIC_BYTES_VERIFIED")
        result = p.static_public_readback("raumzeitterminal.de", p.sha(b"other"), Opener())
        self.assertEqual(result["state"], "HOLD_PUBLIC_STATIC_READBACK")

    def test_unavailable_checker_is_not_target_success(self):
        class Opener:
            def open(self, *args, **kwargs): raise OSError("fixture transport unavailable")
        result = p.static_public_readback("raumzeitterminal.de", "1" * 64, Opener())
        self.assertEqual(result["state"], "HOLD_PUBLIC_STATIC_READBACK")
        self.assertFalse(any(x["verified"] for x in result["observations"]))


if __name__ == "__main__":
    unittest.main()
