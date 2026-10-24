#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Freeze and start the existing monitor/terminal carriers; no job executor."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import hmac
import base64
import importlib.util
import ipaddress
import json
import os
import platform
import re
import secrets
import shutil
import signal
import socket
import stat
import struct
import sqlite3
import time
import urllib.request
import urllib.parse
import urllib.error
from urllib.parse import urlsplit
import subprocess
import sys
import tarfile
import tempfile
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = "runtime/self-host/PACKAGE.json"
BROWSER_COMMANDS = ("firefox-esr", "Xvfb", "x11vnc", "websockify", "xdpyinfo", "xwininfo")
STATE_FILES = frozenset(("binding.json", "monitor/node.json", "temdd/events.sqlite3",
                        "temdd/events.sqlite3-wal", "temdd/events.sqlite3-shm", "repository.qmesh"))
STATE_MAX_BYTES = 2 * 1024 * 1024 * 1024
MESH_CONTRACT = "runtime/self-host/MESH_ACTIVATION.json"
MESH_ROLE_POLICIES = ["policy/CANONICAL_UPSTREAM_REMOTE_V1.json",
                      "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"]
MONOLITH_APPLICATION_ID = 0x51495654
MONOLITH_MAX_FILES = 4096
MONOLITH_MAX_FILE_BYTES = 16 * 1024 * 1024
MESH_PORTABLE_FILES = ["docs/monitor/mesh-file-codec.js", "docs/monitor/mesh-file-client.js",
                       "docs/monitor/mesh-file-view.js", "docs/monitor/mesh-file-store.mjs"]
MESH_COMPONENT_FILES = {
    "universal_transputer": ["src/qikvrt_temdd_event_ledger.py"],
    "universal_terminal": ["src/qikvrt_temdd_event_ledger.py", "src/qikvrt_effect_ack_http_terminal.py",
                           "docs/terminal/temdd/index.html", "docs/monitor/client-replica.js"],
}
MESH_FAULT_CASES = ("PROCESS_CRASH", "NODE_LOSS", "NETWORK_PARTITION", "PROVIDER_LOSS",
                    "LOST_EFFECT_ACK", "CONCURRENT_TAKEOVER", "STALE_WRITER", "NODE_REJOIN")
MESH_INVARIANTS = ("same_work_unit_after_failover", "preserve_confirmed_effects",
                   "no_duplicate_irreversible_effect", "fence_previous_writer",
                   "replicate_before_positive_effect_ack", "fresh_authenticated_readback",
                   "retain_unavailable_inventory_members", "preserve_original_event_bytes",
                   "measure_user_visible_interruption", "hold_writes_without_safe_quorum")
MESH_WORK_MAX = 16 * 1024 * 1024
MESH_WORK_SCOPE = "OWNER_SELECTED_EXPORTABLE_PROPOSAL_BYTES"
MESH_CACHE_SOURCE_FILES = ["tools/qikvrt_self_host.py", "docs/monitor/server.mjs", "docs/monitor/self-host.mjs"]
MESH_CACHE_INVARIANTS = ("all_nodes", "content_addressed_original_bytes", "fresh_checks_on_warm_path",
    "source_bound_validation", "stable_idle_before_transfer", "single_frozen_batch", "atomic_receiver_install",
    "conditional_base_match", "persist_ambiguous_transfer", "readback_before_retry", "authenticated_independent_readback",
    "preserve_work_units_and_instruction_bytes", "hold_on_capacity_or_unknown_state",
    "durable_authenticated_sender_receipt", "fresh_challenged_receiver_readback", "production_requires_received_peer_batch")


def mesh_wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


