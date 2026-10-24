#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Offline, role-neutral full-node snapshots, recovery and isolated genesis.

Only persisted reachable Git bytes are reconstructed. Platform capabilities
and current-head gate results are never inferred from a recovered snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import qikvrt_integrity as integrity
from tools.qikvrt_subprocess import run_bounded

SCHEMA = "qikvrt_full_node_snapshot_v1"
BINDING = "policy/QIKVRT_NODE_BINDING_V1.json"
REMOTE_POLICY = "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
HIERARCHY_ROOT = "Goldkelch/qik-vrt"
KINDS = ("RECOVERY_AUTHORITY", "MIRROR", "CHILD")
REBIND = [
    "AUTHENTICATED_PRINCIPAL_AND_SCOPED_CREDENTIALS",
    "GITHUB_REPOSITORY_CREATION_AND_NAMESPACE_RIGHTS",
    "BRANCH_RULESETS_CODEOWNER_REVIEW_AND_WORKFLOW_ADMISSION",
    "SECRETS_OAUTH_BIOMETRIC_SIGNING_AND_DEPLOYMENT_BINDINGS",
    "EXTERNAL_PAYLOADS_SERVICES_AND_PUBLIC_URL_READBACK",
    "OLD_AUTHORITY_FENCING_AND_CURRENT_MESH_ADMISSION",
]
MAX_BUNDLE_BYTES = 1024 * 1024 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GenesisBlock(RuntimeError):
    """Incomplete, corrupt, stale or unbound recovery input."""


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GenesisBlock(message)


def git(root: Path, *args: str, extra_env: dict[str, str] | None = None,
        optional: bool = False) -> str:
    # Do not import credentials, lazy-fetch, replace objects, hooks, filters or
    # global Git configuration into the offline reconstruction boundary.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
                "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0",
                "LC_ALL": "C"})
    if extra_env:
        env.update(extra_env)
    result = run_bounded(
        ("git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false",
         "-c", "transfer.fsckObjects=true", "-C", str(root), *args),
        env=env, timeout=180, max_output_bytes=16 * 1024 * 1024,
    )
    require(not result.timed_out and not result.output_limit_exceeded,
            "Git time/output bound exceeded")
    if result.returncode:
        if optional and result.returncode == 1:
            return ""
        raise GenesisBlock(f"Git {args[0]} failed: {result.stderr[:2000]}")
    return result.stdout


def digest_file(path: Path, limit: int) -> tuple[int, str]:
    require(path.is_file() and not path.is_symlink(), f"missing/unsafe file: {path.name}")
    require(path.stat().st_size <= limit, f"oversized file: {path.name}")
    digest = hashlib.sha256()
    total = 0
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), "snapshot member must be a regular file")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(chunk)
            require(total <= limit, "file grew beyond bound")
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    require((before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns) and total == before.st_size,
            "file changed during verification")
    return total, digest.hexdigest()


def load_json(path: Path, *, canonical_required: bool = False) -> dict[str, Any]:
    digest_file(path, MAX_METADATA_BYTES)
    raw = integrity._regular_file_bytes(path.parent, path.name, max_bytes=MAX_METADATA_BYTES)

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            require(key not in value, "duplicate JSON field")
            value[key] = item
        return value

    try:
        value = json.loads(raw, object_pairs_hook=unique)
        require(isinstance(value, dict), "JSON must be an object")
        if canonical_required:
            require(raw == canonical(value), "noncanonical JSON bytes")
        return value
    except (ValueError, UnicodeError) as exc:
        raise GenesisBlock("invalid JSON") from exc


def new_path(path: Path) -> Path:
    path = path.absolute()
    require(path.parent.is_dir(), "destination parent must exist")
    require(not any(p.is_symlink() for p in (path, *path.parents)),
            "symlink destination component")
    require(not path.exists(), "destination already exists")
    return path


def fresh_integrity(root: Path) -> str:
    result = integrity.verify(root)
    require(result.ok, "fresh repository integrity failed: " + result.message)
    return digest_file(root / integrity.MANIFEST_NAME, integrity.MAX_INTEGRITY_METADATA_BYTES)[1]


