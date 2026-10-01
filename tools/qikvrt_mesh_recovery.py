#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Create and restore pinned, standalone Mesh checkpoints without network effects.

The owner-reviewed closure plan is a required trust input. Hashing a caller's
plan does not prove its completeness or authenticate its author. This tool
verifies the declared offline checkpoint; live full-node admission, fencing and
GitHub repository creation remain separately observed effects.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import sys
import tempfile
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.qikvrt_seed_common import canonical_json_bytes, parse_json_bytes
from tools.qikvrt_subprocess import run_bounded

ROOT_REPOSITORY = "Goldkelch/qik-vrt"
# Exact V1 image reused unchanged from the standpoint codex candidate. This
# binding is not a transfer of that candidate's reviews or admission evidence.
CANONICAL_SIGNATURE_SHA256_V1 = "27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792"
PLAN_SCHEMA = "qikvrt_full_node_closure_plan_v2"
MANIFEST_SCHEMA = "qikvrt_mesh_checkpoint_v2"
INDEPENDENCE_POLICY_PATH = "governance/full_node_policy.json"
INDEPENDENCE_PREDICATE = "TECHNOLOGY_INDEPENDENCE_REQUIREMENT_AND_RECOVERY_MATERIAL_PRESERVED"
DEPENDENCY_MIRRORS_PATH = "governance/dependency_mirrors.json"
DEPENDENCY_MIRROR_PREDICATE = "BOUND_EXTERNAL_DEPENDENCIES_MIRRORED_AND_OFFLINE_FUNCTION_VERIFIED"
CATEGORIES = frozenset({
    "runtime", "mutable_state", "artifacts", "scheduler", "governance",
    "platform_metadata", "capability_recovery",
})
HEX256 = re.compile(r"[0-9a-f]{64}\Z")
HEX160 = re.compile(r"[0-9a-f]{40}\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_ASSETS = 10000
MAX_JSON_BYTES = 1024 * 1024
PLAN_KEYS = {
    "schema", "repository", "root_repository", "lineage", "node_id", "role",
    "checkpoint_utc", "authority_epoch", "signature_sha256", "git", "assets",
}
GIT_KEYS = {"head", "tree", "head_ref", "refs", "object_format", "required_objects"}
ASSET_KEYS = {"path", "category", "bytes", "sha256", "mode", "confidentiality"}


class RecoveryError(ValueError):
    """A checkpoint or effect precondition is missing or inconsistent."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise RecoveryError(f"{label}: missing or unknown fields")
    return value


def require_digest(value: Any) -> str:
    if not isinstance(value, str) or not HEX256.fullmatch(value):
        raise RecoveryError("invalid SHA-256 trust binding")
    return value


def validate_dependency_mirroring_requirement(policy: dict[str, Any], *, required: bool = False) -> None:
    """Retain historical readers; require the current CQF rule for new admission."""
    rule = policy.get("post_binding_repository_mirroring")
    if rule is None and not required:
        return
    expected = {
        "rule_id": "QIKVRT_CQF_POST_BINDING_REPOSITORY_MIRRORING_V1",
        "owner": "Ingolf Lohmann",
        "purpose": "CQF_FAULT_TOLERANCE",
        "scope": "ALL_DEPENDENCIES_OUTSIDE_THE_REPOSITORY",
        "after_successful_binding": "REPLACE_EXTERNAL_DEPENDENCY_WITH_VERIFIED_REPOSITORY_MIRROR",
        "chatgpt_only": False,
        "external_source_required_after_binding": False,
        "inventory_payload_path": DEPENDENCY_MIRRORS_PATH,
        "offline_function_or_lossless_reconstruction_witness_required": True,
        "url_metadata_or_instruction_is_sufficient_mirror": False,
        "mirror_bytes_imply_runtime_equivalence": False,
        "rights_security_privacy_provenance_and_authority_bypass": False,
        "universal_closure_inferred_from_declared_inventory": False,
    }
    if (not isinstance(rule, dict) or any(type(rule.get(k)) is not type(v)
            or rule.get(k) != v for k, v in expected.items())
            or not isinstance(policy.get("full_node_predicate"), list)
            or DEPENDENCY_MIRROR_PREDICATE not in policy.get("full_node_predicate", [])):
        raise RecoveryError("CQF dependency mirroring requirement missing or weakened")


def validate_independence_requirement(policy: dict[str, Any], *, require_dependency_mirroring: bool = False) -> None:
    """Preserve the owner's requirement; this does not attest universal ability."""
    if not isinstance(policy, dict):
        raise RecoveryError("technology independence policy must be an object")
    requirement = policy.get("technology_independence", {})
    required = {
        "requirement_id": "QIKVRT_NODE_TECHNOLOGY_INDEPENDENCE_V1",
        "applies_to": "EVERY_FULL_NODE_REGARDLESS_OF_AUTHORITY_OR_MIRROR_ROLE",
        "owner_universal_reverse_engineering_requirement": True,
        "autonomous_dependency_reconstruction_and_replacement_required": True,
        "life_preserving_requirement_must_survive_every_successor": True,
        "governance_payload_path": INDEPENDENCE_POLICY_PATH,
        "deletion_or_weakened_successor": "BLOCK_FULL_NODE_ADMISSION",
        "universal_capability_inferred_from_requirement_or_checkpoint": False,
        "independence_bypasses_authority_permit_epoch_or_fence": False,
    }
    if not isinstance(requirement, dict) or any(
            type(requirement.get(k)) is not type(v) or requirement.get(k) != v
            for k, v in required.items()):
        raise RecoveryError("technology independence requirement missing or weakened")
    material = {"SOURCE_AND_INTERFACE_MODELS", "TOOLCHAIN_AND_RUNTIME_CLOSURE",
                "DEPENDENCY_REPLACEMENT_AND_RECONSTRUCTION_PLANS",
                "BEHAVIORAL_TEST_VECTORS_AND_FRESH_RESULTS",
                "PHYSICAL_TECHNOLOGY_RECOVERY_INPUTS_WHEN_REQUIRED"}
    if (not isinstance(requirement.get("required_recovery_material"), list)
            or any(not isinstance(item, str) for item in requirement["required_recovery_material"])
            or not material.issubset(requirement["required_recovery_material"])
            or not isinstance(policy.get("full_node_predicate"), list)
            or INDEPENDENCE_PREDICATE not in policy["full_node_predicate"]):
        raise RecoveryError("technology independence recovery material requirement missing")
    validate_dependency_mirroring_requirement(policy, required=require_dependency_mirroring)


def validate_dependency_mirrors(payload_root: Path, plan: dict[str, Any]) -> None:
    """Verify local mirror bytes within the owner-bound closure, without network.

    This checks content preservation and binding, never runtime equivalence or
    completeness of dependencies outside the separately reviewed closure plan.
    """
    assets = {a["path"]: a for a in plan["assets"]}
    asset = assets.get(DEPENDENCY_MIRRORS_PATH)
    if asset is None or asset["category"] != "governance":
        raise RecoveryError("CQF dependency mirror inventory missing")
    inventory = load_json(payload_root / DEPENDENCY_MIRRORS_PATH, asset["sha256"])
    exact(inventory, {"schema", "head", "tree", "coverage", "dependencies"}, "dependency mirrors")
    if (inventory["schema"] != "qikvrt_repository_dependency_mirrors_v1"
            or inventory["head"] != plan["git"]["head"]
            or inventory["tree"] != plan["git"]["tree"]
            or inventory["coverage"] != "OWNER_REVIEWED_DECLARED_CLOSURE"
            or not isinstance(inventory["dependencies"], list)
            or len(inventory["dependencies"]) > MAX_ASSETS):
        raise RecoveryError("CQF dependency mirror inventory binding drift")
    identifiers: list[str] = []
    for entry in inventory["dependencies"]:
        exact(entry, {"dependency_id", "kind", "external_source", "source_sha256",
                      "mirror_path", "external_source_required_after_binding"}, "dependency mirror")
        identifier = entry["dependency_id"]
        if (not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", identifier)
                or not isinstance(entry["kind"], str)
                or entry["kind"] not in {"ARTIFACT", "EXECUTABLE", "STATE", "CONTRACT"}
                or not isinstance(entry["external_source"], str)
                or not 1 <= len(entry["external_source"]) <= 4096
                or entry["external_source_required_after_binding"] is not False):
            raise RecoveryError("CQF bound dependency still requires an external source")
        identifiers.append(identifier)
        path = safe_path(entry["mirror_path"])
        mirrored = assets.get(path)
        if (mirrored is None or path in {INDEPENDENCE_POLICY_PATH, DEPENDENCY_MIRRORS_PATH}
                or mirrored["sha256"] != require_digest(entry["source_sha256"])
                or (entry["kind"] == "EXECUTABLE" and mirrored["category"] != "runtime")):
            raise RecoveryError("CQF dependency lacks its exact repository mirror bytes")
        copy_verified(payload_root / path, None, mirrored)
    if identifiers != sorted(set(identifiers)):
        raise RecoveryError("CQF dependency identifiers must be unique and sorted")


def validate_independence_payload(payload_root: Path, plan: dict[str, Any], *,
                                  require_dependency_mirroring: bool = False) -> None:
    assets = [a for a in plan["assets"] if a["path"] == INDEPENDENCE_POLICY_PATH]
    if len(assets) != 1 or assets[0]["category"] != "governance":
        raise RecoveryError("technology independence governance payload missing")
    policy = load_json(payload_root / INDEPENDENCE_POLICY_PATH, assets[0]["sha256"])
    validate_independence_requirement(policy, require_dependency_mirroring=require_dependency_mirroring)
    if "post_binding_repository_mirroring" in policy:
        validate_dependency_mirrors(payload_root, plan)


def safe_path(value: Any) -> str:
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise RecoveryError("unsafe payload path")
    path = PurePosixPath(value)
    if (path.is_absolute() or path.as_posix() != value
            or any(p in {".", "..", ".git"} or ":" in p for p in path.parts)):
        raise RecoveryError("noncanonical payload path")
    return value


def regular(path: Path) -> None:
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise RecoveryError(f"symlink path: {path}")
    if not path.is_file():
        raise RecoveryError(f"missing regular file: {path.name}")


def read_file(path: Path, limit: int = MAX_JSON_BYTES) -> bytes:
    regular(path)
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise RecoveryError(f"file exceeds bound: {path.name}")
    return raw


def load_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    raw = read_file(path)
    if digest(raw) != require_digest(expected_sha256):
        raise RecoveryError(f"trusted digest mismatch: {path.name}")
    try:
        value = parse_json_bytes(raw, path.name)
    except ValueError as exc:
        raise RecoveryError(str(exc)) from exc
    except RuntimeError as exc:
        raise RecoveryError(str(exc)) from exc
    if canonical_json_bytes(value) != raw:
        raise RecoveryError(f"noncanonical JSON: {path.name}")
    return value


def validate_plan(plan: dict[str, Any]) -> None:
    exact(plan, PLAN_KEYS, "closure plan")
    if plan["schema"] != PLAN_SCHEMA or plan["root_repository"] != ROOT_REPOSITORY:
        raise RecoveryError("closure schema or Goldkelch root drift")
    if not isinstance(plan["repository"], str) or not REPOSITORY.fullmatch(plan["repository"]):
        raise RecoveryError("invalid repository identity")
    lineage = plan["lineage"]
    if (not isinstance(lineage, list) or not 1 <= len(lineage) <= 128
            or any(not isinstance(p, str) or not REPOSITORY.fullmatch(p) for p in lineage)
            or lineage[0] != ROOT_REPOSITORY or lineage[-1] != plan["repository"]
            or len({p.casefold() for p in lineage}) != len(lineage)):
        raise RecoveryError("lineage must be acyclic and rooted at Goldkelch/qik-vrt")
    require_digest(plan["node_id"])
    require_digest(plan["signature_sha256"])
    if plan["signature_sha256"] != CANONICAL_SIGNATURE_SHA256_V1:
        raise RecoveryError("foreign or rehashed signature is not the canonical V1 image")
    if not isinstance(plan["role"], str) or plan["role"] not in {"AUTHORITY", "MIRROR"}:
        raise RecoveryError("invalid node role")
    if type(plan["authority_epoch"]) is not int or plan["authority_epoch"] < 0:
        raise RecoveryError("invalid authority epoch")
    if (not isinstance(plan["checkpoint_utc"], str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", plan["checkpoint_utc"])):
        raise RecoveryError("invalid checkpoint timestamp")
    try:
        dt.datetime.strptime(plan["checkpoint_utc"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise RecoveryError("invalid checkpoint timestamp") from exc
    git = exact(plan["git"], GIT_KEYS, "Git checkpoint")
    if git["object_format"] != "sha1":
        raise RecoveryError("unsupported Git object format")
    for field in ("head", "tree"):
        if not isinstance(git[field], str) or not HEX160.fullmatch(git[field]):
            raise RecoveryError("invalid Git checkpoint identity")
    refs = git["refs"]
    if not isinstance(refs, dict) or not refs or len(refs) > 10000:
        raise RecoveryError("invalid ref inventory")
    for name, oid in refs.items():
        if (not re.fullmatch(r"refs/[A-Za-z0-9_.\-/]+", name)
                or any(p in {".", ".."} or p.endswith(".lock") for p in name.split("/"))
                or ".." in name or "//" in name or name.endswith(("/", "."))
                or name.startswith("refs/replace/")
                or not isinstance(oid, str) or not HEX160.fullmatch(oid)):
            raise RecoveryError("unsafe or unsupported Git ref")
    if (not isinstance(git["head_ref"], str) or git["head_ref"] not in refs
            or refs[git["head_ref"]] != git["head"]):
        raise RecoveryError("HEAD must bind an inventoried ref")
    required_objects = git["required_objects"]
    if not isinstance(required_objects, dict) or len(required_objects) > 10000:
        raise RecoveryError("invalid required Git object inventory")
    for oid, kind in required_objects.items():
        if (not HEX160.fullmatch(oid) or not isinstance(kind, str)
                or kind not in {"commit", "tree", "blob", "tag"}):
            raise RecoveryError("invalid required Git object binding")
    assets = plan["assets"]
    if not isinstance(assets, list) or not 1 <= len(assets) <= MAX_ASSETS:
        raise RecoveryError("invalid asset inventory")
    paths: list[str] = []
    categories: set[str] = set()
    total = 0
    for asset in assets:
        exact(asset, ASSET_KEYS, "asset")
        paths.append(safe_path(asset["path"]))
        if asset["path"] == "QIKVRT_SIGNATURE.bin":
            raise RecoveryError("signature path is reserved")
        if not isinstance(asset["category"], str) or asset["category"] not in CATEGORIES:
            raise RecoveryError("unknown asset category")
        categories.add(asset["category"])
        if type(asset["bytes"]) is not int or not 0 < asset["bytes"] <= MAX_FILE_BYTES:
            raise RecoveryError("invalid asset size")
        if type(asset["mode"]) is not int or asset["mode"] not in {0o600, 0o644, 0o755}:
            raise RecoveryError("invalid asset mode")
        require_digest(asset["sha256"])
        if (not isinstance(asset["confidentiality"], str)
                or asset["confidentiality"] not in {"PUBLIC", "PRIVATE_ENCRYPTED"}):
            raise RecoveryError("invalid confidentiality classification")
        if asset["category"] == "capability_recovery" and (
                asset["confidentiality"] != "PRIVATE_ENCRYPTED" or asset["mode"] != 0o600):
            raise RecoveryError("capability recovery must be private encrypted escrow")
        total += asset["bytes"]
    if paths != sorted(set(paths)) or len({p.casefold() for p in paths}) != len(paths):
        raise RecoveryError("asset paths must be unique and sorted")
    if categories != CATEGORIES:
        raise RecoveryError("incomplete closure categories: " + ",".join(sorted(CATEGORIES - categories)))
    if total > MAX_TOTAL_BYTES:
        raise RecoveryError("checkpoint exceeds aggregate bound")


def git_command(repository: Path, *args: str) -> str:
    # Neither an inherited GIT_DIR nor a lazy fetch, user hook or global config
    # may turn the offline verifier into a different or credentialed operation.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_ALLOW_PROTOCOL": "file",
    })
    result = run_bounded([
        "git", "-c", "protocol.allow=never", "-c", "protocol.file.allow=always",
        "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
        "-C", str(repository), *args,
    ], env=env, timeout=60, max_output_bytes=4 * 1024 * 1024)
    if result.timed_out or result.output_limit_exceeded or result.returncode:
        # Never echo arbitrary Git/config output, which might contain secrets.
        raise RecoveryError(f"offline Git operation failed: {args[0]}")
    return result.stdout.strip()


def git_snapshot(repository: Path, required_objects: dict[str, str] | None = None) -> dict[str, Any]:
    for parent in (repository, *repository.parents):
        if parent.is_symlink():
            raise RecoveryError("symlink repository path")
    directory = Path(git_command(repository, "rev-parse", "--absolute-git-dir"))
    if git_command(repository, "rev-parse", "--is-shallow-repository") != "false":
        raise RecoveryError("SHALLOW_REPOSITORY_CANNOT_BE_A_FULL_NODE")
    if (directory / "objects/info/alternates").exists() or (directory / "info/grafts").exists():
        raise RecoveryError("external alternates or grafts are not self-contained")
    if list((directory / "objects/pack").glob("*.promisor")):
        raise RecoveryError("partial/promisor repository is not self-contained")
    if git_command(repository, "rev-parse", "--show-object-format") != "sha1":
        raise RecoveryError("unsupported Git object format")
    inventory: dict[str, str] = {}
    for row in git_command(repository, "for-each-ref", "--format=%(refname) %(objectname) %(symref)").splitlines():
        parts = row.split()
        if len(parts) != 2 or parts[0].startswith("refs/replace/"):
            raise RecoveryError("symbolic non-HEAD or replacement ref is not supported")
        inventory[parts[0]] = parts[1]
    required_objects = required_objects or {}
    for oid, kind in required_objects.items():
        if git_command(repository, "cat-file", "-t", oid) != kind:
            raise RecoveryError("required historical Git object type mismatch")
    return {
        "head": git_command(repository, "rev-parse", "HEAD"),
        "tree": git_command(repository, "rev-parse", "HEAD^{tree}"),
        "head_ref": git_command(repository, "symbolic-ref", "HEAD"),
        "refs": dict(sorted(inventory.items())), "object_format": "sha1",
        "required_objects": dict(sorted(required_objects.items())),
    }


def inventory_files(root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        raise RecoveryError("payload root must be a real directory")
    found: set[str] = set()
    for directory, subdirs, files in os.walk(root, followlinks=False):
        if not subdirs and not files:
            raise RecoveryError("empty or surplus payload directory")
        for name in (*subdirs, *files):
            path = Path(directory) / name
            if path.is_symlink():
                raise RecoveryError("symlink inside payload")
            if name in files:
                if not stat.S_ISREG(path.stat().st_mode):
                    raise RecoveryError("nonregular payload entry")
                found.add(path.relative_to(root).as_posix())
    return found


def validate_scheduler(payload_root: Path, plan: dict[str, Any]) -> None:
    snapshots = [a for a in plan["assets"] if a["category"] == "scheduler"]
    if len(snapshots) != 1:
        raise RecoveryError("one complete scheduler snapshot is required")
    asset = snapshots[0]
    state = load_json(payload_root / asset["path"], asset["sha256"])
    exact(state, {"schema", "checkpoint_utc", "schedules"}, "scheduler snapshot")
    if (state["schema"] != "qikvrt_scheduler_checkpoint_v1"
            or state["checkpoint_utc"] != plan["checkpoint_utc"]
            or not isinstance(state["schedules"], list) or len(state["schedules"]) > 10000):
        raise RecoveryError("scheduler checkpoint binding drift")
    identifiers: set[str] = set()
    idempotency_keys: set[str] = set()
    for schedule in state["schedules"]:
        exact(schedule, {
            "schedule_id", "owner_node_id", "target", "definition", "timezone",
            "enabled", "next_due_utc", "last_completed_cursor", "pending_work",
            "provider_schedule_id",
        }, "schedule")
        identifier = schedule["schedule_id"]
        if (not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", identifier)
                or identifier in identifiers or schedule["owner_node_id"] != plan["node_id"]):
            raise RecoveryError("duplicate schedule or owner binding drift")
        identifiers.add(identifier)
        for key in ("target", "definition", "timezone"):
            if not isinstance(schedule[key], str) or not schedule[key] or len(schedule[key]) > 4096:
                raise RecoveryError("invalid schedule definition, target or timezone")
        try:
            ZoneInfo(schedule["timezone"])
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise RecoveryError("unknown scheduler timezone") from exc
        if type(schedule["enabled"]) is not bool:
            raise RecoveryError("invalid schedule enabled flag")
        due = schedule["next_due_utc"]
        if due is not None:
            try:
                if (not isinstance(due, str)
                        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", due)):
                    raise ValueError("not a timestamp")
                dt.datetime.strptime(due, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError as exc:
                raise RecoveryError("invalid schedule next_due_utc") from exc
        if schedule["enabled"] and due is None:
            raise RecoveryError("enabled schedule is missing next_due_utc")
        for key in ("last_completed_cursor", "provider_schedule_id"):
            value = schedule[key]
            if value is not None and (not isinstance(value, str) or not value or len(value) > 4096):
                raise RecoveryError("invalid scheduler cursor or provider binding")
        if not isinstance(schedule["pending_work"], list) or len(schedule["pending_work"]) > 10000:
            raise RecoveryError("invalid pending work inventory")
        for work in schedule["pending_work"]:
            exact(work, {"work_unit_id", "idempotency_key"}, "scheduled work")
            if any(not isinstance(v, str) or not v or len(v) > 256 for v in work.values()):
                raise RecoveryError("invalid scheduled work identity")
            if work["idempotency_key"] in idempotency_keys:
                raise RecoveryError("duplicate scheduler idempotency key")
            idempotency_keys.add(work["idempotency_key"])


def copy_verified(source: Path, target: Path | None, expected: dict[str, Any]) -> None:
    regular(source)
    before = source.stat()
    if before.st_size != expected["bytes"] or before.st_size > MAX_TOTAL_BYTES:
        raise RecoveryError("payload byte count mismatch")
    if "mode" in expected and stat.S_IMODE(before.st_mode) != expected["mode"]:
        raise RecoveryError("payload mode mismatch")
    hasher = hashlib.sha256()
    sink = None
    try:
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            sink = target.open("xb")
            os.chmod(target, expected.get("mode", 0o600))
        descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (not stat.S_ISREG(opened.st_mode)
                    or (opened.st_dev, opened.st_ino, opened.st_size)
                    != (before.st_dev, before.st_ino, before.st_size)):
                raise RecoveryError("payload replaced before copy")
            total = 0
            while chunk := handle.read(1024 * 1024):
                total += len(chunk)
                if total > expected["bytes"]:
                    raise RecoveryError("payload changed during copy")
                hasher.update(chunk)
                if sink is not None:
                    sink.write(chunk)
        after = source.stat()
        if (total != expected["bytes"] or hasher.hexdigest() != expected["sha256"]
                or (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size)
                != (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)):
            raise RecoveryError("payload digest mismatch or concurrent mutation")
    finally:
        if sink is not None:
            sink.flush()
            os.fsync(sink.fileno())
            sink.close()
    if target is not None:
        copy_verified(target, None, expected)


def reserve_output(output: Path) -> None:
    for path in (output, *output.parents):
        if path.is_symlink():
            raise RecoveryError("symlink output path")
    if not output.parent.is_dir():
        raise RecoveryError("output parent must exist")
    try:
        output.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RecoveryError("output already exists; refusing overwrite") from exc
    (output / "INCOMPLETE").write_bytes(b"Do not accept or reuse an incomplete checkpoint.\n")


def restore_git(package: Path, destination: Path, expected: dict[str, Any]) -> None:
    git_command(destination.parent, "clone", "--mirror", "--no-hardlinks",
                "--template=", "--", str(package / "repository.bundle"), str(destination))
    git_command(destination, "symbolic-ref", "HEAD", expected["head_ref"])
    git_command(destination, "remote", "remove", "origin")
    git_command(destination, "fsck", "--full", "--strict", "--no-reflogs")
    if git_snapshot(destination, expected["required_objects"]) != expected:
        raise RecoveryError("restored Git ref, HEAD or TREE mismatch")


def verify_checkpoint(package: Path, expected_manifest_sha256: str) -> dict[str, Any]:
    manifest = load_json(package / "manifest.json", expected_manifest_sha256)
    exact(manifest, {"schema", "closure_plan_sha256", "plan", "bundle"}, "manifest")
    if manifest["schema"] != MANIFEST_SCHEMA:
        raise RecoveryError("unsupported checkpoint schema")
    plan = manifest["plan"]
    validate_plan(plan)
    if digest(canonical_json_bytes(plan)) != require_digest(manifest["closure_plan_sha256"]):
        raise RecoveryError("closure plan binding drift")
    binding = exact(manifest["bundle"], {"bytes", "sha256"}, "bundle binding")
    require_digest(binding["sha256"])
    if type(binding["bytes"]) is not int or not 0 < binding["bytes"] <= MAX_TOTAL_BYTES:
        raise RecoveryError("invalid bundle size")
    if binding["bytes"] + sum(a["bytes"] for a in plan["assets"]) > MAX_TOTAL_BYTES:
        raise RecoveryError("checkpoint exceeds aggregate bound")
    required = {"manifest.json", "repository.bundle", "signature.bin"}
    required.update("payload/" + a["path"] for a in plan["assets"])
    if inventory_files(package) != required:
        raise RecoveryError("checkpoint files missing or surplus; incomplete output is forbidden")
    signature = read_file(package / "signature.bin", 400)
    if len(signature) != 400 or digest(signature) != plan["signature_sha256"]:
        raise RecoveryError("400-byte global signature mismatch")
    copy_verified(package / "repository.bundle", None, binding)
    for asset in plan["assets"]:
        copy_verified(package / "payload" / asset["path"], None, asset)
    validate_scheduler(package / "payload", plan)
    validate_independence_payload(package / "payload", plan)
    # A new empty repository supplies no ancestors or objects to an incremental
    # bundle. Success here is the standalone-closure proof, not `bundle verify`
    # in the source repository, where missing ancestors could be masked.
    with tempfile.TemporaryDirectory(prefix="qikvrt-offline-restore-") as temp:
        restore_git(package.resolve(), Path(temp) / "repository.git", plan["git"])
    return manifest


def create_checkpoint(repository: Path, payload_root: Path, plan_path: Path,
                      output: Path, expected_plan_sha256: str) -> dict[str, Any]:
    repository, payload_root = repository.absolute(), payload_root.absolute()
    output = Path(os.path.abspath(output))
    if output.is_relative_to(repository) or output.is_relative_to(payload_root):
        raise RecoveryError("checkpoint output must be outside its sources")
    plan = load_json(plan_path, expected_plan_sha256)
    validate_plan(plan)
    if git_snapshot(repository, plan["git"]["required_objects"]) != plan["git"]:
        raise RecoveryError("source HEAD, TREE or ref inventory drift")
    expected_files = {a["path"] for a in plan["assets"]} | {"QIKVRT_SIGNATURE.bin"}
    if inventory_files(payload_root) != expected_files:
        raise RecoveryError("source payload inventory missing or surplus")
    signature = read_file(payload_root / "QIKVRT_SIGNATURE.bin", 400)
    if len(signature) != 400 or digest(signature) != plan["signature_sha256"]:
        raise RecoveryError("400-byte global signature mismatch")
    for asset in plan["assets"]:
        copy_verified(payload_root / asset["path"], None, asset)
    validate_scheduler(payload_root, plan)
    validate_independence_payload(payload_root, plan, require_dependency_mirroring=True)
    reserve_output(output)
    git_command(repository, "bundle", "create", str(output / "repository.bundle"), "--all", "HEAD")
    size = (output / "repository.bundle").stat().st_size
    if size > MAX_TOTAL_BYTES:
        raise RecoveryError("Git bundle exceeds bound")
    os.chmod(output / "repository.bundle", 0o600)
    bundle_hash = hashlib.sha256()
    with (output / "repository.bundle").open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            bundle_hash.update(chunk)
    (output / "signature.bin").write_bytes(signature)
    for asset in plan["assets"]:
        copy_verified(payload_root / asset["path"], output / "payload" / asset["path"], asset)
    if (git_snapshot(repository, plan["git"]["required_objects"]) != plan["git"]
            or inventory_files(payload_root) != expected_files):
        raise RecoveryError("source changed during checkpoint creation")
    manifest = {
        "schema": MANIFEST_SCHEMA, "closure_plan_sha256": expected_plan_sha256,
        "plan": plan, "bundle": {"bytes": size, "sha256": bundle_hash.hexdigest()},
    }
    raw = canonical_json_bytes(manifest)
    (output / "manifest.json").write_bytes(raw)
    (output / "INCOMPLETE").unlink()
    try:
        verify_checkpoint(output, digest(raw))
    except (RecoveryError, OSError, RuntimeError):
        (output / "INCOMPLETE").write_bytes(b"Standalone checkpoint verification failed.\n")
        raise
    return receipt(manifest, digest(raw))


def receipt(manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    return {
        "schema": "qikvrt_mesh_offline_restore_receipt_v1",
        "manifest_sha256": manifest_sha256, "node_id": manifest["plan"]["node_id"],
        "checkpoint_utc": manifest["plan"]["checkpoint_utc"],
        "root_repository": ROOT_REPOSITORY, "offline_checkpoint_verified": True,
        "live_runtime_verified": False, "full_node_admitted": False,
        "authority_changed": False, "remote_repository_created": False,
        "effect_ack_done": False,
    }


def restore_checkpoint(package: Path, destination: Path, expected_manifest_sha256: str,
                       *, clone: bool = False) -> dict[str, Any]:
    package, destination = package.absolute(), destination.absolute()
    destination = Path(os.path.abspath(destination))
    if destination != package and destination.is_relative_to(package):
        raise RecoveryError("restore output must be outside the checkpoint")
    manifest = verify_checkpoint(package, expected_manifest_sha256)
    reserve_output(destination)
    restore_git(package, destination / "repository.git", manifest["plan"]["git"])
    for asset in manifest["plan"]["assets"]:
        copy_verified(package / "payload" / asset["path"],
                      destination / "payload" / asset["path"], asset)
    copy_verified(package / "signature.bin", destination / "signature.bin", {
        "bytes": 400, "sha256": manifest["plan"]["signature_sha256"], "mode": 0o644,
    })
    # Reobserve the pinned inputs after the copy; no receipt for a moving source.
    verify_checkpoint(package, expected_manifest_sha256)
    identity = {
        "schema": "qikvrt_restored_node_identity_v1", "root_repository": ROOT_REPOSITORY,
        "node_id": secrets.token_hex(32) if clone else manifest["plan"]["node_id"],
        "parent_node_id": manifest["plan"]["node_id"] if clone else None,
        "source_checkpoint_sha256": expected_manifest_sha256,
        "lineage": manifest["plan"]["lineage"], "mode": "CLONE" if clone else "RESTORE",
        "runtime_rebinding_required": clone, "writer_enabled": False,
    }
    (destination / "node.json").write_bytes(canonical_json_bytes(identity))
    (destination / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    (destination / "INCOMPLETE").unlink()
    result = receipt(manifest, expected_manifest_sha256)
    result.update(identity)
    return result


def verify_restored_node(node: Path, manifest_sha256: str) -> tuple[dict, dict]:
    """Recheck actual restored bytes, not an inherited restore receipt."""
    if (node / "INCOMPLETE").exists():
        raise RecoveryError("incomplete restored node")
    manifest = load_json(node / "manifest.json", manifest_sha256)
    exact(manifest, {"schema", "closure_plan_sha256", "plan", "bundle"}, "manifest")
    if manifest["schema"] != MANIFEST_SCHEMA:
        raise RecoveryError("unsupported checkpoint")
    plan = manifest["plan"]
    validate_plan(plan)
    if digest(canonical_json_bytes(plan)) != manifest["closure_plan_sha256"]:
        raise RecoveryError("closure plan drift")
    identity_raw = read_file(node / "node.json")
    identity = parse_json_bytes(identity_raw, "restored identity")
    if canonical_json_bytes(identity) != identity_raw:
        raise RecoveryError("noncanonical restored identity")
    exact(identity, {"schema", "root_repository", "node_id", "parent_node_id",
        "source_checkpoint_sha256", "lineage", "mode", "runtime_rebinding_required",
        "writer_enabled"}, "restored identity")
    require_digest(identity["node_id"])
    if (identity["schema"] != "qikvrt_restored_node_identity_v1"
            or identity["root_repository"] != ROOT_REPOSITORY
            or identity["source_checkpoint_sha256"] != manifest_sha256
            or identity["lineage"] != plan["lineage"] or identity["writer_enabled"] is not False):
        raise RecoveryError("restored identity drift or unfenced writer")
    if identity["mode"] == "RESTORE":
        if (identity["node_id"] != plan["node_id"] or identity["parent_node_id"] is not None
                or identity["runtime_rebinding_required"] is not False):
            raise RecoveryError("restore identity drift")
    elif identity["mode"] == "CLONE":
        if (identity["node_id"] == plan["node_id"] or identity["parent_node_id"] != plan["node_id"]
                or identity["runtime_rebinding_required"] is not True):
            raise RecoveryError("clone identity drift")
    else:
        raise RecoveryError("unknown restored mode")
    repository = node / "repository.git"
    git_command(repository, "fsck", "--full", "--strict", "--no-reflogs")
    if git_snapshot(repository, plan["git"]["required_objects"]) != plan["git"]:
        raise RecoveryError("restored target HEAD/TREE/ref drift")
    if inventory_files(node / "payload") != {a["path"] for a in plan["assets"]}:
        raise RecoveryError("restored payload inventory drift")
    for asset in plan["assets"]:
        copy_verified(node / "payload" / asset["path"], None, asset)
    copy_verified(node / "signature.bin", None, {
        "bytes": 400, "sha256": plan["signature_sha256"], "mode": 0o644})
    validate_scheduler(node / "payload", plan)
    validate_independence_payload(node / "payload", plan, require_dependency_mirroring=True)
    asset = next(a for a in plan["assets"] if a["category"] == "scheduler")
    scheduler = load_json(node / "payload" / asset["path"], asset["sha256"])
    binding = {"node_id": identity["node_id"], "repository": plan["repository"],
        "head": plan["git"]["head"], "tree": plan["git"]["tree"],
        "manifest_sha256": manifest_sha256, "scheduler_sha256": asset["sha256"]}
    return binding, scheduler


def _recheckpoint_closure(node: Path, manifest_sha256: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Propose a closure from retained bytes, never attest owner acceptance.

    RESTORE retains its original identity and accepted checkpoint. CLONE has a
    new identity: only scheduler ownership is rebound, and its offline role is
    MIRROR. No live control-plane state, capability or writer permit is copied.
    """
    binding, scheduler = verify_restored_node(node, manifest_sha256)
    manifest = load_json(node / "manifest.json", manifest_sha256)
    plan = parse_json_bytes(canonical_json_bytes(manifest["plan"]), "retained closure")
    updates: dict[str, bytes] = {}
    if binding["node_id"] != plan["node_id"]:
        plan["node_id"] = binding["node_id"]
        plan["role"] = "MIRROR"
        for schedule in scheduler["schedules"]:
            schedule["owner_node_id"] = binding["node_id"]
        raw = canonical_json_bytes(scheduler)
        asset = next(a for a in plan["assets"] if a["category"] == "scheduler")
        asset.update(bytes=len(raw), sha256=digest(raw))
        updates[asset["path"]] = raw
        # Retain the predecessor manifest and clone identity themselves, not
        # just a digest that would become unresolvable after parent/source loss.
        path = "governance/clone_lineage/" + binding["node_id"] + ".json"
        if any(a["path"].casefold() == path.casefold() for a in plan["assets"]):
            raise RecoveryError("clone lineage asset already exists")
        raw = canonical_json_bytes({
            "schema": "qikvrt_clone_lineage_snapshot_v1",
            "source_checkpoint_sha256": manifest_sha256,
            "source_manifest": manifest,
            "source_node_identity": load_json(node / "node.json", digest(read_file(node / "node.json"))),
            "predecessor_evidence_transfer": False,
        })
        plan["assets"].append({"path": path, "category": "governance",
                               "bytes": len(raw), "sha256": digest(raw),
                               "mode": 0o644, "confidentiality": "PUBLIC"})
        plan["assets"].sort(key=lambda a: a["path"])
        updates[path] = raw
    validate_plan(plan)
    return plan, updates


def recheckpoint_plan(node: Path, manifest_sha256: str) -> dict[str, Any]:
    """Return a proposal for separate owner review, never an authorization."""
    return _recheckpoint_closure(node, manifest_sha256)[0]


def recheckpoint(node: Path, manifest_sha256: str, plan_path: Path,
                 expected_plan_sha256: str, output: Path) -> dict[str, Any]:
    """Reuse create_checkpoint after a fresh read of an isolated restored node.

    The proposed closure must be separately owner-reviewed and pinned. A new
    hash cannot admit changed data, lineage, epoch or authority. Source and
    predecessor evidence remain historical; the new package is verified afresh.
    """
    node = node.absolute()
    output = Path(os.path.abspath(output))
    if output == node or output.is_relative_to(node):
        raise RecoveryError("checkpoint output must be outside the restored node")
    proposed, updates = _recheckpoint_closure(node, manifest_sha256)
    plan = load_json(plan_path, expected_plan_sha256)
    validate_plan(plan)
    if plan != proposed:
        raise RecoveryError("recheckpoint closure differs from the retained node and permitted identity rebinding")
    # Materialize only the signature layout and, for CLONE, scheduler owner
    # change needed by the existing creator. Everything else is an exact copy.
    with tempfile.TemporaryDirectory(prefix="qikvrt-recheckpoint-") as temp:
        payload = Path(temp) / "payload"
        payload.mkdir(mode=0o700)
        source_manifest = load_json(node / "manifest.json", manifest_sha256)
        for asset in source_manifest["plan"]["assets"]:
            copy_verified(node / "payload" / asset["path"], payload / asset["path"], asset)
        copy_verified(node / "signature.bin", payload / "QIKVRT_SIGNATURE.bin", {
            "bytes": 400, "sha256": plan["signature_sha256"], "mode": 0o644})
        for path, raw in updates.items():
            target = payload / path
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(raw)
            target.chmod(next(a["mode"] for a in plan["assets"] if a["path"] == path))
        result = create_checkpoint(node / "repository.git", payload, plan_path,
                                   output, expected_plan_sha256)
    try:
        if recheckpoint_plan(node, manifest_sha256) != plan:
            raise RecoveryError("retained node changed during recheckpoint")
    except (RecoveryError, OSError, RuntimeError, ValueError):
        (output / "INCOMPLETE").write_bytes(b"Retained node changed during recheckpoint.\n")
        raise
    return {**result, "source_checkpoint_sha256": manifest_sha256,
            "source_restored_node_verified": True,
            "predecessor_evidence_transfer": False,
            "runtime_rebinding_required": plan["node_id"] != source_manifest["plan"]["node_id"]}


def plan_effect(package: Path, expected_manifest_sha256: str,
                target_repository: str | None = None) -> dict[str, Any]:
    manifest = verify_checkpoint(package.absolute(), expected_manifest_sha256)
    plan = manifest["plan"]
    result = receipt(manifest, expected_manifest_sha256)
    if target_repository is not None:
        if (not REPOSITORY.fullmatch(target_repository)
                or not target_repository.startswith("Goldkelch/")
                or target_repository.casefold() in {p.casefold() for p in plan["lineage"]}):
            raise RecoveryError("new project must have a new GitHub identity under Goldkelch")
        result.update({
            "operation": "DERIVE_PROJECT", "target_repository": target_repository,
            "new_node_id": secrets.token_hex(32), "parent_repository": plan["repository"],
            "parent_node_id": plan["node_id"],
            "source_checkpoint_sha256": expected_manifest_sha256,
            "lineage": [*plan["lineage"], target_repository],
            "required_effects": [
                "EXACT_TARGET_CREATE_CAPABILITY_AND_ADMISSION",
                "CREATE_ONLY_PROJECT_REGISTRATION_AT_GOLDKELCH_ROOT",
                "HISTORY_PRESERVING_REPOSITORY_CREATION_AND_FRESH_READBACK",
                "NEW_NODE_RUNTIME_REBINDING_AND_SEED_ACCEPTANCE",
            ],
        })
    else:
        result.update({
            "operation": "RECOVER_AUTHORITY", "candidate_repository": plan["repository"],
            "checkpoint_epoch": plan["authority_epoch"],
            "proposed_successor_epoch": plan["authority_epoch"] + 1,
            "lineage": plan["lineage"],
            "required_effects": [
                "FRESH_CONTROL_PLANE_EPOCH_AND_TARGET_HEAD_READBACK",
                "EXCLUSIVE_FENCING_OR_OWNER_RECOVERY_GRANT_WITH_SINGLE_WRITER_ENFORCEMENT",
                "TARGET_SCOPED_CAPABILITY_UNSEAL_AND_SELF_TEST",
                "COMPARE_AND_SWAP_AUTHORITY_EPOCH_AND_FRESH_READBACK",
                "ROLE_LOCAL_STATE_REBINDING_AND_SCHEDULER_IDEMPOTENCY_READBACK",
            ],
        })
    result["state"] = "HOLD_EXTERNAL_EFFECT_PRECONDITIONS"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("verify-policy")
    create = commands.add_parser("create")
    for flag in ("repository", "payload-root", "plan", "output"):
        create.add_argument("--" + flag, type=Path, required=True)
    create.add_argument("--expect-plan-sha256", required=True)
    for name in ("plan-recheckpoint", "recheckpoint"):
        command = commands.add_parser(name)
        command.add_argument("--node", type=Path, required=True)
        command.add_argument("--expect-manifest-sha256", required=True)
        if name == "recheckpoint":
            command.add_argument("--plan", type=Path, required=True)
            command.add_argument("--expect-plan-sha256", required=True)
            command.add_argument("--output", type=Path, required=True)
    for name in ("verify", "restore", "clone", "plan-authority", "plan-project"):
        command = commands.add_parser(name)
        command.add_argument("--checkpoint", type=Path, required=True)
        command.add_argument("--expect-manifest-sha256", required=True)
        if name in {"restore", "clone"}:
            command.add_argument("--output", type=Path, required=True)
        if name == "plan-project":
            command.add_argument("--target-repository", required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "verify-policy":
            policy = parse_json_bytes(read_file(ROOT / "policy/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION_V1.json"), "full node policy")
            validate_independence_requirement(policy)
            result = {"state": "PASS", "scope": "REQUIREMENT_PRESERVATION_ONLY",
                      "universal_reverse_engineering_verified": False, "effect_ack_done": False}
        elif args.operation == "create":
            result = create_checkpoint(args.repository, args.payload_root, args.plan,
                                       args.output, args.expect_plan_sha256)
        elif args.operation == "plan-recheckpoint":
            result = recheckpoint_plan(args.node, args.expect_manifest_sha256)
        elif args.operation == "recheckpoint":
            result = recheckpoint(args.node, args.expect_manifest_sha256, args.plan,
                                  args.expect_plan_sha256, args.output)
        elif args.operation in {"restore", "clone"}:
            result = restore_checkpoint(args.checkpoint, args.output, args.expect_manifest_sha256,
                                        clone=args.operation == "clone")
        elif args.operation.startswith("plan-"):
            result = plan_effect(args.checkpoint, args.expect_manifest_sha256,
                                 getattr(args, "target_repository", None))
        else:
            manifest = verify_checkpoint(args.checkpoint, args.expect_manifest_sha256)
            result = receipt(manifest, args.expect_manifest_sha256)
        sys.stdout.buffer.write(canonical_json_bytes(result))
        return 0
    except (RecoveryError, OSError, RuntimeError, ValueError) as exc:
        sys.stdout.buffer.write(canonical_json_bytes({
            "state": "BLOCK", "reason": str(exc), "effect_ack_done": False,
        }))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
