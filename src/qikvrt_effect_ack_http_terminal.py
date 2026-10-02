#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Loopback-only reference backend for the QIKVRT Firefox terminal.

Experimental HTTP-profile demonstrator. It proves capability discovery,
Structured-Field prepare/commit, exact-bound single-use commit, and post-effect
reobservation without granting repository, publication, deployment, or other
external-effect capability.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

MAX_BODY = 2 * 1024 * 1024
TOKEN_TTL_SECONDS = 120
HOST = "127.0.0.1"
DEFAULT_PORT = 8771
CANONICAL_SEED_SHA256 = "27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792"
MAX_EVENTS = 4096
MAX_STATE_BYTES = 64 * 1024 * 1024
STATE_SCHEMA = "qikvrt_effect_ack_http_terminal_state_v1"
SF_KEY = re.compile(r"^[a-z*][a-z0-9_.*-]*$")


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


@dataclass
class Prepared:
    token: str
    input_hash: str
    record_hash: str
    expires_at: float
    used: bool = False


class PersistenceError(RuntimeError):
    """Durability is unavailable or ambiguous; no further admission is safe."""


class State:
    def __init__(self, seed_path: Path | None = None, state_path: Path | None = None,
                 *, state_root: Path | None = None) -> None:
        if state_path is not None and state_root is not None:
            raise ValueError("choose state_path or state_root")
        self.seed_path = seed_path
        self.seed_binding = self.validate_seed()
        self.secret = secrets.token_bytes(32)
        self.lock = threading.RLock()
        self.prepared: dict[str, Prepared] = {}
        self.records: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.persistence_failed = False
        self.store = None
        self.store_lock = None
        self.persistence_scope = "PROCESS_LIFETIME_ONLY"
        if state_root is not None or state_path is not None:
            if os.name != "posix":
                raise PersistenceError("DURABLE_TERMINAL_REQUIRES_POSIX_API_PERSISTENCE")
            # Reuse the API handler's sole durable-state root, strict reader,
            # atomic file+directory fsync writer and interprocess lock.
            import qikvrt_api_handler as persistence
            self.persistence = persistence
            # Retain the existing explicit --state file interface. Both forms
            # use the same writer/validator and a lock in the API state root.
            root = state_root if state_root is not None else state_path.absolute().parent
            paths = persistence.dirs(root)
            lock_name = "terminal.lock" if state_path is None else (
                "terminal-" + sha256(str(state_path.absolute()).encode("utf-8"))[:16] + ".lock")
            initialized = (paths["state"] / lock_name).exists()
            self.store_lock = persistence.process_lock(root, name=lock_name, blocking=False)
            try:
                self.store_lock.__enter__()
                self.store = paths["state"] / "terminal.json" if state_path is None else state_path.absolute()
                if self.store.exists() or self.store.is_symlink():
                    self._restore()
                else:
                    if initialized:
                        raise PersistenceError("DURABLE_TERMINAL_STATE_MISSING_NO_AUTOMATIC_RESET")
                    self.persist()
                self.persistence_scope = "FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE"
            except BaseException:
                self.close()
                raise

    def close(self) -> None:
        if self.store_lock is not None:
            self.store_lock.__exit__(None, None, None)
            self.store_lock = None

    def persist(self) -> None:
        """Publish record/event/token state together, before any positive reply.

        Called under the HTTP state lock. If replacement or fsync fails, its
        outcome may be ambiguous: poison the process, never roll back/retry it.
        Only a validated restart may recover the last complete snapshot.
        """
        if self.persistence_failed:
            raise PersistenceError("DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED")
        if self.store is None:
            return
        snapshot = {"schema": STATE_SCHEMA, "seed_binding": self.seed_binding,
                    "secret": self.secret.hex(), "records": self.records,
                    "events": self.events,
                    "prepared": {token: asdict(value) for token, value in self.prepared.items()}}
        try:
            self.validate_seed()
            snapshot["state_sha256"] = sha256(canonical_json(snapshot))
            data = canonical_json(snapshot) + b"\n"
            if len(data) > MAX_STATE_BYTES:
                raise ValueError("bounded terminal state capacity reached")
            self.persistence.atomic_write_bytes(self.store, data)
        except (OSError, ValueError, self.persistence.IntegrityIsolationError) as exc:
            self.persistence_failed = True
            raise PersistenceError("DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED") from exc

    def _restore(self) -> None:
        try:
            raw = self.persistence.secure_read_bytes(self.store, max_bytes=MAX_STATE_BYTES)
            snapshot = self.persistence._strict_json_loads(raw)
            required = {"schema", "seed_binding", "secret", "records", "events", "prepared", "state_sha256"}
            if not isinstance(snapshot, dict) or set(snapshot) != required:
                raise ValueError("invalid terminal state schema")
            if raw != canonical_json(snapshot) + b"\n":
                raise ValueError("noncanonical or truncated terminal state")
            claimed = snapshot.pop("state_sha256")
            if claimed != sha256(canonical_json(snapshot)) or snapshot["schema"] != STATE_SCHEMA:
                raise ValueError("terminal state integrity mismatch")
            if snapshot["seed_binding"] != self.seed_binding:
                raise ValueError("terminal restart seed binding mismatch")
            secret = bytes.fromhex(snapshot["secret"])
            records, events, values = snapshot["records"], snapshot["events"], snapshot["prepared"]
            if (len(secret) != 32 or not isinstance(records, dict) or not isinstance(values, dict)
                    or not isinstance(events, list) or len(events) > MAX_EVENTS):
                raise ValueError("invalid or over-capacity terminal state")
            for digest, record in records.items():
                projection = {key: value for key, value in record.items() if key != "record_hash"}
                if (sha256(canonical_json(projection)) != digest or record.get("record_hash") != "sha256:" + digest
                        or record.get("schema") != "qikvrt_effect_ack_http_terminal_record_v1"
                        or record.get("seed_binding") != self.seed_binding):
                    raise ValueError("terminal record integrity or seed mismatch")
            prepared = {}
            for token, value in values.items():
                item = Prepared(**value)
                decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
                if (item.token != token or type(item.used) is not bool or len(decoded) != 128
                        or base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != token
                        or not hmac.compare_digest(decoded[-32:], hmac.new(secret, decoded[:-32], hashlib.sha256).digest())
                        or item.expires_at != int.from_bytes(decoded[24:32], "big")
                        or item.input_hash != decoded[32:64].hex() or item.record_hash != decoded[64:96].hex()
                        or item.record_hash not in records
                        or records[item.record_hash]["input_hash"] != "sha256:" + item.input_hash):
                    raise ValueError("terminal prepared token binding mismatch")
                prepared[token] = item
            consumed = {sha256(token.encode("ascii")): item for token, item in prepared.items() if item.used}
            seen = set()
            for index, event in enumerate(events, 1):
                token_hash = event["commit_token_sha256"]
                item = consumed.get(token_hash)
                successor = records.get(event["effect_record_hash"], {})
                if (type(event["event_id"]) is not int or event["event_id"] != index
                        or item is None or token_hash in seen or event["record_hash"] != item.record_hash
                        or event["input_hash"] != item.input_hash or event.get("seed_binding") != self.seed_binding
                        or event["kind"] != "TERMINAL_INPUT_ACCEPTED" or event["external_effect"] != "NONE"
                        or successor.get("input_hash") != "sha256:" + item.input_hash
                        or successor.get("state") != "EFFECT_ACK_DONE"):
                    raise ValueError("terminal event order or consumption mismatch")
                seen.add(token_hash)
            if seen != set(consumed):
                raise ValueError("terminal consumed token/event mismatch")
            self.secret, self.records, self.events, self.prepared = secret, records, events, prepared
        except (OSError, ValueError, TypeError, KeyError, AttributeError,
                self.persistence.IntegrityIsolationError) as exc:
            raise PersistenceError("DURABLE_TERMINAL_STATE_INVALID_OR_SEED_MISMATCH") from exc

    def validate_seed(self) -> dict[str, Any] | None:
        if self.seed_path is None:
            return None  # Backward-compatible unseeded HTTP profile; no seed proof.
        try:
            data = self.seed_path.read_bytes()
        except OSError as exc:
            raise ValueError("SEED_UNAVAILABLE") from exc
        if len(data) != 400 or not hmac.compare_digest(sha256(data), CANONICAL_SEED_SHA256):
            raise ValueError("CANONICAL_400_BYTE_SEED_MISMATCH")
        return {"bytes": 400, "sha256": CANONICAL_SEED_SHA256,
                "effect_scope": "LOCAL_TERMINAL_ADMISSION_GATE_ONLY",
                "seed_alone_builds_operating_system": False}

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
        if self.seed_binding is not None:
            body["seed_binding"] = self.seed_binding
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
        # Check poison and select the readback in the same critical section:
        # a concurrent failed fsync must not expose unconfirmed cached events.
        with STATE.lock:
            self._get()

    def _get(self) -> None:
        if STATE.persistence_failed:
            self._json(503, {"state": "HOLD", "ordinary_release": False,
                             "reason": "DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED"})
            return
        if self.path == "/.well-known/effect-ack":
            self._json(200, {
                "schema": "qikvrt_effect_ack_http_capability_v1",
                "versions": [1],
                "modes": ["prepare", "commit"],
                "protected_effects": ["terminal_input"],
                "external_effects": "NONE",
                "record_template": "/effect-ack/records/{sha256}",
                "seed_binding": STATE.seed_binding,
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
                    "seed_binding": STATE.seed_binding,
                    "persistence_scope": STATE.persistence_scope,
                }
            self._json(200, body)
            return
        if self.path == "/terminal/events":
            with STATE.lock:
                events = [dict(event) for event in STATE.events]
            self._json(200, {"schema": "qikvrt_terminal_event_snapshot_v1",
                             "events": events, "event_count": len(events),
                             "events_sha256": sha256(canonical_json(events)),
                             "seed_binding": STATE.seed_binding,
                             "persistence_scope": STATE.persistence_scope})
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
            if STATE.persistence_failed:
                raise PersistenceError("DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED")
            STATE.validate_seed()
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
        except PersistenceError as exc:
            self._json(503, {"state": "HOLD", "ordinary_release": False, "reason": str(exc)})

    def _prepare(self, body: dict[str, Any]) -> None:
        if body.get("schema") != "qikvrt_terminal_input_v1":
            with STATE.lock:
                digest, record = STATE.record(
                    state="EFFECT_ACK_BLOCK",
                    input_hash=sha256(canonical_json(body)),
                    ordinary_release=False,
                    reason="unsupported terminal schema",
                )
                STATE.persist()
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
            STATE.persist()
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
            if STATE.persistence_failed:
                raise PersistenceError("DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED")
            STATE.validate_seed()
            prepared = STATE.prepared.get(token)
            if prepared is None or prepared.used or prepared.expires_at < time.time() or not hmac.compare_digest(prepared.record_hash, record_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "invalid stale used or mismatched token"})
                return
            if not hmac.compare_digest(prepared.input_hash, commit_input_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "commit payload differs from exact prepared payload"})
                return
            if len(STATE.events) >= MAX_EVENTS:
                self._json(409, {"state": "HOLD", "ordinary_release": False,
                                 "reason": "bounded terminal event capacity reached"})
                return
            prepared.used = True
            digest, record = STATE.record(
                state="EFFECT_ACK_DONE",
                input_hash=prepared.input_hash,
                ordinary_release=True,
                reason="single-use exact-bound loopback commit executed",
            )
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
                "seed_binding": STATE.seed_binding,
                "commit_token_sha256": sha256(token.encode("ascii")),
                "effect_record_hash": digest,
            }
            STATE.events.append(event)
            STATE.persist()
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
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--seed", type=Path,
                        help="Require the unchanged canonical 400-byte seed before local admission")
    parser.add_argument("--state-root", type=Path, default=Path.cwd() if os.name == "posix" else None,
                        help="POSIX durable API state root; uses .qikvrt/api/terminal.json")
    parser.add_argument("--state", type=Path,
                        help="Explicit durable state file; uses the same API persistence path")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: reference terminal bridge is loopback-only")
    global STATE
    STATE = State(args.seed, args.state) if args.state is not None else State(args.seed, state_root=args.state_root)
    try:
        with ThreadingHTTPServer((args.host, args.port), Handler) as server:
            print(json.dumps({"state": "READY", "host": args.host, "port": server.server_port,
                              "persistence_scope": STATE.persistence_scope, "external_effects": "NONE"}, sort_keys=True), flush=True)
            server.serve_forever()
    finally:
        STATE.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
