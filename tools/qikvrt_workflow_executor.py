#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-head workflow-executor planning and mesh-node continuity checks.

The planning controller is deliberately repository-local. It observes Git state and
workflow metadata supplied by the caller, creates a deterministic dispatch
plan, and validates a node-split continuity receipt.  It never calls GitHub,
dispatches a workflow, writes a repository file, or treats a terminal watcher
as a successful gate.  The narrowly authorised Action wrapper performs the
single REST dispatch only after this controller has produced a candidate.
The separate authority-readback command performs bounded, authenticated GETs;
it never substitutes a Mirror response or candidate policy for active Main.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ACTIVE_RUN_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
ROLE_POLICY_PATH = "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
GOVERNANCE_POLICY_PATH = "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"


class ExecutorBlock(RuntimeError):
    """A fail-closed executor or continuity validation error."""


def resolve_repository_roles(policy: Mapping[str, Any]) -> dict[str, str]:
    """Resolve the existing normative policy; projections cannot assign roles."""
    if (policy.get("schema") != "qikvrt_canonical_upstream_remote_v1"
            or policy.get("status") != "NORMATIVE"):
        raise ExecutorBlock("CANONICAL_ROLE_POLICY_INVALID")
    roles: dict[str, str] = {}
    for key, role, remote in (("canonical_upstream", "AUTHORITY", "authority"),
                              ("mirror", "MIRROR", "mirror")):
        binding = _mapping(policy.get(key), f"canonical {role} binding")
        repository = _string(binding.get("repository"), f"canonical {role} repository")
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
                or binding.get("role") != role or binding.get("default_branch") != "main"
                or binding.get("canonical_remote_name") != remote
                or binding.get("canonical_entrypoint") != "/AI"
                or binding.get("canonical_https_url") != f"https://github.com/{repository}.git"
                or binding.get("canonical_api_repository") != f"https://api.github.com/repos/{repository}"):
            raise ExecutorBlock("CANONICAL_ROLE_BINDING_INVALID")
        roles[role] = repository
    if roles["AUTHORITY"].casefold() == roles["MIRROR"].casefold():
        raise ExecutorBlock("Authority and Mirror repositories must be distinct")
    if _mapping(policy.get("selection_rule"), "canonical selection rule").get("source_of_truth") != "canonical_upstream.repository":
        raise ExecutorBlock("CANONICAL_ROLE_SOURCE_INVALID")
    if (_mapping(policy.get("exact_head_contract"), "canonical exact-head contract").get("predecessor_gate_evidence_transfer") is not False
            or _mapping(policy.get("promotion_contract"), "canonical promotion contract").get("force_push") is not False):
        raise ExecutorBlock("CANONICAL_ROLE_PROTECTION_BOUNDARY_INVALID")
    return roles


def load_repository_roles(root: Path = ROOT) -> dict[str, str]:
    policy = _mapping(_read_json_file(root / ROLE_POLICY_PATH, "canonical role policy"), "canonical role policy")
    return resolve_repository_roles(policy)


def validate_request_roles(document: Mapping[str, Any], root: Path = ROOT) -> dict[str, str]:
    """A historical exact-artifact grant cannot redefine the current roles."""
    roles = load_repository_roles(root)
    binding = _mapping(document.get("repository_policy", document), "request role projection")
    if (binding.get("authority_repository") != roles["AUTHORITY"]
            or binding.get("mirror_repository") != roles["MIRROR"]):
        raise ExecutorBlock("HISTORICAL_ROLE_REQUEST_NOT_CURRENT")
    return roles


def validate_role_projections(root: Path = ROOT) -> dict[str, str]:
    """Validate live configuration projections; frozen evidence is never migrated."""
    roles = load_repository_roles(root)
    authority_repository(load_contract(root), root)
    for path in ("policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json",
                 "policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json",
                 "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json"):
        policy = _mapping(_read_json_file(root / path, "role projection"), "role projection")
        if policy.get("authority_repository") != roles["AUTHORITY"] or policy.get("role_policy_path") != ROLE_POLICY_PATH:
            raise ExecutorBlock(f"CANONICAL_ROLE_PROJECTION_MISMATCH {path}")
    origin = _mapping(_read_json_file(root / "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json", "origin policy"), "origin policy")
    memory = _mapping(origin.get("personal_working_memory"), "personal working memory")
    if _mapping(memory.get("canonical_source_remote"), "personal source remote").get("url") != f"https://github.com/{roles['AUTHORITY']}.git":
        raise ExecutorBlock("CANONICAL_ORIGIN_ROLE_MISMATCH")
    governance = _mapping(_read_json_file(root / GOVERNANCE_POLICY_PATH, "governance policy"), "governance policy")
    authority = _mapping(governance.get("mesh_authority"), "governance authority")
    if (authority.get("authority_repository") != roles["AUTHORITY"]
            or authority.get("role_policy_path") != ROLE_POLICY_PATH):
        raise ExecutorBlock("CANONICAL_GOVERNANCE_ROLE_MISMATCH")
    validate_governance_policy(load_contract(root), governance, root)
    twin = _mapping(_read_json_file(root / "policy/QIKVRT_ETHICAL_EVOLUTIONARY_DIGITAL_TWIN_MESH_V1.json", "digital twin policy"), "digital twin policy")
    reciprocal = _mapping(twin.get("reciprocal_rest"), "reciprocal REST projection")
    if (reciprocal.get("authority_repository") != roles["AUTHORITY"]
            or reciprocal.get("mirror_repository") != roles["MIRROR"]
            or reciprocal.get("role_policy_path") != ROLE_POLICY_PATH):
        raise ExecutorBlock("CANONICAL_DIGITAL_TWIN_ROLE_MISMATCH")
    return roles


