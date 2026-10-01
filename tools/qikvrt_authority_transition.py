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
import ast
from contextlib import contextmanager
import hmac
import os
import re
from pathlib import Path
import secrets
import sqlite3
import stat
import subprocess
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


def deny_unbrokered_provider_write() -> None:
    """No flag, acceptance record or old bearer can authorize a bypass.

    Unsupported operations require a successor of the existing broker contract.
    This is a denial boundary, never another permit issuer or writer service.
    """
    raise TransitionError("NO_BYPASS: unsupported provider write; use current Authority broker")


def decode(raw: bytes | str) -> Any:
    data = raw.encode() if isinstance(raw, str) else raw
    value = parse_json_bytes(data, "authority control plane")
    if canonical_json_bytes(value) != data:
        raise TransitionError("noncanonical control-plane JSON")
    return value


def verify_restored(node: Path, manifest_sha256: str) -> tuple[dict, dict]:
    """Use the same fresh restored-node validator as recursive checkpointing."""
    return recovery.verify_restored_node(node, manifest_sha256)


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


# Conservative source admission gate. This inventories current runnable bytes;
# it cannot revoke credentials or disable historical workflow runs at GitHub.
WRITER_SIGNAL = re.compile(
    r"(?:\bgit\b[^\n]{0,100}\b(?:push|send-pack)\b|"
    r"[\"'](?:git|--method)[\"'][\s,]+[\"'](?:push|POST|PATCH|PUT|DELETE)[\"']|"
    r"\bgh\s+(?:api[^\n]*(?:--method|-X)\s+(?:POST|PATCH|PUT|DELETE)|"
    r"(?:pr|issue|release)\s+(?:create|merge|edit|comment|review|close|delete|upload)|workflow\s+run)|"
    r"(?:--request|-X)\s+(?:POST|PATCH|PUT|DELETE)|"
    r"\bgh\s+api[^\n]*(?:--input\b|--raw-field\b|--field\b|-f\s|-F\s)|"
    r"--data(?:-binary|-raw)?\s|"
    r"(?:github|octokit)(?:\.rest)?\.[A-Za-z_.]+\.(?:create|update|delete|merge|upload|dispatch)[A-Za-z_]*\s*\(|"
    r"(?:method\s*[=:]\s*|Method\s+)[\"']?(?:POST|PATCH|PUT|DELETE)|"
    r"(?:api|github|transport)\.request\(\s*[\"'](?:POST|PATCH|PUT|DELETE)|"
    r"requests\.(?:post|put|patch|delete)\s*\(|curl\b[^\n]*(?:--data|--json|-d\s)|"
    r"\w+:\s*write\b|persist-credentials:\s*true|"
    r"secrets\.(?:QIKVRT_)?(?:GITHUB|MESH|RULESET)|create-github-app-token)", re.I)
PROVIDER_SIGNAL = re.compile(r"GITHUB_TOKEN|GH_TOKEN|github\.token|api\.github\.com|"
    r"GITHUB_API_BASE|NO_BYPASS:|github_zenodo_release_publish|incoming[/\\]|\bgit\b|\bgh\b|secrets\.(?:QIKVRT_)?(?:GITHUB|MESH|RULESET)")
RUNNABLE_SUFFIXES = {'.py', '.sh', '.bash', '.ps1', '.cmd', '.bat', '.js', '.mjs', '.cjs', '.ts',
                     '.yml', '.yaml', '.c', '.h', '.cpp', '.go', '.rs', '.cs', '.rb', '.pl', '.php'}


def runnable_path(path: Path) -> bool:
    if path.suffix.lower() in RUNNABLE_SUFFIXES or path.name in {
            'Makefile', 'GNUmakefile', 'makefile', 'package.json', 'Jenkinsfile', 'Dockerfile'}:
        return True
    if path.is_symlink():
        return True
    if path.is_file():
        if path.stat().st_mode & 0o111:
            return True
        with path.open('rb') as handle:
            return handle.read(2) == b'#!'
    return False


