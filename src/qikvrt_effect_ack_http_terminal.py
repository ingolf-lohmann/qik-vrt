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
import sys
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


def durable_subject(root: str, repository: str, pr: int, head: str, tree: str,
                    manifest_pin: str | None = None) -> dict[str, Any]:
    """Require a clean, exact checkout; never relabel the running carrier."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise DurableHold("REPOSITORY_REQUIRED")
    if type(pr) is not int or pr < 1 or not all(re.fullmatch(r"[0-9a-f]{40}", x or "") for x in (head, tree)):
        raise DurableHold("EXACT_SUBJECT_REQUIRED")
    if manifest_pin is not None:
        # Explicit sealed-export path. It neither probes Git nor changes the
        # existing clean-checkout path when no independent pin is supplied.
        import importlib.util
        spec = importlib.util.spec_from_file_location("qikvrt_owner_self_host", Path(root) / "tools/qikvrt_self_host.py")
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        return adapter.packaged_subject(Path(root), manifest_pin, repository, pr, head, tree)
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
        if meta.get("schema") not in ("1", "2") or not re.fullmatch(r"[0-9a-f]{32}", epoch):
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


PEER_RULE_SCOPE = "NATIVE_PEER_RULE_ACTIVATION_ONLY"


def peer_rule_request(value: dict[str, Any]) -> dict[str, Any]:
    """Freeze bounded canonical input; incoming bytes never become executable code."""
    try:
        raw = canonical_json(value)
        value = json.loads(raw)
        if (len(raw) > MAX_NATIVE_EVENT // 2 or not isinstance(value, dict)
                or set(value) != {"schema", "request_id", "work_unit_id", "sender_node_id", "sender_repository",
                                  "peer_node_id", "subject", "rule_id", "rule", "rule_sha256"}
                or value["schema"] != "qikvrt-peer-rule-request/v1"
                or any(not isinstance(value[k], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value[k])
                       or value[k] in {"__proto__", "constructor", "prototype"}
                       for k in ("request_id", "work_unit_id", "sender_node_id", "peer_node_id", "rule_id"))
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value["sender_repository"])
                or not isinstance(value["rule"], dict)
                or value["rule_sha256"] != "sha256:" + sha256(canonical_json(value["rule"]))):
            raise ValueError()
        target = value["subject"]
        if (not isinstance(target, dict) or set(target) != {"repository", "pr", "head", "tree"}
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", target["repository"])
                or type(target["pr"]) is not int or target["pr"] < 1
                or any(not re.fullmatch(r"[a-f0-9]{40}", target[k]) for k in ("head", "tree"))):
            raise ValueError()
    except (KeyError, TypeError, ValueError, RecursionError) as exc:
        raise DurableHold("PEER_RULE_BOUNDED_EXACT_REQUEST_REQUIRED") from exc
    return value


def peer_rule_binding(value: dict[str, Any]) -> dict[str, Any]:
    return {"request_id": value["request_id"], "work_unit_id": value["work_unit_id"],
            "request_sha256": "sha256:" + sha256(canonical_json(value)), "rule_id": value["rule_id"],
            "rule_sha256": value["rule_sha256"], "sender_node_id": value["sender_node_id"],
            "peer_node_id": value["peer_node_id"], "scope": PEER_RULE_SCOPE}


def verify_peer_rule_receipt(request: dict[str, Any], receipt: dict[str, Any], stage: str) -> None:
    """Verify original native identity/body digests as well as the peer envelope."""
    binding = peer_rule_binding(peer_rule_request(request))
    expected = {"schema": "qikvrt-peer-rule-receipt/v1", **binding, "subject": request["subject"],
                "stage": stage, "effect_ack_done": False}
    if (not isinstance(receipt, dict) or set(receipt) != set(expected) | {"native_event", "native_digest"}
            or any(receipt.get(k) != v for k, v in expected.items())):
        raise DurableHold("PEER_RULE_RECEIPT_BINDING_MISMATCH")
    event = receipt["native_event"]
    try:
        body = {k: v for k, v in event.items() if k not in ("id", "ledger_digest")}
        native = {k: v for k, v in body.items() if k not in ("recorded_at", "payload_digest", "evidence_transfer", "dod")}
        native["schema"] = NATIVE_SCHEMA
        payload = {**binding, "stage": stage, "effect_ack_done": False}
        if (set(body) != {"schema", "kind", "subject", "provenance", "observed_at", "message", "payload",
                          "recorded_at", "payload_digest", "evidence_transfer", "dod"}
                or not re.fullmatch(r"[a-f0-9]{32}:[1-9][0-9]*", event["id"])
                or event["ledger_digest"] != sha256(canonical_json(body))
                or receipt["native_digest"] != sha256(canonical_json(native))
                or body["schema"] != "qikvrt_temdd_event_v1" or body["subject"] != request["subject"]
                or body["provenance"] != {"source": "transputer", "native_event_id":
                    "peer-rule:" + binding["request_sha256"][7:] + ":" + stage.lower()}
                or body["kind"] != ("OBSERVE" if stage == "RECEIVED" else "EFFECT")
                or body["payload"] != payload or body["payload_digest"] != sha256(canonical_json(payload))
                or body["evidence_transfer"] != "DENY" or body["dod"] is not False):
            raise ValueError()
    except (TypeError, KeyError, ValueError) as exc:
        raise DurableHold("PEER_RULE_NATIVE_EVENT_MISMATCH") from exc


class NativePeerRules:
    """An admitted activation in the original Transputer, not a proposal executor.

    The local grant pins the full request and a rule already in the sealed source.
    Activation installs the rule binding consumed by this native adapter, in the
    original ledger's meta table. It does not attest a model's future behaviour.
    No caller-supplied apply/readback callback or `applied=True` is accepted.
    """
    def __init__(self, runtime: Any, node_id: str, state_dir: str, grants: list[dict[str, Any]]):
        self.runtime, self.node_id, self.state_dir = runtime, node_id, state_dir
        self.grants = json.loads(canonical_json(grants))
        if not isinstance(grants, list) or len(grants) > 128:
            raise DurableHold("PEER_RULE_LOCAL_GRANTS_REQUIRED")
        seen = set()
        for grant in grants:
            if (not isinstance(grant, dict) or set(grant) != {"peer_node_id", "request_id", "request_sha256",
                    "rule_sha256", "rule_path", "rule_pointer"}
                    or any(not isinstance(grant[k], str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", grant[k])
                           for k in ("request_sha256", "rule_sha256"))
                    or any(not isinstance(grant[k], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", grant[k])
                           for k in ("peer_node_id", "request_id"))
                    or not isinstance(grant["rule_path"], str) or not grant["rule_path"].startswith("policy/")
                    or not re.fullmatch(r"[A-Za-z0-9_.+/-]{1,256}", grant["rule_path"])
                    or any(p in ("", ".", "..") for p in grant["rule_path"].split("/"))
                    or not isinstance(grant["rule_pointer"], list) or len(grant["rule_pointer"]) > 12
                    or any(not isinstance(k, str) or not k or len(k) > 128 for k in grant["rule_pointer"])):
                raise DurableHold("PEER_RULE_LOCAL_GRANTS_REQUIRED")
            key = (grant["peer_node_id"], grant["request_id"])
            if key in seen: raise DurableHold("PEER_RULE_DUPLICATE_GRANT")
            seen.add(key)

    def admitted(self, value: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
        value = peer_rule_request(value)
        if (value["peer_node_id"] != self.node_id or value["subject"] != self.runtime.ensure_subject()
                or value["sender_node_id"] != peer["node_id"] or value["sender_repository"] != peer["repository"]):
            raise DurableHold("PEER_RULE_AUTHENTICATED_SUBJECT_MISMATCH")
        grant = next((g for g in self.grants if g["peer_node_id"] == peer["node_id"]
                      and g["request_id"] == value["request_id"]), None)
        if (grant is None or grant["request_sha256"] != peer_rule_binding(value)["request_sha256"]
                or grant["rule_sha256"] != value["rule_sha256"]):
            raise DurableHold("PEER_RULE_EXACT_LOCAL_GRANT_REQUIRED")
        path = self.runtime.root / grant["rule_path"]
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise DurableHold("PEER_RULE_LOCAL_SOURCE_SYMLINK")
        try:
            with path.open("rb") as source:
                raw = source.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY: raise ValueError()
            rule = json.loads(raw)
            for part in grant["rule_pointer"]: rule = rule[part]
            if canonical_json(rule) != canonical_json(value["rule"]): raise ValueError()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DurableHold("PEER_RULE_LOCAL_SOURCE_MISMATCH") from exc
        return value

    def key(self, value: dict[str, Any]) -> str:
        return "peer-rule:" + sha256(canonical_json([value["sender_node_id"], value["request_id"]]))

    def active_key(self, value: dict[str, Any]) -> str:
        return "peer-rule-active:" + sha256(canonical_json(value["rule_id"]))

    def read_meta(self, key: str, *, cold: bool = False) -> Any:
        if not cold:
            row = self.runtime.ledger.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        else:
            directory = _durable_directory(self.state_dir)
            path = _durable_file(directory, "events.sqlite3")
            with contextlib.closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
                db.execute("PRAGMA query_only=ON")
                row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def record(self, value: dict[str, Any], *, create: bool = False, cold: bool = False) -> Any:
        key = self.key(value)
        record = self.read_meta(key, cold=cold)
        if record is None and create:
            binding = peer_rule_binding(value)
            events = {}
            for stage in ("RECEIVED", "APPLIED"):
                events[stage] = {"schema": NATIVE_SCHEMA, "kind": "OBSERVE" if stage == "RECEIVED" else "EFFECT",
                    "subject": value["subject"], "provenance": {"source": "transputer", "native_event_id":
                        "peer-rule:" + binding["request_sha256"][7:] + ":" + stage.lower()},
                    "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "message": "Native peer rule " + stage.lower() + "; " + PEER_RULE_SCOPE,
                    "payload": {**binding, "stage": stage, "effect_ack_done": False}}
                self.runtime.ledger._validate(events[stage])
            record = {"request": value, "epoch": self.runtime.ledger.epoch, "events": events}
            record["sha256"] = sha256(canonical_json(record))
            self.runtime.ledger._check_writer()
            with self.runtime.ledger.db:
                self.runtime.ledger.db.execute("INSERT INTO meta VALUES (?,?)", (key, canonical_json(record).decode()))
            return self.record(value, cold=True)
        if record is not None:
            unsigned = {k: v for k, v in record.items() if k != "sha256"}
            if (set(record) != {"request", "epoch", "events", "sha256"} or record["request"] != value
                    or record["epoch"] != self.runtime.ledger.epoch
                    or record["sha256"] != sha256(canonical_json(unsigned))
                    or set(record["events"]) != {"RECEIVED", "APPLIED"}):
                raise DurableHold("PEER_RULE_DURABLE_REQUEST_CONFLICT")
            for stage, event in record["events"].items():
                self.runtime.ledger._validate(event)
                binding = peer_rule_binding(value)
                if (event["payload"] != {**binding, "stage": stage, "effect_ack_done": False}
                        or event["kind"] != ("OBSERVE" if stage == "RECEIVED" else "EFFECT")
                        or event["provenance"] != {"source": "transputer", "native_event_id":
                            "peer-rule:" + binding["request_sha256"][7:] + ":" + stage.lower()}):
                    raise DurableHold("PEER_RULE_DURABLE_REQUEST_CONFLICT")
        return record

    def receipt(self, value: dict[str, Any], record: dict[str, Any], stage: str) -> dict[str, Any] | None:
        epoch, event = _durable_read(self.state_dir, record["events"][stage])
        if epoch != record["epoch"]: raise DurableHold("PEER_RULE_LEDGER_EPOCH_MISMATCH")
        if event is None: return None
        result = {"schema": "qikvrt-peer-rule-receipt/v1", **peer_rule_binding(value),
                  "subject": value["subject"], "stage": stage, "native_event": event,
                  "native_digest": sha256(canonical_json(record["events"][stage])), "effect_ack_done": False}
        verify_peer_rule_receipt(value, result, stage)
        return result

    def receive(self, value: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
        with self.runtime.ledger.condition:
            value = self.admitted(value, peer)
            record = self.record(value, create=True)
            if self.receipt(value, record, "RECEIVED") is None:
                self.runtime.append(record["events"]["RECEIVED"])
            return self.receipt(value, record, "RECEIVED")

    def apply(self, value: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
        with self.runtime.ledger.condition:
            value = self.admitted(value, peer)
            record = self.record(value)
            if record is None or self.receipt(value, record, "RECEIVED") is None:
                raise DurableHold("PEER_RULE_RECEIPT_REQUIRED_BEFORE_APPLICATION")
            binding = peer_rule_binding(value)
            active_key = self.active_key(value)
            active = self.read_meta(active_key)
            if active is not None and active != binding:
                raise DurableHold("PEER_RULE_ACTIVE_BINDING_CONFLICT")
            # A crash between this reversible binding and the original append
            # is recovered by the same deterministic event, never by replaying
            # arbitrary instructions. Readback requires BOTH persisted effects.
            self.runtime.ledger._check_writer()
            if active is None:
                with self.runtime.ledger.db:
                    self.runtime.ledger.db.execute("INSERT INTO meta VALUES (?,?)",
                        (active_key, canonical_json(binding).decode()))
            if self.receipt(value, record, "APPLIED") is None:
                self.runtime.append(record["events"]["APPLIED"])
            return self.readback(value, peer, secrets.token_hex(16))

    def enforce_event(self, event: dict[str, Any]) -> None:
        """The activated binding is a writer admission guard, not just a label.

        S1 calls this before EVERY subsequent native append. Missing/corrupt
        active state, revoked grants, changed source and interrupted activation
        hold unrelated writes. Only the exact interrupted application event can
        complete that reversible activation. Unactivated receives add no guard.
        """
        rows = self.runtime.ledger.db.execute("SELECT key,value FROM meta WHERE key LIKE 'peer-rule:%'").fetchall()
        active = dict(self.runtime.ledger.db.execute("SELECT key,value FROM meta WHERE key LIKE 'peer-rule-active:%'"))
        for key, raw in rows:
            record = json.loads(raw)
            value = record["request"]
            peer = {"node_id": value["sender_node_id"], "repository": value["sender_repository"]}
            record = self.record(value)
            installed = self.read_meta(self.active_key(value))
            applied = self.receipt(value, record, "APPLIED")
            if installed is None and applied is None: continue
            self.admitted(value, peer)
            if key != self.key(value) or installed != peer_rule_binding(value):
                raise DurableHold("PEER_RULE_ACTIVE_WRITER_GUARD_MISMATCH")
            if self.receipt(value, record, "RECEIVED") is None:
                raise DurableHold("PEER_RULE_ACTIVE_WRITER_RECEIPT_REQUIRED")
            if applied is None and canonical_json(event) != canonical_json(record["events"]["APPLIED"]):
                raise DurableHold("PEER_RULE_INTERRUPTED_ACTIVATION_HOLDS_OTHER_WRITES")
            active.pop(self.active_key(value), None)
        if active: raise DurableHold("PEER_RULE_ORPHANED_ACTIVE_WRITER_GUARD")

    def readback(self, value: dict[str, Any], peer: dict[str, Any], challenge: str) -> dict[str, Any]:
        with self.runtime.ledger.condition:
            if not isinstance(challenge, str) or not re.fullmatch(r"[a-f0-9]{32}", challenge):
                raise DurableHold("PEER_RULE_FRESH_CHALLENGE_REQUIRED")
            value = self.admitted(value, peer)  # Recheck original local rule and source on every read.
            record = self.record(value, cold=True)
            received = self.receipt(value, record, "RECEIVED") if record else None
            applied = self.receipt(value, record, "APPLIED") if record else None
            active = self.read_meta(self.active_key(value), cold=True)
            if applied is not None and (received is None or active != peer_rule_binding(value)):
                raise DurableHold("PEER_RULE_ACTIVE_READBACK_MISMATCH")
            return {"schema": "qikvrt-peer-rule-readback/v1", **peer_rule_binding(value),
                "subject": value["subject"], "challenge": challenge, "received": received, "applied": applied,
                "active_binding": active if applied else None, "effect_ack_done": False}


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

    def _authenticated(self) -> bool:
        # The standalone launcher sets this boundary; legacy loopback tests
        # retain their original scope. No token is emitted in state or receipts.
        token = getattr(self.server, "terminal_auth_token", None)
        if token is None:
            return True
        if hmac.compare_digest(self.headers.get("Authorization", "").encode(), ("Bearer " + token).encode()):
            return True
        self._json(401, {"state": "HOLD", "reason": "local terminal authentication required", "ordinary_release": False})
        return False

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
        if not self._authenticated():
            return
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
                    "runtime_binding": getattr(self.server, "runtime_binding", None),
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
        if not self._authenticated():
            return
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
    parser.add_argument("--manifest-sha256", help="independent sealed S1 export pin; avoids Git only when explicitly supplied")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--prepare-hash")
    parser.add_argument("--personal-state-dir", help="Opt-in Personal adapter: private runtime data directory")
    parser.add_argument("--personal-model", help="Explicit model identifier; no implicit model substitution")
    parser.add_argument("--personal-provider", choices=("openai", "gemini"), default="openai")
    parser.add_argument("--personal-auth-config", type=Path, help="Private registered OIDC public-client configuration; enables OS Secret Service mode")
    parser.add_argument("--personal-legacy-memory-pairing", action="store_true", help="Explicit legacy test/development mode; no durable SSO or release acceptance")
    parser.add_argument("--personal-store-model-credential", action="store_true", help="Provision the selected model key to OS Secret Service from a terminal prompt, then exit")
    args = parser.parse_args()
    if args.personal_store_model_credential:
        if not args.personal_state_dir or not args.personal_auth_config or args.operation != "serve":
            raise SystemExit("BLOCK: explicit Personal state and OIDC configuration required")
        from qikvrt_personal_auth import OSSecretStore, load_config
        import getpass
        import warnings
        try:
            load_config(args.personal_auth_config, f"http://127.0.0.1:{args.port}")
            store = OSSecretStore(args.personal_state_dir, args.personal_provider)
            with store.provision_lock(args.personal_state_dir):
                bundle = store.read()
                if not sys.stdin.isatty():
                    raise ValueError("SECURE_INTERACTIVE_TERMINAL_REQUIRED")
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    key = getpass.getpass("Model API credential (OS protected store): ")
                if not key or any(c.isspace() for c in key) or len(key) > 16384:
                    raise ValueError("MODEL_CREDENTIAL_INVALID")
                bundle.setdefault("provider_keys", {})[args.personal_provider] = key
                store.write(bundle)
            print(json.dumps({"state": "PROTECTED_STORE_READBACK_VERIFIED", "credential_reference": store.profile}))
            return 0
        except (ValueError, OSError, getpass.GetPassWarning):
            raise SystemExit("BLOCK: protected credential provisioning unavailable") from None
    if args.operation != "serve":
        try:
            if not all((args.repository, args.pr, args.expected_head, args.expected_tree, args.input)):
                raise DurableHold("EXACT_SUBJECT_AND_INPUT_REQUIRED")
            subject = durable_subject(args.root, args.repository, args.pr, args.expected_head, args.expected_tree, args.manifest_sha256)
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
    handler = Handler
    runtime = None
    if args.personal_state_dir:
        from qikvrt_personal_assistant import PersonalRuntime, personal_handler
        try:
            if args.personal_auth_config:
                if args.personal_legacy_memory_pairing:
                    raise ValueError("PERSONAL_AUTH_MODES_ARE_MUTUALLY_EXCLUSIVE")
                runtime = PersonalRuntime.from_secret_store(args.personal_state_dir, args.personal_model, args.personal_provider,
                    args.personal_auth_config, f"http://127.0.0.1:{args.port}")
            elif args.personal_legacy_memory_pairing:
                runtime = PersonalRuntime.from_environment(args.personal_state_dir, args.personal_model, args.personal_provider)
            else:
                raise ValueError("PROTECTED_PERSONAL_AUTH_CONFIGURATION_REQUIRED")
            handler = personal_handler(Handler, runtime)
        except (ValueError, OSError) as exc:
            raise SystemExit("BLOCK: " + str(exc)) from None
    elif args.personal_model or args.personal_auth_config or args.personal_legacy_memory_pairing:
        raise SystemExit("BLOCK: Personal arguments require --personal-state-dir")
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(json.dumps({"state": "READY", "host": args.host, "port": args.port,
                      "personal_adapter_enabled": runtime is not None,
                      "external_effects": "AUTHENTICATED_MODEL_REQUESTS_ONLY" if runtime else "NONE"}, sort_keys=True), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if runtime:
            runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
