#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import hmac
import os
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qikvrt_api_handler import HandlerConfig, decode_secret_material, run_handler
from qikvrt_effect_ack import EffectState
from scripts.qikvrt_api_client import NoRedirectHandler, MAX_RESPONSE_BYTES
from tools.qikvrt_authority_transition import AuthorityControlPlane, TransitionError, decode
from tools import qikvrt_mesh_recovery as recovery
from tools.qikvrt_seed_common import canonical_json_bytes, parse_json_bytes, SeedError

REPOSITORY_COMPONENT = r"([A-Za-z0-9_.-]{1,100})"
DISPATCH_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/actions/workflows/qikvrt_mesh_api\.yml/dispatches$")
REPO_DISPATCH_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/dispatches$")
AUTHORITY_EFFECT_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/qikvrt/authority/effects$")
# Current independently established connection scope. No authority-root access
# can be inferred from lineage or an environment variable.
PROVIDER_REPOSITORY = "ingolf-lohmann/qik-vrt"
MAX_REQUEST_BYTES = 1024 * 1024
_RATE_LOCK = threading.Lock()
_RATE_WINDOWS: dict[str, tuple[int, int]] = {}


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


class GitHubAuthorityProvider:
    """Extend the existing authenticated shim; no second executor or token cache.

    V1 admits exactly one native CAS: absent -> create-only ref at the verified
    restored HEAD/TREE. GitHub REST ref PATCH has no expected-old-SHA field;
    ref update/delete, PR and other mutations are denied, not emulated by GET
    then an unconditional write. Independent bearer writers remain unfenced.
    """

    def __init__(self, control_plane: AuthorityControlPlane, repository: str):
        if repository != PROVIDER_REPOSITORY:
            raise TransitionError("no separately established provider capability")
        self.cp = control_plane
        self.repository = repository

    def _request(self, method: str, suffix: str, payload: dict | None = None,
                 *, admission: tuple | None = None) -> tuple[int, dict]:
        """Reuse the client no-redirect/bounded-response contract and token path."""
        token = os.environ.get("GITHUB_TOKEN", "")
        expiry = _parse_expiry(os.environ.get("QIKVRT_GITHUB_TOKEN_EXPIRES_UTC", ""))
        if (len(token) < 20 or any(c.isspace() for c in token) or expiry is None
                or expiry <= datetime.now(timezone.utc)
                or hmac.compare_digest(token, os.environ.get("QIKVRT_API_TOKEN", ""))):
            raise TransitionError("usable distinct short-lived provider capability required")
        if method not in {"GET", "POST"} or not re.fullmatch(r"git/(?:refs|ref/heads/[A-Za-z0-9/_-]+|commits/[0-9a-f]{40})", suffix):
            raise TransitionError("unsupported provider endpoint")
        if method == "POST" and suffix != "git/refs":
            raise TransitionError("provider mutation outside create-only ref contract")
        if method == "POST":
            if admission is None or len(admission) != 4:
                raise TransitionError("provider mutation requires locked fresh admission")
            db, writer, permit, document = admission
            state = self.cp.provider_admission(db, writer, permit, self.repository)
            row = db.execute("SELECT status, document FROM provider_effects WHERE id=?",
                             (document["effect_id"],)).fetchone()
            if (row != ("PENDING", canonical_json_bytes(document))
                    or document["binding"] != state["binding"] or document["permit"] != permit
                    or document["repository"] != self.repository
                    or document["ref"] != self.ref_name(permit, document["effect_id"])
                    or payload != {"ref": document["ref"], "sha": state["binding"]["head"]}):
                raise TransitionError("provider mutation escaped bound durable intent")
        url = f"https://api.github.com/repos/{self.repository}/{suffix}"
        request = urllib.request.Request(url, method=method,
            data=None if payload is None else canonical_json_bytes(payload), headers={
                "Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
                "User-Agent": "qikvrt-authority-api-shim"})
        try:
            response = urllib.request.build_opener(NoRedirectHandler()).open(request, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, urllib.error.URLError) as exc:
            raise TransitionError("provider transport outcome requires readback") from exc
        try:
            status = response.status
            if response.geturl() != url:
                raise TransitionError("provider origin changed")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        finally:
            response.close()
        if len(raw) > MAX_RESPONSE_BYTES or token.encode() in raw:
            raise TransitionError("invalid provider response boundary")
        # Error bodies are neither reflected nor persisted.
        if status not in {200, 201}:
            return status, {}
        try:
            value = parse_json_bytes(raw, "provider response")
        except (ValueError, TypeError, SeedError) as exc:
            raise TransitionError("invalid provider JSON") from exc
        if not isinstance(value, dict):
            raise TransitionError("invalid provider object")
        return status, value

    @staticmethod
    def ref_name(permit: dict, effect_id: str) -> str:
        return (f"refs/heads/work/qikvrt-recovery/{permit['control_plane_epoch']}/"
                f"{permit['authority_epoch']}/{permit['node_id']}/{permit['fence']}/"
                + recovery.digest(effect_id.encode()))

    @staticmethod
    def _journal(db) -> None:
        # Additive migration of the existing private control plane. Ordinary
        # operations still never recreate a missing database/state/epoch.
        db.execute("""CREATE TABLE IF NOT EXISTS provider_effects (
            id TEXT PRIMARY KEY, document BLOB NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('PREPARED','PENDING','VERIFIED','REJECTED')),
            receipt BLOB)""")

    def _read_effect(self, document: dict) -> bool:
        status, observed = self._request("GET", "git/ref/" + document["ref"].removeprefix("refs/"))
        if status == 404:
            return False
        if (status != 200 or not isinstance(observed.get("object"), dict)
                or observed.get("ref") != document["ref"]
                or observed.get("object", {}).get("type") != "commit"
                or observed.get("object", {}).get("sha") != document["sha"]):
            raise TransitionError("provider CAS conflict or ref readback mismatch")
        status, commit = self._request("GET", "git/commits/" + document["sha"])
        if (status != 200 or not isinstance(commit.get("tree"), dict)
                or commit.get("sha") != document["sha"]
                or commit.get("tree", {}).get("sha") != document["binding"]["tree"]):
            raise TransitionError("provider HEAD/TREE readback mismatch")
        return True

    def execute(self, token: str, permit: dict, operation: dict) -> dict:
        recovery.exact(operation, {"operation", "effect_id"}, "provider operation")
        if operation["operation"] != "create_ref":
            raise TransitionError("provider operation lacks a native CAS/readback contract")
        effect_id = operation["effect_id"]
        if (not isinstance(effect_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", effect_id)):
            raise TransitionError("invalid provider idempotency key")
        # Persist intent BEFORE any outbound request. Crash or ambiguity then
        # leaves an explicit PENDING fence, rather than losing an effect record.
        with self.cp.transaction() as db:
            state = self.cp.provider_admission(db, token, permit, self.repository)
            document = {"schema": "qikvrt_github_fenced_ref_intent_v1",
                "repository": self.repository, "permit": permit, "binding": state["binding"],
                "operation": "create_ref", "effect_id": effect_id,
                "ref": self.ref_name(permit, effect_id), "sha": state["binding"]["head"]}
            self._journal(db)
            prior = db.execute("SELECT document FROM provider_effects WHERE id=?", (effect_id,)).fetchone()
            if prior is not None:
                if decode(prior[0]) != document:
                    raise TransitionError("provider idempotency key binding conflict")
            else:
                if db.execute("SELECT 1 FROM provider_effects WHERE status IN ('PREPARED','PENDING') LIMIT 1").fetchone():
                    raise TransitionError("unresolved provider effect blocks new mutations")
                db.execute("INSERT INTO provider_effects VALUES (?, ?, 'PREPARED', NULL)",
                           (effect_id, canonical_json_bytes(document)))
                state["revision"] += 1
                self.cp.store(db, state)
        # Separate durable dispatch admission. PREPARED cannot be mistaken for
        # an attempted effect after restart. PENDING means GET-only recovery.
        dispatch = False
        rejected = False
        with self.cp.transaction() as db:
            self.cp.provider_admission(db, token, permit, self.repository)
            journal_status = db.execute("SELECT status FROM provider_effects WHERE id=?", (effect_id,)).fetchone()[0]
            if journal_status == "REJECTED":
                raise TransitionError("provider effect was rejected; key remains consumed")
            if journal_status == "PREPARED":
                status, _ = self._request("GET", "git/ref/" + document["ref"].removeprefix("refs/"))
                if status == 200:
                    rejected = True
                elif status != 404:
                    raise TransitionError("provider preflight could not establish absent ref")
                else:
                    status, commit = self._request("GET", "git/commits/" + document["sha"])
                    if (status != 200 or not isinstance(commit.get("tree"), dict)
                            or commit.get("sha") != document["sha"]
                            or commit.get("tree", {}).get("sha") != document["binding"]["tree"]):
                        rejected = True
                db.execute("UPDATE provider_effects SET status=? WHERE id=?",
                           ("REJECTED" if rejected else "PENDING", effect_id))
                dispatch = not rejected
        if rejected:
            raise TransitionError("provider CAS conflict or accepted HEAD/TREE mismatch")
        # Hold the SAME takeover lock for fresh permit, CAS and real readback.
        # No observation -> unlocked POST window and no in-process-only mutex.
        with self.cp.transaction() as db:
            self.cp.provider_admission(db, token, permit, self.repository)
            if dispatch:
                # Last fresh admission immediately before the ONLY mutation.
                self.cp.provider_admission(db, token, permit, self.repository)
                status, _ = self._request("POST", "git/refs",
                    {"ref": document["ref"], "sha": document["sha"]},
                    admission=(db, token, permit, document))
                if status in {409, 422}:
                    # A definite native CAS rejection is never laundered into
                    # our receipt by a matching competing writer's later GET.
                    rejected = True
                    db.execute("UPDATE provider_effects SET status='REJECTED' WHERE id=?", (effect_id,))
                elif status != 201:
                    raise TransitionError("provider create outcome requires GET reconciliation")
            if not rejected and not self._read_effect(document):
                raise TransitionError("provider effect not freshly observed; mutation not retried")
            if not rejected:
                receipt = {"schema": "qikvrt_github_fenced_ref_readback_v1",
                    **{k: document[k] for k in ("repository", "permit", "binding", "effect_id", "ref", "sha")},
                    "fresh_provider_readback": True, "replayed": prior is not None,
                    "observed_utc": datetime.now(timezone.utc).isoformat(),
                    "provider_authority_fencing_verified": False,
                    "effect_scope": "BROKER_MEDIATED_CREATE_ONLY_GITHUB_REF",
                    "effect_ack_done": False}
                db.execute("UPDATE provider_effects SET status='VERIFIED', receipt=? WHERE id=?",
                           (canonical_json_bytes(receipt), effect_id))
        if rejected:
            raise TransitionError("provider CAS conflict: native create was rejected")
        # Durable receipt is read separately; never infer it from POST success.
        with self.cp.transaction() as db:
            self.cp.provider_admission(db, token, permit, self.repository)
            observed = db.execute("SELECT status, receipt FROM provider_effects WHERE id=?", (effect_id,)).fetchone()
            if observed != ("VERIFIED", canonical_json_bytes(receipt)):
                raise TransitionError("provider ledger readback mismatch")
        return receipt


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

    def do_GET(self):
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

    def do_POST(self):
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
        ma = AUTHORITY_EFFECT_RE.match(parsed.path)
        if ma:
            try:
                body = self._read_json()
                recovery.exact(body, {"writer_capability", "permit", "operation"}, "provider request")
                repository = f"{ma.group(1)}/{ma.group(2)}"
                if repository != os.environ.get("QIKVRT_ALLOWED_REPOSITORY", ""):
                    raise TransitionError("repository outside authenticated shim scope")
                path = os.environ.get("QIKVRT_AUTHORITY_CONTROL_PLANE", "")
                if not path or not Path(path).is_absolute():
                    raise TransitionError("existing absolute private control-plane path required")
                adapter = GitHubAuthorityProvider(AuthorityControlPlane(Path(path)), repository)
                result = adapter.execute(body["writer_capability"], body["permit"], body["operation"])
                self._send_json(200, {"status": "CONTINUE", "provider_result": result})
            except (ValueError, TypeError, OSError, RuntimeError):
                # Capabilities and provider error bodies must never be echoed.
                self._send_json(409, {"status": "BLOCK", "effect_ack_done": False})
            return
        if not (m or mr):
            self._send_json(404, {"status": "BLOCK", "reason": "unknown endpoint"})
            return
        try:
            body = self._read_json()
            if m:
                unknown = set(body) - {"ref", "inputs"}
                if unknown:
                    raise ValueError(f"unknown workflow dispatch fields: {sorted(unknown)}")
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
