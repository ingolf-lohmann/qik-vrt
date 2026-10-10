#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only MCP facade for the existing REST shim and EFFECT_ACK records.

No server, state machine, writer, Git credential store or effect grant is
created here. Protective replay/audit persistence reuses the API handler.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from qikvrt_api_handler import (
    IntegrityIsolationError, _HANDLER_LOCK, _strict_json_loads, append_audit,
    atomic_write_bytes, decode_secret_material, dirs, process_lock, safe_id,
    secure_read_bytes, utc_now,
)
from qikvrt_effect_ack import (
    ConnectionDecision, EffectAckEngine, EffectAckRequest, ResponsibilityProtocol,
    RiskLevel, canonical_json,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qikvrt_api_client import github_json_get

VERSIONS = ("2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26")
INFO = {"name": "qikvrt-rest-readback", "version": "1.0.0"}
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SOURCE_PATHS = ("api/qikvrt_github_api.openapi.yaml", "src/qikvrt_api_handler.py", "src/qikvrt_effect_ack.py")
SCOPES = {
    "qikvrt_repository_state": "repository:read",
    "qikvrt_capabilities": "capability:read",
    "qikvrt_effect_ack_result": "effect_ack:read",
}


def enabled() -> bool:
    return os.environ.get("QIKVRT_MCP_ENABLED") == "1"


def configuration() -> dict:
    token = os.environ.get("QIKVRT_MCP_TOKEN", "")
    material = decode_secret_material(token, field="QIKVRT_MCP_TOKEN")
    for name in ("QIKVRT_API_TOKEN", "QIKVRT_REMOTE_ATTESTATION_SECRET", "QIKVRT_MCP_GITHUB_READ_TOKEN"):
        other = os.environ.get(name, "")
        if other and hmac.compare_digest(token.encode(), other.encode()):
            raise ValueError("MCP requires a separate read credential")
        if other.startswith("b64url:") and hmac.compare_digest(material, decode_secret_material(other, field=name)):
            raise ValueError("MCP requires separate key material")
    expiry = datetime.fromisoformat(os.environ.get("QIKVRT_MCP_TOKEN_EXPIRES_UTC", "").replace("Z", "+00:00"))
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("MCP credential is expired or has no timezone")
    repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", repository) or any(part in (".", "..") for part in repository.split("/")):
        raise ValueError("MCP requires an exact repository scope")
    principal = os.environ.get("QIKVRT_MCP_PRINCIPAL", "").strip()
    if not principal or len(principal) > 256:
        raise ValueError("MCP requires a configured principal")
    scopes = set(os.environ.get("QIKVRT_MCP_SCOPES", "").split())
    if not scopes or not scopes <= set(SCOPES.values()):
        raise ValueError("MCP scopes must be explicit read scopes")
    ref = os.environ.get("QIKVRT_MCP_REF", "main")
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}", ref) or ".." in ref:
        raise ValueError("MCP ref must be one bounded configured ref")
    return {"repository": repository, "principal": principal, "scopes": scopes, "ref": ref, "token": token}


def authorized(headers) -> bool:
    try:
        config = configuration()
        values = headers.get_all("Authorization", [])
        return len(values) == 1 and hmac.compare_digest(values[0].encode(), ("Bearer " + config["token"]).encode())
    except (ValueError, TypeError, UnicodeError):
        return False


def origin_allowed(headers) -> bool:
    origins = headers.get_all("Origin", [])
    return not origins or (len(origins) == 1 and origins[0] in os.environ.get("QIKVRT_MCP_ALLOWED_ORIGINS", "").split())