class MeshWorkCache:
    """Finite proposal cache/outbox using the existing private snapshot primitives.

    This never delays native-effect replication, executes a received proposal,
    mutates Git, or infers whole-node idle. Only cooperating cache writers and
    selected exact Git bytes belong to this measured idle scope.
    """
    def __init__(self, directory, repository, node_id):
        self.directory = Path(directory)
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository or "")
                or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", node_id or "")
                or node_id in ("__proto__", "constructor", "prototype")):
            raise ValueError("MESH_WORK_IDENTITY_REQUIRED")
        self.binding = {"repository": repository, "node_id": node_id}
        private_path(self.directory.parent, directory=True)
        if not self.directory.exists():
            self.directory.mkdir(mode=0o700)
            sync_directory(self.directory.parent)
        private_path(self.directory, directory=True)
        for name in ("objects", "outbox"):
            path = self.directory / name
            if not path.exists(): path.mkdir(mode=0o700)
            private_path(path, directory=True)
        self.path = self.directory / "CACHE_STATE.json"

    @contextlib.contextmanager
    def locked(self):
        fd = os.open(self.directory / "cache.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            private_path(self.directory / "cache.lock")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.path.exists():
                private_path(self.path)
                envelope = json.loads(self.path.read_bytes())
                self.state = envelope["state"]
                if (envelope["sha256"] != digest(mesh_wire(self.state))
                        or self.state.get("schema") != "qikvrt-repository-work-cache/v1"
                        or self.state.get("binding") != self.binding):
                    raise ValueError("MESH_WORK_CACHE_READBACK_MISMATCH")
            else:
                self.state = {"schema": "qikvrt-repository-work-cache/v1", "binding": self.binding,
                    "epoch": uuid.uuid4().hex, "revision": 0, "entries": {}, "work_units": [],
                    "seen_units": {}, "acknowledged_objects": [], "last_ack": "0" * 64,
                    "source": None, "root": None, "mode": "DIRTY", "pending": None}
            yield
        finally:
            os.close(fd)

    def save(self):
        raw = raw_json({"state": self.state, "sha256": digest(mesh_wire(self.state))})
        temp = self.directory / (".state-" + uuid.uuid4().hex)
        try:
            synced_private_file(temp, raw)
            os.replace(temp, self.path)
            sync_directory(self.directory)
            private_path(self.path)
            if self.path.read_bytes() != raw: raise ValueError("MESH_WORK_CACHE_READBACK_MISMATCH")
        finally:
            if temp.exists(): temp.unlink()

    def object(self, key):
        if not re.fullmatch(r"[a-f0-9]{64}", key or ""):
            raise ValueError("MESH_WORK_OBJECT_DIGEST_REQUIRED")
        path = self.directory / "objects" / key
        private_path(path)
        raw = path.read_bytes()
        if len(raw) > MESH_WORK_MAX or digest(raw) != key:
            raise ValueError("MESH_WORK_OBJECT_READBACK_MISMATCH")
        return raw

    def cache(self, raw):
        key = digest(raw)
        path = self.directory / "objects" / key
        hit = path.exists()
        if hit:
            if self.object(key) != raw: raise ValueError("MESH_WORK_OBJECT_READBACK_MISMATCH")
        else:
            synced_private_file(path, raw)
            sync_directory(path.parent)
        return key, hit

    def snapshot(self, root, paths):
        root = Path(root).resolve(strict=True)
        if (root == self.directory or root in self.directory.parents or self.directory in root.parents
                or not isinstance(paths, list) or not paths or len(paths) > 8192
                or len(paths) != len(set(paths)) or any(not isinstance(p, str) or
                    not re.fullmatch(r"[A-Za-z0-9_.+/-]{1,256}", p) or p.startswith("/") or
                    any(part in ("", ".", "..", ".git", "__proto__", "constructor", "prototype")
                        for part in p.split("/")) for p in paths)):
            raise ValueError("MESH_WORK_EXPLICIT_TRACKED_FILE_SCOPE_REQUIRED")
        head = git(root, "rev-parse", "--verify", "HEAD^{commit}").decode()
        tree = git(root, "rev-parse", "--verify", head + "^{tree}").decode()
        if git(root, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("MESH_WORK_CLEAN_LOCAL_COMMIT_REQUIRED")
        tracked = {}
        for row in git(root, "ls-tree", "-r", "-z", head, "--", *paths).split(b"\0"):
            if not row: continue
            metadata, name = row.split(b"\t", 1)
            mode, kind, blob = metadata.split()
            if kind != b"blob" or mode not in (b"100644", b"100755"):
                raise ValueError("MESH_WORK_REGULAR_TRACKED_FILES_REQUIRED")
            tracked[name.decode()] = blob.decode()
        if set(tracked) != set(paths): raise ValueError("MESH_WORK_REGULAR_TRACKED_FILES_REQUIRED")
        entries, objects = {}, {}
        total = 0
        for name in sorted(paths):
            path = root / name
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError("MESH_WORK_SOURCE_SYMLINK_FORBIDDEN")
            entry = state_file_digest(path)
            total += entry["bytes"]
            if total > MESH_WORK_MAX: raise ValueError("MESH_WORK_SNAPSHOT_TOO_LARGE")
            raw = path.read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if digest(raw) != entry["sha256"] or blob != tracked[name]:
                raise ValueError("MESH_WORK_EXACT_GIT_BYTES_REQUIRED")
            entries[name] = entry
            objects[entry["sha256"]] = raw
        if git(root, "rev-parse", "--verify", "HEAD^{commit}").decode() != head or git(root, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("MESH_WORK_SOURCE_CHANGED")
        return {"head": head, "tree": tree}, entries, objects

    def stage(self, root, paths, unit_id, instructions):
        if (not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", unit_id or "")
                or unit_id in ("__proto__", "constructor", "prototype")
                or not isinstance(instructions, bytes) or len(instructions) > MESH_WORK_MAX):
            raise ValueError("MESH_WORK_UNIT_REQUIRED")
        with self.locked():
            if self.state["pending"]: raise ValueError("MESH_WORK_PENDING_BATCH_BACKPRESSURE")
            if len(self.state["work_units"]) >= 1024: raise ValueError("MESH_WORK_BATCH_CAPACITY_HOLD")
            source, entries, objects = self.snapshot(root, paths)
            unit = {"id": unit_id, "source": source, "entries_sha256": digest(mesh_wire(entries)),
                    "instructions_sha256": digest(instructions)}
            unit_key = digest(mesh_wire(unit))
            if unit_id in self.state["seen_units"]:
                if self.state["seen_units"][unit_id] != unit_key: raise ValueError("MESH_WORK_UNIT_CONFLICT")
                return {"state": "MESH_WORK_DUPLICATE_NOOP", "effect_ack_done": False}
            if self.state["root"] is not None and self.state["root"] != str(Path(root).resolve()):
                raise ValueError("MESH_WORK_LOCAL_ROOT_BINDING_MISMATCH")
            objects[digest(instructions)] = instructions
            hits = sum(self.cache(raw)[1] for raw in objects.values())
            self.state.update(root=str(Path(root).resolve()), source=source, entries=entries,
                revision=self.state["revision"] + 1, mode="DIRTY", idle=None)
            self.state["work_units"].append(unit)
            self.state["seen_units"][unit_id] = unit_key
            self.save()
            return {"state": "MESH_WORK_LOCALLY_STAGED", "revision": self.state["revision"],
                    "cache_hits": hits, "cached_objects": len(objects), "cloud_requests": 0, "effect_ack_done": False}

    def current(self):
        source, entries, _ = self.snapshot(Path(self.state["root"]), sorted(self.state["entries"]))
        if source != self.state["source"] or entries != self.state["entries"]:
            raise ValueError("MESH_WORK_IDLE_INVALIDATED")
        for key in {e["sha256"] for e in entries.values()} | {u["instructions_sha256"] for u in self.state["work_units"]}:
            self.object(key)

    def pending(self):
        pin = self.state["pending"]["batch_id"]
        path = self.directory / "outbox" / pin
        private_path(path)
        raw = path.read_bytes()
        packet = json.loads(raw)
        unsigned = dict(packet); unsigned.pop("batch_id", None)
        if (packet.get("batch_id") != pin or digest(mesh_wire(unsigned)) != pin
                or raw != mesh_wire(packet) or len(raw) > MESH_WORK_MAX):
            raise ValueError("MESH_WORK_OUTBOX_READBACK_MISMATCH")
        return raw, packet

    def idle(self, command):
        with self.locked():
            if self.state["pending"]:
                self.current(); self.pending()
                return {"state": "MESH_WORK_IDLE_BATCH_REUSED", "batch_id": self.state["pending"]["batch_id"], "effect_ack_done": False}
            if not self.state["work_units"]: return {"state": "MESH_WORK_NOOP", "effect_ack_done": False}
            if not isinstance(command, list) or not command or any(not isinstance(a, str) or not a or "\0" in a for a in command):
                raise ValueError("MESH_WORK_EXPLICIT_VALIDATION_COMMAND_REQUIRED")
            self.current()
            self.state.update(mode="VALIDATING", idle=None); self.save()
            try:
                result = subprocess.run(command, cwd=self.state["root"], capture_output=True, timeout=60, check=False)
                if result.returncode != 0: raise ValueError("MESH_WORK_VALIDATION_FAILED")
                self.current()
                proof = {"state": "IDLE_STABLE_VALIDATED", "scope": "CACHE_WRITER_LOCK_AND_EXACT_SELECTED_GIT_BYTES",
                    "active_cache_writers": 0, "equal_source_observations": 2,
                    "entries_sha256": digest(mesh_wire(self.state["entries"])),
                    "validation": {"kind": "EXECUTED_COMMAND_EXIT_ZERO", "command_sha256": digest(mesh_wire(command)),
                        "exit_code": 0, "stdout_sha256": digest(result.stdout), "stderr_sha256": digest(result.stderr)}}
                required = {e["sha256"] for e in self.state["entries"].values()} | {u["instructions_sha256"] for u in self.state["work_units"]}
                packet = {"schema": "qikvrt-repository-work-batch/v1", **self.binding, "scope": MESH_WORK_SCOPE,
                    "epoch": self.state["epoch"], "revision": self.state["revision"], "base_digest": self.state["last_ack"],
                    "source": self.state["source"], "entries": self.state["entries"], "work_units": self.state["work_units"],
                    "objects": {key: base64.b64encode(self.object(key)).decode() for key in sorted(required - set(self.state["acknowledged_objects"]))},
                    "idle": proof, "effect_ack_done": False}
                packet["batch_id"] = digest(mesh_wire(packet))
                raw = mesh_wire(packet)
                if len(raw) > MESH_WORK_MAX: raise ValueError("MESH_WORK_BATCH_TOO_LARGE")
                target = self.directory / "outbox" / packet["batch_id"]
                if target.exists():
                    private_path(target)
                    if target.read_bytes() != raw: raise ValueError("MESH_WORK_OUTBOX_READBACK_MISMATCH")
                else: synced_private_file(target, raw); sync_directory(target.parent)
                self.state.update(mode="IDLE_STABLE_VALIDATED", idle=proof,
                    pending={"batch_id": packet["batch_id"], "attempted": False})
                self.save()
                return {"state": "MESH_WORK_IDLE_BATCH_FROZEN", "batch_id": packet["batch_id"],
                        "wire_bytes": len(raw), "transferred_objects": len(packet["objects"]),
                        "work_units": len(packet["work_units"]), "whole_node_idle_verified": False, "effect_ack_done": False}
            except BaseException:
                self.state.update(mode="HOLD", idle=None); self.save()
                raise

    def send(self, peer, transport=None):
        with self.locked():
            if not self.state["pending"] or self.state["mode"] != "IDLE_STABLE_VALIDATED":
                raise ValueError("MESH_WORK_VALIDATED_IDLE_BATCH_REQUIRED")
            raw, packet = self.pending()
            if not self.state["pending"]["attempted"]: self.current()
            request = self.peer_request(peer, transport)
            path = "/api/mesh-work/receipt/" + packet["batch_id"]
            known = witness = None
            if self.state["pending"]["attempted"]:
                status, known, witness = request("GET", path)
                if status == 404: known = None
                elif status != 200: raise ValueError("MESH_WORK_RECEIPT_UNAVAILABLE")
            if known is None:
                self.current()  # No new payload transfer from an invalidated idle.
                self.state["pending"]["attempted"] = True; self.save()
                status, _, _ = request("POST", "/api/mesh-work/batch", raw)
                if status != 200: raise ValueError("MESH_WORK_TRANSFER_REFUSED")
                status, known, witness = request("GET", path)
                if status != 200: raise ValueError("MESH_WORK_RECEIPT_UNAVAILABLE")
            self.validate_receipt(packet, peer, known)
            try:
                self.current()
                local_mode = "IDLE_STABLE_VALIDATED"
            except ValueError:
                # A known receipt resolves only this already-delivered batch.
                # New local work must be staged/validated afresh, never resent.
                local_mode = "DIRTY"
            self.state.setdefault("receipts", {})[packet["batch_id"]] = {
                "receipt": known, "authenticated_response": witness}
            self.state.update(last_ack=packet["batch_id"], pending=None, work_units=[],
                mode=local_mode, idle=self.state.get("idle") if local_mode == "IDLE_STABLE_VALIDATED" else None,
                acknowledged_objects=sorted(set(self.state["acknowledged_objects"]) | set(packet["objects"])))
            self.save()
            return {"state": "MESH_WORK_BATCH_READBACK_CONFIRMED", "batch_id": packet["batch_id"],
                    "local_idle_state": local_mode, "sender_receipt_durable": True,
                    "proposal_execution": "NOT_EXECUTED", "whole_mesh_distribution_verified": False, "effect_ack_done": False}

    def peer_request(self, peer, transport=None):
        secret_path = Path(peer["secret_file"])
        private_path(secret_path)
        secret = secret_path.read_bytes().strip()
        if not 32 <= len(secret) <= 256 or not secret.isascii() or any(c <= 32 or c >= 127 for c in secret):
            raise ValueError("MESH_WORK_PEER_KEY_REQUIRED")
        target = urllib.parse.urlsplit(peer["url"])
        if (target.scheme not in ("http", "https") or not target.hostname or target.username or target.password
                or target.path not in ("", "/") or target.query or target.fragment
                or (target.scheme == "http" and target.hostname not in ("127.0.0.1", "localhost"))
                or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", peer.get("node_id", ""))
                or any(not re.fullmatch(r"[a-f0-9]{40}", peer.get(k, "")) for k in ("source_head", "source_tree"))):
            raise ValueError("MESH_WORK_PINNED_PEER_REQUIRED")
        def request(method, path, body=b""):
            signature = "sha256=" + hmac.new(secret, method.encode() + b"\n" + path.encode() + b"\n" + body, hashlib.sha256).hexdigest()
            headers = {"Content-Type": "application/json", "x-qikvrt-mesh-node": self.binding["node_id"],
                       "x-qikvrt-replication-signature": signature}
            status, data, response_signature = (transport or mesh_work_transport)(peer["url"].rstrip("/") + path, method, body, headers)
            expected = "sha256=" + hmac.new(secret, b"RESPONSE\n" + path.encode() + b"\n" + data, hashlib.sha256).hexdigest()
            if not isinstance(response_signature, str) or not hmac.compare_digest(expected, response_signature):
                raise ValueError("MESH_WORK_AUTHENTICATED_READBACK_REQUIRED")
            return status, json.loads(data), {"path": path,
                "body_base64": base64.b64encode(data).decode(), "signature": response_signature}
        return request

    def validate_receipt(self, packet, peer, known):
        expected = {"schema": "qikvrt-repository-work-receipt/v1", **self.binding,
            "batch_id": packet["batch_id"], "revision": packet["revision"],
            "entries_sha256": packet["idle"]["entries_sha256"], "scope": MESH_WORK_SCOPE,
            "serving_node_id": peer["node_id"], "source_head": peer["source_head"], "source_tree": peer["source_tree"],
            "proposal_execution": "NOT_EXECUTED", "effect_ack_done": False}
        if (not isinstance(known, dict) or set(known) != set(expected) | {"receipt_sha256"}
                or any(known.get(k) != v for k, v in expected.items())
                or known.get("receipt_sha256") != digest(mesh_wire({k: v for k, v in known.items() if k != "receipt_sha256"}))):
            raise ValueError("MESH_WORK_RECEIPT_BINDING_MISMATCH")

    def check(self, peer, transport=None):
        """Fresh receiver proof for an acknowledged batch; never POST or repair state."""
        with self.locked():
            batch_id = self.state["last_ack"]
            if batch_id == "0" * 64:
                raise ValueError("MESH_WORK_CONFIRMED_BATCH_REQUIRED")
            path = self.directory / "outbox" / batch_id
            private_path(path)
            raw = path.read_bytes(); packet = json.loads(raw)
            unsigned = dict(packet); unsigned.pop("batch_id", None)
            if (packet.get("batch_id") != batch_id or digest(mesh_wire(unsigned)) != batch_id
                    or raw != mesh_wire(packet) or len(raw) > MESH_WORK_MAX):
                raise ValueError("MESH_WORK_OUTBOX_READBACK_MISMATCH")
            challenge = secrets.token_hex(16)
            status, value, _ = self.peer_request(peer, transport)("GET",
                "/api/mesh-work/readback/" + batch_id + "/" + challenge)
            expected = {"schema": "qikvrt-repository-work-live-readback/v1", "challenge": challenge,
                "serving_node_id": peer["node_id"], "source_head": peer["source_head"], "source_tree": peer["source_tree"],
                "proposal_execution": "NOT_EXECUTED", "effect_ack_done": False}
            if (status != 200 or not isinstance(value, dict) or set(value) != set(expected) | {"receipt"}
                    or any(value.get(k) != v for k, v in expected.items())):
                raise ValueError("MESH_WORK_FRESH_RECEIVER_READBACK_REQUIRED")
            self.validate_receipt(packet, peer, value["receipt"])
            stored = self.state.get("receipts", {}).get(batch_id)
            if stored is not None:
                try:
                    witness = stored["authenticated_response"]
                    original = base64.b64decode(witness["body_base64"], validate=True)
                    original_path = "/api/mesh-work/receipt/" + batch_id
                    expected_signature = "sha256=" + hmac.new(Path(peer["secret_file"]).read_bytes().strip(),
                        b"RESPONSE\n" + original_path.encode() + b"\n" + original, hashlib.sha256).hexdigest()
                    if (stored["receipt"] != value["receipt"] or witness["path"] != original_path
                            or json.loads(original) != value["receipt"]
                            or not hmac.compare_digest(expected_signature, witness["signature"])):
                        raise ValueError("invalid sender witness")
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError("MESH_WORK_DURABLE_SENDER_RECEIPT_MISMATCH") from exc
            return {"state": "MESH_WORK_PEER_BATCH_VERIFIED", "batch_id": batch_id,
                "receiver": {k: peer[k] for k in ("node_id", "source_head", "source_tree")},
                "receipt_sha256": value["receipt"]["receipt_sha256"], "sender_receipt_durable": stored is not None,
                "fresh_challenge_verified": True, "proposal_execution": "NOT_EXECUTED", "effect_ack_done": False}

    def confirm_rule(self, peer, value, *, apply=False, transport=None):
        """Finite native request/receipt/application/readback; never execute a work batch."""
        terminal = load_source(ROOT, "qikvrt_effect_ack_http_terminal")
        eap = load_source(ROOT, "qikvrt_effect_ack")
        value = terminal.peer_rule_request(value)
        if (value["sender_node_id"] != self.binding["node_id"] or value["sender_repository"] != self.binding["repository"]
                or value["peer_node_id"] != peer["node_id"]
                or any(value["subject"][k] != peer["source_" + k] for k in ("head", "tree"))
                or type(apply) is not bool):
            raise ValueError("PEER_RULE_PINNED_REQUEST_REQUIRED")
        binding = terminal.peer_rule_binding(value)
        prefix = "/api/mesh-work/rule/"
        with self.locked():
            requests = self.state.setdefault("rule_requests", {})
            key = digest(mesh_wire([value["peer_node_id"], value["request_id"]]))
            prior = requests.get(key)
            if prior is not None and prior["request"] != value:
                raise ValueError("PEER_RULE_SENDER_REQUEST_CONFLICT")
            if prior is None:
                if len(requests) >= 128: raise ValueError("PEER_RULE_SENDER_CAPACITY_HOLD")
                requests[key] = {"request": value, "readback": None, "received_ack": None}
                self.save()  # The exact request survives an ambiguous POST.
            request = self.peer_request(peer, transport)

            def readback():
                challenge = secrets.token_hex(16)
                status, result, witness = request("GET", prefix + "readback/" + value["request_id"] + "/" + challenge)
                absent = {"schema": "qikvrt-peer-rule-absent/v1", "request_id": value["request_id"],
                          "peer_node_id": peer["node_id"], "subject": value["subject"], "challenge": challenge,
                          "effect_ack_done": False}
                if status == 200 and result == absent:
                    old = requests[key]["readback"]
                    if requests[key].get("received_ack") or old and old["value"]["received"] is not None:
                        raise ValueError("PEER_RULE_CONFIRMED_RECEIPT_LOST_HOLD")
                    return {"received": None, "applied": None}
                expected = {"schema": "qikvrt-peer-rule-readback/v1", **binding, "subject": value["subject"],
                            "challenge": challenge, "effect_ack_done": False}
                if (status != 200 or not isinstance(result, dict)
                        or set(result) != set(expected) | {"received", "applied", "active_binding"}
                        or any(result.get(k) != v for k, v in expected.items())):
                    raise ValueError("PEER_RULE_FRESH_AUTHENTICATED_READBACK_REQUIRED")
                for stage in ("RECEIVED", "APPLIED"):
                    if result[stage.lower()] is not None:
                        terminal.verify_peer_rule_receipt(value, result[stage.lower()], stage)
                previous = requests[key]["readback"]
                for stage in ("received", "applied"):
                    if previous and previous["value"][stage] is not None and previous["value"][stage] != result[stage]:
                        raise ValueError("PEER_RULE_CHANGED_NATIVE_RECEIPT")
                ack = requests[key].get("received_ack")
                if ack is not None and ack["receipt"] != result["received"]:
                    raise ValueError("PEER_RULE_CHANGED_NATIVE_RECEIPT")
                if result["applied"] is not None:
                    if (result["received"] is None or result["active_binding"] != binding
                            or result["received"]["native_event"]["id"].split(":")[0] != result["applied"]["native_event"]["id"].split(":")[0]
                            or int(result["received"]["native_event"]["id"].split(":")[1]) >= int(result["applied"]["native_event"]["id"].split(":")[1])):
                        raise ValueError("PEER_RULE_ACTIVE_NATIVE_READBACK_REQUIRED")
                elif result["active_binding"] is not None:
                    raise ValueError("PEER_RULE_UNCONFIRMED_ACTIVE_BINDING")
                requests[key]["readback"] = {"value": result, "authenticated_response": witness}
                self.save()
                return result

            # A read is required even on the first call, and before every retry
            # after lost ACK. An unavailable read never authorizes a new POST.
            observed = readback()
            for operation, stage in (("receive", "received"), ("apply", "applied")):
                if operation == "apply" and not apply: break
                if observed[stage] is not None: continue
                status, reply, witness = request("POST", prefix + operation, mesh_wire(value))
                if status != 200: raise ValueError("PEER_RULE_NATIVE_OPERATION_REFUSED")
                if operation == "receive":
                    terminal.verify_peer_rule_receipt(value, reply, "RECEIVED")
                    requests[key]["received_ack"] = {"receipt": reply, "authenticated_response": witness}; self.save()
                # Never derive release from the POST result. The new GET has a
                # new nonce and reads both original SQLite events and activation.
                observed = readback()
                if observed[stage] is None: raise ValueError("PEER_RULE_NATIVE_EFFECT_NOT_OBSERVED")
            done = observed["applied"] is not None
            evidence = tuple("sha256:" + digest(mesh_wire(observed[k])) for k in ("received", "applied") if observed[k] is not None)
            decision = eap.effect_ack_sync(eap.EffectAckRequest(
                protocol_root_id="native-peer-rule:" + value["rule_id"], input_id=value["request_id"],
                payload=mesh_wire(value), declared_input_hash=binding["request_sha256"], transport_ack=True,
                origin_checked=True, context_checked=True, semantics_reconstructed=True, effect_anticipated=True,
                risk_classified=True, risk_level=eap.RiskLevel.LOW, responsibility_assigned=True,
                responsibility_owner=value["peer_node_id"], policy_allows_release=done,
                connection_decision=eap.ConnectionDecision.RELEASE if done else eap.ConnectionDecision.CONTINUE,
                evidence_refs=evidence, required_evidence_refs=evidence,
                open_questions=() if done else ("Native peer rule application not observed",))).to_dict()
            return {"scope": terminal.PEER_RULE_SCOPE, "rule_effect": decision, "readback": observed,
                    "effect_ack_done": False, "all_peer_adoption_verified": False}


def mesh_work_transport(url, method, body, headers):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    request = urllib.request.Request(url, data=body if method == "POST" else None, headers=headers, method=method)
    try:
        response = urllib.request.build_opener(NoRedirect).open(request, timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read(MESH_WORK_MAX + 1)
        if len(raw) > MESH_WORK_MAX: raise ValueError("MESH_WORK_READBACK_TOO_LARGE")
        return response.code, raw, response.headers.get("x-qikvrt-replication-signature")


def raw_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=30, stderr=subprocess.DEVNULL).strip()


def runtime(command):
    path = Path(shutil.which(command) or command).resolve(strict=True)
    version = subprocess.check_output([str(path), "--version"], timeout=5, stderr=subprocess.STDOUT,
                                      env={"PATH": os.environ.get("PATH", ""), "LANG": "C"}).decode().strip()
    return {"version": version, "executable_sha256": digest(path.read_bytes())}


def browser_commands(firefox_package="firefox-esr"):
    if firefox_package not in {"firefox-esr", "firefox"}:
        raise ValueError("DECLARED_FIREFOX_PACKAGE_REQUIRED")
    return (firefox_package, *BROWSER_COMMANDS[1:])


def firefox_binary(package="firefox-esr"):
    browser_commands(package)
    if package == "firefox":
        # Debian's existing /usr/bin/firefox wrapper can delegate to ESR.
        # The Mozilla DEB owns this ELF; bind it directly, including in a
        # restricted Git/gh-free runtime PATH. Never fall back to that wrapper.
        path = Path("/usr/lib/firefox/firefox")
        with path.open("rb") as source:
            if source.read(4) != b"\x7fELF": raise ValueError("ACTUAL_MOZILLA_FIREFOX_ELF_REQUIRED")
        return path.resolve(strict=True)
    found = shutil.which(package)
    if not found: raise ValueError("ACTUAL_FIREFOX_BINARY_REQUIRED:" + package)
    return Path(found).resolve(strict=True)


def browser_executables(firefox_package="firefox-esr"):
    # Distribution-built tools use an exact executable binding, not a made-up
    # universal version. Actual package versions are retained by the image build.
    return {name: digest((firefox_binary(name) if name == firefox_package else
                Path(shutil.which(name) or name).resolve(strict=True)).read_bytes())
            for name in browser_commands(firefox_package)}


def mesh_contract(root, definition=None):
    """Verify role-independent source obligations, never infer deployed fault tolerance.

    This is the package admission boundary. Live receipts, leader fencing and
    original native effect replication still need separate runtime acceptance.
    """
    definition = definition if definition is not None else json.loads((root / DEFINITION).read_bytes())
    raw = (root / MESH_CONTRACT).read_bytes()
    activation = json.loads(raw)
    if not isinstance(activation, dict) or not isinstance(definition, dict):
        raise ValueError("EVERY_NODE_TRANSPUTER_AND_TERMINAL_CONTRACT_REQUIRED")
    contract = activation.get("required_node_runtime", {})
    if (not isinstance(contract, dict)
            or activation.get("schema") != "qikvrt-self-host-mesh-activation/v1"
            or contract.get("schema") != "qikvrt-node-bus-contract/v1"
            or contract.get("scope") != "EVERY_CURRENT_AND_FUTURE_REPOSITORY_NODE"
            or contract.get("all_roles") is not True
            or contract.get("role_exemptions") != []
            or contract.get("source_carriers") != MESH_COMPONENT_FILES
            or contract.get("live_acceptance_required") is not True):
        raise ValueError("EVERY_NODE_TRANSPUTER_AND_TERMINAL_CONTRACT_REQUIRED")
    portable = activation.get("portable_repository", {})
    if (not isinstance(portable, dict) or portable.get("schema") != "qikvrt-portable-repository-obligation/v1"
            or portable.get("format") != "SQLITE3_WITH_CARRIER_META_AND_EVENTS"
            or portable.get("transport_format") != "QIKMESH1"
            or portable.get("transport_role") != "DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY"
            or portable.get("cloud_transport") != "EXPLICIT_AUTHENTICATED_REST"
            or portable.get("contract") != "runtime/self-host/MESH_FILE.md"
            or portable.get("source_files") != MESH_PORTABLE_FILES
            or any(portable.get(key) is not True for key in ("single_persistent_file", "react_html_client",
                "git_and_github_optional_at_runtime", "mobile_file_chooser_fallback_required", "consistency_and_io_metrics_required"))):
        raise ValueError("PORTABLE_MONOLITHIC_REPOSITORY_CONTRACT_REQUIRED")
    storage = activation.get("storage_contract", {})
    if (not isinstance(storage, dict) or storage.get("schema") != "qikvrt-canonical-storage/v1"
            or storage.get("canonical_format") != portable["format"]
            or storage.get("role_scope") != ["REPOSITORY_NODE", "REPOSITORY_CLIENT"]
            or storage.get("identical_bytes_across_roles") is not True
            or storage.get("transport_format") != "QIKMESH1"
            or storage.get("transport_role") != "DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY"
            or storage.get("transport_entry") != "canonical/store.sqlite3"
            or storage.get("transport_mutations_allowed") is not False
            or storage.get("qikmesh_canonical_promotion_allowed") is not False
            or storage.get("predecessor_evidence_transfer") is not False
            or definition.get("monolithic_store") != "SQLITE_CARRIER_AND_EXISTING_NATIVE_LEDGER"
            or definition.get("qikmesh_role") != storage["transport_role"]):
        raise ValueError("ONE_CANONICAL_SQLITE_STORAGE_CONTRACT_REQUIRED")
    required = {MESH_CONTRACT, "tools/qikvrt_self_host.py", "docs/monitor/self-host.mjs", "runtime/self-host/MESH_FILE.md", *MESH_PORTABLE_FILES}
    required.update(MESH_CACHE_SOURCE_FILES)
    required.update(MESH_ROLE_POLICIES)
    required.update(path for paths in MESH_COMPONENT_FILES.values() for path in paths)
    files = definition.get("files")
    if (not isinstance(files, list) or not all(isinstance(path, str) for path in files)
            or len(files) != len(set(files)) or not required <= set(files)
            or definition.get("native_terminal_daemon_included") is not True):
        raise ValueError("MESH_NATIVE_COMPONENT_PACKAGE_REQUIRED")
    invariants = contract.get("invariants", {})
    if not isinstance(invariants, dict) or any(invariants.get(key) is not True for key in MESH_INVARIANTS):
        raise ValueError("MESH_CONTINUITY_INVARIANTS_REQUIRED")
    cache = contract.get("local_repository_cache", {})
    if (not isinstance(cache, dict) or cache.get("schema") != "qikvrt-repository-work-cache-contract/v1"
            or cache.get("source_carriers") != MESH_CACHE_SOURCE_FILES
            or any(cache.get(key) is not True for key in MESH_CACHE_INVARIANTS)
            or cache.get("idle_scope") != "CACHE_WRITER_LOCK_AND_EXACT_SELECTED_GIT_BYTES"
            or cache.get("canonical_idle_state") != "IDLE_STABLE_VALIDATED"
            or cache.get("scope") != MESH_WORK_SCOPE
            or cache.get("native_effect_replication_deferred") is not False
            or cache.get("received_proposals_auto_execute") is not False
            or type(cache.get("max_batch_wire_bytes")) is not int or cache["max_batch_wire_bytes"] != MESH_WORK_MAX):
        raise ValueError("MESH_LOCAL_CACHE_AND_IDLE_TRANSFER_CONTRACT_REQUIRED")
    cases = contract.get("required_fault_cases")
    if (not isinstance(cases, list) or not all(isinstance(case, str) for case in cases)
            or len(cases) != len(set(cases)) or set(cases) != set(MESH_FAULT_CASES)):
        raise ValueError("MESH_FAULT_MODEL_REQUIRED")
    limits = contract.get("acceptance_limits", {})
    if not isinstance(limits, dict) or any(type(limits.get(key)) is not int or limits[key] != value
            for key, value in (("acknowledged_effect_loss", 0), ("duplicate_irreversible_effects", 0),
                               ("concurrent_writers_per_effect", 1))):
        raise ValueError("MESH_EFFECT_SAFETY_LIMITS_REQUIRED")
    if limits.get("quorum_loss_behavior") != "HOLD_WRITES_PRESERVE_CONFIRMED_READS":
        raise ValueError("MESH_SAFE_PARTITION_BEHAVIOR_REQUIRED")
    for field in ("rto_ms", "user_visible_interruption_slo_ms"):
        value = limits.get(field)
        if field not in limits or (value is not None and (type(value) is not int or value < 0)):
            raise ValueError("MESH_WORKLOAD_BOUND_AVAILABILITY_LIMIT_REQUIRED")
    deployment = activation.get("deployment_contract", {})
    if (not isinstance(deployment, dict)
            or deployment.get("schema") != "qikvrt-node-client-monolithic-deployment/v1"
            or deployment.get("role_scope") != ["REPOSITORY_NODE", "REPOSITORY_CLIENT"]
            or deployment.get("role_exemptions") != []
            or deployment.get("same_store_format_and_starter") is not True
            or deployment.get("terminal") != "REACT_HTML_PASSIVE_INPUT_OUTPUT_OPENED_ON_DEMAND"
            or deployment.get("runtime_adapter_required") is not True
            or deployment.get("live_acceptance_required") is not True
            or deployment.get("app_store_required") is not False
            or deployment.get("git_required_at_runtime") is not False):
        raise ValueError("NODE_CLIENT_MONOLITHIC_PASSIVE_DEPLOYMENT_CONTRACT_REQUIRED")
    access_path = "runtime/self-host/AI_ACCESS.json"
    required.add(access_path)
    component_hashes = {}
    for name in sorted(required):
        path = root / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
            raise ValueError("MESH_REGULAR_SOURCE_COMPONENT_REQUIRED")
        component_hashes[name] = digest(path.read_bytes())
    access = json.loads((root / access_path).read_bytes())
    if (access.get("schema") != "qikvrt-native-access-source/v1"
            or access.get("discovery", {}).get("path") != "/.well-known/qik-vrt"
            or any(access.get("requirements", {}).get(k) is not False for k in
                   ("github_write_identity", "browser_login", "anonymous_writes_allowed"))
            or access.get("requirements", {}).get("private_scoped_native_capability") is not True
            or access.get("runtime", {}).get("ledger") != "src/qikvrt_temdd_event_ledger.py"
            or access_path not in definition.get("files", [])):
        raise ValueError("PROVIDER_INDEPENDENT_SCOPED_NATIVE_ACCESS_REQUIRED")
    if contract.get("authority_succession_policy") != MESH_ROLE_POLICIES[0] + "#/authority_succession":
        raise ValueError("MESH_IRREVERSIBLE_AUTHORITY_SUCCESSION_REQUIRED")
    roles = deployment_roles(root, {})
    return {"schema": "qikvrt-node-bus-contract-check/v1", "state": "SOURCE_OBLIGATIONS_BOUND",
            "authority_repository": roles["authority_repository"], "automatic_authority_failback_allowed": False,
            "entry_contract": {
                "github_push_required_for_native_mesh": False,
                "github_write_identity_scope": "GITHUB_REPOSITORY_MUTATIONS_ONLY",
                "native_adapter_without_github": "none",
                "proposal_ingress": "/api/mesh-work/batch",
                "proposal_readback": "/api/mesh-work/readback/<batch_id>/<challenge>",
                "proposal_admission": "PRIVATE_PEER_KEY_AND_EXACT_SOURCE_PINS",
                "owner_input_adapter": "OwnerREST",
                "runtime_discovery": access["discovery"]["path"],
                "source_access_contract": access_path,
                "public_native_transport": "EXISTING_S1_FIXED_LOOPBACK_BRIDGE",
                "live_endpoint": "UNKNOWN", "peer_admission": "UNKNOWN",
                "native_execution": "NOT_ESTABLISHED",
            },
            "contract_sha256": digest(raw), "source_component_sha256": component_hashes,
            "required_fault_cases": list(MESH_FAULT_CASES), "native_runtime_executed": False,
            "all_node_runtime_verified": False, "write_failover_verified": False,
            "application_transparency_verified": False, "effect_ack_done": False}


def verify_react_assets(root):
    """Recheck the static dependency and each unmodified upstream source slice."""
    lock = json.loads((root / "runtime/self-host/REACT_LOCK.json").read_bytes())
    if lock.get("schema") != "qikvrt-static-react-lock/v1":
        raise ValueError("STATIC_REACT_LOCK_REQUIRED")
    bundle = (root / "docs/monitor/react-runtime.js").read_bytes()
    license_bytes = (root / "docs/monitor/REACT_LICENSE.txt").read_bytes()
    if (lock["bundle"]["path"] != "docs/monitor/react-runtime.js"
            or len(bundle) != lock["bundle"]["bytes"] or digest(bundle) != lock["bundle"]["sha256"]
            or lock["license"]["path"] != "docs/monitor/REACT_LICENSE.txt"
            or digest(license_bytes) != lock["license"]["sha256"]
            or b"MIT License" not in license_bytes or license_bytes not in bundle):
        raise ValueError("STATIC_REACT_BYTES_OR_LICENSE_DRIFT")
    if [item["module"] for item in lock["sources"]] != ["react", "react-dom", "scheduler", "react-dom/client"]:
        raise ValueError("STATIC_REACT_MODULE_SET_DRIFT")
    for item in lock["sources"]:
        marker = ('factories[' + json.dumps(item["module"]) + ']=function(module,exports,require){\n').encode()
        if bundle.count(marker) != 1 or item["license"] != "MIT":
            raise ValueError("STATIC_REACT_SOURCE_BINDING_DRIFT")
        offset = bundle.index(marker) + len(marker)
        source = bundle[offset:offset + item["bytes"]]
        if digest(source) != item["sha256"] or bundle[offset + item["bytes"]:offset + item["bytes"] + 4] != b"\n};\n":
            raise ValueError("STATIC_REACT_SOURCE_BINDING_DRIFT")
    return {"state": "STATIC_REACT_BYTES_VERIFIED", "bundle_sha256": digest(bundle), "effect_ack_done": False}


def portable_history(root, output, head, tree):
    """Export exactly HEAD's complete ancestry; never fetch missing objects."""
    private_output(output, (root,))
    environment = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1",
                       GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="")
    def local(*args):
        return subprocess.check_output(["git", "-c", "protocol.allow=never", "-C", str(root), *args],
                                       env=environment, stderr=subprocess.PIPE, timeout=300)
    if (local("rev-parse", "HEAD").decode().strip() != head
            or local("rev-parse", "HEAD^{tree}").decode().strip() != tree):
        raise ValueError("EXACT_SOURCE_BINDING_MISMATCH")
    if local("rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ValueError("COMPLETE_GIT_HISTORY_REQUIRED_SHALLOW_SOURCE")
    closure = local("rev-list", "--objects", "--missing=print", "HEAD")
    if any(line.startswith(b"?") for line in closure.splitlines()):
        raise ValueError("COMPLETE_GIT_HISTORY_REQUIRED_MISSING_OBJECTS")
    # Preserve historical format defects as failures, never rewrite old objects.
    local("fsck", "--strict", "--no-reflogs", "HEAD")
    local("bundle", "create", str(output), "HEAD")
    output.chmod(0o600)
    local("bundle", "verify", str(output))
    with output.open("rb") as source:
        pin = hashlib.file_digest(source, "sha256").hexdigest()
        os.fsync(source.fileno())
    return {"included": True, "scope": "EXACT_HEAD_REACHABLE_ANCESTRY_AND_OBJECTS",
            "file": output.name, "sha256": pin, "bytes": output.stat().st_size,
            "commits": int(local("rev-list", "--count", "HEAD")),
            "other_refs_included": False, "remote_configuration_included": False,
            "lfs_payloads_or_submodule_repositories_included": False}


def portable(root, output, head, tree, *, include_git_history=False):
    """One canonical SQLite image with the complete original source tree.

    QIKMESH1 is only its derived byte-exact transport; it is not another ledger.
    Git is needed at build time, never for opening or restoring either file.
    """
    if git(root, "rev-parse", "HEAD").decode() != head or git(root, "rev-parse", "HEAD^{tree}").decode() != tree:
        raise ValueError("EXACT_SOURCE_BINDING_MISMATCH")
    git(root, "diff", "--quiet", head, "--")
    verify_react_assets(root)
    files = []
    for record in git(root, "ls-tree", "-r", "-z", head).split(b"\0"):
        if not record:
            continue
        metadata, name = record.split(b"\t", 1)
        mode, kind, sha = metadata.decode().split()
        if kind != "blob":
            raise ValueError("PORTABLE_SUBMODULE_EXPORT_NOT_DEFINED")
        files.append({"path": name.decode("utf-8"), "mode": mode, "sha": sha})
    private_output(output, (root,))
    output.mkdir(mode=0o700)
    try:
        with tempfile.TemporaryDirectory(prefix="qikvrt-source-carrier-") as temp:
            package = Path(temp) / "package"
            receipt = freeze(root, package, head, tree)
            pin = receipt["manifest_sha256"]
            bootstrap = output / ".bootstrap"; bootstrap.mkdir(mode=0o700)
            (bootstrap / "temdd").mkdir(mode=0o700)
            store = bootstrap / "temdd/events.sqlite3"
            pack_monolith(package, pin, store)
            load_source(package, "qikvrt_effect_ack_http_terminal")
            native = load_source(package, "qikvrt_temdd_event_ledger")
            ledger = native.Ledger(bootstrap, {"repository":"ingolf-lohmann/qik-vrt", "pr":1, "head":head, "tree":tree})
            ledger.close()
            with contextlib.closing(sqlite3.connect(store)) as db:
                db.execute("PRAGMA journal_mode=DELETE")
                db.execute("PRAGMA synchronous=FULL")
                with db:
                    db.execute("CREATE TABLE repository_files (path TEXT PRIMARY KEY, mode TEXT NOT NULL, git_blob_sha1 TEXT NOT NULL, body BLOB NOT NULL)")
                    for item in files:
                        body = subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", item["sha"]])
                        if git_blob_digest(body) != item["sha"]: raise ValueError("SOURCE_BLOB_DRIFT")
                        db.execute("INSERT INTO repository_files VALUES (?,?,?,?)", (item["path"], item["mode"], item["sha"], body))
            info = inspect_stable_monolith(store, pin)
            target = output / "repository.sqlite3"
            store.rename(target); shutil.rmtree(bootstrap); sync_directory(output)
            data = dict(info, root=str(root), output=str(output), store=str(target), head=head, tree=tree,
                        repositoryId="qikvrt-source-" + head, files=files)
            raw = subprocess.check_output(["node", str(root / "docs/monitor/mesh-file-store.mjs"), "portable-export"],
                                          input=raw_json(data), timeout=300)
            result = json.loads(raw)
            result.update(canonical_file="repository.sqlite3", canonical_sha256=info["file_sha256"],
                          manifest_sha256=pin, source_files=len(files), full_tree_verified=True,
                          git_history={"included": False, "scope": "CURRENT_TREE_ONLY",
                              "missing": ["ANCESTOR_COMMITS_AND_HISTORICAL_OBJECTS", "OTHER_REFS"],
                              "lfs_payloads_or_submodule_repositories_included": False})
            if include_git_history:
                result["git_history"] = portable_history(root, output / "repository.bundle", head, tree)
                sync_directory(output)
            return result
    except BaseException:
        shutil.rmtree(output)
        raise


def freeze(root, output, head, tree, browser_assets=None, firefox_package="firefox-esr"):
    """Export committed bytes only. Tar metadata is deterministic; no credentials."""
    if git(root, "rev-parse", "HEAD").decode() != head or git(root, "rev-parse", "HEAD^{tree}").decode() != tree:
        raise ValueError("EXACT_SOURCE_BINDING_MISMATCH")
    git(root, "diff", "--quiet", head, "--")
    definition = json.loads(git(root, "show", head + ":" + DEFINITION))
    if definition.get("role_policy"): deployment_roles(root)
    node, python = runtime("node"), runtime(sys.executable)
    if not node["version"].startswith("v24.") or not python["version"].startswith("Python 3.12.") or sys.platform != "linux":
        raise ValueError("LINUX_NODE24_PYTHON312_REQUIRED")
    manifest = {"schema": "qikvrt-self-host-package/v1", "package_version": definition["version"],
                "source_repository": definition["source_repository"], "source_head": head, "source_tree": tree,
                "runtime": {"node": node, "python": python, "platform": platform.machine(), "system": "linux"},
                "files": {}, "effect_ack_done": False,
                "terminal_scope": "RECOVERED_HISTORICAL_TEMDD_DAEMON_AND_FIREFOX_NOVNC_SOURCES; SEALED_S1_ADAPTER",
                "native_terminal_daemon_included": definition.get("native_terminal_daemon_included", False)}
    if browser_assets is not None:
        browser_version = subprocess.check_output([str(firefox_binary(firefox_package)), "--version"],
            timeout=10, stderr=subprocess.DEVNULL).decode().strip()
        if firefox_package == "firefox" and not firefox_release_minimum_satisfied(browser_version):
            raise ValueError("FIREFOX_RELEASE_BELOW_OWNER_MINIMUM")
        manifest["browser_runtime"] = {"executables": browser_executables(firefox_package), "files": [],
            "firefox_command": firefox_package,
            "asset_origin": "OPERATOR_PROVISIONED_DEBIAN_NOVNC_SOURCE; EXACT_EXPORTED_BYTES",
            "firefox_version": browser_version}
        if not (browser_assets / "vnc.html").is_file() or not (browser_assets / "core/rfb.js").is_file():
            raise ValueError("COMPLETE_NOVNC_SOURCE_REQUIRED")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
        for name in sorted(definition["files"]):
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("UNSAFE_PACKAGE_PATH")
            data = subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", head + ":" + name], timeout=30)
            entry = git(root, "ls-tree", head, "--", name).decode().split()[0]
            if entry not in {"100644", "100755"}:
                raise ValueError("REGULAR_COMMITTED_FILES_REQUIRED")
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o755 if entry == "100755" else 0o644)
            manifest["files"][name] = {"bytes": len(data), "sha256": digest(data), "mode": entry}
        if browser_assets is not None:
            # Debian's noVNC tree contains distribution-managed JS links.
            # Freeze their resolved source bytes as regular files, with no key,
            # certificate, credential, VCS or executable payload admitted.
            suffixes = {".html", ".js", ".css", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico",
                        ".woff", ".woff2", ".ttf", ".eot", ".oga", ".ogg", ".wav", ".mp3", ".json", ".txt", ".map"}
            allowed = (browser_assets.resolve(), Path('/usr/share/javascript'), Path('/usr/share/nodejs'))
            def admitted(source):
                resolved = source.resolve(strict=True)
                if not any(resolved == root or root in resolved.parents for root in allowed):
                    raise ValueError("NOVNC_DISTRIBUTION_SOURCE_LINK_ESCAPED")
            sources = []
            for parent, directories, filenames in os.walk(browser_assets, followlinks=True):
                admitted(Path(parent))
                if len(Path(parent).relative_to(browser_assets).parts) > 16:
                    raise ValueError("NOVNC_SOURCE_LINK_CYCLE_OR_DEPTH")
                directories[:] = sorted(p for p in directories if not p.startswith('.'))
                sources.extend(Path(parent) / name for name in filenames)
                if len(sources) > 4096: raise ValueError("BOUNDED_NOVNC_FILESET_REQUIRED")
            for source in sorted(sources):
                relative = source.relative_to(browser_assets)
                if any(p.startswith(".") for p in relative.parts) or not source.is_file() or source.suffix not in suffixes:
                    continue
                admitted(source)
                data = source.read_bytes()
                if len(data) > 8 * 1024 * 1024: raise ValueError("BOUNDED_NOVNC_ASSET_REQUIRED")
                name = "runtime/self-host/novnc/" + relative.as_posix()
                dest = output / name; dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data); dest.chmod(0o644)
                manifest["files"][name] = {"bytes": len(data), "sha256": digest(data), "mode": "100644"}
                manifest["browser_runtime"]["files"].append(name)
            copyright_file = Path("/usr/share/doc/novnc/copyright")
            if not copyright_file.is_file(): raise ValueError("NOVNC_DISTRIBUTION_RIGHTS_REQUIRED")
            name = "runtime/self-host/novnc/DEBIAN_COPYRIGHT.txt"
            data = copyright_file.read_bytes(); (output / name).write_bytes(data); (output / name).chmod(0o644)
            manifest["files"][name] = {"bytes": len(data), "sha256": digest(data), "mode": "100644"}
            manifest["browser_runtime"]["files"].append(name)
            manifest["browser_runtime"]["files"].sort()
        verify_react_assets(output)
        manifest["mesh_node_contract_sha256"] = mesh_contract(output, definition)["contract_sha256"]
        data = raw_json(manifest)
        (output / "MANIFEST.json").write_bytes(data)
        (output / "MANIFEST.json").chmod(0o644)
        with tarfile.open(str(output) + ".tar", "w", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(p for p in output.rglob("*") if p.is_file()):
                info = archive.gettarinfo(str(path), path.relative_to(output).as_posix())
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                with path.open("rb") as source:
                    archive.addfile(info, source)
        return {"state": "PACKAGE_FROZEN", "manifest_sha256": digest(data), "source_head": head,
                "source_tree": tree, "archive_sha256": digest(Path(str(output) + ".tar").read_bytes()),
                "effect_ack_done": False}
    except BaseException:
        shutil.rmtree(output)
        raise


def verify(package, expected, *, check_runtime=True):
    raw = (package / "MANIFEST.json").read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", expected or "") or digest(raw) != expected:
        raise ValueError("PACKAGE_MANIFEST_PIN_MISMATCH")
    value = json.loads(raw)
    if value.get("schema") != "qikvrt-self-host-package/v1" or value.get("effect_ack_done") is not False:
        raise ValueError("PACKAGE_SCHEMA_MISMATCH")
    for key in ("source_head", "source_tree"):
        if not re.fullmatch(r"[a-f0-9]{40}", value.get(key, "")):
            raise ValueError("EXACT_SOURCE_BINDING_REQUIRED")
    actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != set(value["files"]) | {"MANIFEST.json"}:
        raise ValueError("PACKAGE_INVENTORY_MISMATCH")
    for name, entry in value["files"].items():
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("UNSAFE_PACKAGE_PATH")
        path = package / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("PACKAGE_SYMLINK_FORBIDDEN")
        raw = path.read_bytes()
        if (entry["bytes"] != len(raw) or entry["sha256"] != digest(raw)
                or stat.S_IMODE(path.stat().st_mode) != (0o755 if entry["mode"] == "100755" else 0o644)):
            raise ValueError("PACKAGE_ARTIFACT_MISMATCH")
    definition = json.loads((package / DEFINITION).read_bytes())
    browser = value.get("browser_runtime")
    firefox_package = browser.get("firefox_command", "firefox-esr") if isinstance(browser, dict) else "firefox-esr"
    if browser is not None and (not isinstance(browser, dict)
            or set(browser.get('executables', {})) != set(browser_commands(firefox_package))
            or not isinstance(browser.get('files'), list)
            or len(browser['files']) != len(set(browser['files']))
            or not {'runtime/self-host/novnc/vnc.html', 'runtime/self-host/novnc/core/rfb.js',
                    'runtime/self-host/novnc/DEBIAN_COPYRIGHT.txt'} <= set(browser['files'])):
        raise ValueError("BROWSER_RUNTIME_SCHEMA_MISMATCH")
    extra = set(browser["files"]) if browser is not None else set()
    if any(not p.startswith("runtime/self-host/novnc/") for p in extra):
        raise ValueError("NOVNC_SOURCE_CONFINEMENT_REQUIRED")
    if set(value["files"]) != set(definition["files"]) | extra or definition["version"] != value["package_version"]:
        raise ValueError("PACKAGE_DEFINITION_MISMATCH")
    if value.get("mesh_node_contract_sha256") != mesh_contract(package, definition)["contract_sha256"]:
        raise ValueError("MESH_NODE_CONTRACT_BINDING_MISMATCH")
    if browser is not None and check_runtime and browser["executables"] != browser_executables(firefox_package):
        raise ValueError("BROWSER_EXECUTABLE_BINDING_MISMATCH")
    if check_runtime and value["runtime"] != {"node": runtime("node"), "python": runtime(sys.executable),
                            "platform": platform.machine(), "system": sys.platform}:
        raise ValueError("RUNTIME_EXECUTABLE_BINDING_MISMATCH")
    return value



def authority_succession(policy):
    """Validate irreversible role policy; this never performs a native election."""
    value = policy.get("authority_succession", {})
    expected = {"authority_loss_irreversible": True, "automatic_failback_allowed": False,
        "retired_authority_repromotion_allowed": False, "successor_persists_after_predecessor_rejoin": True,
        "successor_subject_to_same_loss_rule": True, "promotion_requires_safe_quorum": True,
        "promotion_requires_original_journal_catch_up": True,
        "promotion_requires_strictly_newer_fencing_epoch": True,
        "previous_writer_fenced_before_successor_effects": True,
        "public_read_failure_is_revocation_proof": False, "native_transition_or_failover_inferred": False}
    if (not isinstance(value, dict)
            or value.get("schema") != "qikvrt-irreversible-authority-succession/v1"
            or any(value.get(key) is not expected_value for key, expected_value in expected.items())
            or value.get("contact_loss_evidence") != "EXPIRED_QUORUM_BOUND_LEASE_OR_CERTIFIED_REVOCATION"
            or value.get("rejoin_role") != "MIRROR_AFTER_AUTHENTICATED_CATCH_UP"
            or value.get("quorum_loss_behavior") != "HOLD_WRITES_PRESERVE_CONFIRMED_READS"):
        raise ValueError("MESH_IRREVERSIBLE_AUTHORITY_SUCCESSION_REQUIRED")
    retired = value.get("retired_authorities")
    if not isinstance(retired, list) or not retired:
        raise ValueError("MESH_RETIRED_AUTHORITY_IDENTITY_REQUIRED")
    identities = []
    for item in retired:
        if (not isinstance(item, dict)
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item.get("repository", ""))
                or item.get("authority_eligibility") != "REVOKED_IRREVERSIBLY"
                or item.get("rejoin_role") != "MIRROR_AFTER_AUTHENTICATED_CATCH_UP"):
            raise ValueError("MESH_RETIRED_AUTHORITY_IDENTITY_REQUIRED")
        identities.append(item["repository"])
    if len(identities) != len(set(identities)):
        raise ValueError("MESH_RETIRED_AUTHORITY_IDENTITY_REQUIRED")
    if policy["canonical_upstream"]["repository"] in identities:
        raise ValueError("REVOKED_AUTHORITY_REPROMOTION_FORBIDDEN")
    return set(identities)


class AuthoritySuccessionModel:
    """Crash-durable *local reference model*, never a distributed election service.

    SQLite serializes the modeled voters, fencing register and effect sink.
    Reachability, authenticated catch-up/certificates and time are supplied
    simulation inputs. No network, signature verification, production writer or
    native replication is installed. See MESH_ACTIVATION's explicit live gap.
    """
    def __init__(self, path, members, authority, lease_until=10):
        self.path = Path(path)
        members = list(members)
        if (len(members) < 2 or len(members) != len(set(members))
                or any(not isinstance(m, str) or not m for m in members)
                or authority not in members or type(lease_until) is not int or lease_until <= 0):
            raise ValueError("MODEL_FIXED_MEMBERSHIP_REQUIRED")
        private_path(self.path.parent, directory=True)
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
        private_path(self.path)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS succession_model (id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS succession_votes (epoch INTEGER NOT NULL, voter TEXT NOT NULL, candidate TEXT NOT NULL, PRIMARY KEY(epoch,voter))")
            db.execute("CREATE TABLE IF NOT EXISTS succession_effects (seq INTEGER PRIMARY KEY, unit TEXT NOT NULL, event TEXT NOT NULL, payload BLOB NOT NULL, record TEXT NOT NULL, UNIQUE(unit,event))")
            row = db.execute("SELECT state FROM succession_model WHERE id=1").fetchone()
            if row is None:
                state = {"schema": "qikvrt-authority-succession-local-model/v1", "members": members,
                    "initial_authority": authority, "initial_lease": lease_until,
                    "authority": authority, "epoch": 1, "retired": [], "now": 0,
                    "lease_until": lease_until, "index": 0, "digest": "0" * 64,
                    "caught_up": {m: [0, "0" * 64] for m in members},
                    "replicas": {m: [0, "0" * 64] for m in members}}
                self.save(db, state)
                db.executemany("INSERT INTO succession_votes VALUES (1,?,?)", [(m, authority) for m in members])
            else:
                state = json.loads(row[0])
                if (state["members"] != members or state["initial_authority"] != authority
                        or state["initial_lease"] != lease_until):
                    raise ValueError("MODEL_MEMBERSHIP_OR_GENESIS_MISMATCH")

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def save(db, state):
        db.execute("INSERT OR REPLACE INTO succession_model VALUES (1,?)", (mesh_wire(state).decode(),))

    @staticmethod
    def quorum(state, voters):
        if not isinstance(voters, (list, tuple)):
            raise ValueError("MODEL_DISTINCT_MEMBER_VOTES_REQUIRED")
        voters = list(voters)
        if len(voters) != len(set(voters)) or not set(voters) <= set(state["members"]):
            raise ValueError("MODEL_DISTINCT_MEMBER_VOTES_REQUIRED")
        if len(voters) <= len(state["members"]) // 2:
            raise ValueError("NO_QUORUM_HOLD")
        return voters

    @staticmethod
    def eligible(state, node):
        if node not in state["members"] or node in state["retired"]:
            raise ValueError("RETIRED_OR_UNAUTHORIZED_CANDIDATE")

    def execute(self, now, operation):
        # Time/expiration survives a rejected command. A savepoint rolls back
        # that command's partial SQL writes, never the qualified retirement.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = json.loads(db.execute("SELECT state FROM succession_model WHERE id=1").fetchone()[0])
            if type(now) is not int or now < state["now"]:
                raise ValueError("MODEL_CLOCK_REGRESSION")
            state["now"] = now
            if state["authority"] is not None and now >= state["lease_until"]:
                state["retired"].append(state["authority"])
                state["authority"] = None
            self.save(db, state)
            db.execute("SAVEPOINT command")
            try:
                result = operation(db, state)
            except ValueError:
                db.execute("ROLLBACK TO command")
                db.execute("RELEASE command")
                db.commit()
                raise
            self.save(db, state)
            db.execute("RELEASE command")
            db.commit()
            return result

    def tick(self, now):
        return self.execute(now, lambda db, state: dict(state))

    def catch_up(self, node, now, index, journal_digest, *, authenticated):
        def apply(db, state):
            if (authenticated is not True or node not in state["members"]
                    or [index, journal_digest] != [state["index"], state["digest"]]):
                raise ValueError("MODEL_AUTHENTICATED_ORIGINAL_JOURNAL_REQUIRED")
            state["caught_up"][node] = [index, journal_digest]
            state["replicas"][node] = [index, journal_digest]
            return {"role": "AUTHORITY" if state["authority"] == node else "MIRROR",
                    "retired": node in state["retired"], "epoch": state["epoch"]}
        return self.execute(now, apply)

    def vote(self, voter, candidate, epoch, now):
        def apply(db, state):
            self.eligible(state, candidate)
            if voter not in state["members"] or type(epoch) is not int or epoch <= state["epoch"]:
                raise ValueError("MODEL_NEW_EPOCH_MEMBER_VOTE_REQUIRED")
            if state["authority"] is not None:
                raise ValueError("MODEL_UNEXPIRED_AUTHORITY_LEASE")
            if state["caught_up"][candidate] != [state["index"], state["digest"]]:
                raise ValueError("MODEL_CANDIDATE_JOURNAL_STALE")
            highest = db.execute("SELECT MAX(epoch) FROM succession_votes WHERE voter=?", (voter,)).fetchone()[0]
            previous = db.execute("SELECT candidate FROM succession_votes WHERE epoch=? AND voter=?", (epoch, voter)).fetchone()
            if (highest is not None and epoch < highest) or (previous and previous[0] != candidate):
                raise ValueError("MODEL_PERSISTENT_VOTE_CONFLICT")
            db.execute("INSERT OR IGNORE INTO succession_votes VALUES (?,?,?)", (epoch, voter, candidate))
            return {"voter": voter, "candidate": candidate, "epoch": epoch}
        return self.execute(now, apply)

    def promote(self, candidate, epoch, voters, now, *, expected_epoch, lease_until):
        def apply(db, state):
            self.eligible(state, candidate)
            voters_checked = self.quorum(state, voters)
            if (state["authority"] is not None or type(epoch) is not int
                    or epoch <= state["epoch"] or type(expected_epoch) is not int or expected_epoch != state["epoch"]):
                raise ValueError("MODEL_FENCE_COMPARE_AND_SWAP_REJECTED")
            if (type(lease_until) is not int or lease_until <= now
                    or state["caught_up"][candidate] != [state["index"], state["digest"]]):
                raise ValueError("MODEL_CURRENT_JOURNAL_AND_FUTURE_LEASE_REQUIRED")
            for voter in voters_checked:
                vote = db.execute("SELECT epoch,candidate FROM succession_votes WHERE voter=? ORDER BY epoch DESC LIMIT 1", (voter,)).fetchone()
                if vote != (epoch, candidate):
                    raise ValueError("MODEL_CURRENT_QUORUM_CERTIFICATE_REQUIRED")
            state.update(authority=candidate, epoch=epoch, lease_until=lease_until)
            return {"node": candidate, "epoch": epoch}
        return self.execute(now, apply)

    def current_writer(self, state, node, epoch, voters):
        self.quorum(state, voters)
        if (type(epoch) is not int or node != state["authority"] or epoch != state["epoch"] or node in state["retired"]
                or state["now"] >= state["lease_until"]):
            raise ValueError("MODEL_STALE_OR_RETIRED_WRITER_FENCED")

    def renew(self, node, epoch, voters, now, lease_until):
        def apply(db, state):
            self.current_writer(state, node, epoch, voters)
            if type(lease_until) is not int or lease_until <= state["lease_until"]:
                raise ValueError("MODEL_STRICT_LEASE_EXTENSION_REQUIRED")
            state["lease_until"] = lease_until
        return self.execute(now, apply)

    def revoke(self, node, epoch, voters, now, *, certificate_verified):
        def apply(db, state):
            self.current_writer(state, node, epoch, voters)
            if certificate_verified is not True:
                raise ValueError("MODEL_VERIFIED_REVOCATION_REQUIRED")
            state["retired"].append(node)
            state["authority"] = None
        return self.execute(now, apply)

    def write(self, node, epoch, voters, now, unit, event, payload):
        def apply(db, state):
            self.current_writer(state, node, epoch, voters)
            if not isinstance(payload, bytes) or not isinstance(unit, str) or not unit or not isinstance(event, str) or not event:
                raise ValueError("MODEL_ORIGINAL_EFFECT_ID_AND_BYTES_REQUIRED")
            old = db.execute("SELECT payload,record FROM succession_effects WHERE unit=? AND event=?", (unit, event)).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError("MODEL_EFFECT_ID_CONFLICT")
                return dict(json.loads(old[1]), duplicate=True)
            record = {"seq": state["index"] + 1, "unit": unit, "event": event,
                      "payload_sha256": digest(payload), "previous": state["digest"],
                      "authority": node, "epoch": epoch}
            record["digest"] = digest(mesh_wire(record))
            db.execute("INSERT INTO succession_effects VALUES (?,?,?,?,?)", (record["seq"], unit, event, payload, mesh_wire(record).decode()))
            state.update(index=record["seq"], digest=record["digest"])
            # Modeled replication and ACK are one local transaction. This is
            # deliberately NOT evidence of distributed native-effect durability.
            for voter in voters:
                state["replicas"][voter] = [state["index"], state["digest"]]
            state["caught_up"][node] = [state["index"], state["digest"]]
            return dict(record, duplicate=False)
        return self.execute(now, apply)

    def read(self):
        """Confirmed local prefix stays readable without write quorum."""
        with self.connect() as db:
            return [(json.loads(record), payload) for record, payload in
                    db.execute("SELECT record,payload FROM succession_effects ORDER BY seq")]

    def view(self):
        with self.connect() as db:
            return json.loads(db.execute("SELECT state FROM succession_model WHERE id=1").fetchone()[0])


def deployment_roles(root, environment=None):
    """Resolve the current contract; old defaults/overrides cannot select Authority."""
    root = Path(root)
    policy_path = "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
    raw = (root / policy_path).read_bytes()
    policy = json.loads(raw)
    owner = json.loads((root / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_bytes())["mesh_authority"]
    authority, mirror = policy["canonical_upstream"], policy["mirror"]
    if (policy.get("status") != "NORMATIVE" or authority.get("role") != "AUTHORITY"
            or mirror.get("role") != "MIRROR" or authority["repository"] == mirror["repository"]
            or owner["authority_repository"] != authority["repository"]
            or owner.get("role_policy_path") != policy_path):
        raise ValueError("DEPLOYMENT_ROLE_CONTRACT_MISMATCH")
    retired = authority_succession(policy)
    if owner.get("former_authority_repository") not in retired:
        raise ValueError("MESH_RETIRED_AUTHORITY_IDENTITY_REQUIRED")
    for item in (authority, mirror):
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item["repository"])
                or item["canonical_https_url"] != "https://github.com/" + item["repository"] + ".git"):
            raise ValueError("DEPLOYMENT_ROLE_CONTRACT_MISMATCH")
    urls = {"QIKVRT_AUTHORITY_URL": authority["canonical_https_url"],
            "QIKVRT_MIRROR_URL": mirror["canonical_https_url"]}
    environment = os.environ if environment is None else environment
    if any(environment.get(key, value) != value for key, value in urls.items()):
        raise ValueError("DEPLOYMENT_ROLE_OVERRIDE_MISMATCH")
    return {"authority_repository": authority["repository"], "mirror_repository": mirror["repository"],
            "authority_url": urls["QIKVRT_AUTHORITY_URL"], "mirror_url": urls["QIKVRT_MIRROR_URL"],
            "role_policy_sha256": digest(raw), "native_activation_inferred": False}


def delivery_verify(directory, expected):
    """Verify delivered bytes without a Docker engine or executing the archived source."""
    directory = Path(directory).resolve(strict=True)
    raw = (directory / "DELIVERY.json").read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", expected or "") or digest(raw) != expected:
        raise ValueError("RUNTIME_DELIVERY_PIN_MISMATCH")
    value = json.loads(raw)
    required = {"runtime-image.tar.gz", "package.tar", "PACKAGE_BUILD_RECEIPT.json",
                "RUNTIME_PACKAGE_READBACK.json", "RUNTIME_IMAGE.json", "LOADED_IMAGE.json",
                "IMAGE_LOAD_READBACK.txt", "DISTRIBUTION_PACKAGES.tsv"}
    if (value.get("schema") != "qikvrt-firefox-runtime-delivery/v1"
            or value.get("os") != "linux" or value.get("architecture") not in {"amd64", "arm64"}
            or value.get("effect_ack_done") is not False or value.get("public_https_verified") is not False
            or set(value["files"]) != required
            or any(not re.fullmatch(r"[a-f0-9]{40}", value.get(key, "")) for key in ("source_head", "source_tree"))
            or not re.fullmatch(r"sha256:[a-f0-9]{64}", value.get("runtime_image_id", ""))):
        raise ValueError("RUNTIME_DELIVERY_SCHEMA_MISMATCH")
    for name, entry in value["files"].items():
        path = directory / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size != entry["bytes"]:
            raise ValueError("RUNTIME_DELIVERY_FILE_MISMATCH")
        with path.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != entry["sha256"]:
                raise ValueError("RUNTIME_DELIVERY_FILE_MISMATCH")
    original = json.loads((directory / "RUNTIME_IMAGE.json").read_bytes())[0]
    loaded = json.loads((directory / "LOADED_IMAGE.json").read_bytes())[0]
    if (original["Id"] != value["runtime_image_id"] or loaded["Id"] != original["Id"]
            or original["RootFS"] != loaded["RootFS"] or original["Os"] != value["os"]
            or original["Architecture"] != value["architecture"]):
        raise ValueError("RUNTIME_DELIVERY_IMAGE_MISMATCH")
    # The outer image digest binds all layers; verify the saved image identity/config too.
    with tarfile.open(directory / "runtime-image.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
        if (len({m.name for m in members}) != len(members)
                or any(m.issym() or m.islnk() or not (m.isfile() or m.isdir())
                       or m.name.startswith("/") or ".." in Path(m.name).parts for m in members)):
            raise ValueError("UNSAFE_RUNTIME_IMAGE_ARCHIVE")
        records = json.load(archive.extractfile("manifest.json"))
        if len(records) != 1:
            raise ValueError("RUNTIME_DELIVERY_IMAGE_MISMATCH")
        record = records[0]
        config = archive.extractfile(record["Config"]).read()
        if ("sha256:" + digest(config) != original["Id"]
                or json.loads(config)["rootfs"]["diff_ids"] != original["RootFS"]["Layers"]
                or len(record["Layers"]) != len(original["RootFS"]["Layers"])
                or any(not archive.getmember(name).isfile() for name in record["Layers"])):
            raise ValueError("RUNTIME_DELIVERY_IMAGE_MISMATCH")
    with tarfile.open(directory / "package.tar", "r:") as archive:
        members = archive.getmembers()
        if (len({m.name for m in members}) != len(members) or any(not m.isfile()
                or m.name.startswith("/") or ".." in Path(m.name).parts for m in members)):
            raise ValueError("UNSAFE_RUNTIME_PACKAGE_ARCHIVE")
        manifest_raw = archive.extractfile("MANIFEST.json").read()
        manifest = json.loads(manifest_raw)
        if (digest(manifest_raw) != value["manifest_sha256"]
                or manifest["source_head"] != value["source_head"] or manifest["source_tree"] != value["source_tree"]
                or manifest.get("effect_ack_done") is not False
                or set(archive.getnames()) != set(manifest["files"]) | {"MANIFEST.json"}):
            raise ValueError("RUNTIME_DELIVERY_SOURCE_MISMATCH")
        for name, entry in manifest["files"].items():
            member = archive.getmember(name)
            with archive.extractfile(member) as source:
                if member.size != entry["bytes"] or hashlib.file_digest(source, "sha256").hexdigest() != entry["sha256"]:
                    raise ValueError("RUNTIME_DELIVERY_PACKAGE_MISMATCH")
    return {**value, "state": "RUNTIME_DELIVERY_BYTES_VERIFIED", "delivery_sha256": expected,
            "layer_count": len(original["RootFS"]["Layers"]), "runtime_execution_verified": False}


def delivery_load(directory, pin):
    value = delivery_verify(directory, pin)
    docker = shutil.which("docker")
    if not docker:
        raise ValueError("EXISTING_DOCKER_ENGINE_CONNECTION_REQUIRED")
    subprocess.run([docker, "load", "--input", str(Path(directory) / "runtime-image.tar.gz")],
                   check=True, capture_output=True, timeout=300)
    inspected = json.loads(subprocess.check_output([docker, "image", "inspect", value["runtime_image_id"]], timeout=15))[0]
    original = json.loads((Path(directory) / "RUNTIME_IMAGE.json").read_bytes())[0]
    if any(inspected[k] != original[k] for k in ("Id", "Os", "Architecture", "RootFS")):
        raise ValueError("LOADED_RUNTIME_IMAGE_MISMATCH")
    return {**value, "state": "RUNTIME_IMAGE_LOADED_NOT_DEPLOYED", "deployment_performed": False}


def docker_plan(package, pin, config_path, admission_path, admission_pin, delivery, delivery_pin):
    """Use the existing admission and systemd launcher with an immutable dependency image."""
    if sys.platform != "linux":
        raise ValueError("LINUX_DOCKER_HOST_REQUIRED")
    package = Path(package).resolve(strict=True)
    for path in (package, config_path, admission_path, delivery):
        if path is None or not Path(path).is_absolute() or any(c in str(path) for c in ",\r\n\x00") or ".." in Path(path).parts:
            raise ValueError("SAFE_ABSOLUTE_DOCKER_MOUNT_REQUIRED")
    private_path(config_path)
    private_path(admission_path)
    image = delivery_verify(delivery, delivery_pin)
    roles = deployment_roles(package)
    docker = shutil.which("docker")
    if not docker:
        raise ValueError("EXISTING_DOCKER_ENGINE_CONNECTION_REQUIRED")
    server = json.loads(subprocess.check_output([docker, "info", "--format", "{{json .}}"], timeout=15))
    context = json.loads(subprocess.check_output([docker, "context", "inspect"], timeout=15))[0]
    endpoint = os.environ.get("DOCKER_HOST") or context["Endpoints"]["docker"]["Host"]
    if not endpoint.startswith("unix://") or not Path(endpoint[7:]).is_socket():
        raise ValueError("ADMITTED_LOCAL_DOCKER_ENGINE_REQUIRED")
    if server.get("OSType") != "linux" or image["architecture"] != {"x86_64":"amd64", "aarch64":"arm64"}.get(platform.machine()):
        raise ValueError("LINUX_DOCKER_ARCHITECTURE_MISMATCH")
    actual = json.loads(subprocess.check_output([docker, "image", "inspect", image["runtime_image_id"]], timeout=15))[0]
    frozen = json.loads((Path(delivery) / "RUNTIME_IMAGE.json").read_bytes())[0]
    if any(actual[k] != frozen[k] for k in ("Id", "Os", "Architecture", "RootFS")):
        raise ValueError("LOADED_RUNTIME_IMAGE_MISMATCH")
    mount = lambda path: ["--mount", "type=bind,source=" + str(path) + ",target=" + str(path) + ",readonly"]
    base = [docker, "run", "--rm", "--init", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--user", str(os.geteuid()) + ":" + str(os.getegid()),
            "--tmpfs", "/tmp:size=768m,mode=1777", "--shm-size", "256m"]
    verify_argv = base + ["--network", "none"] + mount(package) + [image["runtime_image_id"], "python3", "-B",
        str(package / "tools/qikvrt_self_host.py"), "verify", "--root", str(package), "--manifest-sha256", pin]
    def verifier(root, expected):
        manifest = verify(root, expected, check_runtime=False)
        result = subprocess.run(verify_argv, capture_output=True, timeout=60)
        if result.returncode or json.loads(result.stdout).get("state") != "EXACT_PACKAGE_RUNTIME_VERIFIED":
            raise ValueError("INDEPENDENT_CONTAINER_PACKAGE_VERIFY_FAILED")
        if manifest["source_repository"] != roles["authority_repository"]:
            raise ValueError("DEPLOYMENT_AUTHORITY_SOURCE_MISMATCH")
        return manifest
    plan = admission_plan(package, pin, config_path, admission_path, admission_pin, runtime_verifier=verifier)
    config = json.loads(config_path.read_bytes())
    admission = json.loads(admission_path.read_bytes())
    if admission["public_origin"] != "https://raumzeitterminal.de":
        raise ValueError("EXACT_PRODUCT_ORIGIN_REQUIRED")
    if admission["execution_operation"] != "docker run --network host":
        raise ValueError("EXISTING_DOCKER_EXECUTION_ADMISSION_REQUIRED")
    for port in ("port", "terminal_port"):
        if type(config.get(port)) is not int or not 1024 <= config[port] <= 65535:
            raise ValueError("DOCKER_LOOPBACK_PORT_BINDING_REQUIRED")
    paths = [package, config_path, admission_path, Path(delivery), Path(config["state_dir"])]
    secret_values = [config[key] for key in ("terminal_token_file", "browser_password_file", "github_webhook_secret_file") if config.get(key)]
    for key, field in (("mesh_work_peers", "secret_file"), ("owner_rest_grants", "token_file")):
        entries = config.get(key, [])
        if not isinstance(entries, list) or any(not isinstance(entry, dict) or not isinstance(entry.get(field), str) for entry in entries):
            raise ValueError("DECLARED_PRIVATE_DOCKER_MOUNT_REQUIRED")
        secret_values += [entry[field] for entry in entries]
    if any(not isinstance(value, str) for value in secret_values):
        raise ValueError("DECLARED_PRIVATE_DOCKER_MOUNT_REQUIRED")
    secrets_paths = list(dict.fromkeys(Path(value) for value in secret_values))
    for path in paths + secrets_paths:
        if not path.is_absolute() or any(c in str(path) for c in ",\r\n\x00") or ".." in path.parts:
            raise ValueError("SAFE_ABSOLUTE_DOCKER_MOUNT_REQUIRED")
    if package == Path(config["state_dir"]) or package in Path(config["state_dir"]).parents:
        raise ValueError("SEPARATE_PERSISTENT_DOCKER_VOLUME_REQUIRED")
    for path in secrets_paths:
        private_path(path)
    name = "qikvrt-s1-" + digest(config["node_id"].encode())[:20]
    labels = {"qikvrt.source_head":plan["source_head"], "qikvrt.source_tree":plan["source_tree"],
              "qikvrt.manifest_sha256":pin, "qikvrt.admission_sha256":admission_pin, "qikvrt.node_id":config["node_id"]}
    run_argv = base + ["--network", "host", "--restart", "no", "--name", name]
    for key, value in labels.items():
        run_argv += ["--label", key + "=" + value]
    for path in [package, config_path, *secrets_paths]:
        run_argv += mount(path)
    state = str(Path(config["state_dir"]))
    run_argv += ["--mount", "type=bind,source=" + state + ",target=" + state,
        image["runtime_image_id"], "python3", "-B", str(package / "tools/qikvrt_self_host.py"),
        "run", "--root", str(package), "--manifest-sha256", pin, "--config", str(config_path)]
    return {**plan, "state":"DOCKER_LAUNCHER_BOUND_PENDING_EXTERNAL_ACCEPTANCE",
            "docker_executable":docker, "container_name":name, "container_labels":labels,
            "runtime_image_id":image["runtime_image_id"], "dependency_source_head":image["source_head"],
            "dependency_source_tree":image["source_tree"], "verify_argv":verify_argv, "run_argv":run_argv,
            "roles":roles, "restart_controller":"EXISTING_SYSTEMD_ONLY", "public_origin":admission["public_origin"],
            "predecessor_evidence_transfer":False}


def private_path(path, directory=False):
    if not path.is_absolute() or ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("PRIVATE_PATH_MUST_BE_ABSOLUTE_AND_NOT_SYMLINKED")
    info = path.lstat()
    if (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError("OWNER_ONLY_PRIVATE_PATH_REQUIRED")


def pack_monolith(package, pin, output):
    """Put the sealed S1 carrier into the *existing* native SQLite datastore.

    The recovered ledger later creates its own meta/events tables in this same
    file. No second ledger, input protocol, execution kernel or React dependency.
    This is a native Linux carrier, not an assertion of mobile browser support.
    """
    manifest = verify(package, pin)
    private_output(output, (package,))
    synced_private_file(output, b"")
    try:
        with contextlib.closing(sqlite3.connect(output)) as db:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA application_id=" + str(MONOLITH_APPLICATION_ID))
            db.execute("PRAGMA user_version=1")
            with db:
                db.execute("CREATE TABLE carrier (path TEXT PRIMARY KEY, body BLOB NOT NULL)")
                for name in sorted(set(manifest["files"]) | {"MANIFEST.json"}):
                    db.execute("INSERT INTO carrier VALUES (?,?)", (name, (package / name).read_bytes()))
        with output.open("rb") as stored: os.fsync(stored.fileno())
        fd = os.open(output.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
        return {"schema": "qikvrt-monolithic-store-receipt/v1", "state": "NATIVE_CONTAINER_CREATED",
                "manifest_sha256": pin, "file_sha256": digest(output.read_bytes()),
                "source_head": manifest["source_head"], "source_tree": manifest["source_tree"],
                "role_scope": "NODE_AND_CLIENT_SAME_FORMAT_AND_STARTER",
                "native_runtime_executed": False, "mobile_runtime_verified": False, "effect_ack_done": False}
    except BaseException:
        output.unlink(missing_ok=True)
        raise


@contextlib.contextmanager
def materialized_monolith(store, pin, *, check_runtime=True):
    """Verify all embedded bytes before reconstructing a disposable code cache.

    Only the existing ledger may mutate meta/events; the independently pinned
    carrier remains immutable. Active SQLite journal/WAL files are transactional
    companions, so copying the main file alone while a writer runs is forbidden.
    """
    private_path(store)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(store) + suffix)
        if sidecar.exists() or sidecar.is_symlink(): private_path(sidecar)
    allowed_tables = {"carrier", "meta", "events", "sqlite_sequence", "repository_files"}
    with contextlib.closing(sqlite3.connect(store.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        if (db.execute("PRAGMA application_id").fetchone() != (MONOLITH_APPLICATION_ID,)
                or db.execute("PRAGMA user_version").fetchone() != (1,)
                or db.execute("PRAGMA quick_check").fetchone() != ("ok",)):
            raise ValueError("MONOLITH_FORMAT_OR_INTEGRITY_MISMATCH")
        tables = set()
        for kind, name, table, sql in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master"):
            if kind == "table" and name in allowed_tables and "VIRTUAL" not in (sql or "").upper():
                tables.add(name)
            elif kind == "index" and (name == "events_binding" and table == "events"
                    or name.startswith("sqlite_autoindex_") and table in allowed_tables):
                pass
            else:
                raise ValueError("MONOLITH_UNADMITTED_SCHEMA")
        if "carrier" not in tables:
            raise ValueError("MONOLITH_CARRIER_REQUIRED")
        sizes = dict(db.execute("SELECT path,length(body) FROM carrier"))
        if (not 1 <= len(sizes) <= MONOLITH_MAX_FILES or "MANIFEST.json" not in sizes
                or any(type(size) is not int or not 1 <= size <= MONOLITH_MAX_FILE_BYTES for size in sizes.values())):
            raise ValueError("BOUNDED_MONOLITH_CARRIER_REQUIRED")
        raw = db.execute("SELECT body FROM carrier WHERE path=?", ("MANIFEST.json",)).fetchone()[0]
        if not isinstance(raw, bytes) or digest(raw) != pin:
            raise ValueError("PACKAGE_MANIFEST_PIN_MISMATCH")
        manifest = json.loads(raw)
        if set(sizes) != set(manifest["files"]) | {"MANIFEST.json"}:
            raise ValueError("MONOLITH_CARRIER_INVENTORY_MISMATCH")
        if "repository_files" in tables:
            verify_repository_files(db, manifest["source_tree"])
        with tempfile.TemporaryDirectory(prefix="qikvrt-carrier-") as temp:
            package = Path(temp)
            for name, body in db.execute("SELECT path,body FROM carrier ORDER BY path"):
                if (not isinstance(name, str) or not name or name.startswith("/")
                        or any(part in ("", ".", "..") for part in name.split("/")) or not isinstance(body, bytes)):
                    raise ValueError("UNSAFE_MONOLITH_CARRIER_PATH")
                mode = "100644" if name == "MANIFEST.json" else manifest["files"][name]["mode"]
                if mode not in ("100644", "100755"):
                    raise ValueError("REGULAR_COMMITTED_FILES_REQUIRED")
                dest = package / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as target: target.write(body)
                dest.chmod(0o755 if mode == "100755" else 0o644)
            verify(package, pin, check_runtime=check_runtime)
            # Release the read transaction before a native writer starts.
            db.close()
            yield package


def git_blob_digest(body):
    return hashlib.sha1(("blob " + str(len(body)) + "\0").encode() + body).hexdigest()


def source_tree_digest(items):
    """Git's original tree identity without a Git dependency at runtime."""
    root = {}
    for path, mode, sha in items:
        if (not isinstance(path, str) or not path or path.startswith("/") or "\0" in path
                or any(part in ("", ".", "..") for part in path.split("/"))
                or mode not in ("100644", "100755", "120000")
                or not re.fullmatch(r"[a-f0-9]{40}", sha or "")):
            raise ValueError("ORIGINAL_SOURCE_TREE_ENTRY_REQUIRED")
        node = root
        parts = path.split("/")
        for part in parts[:-1]:
            if part in node and not isinstance(node[part], dict): raise ValueError("SOURCE_PATH_CONFLICT")
            node = node.setdefault(part, {})
        if parts[-1] in node: raise ValueError("SOURCE_PATH_CONFLICT")
        node[parts[-1]] = (mode, sha)

    def encode(node):
        rows = []
        for name, value in node.items():
            if isinstance(value, dict): mode, sha = "40000", encode(value)
            else: mode, sha = value
            rows.append((name.encode("utf-8") + (b"/" if mode == "40000" else b""),
                         mode.encode() + b" " + name.encode("utf-8") + b"\0" + bytes.fromhex(sha)))
        raw = b"".join(row for _, row in sorted(rows))
        return hashlib.sha1(("tree " + str(len(raw)) + "\0").encode() + raw).hexdigest()
    return encode(root)


def verify_repository_files(db, expected_tree):
    if [r[1] for r in db.execute("PRAGMA table_info(repository_files)")] != ["path", "mode", "git_blob_sha1", "body"]:
        raise ValueError("SOURCE_TABLE_SCHEMA_MISMATCH")
    items, size = [], 0
    for path, mode, sha, body in db.execute("SELECT path,mode,git_blob_sha1,body FROM repository_files ORDER BY path"):
        if not isinstance(body, bytes) or git_blob_digest(body) != sha: raise ValueError("SOURCE_BLOB_DRIFT")
        items.append((path, mode, sha)); size += len(body)
        if len(items) > 100000 or size > STATE_MAX_BYTES: raise ValueError("SOURCE_TREE_CAPACITY_LIMIT")
    if not items or source_tree_digest(items) != expected_tree: raise ValueError("SOURCE_TREE_INVENTORY_MISMATCH")
    return len(items)


def portable_restore(store, pin, image_pin, output, head, tree):
    """Restore the pinned full source tree with Python alone; execute no input."""
    private_path(store)
    if not re.fullmatch(r"[a-f0-9]{64}", image_pin or ""):
        raise ValueError("INDEPENDENT_SQLITE_IMAGE_PIN_REQUIRED")
    with store.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != image_pin:
            raise ValueError("SQLITE_IMAGE_PIN_MISMATCH")
    info = inspect_stable_monolith(store, pin, check_runtime=False)
    if (info["source_head"] != head or info["source_tree"] != tree or not info["full_tree_present"]):
        raise ValueError("EXACT_FULL_SOURCE_BINDING_REQUIRED")
    private_output(output, (store,))
    with contextlib.closing(sqlite3.connect(store.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        count = verify_repository_files(db, tree)
        # Validate every destination before creating anything. Links are written
        # last, so no parent link is followed while materializing regular bytes.
        links = []
        for path, mode, body in db.execute("SELECT path,mode,body FROM repository_files"):
            if any(part.casefold() == ".git" for part in path.split("/")):
                raise ValueError("RESTORE_GIT_ADMIN_PATH_REFUSED")
            if mode == "120000":
                target = os.fsdecode(body)
                resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
                if (os.path.isabs(target) or resolved == ".." or resolved.startswith("../") or "\0" in target):
                    raise ValueError("RESTORE_ESCAPING_SYMLINK_REFUSED")
                links.append((path, target))
        output.mkdir(mode=0o700)
        try:
            for path, mode, body in db.execute("SELECT path,mode,body FROM repository_files ORDER BY path"):
                dest = output / path
                dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if mode == "120000": continue
                with dest.open("xb") as target:
                    target.write(body); target.flush(); os.fsync(target.fileno())
                dest.chmod(0o755 if mode == "100755" else 0o644)
            for path, target in links: (output / path).symlink_to(target)
            observed = []
            for path, mode, sha in db.execute("SELECT path,mode,git_blob_sha1 FROM repository_files ORDER BY path"):
                dest = output / path
                body = os.fsencode(os.readlink(dest)) if mode == "120000" else dest.read_bytes()
                if git_blob_digest(body) != sha or (mode != "120000" and
                        stat.S_IMODE(dest.stat().st_mode) != (0o755 if mode == "100755" else 0o644)):
                    raise ValueError("RESTORED_SOURCE_READBACK_MISMATCH")
                observed.append((path, mode, sha))
            if source_tree_digest(observed) != tree:
                raise ValueError("RESTORED_SOURCE_TREE_MISMATCH")
            with store.open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != image_pin:
                    raise ValueError("SQLITE_CHANGED_DURING_RESTORE")
            for directory in sorted((p for p in output.rglob("*") if p.is_dir() and not p.is_symlink()),
                                    key=lambda p: len(p.parts), reverse=True): sync_directory(directory)
            sync_directory(output); sync_directory(output.parent)
        except BaseException:
            shutil.rmtree(output)
            raise
    return {"state": "SOURCE_TREE_RESTORED_BYTE_EXACT", "source_head": head, "source_tree": tree,
            "source_files": count, "canonical_sha256": image_pin, "manifest_sha256": pin,
            "git_history_included": False, "native_runtime_executed": False,
            "linux_distribution_verified": False, "effect_ack_done": False}


def inspect_stable_monolith(store, pin, *, check_runtime=True):
    """Read-only, offline validation of a frozen SQLite image and every event.

    The complete original database bytes are transported, including meta-backed
    preparations, sqlite_sequence and replay identity. No SQL projection is used.
    """
    private_path(store)
    if not 100 <= store.stat().st_size <= STATE_MAX_BYTES: raise ValueError("MONOLITH_CAPACITY_LIMIT")
    if any(Path(str(store) + suffix).exists() or Path(str(store) + suffix).is_symlink()
           for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("STOPPED_CHECKPOINTED_MAIN_FILE_REQUIRED")
    raw = store.read_bytes()
    if raw[:16] != b"SQLite format 3\0" or raw[18:20] != b"\1\1":
        raise ValueError("STOPPED_CHECKPOINTED_MAIN_FILE_REQUIRED")
    with materialized_monolith(store, pin, check_runtime=check_runtime) as package:
        manifest = json.loads((package / "MANIFEST.json").read_bytes())
        load_source(package, "qikvrt_effect_ack_http_terminal")
        native = load_source(package, "qikvrt_temdd_event_ledger")
        with contextlib.closing(sqlite3.connect(store.as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("PRAGMA trusted_schema=OFF")
            meta = dict(db.execute("SELECT key,value FROM meta"))
            if meta.get("schema") not in ("1", "2") or not re.fullmatch(r"[a-f0-9]{32}", meta.get("epoch", "")):
                raise ValueError("MONOLITH_LEDGER_IDENTITY_MISMATCH")
            count, last = 0, 0
            for seq, binding, source, native_id, native_sha, body, body_sha in db.execute(
                    "SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events ORDER BY seq"):
                value = json.loads(body)
                original = {k:v for k,v in value.items() if k not in ("recorded_at", "payload_digest", "evidence_transfer", "dod")}
                original["schema"] = native.SCHEMA
                subject = value.get("subject", {})
                if (not isinstance(subject, dict) or set(subject) != {"repository", "pr", "head", "tree"}
                        or type(subject.get("pr")) is not int or subject["pr"] < 1
                        or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", subject.get("repository", ""))
                        or any(not re.fullmatch(r"[a-f0-9]{40}", subject.get(k, "")) for k in ("head", "tree"))):
                    raise ValueError("MONOLITH_LEDGER_SUBJECT_MISMATCH")
                validator = object.__new__(native.Ledger)
                validator.subject = subject
                native.Ledger._validate(validator, original)
                if (type(seq) is not int or seq <= last or native.canonical(value).decode() != body
                        or native.digest(value) != body_sha or native.digest(original) != native_sha
                        or native.digest(value["subject"]) != binding
                        or value.get("payload_digest") != native.digest(value["payload"])
                        or value.get("schema") != "qikvrt_temdd_event_v1"
                        or value.get("evidence_transfer") != "DENY" or value.get("dod") is not False
                        or value.get("provenance") != {"source":source, "native_event_id":native_id}
                        or source not in ("repository", "transputer")):
                    raise ValueError("MONOLITH_LEDGER_READBACK_MISMATCH")
                last = seq; count += 1
            sequence = db.execute("SELECT seq FROM sqlite_sequence WHERE name='events'").fetchone()
            if last and (sequence is None or type(sequence[0]) is not int or sequence[0] < last):
                raise ValueError("MONOLITH_REPLAY_SEQUENCE_MISMATCH")
            full_tree = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='repository_files'").fetchone()
    if store.read_bytes() != raw: raise ValueError("MONOLITH_CHANGED_DURING_READ")
    return {"schema":"qikvrt-monolithic-store-receipt/v1", "file_sha256":digest(raw), "bytes":len(raw),
            "manifest_sha256":pin, "ledger_id":meta["epoch"], "ledger_records":count, "last_sequence":last,
            "source_head":manifest["source_head"], "source_tree":manifest["source_tree"],
            "full_tree_present":bool(full_tree), "canonical_format":"SQLITE3_WITH_CARRIER_META_AND_EVENTS",
            "native_runtime_executed":False, "effect_ack_done":False}


def transport_export(store, pin, config_path, output):
    private_output(output, (store, config_path))
    checkpoint_monolith(store, pin, config_path)
    # Reacquire both writer locks for the entire copy, not just the checkpoint.
    with materialized_monolith(store, pin) as package:
        volume, _ = state_binding(package, pin, config_path)
        with stopped_state(volume):
            info = inspect_stable_monolith(store, pin)
            data = dict(info, store=str(store), output=str(output), repositoryId="qikvrt-sqlite-" + info["ledger_id"])
            result = subprocess.check_output(["node", str(package / "docs/monitor/mesh-file-store.mjs"), "transport-export"],
                                             input=raw_json(data), timeout=300)
            value = json.loads(result)
            if digest(store.read_bytes()) != info["file_sha256"]:
                raise ValueError("MONOLITH_CHANGED_DURING_EXPORT")
            return dict(value, state="DERIVED_SQLITE_TRANSPORT_EXPORTED", native_runtime_executed=False,
                        predecessor_evidence_transfer=False, effect_ack_done=False)


def transport_import(source, pin, image_pin, transport_pin, output):
    """Create-only exact restoration; never mutate or execute an existing store."""
    private_path(source)
    private_output(output, (source,))
    if any(Path(str(output) + suffix).exists() or Path(str(output) + suffix).is_symlink()
           for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("CANONICAL_IMPORT_TARGET_TRANSACTION_COMPANION_PRESENT")
    if any(not re.fullmatch(r"[a-f0-9]{64}", value or "") for value in (pin, image_pin, transport_pin)):
        raise ValueError("INDEPENDENT_PACKAGE_IMAGE_AND_TRANSPORT_PINS_REQUIRED")
    if digest(source.read_bytes()) != transport_pin: raise ValueError("TRANSPORT_PIN_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="qikvrt-sqlite-import-", dir=output.parent) as temp:
        candidate = Path(temp) / "events.sqlite3"
        data = {"source":str(source), "output":str(candidate), "manifest_sha256":pin,
                "file_sha256":image_pin, "transport_sha256":transport_pin}
        subprocess.check_output(["node", str(ROOT / "docs/monitor/mesh-file-store.mjs"), "transport-extract"],
                                input=raw_json(data), timeout=300)
        info = inspect_stable_monolith(candidate, pin)
        if info["file_sha256"] != image_pin: raise ValueError("CANONICAL_IMAGE_PIN_MISMATCH")
        if digest(source.read_bytes()) != transport_pin: raise ValueError("TRANSPORT_CHANGED_DURING_IMPORT")
        # link is atomic and refuses an existing or raced destination.
        os.link(candidate, output, follow_symlinks=False)
        sync_directory(output.parent)
        if inspect_stable_monolith(output, pin)["file_sha256"] != image_pin:
            raise ValueError("CANONICAL_IMPORT_READBACK_MISMATCH")
        return dict(info, state="CANONICAL_SQLITE_RESTORED_BYTE_EXACT", transport_sha256=transport_pin,
                    same_node_client_bytes=True, predecessor_evidence_transfer=False,
                    native_runtime_executed=False, effect_ack_done=False)


def run_monolith(store, pin, config_path):
    if config_path is None: raise ValueError("PRIVATE_START_CONFIGURATION_REQUIRED")
    private_path(config_path)
    config = json.loads(config_path.read_bytes())
    if (config.get("terminal_profile") != "temdd"
            or store != Path(config["state_dir"]) / "temdd/events.sqlite3"):
        raise ValueError("MONOLITH_EXISTING_NATIVE_LEDGER_PATH_AND_PASSIVE_PROFILE_REQUIRED")
    with materialized_monolith(store, pin) as package:
        if digest(Path(__file__).read_bytes()) != digest((package / "tools/qikvrt_self_host.py").read_bytes()):
            raise ValueError("MONOLITH_STARTER_BINDING_MISMATCH")
        return start(package, pin, config_path, monolith=True)


def verify_origin_sqlite_assets(root):
    lock = json.loads((root / 'runtime/self-host/ORIGIN_SQLITE_LOCK.json').read_bytes())
    expected = {'docs/monitor/origin/vendor/' + name for name in
                ('SQLJS_LICENSE.txt', 'sql-wasm.js', 'sql-wasm.wasm')}
    if (lock.get('schema') != 'qikvrt-origin-sqlite-lock/v1'
            or lock.get('version') != '1.14.2' or set(lock.get('files', {})) != expected):
        raise ValueError('ORIGIN_SQLITE_LOCK_REQUIRED')
    for name, entry in lock['files'].items():
        path = root / name
        if path.is_symlink() or not path.is_file(): raise ValueError('ORIGIN_SQLITE_ASSET_REQUIRED')
        raw = path.read_bytes()
        if len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
            raise ValueError('ORIGIN_SQLITE_ASSET_DRIFT')
    return lock


def export_origin_shell(package, output, config, receipt):
    """Emit a bootstrap, never private SQLite bytes or credentials, under locks.

    The independently pinned image is explicitly selected in the browser. All
    shell paths are relative, so an HTTPS subpath works without a root scope.
    """
    verify_origin_sqlite_assets(package)
    verify_react_assets(package)
    manifest = json.loads((package / 'MANIFEST.json').read_bytes())
    assets = {'index.html':'docs/monitor/origin/index.html',
        'react-runtime.js':'docs/monitor/react-runtime.js',
        'REACT_LICENSE.txt':'docs/monitor/REACT_LICENSE.txt',
        'mesh-react.css':'docs/monitor/mesh-react.css'}
    for name in ('origin-store.js','origin-terminal.js','sqlite-reader.js','store-worker.js',
                 'vendor/sql-wasm.js','vendor/sql-wasm.wasm','vendor/SQLJS_LICENSE.txt'):
        assets[name] = 'docs/monitor/origin/' + name
    profile = {'schema':'qikvrt-origin-bootstrap/v1','ledger_id':receipt['ledger_id'],
        'store_sha256':receipt['file_sha256'],'manifest_sha256':receipt['manifest_sha256'],
        'subject':{'repository':manifest['source_repository'],'pr':config['subject_pr'],
                   'head':manifest['source_head'],'tree':manifest['source_tree']},
        'max_store_bytes':64*1024*1024,'max_events':10000,
        'role_scope':['REPOSITORY_NODE','REPOSITORY_CLIENT'],
        'storage_scope':'ORIGIN_PRIVATE_INDEXEDDB','native_execution':False,
        'mobile_runtime_verified':False,'effect_ack_done':False}
    if receipt['bytes'] > profile['max_store_bytes'] or receipt['ledger_records'] > profile['max_events']:
        raise ValueError('BOUNDED_ORIGIN_STORE_REQUIRED')
    output.mkdir(mode=0o700)
    try:
        hashes = {}
        for dest_name, source_name in sorted(assets.items()):
            raw = (package / source_name).read_bytes()
            dest = output / dest_name
            dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            synced_private_file(dest, raw)
            hashes[dest_name] = digest(raw)
        raw = raw_json(profile)
        synced_private_file(output/'ORIGIN_PROFILE.json',raw)
        hashes['ORIGIN_PROFILE.json'] = digest(raw)
        shell_id = digest(raw_json(hashes))
        template = (package/'docs/monitor/origin/service-worker.template.js').read_text()
        worker = template.replace('__SHELL_ID__',shell_id).replace('__SHELL_ASSETS__',json.dumps(hashes,sort_keys=True))
        synced_private_file(output/'service-worker.js',worker.encode())
        for directory in sorted((p for p in output.rglob('*') if p.is_dir()),reverse=True): sync_directory(directory)
        sync_directory(output); sync_directory(output.parent)
        return {'schema':'qikvrt-origin-export-receipt/v1','state':'SOURCE_BOOTSTRAP_EXPORTED',
            'shell_sha256':shell_id,'shell_files_sha256':dict(hashes,**{'service-worker.js':digest(worker.encode())}),
            'store_sha256':receipt['file_sha256'],'ledger_id':receipt['ledger_id'],
            'manifest_sha256':receipt['manifest_sha256'],'private_store_included':False,
            'native_code_executed_in_browser':False,'mobile_runtime_verified':False,
            'public_https_verified':False,'effect_ack_done':False}
    except BaseException:
        shutil.rmtree(output)
        raise


def checkpoint_monolith(store, pin, config_path, origin_output=None):
    """Seal a transferable main file only after both existing writer locks stop."""
    if config_path is None: raise ValueError("PRIVATE_START_CONFIGURATION_REQUIRED")
    private_path(config_path)
    config = json.loads(config_path.read_bytes())
    if origin_output is not None: private_output(origin_output, (store, config_path))
    if (config.get("terminal_profile") != "temdd"
            or store != Path(config["state_dir"]) / "temdd/events.sqlite3"):
        raise ValueError("MONOLITH_EXISTING_NATIVE_LEDGER_PATH_AND_PASSIVE_PROFILE_REQUIRED")
    with materialized_monolith(store, pin) as package:
        volume, binding = state_binding(package, pin, config_path)
        with stopped_state(volume):
            bound = volume / "binding.json"
            private_path(bound)
            if json.loads(bound.read_bytes()) != binding:
                raise ValueError("PERSISTENT_VOLUME_BINDING_MISMATCH")
            with contextlib.closing(sqlite3.connect(store)) as db:
                if db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone() != (0, 0, 0):
                    raise ValueError("MONOLITH_CHECKPOINT_BUSY")
                if db.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
                    raise ValueError("MONOLITH_IDLE_MAIN_FILE_REQUIRED")
                count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                epoch = db.execute("SELECT value FROM meta WHERE key='epoch'").fetchone()[0]
            if any(Path(str(store) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
                raise ValueError("MONOLITH_TRANSACTION_COMPANION_STILL_PRESENT")
            with store.open("rb") as source: os.fsync(source.fileno())
            fd = os.open(store.parent, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
            raw = store.read_bytes()
            receipt = {"schema": "qikvrt-monolithic-store-receipt/v1", "state": "STABLE_SINGLE_FILE_IMAGE",
                    "manifest_sha256": pin, "file_sha256": digest(raw), "bytes": len(raw),
                    "ledger_id": epoch, "ledger_records": count, "both_writer_locks_held": True,
                    "cloud_synchronization_verified": False, "mobile_runtime_verified": False, "effect_ack_done": False}
            return export_origin_shell(package, origin_output, config, receipt) if origin_output is not None else receipt


def state_binding(package, pin, config_path):
    """Bind recovery to the existing package/config, never grant a new subject."""
    manifest = verify(package, pin)
    if config_path is None: raise ValueError("PRIVATE_START_CONFIGURATION_REQUIRED")
    private_path(config_path)
    raw = config_path.read_bytes()
    config = json.loads(raw)
    if (config.get("schema") != "qikvrt-self-host-config/v1"
            or any(config.get(k) != manifest[k] for k in ("source_head", "source_tree"))
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", config.get("node_id", ""))):
        raise ValueError("STATE_CONFIGURATION_BINDING_MISMATCH")
    volume = Path(config["state_dir"])
    if (not volume.is_absolute() or ".." in volume.parts
            or any(p.is_symlink() for p in (volume, *volume.parents))
            or volume == package or package in volume.parents or volume in package.parents):
        raise ValueError("SEPARATE_PRIVATE_STATE_PATH_REQUIRED")
    binding = {"schema": "qikvrt-self-host-volume/v1", "node_id": config["node_id"],
        "manifest_sha256": pin, "config_sha256": digest(raw),
        "source_head": manifest["source_head"], "source_tree": manifest["source_tree"]}
    return volume, binding


@contextlib.contextmanager
def stopped_state(volume):
    """Use both original OS locks, so a live monitor OR native writer blocks."""
    private_path(volume, directory=True)
    with contextlib.ExitStack() as locks:
        names = ["node.lock"]
        if (volume / "temdd/events.sqlite3").exists(): names.append("temdd/owner.lock")
        for name in names:
            path = volume / name
            private_path(path)
            lock = locks.enter_context(os.fdopen(os.open(path, os.O_RDWR | os.O_NOFOLLOW), "rb"))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        mesh_lock = volume / "repository.qmesh.lock"
        if (volume / "repository.qmesh").exists():
            fd = os.open(mesh_lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            locks.callback(mesh_lock.unlink)
            locks.callback(os.close, fd)
        yield


def private_output(path, separate):
    if (path is None or not path.is_absolute() or ".." in path.parts
            or any(p.is_symlink() for p in (path, *path.parents))
            or any(path == p or p in path.parents or path in p.parents for p in separate)):
        raise ValueError("SEPARATE_CREATE_ONLY_PRIVATE_OUTPUT_REQUIRED")
    private_path(path.parent, directory=True)
    if path.exists(): raise ValueError("STATE_OUTPUT_ALREADY_EXISTS")


def synced_private_file(path, raw):
    with path.open("xb") as dest:
        path.chmod(0o600)
        dest.write(raw); dest.flush(); os.fsync(dest.fileno())
    private_path(path)
    if path.read_bytes() != raw: raise ValueError("STATE_FILE_READBACK_MISMATCH")


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def state_file_digest(path, destination=None, *, privileged_capture=False):
    # Original SQLite files may be 0644 inside the existing 0700 directory.
    # Copies always become 0600. Stream bounded data instead of caching a DB.
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("STATE_SYMLINK_FORBIDDEN")
    with contextlib.ExitStack() as stack:
        source = stack.enter_context(os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb"))
        info = os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o7000
                or (privileged_capture and os.geteuid() != 0)
                or (not privileged_capture and (info.st_uid != os.geteuid() or info.st_mode & 0o022))):
            raise ValueError("UNSAFE_SOURCE_STATE_FILE")
        target = None
        if destination is not None:
            target = stack.enter_context(destination.open("xb"))
            destination.chmod(0o600)
        sha = hashlib.sha256(); size = 0
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            if size > STATE_MAX_BYTES: raise ValueError("STATE_SNAPSHOT_SIZE_LIMIT")
            sha.update(chunk)
            if target is not None: target.write(chunk)
        final = os.fstat(source.fileno())
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns, final.st_ctime_ns):
            raise ValueError("STATE_SOURCE_CHANGED_DURING_COPY")
        if target is not None: target.flush(); os.fsync(target.fileno())
        entry = {"bytes": size, "sha256": sha.hexdigest()}
    if destination is not None:
        private_path(destination)
        if state_file_digest(destination) != entry: raise ValueError("STATE_FILE_READBACK_MISMATCH")
    return entry


def snapshot_state(package, pin, config_path, output):
    """Freeze only existing durable stores, not credentials or browser profiles."""
    volume, binding = state_binding(package, pin, config_path)
    private_output(output, (package, volume))
    with stopped_state(volume):
        private_path(volume / "binding.json")
        if json.loads((volume / "binding.json").read_bytes()) != binding:
            raise ValueError("PERSISTENT_VOLUME_BINDING_MISMATCH")
        files = {}
        total = 0
        for name in sorted(STATE_FILES):
            path = volume / name
            if not path.exists() and not path.is_symlink(): continue
            if path.parent != volume: private_path(path.parent, directory=True)
            total += path.stat().st_size
            if total > STATE_MAX_BYTES: raise ValueError("STATE_SNAPSHOT_SIZE_LIMIT")
            files[name] = state_file_digest(path)
        if "monitor/node.json" not in files: raise ValueError("EXISTING_MONITOR_STATE_REQUIRED")
        if not files.get("temdd/events.sqlite3", {}).get("bytes"):
            raise ValueError("EXISTING_NATIVE_LEDGER_REQUIRED")
        if json.loads(config_path.read_bytes()).get("mesh_file") and "repository.qmesh" not in files:
            raise ValueError("EXISTING_MESH_FILE_REQUIRED")
        # Create-only: never rewrite an earlier checkpoint or remove source data.
        output.mkdir(mode=0o700)
        for name, entry in files.items():
            target = output / name
            if target.parent != output: target.parent.mkdir(mode=0o700, exist_ok=True)
            if state_file_digest(volume / name, target) != entry:
                raise ValueError("STATE_SOURCE_CHANGED_DURING_COPY")
        manifest = {"schema": "qikvrt-self-host-state-snapshot/v1", "binding": binding,
            "scope": "EXACT_MONITOR_NATIVE_SQLITE_AND_OPTIONAL_MESH_FILE_BYTES; NOT_SECRETS_BROWSER_PROFILE_OR_OPERATOR_RECEIPTS",
            "files": files,
            "source_writer_quiescence": "ORIGINAL_NODE_AND_NATIVE_OWNER_OS_LOCKS_HELD",
            "effect_ack_done": False}
        raw = raw_json(manifest)
        synced_private_file(output / "STATE_MANIFEST.json", raw)
        for directory in (output / "monitor", output / "temdd", output): sync_directory(directory)
        sync_directory(output.parent)
        verify_state_snapshot(output, digest(raw), binding)
        return {"state": "PRIVATE_STATE_SNAPSHOT_FROZEN", "state_manifest_sha256": digest(raw),
            "files": len(files), "bytes": total, "runtime_readback_verified": False,
            "railway_data_exported": False, "effect_ack_done": False}


def verify_state_snapshot(snapshot, pin, binding):
    private_path(snapshot, directory=True)
    private_path(snapshot / "STATE_MANIFEST.json")
    raw = (snapshot / "STATE_MANIFEST.json").read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", pin or "") or digest(raw) != pin:
        raise ValueError("STATE_MANIFEST_PIN_MISMATCH")
    manifest = json.loads(raw)
    files = manifest.get("files", {})
    if (manifest.get("schema") != "qikvrt-self-host-state-snapshot/v1"
            or manifest.get("binding") != binding or manifest.get("effect_ack_done") is not False
            or not isinstance(files, dict) or not {"binding.json", "monitor/node.json", "temdd/events.sqlite3"} <= set(files)
            or not set(files) <= STATE_FILES):
        raise ValueError("STATE_SNAPSHOT_BINDING_OR_SCHEMA_MISMATCH")
    expected = set(files) | {"STATE_MANIFEST.json", "monitor", "temdd"}
    actual = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*")}
    if actual != expected: raise ValueError("STATE_SNAPSHOT_INVENTORY_MISMATCH")
    total = 0
    for name, entry in files.items():
        path = snapshot / name
        if path.parent != snapshot: private_path(path.parent, directory=True)
        private_path(path)
        if (not isinstance(entry, dict) or set(entry) != {"bytes", "sha256"}
                or type(entry["bytes"]) is not int or entry["bytes"] < 0
                or entry["bytes"] != path.stat().st_size):
            raise ValueError("STATE_SNAPSHOT_FILE_MISMATCH")
        total += entry["bytes"]
        if total > STATE_MAX_BYTES: raise ValueError("STATE_SNAPSHOT_SIZE_LIMIT")
        if state_file_digest(path) != entry: raise ValueError("STATE_SNAPSHOT_FILE_MISMATCH")
    if json.loads((snapshot / "binding.json").read_bytes()) != binding:
        raise ValueError("PERSISTENT_VOLUME_BINDING_MISMATCH")
    if "repository.qmesh" in files:
        # Historical exports are retained as exact archival bytes, never as a
        # second product store. A configured live export gets the stricter gate.
        subprocess.check_output(["node", str(ROOT / "docs/monitor/mesh-file-store.mjs"), "verify-frames",
                                 str(snapshot / "repository.qmesh")], timeout=300)
    return manifest


def restore_state(package, pin, config_path, snapshot, snapshot_pin):
    """Restore to an absent path only; host admission/restart remain separate."""
    volume, binding = state_binding(package, pin, config_path)
    if snapshot is None: raise ValueError("PRIVATE_STATE_SNAPSHOT_REQUIRED")
    private_output(volume, (package, snapshot))
    manifest = verify_state_snapshot(snapshot, snapshot_pin, binding)
    if json.loads(config_path.read_bytes()).get("mesh_file") and "repository.qmesh" not in manifest["files"]:
        raise ValueError("EXISTING_MESH_FILE_REQUIRED")
    if json.loads(config_path.read_bytes()).get("mesh_file"):
        subprocess.check_output(["node", str(ROOT / "docs/monitor/mesh-file-store.mjs"), "verify-file",
                                 str(snapshot / "repository.qmesh")], timeout=300)
    # Pin checked before any target creation; incomplete restores remain HOLD.
    volume.mkdir(mode=0o700)
    for name in ("monitor", "temdd", "receipts"): (volume / name).mkdir(mode=0o700)
    for name in manifest["files"]:
        if state_file_digest(snapshot / name, volume / name) != manifest["files"][name]:
            raise ValueError("STATE_SNAPSHOT_CHANGED_DURING_RESTORE")
    for directory in (volume / "monitor", volume / "temdd", volume / "receipts", volume): sync_directory(directory)
    sync_directory(volume.parent)
    for name, entry in manifest["files"].items():
        private_path(volume / name)
        if state_file_digest(volume / name) != entry:
            raise ValueError("RESTORED_STATE_READBACK_MISMATCH")
    return {"state": "STATE_BYTES_RESTORED_PENDING_HOST_ADMISSION_AND_RUNTIME_READBACK",
        "state_manifest_sha256": snapshot_pin, "files": len(manifest["files"]),
        "source_data_changed": False, "host_admission_verified": False,
        "writer_admission_verified": False, "runtime_readback_verified": False, "railway_cutover_verified": False, "effect_ack_done": False}


def own_host_observation(volume):
    """Observe this Linux host/mount, without reading credentials or using a provider."""
    machine = Path("/etc/machine-id").read_bytes()
    if not re.fullmatch(rb"[a-f0-9]{32}\n?", machine) or machine.strip() == b"0" * 32:
        raise ValueError("OWN_HOST_MACHINE_ID_UNAVAILABLE")
    def unescape(value):
        return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), value)
    mounts = []
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        left, right = line.split(" - ", 1)
        fields, fs = left.split(), right.split()
        point = Path(unescape(fields[4]))
        if volume == point or point in volume.parents:
            mounts.append({"mount_point": str(point), "mount_root": unescape(fields[3]),
                "device_major_minor": fields[2], "filesystem": fs[0], "mount_source": unescape(fs[1])})
    if not mounts: raise ValueError("OWN_HOST_MOUNT_UNAVAILABLE")
    mount = max(mounts, key=lambda m: len(Path(m["mount_point"]).parts))
    if mount["filesystem"] in {"overlay", "tmpfs", "ramfs", "devtmpfs", "squashfs", "proc", "sysfs"}:
        raise ValueError("PERSISTENT_HOST_MOUNT_REQUIRED")
    return {"machine_id_sha256": digest(machine), "mount": mount}


def admission_plan(package, pin, config_path=None, admission_path=None, admission_pin=None, *, runtime_verifier=None):
    """Bind the existing launcher to pinned host declarations; never deploy or assert acceptance.

    An independently obtained admission pin binds the operator's declaration.
    Local identity/mount comparisons do not validate the external authorization,
    storage guarantees, control-plane capability, HTTPS route or review governance.
    """
    manifest = verify(package, pin) if runtime_verifier is None else runtime_verifier(package, pin)
    if config_path is None or admission_path is None:
        raise ValueError("HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE")
    private_path(config_path); private_path(admission_path)
    config_raw, admission_raw = config_path.read_bytes(), admission_path.read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", admission_pin or "") or digest(admission_raw) != admission_pin:
        raise ValueError("HOST_ADMISSION_PIN_MISMATCH")
    config, admission = json.loads(config_raw), json.loads(admission_raw)
    fields = {"schema", "source_head", "source_tree", "manifest_sha256", "config_sha256", "node_id",
              "machine_id_sha256", "mount", "public_origin", "execution_operation", "supervisor_id",
              "authorization_evidence_sha256", "persistence_evidence_sha256", "https_routing_evidence_sha256"}
    if (set(admission) != fields or admission["schema"] != "qikvrt-own-host-admission/v1"
            or config.get("schema") != "qikvrt-self-host-config/v1"
            or config.get("adapter") != "none" or config.get("terminal_profile") not in {"temdd", "firefox"}
            or config.get("source_repository") != manifest["source_repository"]
            or type(config.get("subject_pr")) is not int or config["subject_pr"] < 1
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", config.get("node_id", ""))
            or "CHANGE_ME" in config["node_id"]
            or admission["manifest_sha256"] != pin or admission["config_sha256"] != digest(config_raw)
            or admission["node_id"] != config["node_id"]
            or any(admission[k] != manifest[k] or config.get(k) != manifest[k] for k in ("source_head", "source_tree"))):
        raise ValueError("HOST_ADMISSION_SUBJECT_MISMATCH")
    for field in ("authorization_evidence_sha256", "persistence_evidence_sha256", "https_routing_evidence_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", admission.get(field) or ""):
            raise ValueError("HOST_ADMISSION_EVIDENCE_BINDINGS_REQUIRED")
    if any(not isinstance(admission.get(k), str) or not admission[k].strip()
            or len(admission[k]) > 256 or any(c in admission[k] for c in "\r\n\x00")
            for k in ("execution_operation", "supervisor_id")):
        raise ValueError("EXISTING_HOST_EXECUTION_AND_SUPERVISOR_REQUIRED")
    origin = admission.get("public_origin")
    if not isinstance(origin, str): raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    url = urllib.parse.urlsplit(origin)
    hostname = url.hostname or ""
    if (url.scheme != "https" or url.username or url.password or url.path or url.query or url.fragment
            or url.port not in {None, 443} or not hostname or hostname == "localhost"
            or hostname.endswith((".localhost", ".local", ".invalid", ".test", ".railway.app", ".vercel.app"))):
        raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        tld = r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
        if len(hostname) > 253 or not re.fullmatch(r"(?:" + label + r"\.)+" + tld, hostname):
            raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    else:
        if not address.is_global: raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    volume = Path(config["state_dir"]); private_path(volume, directory=True)
    observed = own_host_observation(volume)
    if admission["machine_id_sha256"] != observed["machine_id_sha256"] or admission["mount"] != observed["mount"]:
        raise ValueError("OWN_HOST_IDENTITY_OR_MOUNT_MISMATCH")
    common = ["--root", str(package), "--manifest-sha256", pin]
    launcher = [str(Path(sys.executable).resolve()), "-B", str(package / "tools/qikvrt_self_host.py")]
    return {"schema": "qikvrt-own-host-launcher-binding/v1", "state": "HOST_LAUNCHER_BOUND_PENDING_EXTERNAL_ACCEPTANCE",
        "source_head": manifest["source_head"], "source_tree": manifest["source_tree"], "manifest_sha256": pin,
        "config_sha256": digest(config_raw), "node_id": config["node_id"], "admission_sha256": admission_pin,
        "admission_tool_sha256": digest(Path(__file__).read_bytes()),
        "local_identity_and_mount_match": True, "verify_argv": launcher + ["verify", *common],
        "run_argv": launcher + ["run", *common, "--config", str(config_path)],
        "readback_argv": [str(Path(shutil.which("node")).resolve()), str(package / "tools/qikvrt_mesh_monitor_readback.mjs"),
            "--self-host", str(package), origin, pin, digest(config_raw), config["node_id"], "none"],
        "execution_performed": False, "host_admission_verified": False, "public_readback_verified": False,
        "restart_verified": False, "review_governance_satisfied": False, "effect_ack_done": False,
        "remaining": ["validate independent host/control-plane, persistence and HTTPS authorization evidence",
            "use existing supervisor and exact verify/run argv on the admitted host",
            "fresh independent public readback, actual supervisor restart and byte-exact durable data readback",
            "separate current native review governance"]}


def supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin, delivery=None, delivery_pin=None):
    """Materialize an existing systemd supervisor binding, never install a service."""
    tool = Path(__file__).resolve()
    if not re.fullmatch(r"[a-f0-9]{64}", tool_pin or "") or digest(tool.read_bytes()) != tool_pin:
        raise ValueError("ADMISSION_TOOL_PIN_MISMATCH")
    plan = (admission_plan(package, pin, config_path, admission_path, admission_pin) if delivery is None
            else docker_plan(package, pin, config_path, admission_path, admission_pin, delivery, delivery_pin))
    admission = json.loads(admission_path.read_bytes())
    match = re.fullmatch(r"systemd:([A-Za-z0-9][A-Za-z0-9_.-]{0,90}\.service)", admission["supervisor_id"])
    if not match: raise ValueError("EXISTING_SYSTEMD_SERVICE_BINDING_REQUIRED")
    config = json.loads(config_path.read_bytes())
    # The main process's HOLD exit must not create an unattended restart loop.
    # Keep the same mount namespace: a private bind-remount would change the
    # mount descriptor that admit just compared with the operator declaration.
    def quoted(value, argv=False):
        if any(c in value for c in "\n\r\x00") or any(ord(c) < 32 for c in value):
            raise ValueError("UNSAFE_SYSTEMD_ARGUMENT")
        value = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
        if argv: value = value.replace("$", "$$")
        return '"' + value + '"'
    point = admission["mount"]["mount_point"]
    if point == "/": mount_unit = "-.mount"
    else:
        escaped = ""
        for byte in point.strip("/").encode():
            char = chr(byte)
            escaped += "-" if char == "/" else char if char.isascii() and (char.isalnum() or char in "_:.") else "\\x%02x" % byte
        if escaped.startswith("."): escaped = "\\x2e" + escaped[1:]
        mount_unit = escaped + ".mount"
    command = [str(Path(sys.executable).resolve()), "-B", str(tool), "run-admitted",
        "--root", str(package), "--manifest-sha256", pin, "--config", str(config_path),
        "--admission", str(admission_path), "--admission-sha256", admission_pin,
        "--admission-tool-sha256", tool_pin]
    if delivery is not None:
        command += ["--delivery", str(delivery), "--delivery-sha256", delivery_pin]
    path = ":".join(dict.fromkeys([str(Path(shutil.which("node")).resolve().parent),
        str(Path(sys.executable).resolve().parent), "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin"]))
    unit = ("# Generated by the exact reviewed QIKVRT launcher; contains no token bytes.\n"
        "[Unit]\nDescription=QIKVRT pinned own-host node\n"
        "Wants=network-online.target\nAfter=network-online.target " + mount_unit + "\n"
        "BindsTo=" + mount_unit + "\nRequiresMountsFor=" + quoted(config["state_dir"]) + "\n"
        "StartLimitIntervalSec=300\nStartLimitBurst=5\n\n[Service]\nType=exec\n"
        "User=" + str(os.geteuid()) + "\nGroup=" + str(os.getegid()) + "\nUMask=0077\n"
        "Environment=" + quoted("PATH=" + path) + "\nNoNewPrivileges=yes\n"
        "ExecStart=" + " ".join(quoted(arg, argv=True) for arg in command) + "\n"
        "KillMode=control-group\nTimeoutStopSec=20\nSendSIGKILL=yes\n"
        "Restart=always\nRestartSec=3\nRestartPreventExitStatus=78\n\n"
        "[Install]\nWantedBy=multi-user.target " + mount_unit + "\n")
    if delivery is not None:
        unit = unit.replace("After=network-online.target ", "After=docker.service network-online.target ")
        unit = unit.replace("ExecStart=", "ExecStop=" + " ".join(quoted(arg, argv=True) for arg in
            [plan['docker_executable'], 'stop', '--time', '10', plan['container_name']]) + "\nExecStart=")
    path_name = match[1][:-8] + ".path"
    def path_value(p):
        # PathChanged is one raw absolute path, unlike ExecStart's argv parser.
        # Quotes would become literal path bytes. Refuse ambiguous unit syntax.
        value = str(p)
        if not re.fullmatch(r"/[A-Za-z0-9_./:$%+\-]+", value):
            raise ValueError("UNREPRESENTABLE_SYSTEMD_PATH")
        return value.replace("%", "%%")
    path_unit = ("# Retry only on a filesystem event; never repin or recreate state.\n"
        "[Unit]\nDescription=QIKVRT exact admission restoration events\n\n[Path]\n"
        + "".join("PathChanged=" + path_value(p) + "\n" for p in
            (config_path, admission_path, package / "MANIFEST.json", tool, Path("/etc/machine-id")))
        + "Unit=" + match[1] + "\nTriggerLimitIntervalSec=300\nTriggerLimitBurst=5\n\n"
        "[Install]\nWantedBy=multi-user.target\n")
    return {**plan, "schema": "qikvrt-own-host-supervisor-binding/v1",
        "state": "SYSTEMD_BINDING_PREPARED_NOT_INSTALLED", "unit_name": match[1], "unit_text": unit,
        "unit_sha256": digest(unit.encode()), "guard_argv": command,
        "path_unit_name": path_name, "path_unit_text": path_unit,
        "path_unit_sha256": digest(path_unit.encode()),
        "automatic_recovery": {"trigger": "PROCESS_EXIT_OR_BOOT", "supervisor": "EXISTING_SYSTEMD",
            "maximum_starts_per_300_seconds": 5, "hold_exit_status": 78,
            "every_start_rechecks_identity_mount_config_package": True,
            "cgroup_orphan_cleanup": True, "state_recreation_or_rebinding": False,
            "exact_admission_restoration_retry": "SYSTEMD_PATH_CHANGED_EVENT",
            "http_health_polling": False, "new_head_auto_deployment": False},
        "supervisor_installed": False, "live_recovery_verified": False}


def materialize_supervisor(plan, output):
    if not output.is_absolute() or any(p.is_symlink() for p in (output, *output.parents)) or ".." in output.parts:
        raise ValueError("ABSOLUTE_CREATE_ONLY_SUPERVISOR_OUTPUT_REQUIRED")
    output.mkdir(mode=0o700, exist_ok=False)
    try:
        for name, raw in ((plan["unit_name"], plan["unit_text"].encode()),
                          (plan["path_unit_name"], plan["path_unit_text"].encode()),
                          ("BINDING.json", raw_json({k: v for k, v in plan.items() if k not in {"unit_text", "path_unit_text"}}))):
            with (output / name).open("xb") as dest:
                os.chmod(dest.name, 0o600)
                dest.write(raw); dest.flush(); os.fsync(dest.fileno())
        fd = os.open(output, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except BaseException:
        shutil.rmtree(output); raise
    return {k: v for k, v in plan.items() if k not in {"unit_text", "path_unit_text"}} | {"output_directory": str(output)}


def systemd_invocation(unit):
    """Match the current process to the existing host manager, not an env self-report."""
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise ValueError("ACTIVE_HOST_SYSTEMD_REQUIRED")
    command = '/usr/bin/systemctl'
    version = subprocess.check_output([command, '--version'], timeout=5).decode()
    match = re.match(r'systemd ([0-9]+)\b', version)
    if not match or int(match[1]) < 252: raise ValueError("SYSTEMD_252_OR_NEWER_REQUIRED")
    raw = subprocess.check_output([command, 'show', unit, '--property=MainPID,InvocationID'], timeout=5).decode()
    observed = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
    invocation = os.environ.get('INVOCATION_ID', '')
    if (not re.fullmatch(r'[a-f0-9]{32}', invocation) or observed.get('InvocationID') != invocation
            or observed.get('MainPID') != str(os.getpid())):
        raise ValueError("EXISTING_SYSTEMD_INVOCATION_BINDING_MISMATCH")
    return invocation


def run_admitted(package, pin, config_path, admission_path, admission_pin, tool_pin, delivery=None, delivery_pin=None):
    # The reviewed guard can also launch an unchanged historical export. A
    # separate process executes that export's verifier before exec'ing its run.
    # exec preserves the systemd MainPID and cgroup; no second supervisor.
    plan = supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin, delivery, delivery_pin)
    result = subprocess.run(plan["verify_argv"], capture_output=True, timeout=60)
    if result.returncode != 0 or json.loads(result.stdout).get("state") != "EXACT_PACKAGE_RUNTIME_VERIFIED":
        raise ValueError("INDEPENDENT_PACKAGE_VERIFY_FAILED")
    config = json.loads(config_path.read_bytes())
    binding = Path(config["state_dir"]) / "binding.json"
    if binding.exists() or binding.is_symlink():
        private_path(binding)
        expected = {"schema": "qikvrt-self-host-volume/v1", "node_id": plan["node_id"],
            "manifest_sha256": pin, "config_sha256": plan["config_sha256"],
            "source_head": plan["source_head"], "source_tree": plan["source_tree"]}
        if json.loads(binding.read_bytes()) != expected:
            raise ValueError("PERSISTENT_VOLUME_BINDING_MISMATCH")
    # Reobserve immediately before the effect; stale plan metadata is not an
    # authorization or a replacement for admission after a crash.
    supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin, delivery, delivery_pin)
    invocation = systemd_invocation(plan['unit_name'])
    if delivery is not None:
        existing = subprocess.run([plan['docker_executable'], 'container', 'inspect', plan['container_name']],
                                  capture_output=True, timeout=15)
        if existing.returncode == 0:
            previous = json.loads(existing.stdout)[0]
            labels = previous.get('Config', {}).get('Labels', {}) or {}
            if previous.get('Image') != plan['runtime_image_id'] or any(labels.get(k) != v for k, v in plan['container_labels'].items()):
                raise ValueError('EXISTING_CONTAINER_SUBJECT_MISMATCH')
            subprocess.run([plan['docker_executable'], 'stop', '--time', '10', plan['container_name']], check=True, timeout=30)
        elif b'No such' not in existing.stderr:
            raise ValueError('EXISTING_CONTAINER_STATE_UNOBSERVABLE')
    print(json.dumps({"state": "HOST_GUARD_VERIFIED_STARTING_EXISTING_LAUNCHER",
        "source_head": plan["source_head"], "source_tree": plan["source_tree"],
        "manifest_sha256": pin, "config_sha256": plan["config_sha256"],
        "admission_sha256": admission_pin, "admission_tool_sha256": tool_pin,
        "systemd_invocation_id": invocation, "existing_supervisor_pid_binding_match": True,
        "public_readback_verified": False, "effect_ack_done": False}, sort_keys=True), flush=True)
    os.execv(plan["run_argv"][0], plan["run_argv"])


def packaged_subject(package, pin, repository, pr, head, tree):
    """Verify an independently pinned export, without Git or a remote provider."""
    manifest = verify(package, pin)
    if (repository != manifest["source_repository"] or type(pr) is not int or pr < 1
            or head != manifest["source_head"] or tree != manifest["source_tree"]):
        raise ValueError("EXACT_PACKAGED_SUBJECT_MISMATCH")
    return {"repository": repository, "pr": pr, "head": head, "tree": tree}


def load_source(package, name):
    spec = importlib.util.spec_from_file_location(name, package / "src" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def owner_rest_grants(config, terminal_token):
    """Explicit owner capabilities, separate from the read-only terminal key."""
    grants = config.get("owner_rest_grants", [])
    if not isinstance(grants, list) or len(grants) > 32:
        raise ValueError("BOUNDED_OWNER_REST_GRANTS_REQUIRED")
    result, principals, tokens = [], set(), {terminal_token}
    for grant in grants:
        if (not isinstance(grant, dict) or set(grant) != {"principal", "token_file", "permissions"}
                or not re.fullmatch(r"[A-Za-z0-9_.@:-]{1,100}", grant.get("principal", ""))
                or grant["principal"] in principals or not isinstance(grant["permissions"], list)
                or not grant["permissions"] or any(p not in ("prepare", "commit", "readback") for p in grant["permissions"])
                or len(set(grant["permissions"])) != len(grant["permissions"])):
            raise ValueError("EXPLICIT_DISTINCT_OWNER_REST_CAPABILITY_REQUIRED")
        path = Path(grant["token_file"]); private_path(path)
        token = path.read_text().strip()
        if (not 32 <= len(token) <= 256 or not token.isascii()
                or any(ord(c) <= 32 or ord(c) >= 127 for c in token) or token in tokens):
            raise ValueError("DISTINCT_BOUNDED_OWNER_REST_SECRET_REQUIRED")
        principals.add(grant["principal"]); tokens.add(token)
        result.append({"principal": grant["principal"], "permissions": grant["permissions"], "token": token})
    return result


class OwnerREST:
    """Transport adapter of the original ledger; no Unix client or second store.

    Prepare records use the existing meta table. The original append transaction
    owns the effect. A fresh read-only SQLite connection verifies it, including
    recovery after a lost response or restart. No bearer secret enters the DB.
    """
    def __init__(self, runtime, terminal, state_dir):
        self.runtime, self.terminal, self.state_dir = runtime, terminal, state_dir

    def request(self, value):
        if (not isinstance(value, dict) or set(value) != {"schema", "request_id", "subject", "input"}
                or value["schema"] != "qikvrt_owner_rest_input_v1"
                or not isinstance(value["request_id"], str)
                or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value["request_id"])):
            raise ValueError("BOUNDED_OWNER_REST_REQUEST_REQUIRED")
        exact = self.runtime.ensure_subject()
        if mesh_wire(value["subject"]) != mesh_wire(exact):
            raise ValueError("EXACT_OWNER_REST_SUBJECT_MISMATCH")
        return {**value, "input": self.terminal._durable_input(value["input"])}

    def key(self, principal, request_id):
        return "owner-rest:" + digest(mesh_wire([principal, request_id]))

    def record(self, principal, request_id):
        row = self.runtime.ledger.db.execute("SELECT value FROM meta WHERE key=?",
            (self.key(principal, request_id),)).fetchone()
        if row is None: return None
        record = json.loads(row[0])
        request, plan = record["request"], record["plan"]
        frozen = self.request(request)
        event = plan["event"]
        if (set(record) != {"request", "plan", "record_hash"}
                or set(plan) != {"schema", "principal", "request_id", "subject", "input_hash", "ledger_id", "event", "expires_at"}
                or plan["schema"] != "qikvrt_owner_rest_terminal_preparation_v1"
                or plan["principal"] != principal or plan["request_id"] != request_id
                or frozen["request_id"] != request_id or plan["subject"] != frozen["subject"]
                or plan["ledger_id"] != self.runtime.ledger.epoch
                or plan["input_hash"] != "sha256:" + digest(mesh_wire(frozen["input"]))
                or event["payload"] != {"adapter": "QIKVRT_OWNER_REST_TERMINAL_V1",
                    "principal": principal, "request_id": request_id, "terminal_input": frozen["input"],
                    "input_hash": plan["input_hash"], "effect_ack_done": False}
                or event["subject"] != plan["subject"] or event["kind"] != "OBSERVE"
                or event["provenance"]["source"] != "transputer"
                or not re.fullmatch(r"terminal:[0-9a-f]{48}", event["provenance"]["native_event_id"])
                or type(plan["expires_at"]) is not int or record["record_hash"] != digest(mesh_wire(plan))):
            raise ValueError("OWNER_REST_PREPARATION_READBACK_MISMATCH")
        self.runtime.ledger._validate(event)
        return record

    def ticket(self, grant, record):
        return hmac.new(grant["token"].encode("ascii"), mesh_wire(record["plan"]), hashlib.sha256).hexdigest()

    def prepare(self, grant, value):
        value = self.request(value)
        ledger = self.runtime.ledger
        with ledger.condition:
            record = self.record(grant["principal"], value["request_id"])
            if record is not None and mesh_wire(record["request"]) != mesh_wire(value):
                raise ValueError("OWNER_REST_REPLAY_CONFLICT")
            if record is None:
                input_hash = "sha256:" + digest(mesh_wire(value["input"]))
                event = {"schema": self.terminal.NATIVE_SCHEMA, "kind": "OBSERVE", "subject": value["subject"],
                    "provenance": {"source": "transputer", "native_event_id": "terminal:" + secrets.token_hex(24)},
                    "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "message": "Universal Terminal: hash-bound durable input observation",
                    "payload": {"adapter": "QIKVRT_OWNER_REST_TERMINAL_V1", "principal": grant["principal"],
                        "request_id": value["request_id"], "terminal_input": value["input"],
                        "input_hash": input_hash, "effect_ack_done": False}}
                ledger._validate(event)
                plan = {"schema": "qikvrt_owner_rest_terminal_preparation_v1", "principal": grant["principal"],
                    "request_id": value["request_id"], "subject": value["subject"], "input_hash": input_hash,
                    "ledger_id": ledger.epoch, "event": event, "expires_at": int(time.time()) + self.terminal.TOKEN_TTL_SECONDS}
                record = {"request": value, "plan": plan, "record_hash": digest(mesh_wire(plan))}
                with ledger.db:
                    ledger.db.execute("INSERT INTO meta VALUES (?,?)",
                        (self.key(grant["principal"], value["request_id"]), mesh_wire(record).decode("utf-8")))
                if self.record(grant["principal"], value["request_id"]) != record:
                    raise ValueError("OWNER_REST_PREPARATION_READBACK_MISMATCH")
            return {"state": "PREPARED", "preparation": record["plan"], "record_hash": record["record_hash"],
                "prepare_hash": "sha256:" + record["record_hash"], "commit_token": self.ticket(grant, record),
                "ordinary_release": False, "EFFECT_ACK_DONE": False}

    def observed(self, record):
        epoch, event = self.terminal._durable_read(self.state_dir, record["plan"]["event"])
        if epoch != record["plan"]["ledger_id"]:
            raise ValueError("OWNER_REST_LEDGER_MISMATCH")
        return event

    def receipt(self, record, event, replayed):
        return {"state": "EFFECT_ACK_CONTINUE", "durable_persisted": True, "durable_readback": event,
            "principal": record["plan"]["principal"], "request_id": record["plan"]["request_id"],
            "prepare_hash": "sha256:" + record["record_hash"], "replayed": replayed,
            "independent_sqlite_readback": True, "ordinary_release": False, "EFFECT_ACK_DONE": False,
            "public_readback_verified": False, "authority_effect": False}

    def commit(self, grant, value, binding):
        value = self.request(value)
        with self.runtime.ledger.condition:
            record = self.record(grant["principal"], value["request_id"])
            if record is None: raise ValueError("OWNER_REST_PREPARATION_REQUIRED")
            if mesh_wire(record["request"]) != mesh_wire(value):
                raise ValueError("OWNER_REST_REPLAY_CONFLICT")
            if (binding["hash"] != record["record_hash"]
                    or not hmac.compare_digest(binding["token"], self.ticket(grant, record))):
                raise ValueError("OWNER_REST_COMMIT_BINDING_MISMATCH")
            event = self.observed(record)
            if event is not None: return self.receipt(record, event, True)
            if record["plan"]["expires_at"] <= time.time():
                raise ValueError("OWNER_REST_PREPARATION_EXPIRED")
            appended = self.runtime.append(record["plan"]["event"])
            event = self.observed(record)
            if event is None or mesh_wire(event) != mesh_wire(appended):
                raise ValueError("OWNER_REST_DURABLE_READBACK_MISMATCH")
            return self.receipt(record, event, False)

    def readback(self, grant, request_id, exact_subject):
        if mesh_wire(exact_subject) != mesh_wire(self.runtime.ensure_subject()):
            raise ValueError("EXACT_OWNER_REST_SUBJECT_MISMATCH")
        with self.runtime.ledger.condition:
            record = self.record(grant["principal"], request_id)
            if record is None: raise ValueError("OWNER_REST_PREPARATION_REQUIRED")
            event = self.observed(record)
            if event is None: raise ValueError("OWNER_REST_EVENT_NOT_OBSERVED")
            return self.receipt(record, event, True)


def native_carrier(package, pin, config, config_path, binding, token):
    """Reuse the recovered ledger/HTTP/Unix implementation; adapt only its source binding.

    The original Runtime requires Git. This S1 adapter binds the sealed
    package/config/volume and adds authenticated REST. Original bytes are frozen.
    """
    native = load_source(package, "qikvrt_temdd_event_ledger")

    class SealedRuntime(native.Runtime):
        def __init__(self):
            self.root = package
            self.repository, self.pr = config["source_repository"], config["subject_pr"]
            self.subject = packaged_subject(package, pin, self.repository, self.pr,
                                            config["source_head"], config["source_tree"])
            self.ledger = native.Ledger(config["state_dir"], self.subject)
            self.subscribers = threading.BoundedSemaphore(32)

        def ensure_subject(self):
            try:
                packaged_subject(package, pin, self.repository, self.pr,
                                 self.subject["head"], self.subject["tree"])
                private_path(config_path)
                if digest(config_path.read_bytes()) != binding["config_sha256"]:
                    raise native.Hold("EXACT_CONFIGURATION_CHANGED")
                volume_binding = Path(config["state_dir"]) / "binding.json"
                private_path(volume_binding)
                if json.loads(volume_binding.read_bytes()) != binding:
                    raise native.Hold("PERSISTENT_VOLUME_BINDING_MISMATCH")
                if self.ledger.stopped:
                    raise native.Hold(self.ledger.reason)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                self.ledger.stop(str(exc))
                raise native.Hold(str(exc)) from exc
            return self.subject

        def append(self, event):
            with self.ledger.condition:
                self.ensure_subject()
                if hasattr(self, "peer_rules"): self.peer_rules.enforce_event(event)
                return self.ledger.append(event)

    runtime_instance = SealedRuntime()
    ingress = server = None
    try:
        original_handler = native.make_handler(runtime_instance)
        terminal = sys.modules["qikvrt_effect_ack_http_terminal"]
        grants = owner_rest_grants(config, token)
        rest = OwnerREST(runtime_instance, terminal, config["state_dir"])
        rules = terminal.NativePeerRules(runtime_instance, config["node_id"], config["state_dir"], config.get("mesh_rule_grants", []))
        runtime_instance.peer_rules = rules

        class OwnerHTTP(original_handler):
            def access_discovery(self):
                host = self.headers.get("Host", "")
                if (self.path != "/.well-known/qik-vrt"
                        or len(self.headers.get_all("Host", [])) != 1
                        or len(self.headers.get_all("Origin", [])) > 1
                        or host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
                        or self.headers.get("Origin") not in (None, "http://" + host)):
                    return self._hold("NATIVE_DISCOVERY_EXACT_LOOPBACK_ROUTE_REQUIRED", 403)
                try:
                    exact = runtime_instance.ensure_subject()
                    live_grants = owner_rest_grants(config, token)
                    self._json(200, {
                        "schema": "qikvrt-native-access/v1", "subject": exact,
                        "client_scope": "ANY_HTTP_JSON_CLIENT_WITH_A_SEPARATELY_ADMITTED_CAPABILITY",
                        "github_write_identity_required": False, "browser_login_required": False,
                        "anonymous_writes_allowed": False,
                        "anonymous_journal_reads_allowed": False,
                        "adapters": {
                            "owner_input": {
                                "configured": any({"prepare", "commit", "readback"}.issubset(g["permissions"]) for g in live_grants),
                                "authentication": "PRIVATE_SCOPED_BEARER_AND_QIKVRT_OWNER",
                                "prepare": "/api/owner/prepare", "commit": "/api/owner/commit",
                                "readback": "/api/owner/receipts/{request_id}",
                                "request_schema": "qikvrt_owner_rest_input_v1",
                                "max_input_characters": 4096, "max_body_bytes": terminal.MAX_NATIVE_EVENT // 2,
                                "effect": "ORIGINAL_LEDGER_INPUT_PERSISTENCE_ONLY"},
                            "peer_rule": {
                                "configured": bool(config.get("mesh_work_peers") and config.get("mesh_rule_grants")),
                                "authentication": "EXISTING_ADMITTED_PEER_HMAC_AND_EXACT_REQUEST_RULE_SOURCE_BINDING",
                                "receive": "/api/mesh-work/rule/receive", "apply": "/api/mesh-work/rule/apply",
                                "readback": "/api/mesh-work/rule/readback/{request_id}/{challenge}"}},
                        "public_routing_verified": False, "peer_join_verified": False,
                        "ordinary_release": False, "effect_ack_done": False})
                except (ValueError, OSError, sqlite3.Error) as exc:
                    self._hold(str(exc) if isinstance(exc, ValueError) else "NATIVE_DISCOVERY_BINDING_UNAVAILABLE", 503)

            def peer_rule_http(self):
                """Existing peer HMAC, listener, source fences and native ledger."""
                self.close_connection = True
                self.connection.settimeout(5)
                peer = next((p for p in config.get("mesh_work_peers", [])
                             if p["node_id"] == self.headers.get("x-qikvrt-mesh-node")), None)
                if peer is None: return self._hold("MESH_WORK_PEER_NOT_ADMITTED", 403)
                try:
                    path = urlsplit(self.path)
                    if (path.query or path.fragment or self.path != path.path
                            or any(len(self.headers.get_all(k, [])) != 1 for k in
                                   ("Host", "x-qikvrt-mesh-node", "x-qikvrt-replication-signature"))
                            or self.headers["Host"] not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
                            or self.headers.get("Origin") is not None):
                        raise ValueError("PEER_RULE_EXACT_NATIVE_ROUTE_REQUIRED")
                    lengths = self.headers.get_all("Content-Length", [])
                    if (len(lengths) > 1 or self.headers.get("Transfer-Encoding") is not None
                            or self.command == "POST" and (len(lengths) != 1 or self.headers.get("Content-Type") != "application/json")):
                        raise ValueError("PEER_RULE_BOUNDED_BODY_REQUIRED")
                    size = int(lengths[0]) if lengths else 0
                    if not 0 <= size <= terminal.MAX_NATIVE_EVENT // 2 or self.command == "GET" and size:
                        raise ValueError("PEER_RULE_BOUNDED_BODY_REQUIRED")
                    raw = self.rfile.read(size)
                    if len(raw) != size: raise ValueError("PEER_RULE_COMPLETE_BODY_REQUIRED")
                    key = Path(peer["secret_file"]); private_path(key)
                    secret = key.read_bytes().strip()
                    signature = "sha256=" + hmac.new(secret, self.command.encode() + b"\n" + self.path.encode() + b"\n" + raw, hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(signature, self.headers["x-qikvrt-replication-signature"]):
                        return self._hold("MESH_WORK_SIGNATURE_REQUIRED", 401)
                    prefix = "/api/mesh-work/rule/"
                    if self.command == "POST" and self.path in (prefix + "receive", prefix + "apply"):
                        value = json.loads(raw)
                        if raw != terminal.canonical_json(value): raise ValueError("PEER_RULE_CANONICAL_BYTES_REQUIRED")
                        result = (rules.receive if self.path.endswith("/receive") else rules.apply)(value, peer)
                    elif self.command == "GET":
                        match = re.fullmatch(re.escape(prefix) + r"readback/([A-Za-z0-9_.:-]{1,100})/([a-f0-9]{32})", self.path)
                        if not match: raise ValueError("PEER_RULE_EXACT_NATIVE_ROUTE_REQUIRED")
                        key = rules.key({"sender_node_id": peer["node_id"], "request_id": match[1]})
                        record = rules.read_meta(key, cold=True)
                        if record is None:
                            # A pre-admitted exact request is not copied into the
                            # journal by a GET. Sender must first submit receive.
                            result = {"schema": "qikvrt-peer-rule-absent/v1", "request_id": match[1],
                                      "peer_node_id": config["node_id"], "subject": runtime_instance.ensure_subject(),
                                      "challenge": match[2], "effect_ack_done": False}
                        else: result = rules.readback(record["request"], peer, match[2])
                    else: raise ValueError("PEER_RULE_EXACT_NATIVE_ROUTE_REQUIRED")
                    body = mesh_wire(result)
                    response_signature = "sha256=" + hmac.new(secret, b"RESPONSE\n" + self.path.encode() + b"\n" + body, hashlib.sha256).hexdigest()
                    self.send_response(200)
                    for k, v in {"Content-Type": "application/json", "Content-Length": str(len(body)),
                                 "Cache-Control": "no-store", "x-qikvrt-replication-signature": response_signature}.items():
                        self.send_header(k, v)
                    self.end_headers(); self.wfile.write(body)
                except (ValueError, KeyError, TypeError, RecursionError) as exc:
                    self._hold(str(exc) if isinstance(exc, ValueError) else "PEER_RULE_INVALID_REQUEST", 409)
                except (OSError, sqlite3.Error): self._hold("PEER_RULE_NATIVE_STORE_UNAVAILABLE", 503)

            def owner_guard(self, permission):
                self.close_connection = True
                self.connection.settimeout(5)
                if not grants:
                    self._hold("OWNER_REST_NOT_AUTHORIZED", 503); return None
                host = self.headers.get("Host", "")
                if (host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
                        or self.headers.get("Origin") not in (None, "http://" + host)):
                    self._hold("OWNER_REST_SAME_ORIGIN_LOOPBACK_REQUIRED", 403); return None
                if any(len(self.headers.get_all(name, [])) != 1 for name in ("Host", "Authorization", "QIKVRT-Owner")):
                    self._hold("OWNER_REST_AUTHENTICATION_REQUIRED", 401); return None
                try:
                    live_grants = owner_rest_grants(config, token)
                except (OSError, ValueError):
                    self._hold("OWNER_REST_AUTHORITY_UNAVAILABLE", 503); return None
                auth = self.headers.get("Authorization", "").encode("utf-8")
                grant = next((g for g in live_grants if hmac.compare_digest(auth, ("Bearer " + g["token"]).encode("ascii"))), None)
                if grant is None:
                    self._hold("OWNER_REST_AUTHENTICATION_REQUIRED", 401); return None
                if self.headers.get("QIKVRT-Owner") != grant["principal"]:
                    self._hold("OWNER_REST_IDENTITY_MISMATCH", 403); return None
                if permission not in grant["permissions"]:
                    self._hold("OWNER_REST_PERMISSION_REQUIRED", 403); return None
                return grant

            def do_GET(self):
                if self.path == "/.well-known/qik-vrt": return self.access_discovery()
                # Original native events may contain private OwnerREST/Unix input.
                # The read-only terminal capability, never public discovery or an
                # unrelated OwnerREST principal, authorizes the complete stream.
                if urlsplit(self.path).path == "/api/temdd/events" and not self._authenticated(): return
                if self.path.startswith("/api/mesh-work/rule/"): return self.peer_rule_http()
                route = urlsplit(self.path)
                prefix = "/api/owner/receipts/"
                if not route.path.startswith(prefix): return super().do_GET()
                grant = self.owner_guard("readback")
                if grant is None: return
                try:
                    request_id = route.path[len(prefix):]
                    if (route.query or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", request_id)
                            or len(self.headers.get_all("QIKVRT-Subject", [])) != 1):
                        raise ValueError("EXACT_OWNER_REST_READBACK_ROUTE_REQUIRED")
                    result = rest.readback(grant, request_id, json.loads(self.headers["QIKVRT-Subject"]))
                    self._json(200, result, state=result["state"], record_hash=result["prepare_hash"][7:])
                except (ValueError, KeyError, TypeError, RecursionError) as exc:
                    self._hold(str(exc) if isinstance(exc, ValueError) else "INVALID_OWNER_REST_REQUEST", 409)
                except (OSError, sqlite3.Error): self._hold("OWNER_REST_READBACK_UNAVAILABLE", 503)

            def do_POST(self):
                if self.path.startswith("/api/mesh-work/rule/"): return self.peer_rule_http()
                route = urlsplit(self.path)
                operation = {"/api/owner/prepare": "prepare", "/api/owner/commit": "commit"}.get(route.path)
                if operation is None:
                    self.close_connection = True
                    return self._hold("OWNER_REST_ROUTE_REQUIRED_LOCAL_UNIX_ADAPTER_SEPARATE", 405)
                grant = self.owner_guard(operation)
                if grant is None: return
                try:
                    if route.query or any(len(self.headers.get_all(h, [])) != 1 for h in
                            ("Content-Length", "Content-Type", "Effect-Ack-Request")):
                        raise ValueError("BOUNDED_OWNER_REST_HTTP_HEADERS_REQUIRED")
                    if not 1 <= int(self.headers["Content-Length"]) <= terminal.MAX_NATIVE_EVENT // 2:
                        raise ValueError("BOUNDED_OWNER_REST_BODY_REQUIRED")
                    effect = terminal.parse_effect_ack_request(self.headers["Effect-Ack-Request"])
                    if effect["mode"] != operation: raise ValueError("OWNER_REST_EFFECT_ACK_MODE_MISMATCH")
                    value = self._read_body()
                    result = rest.prepare(grant, value) if operation == "prepare" else rest.commit(grant, value, effect)
                    self._json(200, result, state="EFFECT_ACK_CONTINUE", record_hash=result.get("record_hash", result["prepare_hash"][7:]),
                        commit_token=result.get("commit_token"))
                except (ValueError, KeyError, TypeError, RecursionError) as exc:
                    self._hold(str(exc) if isinstance(exc, ValueError) else "INVALID_OWNER_REST_REQUEST", 409)
                except (OSError, sqlite3.Error): self._hold("OWNER_REST_PERSISTENCE_OR_READBACK_UNAVAILABLE", 503)

        if config.get("unix_ingress", True):
            ingress = native.make_ingress(runtime_instance)
            # Defense in depth for the separate mode-0600 owner-only adapter.
            def same_owner(request, _address):
                _, uid, _ = struct.unpack("3i", request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                return uid == os.geteuid()
            ingress.verify_request = same_owner
        server = ThreadingHTTPServer(("127.0.0.1", config["terminal_port"]), OwnerHTTP)
        server.terminal_auth_token = token
        server.runtime_binding = binding
        return runtime_instance, ingress, server
    except BaseException:
        if server is not None: server.server_close()
        if ingress is not None: ingress.server_close()
        runtime_instance.ledger.close()
        raise


def novnc_readback(package, port):
    # A loopback startup read must never inherit a provider/proxy route.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:' + str(port) + '/vnc.html', timeout=2) as response:
        return response.status == 200 and response.read() == (package / 'runtime/self-host/novnc/vnc.html').read_bytes()


def _xvfb_command(display):
    # The one-shot xdpyinfo readiness client disconnects before Firefox starts.
    # Keep that display generation alive while its first persistent clients join.
    return [shutil.which("Xvfb"), display, "-screen", "0", "1440x900x24",
            "-noreset", "-nolisten", "tcp"]


def browser_carrier(package, manifest, config, volume):
    """New portable start adapter of the recovered Firefox/Xvfb/VNC recipe.

    No downloader, provider, unsigned-addon exception or public listener.
    Browser profiles remain private; the existing host owns HTTPS admission.
    """
    if "browser_runtime" not in manifest: raise ValueError("BROWSER_PACKAGE_REQUIRED")
    password = Path(config["browser_password_file"]); private_path(password)
    secret = password.read_bytes().rstrip(b"\n")
    if len(secret) != 8 or any(c < 33 or c > 126 for c in secret):
        raise ValueError("EIGHT_ASCII_BYTE_PRIVATE_VNC_PASSWORD_REQUIRED")
    directory = volume / "browser"
    directory.mkdir(mode=0o700, exist_ok=True); private_path(directory, directory=True)
    for name in ("profile", "home", "cache", "logs"):
        (directory / name).mkdir(mode=0o700, exist_ok=True); private_path(directory / name, directory=True)
    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "DISPLAY": config["display"],
        "HOME": str(directory / "home"), "XDG_CACHE_HOME": str(directory / "cache"),
        "XDG_CONFIG_HOME": str(directory / "home")}
    processes, logs = [], []
    def spawn(name, argv):
        path = directory / "logs" / (name + ".log")
        if path.exists() or path.is_symlink(): private_path(path)
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        log = os.fdopen(fd, "wb"); logs.append(log)
        p = subprocess.Popen(argv, env=env, cwd=directory, stdout=log, stderr=log)
        processes.append(p); return p
    def ready(check, edge):
        until = time.monotonic() + 20
        while time.monotonic() < until:
            if any(p.poll() is not None for p in processes): raise ValueError("BROWSER_CHILD_EXITED")
            try:
                if check(): return
            except (OSError, ValueError, subprocess.SubprocessError): pass
            time.sleep(.05)  # bounded startup probe, no runtime polling
        raise ValueError("BROWSER_STARTUP_READBACK_TIMEOUT:" + edge)
    try:
        spawn("xvfb", _xvfb_command(config["display"]))
        ready(lambda: subprocess.run([shutil.which("xdpyinfo"), "-display", config["display"]],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2).returncode == 0, 'X11_DISPLAY')
        spawn("vnc", [shutil.which("x11vnc"), "-display", config["display"], "-forever", "-shared", "-localhost",
            "-no6", "-rfbportv6", "0", "-rfbport", str(config["vnc_port"]), "-passwdfile", str(password)])
        spawn("novnc", [shutil.which("websockify"), "--web=" + str(package / "runtime/self-host/novnc"),
            "127.0.0.1:" + str(config["novnc_port"]), "127.0.0.1:" + str(config["vnc_port"])])
        firefox_package = manifest["browser_runtime"].get("firefox_command", "firefox-esr")
        browser_commands(firefox_package)  # fail closed on an undeclared executable
        spawn("firefox", [str(firefox_binary(firefox_package)), "--no-remote", "--profile", str(directory / "profile"),
            "http://127.0.0.1:" + str(config["terminal_port"]) + "/AI"])
        def browser_window():
            raw = subprocess.check_output([shutil.which("xwininfo"), "-display", config["display"], "-root", "-tree"],
                env=env, timeout=2).decode()
            title = re.search(r'<title>([^<]+)</title>', (package / 'docs/terminal/temdd/index.html').read_text())[1]
            return '"Navigator" "firefox' in raw and '"' + title in raw
        ready(browser_window, 'FIREFOX_NATIVE_DOCUMENT')
        ready(lambda: novnc_readback(package, config['novnc_port']), 'NOVNC_HTTP')
        return processes, logs
    except BaseException:
        stop_children(processes, logs)
        raise


def stop_children(processes, logs=()):
    for p in processes:
        if p.poll() is None: p.terminate()
    for p in processes:
        try: p.wait(timeout=5)
        except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=2)
    for log in logs: log.close()


def migration_module():
    spec = importlib.util.spec_from_file_location("qikvrt_self_host_migration",
        Path(__file__).with_name("qikvrt_self_host_migration.py"))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def provider_module():
    spec = importlib.util.spec_from_file_location("qikvrt_self_host_provider",
        Path(__file__).with_name("qikvrt_self_host_provider.py"))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def start(package, pin, config_path, monolith=False):
    manifest = verify(package, pin)
    if json.loads((package / DEFINITION).read_bytes()).get('role_policy'):
        deployment_roles(package)
    private_path(config_path)
    raw = config_path.read_bytes()
    config = json.loads(raw)
    fields = {"schema", "node_id", "source_head", "source_tree", "adapter", "state_dir", "host", "port", "terminal_port", "terminal_token_file", "github_webhook_secret_file", "terminal_profile", "subject_pr", "source_repository", "browser_password_file", "novnc_port", "vnc_port", "display", "migration_export_sha256", "mesh_work_peers", "mesh_rule_grants", "owner_rest_grants", "unix_ingress", "mesh_file", "mesh_file_allowed_origins"}
    if (set(config) - fields or config.get("schema") != "qikvrt-self-host-config/v1"
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", config.get("node_id", ""))
            or config.get("adapter") not in {"none", "github"} or config.get("host") not in {"127.0.0.1", "0.0.0.0"}
            or any(type(config.get(k)) is not int or not 1 <= config[k] <= 65535 for k in ("port", "terminal_port"))
            or config["port"] == config["terminal_port"]
            or any(config.get(k) != manifest[k] for k in ("source_head", "source_tree"))):
        raise ValueError("START_CONFIGURATION_BINDING_MISMATCH")
    peers = config.get("mesh_work_peers", [])
    if not isinstance(peers, list): raise ValueError("MESH_WORK_ADMITTED_PEERS_REQUIRED")
    peer_ids, peer_keys = set(), set()
    for peer in peers:
        if (not isinstance(peer, dict) or set(peer) != {"node_id", "repository", "secret_file"}
                or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", peer.get("node_id", ""))
                or peer["node_id"] in peer_ids | {"__proto__", "constructor", "prototype"}
                or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", peer.get("repository", ""))):
            raise ValueError("MESH_WORK_ADMITTED_PEERS_REQUIRED")
        key = Path(peer["secret_file"]); private_path(key)
        raw_key = key.read_bytes().strip()
        if not 32 <= len(raw_key) <= 256 or not raw_key.isascii() or any(c <= 32 or c >= 127 for c in raw_key) or raw_key in peer_keys:
            raise ValueError("MESH_WORK_DISTINCT_BOUNDED_PEER_KEYS_REQUIRED")
        peer_ids.add(peer["node_id"]); peer_keys.add(raw_key)
    profile = config.get("terminal_profile", "reference")
    if profile not in {"reference", "temdd", "firefox"}:
        raise ValueError("UNKNOWN_TERMINAL_PROFILE")
    if (type(config.get("unix_ingress", True)) is not bool
            or profile == "reference" and (config.get("owner_rest_grants") or config.get("mesh_rule_grants") or config.get("unix_ingress") is False)):
        raise ValueError("NATIVE_OWNER_REST_AND_UNIX_ADAPTER_CONFIGURATION_REQUIRED")
    if profile != "reference" and (type(config.get("subject_pr")) is not int or config["subject_pr"] < 1
            or config.get("source_repository") != manifest["source_repository"]
            or manifest.get("native_terminal_daemon_included") is not True):
        raise ValueError("EXACT_NATIVE_TERMINAL_SUBJECT_REQUIRED")
    if profile == "firefox" and ("browser_runtime" not in manifest
            or not re.fullmatch(r":[1-9][0-9]{0,3}", config.get("display", ""))
            or any(type(config.get(k)) is not int or not 1 <= config[k] <= 65535 for k in ("novnc_port", "vnc_port"))
            or len({config[k] for k in ("port", "terminal_port", "novnc_port", "vnc_port")}) != 4
            or not config.get("browser_password_file")):
        raise ValueError("EXACT_BROWSER_CONFIGURATION_REQUIRED")
    if config["adapter"] == "github":
        try:
            if runtime("gh")["version"].splitlines()[0].split()[:3] != ["gh", "version", "2.96.0"]:
                raise ValueError("GITHUB_ADAPTER_REQUIRES_LOCKED_GH")
        except OSError as exc:
            raise ValueError("GITHUB_ADAPTER_REQUIRES_LOCKED_GH") from exc
        if not config.get("github_webhook_secret_file"):
            raise ValueError("PRIVATE_GITHUB_WEBHOOK_SECRET_REQUIRED")
        secret = Path(config["github_webhook_secret_file"])
        private_path(secret)
        if not 32 <= len(secret.read_bytes().strip()) <= 256:
            raise ValueError("BOUNDED_PRIVATE_GITHUB_WEBHOOK_SECRET_REQUIRED")
    if config["adapter"] == "none" and config.get("github_webhook_secret_file"):
        raise ValueError("GITHUB_SECRET_WITHOUT_GITHUB_ADAPTER")
    token_file = Path(config["terminal_token_file"])
    private_path(token_file)
    token = token_file.read_text().strip()
    if len(token) < 32 or len(token) > 256 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError("BOUNDED_TERMINAL_SECRET_REQUIRED")
    owner_rest_grants(config, token)
    volume = Path(config["state_dir"])
    private_path(volume, directory=True)
    if "mesh_file" in config:
        if config["mesh_file"] != "repository.qmesh":
            raise ValueError("PORTABLE_MESH_BASENAME_REQUIRED")
        private_path(volume / config["mesh_file"])
    origins = config.get("mesh_file_allowed_origins", [])
    if (not isinstance(origins, list) or len(origins) > 16
            or any(not isinstance(origin, str) or (origin != "null" and
                (urllib.parse.urlparse(origin).scheme != "https" or
                 urllib.parse.urlparse(origin).path or urllib.parse.urlparse(origin).params or
                 urllib.parse.urlparse(origin).query or urllib.parse.urlparse(origin).fragment or
                 urllib.parse.urlparse(origin).username or not urllib.parse.urlparse(origin).hostname))
                for origin in origins)):
        raise ValueError("EXACT_MESH_CLIENT_ORIGINS_REQUIRED")
    # A failed or rolled-back import is never repaired by restarting/rebinding.
    if (volume / ".MIGRATION_HOLD.json").exists() or (volume / ".MIGRATION_HOLD.json").is_symlink():
        raise ValueError("MIGRATION_TARGET_QUARANTINED")
    if volume == package or package in volume.parents or volume in package.parents:
        raise ValueError("STATE_VOLUME_MUST_BE_SEPARATE_FROM_PACKAGE")
    for name in ("monitor", "temdd", "receipts"):
        (volume / name).mkdir(mode=0o700, exist_ok=True)
        private_path(volume / name, directory=True)
    lock_fd = os.open(volume / "node.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "w") as lock:
        private_path(volume / "node.lock")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (volume / ".MIGRATION_HOLD.json").exists() or (volume / ".MIGRATION_HOLD.json").is_symlink():
            raise ValueError("MIGRATION_TARGET_QUARANTINED")
        binding = {"schema": "qikvrt-self-host-volume/v1", "node_id": config["node_id"], "manifest_sha256": pin,
                   "config_sha256": digest(raw), "source_head": manifest["source_head"], "source_tree": manifest["source_tree"]}
        if "migration_export_sha256" in config:
            migration_module().start_receipt(volume, config["migration_export_sha256"], binding, private_path)
        bound_path = volume / "binding.json"
        if bound_path.exists() or bound_path.is_symlink():
            private_path(bound_path)
            if json.loads(bound_path.read_bytes()) != binding:
                raise ValueError("PERSISTENT_VOLUME_BINDING_MISMATCH")
        else:
            with bound_path.open("xb") as dest:
                os.chmod(bound_path, 0o600)
                dest.write(raw_json(binding)); dest.flush(); os.fsync(dest.fileno())
            fd = os.open(volume, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        for file in (volume / "monitor").iterdir():
            private_path(file)
        terminal = load_source(package, "qikvrt_effect_ack_http_terminal")
        native_runtime = ingress = None
        if profile == "reference":
            server = ThreadingHTTPServer(("127.0.0.1", config["terminal_port"]), terminal.Handler)
        else:
            native_runtime, ingress, server = native_carrier(package, pin, config, config_path, binding, token)
        server.terminal_auth_token = token
        server.runtime_binding = binding
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        ingress_thread = None
        if ingress is not None:
            ingress_thread = threading.Thread(target=ingress.serve_forever, daemon=True)
            ingress_thread.start()
        env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "QIKVRT_NODE_CONFIG": str(config_path),
               "QIKVRT_NODE_PACKAGE": str(package), "QIKVRT_NODE_MANIFEST_SHA256": pin,
               "QIKVRT_NODE_CONFIG_SHA256": digest(raw)}
        if monolith: env["QIKVRT_MONOLITH_MODE"] = "SQLITE_CARRIER_V1"
        process = None
        browser_processes, browser_logs = [], []
        def stop(_signum, _frame):
            if process is not None and process.poll() is None:
                process.terminate()
        old_handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            if profile == "firefox":
                browser_processes, browser_logs = browser_carrier(package, manifest, config, volume)
            # flock belongs to the shared open-file description. Keep it in
            # the monitor too, so an isolated launcher SIGKILL cannot admit a
            # second writer while the original monitor is still running.
            process = subprocess.Popen([shutil.which("node"), str(package / "docs/monitor/self-host.mjs")],
                                       cwd=package, env=env, pass_fds=(lock.fileno(),))
            if browser_processes:
                # Linux pidfds wait for actual child exits without timed polls.
                import select
                fds = [os.pidfd_open(p.pid) for p in [process, *browser_processes]]
                try:
                    select.select(fds, [], [])
                    if any(p.poll() is not None for p in browser_processes):
                        raise ValueError("BROWSER_CHILD_EXITED_AFTER_READINESS")
                    return process.wait()
                finally:
                    for fd in fds: os.close(fd)
            return process.wait()
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            server.shutdown(); server.server_close(); thread.join(timeout=2)
            stop_children(browser_processes, browser_logs)
            if native_runtime is not None:
                native_runtime.ledger.stop()
                if ingress is not None:
                    ingress.shutdown(); ingress.server_close(); ingress_thread.join(timeout=6)
                native_runtime.ledger.close()
            for s, handler in old_handlers.items(): signal.signal(s, handler)


def oci_to_docker_archive(source, output, tag):
    """Repackage the already verified OCI bytes for existing Docker load.

    No builder, filesystem extraction, image/config rewrite or registry fetch.
    Verify every blob, decompressed diff ID and the original image config.
    """
    import gzip
    import io
    if not re.fullmatch(r"[a-z0-9][a-z0-9:._/-]{1,150}", tag):
        raise ValueError("LOCAL_DIAGNOSTIC_IMAGE_TAG_REQUIRED")
    output = Path(output)
    if output.exists(): raise ValueError("CREATE_ONLY_DOCKER_ARCHIVE_REQUIRED")
    with tarfile.open(source, "r:*") as original, tempfile.TemporaryDirectory() as work:
        def object_bytes(descriptor):
            key=descriptor["digest"]
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", key):
                raise ValueError("OCI_SHA256_DESCRIPTOR_REQUIRED")
            raw=original.extractfile("blobs/sha256/"+key[7:]).read()
            if len(raw)!=descriptor["size"] or digest(raw)!=key[7:]:
                raise ValueError("OCI_OBJECT_DIGEST_MISMATCH")
            return raw
        index=json.loads(original.extractfile("index.json").read())
        if len(index["manifests"])!=1: raise ValueError("SINGLE_OCI_IMAGE_REQUIRED")
        image=json.loads(object_bytes(index["manifests"][0]))
        config_raw=object_bytes(image["config"]);config=json.loads(config_raw)
        diff_ids=config["rootfs"]["diff_ids"]
        if len(diff_ids)!=len(image["layers"]): raise ValueError("OCI_DIFF_ID_COUNT_MISMATCH")
        config_name=image["config"]["digest"][7:]+".json"
        with tarfile.open(output,"w") as target:
            def add(name,raw):
                entry=tarfile.TarInfo(name);entry.size=len(raw);entry.mode=0o644
                target.addfile(entry,io.BytesIO(raw))
            add(config_name,config_raw)
            layers=[]
            for i,descriptor in enumerate(image["layers"]):
                key=descriptor["digest"]
                if not re.fullmatch(r"sha256:[a-f0-9]{64}",key):
                    raise ValueError("OCI_LAYER_DESCRIPTOR_REQUIRED")
                compressed=original.extractfile("blobs/sha256/"+key[7:])
                # Stream and verify compressed bytes before decompression.
                frozen=Path(work)/"blob";h=hashlib.sha256();size=0
                with frozen.open("wb") as f:
                    for block in iter(lambda:compressed.read(8*1024*1024),b""):
                        f.write(block);h.update(block);size+=len(block)
                if size!=descriptor["size"] or "sha256:"+h.hexdigest()!=key:
                    raise ValueError("OCI_LAYER_BLOB_MISMATCH")
                media=descriptor.get("mediaType","")
                if media not in ("application/vnd.oci.image.layer.v1.tar+gzip",
                        "application/vnd.oci.image.layer.v1.tar"):
                    raise ValueError("SUPPORTED_OCI_LAYER_COMPRESSION_REQUIRED")
                raw_layer=Path(work)/"layer";h=hashlib.sha256()
                opener=gzip.open if media.endswith("+gzip") else open
                with opener(frozen,"rb") as f,raw_layer.open("wb") as out:
                    for block in iter(lambda:f.read(8*1024*1024),b""):
                        h.update(block);out.write(block)
                if "sha256:"+h.hexdigest()!=diff_ids[i]:
                    raise ValueError("OCI_UNCOMPRESSED_DIFF_ID_MISMATCH")
                name=key[7:]+"/layer.tar";layers.append(name)
                entry=tarfile.TarInfo(name);entry.size=raw_layer.stat().st_size;entry.mode=0o644
                with raw_layer.open("rb") as f: target.addfile(entry,f)
            add("manifest.json",raw_json([{"Config":config_name,"RepoTags":[tag],"Layers":layers}]))
    return {"config_digest":image["config"]["digest"],"diff_ids":diff_ids,
        "tag":tag,"rebuilt":False,"config_rewritten":False,"effect_ack_done":False}


def firefox_release_minimum_satisfied(version_output):
    """Bind the actual browser output to the unchanged Owner minimum 158.0."""
    import re
    version = re.search(r"Firefox\s+(\d+)(?:\.(\d+))?", version_output)
    return version is not None and (int(version[1]), int(version[2] or 0)) >= (158, 0)


def firefox_release_provision(output):
    """Official signed Mozilla APT Release package on the retained Debian base.

    No full distribution upgrade, removal, native rebuild, signing exception,
    developer credentials, extension signing or production acceptance.
    """
    import re
    import urllib.request
    if os.geteuid() != 0: raise ValueError("FIREFOX_RELEASE_PROVISION_REQUIRES_IMAGE_BUILDER")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "qikvrt-firefox-release-provision/v1",
        "state": "HOLD_FIREFOX_RELEASE_PROVISION", "minimum": "158.0",
        "origin": "https://packages.mozilla.org/apt", "channel": "release",
        "key_fingerprint": "35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3",
        "extension_activation_verified": False, "effect_ack_done": False,
        "public_production_verified": False, "ordinary_release": False}
    def command(*args, capture=False, cwd=None):
        return subprocess.run(args, check=True, cwd=cwd, timeout=300, text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None).stdout
    def packages():
        raw = command("dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n", capture=True)
        return dict(line.split("\t", 1) for line in raw.splitlines())
    before = packages()
    try:
        command("apt-get", "update")
        command("apt-get", "install", "-y", "--no-install-recommends", "--no-remove", "gnupg")
        receipt["gpg_version"] = command("gpg", "--version", capture=True).splitlines()[0]
        with urllib.request.urlopen(receipt["origin"] + "/repo-signing-key.gpg", timeout=30) as response:
            key = response.read(65537)
        if not 0 < len(key) <= 65536: raise ValueError("MOZILLA_APT_KEY_SIZE_REQUIRED")
        with tempfile.TemporaryDirectory(prefix="qikvrt-mozilla-key-") as work:
            work = Path(work); key_path = work / "key.asc"; key_path.write_bytes(key)
            keys = command("gpg", "--batch", "--homedir", str(work), "--with-colons",
                "--show-keys", str(key_path), capture=True)
            primary = []; expecting = False
            for line in keys.splitlines():
                fields = line.split(":")
                if fields[0] == "pub": expecting = True
                elif fields[0] == "fpr" and expecting:
                    primary.append(fields[9]); expecting = False
            if primary != [receipt["key_fingerprint"]]: raise ValueError("MOZILLA_APT_PRIMARY_KEY_MISMATCH")
        keyring = Path("/etc/apt/keyrings/packages.mozilla.org.asc")
        keyring.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        keyring.write_bytes(key); keyring.chmod(0o644)
        Path("/etc/apt/sources.list.d/qikvrt-mozilla.list").write_text(
            "deb [signed-by=" + str(keyring) + "] " + receipt["origin"] + " mozilla main\n")
        Path("/etc/apt/preferences.d/qikvrt-mozilla").write_text(
            "Package: firefox\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n")
        command("apt-get", "update")
        policy = command("apt-cache", "policy", "firefox", capture=True)
        (output / "apt-policy.txt").write_text(policy)
        candidate = re.search(r"^\s*Candidate:\s*(\S+)\s*$", policy, re.MULTILINE)
        if candidate is None or not re.fullmatch(r"(?:\d+:)?\d+[.][0-9A-Za-z.+~:-]+", candidate[1]):
            raise ValueError("MOZILLA_FIREFOX_PACKAGE_CANDIDATE_REQUIRED")
        version = candidate[1]
        command("dpkg", "--compare-versions", version, "ge", "158")
        with tempfile.TemporaryDirectory(prefix="qikvrt-firefox-deb-") as work:
            # Only public authenticated package bytes live here; permit _apt's
            # ordinary sandbox to read the selected local DEB.
            Path(work).chmod(0o755)
            command("apt-get", "download", "firefox=" + version, cwd=work)
            archives = list(Path(work).glob("*.deb"))
            if len(archives) != 1: raise ValueError("SINGLE_MOZILLA_FIREFOX_DEB_REQUIRED")
            package = archives[0]
            metadata = command("dpkg-deb", "-f", str(package), "Package", "Version", "Architecture", capture=True)
            if "Package: firefox\n" not in metadata or "Version: " + version + "\n" not in metadata:
                raise ValueError("MOZILLA_FIREFOX_DEB_IDENTITY_REQUIRED")
            receipt.update(deb_sha256=digest(package.read_bytes()), deb_bytes=package.stat().st_size,
                deb_metadata=metadata, apt_key_sha256=digest(key), apt_policy_sha256=digest(policy.encode()))
            command("apt-get", "install", "-y", "--no-install-recommends", "--no-remove", str(package))
        binary = firefox_binary("firefox")
        owned = command("dpkg-query", "-L", "firefox", capture=True).splitlines()
        if str(binary) not in owned: raise ValueError("MOZILLA_FIREFOX_ELF_PACKAGE_OWNERSHIP_REQUIRED")
        installed = command("dpkg-query", "-W", "-f=${Version}", "firefox", capture=True).strip()
        browser_version = command(str(binary), "--version", capture=True).strip()
        if installed != version or not firefox_release_minimum_satisfied(browser_version):
            raise ValueError("INSTALLED_FIREFOX_RELEASE_BELOW_OWNER_MINIMUM")
        after = packages()
        receipt.update(state="FIREFOX_RELEASE_PROVISIONED_PENDING_SIGNED_XPI", package="firefox",
            debian_package_version=installed, binary_path=str(binary), binary_sha256=digest(binary.read_bytes()),
            firefox_version_output=browser_version, minimum_satisfied=True,
            package_changes={name: {"before": before.get(name), "after": after.get(name)}
                for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)})
        command("rm", "-rf", "/var/lib/apt/lists")
        return receipt
    except Exception as error:
        receipt["provision_error"] = str(error); raise
    finally:
        (output / "provision.json").write_bytes(raw_json(receipt))


def firefox_profile_xpi_state(path):
    """Removal by Gecko is an observation, not a broken diagnostic."""
    path = Path(path)
    present = path.is_file()
    return {"profile_xpi_present": present,
        "profile_xpi_sha256": digest(path.read_bytes()) if present else None}


def firefox_xpi_source_binding(xpi, source):
    """Verify unchanged Standard payload; signature files are not signature proof."""
    import zipfile
    xpi, source = Path(xpi), Path(source)
    raw = xpi.read_bytes()
    if not 0 < len(raw) <= 1024 * 1024: raise ValueError("BOUNDED_FIREFOX_XPI_REQUIRED")
    names = {"manifest.json", "background.js", "content.js", "options.html", "options.js", "terminal.css", "client.html"}
    metadata = {"meta-inf/manifest.mf", "meta-inf/mozilla.sf", "meta-inf/mozilla.rsa",
        "meta-inf/cose.manifest", "meta-inf/cose.sig"}
    records = []
    with zipfile.ZipFile(xpi) as archive:
        entries = archive.infolist(); actual = [entry.filename for entry in entries]
        if len(actual) != len(set(actual)) or not names <= set(actual) or len(actual) > len(names) + len(metadata) + 1:
            raise ValueError("EXACT_STANDARD_FIREFOX_XPI_INVENTORY_REQUIRED")
        for entry in entries:
            if (entry.flag_bits & 1 or entry.file_size > 1024 * 1024 or
                    stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK):
                raise ValueError("REGULAR_BOUNDED_FIREFOX_XPI_ENTRY_REQUIRED")
            if entry.filename not in names | {"README.md"}:
                if entry.filename.lower() not in metadata:
                    raise ValueError("FOREIGN_FIREFOX_XPI_PAYLOAD_FORBIDDEN")
                continue
            data = archive.read(entry)
            if data != (source / entry.filename).read_bytes():
                raise ValueError("FIREFOX_XPI_SOURCE_BYTES_MISMATCH:" + entry.filename)
            records.append({"path": entry.filename, "git_blob": hashlib.sha1(
                b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(), "sha256": digest(data)})
    return {"xpi_sha256": digest(raw), "xpi_bytes": len(raw), "source_files": records,
        "signature_metadata_present": any(name.lower() in metadata for name in actual),
        "mozilla_signature_verified": False, "effect_ack_done": False}


def firefox_amo_runtime_fingerprint(source):
    """Keep unrelated AMO helpers out of the existing S1 causal identity.

    All pre-existing imports, globals and runtime bodies remain bound. Only the
    new AMO CLI branch/options are projected out; this is no acceptance receipt.
    """
    import ast
    module = ast.parse(source)
    module.body = [node for node in module.body if not (
        isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name.startswith("firefox_amo_"))]
    for node in module.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "main": continue
        node.body = [item for item in node.body if not (
            isinstance(item, ast.Expr) and isinstance(item.value, ast.Call)
            and isinstance(item.value.func, ast.Attribute) and item.value.func.attr == "add_argument"
            and item.value.args and isinstance(item.value.args[0], ast.Constant)
            and (str(item.value.args[0].value).startswith("--amo-") or
                 item.value.args[0].value in {"--image", "--receipt", "--oci-archive", "--second-oci-archive",
                    "--carrier-archive", "--carrier-oci-archive", "--production-binding", "--binding-sha256",
                    "--ca-file", "--cert-file", "--key-file"}))]
        for item in ast.walk(node):
            if isinstance(item, ast.keyword) and item.arg == "choices" and isinstance(item.value, ast.Tuple):
                item.value.elts = [v for v in item.value.elts if not (
                    isinstance(v, ast.Constant) and (v.value == "firefox-amo-unlisted" or
                        isinstance(v.value, str) and v.value.startswith("container-")))]
        for item in node.body:
            if not isinstance(item, ast.Try): continue
            first = item.body[0]
            if (isinstance(first, ast.If) and isinstance(first.test, ast.Compare)
                    and any(isinstance(v, ast.Constant) and v.value == "firefox-amo-unlisted"
                            for v in first.test.comparators)):
                item.body = first.orelse + item.body[1:]
        class ContainerCLIProjection(ast.NodeTransformer):
            def visit_If(self, branch):
                test = branch.test
                if (isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute)
                        and test.func.attr == "startswith" and ast.unparse(test.func.value) == "args.operation"
                        and len(test.args) == 1 and isinstance(test.args[0], ast.Constant)
                        and test.args[0].value == "container-"):
                    return [self.visit(child) for child in branch.orelse]
                return self.generic_visit(branch)
        ContainerCLIProjection().visit(node)
    return digest(ast.dump(module, include_attributes=False).encode())


def firefox_amo_input(root, head, tree):
    """The signing upload is precisely the committed Standard components."""
    import io
    import zipfile
    root = Path(root)
    if (not re.fullmatch(r"[a-f0-9]{40}", head or "") or
            not re.fullmatch(r"[a-f0-9]{40}", tree or "") or
            git(root, "rev-parse", "HEAD").decode() != head or
            git(root, "rev-parse", "HEAD^{tree}").decode() != tree):
        raise ValueError("AMO_EXACT_HEAD_TREE_REQUIRED")
    policy = json.loads(git(root, "show", head + ":policy/CANONICAL_UPSTREAM_REMOTE_V1.json"))
    if policy["canonical_upstream"]["repository"] != "ingolf-lohmann/qik-vrt":
        raise ValueError("AMO_OWNER_AUTHORITY_REQUIRED")
    names = ("manifest.json", "background.js", "content.js", "options.html", "options.js", "terminal.css", "client.html")
    prefix = "browser/firefox/qikvrt-terminal/"
    stream = io.BytesIO(); records = []
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            path = prefix + name; local = root / path
            if local.is_symlink() or not local.is_file(): raise ValueError("AMO_REGULAR_STANDARD_SOURCE_REQUIRED")
            # git() strips bytes, so obtain payloads without that convenience wrapper.
            raw = subprocess.check_output(["git", "-C", str(root), "show", head + ":" + path],
                timeout=30, stderr=subprocess.DEVNULL)
            if raw != local.read_bytes(): raise ValueError("AMO_DIRTY_STANDARD_SOURCE_FORBIDDEN")
            if not 0 < len(raw) <= 1024 * 1024: raise ValueError("AMO_BOUNDED_STANDARD_SOURCE_REQUIRED")
            info = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
            records.append({"path": name, "git_blob": hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(), "sha256": digest(raw)})
    manifest = json.loads((root / prefix / "manifest.json").read_bytes())
    gecko = manifest["browser_specific_settings"]["gecko"]
    if (gecko.get("strict_min_version") != "158.0" or
            gecko.get("id") != "qikvrt-ai-terminal@goldkelch.local" or
            not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", manifest.get("version", ""))):
        raise ValueError("AMO_STANDARD_ID_AND_FIREFOX158_MINIMUM_REQUIRED")
    # The Standard sends explicit command text, source-page URL and optional
    # voice/camera payloads to the owner-local backend, outside the browser.
    # Declaring "none" would misrepresent that boundary even for loopback.
    consent = gecko.get("data_collection_permissions")
    if consent != {"required": ["personalCommunications", "browsingActivity", "personallyIdentifyingInfo"]}:
        raise ValueError("AMO_STANDARD_DATA_COLLECTION_DECLARATION_REQUIRED")
    raw = stream.getvalue()
    if len(raw) > 1024 * 1024: raise ValueError("AMO_BOUNDED_STANDARD_XPI_REQUIRED")
    return raw, {"repository": "ingolf-lohmann/qik-vrt", "source_head": head, "source_tree": tree,
        "extension_id": gecko["id"], "extension_version": manifest["version"],
        "strict_min_version": "158.0", "source_files": records, "unsigned_xpi_sha256": digest(raw)}


def firefox_amo_jwt(issuer, secret):
    def encode(value): return base64.urlsafe_b64encode(value).rstrip(b"=")
    now = int(time.time())
    header = encode(b'{"alg":"HS256","typ":"JWT"}')
    claims = encode(json.dumps({"iss": issuer, "jti": secrets.token_urlsafe(24),
        "iat": now, "exp": now + 60}, separators=(",", ":")).encode())
    message = header + b"." + claims
    return (message + b"." + encode(hmac.new(secret.encode(), message, hashlib.sha256).digest())).decode()


def firefox_amo_transport(url, method, payload, issuer, secret, download=False):
    """AMO-only JWT; HTTPS download redirects never receive Authorization."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs): return None
    opener = urllib.request.build_opener(NoRedirect)
    boundary = "qikvrt-amo-" + secrets.token_hex(16)
    headers = {"Accept": "application/json"}
    if method == "PUT":
        payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="channel"\r\n\r\nunlisted\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; filename="standard.xpi"\r\n'
            'Content-Type: application/x-xpinstall\r\n\r\n').encode() + payload + f'\r\n--{boundary}--\r\n'.encode()
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    for redirect in range(4):
        target = urlsplit(url)
        if (target.scheme != "https" or target.username or target.password or
                target.port not in (None, 443) or target.fragment or
                target.hostname not in {"addons.mozilla.org", "addons.cdn.mozilla.net"}):
            raise ValueError("AMO_OFFICIAL_HTTPS_ORIGIN_REQUIRED")
        if not download and (target.hostname != "addons.mozilla.org" or target.query or
                not target.path.startswith("/api/v4/addons/")):
            raise ValueError("AMO_FIXED_SIGNING_ENDPOINT_REQUIRED")
        if redirect == 0:
            if download and (target.hostname != "addons.mozilla.org" or target.query or
                    not re.match(r"^/api/v4/(?:downloads/file|file)/[0-9]+/", target.path)):
                raise ValueError("AMO_BOUND_FILE_ENDPOINT_REQUIRED")
            headers["Authorization"] = "JWT " + firefox_amo_jwt(issuer, secret)
        else:
            headers.pop("Authorization", None)
        request = urllib.request.Request(url, data=payload if method == "PUT" else None,
            headers=headers, method=method)
        try:
            response = opener.open(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, TimeoutError):
            # Provider error bodies, URLs and credential-bearing objects stay private.
            raise ValueError("AMO_TRANSPORT_OUTCOME_UNVERIFIED") from None
        with response:
            if download and response.code in (301, 302, 303, 307, 308):
                url = urllib.parse.urljoin(url, response.headers.get("Location", ""))
                if redirect == 3: raise ValueError("AMO_BOUNDED_DOWNLOAD_REDIRECT_REQUIRED")
                continue
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024: raise ValueError("AMO_RESPONSE_CAPACITY_LIMIT")
            return response.code, raw
    raise ValueError("AMO_DOWNLOAD_UNVERIFIED")


def firefox_amo_unlisted(root, output, head, tree, state_dir, submit=False, previous_state=None, readback_only=False):
    try:
        return firefox_amo_unlisted_apply(root, output, head, tree, state_dir, submit, previous_state, readback_only)
    except Exception as exc:
        cause = str(exc)
        code = cause.split(":", 1)[0]
        if code in {"FIREFOX_XPI_SOURCE_BYTES_MISMATCH", "FOREIGN_FIREFOX_XPI_PAYLOAD_FORBIDDEN",
                "EXACT_STANDARD_FIREFOX_XPI_INVENTORY_REQUIRED", "REGULAR_BOUNDED_FIREFOX_XPI_ENTRY_REQUIRED"}:
            cause = "AMO_" + code
        if not re.fullmatch(r"AMO_[A-Z0-9_]+", cause): cause = "AMO_EXTERNAL_OR_SOURCE_GATE_REFUSED"
        raise ValueError(cause) from None


def firefox_amo_unlisted_apply(root, output, head, tree, state_dir, submit=False, previous_state=None, readback_only=False):
    """One source-bound official signing submission, then independent readback.

    No credentials in arguments, journal, output, archive or logs. A pending or
    ambiguous upload is read back on resume, never submitted again unchanged.
    """
    if type(readback_only) is not bool: raise ValueError("AMO_READBACK_BOOLEAN_REQUIRED")
    raw, subject = firefox_amo_input(root, head, tree)
    for path in (output, state_dir):
        if path is None: raise ValueError("AMO_PRIVATE_OUTPUT_AND_JOURNAL_REQUIRED")
        path = Path(path)
        if not path.is_absolute() or Path(root).resolve() in path.resolve().parents:
            raise ValueError("AMO_OUTSIDE_REPOSITORY_PRIVATE_DIRECTORY_REQUIRED")
        path.mkdir(mode=0o700, exist_ok=True); private_path(path, directory=True)
    output, state_dir = Path(output), Path(state_dir)
    endpoint = "https://addons.mozilla.org/api/v4/addons/" + urllib.parse.quote(
        subject["extension_id"], safe="") + "/versions/" + urllib.parse.quote(subject["extension_version"], safe="") + "/"
    result = {"schema": "qikvrt-firefox-amo-unlisted/v1", **subject, "channel": "unlisted",
        "amo_endpoint": endpoint, "submission_attempted": False, "readback_only": readback_only, "mozilla_signature_verified": False,
        "extension_activation_verified": False, "main_integration_verified": False,
        "public_production_verified": False, "effect_ack_done": False}
    def finish(state):
        result["state"] = state
        destination = output / "AMO_SIGNING_RECEIPT.json"
        if destination.exists(): private_path(destination)
        temporary = output / (".amo-receipt-" + secrets.token_hex(16))
        synced_private_file(temporary, raw_json(result)); os.replace(temporary, destination)
        sync_directory(output)
        return result
    if not submit: return finish("HOLD_AMO_SUBMISSION_NOT_REQUESTED")
    issuer = os.environ.get("WEB_EXT_API_KEY", "")
    secret = os.environ.get("WEB_EXT_API_SECRET", "")
    if not issuer or not secret: return finish("HOLD_AMO_AUTHORIZED_CREDENTIAL_PAIR_UNAVAILABLE")
    if (not 1 <= len(issuer) <= 256 or not 16 <= len(secret) <= 512 or
            any(ord(c) < 33 or ord(c) > 126 for c in issuer + secret)):
        raise ValueError("AMO_BOUNDED_PRIVATE_CREDENTIAL_PAIR_REQUIRED")
    # Same-owner local lock and fsynced non-secret attempt metadata reuse the
    # existing private-state primitives. AMO GET is authoritative across runners.
    lock = state_dir / "amo-attempt.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(lock); fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = state_dir / "AMO_ATTEMPT.json"
        prior = None
        if previous_state:
            private_path(Path(previous_state))
            if Path(previous_state).stat().st_size > 65536: raise ValueError("AMO_BOUNDED_JOURNAL_REQUIRED")
            prior = json.loads(Path(previous_state).read_bytes())
        if journal.exists():
            private_path(journal)
            if journal.stat().st_size > 65536: raise ValueError("AMO_BOUNDED_JOURNAL_REQUIRED")
            prior = json.loads(journal.read_bytes())
        if prior and (prior.get("extension_id") != subject["extension_id"] or
                prior.get("extension_version") != subject["extension_version"]):
            raise ValueError("AMO_JOURNAL_SUBJECT_MISMATCH")
        status, data = firefox_amo_transport(endpoint, "GET", None, issuer, secret)
        if status == 404:
            if readback_only:
                return finish("HOLD_AMO_EXISTING_VERSION_NOT_OBSERVED_READBACK_ONLY")
            if prior and prior.get("submission_attempted"):
                return finish("HOLD_AMO_PRIOR_UPLOAD_OUTCOME_UNRESOLVED_NO_RESUBMISSION")
            result["submission_attempted"] = True
            # Persist before PUT. Timeout, interruption and 409 never cause retry.
            synced_private_file(journal, raw_json({**subject, "channel": "unlisted", "submission_attempted": True}))
            sync_directory(state_dir)
            status, data = firefox_amo_transport(endpoint, "PUT", raw, issuer, secret)
            if status not in (201, 202):
                result["amo_http_status"] = status
                return finish("HOLD_AMO_UPLOAD_NOT_CONFIRMED_NO_RETRY")
            result["upload_response_sha256"] = digest(data)
            status, data = firefox_amo_transport(endpoint, "GET", None, issuer, secret)
        if status != 200:
            result["amo_http_status"] = status
            return finish("HOLD_AMO_STATUS_READBACK_UNAVAILABLE")
        result["status_response_sha256"] = digest(data)
        value = json.loads(data)
        if value.get("guid") != subject["extension_id"] or value.get("version") != subject["extension_version"]:
            raise ValueError("AMO_RESPONSE_SUBJECT_MISMATCH")
        if value.get("processed") is True and value.get("valid") is False:
            return finish("HOLD_AMO_VALIDATION_REJECTED_NO_RESUBMISSION")
        if value.get("reviewed") is True and value.get("passed_review") is False:
            return finish("HOLD_AMO_REVIEW_REJECTED_NO_RESUBMISSION")
        files = value.get("files", [])
        if (value.get("processed") is not True or value.get("valid") is not True or
                value.get("reviewed") is not True or value.get("passed_review") is not True or
                len(files) != 1 or files[0].get("signed") is not True):
            return finish("PENDING_AMO_REVIEW_OR_SIGNING_READBACK_ONLY")
        item = files[0]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", item.get("hash", "")):
            raise ValueError("AMO_ORIGINAL_SHA256_REQUIRED")
        status, signed = firefox_amo_transport(item["download_url"], "GET", None, issuer, secret, download=True)
        if status != 200: return finish("HOLD_AMO_ORIGINAL_DOWNLOAD_UNAVAILABLE")
        if digest(signed) != item["hash"][7:]: raise ValueError("AMO_ORIGINAL_SHA256_MISMATCH")
        artifact = output / "standard-signed.xpi"
        if artifact.exists():
            private_path(artifact)
            if artifact.read_bytes() != signed: raise ValueError("AMO_EXISTING_ORIGINAL_BYTES_MISMATCH")
        else:
            synced_private_file(artifact, signed)
        try:
            checked = firefox_xpi_source_binding(artifact, Path(root) / "browser/firefox/qikvrt-terminal")
            if (len(checked["source_files"]) != 7 or not checked["signature_metadata_present"]):
                raise ValueError("AMO_SIX_STANDARD_COMPONENTS_AND_SIGNATURE_METADATA_REQUIRED")
        except BaseException:
            artifact.unlink(); raise
        result.update(xpi_sha256=digest(signed), xpi_bytes=len(signed), file_name=artifact.name,
            signed_original_returned=True, amo_api_signed_flag=True, source_component_binding=checked,
            retry_condition="READ_EXISTING_VERSION_ONLY; NO_REPEAT_UPLOAD")
        return finish("AMO_ORIGINAL_SIGNED_XPI_SOURCE_BOUND_PENDING_BROWSER_VERIFICATION")
    finally:
        os.close(descriptor)


def firefox_extension_accepted(value):
    """Require live Gecko acceptance and registration, not a copied XPI."""
    addon = value.get("addon") or {}
    return (value.get("minimum_satisfied") is True
        and addon.get("isCompatible") is True and addon.get("isActive") is True
        and addon.get("appDisabled") is False and addon.get("userDisabled") is False
        and addon.get("temporarilyInstalled") is False
        and value.get("temporary_installation_used") is False
        and value.get("policy_active") is True and value.get("background_registered") is True)


def firefox_production_extension_accepted(value):
    return (firefox_extension_accepted(value) and value.get("signatures_required") is True
        and value.get("mozilla_signed") is True)


class FirefoxProbeConnection:
    """Bounded loopback-only client for Firefox's existing Marionette protocol."""
    def __init__(self, connection):
        self.connection = connection
        self.sequence = 0
        if self.receive().get("marionetteProtocol") != 3:
            raise ValueError("FIREFOX_PROBE_PROTOCOL_REQUIRED")

    def exact(self, count):
        data = bytearray()
        while len(data) < count:
            part = self.connection.recv(count - len(data))
            if not part: raise ValueError("FIREFOX_PROBE_CONNECTION_CLOSED")
            data.extend(part)
        return bytes(data)

    def receive(self):
        length = bytearray()
        while True:
            byte = self.exact(1)
            if byte == b":": break
            if not byte.isdigit() or len(length) >= 8:
                raise ValueError("FIREFOX_PROBE_FRAME_REQUIRED")
            length.extend(byte)
        count = int(length)
        if not 0 < count <= 1024 * 1024: raise ValueError("FIREFOX_PROBE_FRAME_BOUND")
        return json.loads(self.exact(count))

    def call(self, method, params):
        self.sequence += 1
        raw = json.dumps([0, self.sequence, method, params]).encode()
        self.connection.sendall(str(len(raw)).encode() + b":" + raw)
        reply = self.receive()
        if len(reply) != 4 or reply[:2] != [1, self.sequence]:
            raise ValueError("FIREFOX_PROBE_RESPONSE_BINDING_REQUIRED")
        if reply[2] is not None: raise ValueError("FIREFOX_PROBE_COMMAND:" + json.dumps(reply[2]))
        return reply[3]


FIREFOX_EXTENSION_READBACK = """
const [id, minimum, done] = arguments;
(async () => {
  const {AddonManager} = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
  const {ExtensionParent} = ChromeUtils.importESModule("resource://gre/modules/ExtensionParent.sys.mjs");
  await AddonManager.readyPromise;
  const addon = await AddonManager.getAddonByID(id);
  const policy = WebExtensionPolicy.getByID(id);
  const extension = ExtensionParent.GlobalManager.getExtension(id);
  done({browser_version: Services.appinfo.version,
    minimum_satisfied: Services.vc.compare(Services.appinfo.version, minimum) >= 0,
    signatures_required: Services.prefs.getBoolPref("xpinstall.signatures.required", true),
    mozilla_signed: addon ? addon.signedState === AddonManager.SIGNEDSTATE_SIGNED : false,
    addon: addon ? {id: addon.id, version: addon.version, isActive: addon.isActive,
      isCompatible: addon.isCompatible, appDisabled: addon.appDisabled,
      userDisabled: addon.userDisabled, signedState: addon.signedState,
      temporarilyInstalled: addon.temporarilyInstalled} : null,
    policy_active: policy ? policy.active === true : false,
    background_registered: !!extension,
    temporary_installation_used: false});
})().catch(error => done({probe_error: String(error)}));
"""


FIREFOX_PERSISTENT_INSTALL = """
const [path, done] = arguments;
(async () => {
  const {AddonManager} = ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");
  await AddonManager.readyPromise;
  const file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);
  file.initWithPath(path);
  const install = await AddonManager.getInstallForFile(file);
  const status = event => ({event, state: install.state, error: install.error,
    temporary_installation_used: false, explicit_enable_used: false});
  if (install.state === AddonManager.STATE_DOWNLOAD_FAILED) {
    done(status("rejected_before_install")); return;
  }
  install.addListener({onInstallEnded: () => done(status("onInstallEnded")),
    onInstallFailed: () => done(status("onInstallFailed")),
    onDownloadFailed: () => done(status("onDownloadFailed")),
    onInstallCancelled: () => done(status("onInstallCancelled"))});
  Promise.resolve(install.install()).catch(error => done({...status("install_rejected"), error_text: String(error)}));
})().catch(error => done({event: "install_exception", error_text: String(error),
  temporary_installation_used: false, explicit_enable_used: false}));
"""


def firefox_extension_probe(xpi, output, package="firefox-esr"):
    """Persistent XPI installation in disposable profiles on the actual binary.

    No temporary install, compatibility override or AddonManager enable call.
    The second profile reproduces the existing explicit ESR reference exception.
    """
    import io
    import zipfile
    xpi, output = Path(xpi).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw = xpi.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    gecko = manifest["browser_specific_settings"]["gecko"]
    identity, minimum = gecko["id"], gecko["strict_min_version"]
    if identity != "qikvrt-ai-terminal@goldkelch.local" or minimum != "158.0":
        raise ValueError("OWNER_FIREFOX_158_EXACT_EXTENSION_REQUIRED")
    if package not in {"firefox-esr", "firefox"}: raise ValueError("DECLARED_FIREFOX_PACKAGE_REQUIRED")
    release = package == "firefox"
    binary = str(firefox_binary(package))
    result = {"schema": "qikvrt-firefox-extension-installation/v1",
        "scope": "EXACT_EXISTING_S1_IMAGE_AND_CANDIDATE_XPI_DISPOSABLE_PROFILES",
        "xpi_sha256": digest(raw), "xpi_bytes": len(raw), "extension_id": identity,
        "strict_min_version": minimum, "extension_version": manifest["version"],
        "firefox_package": package, "binary_path": str(Path(binary).resolve()),
        "installation_method": "AddonManager.getInstallForFile persistent" if release else "bootstrap profile XPI copy",
        "binary_sha256": digest(Path(binary).resolve().read_bytes()),
        "firefox_version_output": subprocess.check_output([binary, "--version"], stderr=subprocess.STDOUT,
            text=True, timeout=15).strip(),
        "debian_package_version": subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Version}", package], text=True, timeout=15).strip(),
        "existing_s1_bootstrap_xpi_present": Path(
            "/opt/qikvrt/runtime/bootstrap-profile/extensions/" + identity + ".xpi").is_file(),
        "profiles": {}, "effect_ack_done": False, "public_production_verified": False,
        "ordinary_release": False, "predecessor_acceptance_transferred": False}
    try:
        with tempfile.TemporaryDirectory(prefix="qikvrt-extension-probe-") as work:
            modes = (("default_signing_policy", False),) if release else (
                ("default_signing_policy", False), ("explicit_esr_reference", True))
            for mode, unsigned in modes:
                profile = Path(work) / mode
                (profile / "extensions").mkdir(parents=True)
                if not release: (profile / "extensions" / (identity + ".xpi")).write_bytes(raw)
                phases = []
                result["profiles"][mode] = phases
                for phase in ("initial_start", "process_restart"):
                    with socket.socket() as reservation:
                        reservation.bind(("127.0.0.1", 0)); port = reservation.getsockname()[1]
                    preferences = {"marionette.port": port, "browser.shell.checkDefaultBrowser": False,
                        "browser.startup.homepage": "about:blank", "browser.startup.page": 0,
                        "datareporting.policy.dataSubmissionEnabled": False,
                        "toolkit.telemetry.reportingpolicy.firstRun": False}
                    if unsigned: preferences["xpinstall.signatures.required"] = False
                    (profile / "user.js").write_text("".join(
                        "user_pref(" + json.dumps(k) + ", " + json.dumps(v) + ");\n"
                        for k, v in preferences.items()))
                    log = output / (mode + "-" + phase + ".log")
                    env = dict(os.environ, MOZ_REMOTE_ALLOW_SYSTEM_ACCESS="1")
                    with log.open("wb") as stream:
                        process = subprocess.Popen([binary, "--headless", "--no-remote", "--marionette",
                            "--profile", str(profile), "about:blank"], env=env, stdout=stream, stderr=stream)
                        connection = None
                        try:
                            until = time.monotonic() + 45
                            while time.monotonic() < until:
                                if process.poll() is not None: raise ValueError("FIREFOX_PROBE_BROWSER_EXITED")
                                try:
                                    connection = socket.create_connection(("127.0.0.1", port), timeout=1)
                                    break
                                except OSError: time.sleep(.1)
                            if connection is None: raise ValueError("FIREFOX_PROBE_START_TIMEOUT")
                            connection.settimeout(20)
                            client = FirefoxProbeConnection(connection)
                            session = client.call("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
                            client.call("Marionette:SetContext", {"value": "chrome"})
                            installation = None
                            if release and phase == "initial_start":
                                installation = client.call("WebDriver:ExecuteAsyncScript", {
                                    "script": FIREFOX_PERSISTENT_INSTALL, "args": [str(xpi)],
                                    "newSandbox": True, "sandbox": "system", "scriptTimeout": 15000})["value"]
                            observation = client.call("WebDriver:ExecuteAsyncScript", {
                                "script": FIREFOX_EXTENSION_READBACK, "args": [identity, minimum],
                                "newSandbox": True, "sandbox": "system", "scriptTimeout": 15000})["value"]
                            if observation.get("probe_error"): raise ValueError(observation["probe_error"])
                            installed_xpi = profile / "extensions" / (identity + ".xpi")
                            accepted = firefox_production_extension_accepted if release else firefox_extension_accepted
                            observation.update(phase=phase, accepted=accepted(observation),
                                persistent_installation=installation,
                                session_browser_version=session.get("capabilities", {}).get("browserVersion"),
                                **firefox_profile_xpi_state(installed_xpi))
                            phases.append(observation)
                            client.call("WebDriver:DeleteSession", {})
                        finally:
                            if connection: connection.close()
                            process.terminate()
                            try: process.wait(timeout=10)
                            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
                result[mode + "_activation_verified"] = all(p["accepted"] for p in phases)
        result["extension_activation_verified"] = result["default_signing_policy_activation_verified"]
        result["reference_activation_verified"] = result.get("explicit_esr_reference_activation_verified", False)
        result["signed_production_package_verified"] = release and result["extension_activation_verified"]
        observations = [p for phases in result["profiles"].values() for p in phases]
        result["state"] = ("HOLD_FIREFOX_BELOW_OWNER_MINIMUM" if
            any(p["minimum_satisfied"] is False for p in observations) else
            "EXTENSION_ACTIVATION_AND_RESTART_VERIFIED" if result["extension_activation_verified"]
            else "HOLD_EXTENSION_INSTALLATION_OR_ACTIVATION")
        return result
    except Exception as error:
        result.update(state="HOLD_EXTENSION_PROBE", probe_error=str(error),
            extension_activation_verified=False, reference_activation_verified=False)
        raise
    finally:
        (output / "extension-installation.json").write_bytes(raw_json(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("firefox-amo-unlisted", "firefox-release-provision", "firefox-extension-check", "deployment-roles", "runtime-delivery-verify", "runtime-delivery-load", "docker-admit", "pack", "portable", "portable-restore", "verify", "monolith-pack", "monolith-verify", "monolith-run", "monolith-checkpoint", "monolith-origin-export", "monolith-transport-export", "monolith-transport-import", "mesh-contract", "mesh-cache-stage", "mesh-cache-idle", "mesh-cache-send", "mesh-cache-check", "mesh-rule-confirm", "run", "admit", "supervisor", "run-admitted", "snapshot-state", "restore-state", "transfer-local-writer",
        "container-context", "container-carrier", "container-carrier-archive-check", "container-artifact-split", "container-artifact-join", "container-oci-check", "container-smoke", "container-production-gate", "container-deploy", "container-readback",
        "migration-inventory", "migration-verify-source", "migration-export", "migration-verify-export", "migration-import",
        "migration-verify-import", "migration-rollback", "migration-capture-supervisor", "migration-capture-arm", "migration-capture",
        "provider-inventory", "provider-classify", "provider-plan", "provider-apply", "provider-reconcile", "provider-readback"))
    parser.add_argument("--extension-xpi", type=Path, help="exact candidate XPI; disposable local probe only")
    parser.add_argument("--firefox-package", choices=("firefox-esr", "firefox"), default="firefox-esr")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-tree")
    parser.add_argument("--include-git-history", action="store_true", help="add a complete offline HEAD-ancestry bundle; refuse shallow/missing history")
    parser.add_argument("--amo-submit", action="store_true", help="explicitly authorized unlisted upload; secrets only from protected environment")
    parser.add_argument("--amo-state", type=Path, help="existing outside-repository owner-only non-secret attempt journal")
    parser.add_argument("--amo-previous-state", type=Path, help="original private attempt journal from the preceding native signing run")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--image-sha256", help="independently obtained canonical SQLite image pin")
    parser.add_argument("--transport-sha256", help="independently obtained derived QIKMESH1 export pin")
    parser.add_argument("--delivery", type=Path, help="existing verified runtime delivery directory")
    parser.add_argument("--delivery-sha256", help="independent DELIVERY.json pin")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--mesh-cache", type=Path, help="separate owner-only proposal object cache and durable outbox")
    parser.add_argument("--apply-rule", action="store_true", help="request only the peer's separately exact-granted native rule activation")
    parser.add_argument("--work-request", type=Path, help="private explicit exportable file/work-unit selection")
    parser.add_argument("--peer", type=Path, help="private peer URL, exact source pins and owner-only key path")
    parser.add_argument("--validation-command", nargs=argparse.REMAINDER, help="explicit finite command; run against the same exact local commit")
    parser.add_argument("--source-state-dir", type=Path, help="actual observable stopped original store; never a copied snapshot")
    parser.add_argument("--frontier-sha256", help="independent pin of all original ledger rows and epoch")
    parser.add_argument("--state-snapshot", type=Path, help="private exact-byte snapshot directory; never a public export")
    parser.add_argument("--state-manifest-sha256", help="independently obtained private state manifest pin")
    parser.add_argument("--admission", type=Path, help="private operator host declaration; no secrets")
    parser.add_argument("--admission-sha256", help="independently obtained host declaration pin")
    parser.add_argument("--admission-tool-sha256", help="independently reviewed guard pin; required for supervisor operations")
    parser.add_argument("--browser-assets-root", type=Path, help="explicit provisioned noVNC source tree; freeze a Firefox-capable variant")
    parser.add_argument("--image", help="local smoke tag or exact versioned production digest")
    parser.add_argument("--receipt", type=Path, help="non-secret container evidence output")
    parser.add_argument("--oci-archive", type=Path)
    parser.add_argument("--second-oci-archive", type=Path)
    parser.add_argument("--carrier-archive", type=Path, help="existing pinned GitHub delivery ZIP; otherwise download through original Actions REST")
    parser.add_argument("--carrier-oci-archive", type=Path, help="create-only OCI transport preserving the verified original ZIP for the existing publisher")
    parser.add_argument("--production-binding", type=Path, help="existing protected Linux host binding; never credentials")
    parser.add_argument("--binding-sha256", help="independently pinned protected host binding")
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--cert-file", type=Path)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--snapshot", type=Path, help="separately sealed offline volume copy; never a live Railway mount")
    parser.add_argument("--source-declaration", type=Path, help="private independently validated capture/layout declaration")
    parser.add_argument("--source-declaration-sha256", help="independent exact declaration pin")
    parser.add_argument("--bundle", type=Path, help="private verified migration export directory")
    parser.add_argument("--export-sha256", help="independent EXPORT.json pin")
    parser.add_argument("--import-sha256", help="independent private IMPORT.json pin")
    parser.add_argument("--live-volume", type=Path, help="privileged source volume; capture operations only")
    parser.add_argument("--source-root", type=Path, help="actual unchanged live Git checkout; not the sealed capture package")
    parser.add_argument("--capture-request", type=Path, help="owner-only independently pinned capture and acknowledgement cut")
    parser.add_argument("--capture-request-sha256", help="independent private capture request pin")
    parser.add_argument("--capture-output", type=Path, help="separate future snapshot destination for the unstarted supervisor adapter")
    parser.add_argument("--dry-run", action="store_true", help="verify export and proposed binding; create no target")
    parser.add_argument("--provider", choices=("digitalocean", "ionos", "hetzner"))
    parser.add_argument("--provider-binding", type=Path, help="private exact product and account/project/contract binding")
    parser.add_argument("--provider-binding-sha256")
    parser.add_argument("--provider-credential", type=Path, help="existing owner-only bearer token; never an argument value")
    parser.add_argument("--provider-inventory", type=Path, help="independently pinned private inventory; plans only")
    parser.add_argument("--provider-inventory-sha256")
    parser.add_argument("--provider-request", type=Path)
    parser.add_argument("--provider-request-sha256")
    parser.add_argument("--provider-public-key", type=Path, help="existing public SSH key; no generation or private-key reads")
    parser.add_argument("--provider-public-key-sha256")
    parser.add_argument("--provider-quote", type=Path, help="independently pinned IONOS Cloud contract quote")
    parser.add_argument("--provider-quote-sha256")
    parser.add_argument("--provider-authorization", type=Path, help="exact private create, payment and previously accepted terms evidence")
    parser.add_argument("--provider-authorization-sha256")
    parser.add_argument("--provider-receipts", type=Path, help="existing separate owner-only durable receipt directory")
    args = parser.parse_args()
    try:
        if args.operation == "firefox-amo-unlisted":
            result = firefox_amo_unlisted(args.root, args.output, args.expected_head, args.expected_tree,
                args.amo_state, args.amo_submit, args.amo_previous_state)
        elif args.operation == "firefox-release-provision":
            if args.output is None: raise ValueError("FIREFOX_RELEASE_PROVISION_RECEIPT_REQUIRED")
            result = firefox_release_provision(args.output)
        elif args.operation == "firefox-extension-check":
            if not args.extension_xpi or not args.output: raise ValueError("EXACT_XPI_AND_PROBE_OUTPUT_REQUIRED")
            result = firefox_extension_probe(args.extension_xpi, args.output, args.firefox_package)
        elif args.operation == "deployment-roles":
            result = deployment_roles(args.root)
        elif args.operation == "runtime-delivery-verify":
            result = delivery_verify(args.delivery, args.delivery_sha256)
        elif args.operation == "runtime-delivery-load":
            result = delivery_load(args.delivery, args.delivery_sha256)
        elif args.operation == "docker-admit":
            result = docker_plan(args.root, args.manifest_sha256, args.config, args.admission,
                                 args.admission_sha256, args.delivery, args.delivery_sha256)
        elif args.operation.startswith("container-"):
            import importlib
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            result = importlib.import_module("tools.qikvrt_self_host_container").execute(args)
        elif args.operation.startswith("provider-"):
            result = provider_module().execute(args)
        elif args.operation == "mesh-rule-confirm":
            if not args.mesh_cache or not args.work_request or not args.peer:
                raise ValueError("PEER_RULE_PRIVATE_REQUEST_AND_PEER_REQUIRED")
            private_path(args.work_request); private_path(args.peer)
            work = json.loads(args.work_request.read_bytes())
            cache = MeshWorkCache(args.mesh_cache, work["sender_repository"], work["sender_node_id"])
            result = cache.confirm_rule(json.loads(args.peer.read_bytes()), work, apply=args.apply_rule)
        elif args.operation.startswith("mesh-cache-"):
            if not args.mesh_cache or not args.work_request: raise ValueError("MESH_WORK_PRIVATE_REQUEST_REQUIRED")
            private_path(args.work_request)
            work = json.loads(args.work_request.read_bytes())
            if work.get("schema") != "qikvrt-repository-work-request/v1" or work.get("scope") != MESH_WORK_SCOPE:
                raise ValueError("MESH_WORK_EXPLICIT_EXPORTABLE_SCOPE_REQUIRED")
            cache = MeshWorkCache(args.mesh_cache, work["repository"], work["node_id"])
            if args.operation == "mesh-cache-stage":
                instructions = Path(work["instructions_file"])
                private_path(instructions)
                result = cache.stage(args.root, work["paths"], work["work_unit_id"], instructions.read_bytes())
            elif args.operation == "mesh-cache-idle": result = cache.idle(args.validation_command)
            else:
                if not args.peer: raise ValueError("MESH_WORK_PRIVATE_PEER_REQUIRED")
                private_path(args.peer)
                result = (cache.check if args.operation == "mesh-cache-check" else cache.send)(json.loads(args.peer.read_bytes()))
        elif args.operation.startswith("migration-"):
            result = migration_module().execute(args, verify, load_source, private_path)
        elif args.operation == "mesh-contract":
            result = mesh_contract(args.root)
        elif args.operation == "portable":
            if not args.output or not args.expected_head or not args.expected_tree:
                raise ValueError("EXACT_EXPORT_INPUTS_REQUIRED")
            result = portable(args.root.resolve(), args.output.absolute(), args.expected_head, args.expected_tree,
                              include_git_history=args.include_git_history)
        elif args.operation == "portable-restore":
            if not args.output or not args.expected_head or not args.expected_tree:
                raise ValueError("EXACT_EXPORT_INPUTS_REQUIRED")
            result = portable_restore(args.root.resolve(), args.manifest_sha256, args.image_sha256,
                                      args.output.absolute(), args.expected_head, args.expected_tree)
        elif args.operation == "pack":
            if not args.output or not args.expected_head or not args.expected_tree: raise ValueError("EXACT_EXPORT_INPUTS_REQUIRED")
            result = freeze(args.root, args.output, args.expected_head, args.expected_tree,
                args.browser_assets_root, args.firefox_package)
        elif args.operation == "verify":
            verify(args.root, args.manifest_sha256)
            result = {"state": "EXACT_PACKAGE_RUNTIME_VERIFIED", "effect_ack_done": False}
        elif args.operation == "monolith-pack":
            result = pack_monolith(args.root.resolve(), args.manifest_sha256, args.output)
        elif args.operation == "monolith-verify":
            with materialized_monolith(args.root.absolute(), args.manifest_sha256):
                result = {"state": "EXACT_MONOLITH_CARRIER_VERIFIED", "mobile_runtime_verified": False,
                          "effect_ack_done": False}
        elif args.operation == "monolith-run":
            return run_monolith(args.root.absolute(), args.manifest_sha256,
                                args.config.absolute() if args.config else None)
        elif args.operation == "monolith-checkpoint":
            result = checkpoint_monolith(args.root.absolute(), args.manifest_sha256,
                                         args.config.absolute() if args.config else None)
        elif args.operation == "monolith-origin-export":
            if args.output is None: raise ValueError('ORIGIN_BOOTSTRAP_OUTPUT_REQUIRED')
            result = checkpoint_monolith(args.root.absolute(), args.manifest_sha256,
                                         args.config.absolute() if args.config else None, args.output)
        elif args.operation == "monolith-transport-export":
            if args.output is None or args.config is None: raise ValueError("PRIVATE_TRANSPORT_EXPORT_INPUTS_REQUIRED")
            result = transport_export(args.root.absolute(), args.manifest_sha256, args.config.absolute(), args.output.absolute())
        elif args.operation == "monolith-transport-import":
            if args.output is None: raise ValueError("CREATE_ONLY_CANONICAL_IMPORT_OUTPUT_REQUIRED")
            result = transport_import(args.root.absolute(), args.manifest_sha256, args.image_sha256,
                                      args.transport_sha256, args.output.absolute())
        elif args.operation == "admit":
            result = admission_plan(args.root.resolve(), args.manifest_sha256, args.config,
                                    args.admission, args.admission_sha256)
        elif args.operation == "supervisor":
            if not args.output: raise ValueError("CREATE_ONLY_SUPERVISOR_OUTPUT_REQUIRED")
            plan = supervisor_plan(args.root.resolve(), args.manifest_sha256, args.config,
                                   args.admission, args.admission_sha256, args.admission_tool_sha256, args.delivery, args.delivery_sha256)
            result = materialize_supervisor(plan, args.output)
        elif args.operation == "run-admitted":
            run_admitted(args.root.resolve(), args.manifest_sha256, args.config,
                         args.admission, args.admission_sha256, args.admission_tool_sha256, args.delivery, args.delivery_sha256)
            raise ValueError("ORIGINAL_LAUNCHER_EXEC_REQUIRED")
        elif args.operation == "snapshot-state":
            result = snapshot_state(args.root.resolve(), args.manifest_sha256, args.config, args.output)
        elif args.operation == "transfer-local-writer":
            if not args.source_state_dir or not re.fullmatch(r"[a-f0-9]{64}", args.frontier_sha256 or ""):
                raise ValueError("ORIGINAL_LOCAL_STORE_AND_FRONTIER_PIN_REQUIRED")
            volume, binding = state_binding(args.root.resolve(), args.manifest_sha256, args.config)
            config_bytes = args.config.read_bytes()
            if digest(config_bytes) != binding['config_sha256']:
                raise ValueError("EXACT_CONFIGURATION_CHANGED")
            config = json.loads(config_bytes)
            private_path(args.source_state_dir, directory=True)
            load_source(args.root.resolve(), "qikvrt_effect_ack_http_terminal")
            native = load_source(args.root.resolve(), "qikvrt_temdd_event_ledger")
            exact = packaged_subject(args.root.resolve(), args.manifest_sha256,
                config["source_repository"], config["subject_pr"], config["source_head"], config["source_tree"])
            result = native.Ledger.transfer_local_writer(args.source_state_dir,
                volume, exact, args.frontier_sha256)
        elif args.operation == "restore-state":
            result = restore_state(args.root.resolve(), args.manifest_sha256, args.config,
                                   args.state_snapshot, args.state_manifest_sha256)
        else:
            if not args.config: raise ValueError("PRIVATE_START_CONFIGURATION_REQUIRED")
            return start(args.root.resolve(), args.manifest_sha256, args.config.absolute())
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as exc:
        # Capture diagnostics can contain private filenames or event data.
        cause = "CAPTURE_GATE_REFUSED" if args.operation.startswith("migration-capture") else str(exc)
        print(json.dumps({"state": "HOLD", "cause": cause, "effect_ack_done": False}, sort_keys=True))
        return 78 if args.operation == "run-admitted" else 2


if __name__ == "__main__":
    raise SystemExit(main())