def authority_retry_binding(root: Path = ROOT) -> str:
    """Bind causal read prerequisites; unrelated Heads and timestamps do not admit retries."""
    paths = (ROLE_POLICY_PATH, "tools/qikvrt_workflow_executor.py",
             ".github/workflows/qikvrt_reflexive_repository_watchdog.yml",
             ".github/workflows/qikvrt_workflow_executor.yml")
    authority = _mapping(load_contract(root).get("authority"), "retry Authority binding")
    return sha256_bytes(canonical_json_bytes({
        "files": {path: sha256_bytes((root / path).read_bytes()) for path in paths},
        "authority": dict(authority),
    }))


def authority_repository(contract: Mapping[str, Any], root: Path = ROOT) -> str:
    """Resolve one declared Authority without treating its declaration as activation."""
    authority = _mapping(contract.get("authority"), "contract authority")
    repository = _string(authority.get("repository"), "authority repository")
    mirrors = _string_list(authority.get("mirror_repositories"), "mirror repositories")
    roles = load_repository_roles(root)
    if repository != roles["AUTHORITY"] or mirrors != [roles["MIRROR"]]:
        raise ExecutorBlock("AUTHORITY_CONTRACT_CANONICAL_ROLE_MISMATCH")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ExecutorBlock("contract authority repository is invalid")
    if (not mirrors or any(not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item) for item in mirrors)
            or repository.casefold() in {item.casefold() for item in mirrors}):
        raise ExecutorBlock("Authority and Mirror repositories must be distinct")
    if authority.get("entrypoint") != "AI" or authority.get("role_policy_path") != ROLE_POLICY_PATH:
        raise ExecutorBlock("contract authority policy binding is invalid")
    if authority.get("activation") != "FRESH_AUTHORITY_MAIN_POLICY_READBACK_REQUIRED":
        raise ExecutorBlock("contract authority activation is not fail-closed")
    prevention = _mapping(contract.get("reflexive_deadlock_prevention"), "reflexive prevention")
    gatewatch = _mapping(prevention.get("gatewatch"), "reflexive gatewatch")
    liveness = _mapping(gatewatch.get("node_liveness"), "node liveness")
    if liveness.get("authority_repository") != repository:
        raise ExecutorBlock("node liveness and executor Authority repositories disagree")
    return repository


def validate_authority_policy(contract: Mapping[str, Any], policy: Mapping[str, Any], root: Path = ROOT) -> str:
    repository = authority_repository(contract, root)
    try:
        observed = resolve_repository_roles(policy)
    except ExecutorBlock as exc:
        raise ExecutorBlock("AUTHORITY_ROLE_BINDING_NOT_ACTIVE") from exc
    if observed != load_repository_roles(root):
        raise ExecutorBlock("AUTHORITY_ROLE_BINDING_NOT_ACTIVE")
    return repository


def validate_governance_policy(contract: Mapping[str, Any], policy: Mapping[str, Any], root: Path = ROOT) -> str:
    repository = authority_repository(contract, root)
    role = policy.get("mesh_authority")
    if (policy.get("schema") != "qikvrt_requested_review_and_issue_lifecycle_policy_v1"
            or policy.get("status") != "ACTIVE" or not isinstance(role, Mapping)
            or role.get("authority_repository") != repository
            or role.get("role_policy_path") != ROLE_POLICY_PATH
            or not isinstance(role.get("repository"), Mapping)
            or role["repository"].get("full_name") != repository):
        raise ExecutorBlock("AUTHORITY_ROLE_BINDING_NOT_ACTIVE")
    mirrors = contract["authority"]["mirror_repositories"]
    if (role.get("former_authority_repository") not in mirrors
            or role.get("former_authority_permission_required") is not False
            or role.get("independent_native_code_owner_review_required") is not True
            or role.get("github_platform_effects_are_separate") is not True
            or role["repository"].get("may_submit_native_approve") is not False
            or not isinstance(role.get("executor"), Mapping)
            or role["executor"].get("may_submit_native_approve") is not False
            or not isinstance(policy.get("mandatory_boundaries"), Mapping)
            or policy["mandatory_boundaries"].get("github_platform_protections_may_be_bypassed") is not False):
        raise ExecutorBlock("AUTHORITY_ROLE_POLICY_PROTECTION_BOUNDARY_INVALID")
    return repository