PACKAGED_WRITER_STUB = ('#!/usr/bin/env python3\n'
    '# SPDX-License-Identifier: Apache-2.0\n# Copyright 2026 Ingolf Lohmann.\n'
    'import sys\nprint("NO_BYPASS: packaged writer disabled; use current Authority broker", file=sys.stderr)\n'
    'raise SystemExit(78)\n')


def _workflow_jobs(source: str) -> tuple[str, list[tuple[str, str]]]:
    if re.search(r'^\s*<<:|^\s*(?:jobs|permissions):.*[&*]|^\s*permissions:.*write', source, re.M):
        raise TransitionError("unsupported workflow alias or inline write permissions")
    marker = re.search(r'^jobs:[ \t]*$', source, re.M)
    if marker is None:
        raise TransitionError("unsupported workflow layout")
    prefix = source[:marker.end()]
    rest = source[marker.end():]
    starts = list(re.finditer(r'^  ([A-Za-z0-9_-]+):[ \t]*$', rest, re.M))
    if not starts:
        raise TransitionError("unsupported workflow jobs")
    return prefix, [(m.group(1), rest[m.start():starts[i+1].start() if i+1 < len(starts) else len(rest)])
                    for i, m in enumerate(starts)]


def _guarded_request(source: str, name: str, *, plan: bool = False) -> bool:
    """Check denial dominates the function's transport, including fake transports."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(functions) != 1:
        return False
    body = functions[0].body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    if not body or not isinstance(body[0], ast.If):
        return False
    guard = body[0]
    if plan:
        expected = ('any(action.get("effect") in {"github_push", "github_release"} '
                    'for action in plan.get("actions", []))')
        return ast.dump(guard.test) == ast.dump(ast.parse(expected, mode='eval').body) and (
            len(guard.body) == 1 and isinstance(guard.body[0], ast.Return) and
            ast.literal_eval(guard.body[0].value) == (20, [], "NO_BYPASS: GitHub publication requires current Authority broker"))
    return (ast.dump(guard.test) == ast.dump(ast.parse('method != "GET"', mode='eval').body)
            and len(guard.body) == 2 and isinstance(guard.body[0], ast.ImportFrom)
            and guard.body[0].module == 'tools.qikvrt_authority_transition'
            and [(x.name, x.asname) for x in guard.body[0].names] == [('deny_unbrokered_provider_write', None)]
            and ast.dump(guard.body[1]) == ast.dump(ast.parse('deny_unbrokered_provider_write()').body[0]))


def audit_repository_writers(root: Path = ROOT) -> dict:
    """Fail closed on new raw writers; classify history, tests and local paths.

    Every executable file, including untracked candidate files, is considered.
    Historical/documentary bytes never grant authority. Calling incoming code
    from an active entrypoint is a violation, even if that archive is excluded.
    The inventory is evidence for source admission, not production fencing.
    """
    root = root.resolve(strict=True)
    paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z', '--cached',
        '--others', '--exclude-standard'], timeout=30).decode('utf-8').split('\0')
    records = []
    violations = []
    packaged = set()
    filename_map = root / 'payload/monthly_content/PAYLOAD_FILENAME_MAP_V36.json'
    if filename_map.exists():
        mapping = recovery.parse_json_bytes(recovery.read_file(filename_map), 'payload filename map')
        for item in mapping['items']:
            name = recovery.safe_path(item['new_name'])
            if runnable_path(Path(item['old_name'])):
                packaged.add('payload/monthly_content/' + name)
    excluded_runnables = [p for p in paths if p.startswith(('incoming/', 'docs/', 'state/', 'evidence/'))
                          and runnable_path(root / p)]
    for relative in sorted(set(paths) - {''}):
        path = root / relative
        if not runnable_path(path) and relative not in packaged:
            continue
        if path.is_symlink() or not path.is_file():
            violations.append({'path': relative, 'reason': 'nonregular runnable file'})
            continue
        raw = recovery.read_file(path)
        try:
            source = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            violations.append({'path': relative, 'reason': 'non-UTF8 runnable file'})
            continue
        lines = [i for i, line in enumerate(source.splitlines(), 1) if WRITER_SIGNAL.search(line)]
        if not relative.startswith('.github/workflows/') and not lines and not PROVIDER_SIGNAL.search(source):
            continue
        category = 'READ_ONLY_OR_LOCAL_NON_PROVIDER'
        errors = []
        units = []
        if relative.startswith('incoming/'):
            category = 'HISTORICAL_INCOMING_NOT_ADMITTED'
        elif relative in packaged and source == PACKAGED_WRITER_STUB:
            category = 'DISABLED_PACKAGED_WRITER_ENTRYPOINT'
        elif relative.startswith(('evidence/', 'state/')) or (relative.startswith('docs/')
                and path.suffix.lower() not in {'.js', '.mjs', '.ts'}):
            category = 'DOCUMENTARY_NOT_ADMITTED'
        elif relative.startswith('tests/') or '/tests/' in relative:
            category = 'TEST_FIXTURE_NOT_PRODUCTION'
        elif relative == 'api/qikvrt_github_api.openapi.yaml':
            category = 'INTEROPERABILITY_SPEC_NOT_EXECUTABLE'
        elif relative.startswith('.github/workflows/'):
            try:
                prefix, jobs = _workflow_jobs(source)
            except TransitionError:
                violations.append({'path': relative, 'reason': 'unsupported workflow grammar'})
                continue
            if WRITER_SIGNAL.search(prefix):
                errors.append('workflow-level write capability or raw mutation')
            if not re.search(r'^permissions:', prefix, re.M):
                errors.append('workflow relies on implicit token permissions')
            for job, body in jobs:
                disabled = bool(re.search(r'^    if: \$\{\{ false \}\} # NO_BYPASS: unsupported provider writer disabled$', body, re.M))
                if disabled:
                    units.append({'job': job, 'admission': 'LITERAL_FALSE', 'native_permissions': 'EMPTY',
                                  'provider_effect': 'DENIED_UNTIL_BROKER_SUCCESSOR'})
                    if len(re.findall(r'^    if:', body, re.M)) != 1 or len(re.findall(r'^    permissions:', body, re.M)) != 1:
                        errors.append(job + ': ambiguous disabled admission')
                    if not re.search(r'^    permissions: \{\}$', body, re.M):
                        errors.append(job + ': disabled job must have empty permissions')
                    continue
                active = '\n'.join(line for line in body.splitlines() if not line.lstrip().startswith('#'))
                units.append({'job': job, 'admission': 'READ_ONLY_OR_LOCAL', 'native_permissions': 'READ_ONLY',
                              'provider_effect': 'NONE_ADMITTED'})
                if WRITER_SIGNAL.search(active):
                    errors.append(job + ': unbrokered active writer/capability')
                if re.search(r'incoming[/\\]', active):
                    errors.append(job + ': active entrypoint references incoming archive')
                for excluded in excluded_runnables:
                    if excluded in active or excluded.replace('/', '\\') in active:
                        archived = (root / excluded).read_text(encoding='utf-8-sig')
                        if excluded.startswith('incoming/') or WRITER_SIGNAL.search(archived):
                            errors.append(job + ': excluded writer invoked from active job')
                if 'uses: actions/checkout@' in active:
                    # All checkout steps require an explicit no-credential binding.
                    steps = re.split(r'^      - ', active, flags=re.M)
                    if any('uses: actions/checkout@' in step and 'persist-credentials: false' not in step for step in steps):
                        errors.append(job + ': checkout retains raw transport credential')
            category = 'WORKFLOW_EXPLICIT_SOURCE_ADMISSION'
        elif relative == 'src/qikvrt_github_api_shim.py':
            category = 'EXISTING_AUTHORITY_BROKER'
        elif relative == 'tools/qikvrt_authority_transition.py':
            category = 'EXISTING_CONTROL_PLANE_AND_SOURCE_AUDITOR'
        elif relative == 'tools/qikvrt_cicd_publish.py':
            category = 'PLAN_ONLY_GITHUB_EXECUTION_DENIED'
            if not _guarded_request(source, 'execute_plan', plan=True):
                errors.append('publication execution denial missing')
            if 'NO_BYPASS: uncontracted command denied' not in source:
                errors.append('direct command helper denial missing')
        elif relative in {'tools/qikvrt_vrtcore_h3_e1_recovery.py', 'tools/qikvrt_zenodo_publish.py'}:
            category = 'GET_ONLY_GITHUB_TRANSPORT'
            function = 'request' if relative.endswith('h3_e1_recovery.py') else '_github_api_request'
            if not _guarded_request(source, function):
                errors.append('first-statement GitHub write denial missing')
        elif relative == 'tools/github_zenodo_release_publish.ps1':
            category = 'DRY_RUN_LOCAL_SELFTEST_ONLY_PRODUCTIVE_BRANCH_REMOVED'
            if "throw 'NO_BYPASS: productive GitHub publication disabled; use current Authority broker'" not in source:
                errors.append('productive branch denial missing')
            if re.search(r"(?:\bpush\b[^\n]*origin|Invoke-GitHubJson -Method Post|Invoke-RestMethod -Method Post)", source, re.I):
                errors.append('PowerShell productive mutation reintroduced')
        elif relative == 'scripts/qikvrt_api_client.py':
            category = 'LOOPBACK_LOCAL_SHIM_ONLY'
            if 'if parsed_base.hostname not in loopback_hosts:' not in source or 'NO_BYPASS: compatibility dispatch is restricted to the local shim' not in source:
                errors.append('local shim origin restriction missing')
        elif relative in {'GITHUB_DRY_RUN_VERIFY_ONLY.cmd', 'GITHUB_AUTH_PREFLIGHT_ONLY.cmd'}:
            category = 'INDIRECT_DRY_OR_BLOCKED_PREFLIGHT_ENTRYPOINT'
        elif relative in {'tools/qikvrt_r11_read_only_observation_dispatch_v2.py', 'tools/qikvrt_validate_state_run.py'}:
            category = 'GET_ONLY_OBSERVER'
            if 'method="GET"' not in source or lines:
                errors.append('read-only observer changed into provider writer')
        elif relative == 'tools/qikvrt_zenodo_metadata_edit.py':
            category = 'INDIRECT_CALLER_OF_DENIED_GITHUB_CONSUMPTION_LOCK'
            if lines:
                errors.append('new direct GitHub mutation in metadata editor')
        elif relative == 'tools/verify.py':
            category = 'STATIC_SOURCE_VERIFIER_NOT_EXECUTOR'
            tree = ast.parse(source)
            if any(isinstance(n, ast.Import) and any(x.name in {'subprocess', 'requests', 'urllib'} for x in n.names)
                   or isinstance(n, ast.ImportFrom) and n.module and n.module.split('.')[0] in {'subprocess', 'requests', 'urllib'}
                   or isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'exec', 'eval', '__import__'}
                   for n in ast.walk(tree)):
                errors.append('static verifier gained execution/network capability')
        elif relative == 'browser/firefox/qikvrt-terminal/background.js':
            category = 'GET_ONLY_PUBLIC_GITHUB_AND_PINNED_LOCAL_TERMINAL'
            github = re.search(r'async function github\(path\) \{([\s\S]*?)\n\}', source)
            if (not github or 'method: "GET"' not in github.group(1)
                    or WRITER_SIGNAL.search(github.group(1))
                    or 'const ALLOWED_BACKENDS = new Set(["http://127.0.0.1:8771", "http://localhost:8771"]);' not in source
                    or 'if (!ALLOWED_BACKENDS.has' not in source
                    or len(re.findall(r'\bfetch\(', source)) != 2
                    or source.count('https://api.github.com') != 1):
                errors.append('browser provider/local origin restriction missing')
        elif relative == 'tools/offline-audio-transcription/src/materialize-request.cjs':
            category = 'GET_ONLY_BLOB_MATERIALIZER'
            if (lines or len(re.findall(r'\bhttps\.get\(', source)) != 1
                    or re.search(r'\b(?:fetch|https\.request)\(', source)
                    or 'const apiUrl = `https://api.github.com/repos/' not in source
                    or '/git/blobs/${validated.source.blobSha}`' not in source):
                errors.append('blob materializer gained unadmitted provider transport')
        elif 'NO_BYPASS:' in source and (source.rstrip().endswith('exit 78') or source.rstrip().endswith('exit /b 78')):
            category = 'DISABLED_ENTRYPOINT'
            if WRITER_SIGNAL.search('\n'.join(l for l in source.splitlines() if not l.lstrip().lower().startswith(('echo ', '#', 'rem ')))):
                errors.append('disabled entrypoint contains executable writer')
        elif lines:
            # Known non-GitHub providers are not part of GitHub fencing. Their
            # origins are independently pinned by their own existing contracts.
            if relative in {'tools/qikvrt_zenodo_actions.py', 'tools/qikvrt_status_zenodo.py',
                    'tools/qikvrt_formalization_v2_zenodo.py', 'scripts/issue_agent/infer.py'}:
                category = 'OTHER_PROVIDER_NOT_GITHUB_REPOSITORY_WRITE'
            else:
                errors.append('raw writer outside current Authority broker')
        if category == 'READ_ONLY_OR_LOCAL_NON_PROVIDER' and re.search(r'GITHUB_TOKEN|GH_TOKEN|github\.token', source):
            errors.append('raw provider capability in unreviewed operational source')
        if category == 'READ_ONLY_OR_LOCAL_NON_PROVIDER' and re.search(r'(?:GITHUB_TOKEN|GH_TOKEN|api\.github\.com)', source) and (
                re.search(r'method\s*=\s*(?:method|["\'](?:POST|PATCH|PUT|DELETE))', source)):
            errors.append('dynamic GitHub transport not admitted')
        if not category.startswith(('HISTORICAL_', 'DOCUMENTARY_', 'TEST_')) and relative not in {
                'tools/qikvrt_authority_transition.py', 'tools/qikvrt_integrity.py'} and not relative.startswith('.github/workflows/') and re.search(r'incoming[/\\]', source):
            errors.append('operational code references incoming archive')
        records.append({'path': relative, 'sha256': recovery.digest(raw), 'bytes': len(raw),
            'classification': category, 'writer_signal_lines': lines, 'execution_units': units})
        violations.extend({'path': relative, 'reason': error} for error in errors)
    return {'schema': 'qikvrt_repository_writer_inventory_v1', 'state': 'BLOCK' if violations else 'PASS',
        'scope': 'CURRENT_CANDIDATE_SOURCE_GITHUB_REPOSITORY_WRITERS_ONLY',
        'records': records, 'violations': violations, 'predecessor_evidence_transfer': False,
        'production_bypass_capabilities_revoked': False,
        'provider_authority_fencing_verified': False, 'effect_ack_done': False}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["audit-writers"]:
        audit_parser = argparse.ArgumentParser(description="Read-only GitHub writer source admission")
        audit_parser.add_argument("operation", choices=["audit-writers"])
        audit_parser.add_argument("--root", type=Path, default=ROOT)
        audit_args = audit_parser.parse_args(arguments)
        result = audit_repository_writers(audit_args.root)
        sys.stdout.buffer.write(canonical_json_bytes(result))
        return 2 if result["violations"] else 0
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
