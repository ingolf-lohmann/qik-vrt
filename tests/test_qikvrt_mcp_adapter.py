#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""HTTP conformance and security regressions; GitHub is an explicit fixture.

The wire client does not call the MCP implementation directly. Tests do not
authenticate a Claude account, deploy a service, or assert an external effect.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import qikvrt_mcp_adapter as mcp
import qikvrt_github_api_shim as shim
from qikvrt_api_handler import HandlerConfig, run_handler, validate_audit_chain
from qikvrt_effect_ack import ResponsibilityProtocol
from qikvrt_api_client import github_json_get

HEAD, TREE = "a" * 40, "b" * 40
REPO = "tests/qik-vrt"
PRINCIPAL = "test-owner"


def secret(value: bytes) -> str:
    return "b64url:" + base64.urlsafe_b64encode(value).decode().rstrip("=")


class McpHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qikvrt-mcp-")
        self.root = Path(self.temp.name)
        self.token = secret(b"m" * 32)
        self.env = patch.dict(os.environ, {
            "QIKVRT_MCP_ENABLED": "1", "QIKVRT_MCP_TOKEN": self.token,
            "QIKVRT_MCP_TOKEN_EXPIRES_UTC": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "QIKVRT_MCP_PRINCIPAL": PRINCIPAL,
            "QIKVRT_MCP_SCOPES": "repository:read capability:read effect_ack:read",
            "QIKVRT_ALLOWED_REPOSITORY": REPO, "QIKVRT_REPO_ROOT": str(self.root),
            "QIKVRT_MCP_REF": "main", "QIKVRT_MCP_ALLOWED_ORIGINS": "https://claude.ai",
            "QIKVRT_MCP_GITHUB_READ_TOKEN": "", "QIKVRT_REMOTE_ATTESTATION_SECRET": "",
            "QIKVRT_API_TOKEN": secret(b"w" * 32), "QIKVRT_API_PRINCIPAL": PRINCIPAL,
            "QIKVRT_API_TOKEN_EXPIRES_UTC": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "QIKVRT_RATE_LIMIT_PER_MINUTE": "10000", "QIKVRT_API_LOG": "0",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)
        self.paths = []
        self.documents = {}
        entries = []
        for path in mcp.SOURCE_PATHS:
            raw = (ROOT / path).read_bytes()
            sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            entries.append({"path": path, "type": "blob", "mode": "100644", "sha": sha})
            self.documents["git/blobs/" + sha] = {"sha": sha, "size": len(raw), "encoding": "base64", "content": base64.b64encode(raw).decode()}
        self.documents["git/trees/" + TREE + "?recursive=1"] = {"sha": TREE, "truncated": False, "tree": entries}
        self.documents["commits/main"] = {"sha": HEAD, "commit": {"tree": {"sha": TREE}}}
        self.get_patch = patch.object(mcp, "_get", side_effect=self.get_fixture)
        self.get_patch.start()
        self.addCleanup(self.get_patch.stop)
        with shim._RATE_LOCK:
            shim._RATE_WINDOWS.clear()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), shim.QikvrtGitHubApiShim)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.counter = 0

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def get_fixture(self, config, path):
        self.assertEqual(config["repository"], REPO)
        self.paths.append(path)
        document = self.documents[path]
        raw = json.dumps(document, sort_keys=True).encode()
        return {"document": document, "url": f"https://api.github.com/repos/{REPO}/{path}", "response_sha256": hashlib.sha256(raw).hexdigest()}

    def wire(self, body=None, *, token=True, headers=None, method="POST", path="/mcp", raw=None):
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25"}
        if token:
            h["Authorization"] = "Bearer " + self.token
        h.update(headers or {})
        data = raw if raw is not None else None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{self.server.server_port}{path}", data=data, headers=h, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read()
            return response.status, json.loads(content) if content else None, dict(response.headers)

    def rpc(self, method, params=None, **kwargs):
        self.counter += 1
        return self.wire({"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params or {}}, **kwargs)

    def call(self, name="qikvrt_repository_state", args=None, **kwargs):
        return self.rpc("tools/call", {"name": name, "arguments": args or {"request_id": "read-1", "expected_head": HEAD}}, **kwargs)

    def data(self, response):
        code, body, _ = response
        self.assertEqual(code, 200)
        result = body["result"]
        self.assertEqual(json.loads(result["content"][0]["text"]), result["structuredContent"])
        data = result["structuredContent"]
        protocol = ResponsibilityProtocol.from_dict(data["effect_ack"]["responsibility_protocol"])
        self.assertFalse(protocol.ordinary_release)
        self.assertFalse(data["ordinary_release"])
        self.assertFalse(data["external_effect_verified"])
        return data

    def test_initialize_discovery_notification_and_ping(self):
        response = self.rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "independent-wire-test", "version": "1"}})
        self.assertEqual(response[1]["result"]["protocolVersion"], "2025-11-25")
        self.assertNotIn("MCP-Session-Id", response[2])
        self.assertEqual(len(self.rpc("tools/list")[1]["result"]["tools"]), 3)
        self.assertEqual(self.wire({"jsonrpc": "2.0", "method": "notifications/initialized"})[:2], (202, None))
        self.assertEqual(self.rpc("ping")[1]["result"], {})
        self.assertEqual(self.paths, [])

    def test_successful_read_has_fresh_closing_head_and_valid_protocol(self):
        data = self.data(self.call())
        self.assertEqual(data["repository_state"]["head"], HEAD)
        self.assertEqual(data["closing_readback"]["tree"], TREE)
        self.assertEqual(data["effect_ack"]["state"], "EFFECT_ACK_CONTINUE")
        self.assertEqual(self.paths, ["commits/main", "commits/main"])
        self.assertEqual(validate_audit_chain(self.root / ".qikvrt/api/audit/events.jsonl")["sequence"], 1)

    def test_unpinned_initial_repository_discovery(self):
        data = self.data(self.call(args={"request_id": "initial-read"}))
        self.assertEqual(data["repository_state"]["head"], HEAD)

    def test_capabilities_verify_exact_blobs_and_documented_openapi(self):
        data = self.data(self.call("qikvrt_capabilities"))
        self.assertFalse(data["writes_exposed"])
        self.assertEqual(len(data["sources"]), len(mcp.SOURCE_PATHS))
        source = data["sources"][0]
        self.assertEqual(source["sha256"], hashlib.sha256((ROOT / mcp.SOURCE_PATHS[0]).read_bytes()).hexdigest())
        self.assertIn("workflowDispatch", source["documented_operation_ids"])
        self.assertIn(HEAD, source["commit_url"])
        seal = data['owner_seal_acceptance']
        self.assertEqual(seal['receipt']['accepted_by'], 'Ingolf Lohmann')
        self.assertFalse(seal['observed_subject_accepted'])
        self.assertFalse(seal['receipt']['claims']['successor_acceptance'])

    def test_owner_seal_capability_reads_are_independent_of_local_receipts(self):
        local = self.root / mcp.SEAL_PATH
        local.parent.mkdir(parents=True)
        local.write_text('{"status":"ACCEPTED","claims":{"effect_ack_done":true}}')
        data = self.data(self.call('qikvrt_capabilities'))
        self.assertFalse(data['owner_seal_acceptance']['receipt']['claims']['effect_ack_done'])
        self.assertEqual(self.paths[-1], 'commits/main')
        self.assertFalse(data['writes_exposed'])

    def test_changed_receipt_with_valid_git_blob_still_requires_receipt_digest(self):
        tree = self.documents['git/trees/' + TREE + '?recursive=1']
        entry = next(item for item in tree['tree'] if item['path'] == mcp.SEAL_PATH)
        raw = b'{"status":"ACCEPTED"}'
        sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        entry['sha'] = sha
        self.documents['git/blobs/' + sha] = {'sha': sha, 'size': len(raw), 'encoding': 'base64', 'content': base64.b64encode(raw).decode()}
        data = self.data(self.call('qikvrt_capabilities'))
        self.assertEqual(data['error'], 'OWNER_SEAL_READBACK_INVALID')
        self.assertEqual(data['effect_ack']['state'], 'EFFECT_ACK_ISOLATE')

    def test_seal_read_does_not_accept_a_mid_read_head_change(self):
        def changed(config, path):
            result = self.get_fixture(config, path)
            if path == 'commits/main' and self.paths.count(path) == 2:
                result = dict(result, document={'sha': 'c' * 40, 'commit': {'tree': {'sha': TREE}}})
            return result
        self.get_patch.stop()
        with patch.object(mcp, '_get', side_effect=changed):
            data = self.data(self.call('qikvrt_capabilities'))
        self.assertEqual(data['error'], 'REPOSITORY_CHANGED_DURING_READ')
        self.assertNotIn('owner_seal_acceptance', data)

    def test_anonymous_and_wrong_token_denied_before_any_read(self):
        self.assertEqual(self.call(token=False)[0], 401)
        self.assertEqual(self.call(headers={"Authorization": "Bearer wrong"})[0], 401)
        self.assertEqual(self.paths, [])

    def test_expired_and_shared_write_credentials_refused(self):
        os.environ["QIKVRT_MCP_TOKEN_EXPIRES_UTC"] = "2000-01-01T00:00:00Z"
        self.assertEqual(self.call()[0], 401)
        os.environ["QIKVRT_MCP_TOKEN_EXPIRES_UTC"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        os.environ["QIKVRT_API_TOKEN"] = self.token
        self.assertEqual(self.call()[0], 401)
        self.assertEqual(self.paths, [])

    def test_scope_filters_discovery_and_refuses_outside_scope(self):
        os.environ["QIKVRT_MCP_SCOPES"] = "repository:read"
        self.assertEqual(len(self.rpc("tools/list")[1]["result"]["tools"]), 1)
        data = self.data(self.call("qikvrt_capabilities"))
        self.assertEqual(data["effect_ack"]["state"], "EFFECT_ACK_BLOCK")
        self.assertEqual(self.paths, [])

    def test_origins_fail_closed_and_get_delete_offer_no_stream(self):
        self.assertEqual(self.call(headers={"Origin": "https://evil.invalid"})[0], 403)
        self.assertEqual(self.rpc("ping", headers={"Origin": "https://claude.ai"})[0], 200)
        for method in ("GET", "DELETE"):
            self.assertEqual(self.wire(method=method)[0], 405)

    def test_stale_head_never_releases(self):
        data = self.data(self.call(args={"request_id": "stale", "expected_head": "c" * 40}))
        self.assertEqual(data["error"], "STALE_REPOSITORY_HEAD")
        self.assertTrue(self.call(args={"request_id": "stale", "expected_head": "c" * 40})[1]["result"]["isError"])
        self.assertNotIn("repository_state", data)

    def test_mid_read_head_drift_is_refused(self):
        self.get_patch.stop()
        count = 0
        def changing(config, path):
            nonlocal count
            count += 1
            result = self.get_fixture(config, path)
            if count == 2:
                result = dict(result, document={"sha": "c" * 40, "commit": {"tree": {"sha": TREE}}})
            return result
        with patch.object(mcp, "_get", side_effect=changing):
            data = self.data(self.call())
        self.assertEqual(data["error"], "REPOSITORY_CHANGED_DURING_READ")

    def test_replay_is_durable_and_always_reobserves(self):
        self.data(self.call())
        self.assertTrue(self.data(self.call())["replayed"])
        self.assertEqual(len(self.paths), 4)
        # A successor process sees the same immutable binding in shared storage.
        config = mcp.configuration()
        conflict = mcp.call_tool(config, "qikvrt_repository_state", {"request_id": "read-1", "expected_head": "c" * 40})
        self.assertEqual(conflict["structuredContent"]["error"], "REQUEST_ID_REPLAY_CONFLICT")
        self.assertEqual(conflict["structuredContent"]["effect_ack"]["state"], "EFFECT_ACK_ISOLATE")
        self.assertEqual(len(self.paths), 4)

    def test_missing_effect_grant_and_write_tool_are_blocked(self):
        response = self.call("ingest", {"effect_accepted": True})
        self.assertEqual(self.data(response)["effect_ack"]["state"], "EFFECT_ACK_BLOCK")
        path = f"/repos/{REPO}/dispatches"
        self.assertEqual(self.wire({"event_type": "qikvrt_mesh_api", "client_payload": {}}, path=path)[0], 401)
        args = {"request_id": "receipt-read", "expected_head": HEAD, "target_request_id": "absent", "expected_sha256": "0" * 64}
        self.assertEqual(self.data(self.call("qikvrt_effect_ack_result", args))["error"], "EFFECT_AUTHORIZATION_OR_RECEIPT_ABSENT")
        self.assertFalse((self.root / ".qikvrt/api/inbox/anything.bin").exists())

    def make_receipt(self):
        raw = b"bounded local test payload"
        cfg = HandlerConfig(root=self.root, operation="ingest", artifact_id="receipt-test", payload_b64=base64.b64encode(raw).decode(),
                            expected_sha256=hashlib.sha256(raw).hexdigest(), dry_run=False, repository=REPO,
                            request_id="existing-effect", effect_accepted=True, responsibility_owner=PRINCIPAL, origin_authenticated=True)
        self.assertEqual(run_handler(cfg)["effect_state"], "EFFECT_ACK_DONE")
        path = self.root / ".qikvrt/api/replay/existing-effect.json"
        return {"request_id": "receipt-read", "expected_head": HEAD, "target_request_id": "existing-effect", "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, path

    def test_existing_effect_receipt_is_typed_and_independently_byte_bound(self):
        args, path = self.make_receipt()
        data = self.data(self.call("qikvrt_effect_ack_result", args))
        receipt = data["effect_receipt"]
        self.assertEqual(base64.b64decode(receipt["record_b64"], validate=True), path.read_bytes())
        self.assertIsNone(receipt["producer_head"])
        self.assertEqual(receipt["reported_result"]["effect_state"], "EFFECT_ACK_DONE")
        self.assertEqual(data["effect_ack"]["state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["external_effect_verified"])

    def test_receipt_tamper_and_foreign_principal_refused(self):
        args, path = self.make_receipt()
        args["expected_sha256"] = "0" * 64
        self.assertEqual(self.data(self.call("qikvrt_effect_ack_result", args))["error"], "RECEIPT_BYTES_MISMATCH")
        args["request_id"] = "foreign-read"
        args["expected_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        os.environ["QIKVRT_MCP_PRINCIPAL"] = "other-owner"
        self.assertEqual(self.data(self.call("qikvrt_effect_ack_result", args))["error"], "EFFECT_RECEIPT_OUTSIDE_PRINCIPAL_OR_REPOSITORY")

    def test_truncated_tree_and_bad_blob_refused(self):
        self.documents["git/trees/" + TREE + "?recursive=1"]["truncated"] = True
        self.assertEqual(self.data(self.call("qikvrt_capabilities"))["error"], "INCOMPLETE_SOURCE_TREE")
        self.documents["git/trees/" + TREE + "?recursive=1"]["truncated"] = False
        blob = next(key for key in self.documents if key.startswith("git/blobs/"))
        self.documents[blob]["content"] = base64.b64encode(b"tampered").decode()
        self.assertEqual(self.data(self.call("qikvrt_capabilities", {"request_id": "bad-blob", "expected_head": HEAD}))["error"], "SOURCE_BYTES_MISMATCH")

    def test_upstream_failure_is_safe_and_uncached(self):
        self.get_patch.stop()
        with patch.object(mcp, "_get", side_effect=RuntimeError("SECRET-UPSTREAM-DETAIL")):
            response = self.call()
        self.assertNotIn("SECRET-UPSTREAM-DETAIL", json.dumps(response))
        self.assertEqual(self.data(response)["error"], "READBACK_FAILED_NO_EFFECT")
        self.assertFalse(response[1]["result"]["structuredContent"]["ordinary_release"])

    def test_bad_json_unknown_fields_and_malformed_ids(self):
        self.assertEqual(self.wire(raw=b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}')[0], 400)
        self.assertEqual(self.wire(raw=b'{"jsonrpc":"2.0","id":NaN,"method":"ping"}')[0], 400)
        self.assertEqual(self.wire(raw=b'[]')[0], 400)
        self.assertEqual(self.wire({"jsonrpc": "2.0", "id": True, "method": "ping"})[0], 400)
        response = self.call(args={"request_id": "read", "expected_head": HEAD, "repository": "other/repo"})
        self.assertEqual(response[1]["error"]["code"], -32602)
        self.assertEqual(self.paths, [])

    def test_legacy_versions_and_unsupported_version(self):
        for version in mcp.VERSIONS[1:]:
            self.assertEqual(self.rpc("ping", headers={"MCP-Protocol-Version": version})[0], 200)
        self.assertEqual(self.rpc("ping", headers={"MCP-Protocol-Version": "2099-01-01"})[0], 400)

    def modern(self, method, params=None, headers=None):
        params = dict(params or {})
        params["_meta"] = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                           "io.modelcontextprotocol/clientInfo": {"name": "wire-test", "version": "1"},
                           "io.modelcontextprotocol/clientCapabilities": {}}
        h = {"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": method}
        if "name" in params:
            h["Mcp-Name"] = params["name"]
        h.update(headers or {})
        return self.rpc(method, params, headers=h)

    def test_modern_discovery_and_read_without_initialize(self):
        response = self.modern("server/discover")
        self.assertEqual(response[0], 200)
        self.assertIn("2026-07-28", response[1]["result"]["supportedVersions"])
        self.assertEqual(response[1]["result"]["resultType"], "complete")
        self.assertEqual(len(self.modern("tools/list")[1]["result"]["tools"]), 3)
        response = self.modern("tools/call", {"name": "qikvrt_repository_state", "arguments": {"request_id": "modern-read", "expected_head": HEAD}})
        self.assertEqual(self.data(response)["closing_readback"]["head"], HEAD)
        self.assertEqual(response[1]["result"]["resultType"], "complete")

    def test_modern_header_mismatch_and_metadata_refused(self):
        response = self.modern("tools/list", headers={"Mcp-Method": "tools/call"})
        self.assertEqual(response[1]["error"]["code"], -32020)
        response = self.modern("tools/list", headers={"MCP-Protocol-Version": "2025-11-25"})
        self.assertEqual(response[1]["error"]["code"], -32020)
        self.assertEqual(self.rpc("tools/list", headers={"MCP-Protocol-Version": "2026-07-28"})[0], 400)
        response = self.modern("tools/call", {"name": "qikvrt_repository_state", "arguments": {"request_id": "modern-read"}}, headers={"Mcp-Name": "ingest"})
        self.assertEqual(response[1]["error"]["code"], -32020)
        self.assertEqual(self.paths, [])

    def test_modern_encoded_name_and_unknown_method(self):
        encoded = "=?base64?" + base64.b64encode(b"qikvrt_repository_state").decode() + "?="
        response = self.modern("tools/call", {"name": "qikvrt_repository_state", "arguments": {"request_id": "encoded-name"}}, headers={"Mcp-Name": encoded})
        self.assertEqual(response[0], 200)
        self.assertFalse(response[1]["result"]["isError"])
        self.assertEqual(self.modern("write/effect")[0], 404)

    def test_disabled_route_accept_and_query_restrictions(self):
        self.assertEqual(self.rpc("ping", headers={"Accept": "application/json"})[0], 406)
        self.assertEqual(self.rpc("ping", path="/mcp?token=anything")[0], 401)
        os.environ["QIKVRT_MCP_ENABLED"] = "0"
        self.assertEqual(self.rpc("ping")[0], 404)
        self.assertEqual(self.paths, [])


class GitHubReadTransportTests(unittest.TestCase):
    def test_get_only_scope_and_exact_response_bytes(self):
        raw = b'{"sha": "exact bytes"}\n'
        class Response(io.BytesIO):
            status = 200
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response(raw)
        opener = Opener()
        result = github_json_get(REPO, "commits/main", opener=opener)
        self.assertEqual(opener.request.get_method(), "GET")
        self.assertEqual(opener.request.full_url, f"https://api.github.com/repos/{REPO}/commits/main")
        self.assertIsNone(opener.request.get_header("Authorization"))
        self.assertEqual(result["response_sha256"], hashlib.sha256(raw).hexdigest())
        for repository, path in ((REPO, "https://evil.invalid"), ("../repo", "commits/main"), (REPO, "commits/../secrets"), (REPO, "dispatches")):
            with self.assertRaises(ValueError):
                github_json_get(repository, path, opener=opener)

    def test_duplicate_nonfinite_and_oversize_readback_refused(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b"x" * (2 * 1024 * 1024 + 1)):
            class Response(io.BytesIO):
                status = 200
            class Opener:
                def open(self, request, timeout):
                    return Response(raw)
            with self.assertRaises(ValueError):
                github_json_get(REPO, "commits/main", opener=Opener())


if __name__ == "__main__":
    unittest.main()
