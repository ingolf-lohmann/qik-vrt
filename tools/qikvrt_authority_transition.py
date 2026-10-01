#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Executable Authority recovery and serialized, scoped provider admission.

The private, independently surviving SQLite control plane is the fencing sink.
All admitted writes must use commit_write; bypass-capable writers cannot be
fenced by this adapter. Its epoch must never be restored from an old backup.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import qikvrt_mesh_recovery as recovery
from tools.qikvrt_seed_common import canonical_json_bytes, parse_json_bytes

TransitionError = recovery.RecoveryError
SCHEMA = "qikvrt_fenced_authority_state_v1"
OBSERVATION_TTL_NS = 30_000_000_000
BINDING_KEYS = {"node_id", "repository", "head", "tree", "manifest_sha256", "scheduler_sha256"}
STATE_KEYS = {"schema", "control_plane_epoch", "authority_epoch", "revision", "phase",
              "binding", "fence", "scheduler", "root_repository"}
PERMIT_KEYS = {"control_plane_epoch", "authority_epoch", "node_id", "fence"}


def decode(raw: bytes | str) -> Any:
    data = raw.encode() if isinstance(raw, str) else raw
    value = parse_json_bytes(data, "authority control plane")
    if canonical_json_bytes(value) != data:
        raise TransitionError("noncanonical control-plane JSON")
    return value


def verify_restored(node: Path, manifest_sha256: str) -> tuple[dict, dict]:
    """Recheck actual restored bytes, not an inherited restore receipt."""
    if (node / "INCOMPLETE").exists():
        raise TransitionError("incomplete restored node")
    manifest = recovery.load_json(node / "manifest.json", manifest_sha256)
    recovery.exact(manifest, {"schema", "closure_plan_sha256", "plan", "bundle"}, "manifest")
    if manifest["schema"] != recovery.MANIFEST_SCHEMA:
        raise TransitionError("unsupported checkpoint")
    plan = manifest["plan"]
    recovery.validate_plan(plan)
    if recovery.digest(canonical_json_bytes(plan)) != manifest["closure_plan_sha256"]:
        raise TransitionError("closure plan drift")
    identity = decode(recovery.read_file(node / "node.json"))
    recovery.exact(identity, {"schema", "root_repository", "node_id", "parent_node_id",
        "source_checkpoint_sha256", "lineage", "mode", "runtime_rebinding_required",
        "writer_enabled"}, "restored identity")
    recovery.require_digest(identity["node_id"])
    if (identity["schema"] != "qikvrt_restored_node_identity_v1"
            or identity["root_repository"] != recovery.ROOT_REPOSITORY
            or identity["source_checkpoint_sha256"] != manifest_sha256
            or identity["lineage"] != plan["lineage"] or identity["writer_enabled"] is not False):
        raise TransitionError("restored identity drift or unfenced writer")
    if identity["mode"] == "RESTORE":
        if (identity["node_id"] != plan["node_id"] or identity["parent_node_id"] is not None
                or identity["runtime_rebinding_required"] is not False):
            raise TransitionError("restore identity drift")
    elif identity["mode"] == "CLONE":
        if (identity["node_id"] == plan["node_id"] or identity["parent_node_id"] != plan["node_id"]
                or identity["runtime_rebinding_required"] is not True):
            raise TransitionError("clone identity drift")
    else:
        raise TransitionError("unknown restored mode")
    repository = node / "repository.git"
    recovery.git_command(repository, "fsck", "--full", "--strict", "--no-reflogs")
    if recovery.git_snapshot(repository, plan["git"]["required_objects"]) != plan["git"]:
        raise TransitionError("restored target HEAD/TREE/ref drift")
    if recovery.inventory_files(node / "payload") != {a["path"] for a in plan["assets"]}:
        raise TransitionError("restored payload inventory drift")
    for asset in plan["assets"]:
        recovery.copy_verified(node / "payload" / asset["path"], None, asset)
    recovery.copy_verified(node / "signature.bin", None, {
        "bytes": 400, "sha256": plan["signature_sha256"], "mode": 0o644})
    recovery.validate_scheduler(node / "payload", plan)
    asset = next(a for a in plan["assets"] if a["category"] == "scheduler")
    scheduler = recovery.load_json(node / "payload" / asset["path"], asset["sha256"])
    binding = {"node_id": identity["node_id"], "repository": plan["repository"],
        "head": plan["git"]["head"], "tree": plan["git"]["tree"],
        "manifest_sha256": manifest_sha256, "scheduler_sha256": asset["sha256"]}
    return binding, scheduler


