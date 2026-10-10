#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import base64
import hashlib
import hmac
import os
import re
import ssl
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qikvrt_api_handler import HandlerConfig, decode_secret_material, run_handler, read_ingested_artifact, safe_id, require_sha
from qikvrt_effect_ack import EffectState
import qikvrt_mcp_adapter as read_mcp
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qikvrt_api_client import API_CONTRACT_VERSION, read_regular_file

REPOSITORY_COMPONENT = r"([A-Za-z0-9_.-]{1,100})"
DISPATCH_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/actions/workflows/qikvrt_mesh_api\.yml/dispatches$")
REPO_DISPATCH_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/dispatches$")
READBACK_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/qikvrt/artifacts/([A-Za-z0-9_.=-]{{1,128}})/readback$")
MCP_VERSIONS = ("2025-11-25", "2026-07-28")
MCP_MAX_PAYLOAD_BYTES = 256 * 1024
MCP_SOURCE_PATHS = ("scripts/qikvrt_api_client.py", "src/qikvrt_api_handler.py",
                    "src/qikvrt_effect_ack.py", "src/qikvrt_github_api_shim.py",
                    "src/qikvrt_mcp_adapter.py", "api/qikvrt_github_api.openapi.yaml",
                    "tools/qikvrt_self_disclosure.py")
MAX_REQUEST_BYTES = 1024 * 1024
_RATE_LOCK = threading.Lock()
_RATE_WINDOWS: dict[str, tuple[int, int]] = {}


def mcp_implementation_binding() -> dict:
    root = Path(__file__).resolve().parents[1]
    digests = {path: hashlib.sha256(read_regular_file(root / path, max_bytes=1024 * 1024)).hexdigest()
               for path in MCP_SOURCE_PATHS}
    encoded = json.dumps(digests, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "files": digests,
            "api_contract_version": API_CONTRACT_VERSION,
            "scope": "runtime-source-bytes; remote HEAD/TREE must be independently read"}


MCP_BOOT_BINDING = mcp_implementation_binding()


def _mcp_scopes() -> set[str]:
    return set(os.environ.get("QIKVRT_MCP_DATA_SCOPES", os.environ.get("QIKVRT_MCP_SCOPES", "")).split()) & {"ingest", "readback"}


def _mcp_configuration_valid() -> bool:
    enabled = os.environ.get("QIKVRT_MCP_ENABLED", "0")
    scopes = set(os.environ.get("QIKVRT_MCP_SCOPES", "").split())
    read_scopes = set(os.environ.get("QIKVRT_MCP_READ_SCOPES", "").split())
    data_scopes = set(os.environ.get("QIKVRT_MCP_DATA_SCOPES", "").split())
    return (enabled in {"0", "1"}
            and scopes <= {"ingest", "readback"} | set(read_mcp.SCOPES.values())
            and read_scopes <= set(read_mcp.SCOPES.values()) | {"artifact:read"}
            and data_scopes <= {"ingest", "readback"})