def observe(root: Path) -> dict[str, Any]:
    require(root.is_dir() and not root.is_symlink(), "unsafe repository root")
    require(git(root, "rev-parse", "--is-bare-repository").strip() == "false",
            "checked-out full node required")
    require(git(root, "rev-parse", "--is-shallow-repository").strip() == "false",
            "shallow node cannot reconstruct full history")
    gitdir = Path(git(root, "rev-parse", "--absolute-git-dir").strip())
    for path in ("shallow", "info/grafts", "objects/info/alternates", "objects/info/http-alternates"):
        require(not (gitdir / path).exists(), "external/incomplete object store: " + path)
    partial = git(root, "config", "--get-regexp",
                  r"^(extensions\.partialclone|remote\..*\.(promisor|partialclonefilter))$",
                  optional=True)
    require(not partial, "partial/promisor clone is not a complete node")
    require(not list((gitdir / "objects/pack").glob("*.promisor")),
            "promisor object packs cannot establish full-node closure")
    require(not git(root, "status", "--porcelain", "--untracked-files=all").strip(),
            "persist dirty/untracked repository bytes before snapshot/recovery")
    head = git(root, "rev-parse", "--verify", "HEAD^{commit}").strip()
    tree = git(root, "rev-parse", "--verify", "HEAD^{tree}").strip()
    symbol = git(root, "symbolic-ref", "-q", "HEAD", optional=True).strip() or None
    refs = []
    for line in git(root, "for-each-ref", "--sort=refname",
                    "--format=%(refname)%09%(objectname)%09%(symref)").splitlines():
        name, oid, symref = line.split("\t")
        require(not name.startswith("refs/replace/"), "replace refs cannot redefine history")
        refs.append({"name": name, "oid": oid, "symbolic_ref": symref or None})
    require(len(refs) <= 10000, "ref inventory exceeds bound")
    # gitlinks are references to another repository, not its persisted bytes.
    paths = git(root, "ls-tree", "-r", "--full-tree", "HEAD").splitlines()
    require(not any(line.startswith("160000 ") for line in paths),
            "external gitlink payload requires separate materialization")
    git(root, "fsck", "--full", "--strict", "--no-reflogs", "--no-dangling")
    objects = sorted(set(git(root, "rev-list", "--objects", "--all", "HEAD",
                            "--no-object-names").splitlines()))
    require(all(SHA1.fullmatch(oid) for oid in objects), "unsupported Git object format")
    stored = sorted(set(git(root, "cat-file", "--batch-all-objects",
                           "--batch-check=%(objectname)").splitlines()))
    require(stored == objects,
            "pin unreachable/reflog-only persisted objects with retention refs before full-node export")
    return {"head": head, "tree": tree, "head_symbolic_ref": symbol, "refs": refs,
            "reachable_objects": len(objects),
            "object_inventory_sha256": hashlib.sha256(canonical(objects)).hexdigest(),
            "repository_manifest_sha256": fresh_integrity(root)}


def lineage(root: Path, repository: str) -> dict[str, Any]:
    require(bool(REPOSITORY.fullmatch(repository)), "invalid repository identity")
    if (root / BINDING).exists():
        binding = load_json(root / BINDING, canonical_required=True)
        require(binding.get("schema") == "qikvrt_node_binding_v1" and
                binding.get("repository") == repository and
                binding.get("hierarchy_root") == HIERARCHY_ROOT,
                "node ancestry/repository mismatch")
        chain = binding.get("ancestry")
        authority = binding.get("authority_repository")
        epoch = binding.get("authority_epoch")
    else:
        policy = load_json(root / REMOTE_POLICY)
        declared = [policy.get(key, {}).get("repository") for key in
                    ("canonical_upstream", "mirror") if isinstance(policy.get(key), dict)]
        require(repository in declared, "source repository lacks persisted identity binding")
        chain = [HIERARCHY_ROOT] if repository == HIERARCHY_ROOT else [HIERARCHY_ROOT, repository]
        authority = policy["canonical_upstream"]["repository"]
        epoch = 0
    require(isinstance(chain, list) and chain and chain[0] == HIERARCHY_ROOT and
            chain[-1] == repository and len(chain) == len(set(chain)) and
            all(isinstance(item, str) and REPOSITORY.fullmatch(item) for item in chain),
            "invalid Goldkelch ancestry chain")
    require(isinstance(authority, str) and REPOSITORY.fullmatch(authority) is not None and
            type(epoch) is int and epoch >= 0, "invalid authority ancestry")
    return {"hierarchy_root": HIERARCHY_ROOT, "ancestry": chain,
            "authority_repository": authority, "authority_epoch": epoch}


