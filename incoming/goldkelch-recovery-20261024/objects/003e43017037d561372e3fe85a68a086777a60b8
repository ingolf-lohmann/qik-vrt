#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded, node-local liveness repair for the repository self-heal controller.

The tool never writes another repository.  It only prepares a reviewable local
candidate after exact local/Authority reobservation.  The caller remains
responsible for the existing integrity materialization and draft-PR boundary.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


ROOT = pathlib.Path(__file__).resolve().parents[1]
ONBOARDING = pathlib.PurePosixPath("qikvrt/runtime/onboarding")
ACK_PATH = ONBOARDING / "SEED_ACCEPTANCE_STATUS.json"
RENEWAL_PATH = ONBOARDING / "NODE_REGISTRATION_RENEWAL.json"
HEALTH_PATH = ONBOARDING / "NODE_HEALTH.json"
LIVENESS_WORK_UNIT = pathlib.PurePosixPath(
    "state/work_units/RENEW_MIRROR_NODE_LIVENESS_AFTER_EXPIRY_V1.json"
)
ACK_WORK_UNIT = pathlib.PurePosixPath(
    "state/work_units/REFRESH_MIRROR_SEED_ACCEPTANCE_AFTER_LIVENESS_V1.json"
)
AUTHORITY_REPOSITORY = "Goldkelch/qik-vrt"
AUTHORITY_URL = "https://github.com/Goldkelch/qik-vrt.git"
MIRROR_REPOSITORY = "ingolf-lohmann/qik-vrt"
REFRESH_LEAD = dt.timedelta(hours=1)
MAX_FUTURE_SKEW = dt.timedelta(minutes=5)
SHA1 = re.compile(r"^[0-9a-f]{40}$")


class NodeLivenessBlock(RuntimeError):
    """A deterministic condition which may not be repaired automatically."""


@dataclass(frozen=True)
class RepositorySnapshot:
    repository: str
    commit: str
    tree: str


