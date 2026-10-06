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
    "preserve_work_units_and_instruction_bytes", "hold_on_capacity_or_unknown_state")


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
                return status, json.loads(data)
            path = "/api/mesh-work/receipt/" + packet["batch_id"]
            known = None
            if self.state["pending"]["attempted"]:
                status, known = request("GET", path)
                if status == 404: known = None
                elif status != 200: raise ValueError("MESH_WORK_RECEIPT_UNAVAILABLE")
            if known is None:
                self.current()  # No new payload transfer from an invalidated idle.
                self.state["pending"]["attempted"] = True; self.save()
                status, _ = request("POST", "/api/mesh-work/batch", raw)
                if status != 200: raise ValueError("MESH_WORK_TRANSFER_REFUSED")
                status, known = request("GET", path)
                if status != 200: raise ValueError("MESH_WORK_RECEIPT_UNAVAILABLE")
            expected = {"schema": "qikvrt-repository-work-receipt/v1", **self.binding,
                "batch_id": packet["batch_id"], "revision": packet["revision"],
                "entries_sha256": packet["idle"]["entries_sha256"], "scope": MESH_WORK_SCOPE,
                "serving_node_id": peer["node_id"], "source_head": peer["source_head"], "source_tree": peer["source_tree"],
                "proposal_execution": "NOT_EXECUTED", "effect_ack_done": False}
            if not isinstance(known, dict) or any(known.get(k) != v for k, v in expected.items()):
                raise ValueError("MESH_WORK_RECEIPT_BINDING_MISMATCH")
            try:
                self.current()
                local_mode = "IDLE_STABLE_VALIDATED"
            except ValueError:
                # A known receipt resolves only this already-delivered batch.
                # New local work must be staged/validated afresh, never resent.
                local_mode = "DIRTY"
            self.state.update(last_ack=packet["batch_id"], pending=None, work_units=[],
                mode=local_mode, idle=self.state.get("idle") if local_mode == "IDLE_STABLE_VALIDATED" else None,
                acknowledged_objects=sorted(set(self.state["acknowledged_objects"]) | set(packet["objects"])))
            self.save()
            return {"state": "MESH_WORK_BATCH_READBACK_CONFIRMED", "batch_id": packet["batch_id"],
                    "local_idle_state": local_mode,
                    "proposal_execution": "NOT_EXECUTED", "whole_mesh_distribution_verified": False, "effect_ack_done": False}


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


def browser_executables():
    # Distribution-built tools use an exact executable binding, not a made-up
    # universal version. Actual package versions are retained by the image build.
    return {name: digest(Path(shutil.which(name) or name).resolve(strict=True).read_bytes())
            for name in BROWSER_COMMANDS}


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
    component_hashes = {}
    for name in sorted(required):
        path = root / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
            raise ValueError("MESH_REGULAR_SOURCE_COMPONENT_REQUIRED")
        component_hashes[name] = digest(path.read_bytes())
    return {"schema": "qikvrt-node-bus-contract-check/v1", "state": "SOURCE_OBLIGATIONS_BOUND",
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


def portable(root, output, head, tree):
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
                          manifest_sha256=pin, source_files=len(files), full_tree_verified=True)
            return result
    except BaseException:
        shutil.rmtree(output)
        raise


def freeze(root, output, head, tree, browser_assets=None):
    """Export committed bytes only. Tar metadata is deterministic; no credentials."""
    if git(root, "rev-parse", "HEAD").decode() != head or git(root, "rev-parse", "HEAD^{tree}").decode() != tree:
        raise ValueError("EXACT_SOURCE_BINDING_MISMATCH")
    git(root, "diff", "--quiet", head, "--")
    definition = json.loads(git(root, "show", head + ":" + DEFINITION))
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
        manifest["browser_runtime"] = {"executables": browser_executables(), "files": [],
            "asset_origin": "OPERATOR_PROVISIONED_DEBIAN_NOVNC_SOURCE; EXACT_EXPORTED_BYTES",
            "firefox_version": subprocess.check_output([shutil.which("firefox-esr"), "--version"],
                timeout=10, stderr=subprocess.DEVNULL).decode().strip()}
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