def export_snapshot(root: Path, destination: Path, repository: str) -> str:
    destination = new_path(destination)
    require(root.resolve() not in destination.parents, "snapshot must reside outside source tree")
    before = observe(root)
    ancestry = lineage(root, repository)
    with tempfile.TemporaryDirectory(prefix=".qikvrt-snapshot-", dir=destination.parent) as directory:
        stage = Path(directory) / "snapshot"
        stage.mkdir()
        git(root, "bundle", "create", "--quiet", "--version=2",
            str(stage / "node.bundle"), "--all", "HEAD")
        size, bundle_sha = digest_file(stage / "node.bundle", MAX_BUNDLE_BYTES)
        require(observe(root) == before, "source refs/tree changed during export")
        manifest = {"schema": SCHEMA, "repository": repository, "git_object_format": "sha1",
                    "subject": before, "lineage": ancestry,
                    "bundle": {"path": "node.bundle", "bytes": size, "sha256": bundle_sha},
                    "capabilities_to_rebind": REBIND, "predecessor_evidence_transfer": False}
        raw = canonical(manifest)
        require(len(raw) <= MAX_METADATA_BYTES, "snapshot metadata exceeds bound")
        snapshot_sha = hashlib.sha256(raw).hexdigest()
        (stage / "snapshot.json").write_bytes(raw)
        (stage / "snapshot.sha256").write_text(snapshot_sha + "\n", encoding="ascii")
        stage.rename(destination)
    return snapshot_sha


def read_snapshot(snapshot: Path, expected_sha256: str) -> dict[str, Any]:
    require(SHA256.fullmatch(expected_sha256) is not None, "trusted snapshot SHA-256 required")
    require(snapshot.is_dir() and not any(p.is_symlink() for p in (snapshot, *snapshot.parents)),
            "unsafe snapshot directory")
    require(set(p.name for p in snapshot.iterdir()) ==
            {"node.bundle", "snapshot.json", "snapshot.sha256"}, "incomplete/surplus snapshot files")
    require(digest_file(snapshot / "snapshot.json", MAX_METADATA_BYTES)[1] == expected_sha256,
            "snapshot root digest mismatch")
    value = load_json(snapshot / "snapshot.json", canonical_required=True)
    require(set(value) == {"schema", "repository", "git_object_format", "subject", "lineage",
                          "bundle", "capabilities_to_rebind", "predecessor_evidence_transfer"},
            "snapshot fields differ")
    require(value["schema"] == SCHEMA and value["git_object_format"] == "sha1" and
            value["capabilities_to_rebind"] == REBIND and
            value["predecessor_evidence_transfer"] is False, "snapshot contract differs")
    digest_file(snapshot / "snapshot.sha256", 65)
    require((snapshot / "snapshot.sha256").read_bytes() == (expected_sha256 + "\n").encode(),
            "detached snapshot digest mismatch")
    bundle = value["bundle"]
    require(isinstance(bundle, dict) and set(bundle) == {"path", "bytes", "sha256"} and
            bundle["path"] == "node.bundle" and type(bundle["bytes"]) is int and
            isinstance(bundle["sha256"], str), "bundle binding invalid")
    require(digest_file(snapshot / "node.bundle", MAX_BUNDLE_BYTES) ==
            (bundle["bytes"], bundle["sha256"]), "bundle bytes/digest mismatch")
    subject = value["subject"]
    require(isinstance(subject, dict) and set(subject) ==
            {"head", "tree", "head_symbolic_ref", "refs", "reachable_objects",
             "object_inventory_sha256", "repository_manifest_sha256"}, "subject fields differ")
    require(all(isinstance(subject[key], str) and SHA1.fullmatch(subject[key])
                for key in ("head", "tree")), "invalid subject Git identity")
    require(all(isinstance(subject[key], str) and SHA256.fullmatch(subject[key])
                for key in ("object_inventory_sha256", "repository_manifest_sha256")),
            "invalid subject digest")
    require(type(subject["reachable_objects"]) is int and subject["reachable_objects"] > 0,
            "invalid object count")
    require(subject["head_symbolic_ref"] is None or
            isinstance(subject["head_symbolic_ref"], str), "invalid HEAD binding")
    require(isinstance(subject["refs"], list) and len(subject["refs"]) <= 10000,
            "ref inventory invalid")
    names = []
    for item in subject["refs"]:
        require(isinstance(item, dict) and set(item) == {"name", "oid", "symbolic_ref"},
                "ref fields differ")
        require(isinstance(item["name"], str) and item["name"].startswith("refs/") and
                isinstance(item["oid"], str) and SHA1.fullmatch(item["oid"]) is not None and
                (item["symbolic_ref"] is None or isinstance(item["symbolic_ref"], str)),
                "ref identity invalid")
        names.append(item["name"])
    require(names == sorted(set(names)), "ref inventory must be sorted and unique")
    require(isinstance(value["repository"], str) and REPOSITORY.fullmatch(value["repository"]) is not None,
            "invalid snapshot repository")
    require(isinstance(value["lineage"], dict), "invalid snapshot lineage")
    return value