@dataclass(frozen=True)
class AuthorityObservation:
    snapshot: RepositorySnapshot
    guid: str
    node_branch: str
    heartbeat_ttl_minutes: int


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def format_utc(value: dt.datetime) -> str:
    if value.tzinfo != dt.timezone.utc:
        raise NodeLivenessBlock("UTC timestamp is required")
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise NodeLivenessBlock(f"{label} must be a UTC Z timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise NodeLivenessBlock(f"{label} is malformed") from exc
    if parsed.tzinfo != dt.timezone.utc:
        raise NodeLivenessBlock(f"{label} is not UTC")
    return parsed


def load_object(root: pathlib.Path, relative: pathlib.PurePosixPath) -> dict[str, Any]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise NodeLivenessBlock(f"{relative} cannot be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise NodeLivenessBlock(f"{relative} must be a JSON object")
    return value


def require_string(document: Mapping[str, Any], field: str, label: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value:
        raise NodeLivenessBlock(f"{label}.{field} must be a non-empty string")
    return value


def _require_boundaries(document: Mapping[str, Any], label: str) -> None:
    boundaries = document.get("boundaries")
    if not isinstance(boundaries, Mapping):
        raise NodeLivenessBlock(f"{label}.boundaries must be an object")
    for name in (
        "node_writes_only_to_node_repository",
        "no_global_scanning",
        "no_self_propagation",
        "no_remote_mutation_without_authorization",
    ):
        if boundaries.get(name) is not True:
            raise NodeLivenessBlock(f"{label}.boundaries.{name} must be true")


def _validate_common(
    document: Mapping[str, Any],
    *,
    expected_event: str,
    label: str,
) -> tuple[str, str, str]:
    if document.get("qikvrt_event") != expected_event:
        raise NodeLivenessBlock(f"{label}.qikvrt_event differs")
    guid = require_string(document, "guid", label)
    repository = require_string(document, "repository", label)
    seed = require_string(document, "seed_repository", label)
    if repository != MIRROR_REPOSITORY:
        raise NodeLivenessBlock(f"{label}.repository is not the local node")
    if seed != AUTHORITY_REPOSITORY:
        raise NodeLivenessBlock(f"{label}.seed_repository differs")
    _require_boundaries(document, label)
    return guid, repository, seed


def evaluate_liveness(
    root: pathlib.Path = ROOT,
    *,
    now: dt.datetime | None = None,
    authority_ttl_minutes: int | None = None,
    authority_node_branch: str | None = None,
) -> dict[str, Any]:
    """Return a pure current-record assessment without remote access or writes."""
    now = utc_now() if now is None else now
    if now.tzinfo != dt.timezone.utc:
        raise NodeLivenessBlock("now must be UTC")
    paths = (ACK_PATH, RENEWAL_PATH, HEALTH_PATH)
    present = {path: (root / path).is_file() for path in paths}
    if not any(present.values()):
        raise NodeLivenessBlock(
            "all required active Mirror node-liveness records are absent"
        )
    if not all(present.values()):
        missing = [str(path) for path, exists in present.items() if not exists]
        raise NodeLivenessBlock(f"partial node liveness records: {missing}")

    acknowledgement = load_object(root, ACK_PATH)
    renewal = load_object(root, RENEWAL_PATH)
    health = load_object(root, HEALTH_PATH)
    ack_guid, _, _ = _validate_common(
        acknowledgement,
        expected_event="NODE_ACK_OF_SEED_ACCEPTANCE",
        label=str(ACK_PATH),
    )
    renewal_guid, _, _ = _validate_common(
        renewal,
        expected_event="NODE_REGISTRATION_RENEWAL",
        label=str(RENEWAL_PATH),
    )
    health_guid, _, _ = _validate_common(
        health,
        expected_event="NODE_HEALTH_HEARTBEAT",
        label=str(HEALTH_PATH),
    )
    if {ack_guid, renewal_guid, health_guid} != {ack_guid}:
        raise NodeLivenessBlock("node liveness GUIDs differ")
    if acknowledgement.get("status") != "ACCEPTED_BY_SEED":
        raise NodeLivenessBlock(f"{ACK_PATH}.status differs")
    if renewal.get("status") != "RENEWED":
        raise NodeLivenessBlock(f"{RENEWAL_PATH}.status differs")
    if health.get("status") != "ACTIVE":
        raise NodeLivenessBlock(f"{HEALTH_PATH}.status differs")
    if health.get("node_branch") != "main" or renewal.get("node_branch") != "main":
        raise NodeLivenessBlock("node liveness branch differs")
    ttl = health.get("heartbeat_ttl_minutes")
    if not isinstance(ttl, int) or not 1 <= ttl <= 10_080:
        raise NodeLivenessBlock(f"{HEALTH_PATH}.heartbeat_ttl_minutes is invalid")
    if authority_ttl_minutes is not None:
        if not 1 <= authority_ttl_minutes <= 10_080:
            raise NodeLivenessBlock("Authority heartbeat TTL is invalid")
        if ttl != authority_ttl_minutes:
            raise NodeLivenessBlock(
                f"{HEALTH_PATH}.heartbeat_ttl_minutes disagrees with Authority"
            )
        if authority_node_branch != "main":
            raise NodeLivenessBlock("Authority node branch differs")

    renewed = parse_utc(renewal.get("renewed_utc"), str(RENEWAL_PATH))
    due = parse_utc(renewal.get("next_renewal_due_utc"), str(RENEWAL_PATH))
    heartbeat = parse_utc(health.get("heartbeat_utc"), str(HEALTH_PATH))
    expires = parse_utc(health.get("expires_utc"), str(HEALTH_PATH))
    if renewed > now + MAX_FUTURE_SKEW:
        raise NodeLivenessBlock(f"{RENEWAL_PATH}.renewed_utc is too far in the future")
    if due <= renewed:
        raise NodeLivenessBlock(f"{RENEWAL_PATH}.next_renewal_due_utc must follow renewal")
    if heartbeat > now + MAX_FUTURE_SKEW:
        raise NodeLivenessBlock(f"{HEALTH_PATH}.heartbeat_utc is too far in the future")
    if expires < heartbeat:
        raise NodeLivenessBlock(f"{HEALTH_PATH}.expires_utc precedes heartbeat")
    effective_ttl = authority_ttl_minutes if authority_ttl_minutes is not None else ttl
    effective_expires = min(
        expires, heartbeat + dt.timedelta(minutes=effective_ttl)
    )
    reasons: list[str] = []
    if due <= now + REFRESH_LEAD:
        reasons.append("RENEWAL_DUE_OR_WITHIN_LEAD")
    if effective_expires <= now + REFRESH_LEAD:
        reasons.append("HEALTH_EXPIRED_OR_WITHIN_LEAD")
    return {
        "state": "MIRROR_NODE_LIVENESS_REFRESH_REQUIRED"
        if reasons
        else "FRESH",
        "refresh_required": bool(reasons),
        "guid": ack_guid,
        "renewal_due_utc": format_utc(due),
        "health_expires_utc": format_utc(expires),
        "effective_health_expires_utc": format_utc(effective_expires),
        "heartbeat_ttl_minutes": effective_ttl,
        "reasons": reasons,
    }


def run_git(
    root: pathlib.Path,
    command: Sequence[str],
    *,
    timeout: int = 90,
) -> str:
    completed = subprocess.run(
        list(command),
        cwd=root,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        raise NodeLivenessBlock(
            f"git command failed ({' '.join(command)}): "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def run_git_result(
    root: pathlib.Path,
    command: Sequence[str],
    *,
    timeout: int = 90,
) -> subprocess.CompletedProcess[str]:
    """Run Git where a documented nonzero result may be meaningful."""
    return subprocess.run(
        list(command),
        cwd=root,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _read_remote_main(remote: str, root: pathlib.Path) -> str:
    output = run_git(
        root,
        ("git", "ls-remote", "--heads", remote, "refs/heads/main"),
        timeout=90,
    )
    fields = output.split()
    if len(fields) != 2 or not SHA1.fullmatch(fields[0]):
        raise NodeLivenessBlock(f"{remote} main is unavailable or malformed")
    return fields[0]


def local_snapshot(root: pathlib.Path = ROOT) -> RepositorySnapshot:
    commit = run_git(root, ("git", "rev-parse", "--verify", "HEAD"))
    tree = run_git(root, ("git", "show", "-s", "--format=%T", "HEAD"))
    remote = _read_remote_main("origin", root)
    if commit != remote:
        raise NodeLivenessBlock(
            f"local Mirror HEAD drifted from origin/main: {commit} != {remote}"
        )
    if not SHA1.fullmatch(commit) or not SHA1.fullmatch(tree):
        raise NodeLivenessBlock("local Mirror commit or tree is malformed")
    return RepositorySnapshot(MIRROR_REPOSITORY, commit, tree)


def _authority_file(
    bare: pathlib.Path,
    commit: str,
    path: str,
) -> dict[str, Any]:
    completed = subprocess.run(
        ("git", "-C", str(bare), "show", f"{commit}:{path}"),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if completed.returncode:
        raise NodeLivenessBlock(
            f"Authority path {path} is unavailable: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    try:
        value = json.loads(completed.stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        raise NodeLivenessBlock(f"Authority path {path} is malformed") from exc
    if not isinstance(value, dict):
        raise NodeLivenessBlock(f"Authority path {path} is not an object")
    return value


def _authority_text(bare: pathlib.Path, commit: str, path: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(bare), "show", f"{commit}:{path}"),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if completed.returncode:
        raise NodeLivenessBlock(
            f"Authority path {path} is unavailable: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout


def _authority_node_configuration(
    raw: str,
    guid: str,
) -> tuple[str, int]:
    matches: list[tuple[str, int]] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 7:
            raise NodeLivenessBlock(
                "Authority known-node registry row has unexpected column count "
                f"at line {line_number}"
            )
        (
            row_guid,
            repository,
            seed,
            _request_url,
            branch,
            ttl_text,
            lifecycle,
        ) = fields
        if row_guid != guid:
            continue
        if (
            repository != MIRROR_REPOSITORY
            or seed != AUTHORITY_REPOSITORY
            or branch != "main"
            or lifecycle != "ACTIVE"
        ):
            raise NodeLivenessBlock(
                "Authority known-node registry does not authorize this active "
                "Mirror node configuration"
            )
        try:
            ttl = int(ttl_text, 10)
        except ValueError as exc:
            raise NodeLivenessBlock(
                "Authority known-node heartbeat TTL is malformed"
            ) from exc
        if not 1 <= ttl <= 10_080:
            raise NodeLivenessBlock("Authority known-node heartbeat TTL is invalid")
        matches.append((branch, ttl))
    if len(matches) != 1:
        raise NodeLivenessBlock(
            "Authority known-node registry does not contain one active Mirror node"
        )
    return matches[0]


def authority_snapshot(
    root: pathlib.Path = ROOT,
    *,
    expected_guid: str,
) -> AuthorityObservation:
    """Fetch one immutable Authority object and reject remote-head drift."""
    before = _read_remote_main(AUTHORITY_URL, root)
    with tempfile.TemporaryDirectory(prefix="qikvrt-authority-liveness-") as temp:
        bare = pathlib.Path(temp)
        run_git(root, ("git", "init", "--bare", str(bare)))
        run_git(
            root,
            (
                "git",
                "-C",
                str(bare),
                "fetch",
                "--quiet",
                "--depth=1",
                AUTHORITY_URL,
                before,
            ),
            timeout=180,
        )
        tree = run_git(
            root,
            ("git", "-C", str(bare), "show", "-s", "--format=%T", before),
        )
        index = _authority_file(bare, before, "registry/NODEMESH_INDEX.json")
        entry = _authority_file(
            bare, before, f"registry/nodes/{expected_guid}.json"
        )
        known_nodes = _authority_text(
            bare, before, "registry/KNOWN_NODE_REQUESTS.tsv"
        )
    after = _read_remote_main(AUTHORITY_URL, root)
    if before != after:
        raise NodeLivenessBlock(
            f"Authority main drifted during observation: {before} != {after}"
        )
    if not SHA1.fullmatch(tree):
        raise NodeLivenessBlock("Authority tree is malformed")
    branch, ttl = _authority_node_configuration(known_nodes, expected_guid)
    _validate_authority_membership(index, entry, expected_guid, branch)
    return AuthorityObservation(
        snapshot=RepositorySnapshot(AUTHORITY_REPOSITORY, before, tree),
        guid=expected_guid,
        node_branch=branch,
        heartbeat_ttl_minutes=ttl,
    )


def _validate_authority_membership(
    index: Mapping[str, Any],
    entry: Mapping[str, Any],
    guid: str,
    node_branch: str,
) -> None:
    nodes = index.get("nodes")
    if not isinstance(nodes, list):
        raise NodeLivenessBlock("Authority node index has no node list")
    matches = [
        node
        for node in nodes
        if isinstance(node, Mapping)
        and node.get("guid") == guid
        and node.get("repository") == MIRROR_REPOSITORY
        and node.get("seed_repository") == AUTHORITY_REPOSITORY
        and node.get("node_branch") == node_branch
        and node.get("effective_status") == "ACTIVE"
    ]
    if len(matches) != 1:
        raise NodeLivenessBlock("Authority index does not contain one active node")
    if (
        entry.get("qikvrt_event") != "AUTONOMOUS_SEED_ACCEPTANCE"
        or entry.get("guid") != guid
        or entry.get("repository") != MIRROR_REPOSITORY
        or entry.get("seed_repository") != AUTHORITY_REPOSITORY
        or entry.get("node_branch") != node_branch
        or entry.get("status") != "ACCEPTED"
        or entry.get("policy_status") != "ACTIVE"
    ):
        raise NodeLivenessBlock("Authority node entry is not active and accepted")


def _write(root: pathlib.Path, relative: pathlib.PurePosixPath, value: Any) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _record_sha256(root: pathlib.Path, relative: pathlib.PurePosixPath) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def observe_liveness(
    root: pathlib.Path = ROOT,
    *,
    now: dt.datetime | None = None,
) -> tuple[dict[str, Any], RepositorySnapshot, AuthorityObservation]:
    """Bind a local liveness decision to stable current Mirror and Authority."""
    now = utc_now() if now is None else now
    preliminary = evaluate_liveness(root, now=now)
    source_before = local_snapshot(root)
    authority = authority_snapshot(root, expected_guid=preliminary["guid"])
    assessment = evaluate_liveness(
        root,
        now=now,
        authority_ttl_minutes=authority.heartbeat_ttl_minutes,
        authority_node_branch=authority.node_branch,
    )
    source_after = local_snapshot(root)
    if source_after != source_before:
        raise NodeLivenessBlock(
            "Mirror main drifted during paired liveness observation"
        )
    return assessment, source_before, authority


def _common_work_unit(
    *,
    work_unit_id: str,
    source: RepositorySnapshot,
    authority: RepositorySnapshot,
    created_at: str,
    inputs: Mapping[str, Any],
    outputs: Sequence[str],
    description: str,
) -> dict[str, Any]:
    return {
        "_license": {
            "classification": "machine_readable_work_unit",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_node_liveness_repair_work_unit_v1",
        "work_unit_id": work_unit_id,
        "created_at": created_at,
        "source_repository": source.repository,
        "source_ref": "refs/heads/main",
        "source_commit": source.commit,
        "source_tree": source.tree,
        "human_actor": {
            "actor_class": "HUMAN",
            "attribution_id": "Ingolf Lohmann",
            "role": "Product Owner",
            "identity_proof_boundary": (
                "Repository and platform records attribute the instruction to "
                "the named account context; they are not biometric identity proof."
            ),
        },
        "artificial_cognitive_actor": {
            "actor_class": "ARTIFICIAL_COGNITIVE_SYSTEM",
            "provider": "OpenAI",
            "system_family": "Codex",
            "model_or_build": "UNAVAILABLE",
            "session_or_run_id": "qikvrt-node-liveness-self-heal",
            "tools_and_adapters": [
                "QIK-VRT /AI bootstrap contract",
                "repository-native bounded self-heal",
            ],
            "identity_and_observation_limits": (
                "The system identity is a runtime declaration; it does not "
                "establish natural-person identity or independent review."
            ),
        },
        "human_contributions": [
            {
                "type": "AUTHORIZATION_AND_ORDERING",
                "description": (
                    "Product Owner authorized repair of expired Mirror liveness "
                    "and automatic repetition through the bounded review-branch "
                    "self-heal path."
                ),
            }
        ],
        "artificial_cognitive_contributions": [
            {
                "type": "LIVE_REOBSERVATION_AND_MATERIALIZATION",
                "description": description,
            }
        ],
        "joint_components": [
            {
                "component": "Mirror node-liveness recovery",
                "human_part": "scope authorization and effect boundaries",
                "artificial_cognitive_part": (
                    "exact-head observation, deterministic candidate construction, "
                    "and verification planning"
                ),
                "separable": True,
            }
        ],
        "unresolved_origin": [],
        "inputs": {
            "retention_mode": "METADATA_ONLY",
            "raw_transcript_persisted": False,
            "authority_repository": authority.repository,
            "authority_main": authority.commit,
            "authority_tree": authority.tree,
            "mirror_repository": source.repository,
            "mirror_main": source.commit,
            "mirror_tree": source.tree,
            **dict(inputs),
        },
        "outputs": {
            "paths": list(outputs),
            "integrity_binding": "BOUND_BY_FINAL_REPOSITORY_NATIVE_INTEGRITY_TRIO",
            "self_binding_rule": (
                "The containing Git commit and tree bind the exact work-unit "
                "bytes; no impossible in-file self-hash is claimed."
            ),
        },
        "git_history": {
            "branch": "automation/self-heal-BASE_AND_FINGERPRINT_BOUND",
            "base_commit": source.commit,
            "content_commit": "BOUND_BY_CONTAINING_GIT_COMMIT",
            "force_push": False,
            "history_rewrite": False,
            "merge": "EXPECTED_HEAD_BOUND_ONLY",
        },
        "verification": {
            "record_parser_contract": "PENDING_EXACT_HEAD_GATES",
            "repository_native_integrity": "PENDING_DETERMINISTIC_REGENERATION",
            "seed_acceptance": "SEPARATE_POST_PROMOTION_PHASE",
        },
        "human_decision": {
            "directive": "RECEIVED",
            "candidate_review": (
                "AUTHORIZED_FOR_AUTONOMOUS_REPOSITORY_INTERNAL_CONTINUATION_"
                "UNDER_EXACT_HEAD_RULES"
            ),
        },
        "external_effects": {
            "review_branch_creation": "AUTHORIZED_REPOSITORY_INTERNAL_EFFECT",
            "repository_file_commits": "AUTHORIZED_REPOSITORY_INTERNAL_EFFECT",
            "pull_request": "AUTHORIZED_REPOSITORY_INTERNAL_EFFECT",
            "merge": "CONDITIONAL_ON_UNCHANGED_EXPECTED_HEAD_AND_TERMINAL_GREEN_GATES",
            "release": "NOT_AUTHORIZED",
            "deployment": "NOT_AUTHORIZED",
            "zenodo": "NOT_AUTHORIZED",
            "doi": "NOT_AUTHORIZED",
            "ietf": "NOT_AUTHORIZED",
        },
        "release_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_SYNCHRONIZED": False,
        },
    }


def materialize_liveness(
    root: pathlib.Path = ROOT,
    *,
    now: dt.datetime | None = None,
    source: RepositorySnapshot | None = None,
    authority: RepositorySnapshot | None = None,
    authority_ttl_minutes: int | None = None,
) -> dict[str, Any]:
    now = utc_now() if now is None else now
    if source is None or authority is None:
        assessment, observed_source, authority_observation = observe_liveness(
            root, now=now
        )
        source = observed_source if source is None else source
        authority = (
            authority_observation.snapshot if authority is None else authority
        )
        authority_ttl_minutes = authority_observation.heartbeat_ttl_minutes
    else:
        assessment = evaluate_liveness(
            root,
            now=now,
            authority_ttl_minutes=authority_ttl_minutes,
        )
    if not assessment["refresh_required"]:
        return {"state": "NOOP", "changed_paths": []}
    if authority_ttl_minutes is None:
        authority_ttl_minutes = assessment["heartbeat_ttl_minutes"]
    renewed = format_utc(now)
    renewal_due = format_utc(now + dt.timedelta(days=1))
    health_expires = format_utc(
        now + dt.timedelta(minutes=authority_ttl_minutes)
    )
    run_id = f"qikvrt-node-liveness-{now.strftime('%Y%m%dT%H%M%SZ')}"
    renewal = load_object(root, RENEWAL_PATH)
    health = load_object(root, HEALTH_PATH)
    renewal.update(
        {
            "status": "RENEWED",
            "renewed_utc": renewed,
            "next_renewal_due_utc": renewal_due,
            "run_id": run_id,
        }
    )
    health.update(
        {
            "status": "ACTIVE",
            "heartbeat_utc": renewed,
            "expires_utc": health_expires,
            "run_id": run_id,
        }
    )
    _write(root, RENEWAL_PATH, renewal)
    _write(root, HEALTH_PATH, health)
    work_unit = _common_work_unit(
        work_unit_id="RENEW-MIRROR-NODE-LIVENESS-AFTER-EXPIRY-V1",
        source=source,
        authority=authority,
        created_at=renewed,
        inputs={
            "node_guid": assessment["guid"],
            "previous_renewal_due_utc": assessment["renewal_due_utc"],
            "previous_health_expires_utc": assessment["health_expires_utc"],
            "previous_effective_health_expires_utc": assessment[
                "effective_health_expires_utc"
            ],
            "authority_heartbeat_ttl_minutes": authority_ttl_minutes,
            "refresh_lead_seconds": int(REFRESH_LEAD.total_seconds()),
            "seed_acceptance_status_policy": (
                "PRESERVE_UNCHANGED_UNTIL_POST_PROMOTION_AUTHORITY_REOBSERVATION"
            ),
        },
        outputs=[
            str(HEALTH_PATH),
            str(RENEWAL_PATH),
            str(LIVENESS_WORK_UNIT),
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        ],
        description=(
            "Detected overdue/near-expiry local node liveness and materialized "
            "only the local renewal and health projection after exact pair "
            "observation.  The Seed acknowledgement is intentionally unchanged."
        ),
    )
    work_unit["outputs"].update(
        {
            "new_renewed_utc": renewed,
            "new_next_renewal_due_utc": renewal_due,
            "new_health_expires_utc": health_expires,
            "renewal_sha256": _record_sha256(root, RENEWAL_PATH),
            "health_sha256": _record_sha256(root, HEALTH_PATH),
        }
    )
    _write(root, LIVENESS_WORK_UNIT, work_unit)
    return {
        "state": "REPAIRED",
        "failure_class": "MIRROR_NODE_LIVENESS_REFRESH_REQUIRED",
        "changed_paths": [str(HEALTH_PATH), str(RENEWAL_PATH), str(LIVENESS_WORK_UNIT)],
        "authority_main": authority.commit,
        "authority_tree": authority.tree,
        "mirror_main": source.commit,
        "mirror_tree": source.tree,
    }


def _liveness_paths_modified(root: pathlib.Path) -> bool:
    # `git diff` alone misses staged changes, and an ACK must never be
    # refreshed in the same candidate that renews the node-owned records.
    output = run_git(
        root,
        (
            "git",
            "status",
            "--porcelain=v1",
            "--",
            str(HEALTH_PATH),
            str(RENEWAL_PATH),
        ),
    )
    changed = {line[3:] for line in output.splitlines() if len(line) >= 4}
    return bool(changed & {str(HEALTH_PATH), str(RENEWAL_PATH)})


def _ack_covers_current_mirror(
    root: pathlib.Path,
    acknowledgement: Mapping[str, Any],
    source: RepositorySnapshot,
) -> bool:
    """Prove an ACK still covers unchanged node-owned liveness bytes.

    An ACK commit is necessarily later than the immutable Mirror snapshot it
    records.  Requiring literal current-HEAD equality would consequently
    create a new ACK candidate on every idle tick.  We instead require the
    recorded snapshot to be an ancestor of current main, to have the recorded
    tree, and to have unchanged renewal/health bytes since that snapshot.
    """
    observed_commit = acknowledgement.get("observed_mirror_commit")
    observed_tree = acknowledgement.get("observed_mirror_tree")
    if not (
        isinstance(observed_commit, str)
        and isinstance(observed_tree, str)
        and SHA1.fullmatch(observed_commit)
        and SHA1.fullmatch(observed_tree)
    ):
        return False
    try:
        actual_tree = run_git(
            root, ("git", "show", "-s", "--format=%T", observed_commit)
        )
    except NodeLivenessBlock as exc:
        raise NodeLivenessBlock(
            "ACK observed Mirror commit cannot be resolved locally"
        ) from exc
    if actual_tree != observed_tree:
        return False
    ancestor = run_git_result(
        root,
        ("git", "merge-base", "--is-ancestor", observed_commit, source.commit),
    )
    if ancestor.returncode == 1:
        raise NodeLivenessBlock(
            "ACK observed Mirror commit is not an ancestor of current main"
        )
    if ancestor.returncode:
        raise NodeLivenessBlock(
            "cannot verify ACK observed Mirror commit ancestry: "
            f"{ancestor.stderr.strip() or ancestor.stdout.strip()}"
        )
    changed = run_git_result(
        root,
        (
            "git",
            "diff",
            "--quiet",
            observed_commit,
            source.commit,
            "--",
            str(HEALTH_PATH),
            str(RENEWAL_PATH),
        ),
    )
    if changed.returncode == 0:
        return True
    if changed.returncode == 1:
        return False
    raise NodeLivenessBlock(
        "cannot verify liveness-byte continuity since ACK: "
        f"{changed.stderr.strip() or changed.stdout.strip()}"
    )


def acceptance_assessment(
    root: pathlib.Path = ROOT,
    *,
    now: dt.datetime | None = None,
    source: RepositorySnapshot | None = None,
    authority: RepositorySnapshot | None = None,
) -> dict[str, Any]:
    now = utc_now() if now is None else now
    if source is None or authority is None:
        liveness, observed_source, authority_observation = observe_liveness(
            root, now=now
        )
        source = observed_source if source is None else source
        authority = (
            authority_observation.snapshot if authority is None else authority
        )
    else:
        liveness = evaluate_liveness(root, now=now)
    if _liveness_paths_modified(root):
        return {
            "state": "DEFERRED_UNTIL_LIVENESS_PROMOTION",
            "refresh_required": False,
        }
    if liveness["refresh_required"]:
        return {
            "state": "DEFERRED_UNTIL_LIVENESS_IS_CURRENT",
            "refresh_required": False,
        }
    acknowledgement = load_object(root, ACK_PATH)
    _validate_common(
        acknowledgement,
        expected_event="NODE_ACK_OF_SEED_ACCEPTANCE",
        label=str(ACK_PATH),
    )
    if acknowledgement.get("status") != "ACCEPTED_BY_SEED":
        raise NodeLivenessBlock(f"{ACK_PATH}.status differs")
    current = (
        acknowledgement.get("observed_authority_commit") == authority.commit
        and acknowledgement.get("observed_authority_tree") == authority.tree
        and _ack_covers_current_mirror(root, acknowledgement, source)
    )
    return {
        "state": "FRESH" if current else "MIRROR_SEED_ACCEPTANCE_REFRESH_REQUIRED",
        "refresh_required": not current,
        "guid": liveness["guid"],
        "source": source,
        "authority": authority,
    }


def materialize_acceptance(
    root: pathlib.Path = ROOT,
    *,
    now: dt.datetime | None = None,
    source: RepositorySnapshot | None = None,
    authority: RepositorySnapshot | None = None,
) -> dict[str, Any]:
    now = utc_now() if now is None else now
    assessment = acceptance_assessment(
        root, now=now, source=source, authority=authority
    )
    if not assessment.get("refresh_required"):
        return {"state": assessment["state"], "changed_paths": []}
    source = assessment["source"]
    authority = assessment["authority"]
    checked = format_utc(now)
    acknowledgement = load_object(root, ACK_PATH)
    acknowledgement.update(
        {
            "checked_utc": checked,
            "run_id": f"qikvrt-seed-acceptance-refresh-{now.strftime('%Y%m%dT%H%M%SZ')}",
            "observed_authority_commit": authority.commit,
            "observed_authority_tree": authority.tree,
            "observed_mirror_commit": source.commit,
            "observed_mirror_tree": source.tree,
        }
    )
    _write(root, ACK_PATH, acknowledgement)
    work_unit = _common_work_unit(
        work_unit_id="REFRESH-MIRROR-SEED-ACCEPTANCE-AFTER-LIVENESS-V1",
        source=source,
        authority=authority,
        created_at=checked,
        inputs={
            "node_guid": assessment["guid"],
            "authority_registry_reobserved": True,
            "liveness_current_before_ack_refresh": True,
        },
        outputs=[
            str(ACK_PATH),
            str(ACK_WORK_UNIT),
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        ],
        description=(
            "After a separately promoted liveness refresh, reobserved the "
            "Authority registry and refreshed the Mirror-owned acknowledgement "
            "with exact Authority and Mirror commit/tree bindings."
        ),
    )
    work_unit["outputs"].update(
        {
            "acknowledgement_sha256": _record_sha256(root, ACK_PATH),
            "acknowledgement_checked_utc": checked,
        }
    )
    _write(root, ACK_WORK_UNIT, work_unit)
    return {
        "state": "REPAIRED",
        "failure_class": "MIRROR_SEED_ACCEPTANCE_REFRESH_REQUIRED",
        "changed_paths": [str(ACK_PATH), str(ACK_WORK_UNIT)],
        "authority_main": authority.commit,
        "authority_tree": authority.tree,
        "mirror_main": source.commit,
        "mirror_tree": source.tree,
    }


def _print(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("check", "materialize", "check-acceptance", "materialize-acceptance"),
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            value, _, _ = observe_liveness()
            _print(value)
            return 1 if value.get("refresh_required") else 0
        if args.command == "materialize":
            _print(materialize_liveness())
            return 0
        if args.command == "check-acceptance":
            value = acceptance_assessment()
            _print(value)
            return 1 if value.get("refresh_required") else 0
        _print(materialize_acceptance())
        return 0
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
        NodeLivenessBlock,
    ) as exc:
        _print(
            {
                "state": "BLOCK",
                "failure_class": "MIRROR_NODE_LIVENESS_BLOCKED",
                "detail": str(exc),
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