def token_hash(token: str) -> str:
    # Caller supplies an actually unsealed private capability, never a boolean
    # "unseal succeeded" receipt or an opaque escrow digest.
    recovery.require_digest(token)
    return recovery.digest(token.encode("ascii"))


def private_path(path: Path, *, existing: bool) -> None:
    if os.name != "posix":
        raise TransitionError("private Authority sink requires POSIX ownership semantics")
    for parent in (path.parent, *path.parent.parents):
        if parent.is_symlink():
            raise TransitionError("symlink control-plane path")
    parent_stat = path.parent.stat()
    if (not stat.S_ISDIR(parent_stat.st_mode) or stat.S_IMODE(parent_stat.st_mode) != 0o700
            or parent_stat.st_uid != os.getuid()):
        raise TransitionError("control plane requires an owner-only 0700 directory")
    if existing:
        recovery.regular(path)
        st = path.stat()
        if stat.S_IMODE(st.st_mode) != 0o600 or st.st_uid != os.getuid() or st.st_nlink != 1:
            raise TransitionError("control plane requires an owner-only nonlinked 0600 database")


class AuthorityControlPlane:
    """Local trusted sink: bounded SQLite transactions fence every commit.

    Filesystem owner/admin access is the trust boundary; direct DB edits,
    rollback, copied databases and writes to other sinks are outside it.
    No missing DB is auto-created or reconstructed by an ordinary operation.
    """
    def __init__(self, path: Path):
        self.path = path.absolute()

    @contextmanager
    def transaction(self):
        private_path(self.path, existing=True)
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=2)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise TransitionError("unsupported control-plane schema")
            yield db
            db.commit()
        except sqlite3.Error as exc:
            db.rollback()
            raise TransitionError("control-plane transaction failed or unavailable") from exc
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def initialize(self, node: Path, manifest_sha256: str, epoch: int,
                   admin_token: str, writer_token: str) -> dict:
        binding, scheduler = verify_restored(node, manifest_sha256)
        if type(epoch) is not int or not 0 <= epoch < 2**63 - 1:
            raise TransitionError("invalid initial Authority epoch")
        admin_hash, writer_hash = token_hash(admin_token), token_hash(writer_token)
        if hmac.compare_digest(admin_hash, writer_hash):
            raise TransitionError("admin and writer capabilities must be distinct")
        private_path(self.path, existing=False)
        # Explicit owner bootstrap only, create-only. Takeover never calls this.
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(fd)
        db = sqlite3.connect(self.path, timeout=2)
        state = {"schema": SCHEMA, "control_plane_epoch": secrets.token_hex(32),
            "authority_epoch": epoch, "revision": 0, "phase": "ACTIVE",
            "binding": binding, "fence": secrets.token_hex(32), "scheduler": scheduler,
            "root_repository": recovery.ROOT_REPOSITORY}
        for schedule in scheduler["schedules"]:
            schedule["owner_node_id"] = binding["node_id"]
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE state (singleton INTEGER PRIMARY KEY CHECK(singleton=1), document BLOB NOT NULL);
                CREATE TABLE admin (token_hash TEXT PRIMARY KEY);
                CREATE TABLE grants (token_hash TEXT PRIMARY KEY, binding BLOB NOT NULL, role TEXT NOT NULL, recovery_epoch INTEGER);
                CREATE TABLE observations (id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, document BLOB NOT NULL, expires_ns INTEGER NOT NULL);
                CREATE TABLE effects (id TEXT PRIMARY KEY, payload BLOB NOT NULL, node_id TEXT NOT NULL, epoch INTEGER NOT NULL);
                PRAGMA user_version=1;
            """)
            db.execute("INSERT INTO state VALUES (1, ?)", (canonical_json_bytes(state),))
            db.execute("INSERT INTO admin VALUES (?)", (admin_hash,))
            db.execute("INSERT INTO grants VALUES (?, ?, 'AUTHORITY', NULL)", (writer_hash, canonical_json_bytes(binding)))
            db.commit()
        finally:
            db.close()
        return self.readback(writer_token)

    @staticmethod
    def state(db) -> dict:
        row = db.execute("SELECT document FROM state WHERE singleton=1").fetchone()
        if row is None:
            raise TransitionError("missing Authority state")
        state = decode(row[0])
        recovery.exact(state, STATE_KEYS, "Authority state")
        recovery.exact(state["binding"], BINDING_KEYS, "Authority binding")
        if (state["schema"] != SCHEMA or state["root_repository"] != recovery.ROOT_REPOSITORY
                or state["phase"] not in {"ACTIVE", "PENDING_READBACK"}
                or type(state["authority_epoch"]) is not int or not 0 <= state["authority_epoch"] < 2**63 - 1
                or type(state["revision"]) is not int or state["revision"] < 0):
            raise TransitionError("invalid Authority state")
        for field in ("control_plane_epoch", "fence"):
            recovery.require_digest(state[field])
        return state

    @staticmethod
    def grant(db, token: str) -> tuple[dict, str]:
        row = db.execute("SELECT binding, role FROM grants WHERE token_hash=?", (token_hash(token),)).fetchone()
        if row is None:
            raise TransitionError("unsealed capability not authorized for this sink")
        binding = decode(row[0])
        recovery.exact(binding, BINDING_KEYS, "capability binding")
        return binding, row[1]

    @staticmethod
    def store(db, state: dict) -> None:
        db.execute("UPDATE state SET document=? WHERE singleton=1", (canonical_json_bytes(state),))

    def authorize_recovery(self, node: Path, manifest_sha256: str,
                           admin_token: str, recovery_token: str) -> dict:
        binding, _ = verify_restored(node, manifest_sha256)
        capability = token_hash(recovery_token)
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM admin WHERE token_hash=?", (token_hash(admin_token),)).fetchone() is None:
                raise TransitionError("owner recovery grant requires control-plane admin capability")
            if db.execute("SELECT 1 FROM admin WHERE token_hash=?", (capability,)).fetchone():
                raise TransitionError("admin capability cannot become a writer")
            state = self.state(db)
            db.execute("INSERT INTO grants VALUES (?, ?, 'RECOVERY', ?)",
                       (capability, canonical_json_bytes(binding), state["authority_epoch"]))
        return {"binding": binding, "recovery_granted": True, "writer_enabled": False,
                "effect_ack_done": False}

    def readback(self, token: str) -> dict:
        with self.transaction() as db:
            binding, role = self.grant(db, token)
            state = self.state(db)
        return {"state": state, "node_role": role, "node_id": binding["node_id"],
                "effect_ack_done": False, "effect_scope": "LOCAL_CONTROL_PLANE_AND_GATED_EFFECT_LEDGER"}

    def observe(self, node: Path, manifest_sha256: str, token: str) -> dict:
        binding, _ = verify_restored(node, manifest_sha256)
        with self.transaction() as db:
            grant, _ = self.grant(db, token)
            if grant != binding:
                raise TransitionError("capability target drift")
            state = self.state(db)
            now = time.time_ns()
            observation = {"schema": "qikvrt_authority_observation_v1", "id": secrets.token_hex(32),
                "control_plane_epoch": state["control_plane_epoch"],
                "authority_epoch": state["authority_epoch"], "revision": state["revision"],
                "state_sha256": recovery.digest(canonical_json_bytes(state)),
                "target": binding, "issued_ns": now, "expires_ns": now + OBSERVATION_TTL_NS}
            db.execute("DELETE FROM observations WHERE expires_ns < ?", (now,))
            db.execute("INSERT INTO observations VALUES (?, ?, ?, ?)",
                       (observation["id"], token_hash(token), canonical_json_bytes(observation), observation["expires_ns"]))
        return observation

    def takeover(self, node: Path, manifest_sha256: str, token: str, observation: dict) -> dict:
        binding, scheduler = verify_restored(node, manifest_sha256)
        # Authentication, fresh observation, CAS, fence rotation and role/schedule
        # rebinding share the same transaction as the sink's writer exclusion.
        with self.transaction() as db:
            grant, role = self.grant(db, token)
            if grant != binding or role not in {"RECOVERY", "PENDING"}:
                raise TransitionError("no target-scoped recovery grant")
            if not isinstance(observation, dict) or not isinstance(observation.get("id"), str):
                raise TransitionError("invalid observation")
            row = db.execute("SELECT document FROM observations WHERE id=? AND token_hash=?",
                             (observation["id"], token_hash(token))).fetchone()
            if row is None or decode(row[0]) != observation:
                raise TransitionError("unknown, altered or consumed observation")
            now = time.time_ns()
            if not observation["issued_ns"] <= now <= observation["expires_ns"]:
                raise TransitionError("stale observation or clock rollback")
            state = self.state(db)
            # A provider timeout/process death can leave a request in flight.
            # Never rotate the fence while that effect is unresolved. The
            # provider adapter may reconcile it by GET only, including restart.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='provider_effects'").fetchone():
                if db.execute("SELECT 1 FROM provider_effects WHERE status IN ('PREPARED','PENDING') LIMIT 1").fetchone():
                    raise TransitionError("unresolved provider effect blocks Authority takeover")
            granted_epoch = db.execute("SELECT recovery_epoch FROM grants WHERE token_hash=?",
                                      (token_hash(token),)).fetchone()[0]
            if granted_epoch != state["authority_epoch"]:
                raise TransitionError("stale epoch: Owner recovery grant requires renewal")
            if (observation["target"] != binding
                    or observation["state_sha256"] != recovery.digest(canonical_json_bytes(state))):
                raise TransitionError("stale epoch/revision: Authority CAS conflict")
            # Preserve every cursor/key; rebind only role-local ownership. The
            # surviving sink ledger deduplicates already committed pending work.
            scheduler = decode(canonical_json_bytes(scheduler))
            for schedule in scheduler["schedules"]:
                schedule["owner_node_id"] = binding["node_id"]
            if any(binding[key] != state["binding"][key] for key in ("head", "tree")):
                raise TransitionError("restored target is behind or diverges from accepted HEAD/TREE")
            previous_scheduler = decode(canonical_json_bytes(state["scheduler"]))
            for schedule in previous_scheduler["schedules"]:
                schedule["owner_node_id"] = binding["node_id"]
            if scheduler != previous_scheduler:
                raise TransitionError("scheduler cursor/key checkpoint drift")
            if state["authority_epoch"] >= 2**63 - 2:
                raise TransitionError("Authority epoch exhausted; versioned control-plane successor required")
            successor = {**state, "authority_epoch": state["authority_epoch"] + 1,
                "revision": state["revision"] + 1, "phase": "PENDING_READBACK",
                "binding": binding, "fence": secrets.token_hex(32), "scheduler": scheduler}
            db.execute("UPDATE grants SET role='MIRROR' WHERE role IN ('AUTHORITY', 'PENDING')")
            db.execute("UPDATE grants SET role='PENDING' WHERE token_hash=?", (token_hash(token),))
            db.execute("DELETE FROM observations WHERE id=?", (observation["id"],))
            self.store(db, successor)
        # Commit acknowledgement alone never opens the writer. Separate fresh
        # activation/readback is required, including after a process restart.
        return {"permit": self.permit(successor), "authority_changed": True,
                "writer_enabled": False, "effect_ack_done": False}

    @staticmethod
    def permit(state: dict) -> dict:
        return {"control_plane_epoch": state["control_plane_epoch"],
            "authority_epoch": state["authority_epoch"], "node_id": state["binding"]["node_id"],
            "fence": state["fence"]}

    @staticmethod
    def check_permit(state: dict, grant: dict, permit: dict) -> None:
        recovery.exact(permit, PERMIT_KEYS, "writer permit")
        if (type(permit["authority_epoch"]) is not int
                or permit != AuthorityControlPlane.permit(state) or grant != state["binding"]):
            raise TransitionError("old writer rejected: epoch/fence/target mismatch")

    def provider_admission(self, db, token: str, permit: dict, repository: str) -> dict:
        """Fresh check while the caller holds the same lock as takeover.

        Only the scoped API shim owns the provider bearer credential. A client
        with its own bypass credential is explicitly outside this boundary.
        """
        grant, role = self.grant(db, token)
        state = self.state(db)
        self.check_permit(state, grant, permit)
        if state["phase"] != "ACTIVE" or role != "AUTHORITY":
            raise TransitionError("provider writer fenced until fresh activation")
        if repository != grant["repository"]:
            raise TransitionError("provider repository outside active node capability")
        return state

    def activate(self, node: Path, manifest_sha256: str, token: str, permit: dict) -> dict:
        binding, scheduler = verify_restored(node, manifest_sha256)
        for schedule in scheduler["schedules"]:
            schedule["owner_node_id"] = binding["node_id"]
        with self.transaction() as db:
            grant, role = self.grant(db, token)
            state = self.state(db)  # Fresh post-CAS read from durable sink.
            self.check_permit(state, grant, permit)
            if (grant != binding or state["scheduler"] != scheduler
                    or state["phase"] != "PENDING_READBACK" or role != "PENDING"):
                raise TransitionError("fresh role/target/scheduler readback mismatch")
            state.update(phase="ACTIVE", revision=state["revision"] + 1)
            self.store(db, state)
            db.execute("UPDATE grants SET role='AUTHORITY' WHERE token_hash=?", (token_hash(token),))
        result = self.readback(token)
        # A concurrent successor between commit and readback must not yield a
        # stale local writer-enabled receipt. Every later write checks again.
        self.check_permit(result["state"], binding, permit)
        if result["state"]["phase"] != "ACTIVE" or result["node_role"] != "AUTHORITY":
            raise TransitionError("activation superseded before readback")
        return {**result, "permit": permit, "writer_enabled": True, "authority_changed": True}

    def commit_write(self, token: str, permit: dict, effect_id: str, payload: bytes) -> dict:
        if (not isinstance(effect_id, str) or not 1 <= len(effect_id) <= 256
                or any(ord(c) < 32 for c in effect_id) or not isinstance(payload, bytes)
                or len(payload) > recovery.MAX_JSON_BYTES):
            raise TransitionError("invalid bounded sink effect")
        with self.transaction() as db:
            grant, role = self.grant(db, token)
            state = self.state(db)
            self.check_permit(state, grant, permit)
            if state["phase"] != "ACTIVE" or role != "AUTHORITY":
                raise TransitionError("writer fenced until fresh activation")
            previous = db.execute("SELECT payload FROM effects WHERE id=?", (effect_id,)).fetchone()
            if previous is not None:
                if previous[0] != payload:
                    raise TransitionError("idempotency key payload conflict")
            else:
                db.execute("INSERT INTO effects VALUES (?, ?, ?, ?)",
                    (effect_id, payload, grant["node_id"], state["authority_epoch"]))
                state["revision"] += 1
                self.store(db, state)
        # Actual post-commit byte readback, still fenced against a later takeover.
        with self.transaction() as db:
            grant, role = self.grant(db, token)
            state = self.state(db)
            self.check_permit(state, grant, permit)
            if state["phase"] != "ACTIVE" or role != "AUTHORITY":
                raise TransitionError("effect committed but writer superseded before readback")
            observed = db.execute("SELECT payload FROM effects WHERE id=?", (effect_id,)).fetchone()
            if observed is None or observed[0] != payload:
                raise TransitionError("sink effect readback mismatch")
        return {"effect_id": effect_id, "payload_sha256": recovery.digest(payload),
            "fresh_sink_readback": True, "replayed": previous is not None,
            "effect_ack_done": False, "effect_scope": "LOCAL_GATED_EFFECT_LEDGER"}

    def rejoin(self, token: str, old_permit: dict) -> dict:
        with self.transaction() as db:
            grant, role = self.grant(db, token)
            state = self.state(db)
            recovery.exact(old_permit, PERMIT_KEYS, "old writer permit")
            if (old_permit["control_plane_epoch"] != state["control_plane_epoch"]
                    or old_permit["node_id"] != grant["node_id"]
                    or type(old_permit["authority_epoch"]) is not int
                    or old_permit["authority_epoch"] >= state["authority_epoch"]
                    or grant["node_id"] == state["binding"]["node_id"] or role != "MIRROR"):
                raise TransitionError("rejoin requires a fenced predecessor from this control plane")
        return {"node_id": grant["node_id"], "role": "MIRROR", "writer_enabled": False,
                "full_node_admitted": False, "catch_up_required": True, "effect_ack_done": False}


def secret_file(path: Path) -> str:
    if os.name != "posix":
        raise TransitionError("private capability input requires POSIX ownership semantics")
    recovery.regular(path)
    st = path.stat()
    if stat.S_IMODE(st.st_mode) != 0o600 or st.st_uid != os.getuid():
        raise TransitionError("capability input requires a private owner-only 0600 file")
    token = recovery.read_file(path, 65).decode("ascii").strip()
    token_hash(token)
    return token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("init", "grant", "observe", "takeover", "activate", "write", "readback", "rejoin"))
    parser.add_argument("--control-plane", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--admin-token-file", type=Path)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--authority-epoch", type=int)
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--permit", type=Path)
    parser.add_argument("--effect-id")
    parser.add_argument("--payload", type=Path)
    args = parser.parse_args(argv)
    try:
        cp = AuthorityControlPlane(args.control_plane)
        token = secret_file(args.token_file)
        if args.operation in {"init", "grant", "observe", "takeover", "activate"}:
            if args.node is None or args.expect_manifest_sha256 is None:
                raise TransitionError("node and externally pinned manifest digest required")
        if args.operation in {"init", "grant"}:
            if args.admin_token_file is None:
                raise TransitionError("separate owner/admin capability required")
            admin = secret_file(args.admin_token_file)
        if args.operation in {"activate", "write", "rejoin"}:
            if args.permit is None:
                raise TransitionError("exact writer permit required")
            permit = decode(recovery.read_file(args.permit))
        if args.operation == "init":
            result = cp.initialize(args.node, args.expect_manifest_sha256, args.authority_epoch, admin, token)
        elif args.operation == "grant":
            result = cp.authorize_recovery(args.node, args.expect_manifest_sha256, admin, token)
        elif args.operation == "observe":
            result = cp.observe(args.node, args.expect_manifest_sha256, token)
        elif args.operation == "takeover":
            if args.observation is None:
                raise TransitionError("fresh authenticated observation required")
            result = cp.takeover(args.node, args.expect_manifest_sha256, token,
                                 decode(recovery.read_file(args.observation)))
        elif args.operation == "activate":
            result = cp.activate(args.node, args.expect_manifest_sha256, token, permit)
        elif args.operation == "write":
            if args.payload is None:
                raise TransitionError("bounded payload file required")
            result = cp.commit_write(token, permit, args.effect_id, recovery.read_file(args.payload))
        elif args.operation == "rejoin":
            result = cp.rejoin(token, permit)
        else:
            result = cp.readback(token)
        sys.stdout.buffer.write(canonical_json_bytes(result))
        return 0
    except (TransitionError, OSError, RuntimeError, ValueError, TypeError, sqlite3.Error):
        # No arbitrary database, payload, capability or Git text in errors.
        sys.stdout.buffer.write(canonical_json_bytes({"state": "BLOCK", "effect_ack_done": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