def tools(config: dict) -> list[dict]:
    result = []
    for name, scope in SCOPES.items():
        if scope not in config["scopes"]:
            continue
        properties = {
            "request_id": {"type": "string", "pattern": "^[A-Za-z0-9_.=-]{1,128}$"},
            "expected_head": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
        }
        required = ["request_id"]
        if name != "qikvrt_repository_state":
            required.append("expected_head")
        if name == "qikvrt_effect_ack_result":
            properties.update({
                "target_request_id": {"type": "string", "pattern": "^[A-Za-z0-9_.=-]{1,128}$"},
                "expected_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            })
            required.extend(("target_request_id", "expected_sha256"))
        result.append({
            "name": name, "description": "Read bound QIK-VRT evidence; no effect authorization or execution.",
            "inputSchema": {"type": "object", "properties": properties, "required": required, "additionalProperties": False},
            "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
        })
    return result


class ReadFailure(ValueError):
    def __init__(self, code: str, *, isolate: bool = False):
        super().__init__(code)
        self.code, self.isolate = code, isolate


def _get(config: dict, path: str) -> dict:
    return github_json_get(config["repository"], path, token=os.environ.get("QIKVRT_MCP_GITHUB_READ_TOKEN", ""))


def _head(config: dict) -> dict:
    source = _get(config, "commits/" + config["ref"])
    doc = source["document"]
    head, tree = doc.get("sha"), doc.get("commit", {}).get("tree", {}).get("sha")
    if not isinstance(head, str) or not SHA1.fullmatch(head) or not isinstance(tree, str) or not SHA1.fullmatch(tree):
        raise ReadFailure("INVALID_REPOSITORY_BINDING", isolate=True)
    return {"repository": config["repository"], "ref": config["ref"], "head": head, "tree": tree,
            "source_url": source["url"], "response_sha256": source["response_sha256"], "observed_at": utc_now()}


def _sources(config: dict, state: dict) -> list[dict]:
    tree = _get(config, "git/trees/" + state["tree"] + "?recursive=1")["document"]
    if tree.get("sha") != state["tree"] or tree.get("truncated") is not False or not isinstance(tree.get("tree"), list):
        raise ReadFailure("INCOMPLETE_SOURCE_TREE", isolate=True)
    entries = {item["path"]: item for item in tree["tree"]}
    result = []
    for path in SOURCE_PATHS:
        entry = entries.get(path, {})
        blob_sha = entry.get("sha", "")
        if entry.get("type") != "blob" or entry.get("mode") not in ("100644", "100755") or not SHA1.fullmatch(blob_sha):
            raise ReadFailure("SOURCE_NOT_BOUND", isolate=True)
        source = _get(config, "git/blobs/" + blob_sha)
        blob = source["document"]
        if blob.get("sha") != blob_sha or blob.get("encoding") != "base64":
            raise ReadFailure("INVALID_SOURCE_BLOB", isolate=True)
        raw = base64.b64decode("".join(blob.get("content", "").split()), validate=True)
        if len(raw) > 1024 * 1024 or blob.get("size") != len(raw) or hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != blob_sha:
            raise ReadFailure("SOURCE_BYTES_MISMATCH", isolate=True)
        item = {"path": path, "git_blob_sha1": blob_sha, "sha256": hashlib.sha256(raw).hexdigest(),
                "source_url": source["url"], "commit_url": f"https://github.com/{config['repository']}/blob/{state['head']}/{path}"}
        if path.endswith(".yaml"):
            item["documented_operation_ids"] = re.findall(r"^\s+operationId:\s*([A-Za-z0-9_]+)\s*$", raw.decode("utf-8"), re.M)
        result.append(item)
    return result


def _receipt(root: Path, config: dict, args: dict) -> dict:
    target = safe_id(args["target_request_id"], field="target_request_id")
    path = dirs(root)["replay"] / (target + ".json")
    try:
        raw = secure_read_bytes(path, max_bytes=1024 * 1024)
    except FileNotFoundError:
        raise ReadFailure("EFFECT_AUTHORIZATION_OR_RECEIPT_ABSENT") from None
    if hashlib.sha256(raw).hexdigest() != args["expected_sha256"]:
        raise ReadFailure("RECEIPT_BYTES_MISMATCH", isolate=True)
    receipt = _strict_json_loads(raw)
    if not isinstance(receipt, dict) or receipt.get("schema") != "qikvrt_api_idempotency_receipt_v1" or receipt.get("request_id") != target:
        raise ReadFailure("INVALID_EFFECT_RECEIPT", isolate=True)
    result = receipt.get("result", {})
    if receipt.get("result_sha256") != "sha256:" + hashlib.sha256(canonical_json(result).encode()).hexdigest():
        raise ReadFailure("EFFECT_RESULT_HASH_MISMATCH", isolate=True)
    protocol = ResponsibilityProtocol.from_dict(result["effect_ack"]["responsibility_protocol"])
    expected_root = "qikvrt:api:" + hashlib.sha256((config["repository"] + ":" + target).encode()).hexdigest()
    if protocol.input_id != target or protocol.protocol_root_id != expected_root or protocol.responsibility_owner != config["principal"]:
        raise ReadFailure("EFFECT_RECEIPT_OUTSIDE_PRINCIPAL_OR_REPOSITORY", isolate=True)
    if result.get("effect_state") != protocol.state.value or result.get("ordinary_release") != protocol.ordinary_release or result["effect_ack"].get("state") != protocol.state.value or result["effect_ack"].get("ordinary_release") != protocol.ordinary_release:
        raise ReadFailure("EFFECT_ENVELOPE_MISMATCH", isolate=True)
    return {"record_sha256": hashlib.sha256(raw).hexdigest(), "record_b64": base64.b64encode(raw).decode(),
            "record_source": ".qikvrt/api/replay/" + target + ".json", "producer_head": None,
            "producer_head_binding": "NOT_RECORDED_BY_LEGACY_HANDLER", "reported_result": result,
            "external_effect_verified": False, "verification_scope": "RECEIPT_BYTES_AND_PROTOCOL_ONLY"}


def _gate(config: dict, request_id: str, data: dict, failure: ReadFailure | None = None) -> dict:
    return EffectAckEngine().evaluate(EffectAckRequest(
        protocol_root_id="qikvrt:mcp:" + hashlib.sha256((config["repository"] + ":" + request_id).encode()).hexdigest(),
        input_id=request_id, payload=canonical_json(data).encode(), transport_ack=True,
        origin_checked=True, context_checked=True, semantics_reconstructed=True, effect_anticipated=True,
        risk_classified=True, risk_level=RiskLevel.LOW, responsibility_assigned=True,
        responsibility_owner=config["principal"], policy_allows_release=False,
        connection_decision=(ConnectionDecision.ISOLATE if failure and failure.isolate else ConnectionDecision.BLOCK if failure else ConnectionDecision.CONTINUE),
        reasons=(failure.code if failure else "READ_ONLY_NO_EFFECT_GRANT",),
    )).to_dict()


def call_tool(config: dict, name: str, args: dict) -> dict:
    definition = next((tool for tool in tools(config) if tool["name"] == name), None)
    if definition is None:
        failure = ReadFailure("TOOL_NOT_AUTHORIZED_OR_WRITE_NOT_EXPOSED")
        return _tool_result(config, "denied", {"error": failure.code}, failure)
    schema = definition["inputSchema"]
    if not isinstance(args, dict) or set(args) - set(schema["properties"]) or set(schema["required"]) - set(args):
        raise ValueError("tool arguments do not match the bounded schema")
    for key, value in args.items():
        if not isinstance(value, str) or not re.fullmatch(schema["properties"][key]["pattern"], value):
            raise ValueError("invalid tool argument: " + key)
    request_id = safe_id(args["request_id"], field="request_id")
    root = Path(os.environ.get("QIKVRT_REPO_ROOT", os.getcwd()))
    fingerprint = hashlib.sha256(canonical_json({"repository": config["repository"], "principal": config["principal"], "tool": name, "args": args}).encode()).hexdigest()
    try:
        with _HANDLER_LOCK, process_lock(root):
            # Durable replay binding only; results are ALWAYS read afresh.
            key = hashlib.sha256((config["principal"] + ":" + request_id).encode()).hexdigest()
            path = dirs(root)["state"] / ("mcp-request-" + key + ".json")
            replayed = path.exists()
            binding = {"schema": "qikvrt_mcp_request_binding_v1", "fingerprint": fingerprint}
            if replayed:
                if _strict_json_loads(secure_read_bytes(path, max_bytes=1024)) != binding:
                    raise ReadFailure("REQUEST_ID_REPLAY_CONFLICT", isolate=True)
            else:
                atomic_write_bytes(path, canonical_json(binding).encode())
            state = _head(config)
            if args.get("expected_head", state["head"]) != state["head"]:
                raise ReadFailure("STALE_REPOSITORY_HEAD")
            data = {"repository_state": state, "replayed": replayed, "external_effect": "NONE"}
            if name == "qikvrt_capabilities":
                data.update({"sources": _sources(config, state), "mcp_tools": tools(config), "writes_exposed": False})
            elif name == "qikvrt_effect_ack_result":
                data["effect_receipt"] = _receipt(root, config, args)
            after = _head(config)
            if (after["head"], after["tree"]) != (state["head"], state["tree"]):
                raise ReadFailure("REPOSITORY_CHANGED_DURING_READ")
            data["closing_readback"] = after
            result = _tool_result(config, request_id, data)
            append_audit(root, {"event": "mcp_read_result", "request_id": request_id, "tool": name,
                                "head": after["head"], "tree": after["tree"], "result_sha256": hashlib.sha256(canonical_json(result).encode()).hexdigest(), "ordinary_release": False})
            return result
    except ReadFailure as failure:
        return _tool_result(config, request_id, {"error": failure.code, "external_effect": "NONE"}, failure)
    except IntegrityIsolationError:
        return _tool_result(config, request_id, {"error": "LOCAL_INTEGRITY_FAILURE"}, ReadFailure("LOCAL_INTEGRITY_FAILURE", isolate=True))
    except Exception:
        # Never copy upstream errors, paths, credentials, or raw HTTP bodies.
        return _tool_result(config, request_id, {"error": "READBACK_FAILED_NO_EFFECT"}, ReadFailure("READBACK_FAILED_NO_EFFECT"))


def _tool_result(config: dict, request_id: str, data: dict, failure: ReadFailure | None = None) -> dict:
    data.update({"effect_ack": _gate(config, request_id, data, failure), "ordinary_release": False, "external_effect_verified": False})
    return {"content": [{"type": "text", "text": canonical_json(data)}], "structuredContent": data, "isError": failure is not None}


def rpc(body: dict, version_header: str | None, headers=None) -> tuple[int, dict | None]:
    """Bounded stateless tools profile; modern discovery and legacy initialize."""
    request_id = body.get("id")
    def error(code, message, status=400):
        return status, {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    if body.get("jsonrpc") != "2.0" or set(body) - {"jsonrpc", "id", "method", "params"} or not isinstance(body.get("method"), str):
        return error(-32600, "Invalid Request")
    if "id" in body and (isinstance(request_id, bool) or not isinstance(request_id, (str, int)) or len(str(request_id)) > 128):
        return error(-32600, "Invalid request id")
    params = body.get("params", {})
    if not isinstance(params, dict):
        return error(-32602, "Object params required")
    method = body["method"]
    if version_header is not None and version_header not in VERSIONS:
        return error(-32602, "Unsupported protocol version; supported: " + ", ".join(VERSIONS))
    meta = params.get("_meta", {})
    modern = version_header == VERSIONS[0] or isinstance(meta, dict) and meta.get("io.modelcontextprotocol/protocolVersion") == VERSIONS[0]
    if modern:
        if not isinstance(meta, dict) or version_header != meta.get("io.modelcontextprotocol/protocolVersion"):
            return error(-32020, "HeaderMismatch: protocol version")
        if not isinstance(meta.get("io.modelcontextprotocol/clientInfo"), dict) or not isinstance(meta.get("io.modelcontextprotocol/clientCapabilities"), dict):
            return error(-32602, "Required per-request client metadata missing")
        for field, expected in (("Mcp-Method", method), ("Mcp-Name", params.get("name") if method == "tools/call" else None)):
            if expected is None:
                continue
            values = headers.get_all(field, []) if headers is not None else []
            if len(values) != 1:
                return error(-32020, "HeaderMismatch: required header")
            value = values[0]
            if any(ord(char) < 32 or ord(char) > 126 for char in value):
                return error(-32020, "HeaderMismatch: malformed header")
            if field == "Mcp-Name" and value.startswith("=?base64?") and value.endswith("?="):
                try:
                    value = base64.b64decode(value[9:-2], validate=True).decode("utf-8")
                except (ValueError, UnicodeError):
                    return error(-32020, "HeaderMismatch: encoded name")
            if value != expected:
                return error(-32020, "HeaderMismatch: body differs")
    if "id" not in body:
        if method in ("notifications/initialized", "notifications/cancelled"):
            return 202, None
        return error(-32600, "This method requires an id")
    config = configuration()
    if method == "server/discover" and modern:
        if set(params) - {"_meta"}:
            return error(-32602, "Unexpected discovery parameters")
        result = {"supportedVersions": list(VERSIONS), "capabilities": {"tools": {"listChanged": False}},
                  "_meta": {"io.modelcontextprotocol/serverInfo": INFO}}
    elif method == "initialize" and not modern:
        if set(params) - {"protocolVersion", "capabilities", "clientInfo"} or not isinstance(params.get("protocolVersion"), str) or not isinstance(params.get("capabilities"), dict) or not isinstance(params.get("clientInfo"), dict):
            return error(-32602, "Invalid initialize parameters")
        result = {"protocolVersion": params["protocolVersion"] if params["protocolVersion"] in VERSIONS[1:] else VERSIONS[1],
                  "capabilities": {"tools": {"listChanged": False}}, "serverInfo": INFO,
                  "instructions": "Read-only evidence. Tool results do not authorize or prove external effects."}
    elif method in ("ping", "tools/list"):
        if set(params) - {"_meta"}:
            return error(-32602, "Unexpected parameters")
        result = {} if method == "ping" else {"tools": tools(config)}
    elif method == "tools/call":
        if set(params) - {"name", "arguments", "_meta"} or not isinstance(params.get("name"), str):
            return error(-32602, "Invalid tool call")
        try:
            result = call_tool(config, params["name"], params.get("arguments", {}))
        except ValueError:
            return error(-32602, "Invalid tool arguments")
    else:
        return error(-32601, "Method not found", 404 if modern else 200)
    if modern:
        result["resultType"] = "complete"
    return 200, {"jsonrpc": "2.0", "id": request_id, "result": result}