def _mcp_tools(scopes: set[str] | None = None) -> list[dict]:
    common = {
        "repository": {"type": "string"},
        "artifact_id": {"type": "string", "pattern": "^[A-Za-z0-9_.=-]{1,128}$"},
        "request_id": {"type": "string", "pattern": "^[A-Za-z0-9_.=-]{1,128}$"},
        "expected_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "api_contract_version": {"type": "string", "const": API_CONTRACT_VERSION},
        "expected_implementation_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    }
    result = []
    for scope in sorted(_mcp_scopes() if scopes is None else scopes):
        properties = dict(common)
        if scope == "ingest":
            properties.update({"payload_b64": {"type": "string", "maxLength": 4 * ((MCP_MAX_PAYLOAD_BYTES + 2) // 3)},
                               "effect_accepted": {"type": "boolean", "const": True}})
        result.append({
            "name": f"qikvrt_{scope}",
            "description": ("Store opaque bytes only after explicit scoped acceptance; stable request_id is idempotent."
                            if scope == "ingest" else "Read committed ingest bytes and provenance without mutation."),
            "inputSchema": {"type": "object", "properties": properties,
                            "required": list(properties), "additionalProperties": False},
            "annotations": {"readOnlyHint": scope == "readback", "destructiveHint": False,
                            "idempotentHint": True, "openWorldHint": False},
        })
    return result


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


def _parse_expiry(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)

def _api_credential_valid() -> bool:
    token = os.environ.get("QIKVRT_API_TOKEN", "")
    expiry = _parse_expiry(os.environ.get("QIKVRT_API_TOKEN_EXPIRES_UTC", ""))
    try:
        decode_secret_material(token, field="QIKVRT_API_TOKEN")
    except ValueError:
        return False
    return bool(expiry is not None and expiry > datetime.now(timezone.utc))


def _attestation_configuration_valid() -> bool:
    secret = os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", "")
    signer = os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip()
    if not secret and not signer:
        return True
    if not secret or not signer or len(signer) > 256:
        return False
    try:
        secret_material = decode_secret_material(
            secret, field="QIKVRT_REMOTE_ATTESTATION_SECRET"
        )
        token_material = decode_secret_material(
            os.environ.get("QIKVRT_API_TOKEN", ""), field="QIKVRT_API_TOKEN"
        )
    except ValueError:
        return False
    return not hmac.compare_digest(secret_material, token_material)


def _security_configuration_valid() -> bool:
    repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
    principal = os.environ.get("QIKVRT_API_PRINCIPAL", "").strip()
    try:
        socket_timeout = float(os.environ.get("QIKVRT_SOCKET_TIMEOUT_SECONDS", "10"))
        rate_limit = int(os.environ.get("QIKVRT_RATE_LIMIT_PER_MINUTE", "120"))
    except ValueError:
        return False
    return bool(
        _api_credential_valid()
        and _attestation_configuration_valid()
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", repository)
        and principal
        and len(principal) <= 256
        and 0.1 <= socket_timeout <= 120
        and 1 <= rate_limit <= 100_000
    )


class QikvrtGitHubApiShim(BaseHTTPRequestHandler):
    server_version = "QIKVRTGitHubApiShim/2.1"

    def setup(self) -> None:
        super().setup()
        try:
            timeout = float(os.environ.get("QIKVRT_SOCKET_TIMEOUT_SECONDS", "10"))
        except ValueError:
            timeout = 10.0
        self.connection.settimeout(timeout if 0.1 <= timeout <= 120 else 10.0)

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        if self.headers.get("Transfer-Encoding") is not None:
            raise ValueError("Transfer-Encoding is not supported")
        lengths = self.headers.get_all("Content-Length", failobj=[])
        if len(lengths) != 1:
            raise ValueError("exactly one Content-Length header is required")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            n = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if n <= 0:
            raise ValueError("JSON request body is required")
        if n > MAX_REQUEST_BYTES:
            raise ValueError("request too large")
        raw = self.rfile.read(n)
        if len(raw) != n:
            raise ValueError("incomplete request body")
        try:
            body = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("malformed UTF-8 JSON request") from exc
        if not isinstance(body, dict):
            raise ValueError("JSON request body must be an object")
        return body

    def _authorized(self) -> bool:
        token = os.environ.get("QIKVRT_API_TOKEN", "")
        if not _api_credential_valid():
            return False
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied.encode("utf-8"), f"Bearer {token}".encode("utf-8"))

    def _rate_allowed(self) -> bool:
        try:
            limit = int(os.environ.get("QIKVRT_RATE_LIMIT_PER_MINUTE", "120"))
        except ValueError:
            return False
        if not 1 <= limit <= 100_000:
            return False
        identity = self.client_address[0]
        window = int(time.time() // 60)
        with _RATE_LOCK:
            if len(_RATE_WINDOWS) > 4096:
                stale = [key for key, (seen_window, _) in _RATE_WINDOWS.items() if seen_window != window]
                for key in stale:
                    _RATE_WINDOWS.pop(key, None)
            prior_window, count = _RATE_WINDOWS.get(identity, (window, 0))
            if prior_window != window:
                prior_window, count = window, 0
            count += 1
            _RATE_WINDOWS[identity] = (prior_window, count)
            return count <= limit

    @staticmethod
    def _boolean(raw: object, *, field: str) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.lower() in ("true", "false"):
            return raw.lower() == "true"
        raise ValueError(f"{field} must be true or false")

    def _mcp_guard(self) -> bool:
        if not _mcp_configuration_valid():
            self._send_json(503, {"status": "BLOCK", "reason": "invalid service configuration"})
            return False
        for header in ("Host", "Origin", "Authorization", "Accept", "Content-Type",
                       "MCP-Protocol-Version", "Mcp-Method", "Mcp-Name"):
            if len(self.headers.get_all(header, [])) > 1:
                self._send_json(400, {"status": "BLOCK", "reason": "duplicate security or routing header"})
                return False
        hosts = set(os.environ.get("QIKVRT_MCP_HOSTS", "").split())
        if not hosts and self.server.server_address[0] == "127.0.0.1":
            hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host", "") not in hosts:
            self._send_json(403, {"status": "BLOCK", "reason": "Host outside the configured scope"})
            return False
        origins = set(os.environ.get("QIKVRT_MCP_ORIGINS", "").split())
        origins |= set(os.environ.get("QIKVRT_MCP_ALLOWED_ORIGINS", "").split())
        if self.server.server_address[0] == "127.0.0.1":
            origins |= {f"http://{host}" for host in hosts}
        if "Origin" in self.headers and self.headers["Origin"] not in origins:
            self._send_json(403, {"status": "BLOCK", "reason": "Origin outside the configured scope"})
            return False
        if not self._rate_allowed():
            self._send_json(429, {"status": "BLOCK", "reason": "rate limit exceeded"})
            return False
        self._mcp_read_config = None
        self._mcp_data_identity = False
        # Credential domains never inherit each other's tools or scopes.
        supplied = self.headers.get("Authorization", "").encode("utf-8")
        try:
            config = read_mcp.configuration()
            evidence_identity = hmac.compare_digest(supplied, ("Bearer " + config["token"]).encode("utf-8"))
        except (ValueError, TypeError, UnicodeError):
            config, evidence_identity = None, False
        # A present read key may never alias the data or attestation key,
        # including alternate encodings of the same secret material.
        read_key = os.environ.get("QIKVRT_MCP_TOKEN", "")
        if read_key:
            try:
                read_mcp.separate_read_credential()
            except (ValueError, TypeError, UnicodeError):
                self._send_json(401, {"status": "BLOCK", "reason": "invalid read credential"})
                return False
        if evidence_identity:
            self._mcp_read_config = config
        elif self._authorized():
            if not _security_configuration_valid():
                self._send_json(503, {"status": "BLOCK", "reason": "invalid service configuration"})
                return False
            self._mcp_data_identity = True
        else:
            self._send_json(401, {"status": "BLOCK", "reason": "unauthorized"})
            return False
        return True

    def _mcp_cfg(self, arguments: dict, *, write: bool) -> HandlerConfig:
        common = {"repository", "artifact_id", "request_id", "expected_sha256",
                  "api_contract_version", "expected_implementation_sha256"}
        required = common | ({"payload_b64", "effect_accepted"} if write else set())
        if not self._mcp_data_identity and (write or not self._mcp_readback_permitted()):
            raise ValueError("data credential required")
        if not isinstance(arguments, dict) or set(arguments) != required:
            raise ValueError("exact tool argument fields are required")
        if any(not isinstance(arguments[key], str) for key in required - {"effect_accepted"}):
            raise ValueError("tool string arguments are required")
        if arguments["api_contract_version"] != API_CONTRACT_VERSION:
            raise ValueError("REST contract version mismatch")
        binding = mcp_implementation_binding()
        if binding != MCP_BOOT_BINDING or arguments["expected_implementation_sha256"] != binding["sha256"]:
            raise ValueError("implementation source binding mismatch")
        if arguments["repository"] != os.environ.get("QIKVRT_ALLOWED_REPOSITORY"):
            raise ValueError("repository outside the credential scope")
        safe_id(arguments["artifact_id"])
        safe_id(arguments["request_id"], field="request_id")
        require_sha(arguments["expected_sha256"])
        if write:
            if arguments["effect_accepted"] is not True:
                raise ValueError("explicit scoped effect acceptance is required")
            encoded = arguments["payload_b64"]
            if len(encoded) > 4 * ((MCP_MAX_PAYLOAD_BYTES + 2) // 3):
                raise ValueError("MCP payload exceeds 256 KiB")
            payload = base64.b64decode(encoded, validate=True)
            if (len(payload) > MCP_MAX_PAYLOAD_BYTES
                    or base64.b64encode(payload).decode("ascii") != encoded
                    or hashlib.sha256(payload).hexdigest() != arguments["expected_sha256"]):
                raise ValueError("MCP payload byte binding mismatch")
        return HandlerConfig(
            root=Path(os.environ.get("QIKVRT_REPO_ROOT", os.getcwd())),
            operation="ingest" if write else "verify",
            artifact_id=arguments["artifact_id"], payload_b64=arguments.get("payload_b64", ""),
            expected_sha256=arguments["expected_sha256"], dry_run=not write,
            repository=arguments["repository"], run_id="mcp-rest-shim",
            request_id=arguments["request_id"], effect_accepted=write,
            responsibility_owner=(self._mcp_read_config["principal"] if self._mcp_read_config
                                  else os.environ["QIKVRT_API_PRINCIPAL"].strip()), origin_authenticated=True,
            trusted_attestation_secret=os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", ""),
            trusted_attestation_signer=os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip(),
        )

    def _mcp_readback_permitted(self) -> bool:
        return ("artifact:read" in self._mcp_read_config["scopes"] if self._mcp_read_config
                else self._mcp_data_identity and "readback" in _mcp_scopes())

    def _artifact_readback(self) -> None:
        if not self._mcp_guard():
            return
        if not self._mcp_readback_permitted():
            self._send_json(403, {"status": "BLOCK", "reason": "readback permission required"})
            return
        try:
            parsed = urlparse(self.path)
            match = READBACK_RE.fullmatch(parsed.path)
            query = parse_qs(parsed.query, strict_parsing=True)
            if (set(query) != {"request_id", "expected_sha256", "api_contract_version", "expected_implementation_sha256"}
                    or parsed.params or parsed.fragment or any(len(values) != 1 for values in query.values())):
                raise ValueError("invalid readback locator")
            arguments = {key: values[0] for key, values in query.items()}
            arguments.update({"repository": f"{match.group(1)}/{match.group(2)}", "artifact_id": match.group(3)})
            cfg = self._mcp_cfg(arguments, write=False)
            payload, proof = read_ingested_artifact(cfg, max_bytes=MCP_MAX_PAYLOAD_BYTES)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-QIKVRT-Readback-SHA256", proof["sha256"])
            self.end_headers()
            self.wfile.write(payload)
        except Exception:
            self._send_json(409, {"status": "BLOCK", "reason": "readback binding or committed evidence unavailable"})

    def _mcp_post(self) -> None:
        if not self._mcp_guard():
            return
        identifier = None
        version = self.headers.get("MCP-Protocol-Version", "")
        supported_versions = read_mcp.VERSIONS if self._mcp_read_config else MCP_VERSIONS
        def error(status: int, code: int, message: str, data=None) -> None:
            body = {"jsonrpc": "2.0", "id": identifier, "error": {"code": code, "message": message}}
            if data is not None:
                body["error"]["data"] = data
            self._send_json(status, body)
        def reply(result: dict) -> None:
            if version == "2026-07-28":
                result["resultType"] = "complete"
            self._send_json(200, {"jsonrpc": "2.0", "id": identifier, "result": result})
        try:
            accept = {item.split(";", 1)[0].strip() for item in self.headers.get("Accept", "").split(",")}
            if not {"application/json", "text/event-stream"} <= accept:
                error(406, -32600, "Accept must include JSON and event-stream")
                return
            body = self._read_json()
            if (body.get("jsonrpc") != "2.0" or set(body) - {"jsonrpc", "id", "method", "params"}
                    or not isinstance(body.get("method"), str) or not isinstance(body.get("params", {}), dict)):
                raise ValueError("invalid JSON-RPC request")
            identifier = body.get("id")
            if "id" in body and (type(identifier) not in (str, int) or isinstance(identifier, str) and not 0 < len(identifier) <= 128):
                raise ValueError("invalid JSON-RPC id")
            method = body["method"]
            params = body.get("params", {})
            if method == "initialize":
                version = params.get("protocolVersion", "")
                if (set(params) != {"protocolVersion", "capabilities", "clientInfo"}
                        or not isinstance(params["capabilities"], dict) or not isinstance(params["clientInfo"], dict)):
                    raise ValueError("invalid initialization")
                if self.headers.get("MCP-Protocol-Version") not in (None, version):
                    error(400, -32020, "HeaderMismatch")
                    return
            if version not in supported_versions:
                error(400, -32022, "Unsupported protocol version", {"supported": list(supported_versions)})
                return
            body_meta = params.get("_meta", {})
            if (isinstance(body_meta, dict) and "io.modelcontextprotocol/protocolVersion" in body_meta
                    and body_meta["io.modelcontextprotocol/protocolVersion"] != version):
                error(400, -32020, "HeaderMismatch")
                return
            if version == "2026-07-28":
                meta = params.get("_meta", {})
                info = meta.get("io.modelcontextprotocol/clientInfo", {}) if isinstance(meta, dict) else {}
                if (not isinstance(meta, dict) or meta.get("io.modelcontextprotocol/protocolVersion") != version
                        or self.headers.get("Mcp-Method") != method):
                    error(400, -32020, "HeaderMismatch")
                    return
                if (not isinstance(info, dict) or not all(isinstance(info.get(k), str) and 0 < len(info[k]) <= 256 for k in ("name", "version"))
                        or not isinstance(meta.get("io.modelcontextprotocol/clientCapabilities"), dict)):
                    raise ValueError("required per-request client metadata missing")
                if method == "tools/call":
                    name_header = self.headers.get("Mcp-Name", "")
                    if name_header.startswith("=?base64?") and name_header.endswith("?="):
                        name_header = base64.b64decode(name_header[9:-2], validate=True).decode("utf-8")
                    if name_header != params.get("name"):
                        error(400, -32020, "HeaderMismatch")
                        return
            if "id" not in body:
                if method == "notifications/initialized" and version != "2026-07-28" and not params:
                    self.send_response(202)
                    self.send_header("Content-Length", "0")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    return
                raise ValueError("effectful notifications are forbidden")
            server_info = {"name": "QIKVRT-REST-MCP", "version": "1.1.0"}
            if method == "initialize" and version != "2026-07-28":
                reply({"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": server_info,
                       "_meta": {"qikvrt/implementation": MCP_BOOT_BINDING}})
            elif method == "server/discover" and version == "2026-07-28" and set(params) == {"_meta"}:
                reply({"supportedVersions": list(supported_versions), "capabilities": {"tools": {}},
                       "_meta": {"io.modelcontextprotocol/serverInfo": server_info, "qikvrt/implementation": MCP_BOOT_BINDING},
                       "cacheScope": "private", "ttlMs": 0})
            elif method in {"tools/list", "ping"}:
                if set(params) - {"_meta"}:
                    raise ValueError("unexpected method parameters")
                evidence_tools = read_mcp.tools(self._mcp_read_config) if self._mcp_read_config else []
                data_tools = (_mcp_tools({"readback"}) if self._mcp_readback_permitted() else []) if self._mcp_read_config else _mcp_tools()
                reply({"tools": evidence_tools + data_tools}
                      if method == "tools/list" else {})
            elif method == "tools/call":
                if set(params) - {"name", "arguments", "_meta"} or not {"name", "arguments"} <= set(params):
                    raise ValueError("exact call parameters are required")
                name = params["name"]
                if not isinstance(name, str):
                    raise ValueError("tool name must be a string")
                if self._mcp_read_config and name != "qikvrt_readback":
                    if name in {"qikvrt_ingest", "qikvrt_readback"}:
                        error(403, -32001, "Data credential required")
                        return
                    if mcp_implementation_binding() != MCP_BOOT_BINDING:
                        raise ValueError("implementation source binding mismatch")
                    reply(read_mcp.call_tool(self._mcp_read_config, name, params["arguments"]))
                    return
                if name in read_mcp.SCOPES:
                    error(403, -32001, "Evidence read credential required")
                    return
                if name not in {"qikvrt_ingest", "qikvrt_readback"}:
                    error(200, -32602, "Unknown tool")
                    return
                scope = name.removeprefix("qikvrt_")
                if (scope == "readback" and not self._mcp_readback_permitted()
                        or scope == "ingest" and (not self._mcp_data_identity or scope not in _mcp_scopes())):
                    error(403, -32001, "Required permission unavailable")
                    return
                cfg = self._mcp_cfg(params["arguments"], write=scope == "ingest")
                if scope == "ingest":
                    result = run_handler(cfg)
                else:
                    payload, result = read_ingested_artifact(cfg, max_bytes=MCP_MAX_PAYLOAD_BYTES)
                    result["payload_b64"] = base64.b64encode(payload).decode("ascii")
                wrapped = {"api_contract_version": API_CONTRACT_VERSION,
                           "implementation": MCP_BOOT_BINDING, "handler_result": result,
                           "effect_state": EffectState.EFFECT_ACK_CONTINUE.value, "ordinary_release": False,
                           "claude_connector_execution_verified": False}
                is_error = not (result.get("readback_verified") or result.get("effect_state") == EffectState.EFFECT_ACK_DONE.value)
                reply({"content": [{"type": "text", "text": json.dumps(wrapped, ensure_ascii=False, sort_keys=True)}],
                       "structuredContent": wrapped, "isError": is_error})
            else:
                error(404 if version == "2026-07-28" else 200, -32601, "Method not found")
        except (ValueError, UnicodeError):
            error(400, -32602, "Invalid request or exact version/source/effect binding")
        except Exception:
            error(200, -32603, "Committed evidence unavailable; reobserve before any mutation")

    def do_GET(self):
        if self.path == "/mcp" and os.environ.get("QIKVRT_MCP_ENABLED") == "1":
            if self._mcp_guard():
                self._send_json(405, {"status": "BLOCK", "reason": "MCP uses POST; no SSE stream"})
            return
        if READBACK_RE.match(urlparse(self.path).path) and os.environ.get("QIKVRT_MCP_ENABLED") == "1":
            self._artifact_readback()
            return
        if self.path == "/health":
            valid = _security_configuration_valid()
            attestation_configured = bool(
                os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", "")
                and os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip()
            )
            self._send_json(
                200 if valid else 503,
                {
                    "status": "ALIVE" if valid else "BLOCK",
                    "service": "QIKVRT GitHub-Compatible REST API Shim",
                    "tcpip": True,
                    "github_compatible_dispatch": True,
                    "configuration_valid": valid,
                    "authentication_configured": _api_credential_valid(),
                    "remote_attestation_configured": attestation_configured,
                },
            )
            return
        self._send_json(404, {"status": "BLOCK", "reason": "not found"})

    def do_DELETE(self):
        if self.path == "/mcp" and read_mcp.enabled():
            if self._mcp_guard():
                self._send_json(405, {"status": "BLOCK", "reason": "no protocol sessions"})
            return
        self._send_json(404, {"status": "BLOCK", "reason": "not found"})

    def do_POST(self):
        if self.path == "/mcp":
            if read_mcp.enabled():
                self._mcp_post()
            else:
                self._send_json(404, {"status": "BLOCK", "reason": "MCP disabled"})
            return
        if not self._rate_allowed():
            self._send_json(429, {"status": "BLOCK", "reason": "rate limit exceeded"})
            return
        if not self._authorized():
            self._send_json(401, {"status": "BLOCK", "reason": "unauthorized"})
            return
        parsed = urlparse(self.path)
        if parsed.query or parsed.params or parsed.fragment:
            self._send_json(404, {"status": "BLOCK", "reason": "unknown endpoint"})
            return
        m = DISPATCH_RE.match(parsed.path)
        mr = REPO_DISPATCH_RE.match(parsed.path)
        if not (m or mr):
            self._send_json(404, {"status": "BLOCK", "reason": "unknown endpoint"})
            return
        try:
            body = self._read_json()
            if m:
                unknown = set(body) - {"ref", "inputs", "return_run_details"}
                if unknown:
                    raise ValueError(f"unknown workflow dispatch fields: {sorted(unknown)}")
                if "return_run_details" in body and type(body["return_run_details"]) is not bool:
                    raise ValueError("return_run_details must be boolean")
                owner, repo = m.group(1), m.group(2)
                ref = body.get("ref")
                if not isinstance(ref, str) or not ref.strip() or len(ref) > 255:
                    raise ValueError("workflow dispatch ref is required")
                inputs = body.get("inputs", {})
            else:
                unknown = set(body) - {"event_type", "client_payload"}
                if unknown:
                    raise ValueError(f"unknown repository dispatch fields: {sorted(unknown)}")
                owner, repo = mr.group(1), mr.group(2)
                if body.get("event_type") != "qikvrt_mesh_api":
                    raise ValueError("unsupported repository_dispatch event_type")
                inputs = body.get("client_payload", {}) if isinstance(body.get("client_payload", {}), dict) else {}
            if not isinstance(inputs, dict):
                raise ValueError("dispatch inputs must be an object")
            required_inputs = {
                "operation", "artifact_id", "dry_run", "request_id", "effect_accepted",
            }
            missing_inputs = required_inputs - set(inputs)
            if missing_inputs:
                raise ValueError(f"missing dispatch inputs: {sorted(missing_inputs)}")
            allowed_inputs = {
                "operation", "artifact_id", "payload_b64", "expected_sha256",
                "dry_run", "request_id", "effect_accepted",
                "responsibility_owner", "state_run_id", "remote_evidence_b64",
            }
            unknown_inputs = set(inputs) - allowed_inputs
            if unknown_inputs:
                raise ValueError(f"unknown dispatch inputs: {sorted(unknown_inputs)}")
            request_id = str(inputs.get("request_id", "") or self.headers.get("X-QIKVRT-Request-ID", "")).strip()
            if not request_id:
                raise ValueError("request_id is required")
            requested_repository = f"{owner}/{repo}"
            allowed_repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
            if not hmac.compare_digest(requested_repository, allowed_repository):
                raise ValueError("repository is outside this credential scope")
            principal = os.environ.get("QIKVRT_API_PRINCIPAL", "").strip()
            supplied_owner = str(inputs.get("responsibility_owner", "")).strip()
            if supplied_owner and supplied_owner != principal:
                raise ValueError("responsibility_owner must match the authenticated principal")
            cfg = HandlerConfig(
                root=Path(os.environ.get("QIKVRT_REPO_ROOT", os.getcwd())),
                operation=str(inputs.get("operation", "")),
                artifact_id=str(inputs.get("artifact_id", "")),
                payload_b64=str(inputs.get("payload_b64", "")),
                expected_sha256=str(inputs.get("expected_sha256", "")),
                dry_run=self._boolean(inputs.get("dry_run", "true"), field="dry_run"),
                repository=requested_repository,
                run_id="local-tcpip-shim",
                request_id=request_id,
                effect_accepted=self._boolean(inputs.get("effect_accepted", "false"), field="effect_accepted"),
                responsibility_owner=principal,
                origin_authenticated=True,
                remote_evidence_b64=str(inputs.get("remote_evidence_b64", "")),
                trusted_attestation_secret=os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", ""),
                trusted_attestation_signer=os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip(),
            )
            result = run_handler(cfg)
            effect_state = result.get("effect_state")
            status = {
                EffectState.EFFECT_ACK_DONE.value: 202,
                EffectState.EFFECT_ACK_CONTINUE.value: 202,
                EffectState.EFFECT_NACK.value: 422,
                EffectState.EFFECT_ACK_ISOLATE.value: 423,
                EffectState.EFFECT_ACK_BLOCK.value: 409,
            }.get(effect_state, 500)
            response_status = {
                EffectState.EFFECT_ACK_DONE.value: "ACCEPTED",
                EffectState.EFFECT_ACK_CONTINUE.value: "CONTINUE",
                EffectState.EFFECT_NACK.value: "NACK",
                EffectState.EFFECT_ACK_ISOLATE.value: "ISOLATE",
                EffectState.EFFECT_ACK_BLOCK.value: "BLOCK",
            }.get(effect_state, "INTERNAL_ERROR")
            self._send_json(status, {"status": response_status, "handler_result": result})
        except (ValueError, UnicodeError) as exc:
            self._send_json(400, {"status": "BLOCK", "reason": str(exc)})
        except Exception as exc:
            if os.environ.get("QIKVRT_API_LOG", "0") == "1":
                print(f"QIK-VRT adapter internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
            self._send_json(500, {"status": "BLOCK", "reason": "internal adapter error"})

    def log_message(self, fmt, *args):
        if os.environ.get("QIKVRT_API_LOG", "0") == "1":
            super().log_message(fmt, *args)

def main() -> int:
    host = os.environ.get("QIKVRT_API_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("QIKVRT_API_PORT", "8766"))
    except ValueError:
        print("BLOCK QIKVRT_API_PORT must be an integer", file=sys.stderr)
        return 2
    if not 1 <= port <= 65535:
        print("BLOCK QIKVRT_API_PORT must be between 1 and 65535", file=sys.stderr)
        return 2
    try:
        decode_secret_material(
            os.environ.get("QIKVRT_API_TOKEN", ""),
            field="QIKVRT_API_TOKEN",
        )
    except ValueError as exc:
        print(f"BLOCK {exc}", file=sys.stderr)
        return 2
    allowed_repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
    principal = os.environ.get("QIKVRT_API_PRINCIPAL", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", allowed_repository):
        print("BLOCK QIKVRT_ALLOWED_REPOSITORY must be an exact owner/repo scope", file=sys.stderr)
        return 2
    if not principal or len(principal) > 256:
        print("BLOCK QIKVRT_API_PRINCIPAL must identify the authenticated responsibility owner", file=sys.stderr)
        return 2
    expiry = _parse_expiry(os.environ.get("QIKVRT_API_TOKEN_EXPIRES_UTC", ""))
    if expiry is None or expiry <= datetime.now(timezone.utc):
        print("BLOCK QIKVRT_API_TOKEN_EXPIRES_UTC must be a future timezone-aware timestamp", file=sys.stderr)
        return 2
    if not _attestation_configuration_valid():
        print(
            "BLOCK remote attestation requires a signer plus a canonical b64url secret decoding to 32--128 bytes",
            file=sys.stderr,
        )
        return 2
    try:
        socket_timeout = float(os.environ.get("QIKVRT_SOCKET_TIMEOUT_SECONDS", "10"))
        rate_limit = int(os.environ.get("QIKVRT_RATE_LIMIT_PER_MINUTE", "120"))
    except ValueError:
        print("BLOCK socket timeout and rate limit must be numeric", file=sys.stderr)
        return 2
    if not 0.1 <= socket_timeout <= 120:
        print("BLOCK QIKVRT_SOCKET_TIMEOUT_SECONDS must be between 0.1 and 120", file=sys.stderr)
        return 2
    if not 1 <= rate_limit <= 100_000:
        print("BLOCK QIKVRT_RATE_LIMIT_PER_MINUTE must be between 1 and 100000", file=sys.stderr)
        return 2
    if not _mcp_configuration_valid():
        print("BLOCK invalid MCP enable flag or scope allowlist", file=sys.stderr)
        return 2
    if host != "127.0.0.1" and os.environ.get("QIKVRT_ALLOW_NON_LOOPBACK") != "1":
        print("BLOCK non-loopback requires QIKVRT_ALLOW_NON_LOOPBACK=1", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((host, port), QikvrtGitHubApiShim)
    if host != "127.0.0.1":
        cert_file = os.environ.get("QIKVRT_TLS_CERT_FILE", "")
        key_file = os.environ.get("QIKVRT_TLS_KEY_FILE", "")
        if not cert_file or not key_file:
            print("BLOCK non-loopback service requires QIKVRT_TLS_CERT_FILE and QIKVRT_TLS_KEY_FILE", file=sys.stderr)
            server.server_close()
            return 2
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    print(json.dumps({"status": "PASS", "listening": f"{host}:{port}"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
