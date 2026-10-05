#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Offline storage operations of qikvrt_self_host; no provider or host executor.

All original payloads survive in legacy/railway. SQLite recovery/backup takes
place only in a disposable copy. No producer, socket, route or supervisor starts.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile

try:
    from . import qikvrt_self_host as storage
except ImportError:
    import qikvrt_self_host as storage

SOURCE_SCHEMA = "qikvrt-railway-offline-source/v1"
EXPORT_SCHEMA = "qikvrt-railway-state-export/v1"
IMPORT_SCHEMA = "qikvrt-railway-state-import/v1"
HOLD = ".MIGRATION_HOLD.json"
RECEIPT = "receipts/railway-migration/IMPORT.json"
VERIFIED = "receipts/railway-migration/VERIFIED.json"
SOURCE_CARRIER = {
    "provider": "railway", "project_id": "a2440de5-6250-4d02-8845-c166aeaa3d0d",
    "environment_id": "1286f33e-9f11-43d9-b86c-be5df57718a0",
    "service_id": "feb518e8-bfb2-450d-a36a-c992b052427c",
    "volume_id": "0e2d37e2-ac58-4bdc-8238-ed81bf2aa187",
    "volume_name": "qikvrt-state", "mount_path": "/var/lib/qikvrt",
    "domain": "universal-terminal-production.up.railway.app",
}


