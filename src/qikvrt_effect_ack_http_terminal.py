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
import contextlib
import errno
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import subprocess
import threading
import time
from contextlib import ExitStack
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


class WindowsTerminalPersistence:
    """Native Windows I/O adapter for the existing bounded State snapshot.

    The POSIX API adapter cannot load on Windows (fcntl, directory fsync).
    Keep the snapshot, validators and admission logic shared; replace only I/O.
    Process-crash evidence does not establish power-loss durability.
    """
    IntegrityIsolationError = PersistenceError

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.security = ctypes.WinDLL("advapi32", use_last_error=True)
        signatures = {
            "CreateFileW": ([wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                             wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                             wintypes.HANDLE], wintypes.HANDLE),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
            "GetFileInformationByHandleEx": ([wintypes.HANDLE, ctypes.c_int,
                                              wintypes.LPVOID, wintypes.DWORD], wintypes.BOOL),
            "MoveFileExW": ([wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD], wintypes.BOOL),
            "GetDriveTypeW": ([wintypes.LPCWSTR], wintypes.UINT),
            "LocalFree": ([wintypes.HLOCAL], wintypes.HLOCAL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = arguments, result
        self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID), wintypes.LPVOID]
        self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
        self.security.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID]
        self.security.SetFileSecurityW.restype = wintypes.BOOL

    def _open(self, path, *, directory=False, create=False, write=False):
        # No share-delete: a held directory/lock cannot be renamed or replaced.
        # OPEN_REPARSE_POINT also rejects a junction/symlink at the final path.
        access = 0x80 if directory else (0xc0000000 if write else 0x80000000)
        handle = self.api.CreateFileW(str(path), access, 3 if directory else 0, None,
                                     4 if create else 3,
                                     0x00200000 | (0x02000000 if directory else 0), None)
        if handle == self.ctypes.c_void_p(-1).value:
            error = self.ctypes.get_last_error()
            if create and error == 32:
                raise BlockingIOError(errno.EWOULDBLOCK, "terminal state already owned")
            raise self.ctypes.WinError(error)
        try:
            attributes = (self.ctypes.c_ulong * 2)()  # FILE_ATTRIBUTE_TAG_INFO
            if not self.api.GetFileInformationByHandleEx(handle, 9, attributes, self.ctypes.sizeof(attributes)):
                raise self.ctypes.WinError(self.ctypes.get_last_error())
            if attributes[0] & 0x400 or bool(attributes[0] & 0x10) != directory:
                raise PersistenceError("WINDOWS_STATE_REPARSE_OR_FILE_TYPE_REFUSED")
            return handle
        except BaseException:
            self.api.CloseHandle(handle)
            raise

    @contextlib.contextmanager
    def _directories(self, path):
        handles = []
        try:
            for parent in reversed((path, *path.parents)):
                handles.append(self._open(parent, directory=True))
            yield
        finally:
            for handle in reversed(handles):
                self.api.CloseHandle(handle)

    def _private(self, path):
        # A protected inheritable DACL: only the object owner and LocalSystem.
        descriptor = self.ctypes.c_void_p()
        if not self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                "D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)", 1, self.ctypes.byref(descriptor), None):
            raise self.ctypes.WinError(self.ctypes.get_last_error())
        try:
            if not self.security.SetFileSecurityW(str(path), 0x80000004, descriptor):
                raise self.ctypes.WinError(self.ctypes.get_last_error())
        finally:
            self.api.LocalFree(descriptor)

    def dirs(self, root):
        root = root.absolute()
        if self.api.GetDriveTypeW(root.anchor) != 3:
            raise PersistenceError("WINDOWS_STATE_REQUIRES_LOCAL_FIXED_VOLUME")
        # Pin existing ancestors before creating each successive directory.
        for path in reversed((root, *root.parents)):
            if path == path.parent:
                continue
            with self._directories(path.parent):
                path.mkdir(exist_ok=True)
                handle = self._open(path, directory=True)
                self.api.CloseHandle(handle)
        state = root / ".qikvrt" / "api"
        for path in (state.parent, state):
            with self._directories(path.parent):
                path.mkdir(exist_ok=True)
                handle = self._open(path, directory=True)
                self.api.CloseHandle(handle)
        with self._directories(state):
            self._private(state)
        return {"state": state}

    @contextlib.contextmanager
    def process_lock(self, root, *, name, blocking=False):
        if blocking:
            raise PersistenceError("WINDOWS_TERMINAL_LOCK_MUST_BE_NONBLOCKING")
        state = self.dirs(root)["state"]
        with self._directories(state):
            handle = self._open(state / name, create=True, write=True)
            try:
                yield
            finally:
                self.api.CloseHandle(handle)

    def secure_read_bytes(self, path, *, max_bytes):
        import msvcrt
        with self._directories(path.parent):
            handle = self._open(path)
            try:
                fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except BaseException:
                self.api.CloseHandle(handle)
                raise
            with os.fdopen(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
                    raise PersistenceError("WINDOWS_STATE_FILE_SIZE_OR_TYPE_REFUSED")
                data = stream.read(max_bytes + 1)
                after = os.fstat(stream.fileno())
                if (len(data) > max_bytes or (before.st_ino, before.st_size, before.st_mtime_ns) !=
                        (after.st_ino, after.st_size, after.st_mtime_ns)):
                    raise PersistenceError("WINDOWS_STATE_CHANGED_DURING_READ")
                return data

    def atomic_write_bytes(self, path, data):
        import tempfile
        with self._directories(path.parent):
            if path.exists() or path.is_symlink():
                handle = self._open(path)
                self.api.CloseHandle(handle)
            fd, name = tempfile.mkstemp(prefix=".terminal-", suffix=".tmp", dir=path.parent)
            temporary = Path(name)
            try:
                with os.fdopen(fd, "wb") as stream:
                    self._private(temporary)
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())  # Windows CRT _commit / FlushFileBuffers.
                if not self.api.MoveFileExW(str(temporary), str(path), 0x1 | 0x8):
                    raise self.ctypes.WinError(self.ctypes.get_last_error())
            finally:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _strict_json_loads(data):
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        def reject(value):
            raise ValueError("nonfinite JSON number")
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject)


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
            # Reuse the API handler's sole durable-state root, strict reader,
            # snapshot validator and POSIX I/O; Windows uses native I/O only.
            if os.name == "nt":
                persistence = WindowsTerminalPersistence()
            elif os.name == "posix":
                import qikvrt_api_handler as persistence
            else:
                raise PersistenceError("DURABLE_TERMINAL_PLATFORM_UNSUPPORTED")
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

    @property
    def state(self) -> State:
        return getattr(self, "node_state", getattr(self.server, "state", STATE))

    @property
    def path_prefix(self) -> str:
        return getattr(self, "node_prefix", "")

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
        self.send_header("Link", f'<{self.path_prefix}/.well-known/effect-ack>; rel="effect-ack"; type="application/json"')
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
        with self.state.lock:
            self._get()

    def _get(self) -> None:
        if self.state.persistence_failed:
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
                "record_template": self.path_prefix + "/effect-ack/records/{sha256}",
                "seed_binding": self.state.seed_binding,
            })
            return
        if self.path == "/terminal/state":
            head = git_read("rev-parse", "HEAD")
            tree = git_read("rev-parse", "HEAD^{tree}")
            with self.state.lock:
                body = {
                    "schema": "qikvrt_terminal_backend_state_v1",
                    "events": len(self.state.events),
                    "last_event": self.state.events[-1] if self.state.events else None,
                    "repository_head": head,
                    "repository_tree": tree,
                    "external_effects": "NONE",
                    "seed_binding": self.state.seed_binding,
                    "persistence_scope": self.state.persistence_scope,
                }
            self._json(200, body)
            return
        if self.path == "/terminal/events":
            with self.state.lock:
                events = [dict(event) for event in self.state.events]
            self._json(200, {"schema": "qikvrt_terminal_event_snapshot_v1",
                             "events": events, "event_count": len(events),
                             "events_sha256": sha256(canonical_json(events)),
                             "seed_binding": self.state.seed_binding,
                             "persistence_scope": self.state.persistence_scope})
            return
        prefix = "/effect-ack/records/"
        if self.path.startswith(prefix):
            digest = self.path[len(prefix):]
            with self.state.lock:
                body = self.state.records.get(digest)
            if body is None:
                self._json(404, {"state": "HOLD", "reason": "record not found"})
            else:
                self._json(200, body, state=body["state"], record_hash=digest)
            return
        self._json(404, {"state": "HOLD", "reason": "not found"})

    def do_POST(self) -> None:
        try:
            if self.state.persistence_failed:
                raise PersistenceError("DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED")
            self.state.validate_seed()
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
            with self.state.lock:
                digest, record = self.state.record(
                    state="EFFECT_ACK_BLOCK",
                    input_hash=sha256(canonical_json(body)),
                    ordinary_release=False,
                    reason="unsupported terminal schema",
                )
                self.state.persist()
            self._json(422, {"record": record, "record_hash": digest}, state=record["state"], record_hash=digest)
            return
        input_hash = sha256(canonical_json(body))
        with self.state.lock:
            digest, record = self.state.record(
                state="EFFECT_ACK_DONE",
                input_hash=input_hash,
                ordinary_release=True,
                reason="loopback terminal input satisfies bounded local policy",
            )
            token = self.state.make_token(input_hash, digest)
            self.state.persist()
        response = {
            "state": "EFFECT_ACK_DONE",
            "ordinary_release": False,
            "commit_token": token,
            "record_hash": digest,
            "record_url": f"{self.path_prefix}/effect-ack/records/{digest}",
            "expires_in_seconds": TOKEN_TTL_SECONDS,
            "external_effect": "NONE",
        }
        self._json(200, response, state="EFFECT_ACK_DONE", record_hash=digest, commit_token=token)

    def _commit(self, body: dict[str, Any], binding: dict[str, Any]) -> None:
        token = binding["token"]
        record_hash = binding["hash"]
        commit_input_hash = sha256(canonical_json(body))
        with self.state.lock:
            if self.state.persistence_failed:
                raise PersistenceError("DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED")
            self.state.validate_seed()
            prepared = self.state.prepared.get(token)
            if prepared is None or prepared.used or prepared.expires_at < time.time() or not hmac.compare_digest(prepared.record_hash, record_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "invalid stale used or mismatched token"})
                return
            if not hmac.compare_digest(prepared.input_hash, commit_input_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "commit payload differs from exact prepared payload"})
                return
            if len(self.state.events) >= MAX_EVENTS:
                self._json(409, {"state": "HOLD", "ordinary_release": False,
                                 "reason": "bounded terminal event capacity reached"})
                return
            prepared.used = True
            digest, record = self.state.record(
                state="EFFECT_ACK_DONE",
                input_hash=prepared.input_hash,
                ordinary_release=True,
                reason="single-use exact-bound loopback commit executed",
            )
            event = {
                "event_id": len(self.state.events) + 1,
                "kind": "TERMINAL_INPUT_ACCEPTED",
                "record_hash": record_hash,
                "input_hash": commit_input_hash,
                "text": str(body.get("text", ""))[:4096],
                "audio_present": body.get("audio") is not None,
                "video_present": body.get("video") is not None,
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "external_effect": "NONE",
                "seed_binding": self.state.seed_binding,
                "commit_token_sha256": sha256(token.encode("ascii")),
                "effect_record_hash": digest,
            }
            self.state.events.append(event)
            self.state.persist()
        self._json(
            200,
            {"state": "EFFECT_ACK_DONE", "ordinary_release": True, "post_effect": event, "successor_record": record},
            state="EFFECT_ACK_DONE",
            record_hash=digest,
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def load_ring_states(root: Path, seed: Path | None, *, expected_nodes: int = 4) -> dict[str, State]:
    """Take exclusive ownership of every retained origin; never merge token keys.

    Process consolidation changes execution placement, not origin identity or
    snapshot bytes. Missing, extra, corrupt or concurrently owned origins block
    the complete admission surface before any HTTP server is started.
    """
    if os.name != "posix" or seed is None or type(expected_nodes) is not int or expected_nodes not in (1, 2, 4):
        raise PersistenceError("LINUX_RING_REQUIRES_POSIX_AND_CANONICAL_SEED")
    states: dict[str, State] = {}
    try:
        root = root.absolute()
        if any(path.is_symlink() for path in (root, *root.parents)) or not root.is_dir():
            raise ValueError("ring root must be an existing no-follow directory")
        children = sorted(root.iterdir())
        if [p.name for p in children] != ["node-" + str(i) for i in range(expected_nodes)]:
            raise ValueError("ring inventory differs from the complete expected origin set")
        identities = {}
        for child in children:
            if child.is_symlink() or not child.is_dir():
                raise ValueError("origin must be a no-follow directory")
            info = child.stat()
            identities[child.name] = (info.st_dev, info.st_ino)
            store = child / ".qikvrt/api/terminal.json"
            if not store.is_file() or store.is_symlink():
                raise ValueError("retained origin snapshot is missing")
        if len(set(identities.values())) != len(children):
            raise ValueError("origin directories alias")
        for child in children:
            states[child.name] = State(seed, state_root=child)
        if len({state.secret for state in states.values()}) != expected_nodes:
            raise ValueError("origin stores share a token key")
        if sorted(p.name for p in root.iterdir()) != list(states) or any(
                child.is_symlink() or (child.stat().st_dev, child.stat().st_ino) != identities[child.name]
                for child in children):
            raise ValueError("ring inventory changed during ownership transfer")
        return states
    except BaseException as exc:
        for state in states.values():
            state.close()
        if isinstance(exc, (OSError, ValueError, PersistenceError)):
            raise PersistenceError("LINUX_RING_ORIGIN_UNAVAILABLE_NO_AUTOMATIC_RESET") from exc
        raise


class RingHandler(Handler):
    """One process serves unchanged origin stores through explicit node routes."""

    def _select_node(self) -> bool:
        match = re.fullmatch(r"/nodes/(node-[0-3])(/.*)", self.path)
        if match is None or match[1] not in self.server.ring_states:
            self._json(404, {"state": "HOLD", "ordinary_release": False,
                             "reason": "EXPLICIT_RETAINED_ORIGIN_NODE_REQUIRED"})
            return False
        self.node_state = self.server.ring_states[match[1]]
        self.node_prefix = "/nodes/" + match[1]
        self.path = match[2]
        return True

    def do_POST(self) -> None:
        if self._select_node():
            super().do_POST()

    def do_GET(self) -> None:
        if self.path == "/terminal/events":
            with ExitStack() as locks:
                for state in self.server.ring_states.values():
                    locks.enter_context(state.lock)
                if any(state.persistence_failed for state in self.server.ring_states.values()):
                    self._json(503, {"state": "HOLD", "ordinary_release": False,
                                     "reason": "DURABLE_TERMINAL_STATE_UNAVAILABLE_RESTART_REQUIRED"})
                    return
                events = [{"node_id": node, "event": dict(event)}
                          for node, state in self.server.ring_states.items()
                          for event in state.events]
                self._json(200, {"schema": "qikvrt_terminal_ring_snapshot_v1",
                    "origin_nodes": list(self.server.ring_states),
                    "events": events, "event_count": len(events),
                    "events_sha256": sha256(canonical_json(events)),
                    "event_identity": "ORIGIN_NODE_AND_ORIGINAL_EVENT_ID",
                    "persistence_scope": "FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE",
                    "external_effects": "NONE"})
        elif self.path == "/.well-known/effect-ack":
            self._json(200, {"schema": "qikvrt_linux_ring_capability_v1",
                "origin_nodes": list(self.server.ring_states),
                "node_prefix": "/nodes/{node_id}", "modes": ["prepare", "commit"],
                "aggregate_readback": "/terminal/events", "external_effects": "NONE"})
        elif self._select_node():
            super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--seed", type=Path,
                        help="Require the unchanged canonical 400-byte seed before local admission")
    parser.add_argument("--state-root", type=Path, default=Path.cwd(),
                        help="Durable local state root; uses .qikvrt/api/terminal.json")
    parser.add_argument("--state", type=Path,
                        help="Explicit durable state file; uses the same API persistence path")
    parser.add_argument("--ring-root", type=Path,
                        help="Consolidate all retained node-0..node-3 stores into one Linux process")
    parser.add_argument("--ring-nodes", type=int, choices=(1, 2, 4), default=4,
                        help="Complete expected origin count; missing origins must never disappear silently")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: reference terminal bridge is loopback-only")
    global STATE
    if args.ring_root is not None and args.state is not None:
        parser.error("choose --ring-root or --state")
    states = load_ring_states(args.ring_root, args.seed, expected_nodes=args.ring_nodes) if args.ring_root is not None else None
    if states is None:
        STATE = State(args.seed, args.state) if args.state is not None else State(args.seed, state_root=args.state_root)
    try:
        with ThreadingHTTPServer((args.host, args.port), RingHandler if states else Handler) as server:
            if states is not None:
                server.ring_states = states
            print(json.dumps({"state": "READY", "host": args.host, "port": server.server_port,
                              "persistence_scope": "FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE" if states else STATE.persistence_scope,
                              "origin_nodes": list(states) if states else [],
                              "runtime_profile": "LINUX_RING_CONSOLIDATED" if states else "SINGLE_TERMINAL",
                              "external_effects": "NONE"}, sort_keys=True), flush=True)
            server.serve_forever()
    finally:
        for state in states.values() if states else [STATE]:
            state.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