def verify(package, expected):
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
    if browser is not None and (not isinstance(browser, dict)
            or set(browser.get('executables', {})) != set(BROWSER_COMMANDS)
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
    if browser is not None and browser["executables"] != browser_executables():
        raise ValueError("BROWSER_EXECUTABLE_BINDING_MISMATCH")
    if value["runtime"] != {"node": runtime("node"), "python": runtime(sys.executable),
                            "platform": platform.machine(), "system": sys.platform}:
        raise ValueError("RUNTIME_EXECUTABLE_BINDING_MISMATCH")
    return value


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
def materialized_monolith(store, pin):
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
            verify(package, pin)
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


def inspect_stable_monolith(store, pin):
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
    with materialized_monolith(store, pin) as package:
        manifest = json.loads((package / "MANIFEST.json").read_bytes())
        load_source(package, "qikvrt_effect_ack_http_terminal")
        native = load_source(package, "qikvrt_temdd_event_ledger")
        with contextlib.closing(sqlite3.connect(store.as_uri() + "?mode=ro", uri=True)) as db:
            db.execute("PRAGMA trusted_schema=OFF")
            meta = dict(db.execute("SELECT key,value FROM meta"))
            if meta.get("schema") != "1" or not re.fullmatch(r"[a-f0-9]{32}", meta.get("epoch", "")):
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
        "runtime_readback_verified": False, "railway_cutover_verified": False, "effect_ack_done": False}


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


def admission_plan(package, pin, config_path=None, admission_path=None, admission_pin=None):
    """Bind the existing launcher to pinned host declarations; never deploy or assert acceptance.

    An independently obtained admission pin binds the operator's declaration.
    Local identity/mount comparisons do not validate the external authorization,
    storage guarantees, control-plane capability, HTTPS route or review governance.
    """
    manifest = verify(package, pin)
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


def supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin):
    """Materialize an existing systemd supervisor binding, never install a service."""
    tool = Path(__file__).resolve()
    if not re.fullmatch(r"[a-f0-9]{64}", tool_pin or "") or digest(tool.read_bytes()) != tool_pin:
        raise ValueError("ADMISSION_TOOL_PIN_MISMATCH")
    plan = admission_plan(package, pin, config_path, admission_path, admission_pin)
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