def raw(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def pin(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("INDEPENDENT_SHA256_PIN_REQUIRED")
    return value


def decode(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result: raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = item
        return result
    def finite(_): raise ValueError("NONFINITE_JSON_VALUE")
    return json.loads(value, object_pairs_hook=pairs, parse_constant=finite)


def relative(name):
    if (not isinstance(name, str) or not name or "\\" in name
            or any(c in name for c in "\x00\r\n") or name.startswith("/")
            or any(p in {"", ".", ".."} for p in name.split("/"))
            or PurePosixPath(name).as_posix() != name):
        raise ValueError("UNSAFE_MIGRATION_PATH")
    return name


def confined(path, exists=True):
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("ABSOLUTE_MIGRATION_PATH_REQUIRED")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("MIGRATION_SYMLINK_FORBIDDEN")
    if exists and not path.exists(): raise ValueError("MIGRATION_PATH_MISSING")


def disjoint(*paths):
    for path in paths: confined(path, exists=False)
    for i, a in enumerate(paths):
        for b in paths[i + 1:]:
            if a == b or a in b.parents or b in a.parents:
                raise ValueError("MIGRATION_PATHS_MUST_BE_DISJOINT")


def read(path):
    confined(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("SINGLE_LINK_REGULAR_MIGRATION_FILE_REQUIRED")
        if info.st_size > 512 * 1024 * 1024: raise ValueError("MIGRATION_FILE_SIZE_LIMIT")
        data = source.read()
        after = os.fstat(source.fileno())
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(info, k) != getattr(after, k) for k in fields):
            raise ValueError("MIGRATION_FILE_CHANGED_DURING_READ")
        return data


def inventory(root):
    """No writes, sockets, symlinks, hardlinks or silently skipped private files."""
    confined(root)
    if not root.is_dir(): raise ValueError("MIGRATION_DIRECTORY_REQUIRED")
    result = {}
    for parent, directories, files in os.walk(root, followlinks=False):
        confined(Path(parent))
        for name in sorted(directories + files):
            path = Path(parent) / name
            key = relative(path.relative_to(root).as_posix())
            info = path.lstat()
            entry = {"mode": stat.S_IMODE(info.st_mode)}
            if stat.S_ISDIR(info.st_mode): entry["kind"] = "directory"
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1: raise ValueError("SINGLE_LINK_REGULAR_MIGRATION_FILE_REQUIRED")
                if info.st_size > 512 * 1024 * 1024: raise ValueError("MIGRATION_FILE_SIZE_LIMIT")
                entry.update(kind="file", **storage.state_file_digest(path))
            else:
                raise ValueError("UNSUPPORTED_MIGRATION_ENTRY:" + key)
            if info.st_uid != os.geteuid() or entry["mode"] & 0o7000:
                raise ValueError("MIGRATION_OWNER_OR_SPECIAL_MODE_MISMATCH")
            result[key] = entry
            if len(result) > 100000: raise ValueError("MIGRATION_INVENTORY_LIMIT")
    if sum(e.get("bytes", 0) for e in result.values()) > 4 * 1024**3:
        raise ValueError("MIGRATION_TOTAL_SIZE_LIMIT")
    return dict(sorted(result.items()))


def fresh(path):
    confined(path, exists=False)
    confined(path.parent)
    path.mkdir(mode=0o700, exist_ok=False)
    sync(path.parent)


def directories(path):
    """Path.mkdir(parents=True) does not apply 0700 to intermediate parents."""
    confined(path, exists=False)
    missing = []
    current = path
    while not current.exists():
        missing.append(current); current = current.parent
    if not current.is_dir(): raise ValueError("MIGRATION_DIRECTORY_REQUIRED")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=False)
        sync(directory.parent)


def write(path, data):
    confined(path, exists=False)
    directories(path.parent)
    confined(path.parent)
    storage.synced_private_file(path, data)
    sync(path.parent)


def sync(path):
    confined(path)
    storage.sync_directory(path)


def copy_tree(source, dest, entries):
    for name, entry in entries.items():
        path = dest / relative(name)
        if entry["kind"] == "directory": directories(path)
        else:
            directories(path.parent)
            if storage.state_file_digest(source / name, path) != {"bytes": entry["bytes"], "sha256": entry["sha256"]}:
                raise ValueError("SOURCE_CHANGED_DURING_COPY:" + name)
            sync(path.parent)
    for directory in sorted((p for p in dest.rglob("*") if p.is_dir()), reverse=True): sync(directory)
    sync(dest)


def same_bytes(root, entries):
    actual = inventory(root)
    if set(actual) != set(entries): raise ValueError("MIGRATION_FILESET_MISMATCH")
    for name, entry in entries.items():
        got = actual[name]
        # Original modes are retained as evidence; transported files are private.
        if got != dict(entry, mode=0o700 if entry["kind"] == "directory" else 0o600):
            raise ValueError("MIGRATION_ARTIFACT_MISMATCH:" + name)


def source_declaration(path, expected, entries):
    data = read(path)
    if sha(data) != pin(expected): raise ValueError("SOURCE_DECLARATION_PIN_MISMATCH")
    value = decode(data)
    fields = {"schema", "carrier", "source_repository", "source_head", "source_tree",
              "snapshot_id", "capture_evidence_sha256", "consistency", "inventory_sha256", "layout"}
    if (set(value) != fields or value["schema"] != SOURCE_SCHEMA
            or value["carrier"] != SOURCE_CARRIER
            or value["source_repository"] != "Goldkelch/qik-vrt"
            or any(not re.fullmatch(r"[a-f0-9]{40}", value[k] or "") for k in ("source_head", "source_tree"))
            or value["consistency"] != "QUIESCED_OFFLINE_SNAPSHOT"
            or not isinstance(value["snapshot_id"], str) or not value["snapshot_id"].strip()
            or value["inventory_sha256"] != sha(raw(entries))):
        raise ValueError("UNVERIFIED_OR_CHANGED_OFFLINE_SNAPSHOT")
    pin(value["capture_evidence_sha256"])
    layout = value["layout"]
    if not isinstance(layout, dict) or set(layout) != {"ledger", "monitor", "binding", "locks", "jsonl"}:
        raise ValueError("EXPLICIT_SOURCE_LAYOUT_REQUIRED")
    for key in ("ledger", "monitor", "binding"):
        if layout[key] is not None:
            name = relative(layout[key])
            if entries.get(name, {}).get("kind") != "file": raise ValueError("SOURCE_ROLE_FILE_MISSING:" + key)
    candidates = {
        "ledger": {n for n in entries if PurePosixPath(n).name == "events.sqlite3"},
        "monitor": {n for n in entries if n == "monitor/node.json" or n.endswith("/monitor/node.json")},
        "binding": {n for n in entries if n == "binding.json" or n == "state/binding.json"},
    }
    for key, found in candidates.items():
        if found and found != {layout[key]}: raise ValueError("UNDECLARED_OR_AMBIGUOUS_SOURCE_ROLE:" + key)
    if layout["ledger"] is None: raise ValueError("NATIVE_LEDGER_SOURCE_REQUIRED")
    for key in ("locks", "jsonl"):
        if not isinstance(layout[key], list) or len(layout[key]) != len(set(layout[key])):
            raise ValueError("EXPLICIT_SOURCE_LAYOUT_REQUIRED")
        for name in layout[key]:
            relative(name)
            if entries.get(name, {}).get("kind") != "file": raise ValueError("SOURCE_ROLE_FILE_MISSING:" + key)
    if {n for n in entries if n.endswith(".jsonl")} != set(layout["jsonl"]):
        raise ValueError("COMPLETE_JSONL_JOURNAL_LAYOUT_REQUIRED")
    # Declared locks must be actual kernel lock files, not arbitrary artifacts.
    required = {str(PurePosixPath(layout["ledger"]).parent / "owner.lock")}
    if layout["binding"] is not None: required.add(str(PurePosixPath(layout["binding"]).parent / "node.lock"))
    if not required <= set(layout["locks"]): raise ValueError("SOURCE_WRITER_LOCK_BINDING_REQUIRED")
    return value, data


@contextlib.contextmanager
def locked(root, names):
    with contextlib.ExitStack() as stack:
        for name in names:
            fd = os.open(root / relative(name), os.O_RDONLY | os.O_NOFOLLOW)
            stack.callback(os.close, fd)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def wal_check(data, page_size):
    """Strict complete committed WAL, per sqlite.org/fileformat2.html#walformat.

    SQLite may ignore invalid/stale suffixes. This transfer instead refuses
    them; a separately sealed clean snapshot is required, never source repair.
    """
    if not data: return {"frames": 0, "commits": 0}
    if len(data) < 32: raise ValueError("TRUNCATED_SQLITE_WAL")
    magic, version, pages, _, s1, s2, c1, c2 = struct.unpack(">8I", data[:32])
    if (magic not in {0x377f0682, 0x377f0683} or version != 3007000 or pages != page_size
            or (len(data) - 32) % (24 + pages)):
        raise ValueError("INVALID_SQLITE_WAL_HEADER_OR_LENGTH")
    endian = "<" if magic == 0x377f0682 else ">"
    def checksum(chunk, state):
        x = struct.unpack(endian + str(len(chunk) // 4) + "I", chunk)
        a, b = state
        for i in range(0, len(x), 2):
            a = (a + x[i] + b) & 0xffffffff
            b = (b + x[i + 1] + a) & 0xffffffff
        return a, b
    state = checksum(data[:24], (0, 0))
    if state != (c1, c2): raise ValueError("SQLITE_WAL_HEADER_CHECKSUM_MISMATCH")
    frames = commits = last_commit = 0
    for offset in range(32, len(data), 24 + pages):
        header = data[offset:offset + 24]
        pg, committed, a, b, c, d = struct.unpack(">6I", header)
        state = checksum(header[:8] + data[offset + 24:offset + 24 + pages], state)
        if not pg or (a, b) != (s1, s2) or state != (c, d):
            raise ValueError("SQLITE_WAL_FRAME_CHECKSUM_OR_SALT_MISMATCH")
        frames += 1
        if committed: commits += 1; last_commit = frames
    if frames != last_commit: raise ValueError("UNCOMMITTED_SQLITE_WAL_SUFFIX")
    return {"frames": frames, "commits": commits}


def inspect_sqlite(root, name, native, normalized=None):
    image = read(root / name)
    if not image.startswith(b"SQLite format 3\0") or len(image) < 100:
        raise ValueError("SQLITE_IMAGE_REQUIRED:" + name)
    page_size = int.from_bytes(image[16:18], "big") or 65536
    if page_size == 1: page_size = 65536
    if page_size not in {2**n for n in range(9, 17)} or len(image) % page_size:
        raise ValueError("INVALID_SQLITE_PAGE_SIZE_OR_LENGTH")
    wal = read(root / (name + "-wal")) if (root / (name + "-wal")).exists() else b""
    frames = wal_check(wal, page_size)
    journal = root / (name + "-journal")
    if journal.exists() and any(read(journal)):
        raise ValueError("SQLITE_ROLLBACK_JOURNAL_REQUIRES_SEALED_RECOVERY")
    with tempfile.TemporaryDirectory(prefix="qikvrt-sqlite-inspect-") as scratch:
        dbpath = Path(scratch) / "image.sqlite3"
        dbpath.write_bytes(image)
        if wal: Path(str(dbpath) + "-wal").write_bytes(wal)
        # Never trust/copy the shared memory index into recovery; original bytes
        # still survive in the payload. SQLite rebuilds it only in this copy.
        with contextlib.closing(sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("SQLITE_INTEGRITY_CHECK_FAILED:" + name)
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("SQLITE_FOREIGN_KEY_CHECK_FAILED:" + name)
            logical = sha("\n".join(db.iterdump()).encode())
            result = {"logical_sha256": logical, "wal": frames, "integrity": "ok"}
            if native is not None:
                objects = db.execute("SELECT type,name FROM sqlite_master").fetchall()
                if (set(objects) != {("table", "meta"), ("index", "sqlite_autoindex_meta_1"),
                        ("table", "events"), ("table", "sqlite_sequence"),
                        ("index", "sqlite_autoindex_events_1"), ("index", "events_binding")}
                        or [r[1] for r in db.execute("PRAGMA table_info(events)")] !=
                        ["seq", "binding", "source", "native_id", "native_digest", "body", "body_digest"]):
                    raise ValueError("UNKNOWN_OR_EXECUTABLE_NATIVE_LEDGER_SCHEMA")
                meta = dict(db.execute("SELECT key,value FROM meta"))
                if set(meta) != {"schema", "epoch"} or meta["schema"] != "1" or not re.fullmatch(r"[a-f0-9]{32}", meta["epoch"]):
                    raise ValueError("UNKNOWN_NATIVE_LEDGER_META")
                count = 0
                subjects = {}
                for seq, binding, source, identity, ndigest, body, bdigest in db.execute("SELECT * FROM events ORDER BY seq"):
                    event = decode(body)
                    subject = event.get("subject", {})
                    original = {k: event[k] for k in ("kind", "subject", "provenance", "observed_at", "message", "payload")}
                    original["schema"] = native.SCHEMA
                    kernel = object.__new__(native.Ledger); kernel.subject = subject
                    kernel._validate(original)  # Original semantic validator, no new store.
                    if (type(seq) is not int or seq < 1 or binding != native.digest(subject)
                            or not re.fullmatch(r"[a-f0-9]{40}", subject.get("head", ""))
                            or not re.fullmatch(r"[a-f0-9]{40}", subject.get("tree", ""))
                            or body != native.canonical(event).decode() or bdigest != native.digest(event)
                            or ndigest != native.digest(original) or event.get("schema") != "qikvrt_temdd_event_v1"
                            or event.get("payload_digest") != native.digest(event["payload"])
                            or event.get("evidence_transfer") != "DENY" or event.get("dod") is not False
                            or source != original["provenance"]["source"] or identity != original["provenance"]["native_event_id"]):
                        raise ValueError("NATIVE_EVENT_DIGEST_OR_SUBJECT_MISMATCH")
                    subjects[binding] = subject; count += 1
                result.update(epoch=meta["epoch"], events=count, subjects=subjects)
            if normalized is not None:
                with contextlib.closing(sqlite3.connect(normalized)) as target:
                    db.backup(target)
                    target.execute("PRAGMA journal_mode=DELETE")
                normalized.chmod(0o600)
                with normalized.open("rb") as output: os.fsync(output.fileno())
    return result


def monitor_check(package, path):
    program = """import {readFileSync} from 'node:fs';
const {MonitorStore} = await import(process.argv[1]);
const path=process.argv[2];const value=JSON.parse(readFileSync(path));
const store=new MonitorStore(path,value.node_id);
if (typeof value.node_id !== 'string' || !value.node_id || !value.epoch || value.sequence<value.deliveries.length)
 throw Error('MONITOR_IDENTITY_OR_SEQUENCE_MISMATCH');
const last=value.deliveries.at(-1);
const expected=last ? Object.fromEntries(['id','event','repository','event_sequence','payload_sha256','record_digest','observed_at'].map(k=>[k,last[k]])) : null;
if (JSON.stringify(value.last_delivery)!==JSON.stringify(expected)) throw Error('MONITOR_LAST_DELIVERY_MISMATCH');
if (!value.snapshot && (value.digest!==null || value.sequence!==0 || value.deliveries.length)) throw Error('MONITOR_EMPTY_CHECKPOINT_MISMATCH');
if (value.journal_source_node_id || value.required_replica_node_id) throw Error('MONITOR_REPLICA_REQUIRES_SEPARATE_ADMISSION');
console.log(JSON.stringify({node_id:value.node_id,epoch:value.epoch,sequence:value.sequence,
event_sequence:value.deliveries.length,journal_head_digest:store.checkpoint().journal_head_digest}));"""
    outcome = subprocess.run([shutil.which("node"), "--input-type=module", "-e", program,
        (package / "docs/monitor/server.mjs").as_uri(), str(path)], timeout=30, capture_output=True,
        env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8"})
    if outcome.returncode: raise ValueError("MONITOR_JOURNAL_CONSISTENCY_FAILED")
    return decode(outcome.stdout)


def native_source(package, load_source):
    load_source(package, "qikvrt_effect_ack_http_terminal")
    return load_source(package, "qikvrt_temdd_event_ledger")


def consistency(package, root, declaration, entries, load_source):
    layout = declaration["layout"]
    native = native_source(package, load_source)
    databases = {}
    for name, entry in entries.items():
        if entry["kind"] != "file": continue
        data = read(root / name)
        if data.startswith(b"SQLite format 3\0") or name.endswith((".sqlite", ".sqlite3", ".db")):
            databases[name] = inspect_sqlite(root, name, native if name == layout["ledger"] else None)
        if name.endswith(("-wal", "-shm", "-journal")):
            base = name.rsplit("-", 1)[0]
            if entries.get(base, {}).get("kind") != "file": raise ValueError("ORPHAN_SQLITE_SIDECAR")
    if layout["ledger"] not in databases: raise ValueError("NATIVE_LEDGER_NOT_INSPECTED")
    journals = {}
    for name in layout["jsonl"]:
        data = read(root / name)
        if data and not data.endswith(b"\n"): raise ValueError("TRUNCATED_JSONL_JOURNAL")
        lines = data.splitlines()
        for line in lines:
            if not isinstance(decode(line), dict): raise ValueError("JSONL_OBJECT_REQUIRED")
        journals[name] = {"records": len(lines), "ordered_bytes_sha256": sha(data),
                          "scope": "EXACT_BYTES_AND_JSONL_FRAMING; NO_UNDECLARED_CHAIN_SCHEMA_INFERRED"}
    monitor = monitor_check(package, root / layout["monitor"]) if layout["monitor"] else None
    binding = decode(read(root / layout["binding"])) if layout["binding"] else None
    if binding is not None:
        if (binding.get("schema") != "qikvrt-self-host-volume/v1"
                or any(binding.get(k) != declaration[k] for k in ("source_head", "source_tree"))):
            raise ValueError("SOURCE_VOLUME_BINDING_MISMATCH")
        pin(binding.get("manifest_sha256")); pin(binding.get("config_sha256"))
        if monitor and monitor["node_id"] != binding.get("node_id"):
            raise ValueError("SOURCE_MONITOR_NODE_BINDING_MISMATCH")
    return {"sqlite": databases, "monitor": monitor, "binding": binding, "jsonl": journals}


def independent(args, operation, output=None):
    """Separate exact tool/runtime process, same offline input pins; no receipt trust."""
    command = [str(Path(sys.executable).resolve()), "-B", str(Path(__file__).with_name("qikvrt_self_host.py")),
               operation, "--root", str(args.root), "--manifest-sha256", args.manifest_sha256]
    for flag, attr in (("--snapshot", "snapshot"), ("--source-declaration", "source_declaration"),
                       ("--source-declaration-sha256", "source_declaration_sha256"),
                       ("--bundle", "bundle"), ("--export-sha256", "export_sha256"),
                       ("--config", "config"), ("--import-sha256", "import_sha256")):
        value = getattr(args, attr, None)
        if value is not None: command += [flag, str(value)]
    if output is not None: command += ["--output", str(output)]
    completed = subprocess.run(command, timeout=120, capture_output=True,
        env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
    if completed.returncode:
        value = decode(completed.stdout) if completed.stdout else {}
        raise ValueError("INDEPENDENT_MIGRATION_VERIFICATION_FAILED:" + value.get("cause", "PROCESS_FAILURE"))
    return decode(completed.stdout)


def verify_export(args, load_source):
    data = read(args.bundle / "EXPORT.json")
    if sha(data) != pin(args.export_sha256): raise ValueError("EXPORT_MANIFEST_PIN_MISMATCH")
    export = decode(data)
    if (set(export) != {"schema", "source_declaration_sha256", "entries", "consistency", "verifier_sha256", "effect_ack_done"}
            or export.get("schema") != EXPORT_SCHEMA or export.get("effect_ack_done") is not False
            or export.get("verifier_sha256") != sha(Path(__file__).read_bytes())):
        raise ValueError("EXPORT_SCHEMA_OR_VERIFIER_MISMATCH")
    source_data = read(args.bundle / "SOURCE.json")
    if sha(source_data) != export["source_declaration_sha256"]: raise ValueError("SOURCE_DECLARATION_PIN_MISMATCH")
    declaration, _ = source_declaration(args.bundle / "SOURCE.json", export["source_declaration_sha256"], export["entries"])
    if set(p.name for p in args.bundle.iterdir()) != {"EXPORT.json", "SOURCE.json", "payload"}:
        raise ValueError("EXPORT_BUNDLE_INVENTORY_MISMATCH")
    same_bytes(args.bundle / "payload", export["entries"])
    observed = consistency(args.root, args.bundle / "payload", declaration, export["entries"], load_source)
    if observed != export["consistency"]: raise ValueError("EXPORT_CONSISTENCY_READBACK_MISMATCH")
    same_bytes(args.bundle / "payload", export["entries"])
    if read(args.bundle / "EXPORT.json") != data or read(args.bundle / "SOURCE.json") != source_data:
        raise ValueError("EXPORT_CHANGED_DURING_VERIFICATION")
    return export, declaration


def target_binding(args, manifest, declaration, observed, private_path):
    private_path(args.config)
    config_data = read(args.config); config = decode(config_data)
    fields = {"schema", "node_id", "source_head", "source_tree", "adapter", "state_dir", "host", "port",
              "terminal_port", "terminal_token_file", "terminal_profile", "subject_pr", "source_repository",
              "browser_password_file", "novnc_port", "vnc_port", "display", "github_webhook_secret_file", "migration_export_sha256"}
    if (set(config) - fields or config.get("schema") != "qikvrt-self-host-config/v1" or config.get("adapter") != "none"
            or config.get("terminal_profile") not in {"temdd", "firefox"}
            or config.get("host") not in {"127.0.0.1", "0.0.0.0"}
            or any(type(config.get(k)) is not int or not 1 <= config[k] <= 65535 for k in ("port", "terminal_port"))
            or config["port"] == config["terminal_port"] or config.get("github_webhook_secret_file")
            or not isinstance(config.get("terminal_token_file"), str) or not Path(config["terminal_token_file"]).is_absolute()
            or config.get("source_repository") != manifest["source_repository"]
            or any(config.get(k) != manifest[k] for k in ("source_head", "source_tree"))
            or config.get("state_dir") != str(args.output)
            or config.get("migration_export_sha256") != args.export_sha256
            or type(config.get("subject_pr")) is not int or config["subject_pr"] < 1
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", config.get("node_id", ""))
            or "CHANGE_ME" in config["node_id"]):
        raise ValueError("MIGRATION_TARGET_CONFIGURATION_MISMATCH")
    for record in (observed["monitor"], observed["binding"]):
        if record is not None and record["node_id"] != config["node_id"]:
            raise ValueError("MIGRATION_NODE_ID_CHANGE_FORBIDDEN")
    if config["terminal_profile"] == "firefox":
        if ("browser_runtime" not in manifest or not re.fullmatch(r":[1-9][0-9]{0,3}", config.get("display", ""))
                or any(type(config.get(k)) is not int or not 1 <= config[k] <= 65535 for k in ("novnc_port", "vnc_port"))
                or len({config[k] for k in ("port", "terminal_port", "novnc_port", "vnc_port")}) != 4
                or not isinstance(config.get("browser_password_file"), str) or not Path(config["browser_password_file"]).is_absolute()):
            raise ValueError("EXACT_BROWSER_CONFIGURATION_REQUIRED")
    return {"schema": "qikvrt-self-host-volume/v1", "node_id": config["node_id"],
            "manifest_sha256": args.manifest_sha256, "config_sha256": sha(config_data),
            "source_head": manifest["source_head"], "source_tree": manifest["source_tree"]}


def target_inventory(root):
    return {k: v for k, v in inventory(root).items() if k not in {HOLD, RECEIPT, VERIFIED}}


def completion(import_pin, export_pin, binding):
    return raw({"schema": "qikvrt-railway-import-verified/v1", "import_sha256": import_pin,
                "export_sha256": export_pin, "binding": binding, "effect_ack_done": False})


def start_receipt(volume, export_pin, binding, private_path):
    """No implicit fresh state after an interrupted/failed planned migration."""
    try:
        pin(export_pin)
        private_path(volume / RECEIPT); private_path(volume / VERIFIED)
        data = read(volume / RECEIPT); receipt = decode(data)
        if (receipt.get("schema") != IMPORT_SCHEMA or receipt.get("effect_ack_done") is not False
                or receipt.get("binding") != binding or receipt.get("export_sha256") != export_pin
                or receipt.get("target") != str(volume)
                or read(volume / VERIFIED) != completion(sha(data), export_pin, binding)):
            raise ValueError("MIGRATION_VERIFIED_IMPORT_REQUIRED")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("MIGRATION_VERIFIED_IMPORT_REQUIRED") from exc


def verify_import(args, manifest, load_source, private_path):
    export, declaration = verify_export(args, load_source)
    private_path(args.output / RECEIPT)
    data = read(args.output / RECEIPT)
    if sha(data) != pin(args.import_sha256): raise ValueError("IMPORT_MANIFEST_PIN_MISMATCH")
    receipt = decode(data)
    if (receipt.get("schema") != IMPORT_SCHEMA or receipt.get("effect_ack_done") is not False
            or receipt.get("export_sha256") != args.export_sha256
            or receipt.get("target") != str(args.output)
            or receipt.get("binding") != target_binding(args, manifest, declaration, export["consistency"], private_path)):
        raise ValueError("IMPORT_SUBJECT_BINDING_MISMATCH")
    if target_inventory(args.output) != receipt["entries"]: raise ValueError("IMPORT_FILESET_OR_DIGEST_MISMATCH")
    same_bytes(args.output / "legacy/railway", export["entries"])
    if decode(read(args.output / "binding.json")) != receipt["binding"]:
        raise ValueError("IMPORT_VOLUME_BINDING_MISMATCH")
    native = native_source(args.root, load_source)
    active = inspect_sqlite(args.output, "temdd/events.sqlite3", native)
    before = export["consistency"]["sqlite"][declaration["layout"]["ledger"]]
    if {k: v for k, v in active.items() if k != "wal"} != {k: v for k, v in before.items() if k != "wal"}:
        raise ValueError("IMPORTED_NATIVE_LEDGER_NOT_LOSSLESS")
    if declaration["layout"]["monitor"]:
        if read(args.output / "monitor/node.json") != read(args.bundle / "payload" / declaration["layout"]["monitor"]):
            raise ValueError("IMPORTED_MONITOR_BYTES_CHANGED")
        if monitor_check(args.root, args.output / "monitor/node.json") != export["consistency"]["monitor"]:
            raise ValueError("IMPORTED_MONITOR_CHECKPOINT_CHANGED")
    if (args.output / VERIFIED).exists():
        start_receipt(args.output, args.export_sha256, receipt["binding"], private_path)
    elif not (args.output / HOLD).exists() or decode(read(args.output / HOLD)).get("state") != "IMPORT_PREPARING":
        raise ValueError("MIGRATION_VERIFIED_IMPORT_REQUIRED")
    return receipt


def execute(args, verify, load_source, private_path):
    required = {
        "migration-inventory": ("snapshot",),
        "migration-verify-source": ("snapshot", "source_declaration", "source_declaration_sha256", "manifest_sha256"),
        "migration-export": ("snapshot", "source_declaration", "source_declaration_sha256", "manifest_sha256", "output"),
        "migration-verify-export": ("bundle", "export_sha256", "manifest_sha256"),
        "migration-import": ("bundle", "export_sha256", "manifest_sha256", "config", "output"),
        "migration-verify-import": ("bundle", "export_sha256", "manifest_sha256", "config", "output", "import_sha256"),
        "migration-rollback": ("bundle", "export_sha256", "manifest_sha256", "config", "output", "import_sha256"),
    }
    if args.operation not in required or any(getattr(args, k, None) is None for k in required[args.operation]):
        raise ValueError("EXACT_MIGRATION_INPUTS_REQUIRED")
    if args.dry_run and args.operation != "migration-import": raise ValueError("DRY_RUN_IS_IMPORT_ONLY")
    if args.operation == "migration-inventory":
        entries = inventory(args.snapshot)
        return {"schema": "qikvrt-offline-inventory/v1", "entries": entries,
                "inventory_sha256": sha(raw(entries)), "capture_consistency_verified": False,
                "effect_ack_done": False}
    manifest = verify(args.root, args.manifest_sha256)
    if manifest["files"].get("tools/qikvrt_self_host_migration.py", {}).get("sha256") != sha(Path(__file__).read_bytes()):
        raise ValueError("EXACT_PACKAGED_MIGRATION_VERIFIER_REQUIRED")
    if args.bundle is not None and args.operation != "migration-rollback":
        private_path(args.bundle, directory=True)
        private_path(args.bundle / "EXPORT.json"); private_path(args.bundle / "SOURCE.json")
    if args.operation == "migration-verify-source":
        disjoint(args.root, args.snapshot, args.source_declaration)
        private_path(args.snapshot, directory=True); private_path(args.source_declaration)
        entries = inventory(args.snapshot)
        declaration, _ = source_declaration(args.source_declaration, args.source_declaration_sha256, entries)
        with locked(args.snapshot, declaration["layout"]["locks"]):
            observed = consistency(args.root, args.snapshot, declaration, entries, load_source)
            if inventory(args.snapshot) != entries: raise ValueError("OFFLINE_SNAPSHOT_CHANGED_DURING_VERIFICATION")
        return {"state": "OFFLINE_SOURCE_VERIFIED", "inventory_sha256": sha(raw(entries)),
                "consistency": observed, "capture_evidence_independently_validated": False, "effect_ack_done": False}
    if args.operation == "migration-export":
        disjoint(args.root, args.snapshot, args.output, args.source_declaration)
        private_path(args.snapshot, directory=True); private_path(args.source_declaration)
        entries = inventory(args.snapshot)
        declaration, source_data = source_declaration(args.source_declaration, args.source_declaration_sha256, entries)
        pre = independent(args, "migration-verify-source")
        with locked(args.snapshot, declaration["layout"]["locks"]):
            observed = consistency(args.root, args.snapshot, declaration, entries, load_source)
            if pre["inventory_sha256"] != sha(raw(entries)) or pre["consistency"] != observed:
                raise ValueError("INDEPENDENT_SOURCE_READBACK_MISMATCH")
            fresh(args.output); (args.output / "payload").mkdir(mode=0o700)
            try:
                copy_tree(args.snapshot, args.output / "payload", entries)
                if inventory(args.snapshot) != entries: raise ValueError("OFFLINE_SNAPSHOT_CHANGED_DURING_EXPORT")
                write(args.output / "SOURCE.json", source_data)
                export = {"schema": EXPORT_SCHEMA, "source_declaration_sha256": sha(source_data),
                          "entries": entries, "consistency": observed,
                          "verifier_sha256": sha(Path(__file__).read_bytes()), "effect_ack_done": False}
                data = raw(export); write(args.output / "EXPORT.json", data)
                args.bundle, args.export_sha256 = args.output, sha(data)
                result = independent(args, "migration-verify-export")
                if inventory(args.snapshot) != entries: raise ValueError("OFFLINE_SNAPSHOT_CHANGED_AFTER_EXPORT")
                result.update(state="OFFLINE_EXPORT_VERIFIED", export_sha256=sha(data), source_untouched=True)
                return result
            except BaseException:
                if not (args.output / HOLD).exists(): write(args.output / HOLD, raw({"state": "EXPORT_QUARANTINED", "effect_ack_done": False}))
                raise
    if args.operation == "migration-verify-export":
        export, _ = verify_export(args, load_source)
        return {"state": "OFFLINE_EXPORT_VERIFIED", "export_sha256": args.export_sha256,
                "source_inventory_sha256": sha(raw(export["entries"])), "effect_ack_done": False}
    if args.operation == "migration-verify-import":
        verify_import(args, manifest, load_source, private_path)
        return {"state": "OFFLINE_IMPORT_VERIFIED_PENDING_HOST_ADMISSION_AND_EXTERNAL_READBACK",
                "import_sha256": args.import_sha256, "host_admission_verified": False,
                "public_readback_verified": False, "effect_ack_done": False}
    if args.operation == "migration-rollback":
        # Quarantine first, even when bytes/pins are damaged. Never erase a
        # changed target or switch a provider route back to stale source data.
        private_path(args.output, directory=True)
        with storage.stopped_state(args.output):
            if not (args.output / HOLD).exists():
                write(args.output / HOLD, raw({"state": "ROLLBACK_QUARANTINED", "effect_ack_done": False}))
            try:
                private_path(args.bundle, directory=True)
                private_path(args.bundle / "EXPORT.json"); private_path(args.bundle / "SOURCE.json")
                verify_import(args, manifest, load_source, private_path)
                state = "CANDIDATE_QUARANTINED_SOURCE_UNTOUCHED"
            except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
                state = "HOLD_TARGET_DRIFT_RECONCILIATION_REQUIRED"
        return {"state": state, "target_start_permitted": False, "target_deleted": False,
                "source_restart_authorized": False, "routing_changed": False, "effect_ack_done": False}
    if args.operation != "migration-import": raise ValueError("UNKNOWN_MIGRATION_OPERATION")
    disjoint(args.root, args.bundle, args.output, args.config)
    independent(args, "migration-verify-export")
    export, declaration = verify_export(args, load_source)
    binding = target_binding(args, manifest, declaration, export["consistency"], private_path)
    if args.dry_run:
        return {"state": "DRY_RUN_VERIFIED_NO_TARGET_WRITE", "export_sha256": args.export_sha256,
                "proposed_binding": binding, "source_files": len(export["entries"]),
                "routing_changed": False, "host_admission_verified": False, "effect_ack_done": False}
    fresh(args.output)
    write(args.output / HOLD, raw({"state": "IMPORT_PREPARING", "export_sha256": args.export_sha256, "effect_ack_done": False}))
    try:
        directories(args.output / "legacy/railway")
        copy_tree(args.bundle / "payload", args.output / "legacy/railway", export["entries"])
        for name in ("temdd", "monitor", "receipts/railway-migration"):
            directories(args.output / name)
        native = native_source(args.root, load_source)
        inspect_sqlite(args.bundle / "payload", declaration["layout"]["ledger"], native,
                       args.output / "temdd/events.sqlite3")
        if declaration["layout"]["monitor"]:
            write(args.output / "monitor/node.json", read(args.bundle / "payload" / declaration["layout"]["monitor"]))
        # Keep the old binding in the byte-identical legacy tree; write only the
        # new volume binding. No historical event subject/digest is relabelled.
        write(args.output / "binding.json", raw(binding))
        write(args.output / "node.lock", b""); write(args.output / "temdd/owner.lock", b"")
        write(args.output / "receipts/railway-migration/EXPORT.json", read(args.bundle / "EXPORT.json"))
        write(args.output / "receipts/railway-migration/SOURCE.json", read(args.bundle / "SOURCE.json"))
        receipt = {"schema": IMPORT_SCHEMA, "export_sha256": args.export_sha256,
            "target": str(args.output), "binding": binding, "entries": target_inventory(args.output),
            "preservation": "ALL_ORIGINAL_FILES_AND_DIRECTORIES; NATIVE_ROWS_EPOCH_AND_JOURNAL_BYTES_UNCHANGED",
            "sqlite_transform": "BACKUP_OF_COMPLETE_COMMITTED_IMAGE; ORIGINAL_DB_WAL_SHM_RETAINED_IN_LEGACY",
            "mode_transform": "OWNER_ONLY_0700_DIRECTORIES_0600_FILES; ORIGINAL_MODES_IN_EXPORT",
            "host_admission_verified": False, "public_readback_verified": False, "effect_ack_done": False}
        data = raw(receipt); write(args.output / RECEIPT, data)
        args.import_sha256 = sha(data)
        with storage.stopped_state(args.output):
            result = independent(args, "migration-verify-import", args.output)
            # Reobserve in this process as well before releasing the offline hold.
            verify_import(args, manifest, load_source, private_path)
            verified = completion(args.import_sha256, args.export_sha256, binding)
            write(args.output / VERIFIED, verified)
            start_receipt(args.output, args.export_sha256, binding, private_path)
            (args.output / HOLD).unlink(); sync(args.output)
        result.update(source_untouched=True, routing_changed=False, deployment_performed=False,
                      completion_sha256=sha(verified))
        return result
    except BaseException:
        # The held candidate remains available for forensic/recovery readback.
        # No existing volume, source service, route or acknowledged row is erased.
        if not (args.output / HOLD).exists(): write(args.output / HOLD, raw({"state": "IMPORT_QUARANTINED", "effect_ack_done": False}))
        raise
