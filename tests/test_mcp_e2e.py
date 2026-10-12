#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Independent wire tests of the existing REST shim's optional MCP facade."""
from __future__ import annotations

import base64
import copy
import hashlib
import http.client
import json
import os
import subprocess
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from tests import test_tcpip_e2e as tcp_fixture

REPOSITORY_ROOT = tcp_fixture.REPOSITORY_ROOT


class McpEndToEndTests(unittest.TestCase):
    # Reuse the established process/port/state fixture, without inheriting or
    # replaying the unrelated tests. No MCP implementation imports are used.
    tearDown = tcp_fixture.TcpIpEndToEndTests.tearDown
    _wait_until_ready = tcp_fixture.TcpIpEndToEndTests._wait_until_ready
    request = tcp_fixture.TcpIpEndToEndTests.request

    def setUp(self):
        with mock.patch.dict(os.environ, {"QIKVRT_MCP_ENABLED": "1", "QIKVRT_MCP_SCOPES": "readback ingest"}):
            tcp_fixture.TcpIpEndToEndTests.setUp(self)
        self.binding_files = {
            p: hashlib.sha256((REPOSITORY_ROOT / p).read_bytes()).hexdigest()
            for p in ("scripts/qikvrt_api_client.py", "src/qikvrt_api_handler.py",
                      "src/qikvrt_effect_ack.py", "src/qikvrt_github_api_shim.py",
                      "src/qikvrt_mcp_adapter.py", "api/qikvrt_github_api.openapi.yaml")
        }
        self.binding = hashlib.sha256(json.dumps(self.binding_files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.payload = b"Authorized QIK-VRT MCP conformance bytes\n\x00\xff"
        self.arguments = {
            "repository": "owner/repo", "artifact_id": "mcp-proof", "request_id": "mcp-ingest",
            "expected_sha256": hashlib.sha256(self.payload).hexdigest(), "api_contract_version": "2.3.0",
            "expected_implementation_sha256": self.binding,
        }

    def restart(self, **overrides):
        self.server.terminate()
        self.server.communicate(timeout=5)
        env = os.environ.copy()
        env.update({"PYTHONNOUSERSITE": "1", "QIKVRT_API_HOST": "127.0.0.1", "QIKVRT_API_PORT": str(self.port),
                    "QIKVRT_API_TOKEN": self.token, "QIKVRT_API_TOKEN_EXPIRES_UTC": "2099-01-01T00:00:00Z",
                    "QIKVRT_ALLOWED_REPOSITORY": "owner/repo", "QIKVRT_API_PRINCIPAL": "e2e-responsible-operator",
                    "QIKVRT_REPO_ROOT": str(self.state), "QIKVRT_RATE_LIMIT_PER_MINUTE": "10000",
                    "QIKVRT_MCP_ENABLED": "1", "QIKVRT_MCP_SCOPES": "ingest readback"})
        env.update(overrides)
        self.server = subprocess.Popen([sys.executable, "-S", "src/qikvrt_github_api_shim.py"],
                                       cwd=REPOSITORY_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._wait_until_ready()

    def wire(self, body, *, version="2026-07-28", token=True, headers=None, raw=False):
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if version:
            h["MCP-Protocol-Version"] = version
        if isinstance(body, dict) and version == "2026-07-28":
            body = copy.deepcopy(body)
            body.setdefault("params", {}).setdefault("_meta", {
                "io.modelcontextprotocol/protocolVersion": version,
                "io.modelcontextprotocol/clientInfo": {"name": "independent-wire-test", "version": "1.0"},
                "io.modelcontextprotocol/clientCapabilities": {},
            })
            h["Mcp-Method"] = body.get("method", "")
            if body.get("method") == "tools/call":
                h["Mcp-Name"] = body["params"].get("name", "")
        if token:
            h["Authorization"] = f"Bearer {self.token}"
        h.update(headers or {})
        data = body if raw else json.dumps(body).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/mcp", data=data, headers=h, method="POST")
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            content = response.read()
            return response.code, json.loads(content) if content else None

    def call(self, name, arguments, **kwargs):
        return self.wire({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": name, "arguments": arguments}}, **kwargs)

    def write(self, **kwargs):
        args = {**self.arguments, "payload_b64": base64.b64encode(self.payload).decode(), "effect_accepted": True}
        args.update(kwargs)
        return self.call("qikvrt_ingest", args)

    def files(self):
        return {str(p.relative_to(self.state)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.state.rglob("*") if p.is_file()}

    def raw_readback(self, **kwargs):
        query = {k: v for k, v in self.arguments.items() if k not in {"repository", "artifact_id"}}
        query.update(kwargs)
        path = "/repos/owner/repo/qikvrt/artifacts/mcp-proof/readback?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", headers={"Authorization": f"Bearer {self.token}"})
        try:
            r = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            r = exc
        with r:
            return r.code, r.read()

    def test_real_mcp_write_and_separate_raw_rest_byte_readback(self):
        status, body = self.write()
        self.assertEqual(status, 200)
        result = body["result"]["structuredContent"]
        self.assertFalse(body["result"]["isError"])
        self.assertEqual(result["handler_result"]["effect_state"], "EFFECT_ACK_DONE")
        self.assertEqual(result["handler_result"]["effect_scope"], "opaque-byte-storage-only")
        self.assertEqual(result["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(result["ordinary_release"])
        self.assertFalse(result["claude_connector_execution_verified"])
        status, original_bytes = self.raw_readback()
        self.assertEqual(status, 200)
        self.assertEqual(original_bytes, self.payload)
        self.assertEqual(hashlib.sha256(original_bytes).hexdigest(), self.arguments["expected_sha256"])
        self.assertEqual(result["implementation"]["files"], self.binding_files)

    def test_mcp_readback_has_no_state_mutation(self):
        self.write()
        before = self.files()
        status, body = self.call("qikvrt_readback", self.arguments)
        self.assertEqual(status, 200)
        result = body["result"]["structuredContent"]["handler_result"]
        self.assertTrue(result["readback_verified"])
        self.assertEqual(base64.b64decode(result["payload_b64"]), self.payload)
        self.assertEqual(before, self.files())
        self.raw_readback()
        self.assertEqual(before, self.files())

    def test_missing_readback_does_not_create_store(self):
        self.call("qikvrt_readback", self.arguments)
        self.raw_readback()
        self.assertEqual(self.files(), {})
        self.assertFalse((self.state / ".qikvrt").exists())

    def test_restart_preserves_idempotent_ingest_and_independent_readback(self):
        self.write()
        target = self.state / ".qikvrt/api/inbox/mcp-proof.bin"
        before = target.stat().st_mtime_ns
        self.restart()
        status, body = self.write()
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["structuredContent"]["handler_result"]["replayed"])
        self.assertEqual(before, target.stat().st_mtime_ns)
        self.assertEqual(self.raw_readback(), (200, self.payload))

    def test_changed_replay_is_isolated_without_overwrite(self):
        self.write()
        changed = b"Different bytes"
        status, body = self.write(payload_b64=base64.b64encode(changed).decode(), expected_sha256=hashlib.sha256(changed).hexdigest())
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])
        self.assertEqual(body["result"]["structuredContent"]["handler_result"]["effect_state"], "EFFECT_ACK_ISOLATE")
        self.assertEqual(self.raw_readback(), (200, self.payload))

    def test_authentication_missing_invalid_and_expired(self):
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        self.assertEqual(self.wire(request, token=False)[0], 401)
        self.assertEqual(self.wire(request, headers={"Authorization": "Bearer invalid"})[0], 401)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=2)
        self.restart(QIKVRT_API_TOKEN_EXPIRES_UTC=expiry.isoformat())
        while datetime.now(timezone.utc) <= expiry:
            time.sleep(0.05)
        self.assertEqual(self.wire(request)[0], 401)
        self.assertEqual(self.files(), {})

    def test_concurrent_identical_writes_have_one_payload_effect(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.write(), range(8)))
        self.assertTrue(all(status == 200 and not body["result"]["isError"] for status, body in results))
        handler_results = [body["result"]["structuredContent"]["handler_result"] for _, body in results]
        self.assertEqual(sum(bool(r.get("replayed")) for r in handler_results), 7)
        self.assertEqual(len(list((self.state / ".qikvrt/api/provenance").glob("*.json"))), 1)
        self.assertEqual(self.raw_readback(), (200, self.payload))

    def test_missing_write_permission_is_denied_and_hidden(self):
        self.restart(QIKVRT_MCP_SCOPES="readback")
        status, body = self.wire({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(status, 200)
        self.assertEqual([t["name"] for t in body["result"]["tools"]], ["qikvrt_readback"])
        self.assertEqual(self.write()[0], 403)
        self.assertEqual(self.files(), {})

    def test_missing_read_permission_blocks_mcp_and_rest(self):
        self.write()
        self.restart(QIKVRT_MCP_SCOPES="ingest")
        self.assertEqual(self.call("qikvrt_readback", self.arguments)[0], 403)
        self.assertEqual(self.raw_readback()[0], 403)

    def test_owner_cannot_be_forged_by_tool_arguments(self):
        status, _ = self.write(responsibility_owner="Ingolf Lohmann")
        self.assertEqual(status, 400)
        self.assertEqual(self.files(), {})

    def test_other_principal_cannot_read_predecessor_effect(self):
        self.write()
        self.restart(QIKVRT_API_PRINCIPAL="different-authenticated-principal")
        self.assertEqual(self.raw_readback()[0], 409)

    def test_version_source_repository_hash_and_acceptance_fail_before_writes(self):
        for key, value in (("api_contract_version", "2.2.0"), ("expected_implementation_sha256", "0" * 64),
                           ("repository", "other/repo"), ("effect_accepted", False), ("effect_accepted", "true"),
                           ("expected_sha256", "0" * 64), ("artifact_id", "../escape"),
                           ("request_id", "../escape"), ("payload_b64", "invalid")):
            with self.subTest(key=key, value=value):
                self.assertEqual(self.write(**{key: value})[0], 400)
                self.assertEqual(self.files(), {})

    def test_origin_and_host_fail_without_effect(self):
        for h in ({"Origin": "https://attacker.invalid"}, {"Host": "attacker.invalid"}):
            with self.subTest(headers=h):
                self.assertEqual(self.call("qikvrt_ingest", {}, headers=h)[0], 403)
                self.assertEqual(self.files(), {})

    def test_modern_discovery_and_header_consistency(self):
        status, body = self.wire({"jsonrpc": "2.0", "id": 1, "method": "server/discover"})
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["supportedVersions"], ["2025-11-25", "2026-07-28"])
        self.assertEqual(body["result"]["_meta"]["qikvrt/implementation"]["sha256"], self.binding)
        for h in ({"Mcp-Method": "ping"}, {"MCP-Protocol-Version": "2025-11-25"}, {"Mcp-Name": "qikvrt_readback"}):
            status, _ = self.call("qikvrt_ingest", {}, headers=h)
            self.assertEqual(status, 400)
        self.assertEqual(self.files(), {})

    def test_unknown_protocol_no_automatic_version_fallback(self):
        status, body = self.wire({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, version="2099-01-01")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], -32022)
        self.assertEqual(self.files(), {})

    def test_legacy_initialization_notification_and_write(self):
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "legacy", "version": "1"}}}
        self.assertEqual(self.wire(request, version=None)[0], 200)
        notification = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        self.assertEqual(self.wire(notification, version="2025-11-25"), (202, None))
        args = {**self.arguments, "payload_b64": base64.b64encode(self.payload).decode(), "effect_accepted": True}
        self.assertEqual(self.call("qikvrt_ingest", args, version="2025-11-25")[0], 200)
        self.assertEqual(self.raw_readback(), (200, self.payload))

    def test_notifications_batches_duplicate_json_and_invalid_ids_never_write(self):
        requests = [
            {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "qikvrt_ingest", "arguments": {}}},
            {"jsonrpc": "2.0", "id": True, "method": "tools/list"},
            [{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}],
        ]
        for body in requests:
            self.assertEqual(self.wire(body)[0], 400)
        self.assertEqual(self.wire(b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}', raw=True)[0], 400)
        self.assertEqual(self.files(), {})

    def test_duplicate_security_headers_are_rejected(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.putrequest("POST", "/mcp")
            connection.putheader("Authorization", f"Bearer {self.token}")
            connection.putheader("Authorization", f"Bearer {self.token}")
            connection.putheader("Content-Length", "2")
            connection.putheader("Content-Type", "application/json")
            connection.endheaders(b"{}")
            self.assertEqual(connection.getresponse().status, 400)
        finally:
            connection.close()
        self.assertEqual(self.files(), {})

    def test_tamper_controls_bytes_sidecar_provenance_receipt_and_transaction(self):
        self.write()
        before = self.files()
        for path in ("inbox/mcp-proof.bin", "inbox/mcp-proof.bin.sha256", "provenance/mcp-proof.mcp-ingest.json",
                     "replay/mcp-ingest.json", "transactions/mcp-ingest.json"):
            with self.subTest(path=path):
                target = self.state / ".qikvrt/api" / path
                original = target.read_bytes()
                target.write_bytes(b"tampered")
                self.assertEqual(self.raw_readback()[0], 409)
                target.write_bytes(original)
        self.assertEqual(before, self.files())
        self.assertEqual(self.raw_readback(), (200, self.payload))

    def test_missing_proof_wrong_expected_hash_and_symlink_are_blocked(self):
        self.write()
        self.assertEqual(self.raw_readback(expected_sha256="0" * 64)[0], 409)
        self.assertEqual(self.raw_readback(request_id="other-request")[0], 409)
        target = self.state / ".qikvrt/api/inbox/mcp-proof.bin"
        original = target.read_bytes()
        outside = Path(self.temporary.name) / "outside.bin"
        outside.write_bytes(original)
        target.unlink()
        target.symlink_to(outside)
        self.assertEqual(self.raw_readback()[0], 409)

    def test_payload_limit_and_unknown_tools(self):
        payload = b"x" * (256 * 1024 + 1)
        self.assertEqual(self.write(payload_b64=base64.b64encode(payload).decode(), expected_sha256=hashlib.sha256(payload).hexdigest())[0], 400)
        status, body = self.call("qikvrt_ruleset_authority_dispatch", {})
        self.assertEqual(status, 200)
        self.assertEqual(body["error"]["code"], -32602)
        self.assertEqual(self.files(), {})

    def test_optional_mcp_defaults_preserve_existing_rest_surface(self):
        self.restart(QIKVRT_MCP_ENABLED="0")
        self.assertEqual(self.wire({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[0], 404)
        status, response = self.request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches", {
            "ref": "main", "inputs": {"operation": "release_status", "artifact_id": "status", "dry_run": True,
                                        "request_id": "old-rest-still-valid", "effect_accepted": False}})
        self.assertEqual(status, 202)
        self.assertEqual(response["handler_result"]["effect_state"], "EFFECT_ACK_CONTINUE")

    def test_standalone_probe_uses_one_write_and_independent_readback_in_both_eras(self):
        payload_file = Path(self.temporary.name) / "probe-input.bin"
        payload_file.write_bytes(self.payload)
        for version in ("2025-11-25", "2026-07-28"):
            command = [sys.executable, "-B", "scripts/qikvrt_mcp_probe.py",
                       "--base-url", f"http://127.0.0.1:{self.port}", "--repository", "owner/repo",
                       "--artifact-id", "mcp-proof", "--request-id", "probe-" + version,
                       "--expected-sha256", self.arguments["expected_sha256"],
                       "--expected-implementation-sha256", self.binding, "--protocol-version", version]
            env = {**os.environ, "QIKVRT_API_TOKEN": self.token}
            completed = subprocess.run(command + ["--payload-file", str(payload_file), "--accept-effect"],
                                       cwd=REPOSITORY_ROOT, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(completed.returncode, 0, completed.stdout)
            result = json.loads(completed.stdout)
            self.assertEqual(result["ingest_call_count"], 1)
            self.assertTrue(result["independent_byte_readback"])
            self.assertFalse(result["claude_connector_execution_verified"])
            self.assertNotIn(self.token, completed.stdout + completed.stderr)
            read_only = subprocess.run(command, cwd=REPOSITORY_ROOT, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(read_only.returncode, 0, read_only.stdout)
            self.assertEqual(json.loads(read_only.stdout)["ingest_call_count"], 0)

    def test_probe_unauthorized_response_has_no_retry_or_credential_output(self):
        command = [sys.executable, "-B", "scripts/qikvrt_mcp_probe.py",
                   "--base-url", f"http://127.0.0.1:{self.port}", "--repository", "owner/repo",
                   "--artifact-id", "mcp-proof", "--request-id", "probe-denied",
                   "--expected-sha256", self.arguments["expected_sha256"], "--expected-implementation-sha256", self.binding]
        env = {**os.environ, "QIKVRT_API_TOKEN": "invalid-private-credential"}
        completed = subprocess.run(command, cwd=REPOSITORY_ROOT, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 1)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["ingest_call_count"], 0)
        self.assertEqual(len(result["requests"]), 1)
        self.assertEqual(result["requests"][0]["status"], 401)
        self.assertNotIn(env["QIKVRT_API_TOKEN"], completed.stdout + completed.stderr)
        self.assertEqual(self.files(), {})


if __name__ == "__main__":
    unittest.main()