def read_authority_main(root: Path = ROOT, previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Read the declared Authority and its policy with the mandatory job token."""
    contract = load_contract(root)
    repository = authority_repository(contract, root)
    if (previous is not None and previous.get("retry_binding_sha256") == authority_retry_binding(root)
            and re.fullmatch(r"AUTHORITY_READBACK_DENIED HTTP_(?:403|404)", str(previous.get("first_blocker")))):
        raise ExecutorBlock(previous["first_blocker"])
    if not os.environ.get("GH_TOKEN"):
        raise ExecutorBlock("AUTHORITY_READBACK_JOB_TOKEN_REQUIRED")

    def get(endpoint: str) -> Mapping[str, Any]:
        try:
            response = subprocess.run(
                ["gh", "api", "--hostname", "github.com", "--method", "GET", endpoint],
                cwd=root, capture_output=True, text=True, check=False, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ExecutorBlock("AUTHORITY_READBACK_TRANSPORT_UNAVAILABLE") from exc
        if response.returncode:
            # Preserve the failure class only, never arbitrary response bodies or tokens.
            status = re.search(r"HTTP (\d{3})", response.stderr)
            detail = f"HTTP_{status.group(1)}" if status else f"CLI_EXIT_{response.returncode}"
            raise ExecutorBlock(f"AUTHORITY_READBACK_DENIED {detail}")
        try:
            return _mapping(json.loads(response.stdout), "Authority GET response")
        except json.JSONDecodeError as exc:
            raise ExecutorBlock("AUTHORITY_READBACK_INVALID_JSON") from exc

    endpoint = f"repos/{repository}/git/ref/heads/main"

    def head() -> str:
        value = get(endpoint)
        object_ref = _mapping(value.get("object"), "Authority main ref object")
        if value.get("ref") != "refs/heads/main" or object_ref.get("type") != "commit":
            raise ExecutorBlock("AUTHORITY_MAIN_REF_IDENTITY_INVALID")
        sha = _sha(object_ref.get("sha"), "Authority main head")
        api_root = f"https://api.github.com/repos/{repository}/git"
        if (value.get("url") != f"{api_root}/refs/heads/main"
                or object_ref.get("url") != f"{api_root}/commits/{sha}"):
            raise ExecutorBlock("AUTHORITY_MAIN_REPOSITORY_IDENTITY_INVALID")
        return sha

    main_head = head()
    commit = get(f"repos/{repository}/git/commits/{main_head}")
    tree = _mapping(commit.get("tree"), "Authority Main tree")
    main_tree = _sha(tree.get("sha"), "Authority Main tree")
    if (commit.get("sha") != main_head
            or tree.get("url") != f"https://api.github.com/repos/{repository}/git/trees/{main_tree}"):
        raise ExecutorBlock("AUTHORITY_MAIN_COMMIT_IDENTITY_INVALID")

    def content(path: str) -> tuple[bytes, str]:
        response = get(f"repos/{repository}/contents/{path}?ref={main_head}")
        if (response.get("type") != "file" or response.get("path") != path
                or response.get("encoding") != "base64"):
            raise ExecutorBlock("AUTHORITY_ROLE_POLICY_READBACK_IDENTITY_INVALID")
        try:
            encoded = _string(response.get("content"), "Authority policy content")
            raw = base64.b64decode("".join(encoded.split()), validate=True)
        except ValueError as exc:
            raise ExecutorBlock("AUTHORITY_ROLE_POLICY_READBACK_BYTES_INVALID") from exc
        if len(raw) > 1_048_576:
            raise ExecutorBlock("AUTHORITY_ROLE_POLICY_READBACK_TOO_LARGE")
        blob = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
        if (response.get("sha") != blob or type(response.get("size")) is not int
                or response.get("size") != len(raw)
                or response.get("git_url") != f"https://api.github.com/repos/{repository}/git/blobs/{blob}"):
            raise ExecutorBlock("AUTHORITY_ROLE_POLICY_BLOB_MISMATCH")
        return raw, blob

    def document(path: str) -> tuple[Mapping[str, Any], str]:
        raw, blob = content(path)
        try:
            return _mapping(json.loads(raw.decode("utf-8")), "Authority Main policy"), blob
        except (ValueError, UnicodeError) as exc:
            raise ExecutorBlock("AUTHORITY_ROLE_POLICY_READBACK_BYTES_INVALID") from exc

    policy, blob_sha = document(ROLE_POLICY_PATH)
    validate_authority_policy(contract, policy, root)
    governance, governance_blob = document(GOVERNANCE_POLICY_PATH)
    validate_governance_policy(contract, governance, root)
    codeowners, codeowners_blob = content(".github/CODEOWNERS")
    try:
        try:
            from tools.qikvrt_required_review_gate import resolve_required_code_owner
        except ModuleNotFoundError:
            from qikvrt_required_review_gate import resolve_required_code_owner
        owner = resolve_required_code_owner(repository, policy=governance, codeowners=codeowners.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ExecutorBlock("AUTHORITY_CODE_OWNER_POLICY_MISMATCH") from exc
    if head() != main_head:
        raise ExecutorBlock("AUTHORITY_MAIN_HEAD_DRIFT")
    return {
        "schema": "qikvrt_workflow_executor_authority_readback_v1",
        "state": "AUTHORITY_MAIN_ROLE_POLICY_REOBSERVED",
        "repository": repository, "main_head": main_head, "main_tree": main_tree,
        "role_policy_path": ROLE_POLICY_PATH, "role_policy_blob_sha": blob_sha,
        "governance_policy_blob_sha": governance_blob, "codeowners_blob_sha": codeowners_blob,
        "required_code_owner": owner, "native_activation_verified": False,
        "native_governance_verification": "SEPARATE_REQUIRED_GATE",
        "contract_sha256": _contract_sha256(root),
        "credential": "MANDATORY_GITHUB_JOB_TOKEN", "first_blocker": None,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExecutorBlock(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExecutorBlock(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ExecutorBlock(f"{label} must be a list of non-empty strings")
    return list(value)


def _sha(value: Any, label: str) -> str:
    value = _string(value, label)
    if not SHA_RE.fullmatch(value):
        raise ExecutorBlock(f"{label} must be a lower-case 40-character Git SHA")
    return value


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ExecutorBlock(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    path = root / CONTRACT_RELATIVE_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock(f"cannot load workflow executor contract: {exc}") from exc
    result = dict(_mapping(value, "workflow executor contract"))
    if result.get("schema") != "qikvrt_workflow_executor_mesh_contract_v1":
        raise ExecutorBlock("workflow executor contract schema is not v1")
    if result.get("contract_id") != "qikvrt-workflow-executor-mesh-v1":
        raise ExecutorBlock("workflow executor contract id is not recognized")
    return result


def _contract_sha256(root: Path) -> str:
    try:
        return sha256_bytes((root / CONTRACT_RELATIVE_PATH).read_bytes())
    except OSError as exc:
        raise ExecutorBlock(f"cannot hash workflow executor contract: {exc}") from exc


def _workflow_inventory(root: Path, revision: str) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", revision, "--", ".github/workflows"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExecutorBlock(f"cannot enumerate workflow tree: {detail}")
    inventory: list[dict[str, str]] = []
    for entry in completed.stdout.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, encoded_path = entry.split(b"\t", 1)
            _mode, object_type, blob_sha = metadata.decode("ascii").split(" ", 2)
            path = encoded_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise ExecutorBlock("workflow inventory contains a malformed Git tree entry") from exc
        if object_type != "blob" or not path.endswith((".yml", ".yaml")):
            continue
        inventory.append({"path": path, "blob_sha": _sha(blob_sha, f"workflow blob for {path}")})
    return sorted(inventory, key=lambda item: item["path"])


def _validate_contract_shape(contract: Mapping[str, Any], root: Path) -> None:
    authority_repository(contract, root)
    executor = _mapping(contract.get("executor"), "contract executor")
    for key in ("controller_path", "workflow_path", "watchdog_workflow_path", "monitor_workflow_path"):
        relative_path = _string(executor.get(key), f"contract executor.{key}")
        if not (root / relative_path).is_file():
            raise ExecutorBlock(f"contract-required file is absent: {relative_path}")
    if executor.get("observation_mode") != "REPOSITORY_NATIVE_EXACT_HEAD_BOUND":
        raise ExecutorBlock("executor observation mode is not exact-head bound")
    if executor.get("stateful_writes") != "ACTION_ARTIFACTS_ONLY":
        raise ExecutorBlock("executor stateful write boundary is not artifact-only")
    if _string_list(executor.get("single_writer_order"), "executor single writer order") != [
        "AUTHORITY",
        "MIRROR",
        "MESH_NODE",
    ]:
        raise ExecutorBlock("executor single writer order is not authority-first")

    policy = _mapping(contract.get("dispatch_policy"), "dispatch policy")
    if policy.get("enabled") is not True or policy.get("dispatch_ref") != "main":
        raise ExecutorBlock("dispatch policy is not enabled for main")
    if policy.get("terminal_or_active_exact_run_suppresses_duplicate_dispatch") is not True:
        raise ExecutorBlock("dispatch policy does not suppress duplicate exact-head runs")
    if policy.get("rerun") != "ONLY_REPOSITORY_DECLARED_TRANSIENT_FAILURE":
        raise ExecutorBlock("dispatch policy allows an unbounded rerun")
    required_conditions = set(_string_list(policy.get("required_conditions"), "dispatch conditions"))
    for condition in (
        "CURRENT_MAIN_HEAD_REOBSERVED",
        "CURRENT_MAIN_TREE_REOBSERVED",
        "WORKFLOW_IS_EXACT_TREE_MEMBER",
        "NO_COMPETING_WRITER",
        "NO_EQUIVALENT_EXACT_HEAD_RUN",
        "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT",
    ):
        if condition not in required_conditions:
            raise ExecutorBlock(f"dispatch condition missing: {condition}")
    _string_list(policy.get("writer_workflow_names"), "writer workflow names")
    allowed = policy.get("authorized_workflows")
    if not isinstance(allowed, list) or not allowed:
        raise ExecutorBlock("dispatch policy has no authorized workflow")
    for entry in allowed:
        item = _mapping(entry, "authorized workflow")
        workflow_id = _string(item.get("workflow_id"), "authorized workflow id")
        workflow_path = _string(item.get("workflow_path"), "authorized workflow path")
        if Path(workflow_path).name != workflow_id or not workflow_path.startswith(".github/workflows/"):
            raise ExecutorBlock("authorized workflow id/path binding is invalid")
        _string(item.get("workflow_name"), "authorized workflow name")
        if _string_list(item.get("allowed_events"), "authorized workflow events") != ["workflow_dispatch"]:
            raise ExecutorBlock("authorized workflow has an unbounded event set")
        if item.get("external_effect") != "NONE" or item.get("is_writer") is not False:
            raise ExecutorBlock("authorized workflow exceeds the no-effect observer boundary")

    boundaries = _mapping(contract.get("boundaries"), "executor boundaries")
    if boundaries.get("direct_repository_mutation") != "FORBIDDEN":
        raise ExecutorBlock("executor permits direct repository mutation")
    for key in (
        "watchdog_terminality_is_gate_success",
        "action_required_is_trusted_execution",
        "zero_job_is_trusted_execution",
    ):
        if boundaries.get(key) is not False:
            raise ExecutorBlock(f"executor boundary {key} must be false")

    continuity = _mapping(contract.get("mesh_node_split_acceptance"), "mesh node split acceptance")
    if continuity.get("applies_to") != "EVERY_FUTURE_NODE_ADDED_BY_QUEUE_ROW":
        raise ExecutorBlock("mesh node acceptance does not bind every future queue node")
    for key in ("receipt_path", "receipt_schema", "continuity_declaration_schema"):
        _string(continuity.get(key), f"mesh node split acceptance.{key}")
    _string_list(continuity.get("required_acceptance_tests"), "mesh node acceptance tests")
    _string_list(continuity.get("connection_order"), "mesh node connection order")


def workflow_delta(
    current_inventory: Sequence[Mapping[str, str]], baseline: Mapping[str, Any] | None
) -> dict[str, Any]:
    if baseline is None:
        return {"state": "BASELINE_UNAVAILABLE", "added": [], "removed": [], "changed": []}
    previous_raw = baseline.get("workflow_inventory")
    if not isinstance(previous_raw, list):
        raise ExecutorBlock("baseline does not contain a workflow inventory")
    previous: dict[str, str] = {}
    for entry in previous_raw:
        item = _mapping(entry, "baseline workflow inventory entry")
        path = _string(item.get("path"), "baseline workflow path")
        previous[path] = _sha(item.get("blob_sha"), f"baseline workflow blob for {path}")
    current = {item["path"]: item["blob_sha"] for item in current_inventory}
    return {
        "state": "COMPARED",
        "added": sorted(set(current) - set(previous)),
        "removed": sorted(set(previous) - set(current)),
        "changed": sorted(path for path in set(current) & set(previous) if current[path] != previous[path]),
    }


def snapshot(
    root: Path = ROOT,
    *,
    revision: str = "HEAD",
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = load_contract(root)
    _validate_contract_shape(contract, root)
    head = _sha(_git(root, "rev-parse", "--verify", f"{revision}^{{commit}}"), "exact head")
    tree = _sha(_git(root, "rev-parse", "--verify", f"{revision}^{{tree}}"), "exact tree")
    inventory = _workflow_inventory(root, revision)
    inventory_by_path = {item["path"]: item["blob_sha"] for item in inventory}
    for authorized in _mapping(contract["dispatch_policy"], "dispatch policy")["authorized_workflows"]:
        path = _mapping(authorized, "authorized workflow")["workflow_path"]
        if path not in inventory_by_path:
            raise ExecutorBlock(f"authorized workflow is absent from exact tree: {path}")
    return {
        "schema": "qikvrt_workflow_executor_snapshot_v1",
        "contract_id": contract["contract_id"],
        "contract_path": CONTRACT_RELATIVE_PATH,
        "contract_sha256": _contract_sha256(root),
        "head_sha": head,
        "tree_sha": tree,
        "workflow_inventory": inventory,
        "workflow_inventory_sha256": sha256_bytes(canonical_json_bytes(inventory)),
        "workflow_delta": workflow_delta(inventory, baseline),
    }


def _runs(value: Mapping[str, Any] | Sequence[Any]) -> list[Mapping[str, Any]]:
    raw: Any = value.get("workflow_runs") if isinstance(value, Mapping) else value
    if not isinstance(raw, list):
        raise ExecutorBlock("workflow run observation must contain workflow_runs")
    return [item for item in raw if isinstance(item, Mapping)]


def dispatch_plan(snapshot_value: Mapping[str, Any], runs_value: Mapping[str, Any] | Sequence[Any], ref: str) -> dict[str, Any]:
    contract = load_contract()
    role_blocker = None
    try:
        validate_role_projections()
    except ExecutorBlock as exc:
        role_blocker = str(exc)
    policy = _mapping(contract["dispatch_policy"], "dispatch policy")
    if ref != policy["dispatch_ref"]:
        raise ExecutorBlock(f"dispatch ref {ref!r} is not the authorised ref {policy['dispatch_ref']!r}")
    head = _sha(snapshot_value.get("head_sha"), "snapshot head")
    tree = _sha(snapshot_value.get("tree_sha"), "snapshot tree")
    inventory = snapshot_value.get("workflow_inventory")
    if not isinstance(inventory, list):
        raise ExecutorBlock("snapshot workflow inventory is missing")
    workflow_blobs = {
        _string(_mapping(item, "snapshot workflow").get("path"), "snapshot workflow path"):
        _sha(_mapping(item, "snapshot workflow").get("blob_sha"), "snapshot workflow blob")
        for item in inventory
    }
    runs = _runs(runs_value)
    writer_names = set(_string_list(policy["writer_workflow_names"], "writer workflow names"))
    active_writers = [
        {
            "id": run.get("id"),
            "name": run.get("name"),
            "status": run.get("status"),
            "head_sha": run.get("head_sha"),
        }
        for run in runs
        if run.get("name") in writer_names and run.get("status") in ACTIVE_RUN_STATUSES
    ]
    candidates: list[dict[str, Any]] = []
    for raw_authorized in policy["authorized_workflows"]:
        authorized = _mapping(raw_authorized, "authorized workflow")
        path = _string(authorized["workflow_path"], "authorized workflow path")
        workflow_name = _string(authorized["workflow_name"], "authorized workflow name")
        candidate = {
            "workflow_id": _string(authorized["workflow_id"], "authorized workflow id"),
            "workflow_path": path,
            "workflow_name": workflow_name,
            "ref": ref,
            "head_sha": head,
            "tree_sha": tree,
            "workflow_blob_sha": workflow_blobs.get(path),
            "external_effect": authorized["external_effect"],
            "required_artifact_prefix": authorized["required_artifact_prefix"],
        }
        if role_blocker is not None:
            candidate.update({"disposition": "HOLD", "first_blocker": role_blocker})
        elif candidate["workflow_blob_sha"] is None:
            candidate.update({"disposition": "HOLD", "first_blocker": "WORKFLOW_ABSENT_FROM_EXACT_TREE"})
        elif active_writers:
            candidate.update({"disposition": "HOLD", "first_blocker": "COMPETING_WRITER_ACTIVE"})
        else:
            equivalent = [
                run
                for run in runs
                if run.get("name") == workflow_name and run.get("head_sha") == head
            ]
            active = [run for run in equivalent if run.get("status") in ACTIVE_RUN_STATUSES]
            if active:
                candidate.update({"disposition": "HOLD", "first_blocker": "EQUIVALENT_EXACT_HEAD_RUN_ACTIVE"})
            elif equivalent:
                trusted = all(
                    run.get("conclusion") not in {"action_required", None} for run in equivalent
                )
                candidate.update(
                    {
                        "disposition": "HOLD",
                        "first_blocker": (
                            "EQUIVALENT_EXACT_HEAD_RUN_REQUIRES_JOB_EVIDENCE"
                            if not trusted
                            else "EQUIVALENT_EXACT_HEAD_RUN_TERMINAL"
                        ),
                    }
                )
            else:
                candidate.update({"disposition": "DISPATCH", "first_blocker": None})
        candidates.append(candidate)
    return {
        "schema": "qikvrt_workflow_executor_plan_v1",
        "contract_id": contract["contract_id"],
        "observed": dict(snapshot_value),
        "active_writers": active_writers,
        "candidates": candidates,
        "state": "DISPATCH_CANDIDATE_READY" if any(item["disposition"] == "DISPATCH" for item in candidates) else "HOLD",
    }


def expected_node_receipt_url(node_repository: str, node_branch: str) -> str:
    _string(node_repository, "node repository")
    _string(node_branch, "node branch")
    contract = load_contract()
    receipt_path = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")["receipt_path"]
    return (
        f"https://raw.githubusercontent.com/{node_repository}/"
        f"{urllib.parse.quote(node_branch, safe='/-._~')}/{receipt_path}"
    )


def validate_node_continuity_declaration(
    document: Mapping[str, Any], node_repository: str, node_branch: str
) -> str:
    contract = load_contract()
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    value = _mapping(document.get(continuity["registration_request_field"]), "workflow executor continuity declaration")
    if value.get("schema") != continuity["continuity_declaration_schema"]:
        raise ExecutorBlock("workflow executor continuity declaration schema is invalid")
    if value.get("receipt_path") != continuity["receipt_path"]:
        raise ExecutorBlock("workflow executor continuity declaration receipt path is invalid")
    receipt_url = _string(value.get("receipt_url"), "workflow executor continuity receipt url")
    if receipt_url != expected_node_receipt_url(node_repository, node_branch):
        raise ExecutorBlock("workflow executor continuity receipt URL is not bound to the node repository and branch")
    if value.get("acceptance_required") is not True:
        raise ExecutorBlock("workflow executor continuity declaration does not require acceptance")
    return receipt_url


def build_node_receipt(node_repository: str, node_branch: str, root: Path = ROOT) -> dict[str, Any]:
    contract = load_contract(root)
    value = snapshot(root)
    executor = _mapping(contract["executor"], "contract executor")
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    return {
        "schema": continuity["receipt_schema"],
        "qikvrt_event": "QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY",
        "node_repository": node_repository,
        "node_branch": node_branch,
        "authority": {
            "repository": _mapping(contract["authority"], "contract authority")["repository"],
            "entrypoint": "AI",
            "contract_id": contract["contract_id"],
            "contract_sha256": value["contract_sha256"],
            "head_sha": value["head_sha"],
            "tree_sha": value["tree_sha"],
        },
        "executor": {
            "controller_path": executor["controller_path"],
            "workflow_path": executor["workflow_path"],
            "watchdog_workflow_path": executor["watchdog_workflow_path"],
            "monitor_workflow_path": executor["monitor_workflow_path"],
        },
        "acceptance": {
            "required_tests": continuity["required_acceptance_tests"],
            "connection_order": continuity["connection_order"],
            "status": "DECLARED_NOT_EXECUTION_EVIDENCE",
        },
        "external_effect": "NONE",
        "completion_claims": contract["completion_claims"],
    }


def validate_node_receipt(
    receipt: Mapping[str, Any], node_repository: str, node_branch: str, root: Path = ROOT
) -> dict[str, Any]:
    contract = load_contract(root)
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    receipt = _mapping(receipt, "node continuity receipt")
    if receipt.get("schema") != continuity["receipt_schema"]:
        raise ExecutorBlock("node continuity receipt schema is invalid")
    if receipt.get("qikvrt_event") != "QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY":
        raise ExecutorBlock("node continuity receipt event is invalid")
    if receipt.get("node_repository") != node_repository or receipt.get("node_branch") != node_branch:
        raise ExecutorBlock("node continuity receipt is not bound to the declared node")
    authority = _mapping(receipt.get("authority"), "node receipt authority")
    contract_authority = _mapping(contract["authority"], "contract authority")
    if authority.get("repository") != contract_authority["repository"] or authority.get("entrypoint") != "AI":
        raise ExecutorBlock("node continuity receipt authority binding is invalid")
    if authority.get("contract_id") != contract["contract_id"]:
        raise ExecutorBlock("node continuity receipt contract id is invalid")
    if authority.get("contract_sha256") != _contract_sha256(root):
        raise ExecutorBlock("node continuity receipt does not bind the current authority contract")
    _sha(authority.get("head_sha"), "node receipt authority head")
    _sha(authority.get("tree_sha"), "node receipt authority tree")

    expected_executor = _mapping(contract["executor"], "contract executor")
    executor = _mapping(receipt.get("executor"), "node receipt executor")
    for key in ("controller_path", "workflow_path", "watchdog_workflow_path", "monitor_workflow_path"):
        if executor.get(key) != expected_executor[key]:
            raise ExecutorBlock(f"node continuity receipt executor binding is invalid: {key}")
    acceptance = _mapping(receipt.get("acceptance"), "node receipt acceptance")
    if _string_list(acceptance.get("required_tests"), "node receipt required tests") != continuity["required_acceptance_tests"]:
        raise ExecutorBlock("node continuity receipt acceptance tests are incomplete")
    if _string_list(acceptance.get("connection_order"), "node receipt connection order") != continuity["connection_order"]:
        raise ExecutorBlock("node continuity receipt connection order is incomplete")
    if acceptance.get("status") != "DECLARED_NOT_EXECUTION_EVIDENCE":
        raise ExecutorBlock("node continuity receipt overstates execution evidence")
    if receipt.get("external_effect") != "NONE":
        raise ExecutorBlock("node continuity receipt exceeds the no-effect boundary")
    claims = _mapping(receipt.get("completion_claims"), "node receipt completion claims")
    for key, expected in _mapping(contract["completion_claims"], "contract completion claims").items():
        if claims.get(key) is not expected:
            raise ExecutorBlock(f"node continuity receipt completion claim is invalid: {key}")
    return {
        "schema": "qikvrt_workflow_executor_node_receipt_validation_v1",
        "state": "NODE_SPLIT_CONTINUITY_ACCEPTANCE_READY",
        "node_repository": node_repository,
        "node_branch": node_branch,
        "contract_sha256": _contract_sha256(root),
        "first_blocker": None,
    }


def _read_json_file(path: Path, label: str) -> Mapping[str, Any] | Sequence[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, (Mapping, list)):
        raise ExecutorBlock(f"{label} must be an object or a list")
    return value


def _emit(value: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(canonical_json_bytes(value).decode("utf-8"), end="")
        return
    print(
        f"{value.get('state', 'OBSERVATION_READY')} "
        f"head={value.get('head_sha', value.get('node_repository', '-'))} "
        f"tree={value.get('tree_sha', '-')}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    authority = subcommands.add_parser("authority-readback")
    authority.add_argument("--previous-readback", type=Path)
    authority.add_argument("--json", action="store_true")
    for name in ("snapshot", "check"):
        command = subcommands.add_parser(name)
        command.add_argument("--baseline", type=Path)
        command.add_argument("--expect-head")
        command.add_argument("--json", action="store_true")
    plan = subcommands.add_parser("plan")
    plan.add_argument("--runs-file", type=Path, required=True)
    plan.add_argument("--baseline", type=Path)
    plan.add_argument("--expect-head", required=True)
    plan.add_argument("--ref", required=True)
    plan.add_argument("--json", action="store_true")
    template = subcommands.add_parser("node-receipt-template")
    template.add_argument("--node-repository", required=True)
    template.add_argument("--node-branch", required=True)
    template.add_argument("--json", action="store_true")
    roles = subcommands.add_parser("roles")
    roles.add_argument("--role", choices=("AUTHORITY", "MIRROR"))
    roles.add_argument("--projection-file", type=Path)
    roles.add_argument("--json", action="store_true")
    receipt = subcommands.add_parser("validate-node-receipt")
    receipt.add_argument("--receipt", type=Path, required=True)
    receipt.add_argument("--node-repository", required=True)
    receipt.add_argument("--node-branch", required=True)
    receipt.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "roles":
            roles = validate_role_projections()
            if arguments.projection_file:
                validate_request_roles(_mapping(_read_json_file(arguments.projection_file, "request role projection"), "request role projection"))
            if arguments.role:
                print(roles[arguments.role])
                return 0
            value = {"schema": "qikvrt_repository_roles_v1", "source": ROLE_POLICY_PATH,
                     "roles": roles, "native_activation_verified": False}
        elif arguments.command == "authority-readback":
            previous = _read_json_file(arguments.previous_readback, "previous Authority readback") if arguments.previous_readback else None
            value = read_authority_main(previous=_mapping(previous, "previous Authority readback") if previous is not None else None)
        elif arguments.command in {"snapshot", "check", "plan"}:
            baseline = _read_json_file(arguments.baseline, "baseline") if arguments.baseline else None
            value = snapshot(baseline=baseline if isinstance(baseline, Mapping) else None)
            if arguments.expect_head is not None and value["head_sha"] != arguments.expect_head:
                raise ExecutorBlock("EXACT_HEAD_DRIFT")
            if arguments.command == "plan":
                runs = _read_json_file(arguments.runs_file, "workflow runs")
                value = dispatch_plan(value, runs, arguments.ref)
        elif arguments.command == "node-receipt-template":
            value = build_node_receipt(arguments.node_repository, arguments.node_branch)
        else:
            receipt = _read_json_file(arguments.receipt, "node continuity receipt")
            if not isinstance(receipt, Mapping):
                raise ExecutorBlock("node continuity receipt must be an object")
            value = validate_node_receipt(receipt, arguments.node_repository, arguments.node_branch)
        _emit(value, arguments.json)
        return 0
    except ExecutorBlock as exc:
        if arguments.command == "authority-readback" and arguments.json:
            try:
                retry_binding = authority_retry_binding()
            except (OSError, ExecutorBlock):
                retry_binding = None
            _emit({"schema": "qikvrt_workflow_executor_authority_readback_v1",
                   "state": "HOLD", "first_blocker": str(exc),
                   "retry_binding_sha256": retry_binding,
                   "retry_condition": "MATERIALLY_CHANGED_ROLE_READ_PREREQUISITES_OR_INDEPENDENT_ACCESS_RECOVERY_EVIDENCE",
                   "native_activation_verified": False,
                   "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}}, True)
        print(f"BLOCK WORKFLOW_EXECUTOR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
