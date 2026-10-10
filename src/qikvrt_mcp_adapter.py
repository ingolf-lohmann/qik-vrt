#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only MCP facade for the existing REST shim and EFFECT_ACK records.

The common shim owns HTTP authentication and JSON-RPC. Protective replay and
audit persistence reuses the API handler; no effect grant is created here.
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qikvrt_api_client import github_json_get
from tools.qikvrt_self_disclosure import SEAL_PATH, validate_owner_seal

VERSIONS = ("2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SOURCE_PATHS = ("api/qikvrt_github_api.openapi.yaml", "scripts/qikvrt_api_client.py",
                "src/qikvrt_api_handler.py", "src/qikvrt_effect_ack.py",
                "src/qikvrt_github_api_shim.py", "src/qikvrt_mcp_adapter.py",
                ".well-known/qik-vrt-self-disclosure.json", SEAL_PATH,
                "tools/qikvrt_self_disclosure.py")
SCOPES = {
    "qikvrt_repository_state": "repository:read",
    "qikvrt_capabilities": "capability:read",
    "qikvrt_effect_ack_result": "effect_ack:read",
}


def enabled() -> bool:
    return os.environ.get("QIKVRT_MCP_ENABLED") == "1"


def separate_read_credential() -> str:
    """Validate key separation independently of expiry or tool admission."""
    token = os.environ.get("QIKVRT_MCP_TOKEN", "")
    material = decode_secret_material(token, field="QIKVRT_MCP_TOKEN")
    for name in ("QIKVRT_API_TOKEN", "QIKVRT_REMOTE_ATTESTATION_SECRET", "QIKVRT_MCP_GITHUB_READ_TOKEN"):
        other = os.environ.get(name, "")
        if other and hmac.compare_digest(token.encode(), other.encode()):
            raise ValueError("MCP requires a separate read credential")
        if other.startswith("b64url:") and hmac.compare_digest(material, decode_secret_material(other, field=name)):
            raise ValueError("MCP requires separate key material")
    return token


def configuration() -> dict:
    token = separate_read_credential()
    expiry = datetime.fromisoformat(os.environ.get("QIKVRT_MCP_TOKEN_EXPIRES_UTC", "").replace("Z", "+00:00"))
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("MCP credential is expired or has no timezone")
    repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", repository) or any(part in (".", "..") for part in repository.split("/")):
        raise ValueError("MCP requires an exact repository scope")
    principal = os.environ.get("QIKVRT_MCP_PRINCIPAL", "").strip()
    if not principal or len(principal) > 256:
        raise ValueError("MCP requires a configured principal")
    explicit = os.environ.get("QIKVRT_MCP_READ_SCOPES")
    scopes = set((explicit if explicit is not None else os.environ.get("QIKVRT_MCP_SCOPES", "")).split())
    if not scopes <= set(SCOPES.values()) | {"artifact:read"} | ({"ingest", "readback"} if explicit is None else set()):
        raise ValueError("MCP scopes must be explicit known scopes")
    scopes &= set(SCOPES.values()) | {"artifact:read"}
    if not scopes:
        raise ValueError("MCP credential requires an explicit evidence read scope")
    ref = os.environ.get("QIKVRT_MCP_REF", "main")
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}", ref) or ".." in ref:
        raise ValueError("MCP ref must be one bounded configured ref")
    return {"repository": repository, "principal": principal, "scopes": scopes, "ref": ref, "token": token}

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


def _sources(config: dict, state: dict) -> tuple[list[dict], dict]:
    tree = _get(config, "git/trees/" + state["tree"] + "?recursive=1")["document"]
    if tree.get("sha") != state["tree"] or tree.get("truncated") is not False or not isinstance(tree.get("tree"), list):
        raise ReadFailure("INCOMPLETE_SOURCE_TREE", isolate=True)
    entries = {item["path"]: item for item in tree["tree"]}
    result = []
    seal_bytes = {}
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
        if path in (SEAL_PATH, ".well-known/qik-vrt-self-disclosure.json"):
            seal_bytes[path] = raw
    try:
        binding = _strict_json_loads(seal_bytes[".well-known/qik-vrt-self-disclosure.json"])["bindings"]["owner_seal_acceptance"]
        receipt = validate_owner_seal(seal_bytes[SEAL_PATH], binding)
    except (ValueError, KeyError, TypeError):
        raise ReadFailure("OWNER_SEAL_READBACK_INVALID", isolate=True)
    subject = receipt["subject"]
    seal = {"binding": binding, "receipt": receipt,
            "observed_subject_accepted": (config["repository"], state["head"], state["tree"]) == (subject["repository"], subject["head"], subject["tree"])}
    return result, seal


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
                sources, seal = _sources(config, state)
                data.update({"sources": sources, "owner_seal_acceptance": seal,
                             "mcp_tools": tools(config), "writes_exposed": False})
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