def run_admitted(package, pin, config_path, admission_path, admission_pin, tool_pin):
    # The reviewed guard can also launch an unchanged historical export. A
    # separate process executes that export's verifier before exec'ing its run.
    # exec preserves the systemd MainPID and cgroup; no second supervisor.
    plan = supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin)
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
    supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin)
    invocation = systemd_invocation(plan['unit_name'])
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

    runtime_instance = SealedRuntime()
    ingress = server = None
    try:
        original_handler = native.make_handler(runtime_instance)
        terminal = sys.modules["qikvrt_effect_ack_http_terminal"]
        grants = owner_rest_grants(config, token)
        rest = OwnerREST(runtime_instance, terminal, config["state_dir"])

        class OwnerHTTP(original_handler):
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
        spawn("xvfb", [shutil.which("Xvfb"), config["display"], "-screen", "0", "1440x900x24", "-nolisten", "tcp"])
        ready(lambda: subprocess.run([shutil.which("xdpyinfo"), "-display", config["display"]],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2).returncode == 0, 'X11_DISPLAY')
        spawn("vnc", [shutil.which("x11vnc"), "-display", config["display"], "-forever", "-shared", "-localhost",
            "-no6", "-rfbportv6", "0", "-rfbport", str(config["vnc_port"]), "-passwdfile", str(password)])
        spawn("novnc", [shutil.which("websockify"), "--web=" + str(package / "runtime/self-host/novnc"),
            "127.0.0.1:" + str(config["novnc_port"]), "127.0.0.1:" + str(config["vnc_port"])])
        spawn("firefox", [shutil.which("firefox-esr"), "--no-remote", "--profile", str(directory / "profile"),
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
    private_path(config_path)
    raw = config_path.read_bytes()
    config = json.loads(raw)
    fields = {"schema", "node_id", "source_head", "source_tree", "adapter", "state_dir", "host", "port", "terminal_port", "terminal_token_file", "github_webhook_secret_file", "terminal_profile", "subject_pr", "source_repository", "browser_password_file", "novnc_port", "vnc_port", "display", "migration_export_sha256", "mesh_work_peers", "owner_rest_grants", "unix_ingress", "mesh_file", "mesh_file_allowed_origins"}
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
            or profile == "reference" and (config.get("owner_rest_grants") or config.get("unix_ingress") is False)):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("pack", "portable", "verify", "monolith-pack", "monolith-verify", "monolith-run", "monolith-checkpoint", "monolith-origin-export", "monolith-transport-export", "monolith-transport-import", "mesh-contract", "mesh-cache-stage", "mesh-cache-idle", "mesh-cache-send", "run", "admit", "supervisor", "run-admitted", "snapshot-state", "restore-state",
        "migration-inventory", "migration-verify-source", "migration-export", "migration-verify-export", "migration-import",
        "migration-verify-import", "migration-rollback", "migration-capture-supervisor", "migration-capture-arm", "migration-capture",
        "provider-inventory", "provider-classify", "provider-plan", "provider-apply", "provider-reconcile", "provider-readback"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-tree")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--image-sha256", help="independently obtained canonical SQLite image pin")
    parser.add_argument("--transport-sha256", help="independently obtained derived QIKMESH1 export pin")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--mesh-cache", type=Path, help="separate owner-only proposal object cache and durable outbox")
    parser.add_argument("--work-request", type=Path, help="private explicit exportable file/work-unit selection")
    parser.add_argument("--peer", type=Path, help="private peer URL, exact source pins and owner-only key path")
    parser.add_argument("--validation-command", nargs=argparse.REMAINDER, help="explicit finite command; run against the same exact local commit")
    parser.add_argument("--state-snapshot", type=Path, help="private exact-byte snapshot directory; never a public export")
    parser.add_argument("--state-manifest-sha256", help="independently obtained private state manifest pin")
    parser.add_argument("--admission", type=Path, help="private operator host declaration; no secrets")
    parser.add_argument("--admission-sha256", help="independently obtained host declaration pin")
    parser.add_argument("--admission-tool-sha256", help="independently reviewed guard pin; required for supervisor operations")
    parser.add_argument("--browser-assets-root", type=Path, help="explicit provisioned noVNC source tree; freeze a Firefox-capable variant")
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
        if args.operation.startswith("provider-"):
            result = provider_module().execute(args)
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
                result = cache.send(json.loads(args.peer.read_bytes()))
        elif args.operation.startswith("migration-"):
            result = migration_module().execute(args, verify, load_source, private_path)
        elif args.operation == "mesh-contract":
            result = mesh_contract(args.root)
        elif args.operation == "portable":
            if not args.output or not args.expected_head or not args.expected_tree:
                raise ValueError("EXACT_EXPORT_INPUTS_REQUIRED")
            result = portable(args.root.resolve(), args.output.absolute(), args.expected_head, args.expected_tree)
        elif args.operation == "pack":
            if not args.output or not args.expected_head or not args.expected_tree: raise ValueError("EXACT_EXPORT_INPUTS_REQUIRED")
            result = freeze(args.root, args.output, args.expected_head, args.expected_tree, args.browser_assets_root)
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
                                   args.admission, args.admission_sha256, args.admission_tool_sha256)
            result = materialize_supervisor(plan, args.output)
        elif args.operation == "run-admitted":
            run_admitted(args.root.resolve(), args.manifest_sha256, args.config,
                         args.admission, args.admission_sha256, args.admission_tool_sha256)
            raise ValueError("ORIGINAL_LAUNCHER_EXEC_REQUIRED")
        elif args.operation == "snapshot-state":
            result = snapshot_state(args.root.resolve(), args.manifest_sha256, args.config, args.output)
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
