#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Independent MCP + raw REST byte probe; no server/handler imports or retries."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(args, *, token: str) -> dict:
    """Execute at most one accepted ingest and fresh, independent readbacks."""
    base = args.base_url.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.path
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}):
        raise ValueError("base URL must be credential-free HTTPS, or loopback HTTP")
    if not token or len(token) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ValueError("ephemeral bounded API token is required")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", args.repository):
        raise ValueError("exact repository scope required")
    for value in (args.request_id, args.artifact_id):
        if not re.fullmatch(r"[A-Za-z0-9_.=-]{1,128}", value):
            raise ValueError("safe artifact and request IDs required")
    for value in (args.expected_sha256, args.expected_implementation_sha256):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("independently expected SHA-256 bindings required")
    if args.protocol_version not in {"2025-11-25", "2026-07-28"}:
        raise ValueError("unsupported protocol version")
    if args.payload_file and not args.accept_effect:
        raise ValueError("--accept-effect required for one opaque-byte ingest")
    if args.accept_effect and not args.payload_file:
        raise ValueError("effect acceptance requires an explicit payload")
    arguments = {"repository": args.repository, "artifact_id": args.artifact_id,
                 "request_id": args.request_id, "expected_sha256": args.expected_sha256,
                 "api_contract_version": "2.3.0", "expected_implementation_sha256": args.expected_implementation_sha256}
    opener = urllib.request.build_opener(NoRedirect())
    observations = []
    def request(method, path, body=None, *, protocol=True):
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"}
        if body is not None:
            headers["Content-Type"] = "application/json"
            if protocol:
                headers["MCP-Protocol-Version"] = args.protocol_version
                if args.protocol_version == "2026-07-28":
                    headers["Mcp-Method"] = body["method"]
                    body.setdefault("params", {})["_meta"] = {
                        "io.modelcontextprotocol/protocolVersion": args.protocol_version,
                        "io.modelcontextprotocol/clientInfo": {"name": "qikvrt-independent-byte-probe", "version": "1.0.0"},
                        "io.modelcontextprotocol/clientCapabilities": {},
                    }
                    if body["method"] == "tools/call":
                        headers["Mcp-Name"] = body["params"]["name"]
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        try:
            response = opener.open(req, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("response limit exceeded")
            observations.append({"method": method, "path": path.split("?", 1)[0], "status": response.code,
                                 "observed_at": datetime.now(timezone.utc).isoformat(),
                                 "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
            if response.code != 200:
                raise ValueError(f"HTTP {response.code}; no retry; provider body omitted")
            return raw
    def rpc(method, params, identifier):
        raw = request("POST", "/mcp", {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
        body = json.loads(raw)
        if body.get("jsonrpc") != "2.0" or body.get("id") != identifier or "error" in body:
            raise ValueError("MCP request rejected; no retry")
        return body["result"]
    result = {"schema": "qikvrt_mcp_independent_probe_v1", "endpoint": base + "/mcp", "repository": args.repository,
              "artifact_id": args.artifact_id, "request_id": args.request_id,
              "implementation_sha256": args.expected_implementation_sha256, "protocol_version": args.protocol_version,
              "requests": observations, "ingest_call_count": 0, "independent_byte_readback": False,
              "claude_connector_execution_verified": False, "effect_state": "EFFECT_ACK_CONTINUE", "ordinary_release": False}
    try:
        if args.protocol_version == "2025-11-25":
            rpc("initialize", {"protocolVersion": args.protocol_version, "capabilities": {},
                               "clientInfo": {"name": "independent-byte-probe", "version": "1.0.0"}}, 1)
        else:
            rpc("server/discover", {}, 1)
        catalog = rpc("tools/list", {}, 2)
        if not {"qikvrt_readback"} <= {tool["name"] for tool in catalog["tools"]}:
            raise ValueError("readback permission missing")
        if args.payload_file:
            path = Path(args.payload_file)
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise ValueError("payload must be a regular file")
                payload = os.read(descriptor, 256 * 1024 + 1)
            finally:
                os.close(descriptor)
            if len(payload) > 256 * 1024 or hashlib.sha256(payload).hexdigest() != args.expected_sha256:
                raise ValueError("expected payload bytes differ")
            if "qikvrt_ingest" not in {tool["name"] for tool in catalog["tools"]}:
                raise ValueError("ingest permission missing")
            result["ingest_call_count"] = 1
            response = rpc("tools/call", {"name": "qikvrt_ingest", "arguments": {
                **arguments, "payload_b64": base64.b64encode(payload).decode(), "effect_accepted": True}}, 3)
            scoped = response["structuredContent"]
            if response.get("isError") or scoped["handler_result"].get("effect_state") != "EFFECT_ACK_DONE":
                raise ValueError("ingest effect not established")
            result["ingest_receipt_sha256"] = hashlib.sha256(json.dumps(scoped, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        response = rpc("tools/call", {"name": "qikvrt_readback", "arguments": arguments}, 4)
        scoped = response["structuredContent"]
        readback = scoped["handler_result"]
        encoded_bytes = base64.b64decode(readback["payload_b64"], validate=True)
        query = urllib.parse.urlencode({key: value for key, value in arguments.items() if key not in {"repository", "artifact_id"}})
        raw_bytes = request("GET", f"/repos/{args.repository}/qikvrt/artifacts/{args.artifact_id}/readback?{query}", protocol=False)
        if (response.get("isError") or scoped.get("api_contract_version") != "2.3.0"
                or scoped.get("implementation", {}).get("sha256") != args.expected_implementation_sha256
                or readback.get("repository") != args.repository or readback.get("artifact_id") != args.artifact_id
                or readback.get("request_id") != args.request_id or readback.get("readback_verified") is not True
                or encoded_bytes != raw_bytes or hashlib.sha256(raw_bytes).hexdigest() != args.expected_sha256):
            raise ValueError("independent result binding failed")
        result.update({"status": "PASS_SCOPED_BYTE_CONFORMANCE", "independent_byte_readback": True,
                       "payload_sha256": hashlib.sha256(raw_bytes).hexdigest(), "payload_bytes": len(raw_bytes),
                       "provenance": readback["provenance"]})
    except Exception as exc:
        result["status"] = "BLOCK"
        result["error_class"] = type(exc).__name__
        result["retry_policy"] = "NO_RETRY; read authoritative evidence before any new ingest"
        # Do not echo credentials, payloads, provider bodies or exception text.
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--repository", required=True)
    ap.add_argument("--artifact-id", required=True)
    ap.add_argument("--request-id", required=True)
    ap.add_argument("--expected-sha256", required=True)
    ap.add_argument("--expected-implementation-sha256", required=True)
    ap.add_argument("--protocol-version", choices=["2025-11-25", "2026-07-28"], default="2026-07-28")
    ap.add_argument("--payload-file")
    ap.add_argument("--accept-effect", action="store_true")
    args = ap.parse_args()
    try:
        result = probe(args, token=os.environ.get("QIKVRT_API_TOKEN", ""))
    except Exception as exc:
        result = {"status": "BLOCK", "error_class": type(exc).__name__, "ingest_call_count": 0,
                  "claude_connector_execution_verified": False, "ordinary_release": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS_SCOPED_BYTE_CONFORMANCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
