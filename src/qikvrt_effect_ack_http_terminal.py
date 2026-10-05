#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Loopback-only reference backend for the QIKVRT Firefox terminal.

Experimental HTTP-profile demonstrator. It proves capability discovery,
Structured-Field prepare/commit, exact-bound single-use commit, and post-effect
reobservation without granting repository, publication, deployment, or other
external-effect capability.

The separate durable-* CLI operations are owner-local clients of the existing
TEMDD Unix ingress. They add no HTTP writer and never infer product completion.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import stat
import struct
import subprocess
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MAX_BODY = 2 * 1024 * 1024
TOKEN_TTL_SECONDS = 120
HOST = "127.0.0.1"
DEFAULT_PORT = 8771
SF_KEY = re.compile(r"^[a-z*][a-z0-9_.*-]*$")
MAX_NATIVE_EVENT = 65536
NATIVE_SCHEMA = "qikvrt_temdd_native_event_v1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def parse_sf_bytes(value: str) -> bytes:
    if len(value) < 2 or not (value.startswith(":") and value.endswith(":")):
        raise ValueError("Structured Field Byte Sequence required")
    try:
        return base64.b64decode(value[1:-1], validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("malformed Structured Field Byte Sequence") from exc


def parse_effect_ack_request(raw: str | None) -> dict[str, Any]:
    if raw is None or not raw.strip():
        raise ValueError("Effect-Ack-Request required")
    members: dict[str, str] = {}
    for item in raw.split(","):
        if "=" not in item:
            raise ValueError("malformed Effect-Ack-Request dictionary")
        key, value = item.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not SF_KEY.fullmatch(key) or key in members:
            raise ValueError("invalid or duplicate Effect-Ack-Request member")
        members[key] = value
    if set(members) - {"v", "mode", "token", "hash"}:
        raise ValueError("unknown Effect-Ack-Request member in version 1")
    try:
        version = int(members.get("v", ""))
    except ValueError as exc:
        raise ValueError("Effect-Ack-Request v must be an integer") from exc
    if version != 1:
        raise ValueError("unsupported Effect-Ack-Request version")
    mode = members.get("mode")
    if mode not in {"prepare", "commit"}:
        raise ValueError("Effect-Ack-Request mode must be prepare or commit")
    if mode == "prepare":
        if set(members) != {"v", "mode"}:
            raise ValueError("prepare must not carry token or hash")
        return {"v": 1, "mode": "prepare"}
    if set(members) != {"v", "mode", "token", "hash"}:
        raise ValueError("commit requires token and hash")
    token_bytes = parse_sf_bytes(members["token"])
    try:
        token = token_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("commit token must be ASCII") from exc
    hash_bytes = parse_sf_bytes(members["hash"])
    if len(hash_bytes) != 32:
        raise ValueError("commit hash must contain exactly 32 octets")
    return {"v": 1, "mode": "commit", "token": token, "hash": hash_bytes.hex()}


def git_read(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
    except (OSError, subprocess.SubprocessError):
        return None


class DurableHold(ValueError):
    """The owner-local persistence effect is not verified."""


def durable_subject(root: str, repository: str, pr: int, head: str, tree: str) -> dict[str, Any]:
    """Require a clean, exact checkout; never relabel the running carrier."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise DurableHold("REPOSITORY_REQUIRED")
    if type(pr) is not int or pr < 1 or not all(re.fullmatch(r"[0-9a-f]{40}", x or "") for x in (head, tree)):
        raise DurableHold("EXACT_SUBJECT_REQUIRED")
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", root, *args], text=True,
                                       stderr=subprocess.DEVNULL, timeout=5).strip()
    try:
        if git("rev-parse", "HEAD^{commit}") != head or git("rev-parse", head + "^{tree}") != tree:
            raise DurableHold("EXACT_SUBJECT_MISMATCH")
        if git("remote", "get-url", "origin") not in {f"https://github.com/{repository}", f"https://github.com/{repository}.git"}:
            raise DurableHold("CHECKOUT_REPOSITORY_MISMATCH")
        git("diff", "--quiet", head, "--")
        if git("rev-parse", "HEAD^{commit}") != head:
            raise DurableHold("EXACT_SUBJECT_CHANGED")
    except (OSError, subprocess.SubprocessError) as exc:
        raise DurableHold("EXACT_SUBJECT_UNOBSERVABLE_OR_DIRTY") from exc
    return {"repository": repository, "pr": pr, "head": head, "tree": tree}


def _durable_directory(state_dir: str) -> Path:
    path = Path(state_dir)
    if ".." in path.parts:
        raise DurableHold("UNSAFE_STATE_PATH")
    directory = path.absolute() / "temdd"
    for component in (*reversed(directory.parents), directory):
        if component.is_symlink():
            raise DurableHold("SYMLINK_STATE_PATH")
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise DurableHold("LEDGER_DIRECTORY_MUST_BE_OWNER_ONLY")
    return directory


def _durable_file(directory: Path, name: str, *, is_socket: bool = False) -> Path:
    path = directory / name
    info = path.lstat()
    valid_type = stat.S_ISSOCK(info.st_mode) if is_socket else stat.S_ISREG(info.st_mode)
    if not valid_type or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise DurableHold("UNSAFE_DURABLE_PATH")
    if is_socket and stat.S_IMODE(info.st_mode) != 0o600:
        raise DurableHold("INGRESS_MUST_REMAIN_OWNER_ONLY_0600")
    return path


def _durable_read(state_dir: str, event: dict[str, Any] | None = None) -> tuple[str, dict[str, Any] | None]:
    """Fresh read-only SQLite connection to the existing ledger, never a writer."""
    directory = _durable_directory(state_dir)
    database = _durable_file(directory, "events.sqlite3")
    for name in ("events.sqlite3-wal", "events.sqlite3-shm"):
        if (directory / name).exists() or (directory / name).is_symlink():
            _durable_file(directory, name)
    with contextlib.closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        meta = dict(db.execute("SELECT key,value FROM meta"))
        epoch = meta.get("epoch", "")
        if meta.get("schema") != "1" or not re.fullmatch(r"[0-9a-f]{32}", epoch):
            raise DurableHold("UNKNOWN_LEDGER_SCHEMA")
        if event is None:
            return epoch, None
        provenance = event["provenance"]
        row = db.execute("SELECT seq,binding,native_digest,body,body_digest FROM events WHERE source=? AND native_id=?",
                         (provenance["source"], provenance["native_event_id"])).fetchone()
        if row is None:
            return epoch, None
        seq, binding, native_digest, text, body_digest = row
        body = json.loads(text)
        if not isinstance(body, dict):
            raise DurableHold("DURABLE_BODY_OBJECT_REQUIRED")
        expected = dict(event, schema="qikvrt_temdd_event_v1", recorded_at=body.get("recorded_at"),
                        payload_digest=sha256(canonical_json(event["payload"])), evidence_transfer="DENY", dod=False)
        if (type(seq) is not int or seq < 1 or binding != sha256(canonical_json(event["subject"]))
                or native_digest != sha256(canonical_json(event)) or canonical_json(body) != canonical_json(expected)
                or not isinstance(body.get("recorded_at"), str)
                or body_digest != sha256(canonical_json(body))):
            raise DurableHold("DURABLE_READBACK_MISMATCH")
        return epoch, dict(body, id=f"{epoch}:{seq}", ledger_digest=body_digest)


def _durable_input(body: dict[str, Any]) -> dict[str, Any]:
    body = json.loads(canonical_json(body))  # Freeze caller-owned objects.
    if (not isinstance(body, dict) or body.get("schema") != "qikvrt_terminal_input_v1"
            or set(body) - {"schema", "text", "audio", "video", "page", "submitted_at"}
            or not isinstance(body.get("text"), str) or not 1 <= len(body["text"]) <= 4096
            or body.get("audio") is not None or body.get("video") is not None
            or len(canonical_json(body)) > MAX_NATIVE_EVENT // 2):
        raise DurableHold("BOUNDED_TEXT_INPUT_REQUIRED_MEDIA_NOT_ADMITTED")
    return body


def durable_prepare(body: dict[str, Any], subject: dict[str, Any], state_dir: str) -> dict[str, Any]:
    """Prepare an owner-local observation; insert no event and expose no HTTP route."""
    body = _durable_input(body)
    subject = json.loads(canonical_json(subject))
    if (set(subject) != {"repository", "pr", "head", "tree"} or type(subject["pr"]) is not int or subject["pr"] < 1
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", subject["repository"])
            or not all(re.fullmatch(r"[0-9a-f]{40}", subject[x]) for x in ("head", "tree"))):
        raise DurableHold("EXACT_SUBJECT_REQUIRED")
    directory = _durable_directory(state_dir)
    _durable_file(directory, "ingress.sock", is_socket=True)
    epoch, _ = _durable_read(state_dir)
    input_hash = "sha256:" + sha256(canonical_json(body))
    event = {"schema": NATIVE_SCHEMA, "kind": "OBSERVE", "subject": subject,
             "provenance": {"source": "transputer", "native_event_id": "terminal:" + secrets.token_hex(24)},
             "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "message": "Universal Terminal: hash-bound durable input observation",
             "payload": {"adapter": "QIKVRT_OWNER_UNIX_TERMINAL_V1", "terminal_input": body,
                         "input_hash": input_hash, "effect_ack_done": False}}
    plan = {"schema": "qikvrt_owner_unix_terminal_preparation_v1", "subject": subject, "event": event,
            "input_hash": input_hash, "ledger_id": epoch, "state_directory": str(directory.parent),
            "expires_at": int(time.time()) + TOKEN_TTL_SECONDS}
    return {"state": "PREPARED", "preparation": plan, "prepare_hash": "sha256:" + sha256(canonical_json(plan)),
            "ordinary_release": False, "EFFECT_ACK_DONE": False}


def _durable_plan(prepared: dict[str, Any], expected_hash: str, body: dict[str, Any],
                  subject: dict[str, Any], state_dir: str) -> dict[str, Any]:
    if (set(prepared) != {"state", "preparation", "prepare_hash", "ordinary_release", "EFFECT_ACK_DONE"}
            or prepared["state"] != "PREPARED" or prepared["ordinary_release"] is not False
            or prepared["EFFECT_ACK_DONE"] is not False):
        raise DurableHold("INVALID_PREPARATION")
    plan = prepared["preparation"]
    digest = "sha256:" + sha256(canonical_json(plan))
    if not hmac.compare_digest(digest, expected_hash) or prepared["prepare_hash"] != digest:
        raise DurableHold("PREPARE_HASH_MISMATCH")
    if (set(plan) != {"schema", "subject", "event", "input_hash", "ledger_id", "state_directory", "expires_at"}
            or plan["schema"] != "qikvrt_owner_unix_terminal_preparation_v1"
            or canonical_json(plan["subject"]) != canonical_json(subject)
            or plan["state_directory"] != str(_durable_directory(state_dir).parent)):
        raise DurableHold("PREPARED_SUBJECT_OR_ROUTE_MISMATCH")
    frozen = _durable_input(body)
    event = plan["event"]
    if (plan["input_hash"] != "sha256:" + sha256(canonical_json(frozen))
            or event.get("subject") != subject or event.get("schema") != NATIVE_SCHEMA or event.get("kind") != "OBSERVE"
            or event.get("payload") != {"adapter": "QIKVRT_OWNER_UNIX_TERMINAL_V1", "terminal_input": frozen,
                                       "input_hash": plan["input_hash"], "effect_ack_done": False}
            or event.get("provenance", {}).get("source") != "transputer"
            or not re.fullmatch(r"terminal:[0-9a-f]{48}", event.get("provenance", {}).get("native_event_id", ""))
            or len(canonical_json(event)) > MAX_NATIVE_EVENT):
        raise DurableHold("PREPARED_INPUT_MISMATCH")
    return plan


def durable_readback(prepared: dict[str, Any], expected_hash: str, body: dict[str, Any],
                     subject: dict[str, Any], state_dir: str) -> dict[str, Any]:
    """May recover an ambiguous commit after expiry/restart, without resubmission."""
    plan = _durable_plan(prepared, expected_hash, body, subject, state_dir)
    epoch, event = _durable_read(state_dir, plan["event"])
    if epoch != plan["ledger_id"] or event is None:
        raise DurableHold("DURABLE_EVENT_NOT_OBSERVED_IN_PREPARED_LEDGER")
    return {"state": "EFFECT_ACK_CONTINUE", "durable_persisted": True, "durable_readback": event,
            "prepare_hash": expected_hash, "ordinary_release": False, "EFFECT_ACK_DONE": False,
            "public_readback_verified": False, "authority_effect": False}


def durable_commit(prepared: dict[str, Any], expected_hash: str, body: dict[str, Any],
                   subject: dict[str, Any], state_dir: str) -> dict[str, Any]:
    plan = _durable_plan(prepared, expected_hash, body, subject, state_dir)
    if type(plan["expires_at"]) is not int or plan["expires_at"] < time.time():
        raise DurableHold("EXPIRED_PREPARATION")
    epoch, old = _durable_read(state_dir, plan["event"])
    if epoch != plan["ledger_id"]:
        raise DurableHold("PREPARED_LEDGER_CHANGED")
    if old is not None:
        raise DurableHold("PREPARATION_ALREADY_COMMITTED_USE_READBACK")
    path = _durable_file(_durable_directory(state_dir), "ingress.sock", is_socket=True)
    if not hasattr(socket, "SO_PEERCRED"):
        raise DurableHold("UNIX_PEER_UID_VERIFICATION_REQUIRED")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(str(path))
        _, uid, _ = struct.unpack("3i", client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
        if uid != os.geteuid():
            raise DurableHold("INGRESS_PEER_OWNER_MISMATCH")
        client.sendall(canonical_json(plan["event"]) + b"\n")
        with client.makefile("rb") as response:
            raw = response.readline(MAX_NATIVE_EVENT * 2 + 2)
        if len(raw) > MAX_NATIVE_EVENT * 2 + 1 or not raw.endswith(b"\n"):
            raise DurableHold("AMBIGUOUS_COMMIT_USE_READBACK_DO_NOT_RESUBMIT")
        reply = json.loads(raw)
    if not isinstance(reply, dict):
        raise DurableHold("INGRESS_REPLY_OBJECT_REQUIRED_USE_READBACK")
    if reply.get("state") != "PERSISTED" or reply.get("dod") is not False or reply.get("authority_effect") is not False:
        raise DurableHold("INGRESS_DID_NOT_QUIT_DURABLE_EFFECT")
    receipt = durable_readback(prepared, expected_hash, body, subject, state_dir)
    if canonical_json(reply.get("event")) != canonical_json(receipt["durable_readback"]):
        raise DurableHold("INGRESS_REPLY_DIFFERS_FROM_FRESH_DURABLE_READBACK")
    return receipt


@dataclass
class Prepared:
    token: str
    input_hash: str
    record_hash: str
    expires_at: float
    used: bool = False


class State:
    def __init__(self) -> None:
        self.secret = secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.prepared: dict[str, Prepared] = {}
        self.records: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []

    def record(self, *, state: str, input_hash: str, ordinary_release: bool, reason: str) -> tuple[str, dict[str, Any]]:
        body = {
            "schema": "qikvrt_effect_ack_http_terminal_record_v1",
            "wire_version": 1,
            "message_type": "effect-ack-record",
            "state": state,
            "input_hash": "sha256:" + input_hash,
            "policy_id": "QIKVRT_LOOPBACK_TERMINAL_V1",
            "policy_version": 1,
            "policy_allows_release": ordinary_release,
            "ordinary_release": ordinary_release,
            "responsibility_owner": "LOCAL_INTERACTIVE_USER",
            "reason": reason,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "external_effect": "NONE",
        }
        digest = sha256(canonical_json(body))
        body["record_hash"] = "sha256:" + digest
        self.records[digest] = body
        return digest, body

    def make_token(self, input_hash: str, record_hash: str) -> str:
        nonce = secrets.token_bytes(24)
        expires = int(time.time()) + TOKEN_TTL_SECONDS
        payload = nonce + expires.to_bytes(8, "big") + bytes.fromhex(input_hash) + bytes.fromhex(record_hash)
        mac = hmac.new(self.secret, payload, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(payload + mac).decode("ascii").rstrip("=")
        self.prepared[token] = Prepared(token, input_hash, record_hash, float(expires))
        return token


STATE = State()


class Handler(BaseHTTPRequestHandler):
    server_version = "QIKVRTEffectAckTerminal/1.0"

    def _json(
        self,
        code: int,
        body: dict[str, Any],
        *,
        state: str | None = None,
        record_hash: str | None = None,
        commit_token: str | None = None,
    ) -> None:
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "https://github.com")
        self.send_header("Access-Control-Expose-Headers", "Effect-Ack, Link")
        self.send_header("Link", "</.well-known/effect-ack>; rel=\"effect-ack\"; type=\"application/json\"")
        if state and record_hash:
            state_token = {
                "EFFECT_NACK": "nack",
                "EFFECT_ACK_CONTINUE": "continue",
                "EFFECT_ACK_DONE": "done",
                "EFFECT_ACK_ISOLATE": "isolate",
                "EFFECT_ACK_BLOCK": "block",
            }[state]
            value = f"v=1, state={state_token}, hash={sf_bytes(bytes.fromhex(record_hash))}"
            if commit_token is not None:
                value += f", token={sf_bytes(commit_token.encode('ascii'))}"
            self.send_header("Effect-Ack", value)
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Transfer-Encoding unsupported")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length required")
        length = int(raw_length)
        if length < 1 or length > MAX_BODY:
            raise ValueError("body outside bounded size")
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("application/json required")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "https://github.com")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Effect-Ack-Request")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/.well-known/effect-ack":
            self._json(200, {
                "schema": "qikvrt_effect_ack_http_capability_v1",
                "versions": [1],
                "modes": ["prepare", "commit"],
                "protected_effects": ["terminal_input"],
                "external_effects": "NONE",
                "record_template": "/effect-ack/records/{sha256}",
            })
            return
        if self.path == "/terminal/state":
            head = git_read("rev-parse", "HEAD")
            tree = git_read("rev-parse", "HEAD^{tree}")
            with STATE.lock:
                body = {
                    "schema": "qikvrt_terminal_backend_state_v1",
                    "events": len(STATE.events),
                    "last_event": STATE.events[-1] if STATE.events else None,
                    "repository_head": head,
                    "repository_tree": tree,
                    "external_effects": "NONE",
                }
            self._json(200, body)
            return
        prefix = "/effect-ack/records/"
        if self.path.startswith(prefix):
            digest = self.path[len(prefix):]
            with STATE.lock:
                body = STATE.records.get(digest)
            if body is None:
                self._json(404, {"state": "HOLD", "reason": "record not found"})
            else:
                self._json(200, body, state=body["state"], record_hash=digest)
            return
        self._json(404, {"state": "HOLD", "reason": "not found"})

    def do_POST(self) -> None:
        try:
            request_binding = parse_effect_ack_request(self.headers.get("Effect-Ack-Request"))
            body = self._read_body()
            if self.path == "/terminal/prepare":
                if request_binding["mode"] != "prepare":
                    raise ValueError("prepare endpoint requires mode=prepare")
                self._prepare(body)
                return
            if self.path == "/terminal/commit":
                if request_binding["mode"] != "commit":
                    raise ValueError("commit endpoint requires mode=commit")
                self._commit(body, request_binding)
                return
            self._json(404, {"state": "HOLD", "reason": "not found"})
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self._json(400, {"state": "HOLD", "ordinary_release": False, "reason": str(exc)})

    def _prepare(self, body: dict[str, Any]) -> None:
        if body.get("schema") != "qikvrt_terminal_input_v1":
            digest, record = STATE.record(
                state="EFFECT_ACK_BLOCK",
                input_hash=sha256(canonical_json(body)),
                ordinary_release=False,
                reason="unsupported terminal schema",
            )
            self._json(422, {"record": record, "record_hash": digest}, state=record["state"], record_hash=digest)
            return
        input_hash = sha256(canonical_json(body))
        with STATE.lock:
            digest, record = STATE.record(
                state="EFFECT_ACK_DONE",
                input_hash=input_hash,
                ordinary_release=True,
                reason="loopback terminal input satisfies bounded local policy",
            )
            token = STATE.make_token(input_hash, digest)
        response = {
            "state": "EFFECT_ACK_DONE",
            "ordinary_release": False,
            "commit_token": token,
            "record_hash": digest,
            "record_url": f"/effect-ack/records/{digest}",
            "expires_in_seconds": TOKEN_TTL_SECONDS,
            "external_effect": "NONE",
        }
        self._json(200, response, state="EFFECT_ACK_DONE", record_hash=digest, commit_token=token)

    def _commit(self, body: dict[str, Any], binding: dict[str, Any]) -> None:
        token = binding["token"]
        record_hash = binding["hash"]
        commit_input_hash = sha256(canonical_json(body))
        with STATE.lock:
            prepared = STATE.prepared.get(token)
            if prepared is None or prepared.used or prepared.expires_at < time.time() or not hmac.compare_digest(prepared.record_hash, record_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "invalid stale used or mismatched token"})
                return
            if not hmac.compare_digest(prepared.input_hash, commit_input_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "commit payload differs from exact prepared payload"})
                return
            prepared.used = True
            event = {
                "event_id": len(STATE.events) + 1,
                "kind": "TERMINAL_INPUT_ACCEPTED",
                "record_hash": record_hash,
                "input_hash": commit_input_hash,
                "text": str(body.get("text", ""))[:4096],
                "audio_present": body.get("audio") is not None,
                "video_present": body.get("video") is not None,
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "external_effect": "NONE",
            }
            STATE.events.append(event)
            digest, record = STATE.record(
                state="EFFECT_ACK_DONE",
                input_hash=prepared.input_hash,
                ordinary_release=True,
                reason="single-use exact-bound loopback commit executed",
            )
        self._json(
            200,
            {"state": "EFFECT_ACK_DONE", "ordinary_release": True, "post_effect": event, "successor_record": record},
            state="EFFECT_ACK_DONE",
            record_hash=digest,
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", nargs="?", default="serve", choices=("serve", "durable-prepare", "durable-commit", "durable-readback"))
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--state-dir", default="/var/lib/qikvrt/state")
    parser.add_argument("--root", default=".")
    parser.add_argument("--repository")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-tree")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--prepare-hash")
    args = parser.parse_args()
    if args.operation != "serve":
        try:
            if not all((args.repository, args.pr, args.expected_head, args.expected_tree, args.input)):
                raise DurableHold("EXACT_SUBJECT_AND_INPUT_REQUIRED")
            subject = durable_subject(args.root, args.repository, args.pr, args.expected_head, args.expected_tree)
            def load(path: Path) -> dict[str, Any]:
                with path.open("rb") as source:
                    raw = source.read(MAX_NATIVE_EVENT * 2 + 1)
                if len(raw) > MAX_NATIVE_EVENT * 2:
                    raise DurableHold("BOUNDED_FILE_REQUIRED")
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise DurableHold("JSON_OBJECT_REQUIRED")
                return value
            body = load(args.input)
            if args.operation == "durable-prepare":
                result = durable_prepare(body, subject, args.state_dir)
            else:
                if not args.prepared or not args.prepare_hash:
                    raise DurableHold("EXACT_PREPARE_HASH_REQUIRED")
                operation = durable_commit if args.operation == "durable-commit" else durable_readback
                result = operation(load(args.prepared), args.prepare_hash, body, subject, args.state_dir)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        except (OSError, ValueError, sqlite3.Error, TypeError, KeyError, RecursionError) as exc:
            print(json.dumps({"state": "HOLD", "reason": str(exc), "EFFECT_ACK_DONE": False,
                              "ordinary_release": False, "next_action": "READBACK_BEFORE_ANY_COMMIT_RETRY"}, sort_keys=True))
            return 2
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: reference terminal bridge is loopback-only")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(json.dumps({"state": "READY", "host": args.host, "port": args.port, "external_effects": "NONE"}, sort_keys=True), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