def recovery_receipt(root: Path, snapshot_sha: str, subject: dict[str, Any]) -> dict[str, Any]:
    receipt = {"schema": "qikvrt_node_recovery_receipt_v1", "state": "RECOVERED_ISOLATED",
               "observation_id": uuid.uuid4().hex,
               "observed_at": datetime.now(timezone.utc).isoformat(),
               "snapshot_sha256": snapshot_sha, "subject": subject,
               "fresh_integrity_verified": True, "fresh_git_closure_verified": True,
               "predecessor_evidence_transfer": False, "capabilities_to_rebind": REBIND,
               "external_effects": [], "effect_ack_done": False}
    gitdir = Path(git(root, "rev-parse", "--absolute-git-dir").strip())
    target = gitdir / "qikvrt-recovery.json"
    require(not target.is_symlink(), "unsafe recovery receipt path")
    temporary = gitdir / ("qikvrt-recovery-" + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_bytes(canonical(receipt))
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return receipt


def restore_snapshot(snapshot: Path, destination: Path, expected_sha256: str) -> dict[str, Any]:
    value = read_snapshot(snapshot, expected_sha256)
    subject = value["subject"]
    destination = destination.absolute()
    require(not any(p.is_symlink() for p in (destination, *destination.parents)),
            "unsafe recovery destination")
    if destination.exists():
        require(observe(destination) == subject, "existing destination differs from snapshot")
        require(lineage(destination, value["repository"]) == value["lineage"], "ancestry mismatch")
        return recovery_receipt(destination, expected_sha256, subject)
    new_path(destination)
    with tempfile.TemporaryDirectory(prefix=".qikvrt-restore-", dir=destination.parent) as directory:
        stage = Path(directory) / "node"
        stage.mkdir()
        template = Path(directory) / "empty-template"
        template.mkdir()
        git(stage, "init", "--quiet", "--object-format=sha1", "--template=" + str(template))
        bundle = str((snapshot / "node.bundle").resolve())
        # Verification in a completely empty object database rejects a thin or
        # prerequisite-bound archive even when the exporting node had the base.
        git(stage, "bundle", "verify", "--quiet", bundle)
        advertised = {}
        for line in git(stage, "bundle", "list-heads", bundle).splitlines():
            oid, name = line.split(" ", 1)
            require(name not in advertised, "duplicate bundle ref")
            advertised[name] = oid
        expected = {item["name"]: item["oid"] for item in subject["refs"]}
        require(len(expected) == len(subject["refs"]), "duplicate snapshot ref")
        expected["HEAD"] = subject["head"]
        require(advertised == expected, "bundle ref coverage differs from snapshot")
        git(stage, "bundle", "unbundle", bundle)
        for item in subject["refs"]:
            git(stage, "check-ref-format", item["name"])
            require(not item["name"].startswith("refs/replace/"), "replace ref forbidden")
            git(stage, "update-ref", item["name"], item["oid"], "0" * 40)
        for item in subject["refs"]:
            if item["symbolic_ref"]:
                require(expected.get(item["symbolic_ref"]) == item["oid"], "unbound symbolic ref")
                git(stage, "symbolic-ref", item["name"], item["symbolic_ref"])
        if subject["head_symbolic_ref"]:
            require(expected.get(subject["head_symbolic_ref"]) == subject["head"], "unbound HEAD ref")
            git(stage, "symbolic-ref", "HEAD", subject["head_symbolic_ref"])
        else:
            git(stage, "update-ref", "--no-deref", "HEAD", subject["head"])
        git(stage, "read-tree", "--reset", "-u", "HEAD")
        require(observe(stage) == subject, "reconstructed history/refs/tree/bytes differ")
        require(lineage(stage, value["repository"]) == value["lineage"], "reconstructed ancestry differs")
        # Rehash after import; never trust a successful transport or a stale receipt.
        read_snapshot(snapshot, expected_sha256)
        stage.rename(destination)
    return recovery_receipt(destination, expected_sha256, observe(destination))


def genesis(snapshot: Path, destination: Path, expected_sha256: str, *,
            repository: str, kind: str, expected_head: str,
            authorize_local_candidate: bool = False) -> dict[str, Any]:
    require(authorize_local_candidate is True, "local genesis candidate authorization required")
    require(kind in KINDS and REPOSITORY.fullmatch(repository) is not None, "invalid genesis target")
    value = read_snapshot(snapshot, expected_sha256)
    require(expected_head == value["subject"]["head"], "genesis expected-head mismatch")
    require(not destination.exists(), "genesis is create-only; target already exists")
    if kind != "RECOVERY_AUTHORITY":
        require(repository != value["repository"] and repository not in value["lineage"]["ancestry"],
                "child/mirror identity must be new; ancestry cycles forbidden")
    else:
        require(repository == value["repository"], "recovery promotion retains node repository identity")
    if kind == "CHILD":
        require(repository.split("/")[0] == "Goldkelch", "child must remain in Goldkelch namespace")
    destination = new_path(destination)
    # A failed genesis never exposes a partially materialized target.
    with tempfile.TemporaryDirectory(prefix=".qikvrt-genesis-", dir=destination.parent) as directory:
        stage = Path(directory) / "node"
        restore_snapshot(snapshot, stage, expected_sha256)
        ancestry = value["lineage"]["ancestry"][:]
        if ancestry[-1] != repository:
            ancestry.append(repository)
        role = "MIRROR" if kind == "MIRROR" else "AUTHORITY"
        authority = value["lineage"]["authority_repository"] if role == "MIRROR" else repository
        material = {"snapshot_sha256": expected_sha256, "repository": repository, "kind": kind}
        node_id = hashlib.sha256(canonical(material)).hexdigest()
        binding = {"schema": "qikvrt_node_binding_v1", "node_id": node_id,
                   "repository": repository, "role": role, "genesis_kind": kind,
                   "state": "CANDIDATE_ISOLATED", "hierarchy_root": HIERARCHY_ROOT,
                   "ancestry": ancestry, "authority_repository": authority,
                   "authority_epoch": value["lineage"]["authority_epoch"] + int(role == "AUTHORITY"),
                   "parent": {"repository": value["repository"], "head": expected_head,
                              "tree": value["subject"]["tree"], "snapshot_sha256": expected_sha256},
                   "capabilities_to_rebind": REBIND, "predecessor_evidence_transfer": False,
                   "external_effects": [], "effect_ack_done": False}
        policy = load_json(stage / REMOTE_POLICY)
        policy["node_genesis_state"] = "CANDIDATE_ISOLATED"
        policy["node_binding"] = BINDING
        key = "mirror" if role == "MIRROR" else "canonical_upstream"
        policy[key] = {"repository": repository, "role": role,
                       "canonical_remote_name": "mirror" if role == "MIRROR" else "authority",
                       "canonical_https_url": f"https://github.com/{repository}.git",
                       "canonical_api_repository": f"https://api.github.com/repos/{repository}",
                       "canonical_entrypoint": "/AI", "default_branch": "main"}
        if role == "AUTHORITY":
            policy["mirror"] = None  # A former peer is not silently assigned a new role.
        (stage / BINDING).write_bytes(canonical(binding))
        (stage / REMOTE_POLICY).write_bytes(canonical(policy))
        integrity.generate(stage)
        fresh_integrity(stage)
        changed = [BINDING, REMOTE_POLICY, *sorted(integrity.INTEGRITY_PATHS)]
        git(stage, "add", "--", *changed)
        tree = git(stage, "write-tree").strip()
        timestamp = int(git(stage, "show", "-s", "--format=%ct", expected_head).strip()) + 1
        env = {"GIT_AUTHOR_NAME": "QIKVRT Genesis", "GIT_AUTHOR_EMAIL": "genesis@qikvrt.invalid",
               "GIT_COMMITTER_NAME": "QIKVRT Genesis", "GIT_COMMITTER_EMAIL": "genesis@qikvrt.invalid",
               "GIT_AUTHOR_DATE": f"@{timestamp} +0000", "GIT_COMMITTER_DATE": f"@{timestamp} +0000"}
        head = git(stage, "commit-tree", tree, "-p", expected_head,
                   "-m", f"genesis: isolated {kind} candidate {node_id}", extra_env=env).strip()
        branch = "refs/heads/genesis/" + node_id[:24]
        require(git(stage, "rev-parse", "HEAD").strip() == expected_head,
                "competing local writer changed genesis base")
        git(stage, "update-ref", branch, head, "0" * 40)
        git(stage, "symbolic-ref", "HEAD", branch)
        observed = observe(stage)
        require(observed["head"] == head and observed["tree"] == tree, "genesis readback differs")
        require(git(stage, "rev-list", "--parents", "-n", "1", head).strip() ==
                f"{head} {expected_head}", "genesis must preserve its exact source parent")
        stage.rename(destination)
    return {"schema": "qikvrt_node_genesis_receipt_v1", "state": "CANDIDATE_ISOLATED",
            "repository": repository, "role": role, "head": head, "tree": tree,
            "parent_head": expected_head, "snapshot_sha256": expected_sha256,
            "branch": branch, "node_binding": binding, "capabilities_to_rebind": REBIND,
            "external_effects": [], "effect_ack_done": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--root", type=Path, default=ROOT)
    export.add_argument("--repository", required=True)
    export.add_argument("--destination", type=Path, required=True)
    for command in ("restore", "genesis"):
        child = sub.add_parser(command)
        child.add_argument("--snapshot", type=Path, required=True)
        child.add_argument("--expect-snapshot-sha256", required=True)
        child.add_argument("--destination", type=Path, required=True)
        if command == "genesis":
            child.add_argument("--repository", required=True)
            child.add_argument("--kind", choices=KINDS, required=True)
            child.add_argument("--expect-head", required=True)
            child.add_argument("--authorize-local-candidate", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            sha = export_snapshot(args.root, args.destination, args.repository)
            result = {"snapshot_sha256": sha, "state": "SNAPSHOT_MATERIALIZED",
                      "effect_ack_done": False}
        elif args.command == "restore":
            result = restore_snapshot(args.snapshot, args.destination, args.expect_snapshot_sha256)
        else:
            result = genesis(args.snapshot, args.destination, args.expect_snapshot_sha256,
                             repository=args.repository, kind=args.kind,
                             expected_head=args.expect_head,
                             authorize_local_candidate=args.authorize_local_candidate)
        sys.stdout.buffer.write(canonical(result))
        return 0
    except (GenesisBlock, OSError, ValueError, KeyError, TypeError) as exc:
        sys.stdout.buffer.write(canonical({"state": "BLOCK", "blocker": str(exc),
                                         "effect_ack_done": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
