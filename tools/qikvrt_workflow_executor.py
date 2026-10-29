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
import io
import json
import os
import re
import subprocess
import sys
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ACTIVE_RUN_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
ROLE_POLICY_PATH = "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
GOVERNANCE_POLICY_PATH = "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
AMO_REPOSITORY = "ingolf-lohmann/qik-vrt"
AMO_NATIVE_WORKFLOW = ".github/workflows/qikvrt_workflow_executor.yml"
AMO_CI_WORKFLOW = ".github/workflows/qikvrt_ci.yml"
AMO_JOB = "Owner-authorized Firefox signing continuation"
AMO_DISPATCH_STEP = "Dispatch the admitted exact-source signing request once"
AMO_SCOPE = "firefox-amo-unlisted"
AMO_SCHEMA = "qikvrt-owner-amo-continuation/v1"
AMO_OWNER_CI_REF = "integration/515-519-521-522-20261012-eceb9b63"
AMO_OWNER_CI_AUTHORIZED_AT = "2026-10-17T09:33:35Z"
AMO_RUN_PAGE_SIZE = 20
AMO_RUN_HISTORY_BUDGET = 1600


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
            or role.get("github_platform_effects_are_separate") is not True
            or role["repository"].get("may_submit_native_approve") is not False
            or not isinstance(role.get("executor"), Mapping)
            or role["executor"].get("may_submit_native_approve") is not False
            or not isinstance(policy.get("mandatory_boundaries"), Mapping)
            or policy["mandatory_boundaries"].get("github_platform_protections_may_be_bypassed") is not False):
        raise ExecutorBlock("AUTHORITY_ROLE_POLICY_PROTECTION_BOUNDARY_INVALID")
    try:
        try:
            from tools.qikvrt_required_review_gate import validate_review_acceptance_policy, ReviewGateInputError
        except ModuleNotFoundError:
            from qikvrt_required_review_gate import validate_review_acceptance_policy, ReviewGateInputError
        validate_review_acceptance_policy(policy, root)
    except ReviewGateInputError as exc:
        raise ExecutorBlock("AUTHORITY_ROLE_POLICY_PROTECTION_BOUNDARY_INVALID") from exc
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


def _amo_object(raw: bytes) -> dict[str, Any]:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ExecutorBlock("AMO_DUPLICATE_JSON_MEMBER")
            result[key] = value
        return result
    if len(raw) > 1_048_576:
        raise ExecutorBlock("AMO_METADATA_CAPACITY_LIMIT")
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError) as exc:
        raise ExecutorBlock("AMO_METADATA_INVALID") from exc
    if not isinstance(value, dict):
        raise ExecutorBlock("AMO_METADATA_OBJECT_REQUIRED")
    return value


def amo_request(root: Path = ROOT) -> dict[str, Any]:
    request = load_contract(root).get("owner_authorized_operations", {}).get(AMO_SCOPE)
    fixed = {"schema": "qikvrt-owner-amo-request/v1", "enabled": True,
             "owner": "Ingolf Lohmann", "authorization_source": "DIRECT_OWNER_INSTRUCTION",
             "repository": AMO_REPOSITORY, "ref": "main", "workflow": "qikvrt_ci.yml",
             "credential_secret_names": ["AMO_JWT_ISSUER", "AMO_JWT_SECRET"],
             "binding_revision_variable": "QIKVRT_AMO_BINDING_REVISION",
             "requires_native_main_protection": True, "delegated_actor": "github-actions[bot]",
             "ambiguous_dispatch": "READBACK_ONLY", "unchanged_failed_effect": "NOOP",
             "feedback_event": "GITHUB_WORKFLOW_RUN_COMPLETED", "elapsed_time_is_abort_evidence": False,
             "callback_waits_for_caller": False, "cancelled_upload_resume": "GET_ONLY",
             "pre_activation_main": {"head": "d8ff32dad42a50be719a683c37b9104392281384",
                                     "contract_blob": "5111fcbeb2c1100087b6b61d096a4427e88ca981"},
             "external_effect_scope": "OFFICIAL_UNLISTED_SIGNING_OF_EXACT_STANDARD_COMPONENTS_ONLY",
             "public_production_verified": False}
    if (not isinstance(request, dict) or set(request) != set(fixed) | {
            "authorized_at", "statement", "unsigned_xpi_sha256"}
            or any(type(request.get(k)) is not type(v) or request[k] != v for k, v in fixed.items())
            or not re.fullmatch(r"[a-f0-9]{64}", str(request.get("unsigned_xpi_sha256", "")))
            or not isinstance(request.get("statement"), str) or not request["statement"].strip()
            or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+]03:00", str(request.get("authorized_at", "")))):
        raise ExecutorBlock("AMO_EXACT_OWNER_REQUEST_REQUIRED")
    return request


def amo_native_protection(branch: Mapping[str, Any], rules: Sequence[Mapping[str, Any]]) -> None:
    """Check actual effective rules; a candidate policy is not enforcement."""
    if (not isinstance(branch, Mapping) or not isinstance(rules, list)
            or any(not isinstance(r, Mapping) or not isinstance(r.get("parameters", {}), Mapping) for r in rules)):
        raise ExecutorBlock("AMO_NATIVE_MAIN_PROTECTION_REQUIRED")
    try:
        from tools.qikvrt_required_review_gate import code_owner_review_policy_is_enforced
    except ModuleNotFoundError:
        from qikvrt_required_review_gate import code_owner_review_policy_is_enforced
    statuses = [r.get("parameters", {}) for r in rules if r.get("type") == "required_status_checks"]
    if (branch.get("name") != "main" or branch.get("protected") is not True
            or not code_owner_review_policy_is_enforced(rules)
            or not any(r.get("type") == "non_fast_forward" for r in rules)
            or not any(p.get("strict_required_status_checks_policy") is True
                       and {"test", "QIKVRT required code-owner review"} <= {
                           s.get("context") for s in p.get("required_status_checks", [])
                           if isinstance(s, dict)} for p in statuses)):
        raise ExecutorBlock("AMO_NATIVE_MAIN_PROTECTION_REQUIRED")


def amo_credential_delivery(context: Mapping[str, Any]) -> dict[str, Any]:
    """Report only secret delivery to this job, never inventory or authentication."""
    if any(type(context.get(k)) is not bool for k in ("issuer_present", "secret_present")):
        raise ExecutorBlock("AMO_PRESENCE_BOOLEAN_REQUIRED")
    issuer, secret = context["issuer_present"], context["secret_present"]
    return {"scope": "CURRENT_JOB_SECRET_CONTEXT_ONLY",
        "secret_names": ["AMO_JWT_ISSUER", "AMO_JWT_SECRET"],
        "issuer_present": issuer, "secret_present": secret,
        "state": "PAIR_DELIVERED" if issuer and secret else (
            "PARTIAL_PAIR_DELIVERED" if issuer or secret else "PAIR_NOT_DELIVERED"),
        "configuration_status": "NOT_INSPECTED", "credential_values_read": False,
        "amo_authentication_verified": False}


def amo_owner_ci_admission(root: Path, context: Mapping[str, Any],
                           subject: Mapping[str, Any], pr: Mapping[str, Any]) -> dict[str, Any]:
    """Admit the direct Owner's tested PR push, separately from Main delegation."""
    request = load_contract(root).get("owner_ci_handoff")
    fixed = {"schema": "qikvrt-owner-tested-ci-handoff/v1", "enabled": True,
        "authorization_source": "DIRECT_OWNER_INSTRUCTION", "owner": "Ingolf Lohmann",
        "authorized_at": AMO_OWNER_CI_AUTHORIZED_AT,
        "statement": "Ja, genau dafür ist die Continuous Integration Continuous Development Pipeline in der Linux-Distribution ja gedacht, diesen Teil zu übernehmen. Freigabe erteilt.",
        "repository": AMO_REPOSITORY, "actor": "ingolf-lohmann", "event": "push",
        "ref": AMO_OWNER_CI_REF, "pull_request": 523, "workflow": AMO_CI_WORKFLOW,
        "unsigned_xpi_sha256": "1f5f583181d6134584f98bf6b59848d4542176d624d97709fa915b9934e2c46c",
        "external_effect_scope": "OFFICIAL_UNLISTED_SIGNING_OF_EXACT_STANDARD_COMPONENTS_ONLY",
        "requires_successful_exact_subject_test": True, "independent_approval": False,
        "changes_main_admission": False, "unchanged_failed_effect": "NOOP"}
    if (not isinstance(request, dict) or set(request) != set(fixed)
            or any(type(request.get(k)) is not type(v) or request[k] != v for k, v in fixed.items())):
        raise ExecutorBlock("AMO_EXACT_OWNER_CI_HANDOFF_REQUIRED")
    head, tree = context.get("head"), context.get("tree")
    if (not isinstance(head, str) or not SHA_RE.fullmatch(head)
            or not isinstance(tree, str) or not SHA_RE.fullmatch(tree)
            or context.get("repository") != AMO_REPOSITORY
            or context.get("event") != "push" or context.get("actor") != "ingolf-lohmann"
            or context.get("triggering_actor") != "ingolf-lohmann"
            or context.get("ref") != "refs/heads/" + AMO_OWNER_CI_REF
            or context.get("workflow_ref") != f"{AMO_REPOSITORY}/{AMO_CI_WORKFLOW}@refs/heads/{AMO_OWNER_CI_REF}"
            or context.get("workflow_sha") != head or context.get("event_head") != head
            or type(context.get("run_attempt")) is not int or context["run_attempt"] != 1):
        raise ExecutorBlock("AMO_DIRECT_OWNER_CI_CONTEXT_REQUIRED")
    if (context.get("test_result") != "success" or context.get("tested_head") != head
            or context.get("tested_tree") != tree):
        raise ExecutorBlock("AMO_SUCCESSFUL_EXACT_SUBJECT_TEST_REQUIRED")
    if (pr.get("number") != 523 or pr.get("state") != "open" or pr.get("merged") is not False
            or pr.get("base", {}).get("ref") != "main"
            or pr.get("base", {}).get("repo", {}).get("full_name") != AMO_REPOSITORY
            or pr.get("head", {}).get("repo", {}).get("full_name") != AMO_REPOSITORY
            or pr.get("head", {}).get("ref") != AMO_OWNER_CI_REF or pr.get("head", {}).get("sha") != head):
        raise ExecutorBlock("AMO_PR523_HEAD_DRIFT")
    if (subject.get("repository") != AMO_REPOSITORY or subject.get("source_head") != head
            or subject.get("source_tree") != tree
            or subject.get("unsigned_xpi_sha256") != request["unsigned_xpi_sha256"]):
        raise ExecutorBlock("AMO_OWNER_CI_PACKAGE_CHANGED")
    return {"schema": request["schema"], "mode": "DIRECT_OWNER_TESTED_PUSH",
        "authorization_source": request["authorization_source"], "authorized_at": request["authorized_at"],
        "repository": AMO_REPOSITORY, "pull_request": 523, "source_head": head, "source_tree": tree,
        "unsigned_xpi_sha256": request["unsigned_xpi_sha256"], "test_result": "success",
        "independent_approval": False, "changes_main_admission": False, "effect_ack_done": False}


def amo_validate_owner_ci(root: Path, environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Reobserve the current PR and rebuild the existing exact six-component input."""
    env = os.environ if environment is None else environment
    from tools.qikvrt_self_host import firefox_amo_input
    head, tree = _git(root, "rev-parse", "HEAD"), _git(root, "rev-parse", "HEAD^{tree}")
    _raw, subject = firefox_amo_input(root, head, tree)
    context = {key: env.get(name, "") for key, name in {
        "repository": "GITHUB_REPOSITORY", "event": "GITHUB_EVENT_NAME", "actor": "GITHUB_ACTOR",
        "triggering_actor": "GITHUB_TRIGGERING_ACTOR", "ref": "GITHUB_REF",
        "workflow_ref": "GITHUB_WORKFLOW_REF", "workflow_sha": "GITHUB_WORKFLOW_SHA",
        "event_head": "GITHUB_SHA", "test_result": "AMO_TEST_RESULT",
        "tested_head": "AMO_TESTED_HEAD", "tested_tree": "AMO_TESTED_TREE"}.items()}
    context.update(head=head, tree=tree, run_attempt=int(env.get("GITHUB_RUN_ATTEMPT", "0")))
    pr = _amo_get(root, f"repos/{AMO_REPOSITORY}/pulls/523")
    return amo_owner_ci_admission(root, context, subject, pr)


def amo_signing_predecessor(root: Path, run_id: int, run_attempt: int,
                            requested: int, read=None) -> int:
    """Read both admitted producer histories before resuming the existing journal."""
    if (type(run_id) is not int or run_id <= 0 or type(run_attempt) is not int or run_attempt != 1
            or type(requested) is not int or requested < 0):
        raise ExecutorBlock("AMO_USE_FRESH_READBACK_DISPATCH_NOT_RERUN")
    read = read or (lambda path: _amo_get(root, f"repos/{AMO_REPOSITORY}" + path))
    histories = [("event=workflow_dispatch", "2026-10-14T17:06:35Z"),
        ("event=push&branch=" + urllib.parse.quote(AMO_OWNER_CI_REF, safe=""), AMO_OWNER_CI_AUTHORIZED_AT)]
    candidates = []
    for query, cutoff in histories:
        for runs in _amo_run_pages(read, "/actions/workflows/qikvrt_ci.yml/runs?" + query,
                                   "AMO_PREDECESSOR_RUN_INVENTORY_INCOMPLETE"):
            stop = False
            for run in runs:
                created = run.get("created_at", "")
                if not isinstance(created, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", created):
                    raise ExecutorBlock("AMO_PREDECESSOR_RUN_BINDING_INVALID")
                if created < cutoff:
                    stop = True; break
                if (type(run.get("id")) is not int or run["id"] <= 0 or run.get("path") != AMO_CI_WORKFLOW
                        or run.get("repository", {}).get("full_name") != AMO_REPOSITORY
                        or run.get("head_repository", {}).get("full_name") != AMO_REPOSITORY
                        or run.get("event") != ("push" if query.startswith("event=push") else "workflow_dispatch")
                        or (run["event"] == "push" and run.get("head_branch") != AMO_OWNER_CI_REF)):
                    raise ExecutorBlock("AMO_PREDECESSOR_RUN_BINDING_INVALID")
                if run["id"] == run_id:
                    continue
                jobs = read("/actions/runs/" + str(run["id"]) + "/jobs?filter=all&per_page=100").get("jobs")
                if not isinstance(jobs, list) or len(jobs) >= 100:
                    raise ExecutorBlock("AMO_PREDECESSOR_JOB_INVENTORY_INCOMPLETE")
                active = any(job.get("name") == "Mozilla AMO unlisted access and exact-source signing"
                    and any(step.get("name") == "Official source-bound unlisted signing and original-byte readback"
                        and step.get("started_at") and step.get("conclusion") != "skipped"
                        for step in job.get("steps", [])) for job in jobs)
                if active:
                    candidates.append((created, run["id"])); stop = True; break
            if stop:
                break
    previous = max(candidates, default=("", 0))[1]
    if requested not in (0, previous):
        raise ExecutorBlock("AMO_PREDECESSOR_BINDING_MISMATCH")
    return previous


def amo_intent(root: Path, context: Mapping[str, Any], authority: Mapping[str, Any],
               branch: Mapping[str, Any], rules: Sequence[Mapping[str, Any]],
               subject: Mapping[str, Any], previous: Mapping[str, Any] | None,
               history_verified: bool) -> dict[str, Any]:
    """Pure admission. Secret values are neither accepted nor fingerprinted."""
    request = amo_request(root)
    head, tree = _sha(context.get("head"), "AMO Main head"), _sha(context.get("tree"), "AMO Main tree")
    run_id = context.get("run_id")
    if (context.get("repository") != AMO_REPOSITORY or context.get("ref") != "refs/heads/main"
            or context.get("event") not in {"workflow_run", "workflow_dispatch", "push"}
            or context.get("workflow_ref") != f"{AMO_REPOSITORY}/{AMO_NATIVE_WORKFLOW}@refs/heads/main"
            or type(run_id) is not int or not 0 < run_id < 10 ** 20
            or context.get("run_attempt") != 1
            or authority.get("repository") != AMO_REPOSITORY
            or authority.get("main_head") != head or authority.get("main_tree") != tree
            or authority.get("state") != "AUTHORITY_MAIN_ROLE_POLICY_REOBSERVED"):
        raise ExecutorBlock("AMO_TRUSTED_NATIVE_MAIN_REQUIRED")
    amo_native_protection(branch, rules)
    if (subject.get("repository") != AMO_REPOSITORY or subject.get("source_head") != head
            or subject.get("source_tree") != tree
            or subject.get("unsigned_xpi_sha256") != request["unsigned_xpi_sha256"]):
        raise ExecutorBlock("AMO_OWNER_PACKAGE_CHANGED")
    revision = context.get("binding_revision", "initial") or "initial"
    if not isinstance(revision, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", revision):
        raise ExecutorBlock("AMO_BINDING_REVISION_INVALID")
    if any(type(context.get(k)) is not bool for k in ("issuer_present", "secret_present")):
        raise ExecutorBlock("AMO_PRESENCE_BOOLEAN_REQUIRED")
    if not history_verified:
        raise ExecutorBlock("AMO_PREDECESSOR_HISTORY_UNVERIFIED")
    fingerprint = sha256_bytes(canonical_json_bytes({"scope": AMO_SCOPE,
        "package": request["unsigned_xpi_sha256"], "binding_revision": revision,
        "repository": AMO_REPOSITORY, "ref": "main"}))
    result = {"schema": AMO_SCHEMA, "scope": AMO_SCOPE, "repository": AMO_REPOSITORY,
        "head": head, "tree": tree, "ref": "main", "executor_run_id": run_id,
        "request_sha256": sha256_bytes(canonical_json_bytes(request)),
        "unsigned_xpi_sha256": request["unsigned_xpi_sha256"], "binding_revision": revision,
        "fingerprint": fingerprint, "last_attempt": None, "dispatch": False, "history_verified": True,
        "readback_only": False,
        "credential_delivery": amo_credential_delivery(context),
        "effect_ack_done": False, "public_production_verified": False,
        "state": "HOLD_AMO_AUTHORIZED_CREDENTIAL_PAIR_UNAVAILABLE"}
    if previous is not None:
        if (previous.get("schema") != AMO_SCHEMA or previous.get("scope") != AMO_SCOPE
                or previous.get("repository") != AMO_REPOSITORY
                or previous.get("effect_ack_done") is not False
                or "last_attempt" not in previous):
            raise ExecutorBlock("AMO_PREDECESSOR_JOURNAL_INVALID")
        prior = previous["last_attempt"]
        if prior is not None:
            required = {"fingerprint", "head", "tree", "executor_run_id", "target_run_id", "state",
                        "readback_only", "unsigned_xpi_sha256"}
            if (not isinstance(prior, dict) or set(prior) != required
                    or not re.fullmatch(r"[a-f0-9]{64}", str(prior.get("fingerprint", "")))
                    or not SHA_RE.fullmatch(str(prior.get("head", "")))
                    or not SHA_RE.fullmatch(str(prior.get("tree", "")))
                    or type(prior.get("executor_run_id")) is not int
                    or type(prior.get("target_run_id")) is not int
                    or prior["executor_run_id"] <= 0 or prior["target_run_id"] < 0
                    or type(prior.get("readback_only")) is not bool
                    or not re.fullmatch(r"[a-f0-9]{64}", str(prior.get("unsigned_xpi_sha256", "")))
                    or prior.get("state") not in {"AMBIGUOUS", "ACCEPTED", "FAILED",
                        "CI_PENDING", "READBACK_PENDING", "SIGNED", "SOURCE_DRIFT", "RECOVERED_PRE_EFFECT", "ABORTED"}):
                raise ExecutorBlock("AMO_PREDECESSOR_ATTEMPT_INVALID")
            result["last_attempt"] = dict(prior)
            if "github_feedback" in previous:
                result["github_feedback"] = previous["github_feedback"]
            state = prior["state"]
            if prior["unsigned_xpi_sha256"] != request["unsigned_xpi_sha256"]:
                raise ExecutorBlock("AMO_PREDECESSOR_PACKAGE_CHANGED")
            if state == "SIGNED":
                result["state"] = "SIGNING_SOURCE_BOUND"
                return result
            if state in {"AMBIGUOUS", "ACCEPTED", "CI_PENDING"}:
                result["state"] = "HOLD_EXISTING_DISPATCH_READBACK"
                return result
            if state in {"ABORTED", "READBACK_PENDING"} and not prior["readback_only"]:
                # GitHub's terminal event, never elapsed time, permits a separate
                # GET-only recovery. It never permits a replacement upload.
                result["readback_only"] = True
            if state in {"ABORTED", "READBACK_PENDING"} and prior["readback_only"]:
                result["state"] = "NOOP_AWAIT_NEW_PROVIDER_EVIDENCE"
                return result
            if (prior["fingerprint"] == fingerprint and state not in {"ABORTED", "READBACK_PENDING", "RECOVERED_PRE_EFFECT"}
                    and not (state == "SOURCE_DRIFT" and prior["head"] != head)):
                result["state"] = "NOOP_UNCHANGED_SIGNING_FAILURE"
                return result
    if context["issuer_present"] and context["secret_present"]:
        result.update(state="DISPATCH_CANDIDATE_READY", dispatch=True)
    return result


def amo_dispatch_body(intent: Mapping[str, Any], intent_sha256: str) -> dict[str, Any]:
    if (intent.get("schema") != AMO_SCHEMA or intent.get("dispatch") is not True
            or intent.get("state") != "DISPATCH_CANDIDATE_READY"
            or intent.get("repository") != AMO_REPOSITORY or intent.get("ref") != "main"
            or not re.fullmatch(r"[a-f0-9]{64}", intent_sha256)):
        raise ExecutorBlock("AMO_ADMITTED_INTENT_REQUIRED")
    return {"ref": "main", "return_run_details": True, "inputs": {
        "amo_sign_unlisted": True, "amo_expected_head": _sha(intent.get("head"), "AMO head"),
        "amo_expected_tree": _sha(intent.get("tree"), "AMO tree"), "amo_previous_run_id": "0",
        "amo_executor_run_id": str(intent["executor_run_id"]), "amo_intent_sha256": intent_sha256,
        "amo_readback_only": intent["readback_only"]}}


def amo_dispatch_record(intent: Mapping[str, Any], response: Mapping[str, Any] | None) -> dict[str, Any]:
    """An absent/invalid response stays ambiguous, including a lost HTTP ACK."""
    if intent.get("dispatch") is not True or intent.get("state") != "DISPATCH_CANDIDATE_READY":
        raise ExecutorBlock("AMO_ADMITTED_INTENT_REQUIRED")
    value = dict(intent)
    target = response.get("workflow_run_id") if isinstance(response, Mapping) else None
    accepted = (type(target) is int and 0 < target < 10 ** 20
        and response.get("run_url") == f"https://api.github.com/repos/{AMO_REPOSITORY}/actions/runs/{target}"
        and response.get("html_url") == f"https://github.com/{AMO_REPOSITORY}/actions/runs/{target}")
    denied = isinstance(response, Mapping) and response.get("denied_http_status") in (400, 401, 403, 404, 422)
    value["last_attempt"] = {"fingerprint": intent["fingerprint"], "head": intent["head"],
        "tree": intent["tree"], "executor_run_id": intent["executor_run_id"],
        "target_run_id": target if accepted else 0,
        "readback_only": intent["readback_only"],
        "unsigned_xpi_sha256": intent["unsigned_xpi_sha256"],
        "state": "ACCEPTED" if accepted else ("FAILED" if denied else "AMBIGUOUS")}
    value.update(dispatch=False, state="DISPATCH_ACCEPTED_PENDING_READBACK" if accepted else "HOLD_DISPATCH_OUTCOME_UNVERIFIED")
    if not accepted:
        value["first_boundary"] = "AMO_DISPATCH_DENIED_" + str(response["denied_http_status"]) if denied else "AMO_DISPATCH_ACK_UNVERIFIED"
    return value


def _amo_get(root: Path, endpoint: str, binary: bool = False) -> Any:
    if not os.environ.get("GH_TOKEN") or not endpoint.startswith(f"repos/{AMO_REPOSITORY}/"):
        raise ExecutorBlock("AMO_NATIVE_REPOSITORY_TOKEN_REQUIRED")
    try:
        response = subprocess.run(["gh", "api", "--hostname", "github.com", "--method", "GET", endpoint],
            cwd=root, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ExecutorBlock("AMO_GITHUB_GET_UNVERIFIED") from None
    if response.returncode:
        status = re.search(rb"HTTP (\d{3})", response.stderr)
        raise ExecutorBlock("AMO_GITHUB_GET_DENIED_" + (status.group(1).decode() if status else "UNKNOWN"))
    if len(response.stdout) > 2 * 1_048_576:
        raise ExecutorBlock("AMO_GITHUB_READ_CAPACITY_LIMIT")
    if binary:
        return response.stdout
    return _amo_object(b'{"data":' + response.stdout + b'}')["data"]


def _amo_run_pages(read, endpoint: str, incomplete: str):
    """Keep strict byte limits while reading the same bounded run history.

    GitHub repeats repository metadata in every row. Twenty-row pages avoid
    the observed 1 MiB overflow; no rows, original journals or lost ACKs are
    discarded. Count drift, repeated rows and API search truncation hold.
    A consumer may stop early only on its existing verified causal boundary.
    """
    seen, total = set(), None
    separator = "&" if "?" in endpoint else "?"
    for page in range(1, AMO_RUN_HISTORY_BUDGET // AMO_RUN_PAGE_SIZE + 1):
        value = read(endpoint + separator + f"per_page={AMO_RUN_PAGE_SIZE}&page={page}")
        if not isinstance(value, Mapping):
            raise ExecutorBlock(incomplete)
        rows, count = value.get("workflow_runs"), value.get("total_count")
        if (not isinstance(rows, list) or len(rows) > AMO_RUN_PAGE_SIZE
                or type(count) is not int or count < 0 or (total is not None and count != total)):
            raise ExecutorBlock(incomplete)
        total = count
        for row in rows:
            identifier = row.get("id") if isinstance(row, Mapping) else None
            if type(identifier) is not int or identifier <= 0 or identifier in seen:
                raise ExecutorBlock(incomplete)
            seen.add(identifier)
        if len(seen) > total:
            raise ExecutorBlock(incomplete)
        yield rows
        if len(seen) == total:
            return
        if len(rows) < AMO_RUN_PAGE_SIZE:
            raise ExecutorBlock(incomplete)
    raise ExecutorBlock(incomplete)


def _amo_competing_writer(root: Path, writers: Sequence[str]) -> bool:
    for status in sorted(ACTIVE_RUN_STATUSES):
        endpoint = f"repos/{AMO_REPOSITORY}/actions/runs?branch=main&status={status}"
        for runs in _amo_run_pages(lambda path: _amo_get(root, path), endpoint,
                                   "AMO_ACTIVE_WRITER_INVENTORY_INCOMPLETE"):
            if any(run.get("status") != status for run in runs):
                raise ExecutorBlock("AMO_ACTIVE_WRITER_INVENTORY_INCOMPLETE")
            if any(run.get("name") in writers for run in runs):
                return True
    return False


def amo_artifact(root: Path, run_id: int, name: str, allowed: set[str]) -> dict[str, bytes] | None:
    value = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or value.get("total_count") != len(artifacts) or len(artifacts) >= 100:
        raise ExecutorBlock("AMO_ARTIFACT_INVENTORY_INCOMPLETE")
    matches = [a for a in artifacts if a.get("name") == name]
    if not matches:
        return None
    if len(matches) != 1:
        raise ExecutorBlock("AMO_ORIGINAL_ARTIFACT_AMBIGUOUS")
    item = matches[0]
    if (item.get("expired") is not False or type(item.get("id")) is not int
            or item.get("workflow_run", {}).get("id") != run_id
            or not re.fullmatch(r"sha256:[a-f0-9]{64}", str(item.get("digest", "")))
            or type(item.get("size_in_bytes")) is not int or not 0 < item["size_in_bytes"] <= 2 * 1_048_576):
        raise ExecutorBlock("AMO_ORIGINAL_ARTIFACT_UNAVAILABLE")
    raw = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/artifacts/{item['id']}/zip", binary=True)
    if sha256_bytes(raw) != item["digest"][7:] or len(raw) != item["size_in_bytes"]:
        raise ExecutorBlock("AMO_ORIGINAL_ARTIFACT_DIGEST_MISMATCH")
    result = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for entry in archive.infolist():
                if (entry.filename not in allowed or entry.filename in result or entry.is_dir()
                        or not 0 < entry.file_size <= 1_048_576
                        or entry.external_attr >> 16 & 0o170000 not in (0, 0o100000)):
                    raise ExecutorBlock("AMO_CLOSED_ARTIFACT_INVENTORY_REQUIRED")
                result[entry.filename] = archive.read(entry)
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError):
        raise ExecutorBlock("AMO_ORIGINAL_ARTIFACT_BYTES_INVALID") from None
    return result


def amo_run(root: Path, run_id: int, workflow: str) -> dict[str, Any]:
    value = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{run_id}")
    if (value.get("id") != run_id or value.get("path") != workflow
            or value.get("repository", {}).get("full_name") != AMO_REPOSITORY
            or value.get("head_branch") != "main" or value.get("run_attempt") != 1
            or value.get("event") not in {"schedule", "workflow_dispatch", "push", "workflow_run"}
            or not SHA_RE.fullmatch(str(value.get("head_sha", "")))):
        raise ExecutorBlock("AMO_ORIGINAL_RUN_IDENTITY_INVALID")
    return value


def amo_previous(root: Path, current_run_id: int) -> tuple[dict[str, Any] | None, bool]:
    """Carry the last attempt through original native artifacts, never a chat cache."""
    baseline = amo_request(root)["pre_activation_main"]
    current = amo_run(root, current_run_id, AMO_NATIVE_WORKFLOW)
    current_order = (current.get("created_at", ""), current_run_id)
    endpoint = f"repos/{AMO_REPOSITORY}/actions/workflows/qikvrt_workflow_executor.yml/runs?branch=main"
    for runs in _amo_run_pages(lambda path: _amo_get(root, path), endpoint,
                               "AMO_NATIVE_HISTORY_INCOMPLETE"):
        for run in runs:
            if run.get("id") == current_run_id:
                continue
            prior_id = run.get("id")
            if type(prior_id) is not int or prior_id <= 0:
                raise ExecutorBlock("AMO_NATIVE_HISTORY_ID_INVALID")
            if (run.get("created_at", ""), prior_id) >= current_order:
                continue
            if run.get("head_sha") == baseline["head"]:
                # Exact protected-Main lineage, not elapsed time, bounds the
                # first activation. This old source did not have this producer.
                # No earlier admitted invocation can precede its introduction.
                original = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{prior_id}")
                if (original.get("id") != prior_id or original.get("path") != AMO_NATIVE_WORKFLOW
                        or original.get("repository", {}).get("full_name") != AMO_REPOSITORY
                        or original.get("head_branch") != "main" or original.get("head_sha") != baseline["head"]):
                    raise ExecutorBlock("AMO_PRE_ACTIVATION_RUN_MISMATCH")
                source = _amo_get(root, f"repos/{AMO_REPOSITORY}/contents/{CONTRACT_RELATIVE_PATH}?ref={baseline['head']}")
                raw = base64.b64decode("".join(source.get("content", "").split()), validate=True)
                blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
                if (blob != baseline["contract_blob"] or source.get("sha") != blob
                        or source.get("path") != CONTRACT_RELATIVE_PATH or source.get("type") != "file"
                        or source.get("encoding") != "base64" or source.get("size") != len(raw)
                        or AMO_SCOPE in _amo_object(raw).get("owner_authorized_operations", {})):
                    raise ExecutorBlock("AMO_PRE_ACTIVATION_SOURCE_UNVERIFIED")
                return None, True
            original = amo_run(root, prior_id, AMO_NATIVE_WORKFLOW)
            jobs = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{prior_id}/jobs?per_page=100")
            if jobs.get("total_count") != len(jobs.get("jobs", [])) or len(jobs.get("jobs", [])) >= 100:
                raise ExecutorBlock("AMO_NATIVE_JOB_INVENTORY_INCOMPLETE")
            matching = [j for j in jobs["jobs"] if j.get("name") == AMO_JOB]
            if len(matching) > 1:
                raise ExecutorBlock("AMO_PREDECESSOR_JOB_AMBIGUOUS")
            if not matching:
                # An older workflow without this separately authorized producer
                # cannot have issued its dispatch. Verify that source, not timing.
                source = _amo_get(root, f"repos/{AMO_REPOSITORY}/contents/{CONTRACT_RELATIVE_PATH}?ref={original['head_sha']}")
                raw = base64.b64decode("".join(source.get("content", "").split()), validate=True)
                blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
                if source.get("sha") != blob:
                    raise ExecutorBlock("AMO_PREDECESSOR_SOURCE_UNVERIFIED")
                contract = _amo_object(raw)
                if AMO_SCOPE not in contract.get("owner_authorized_operations", {}):
                    # A later old-source run cannot erase an earlier producer.
                    continue
                # A still queued producer has no proof that POST cannot start.
                raise ExecutorBlock("AMO_PREDECESSOR_PRODUCER_JOB_UNOBSERVED")
            if matching[0].get("conclusion") == "skipped":
                continue
            journal = amo_artifact(root, prior_id, f"qikvrt-amo-continuation-{prior_id}",
                                   {"intent.json", "receipt.json", "AI_PROGRESS.json", "AI_STATUS.md"})
            if journal and "receipt.json" in journal:
                receipt = _amo_object(journal["receipt.json"])
                if receipt.get("executor_run_id") != prior_id:
                    raise ExecutorBlock("AMO_PREDECESSOR_ARTIFACT_RUN_MISMATCH")
                if receipt.get("history_verified") is not True:
                    # A failed pre-effect inventory cannot erase older duties.
                    if any(s.get("name") == AMO_DISPATCH_STEP and s.get("started_at")
                           and s.get("conclusion") != "skipped" for s in matching[0].get("steps", [])):
                        raise ExecutorBlock("AMO_UNVERIFIED_HISTORY_AFTER_DISPATCH")
                    continue
                return amo_reconcile(root, receipt), True
            intent = amo_artifact(root, prior_id, f"qikvrt-amo-intent-{prior_id}", {"intent.json"})
            if intent and "intent.json" in intent:
                receipt = _amo_object(intent["intent.json"])
                if receipt.get("executor_run_id") != prior_id:
                    raise ExecutorBlock("AMO_PREDECESSOR_ARTIFACT_RUN_MISMATCH")
                dispatched = any(s.get("name") == AMO_DISPATCH_STEP and s.get("started_at")
                    and s.get("conclusion") != "skipped" for s in matching[0].get("steps", []))
                if not dispatched and matching[0].get("status") != "completed":
                    raise ExecutorBlock("AMO_PREDECESSOR_DISPATCH_STILL_POSSIBLE")
                return amo_reconcile(root, amo_dispatch_record(receipt, None) if dispatched else receipt), True
            if any(s.get("name") == AMO_DISPATCH_STEP and s.get("started_at")
                   and s.get("conclusion") != "skipped" for s in matching[0].get("steps", [])):
                raise ExecutorBlock("AMO_PREDECESSOR_ORIGINAL_ARTIFACT_MISSING")
            if matching[0].get("status") != "completed":
                raise ExecutorBlock("AMO_PREDECESSOR_INTENT_NOT_YET_PUBLISHED")
            # Platform job metadata proves this failed setup never entered POST.
            # Continue to the older original journal rather than resetting it.
    return None, True


def amo_reconcile(root: Path, receipt: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(receipt)
    prior = value.get("last_attempt")
    if not isinstance(prior, dict) or prior.get("state") not in {"AMBIGUOUS", "ACCEPTED", "CI_PENDING", "ABORTED"}:
        return value
    prior = dict(prior)
    target = prior.get("target_run_id")
    if type(target) is not int or target <= 0:
        caller = amo_run(root, prior["executor_run_id"], AMO_NATIVE_WORKFLOW)
        found = []
        endpoint = f"repos/{AMO_REPOSITORY}/actions/workflows/qikvrt_ci.yml/runs?event=workflow_dispatch"
        for runs in _amo_run_pages(lambda path: _amo_get(root, path), endpoint,
                                   "AMO_ACK_READBACK_HISTORY_INCOMPLETE"):
            stop = False
            for candidate in runs:
                if candidate.get("created_at", "") < caller.get("created_at", ""):
                    stop = True
                    break
                if candidate.get("head_sha") != prior["head"] or candidate.get("actor", {}).get("login") != "github-actions[bot]":
                    continue
                candidate_id = candidate.get("id")
                if type(candidate_id) is not int or candidate_id <= 0:
                    raise ExecutorBlock("AMO_ACK_READBACK_RUN_ID_INVALID")
                original = amo_artifact(root, candidate_id, f"qikvrt-amo-unlisted-{prior['head']}",
                    {"ACCESS_PREFLIGHT.json", "AMO_ATTEMPT.json", "AMO_SIGNING_RECEIPT.json", "standard-signed.xpi"})
                if original and "ACCESS_PREFLIGHT.json" in original:
                    access = _amo_object(original["ACCESS_PREFLIGHT.json"])
                    if str(access.get("executor_run_id")) == str(prior["executor_run_id"]):
                        found.append(candidate_id)
            if stop:
                break
        if len(found) != 1:
            if len(found) > 1:
                raise ExecutorBlock("AMO_ACK_READBACK_AMBIGUOUS")
            return value
        target = prior["target_run_id"] = found[0]
    run = amo_run(root, target, AMO_CI_WORKFLOW)
    if run.get("head_sha") != prior.get("head") or run.get("event") != "workflow_dispatch":
        raise ExecutorBlock("AMO_DISPATCH_TARGET_SOURCE_MISMATCH")
    jobs = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{target}/jobs?per_page=100")
    if jobs.get("total_count") != len(jobs.get("jobs", [])):
        raise ExecutorBlock("AMO_TARGET_JOB_INVENTORY_INCOMPLETE")
    value["github_feedback"] = amo_feedback(run, jobs["jobs"])
    signing_jobs = [j for j in jobs.get("jobs", []) if j.get("name") == "Mozilla AMO unlisted access and exact-source signing"]
    if len(signing_jobs) > 1:
        raise ExecutorBlock("AMO_TARGET_SIGNING_JOB_AMBIGUOUS")
    # A hung compile/deploy job must not hide a finished signing effect.
    if not signing_jobs or signing_jobs[0].get("status") != "completed":
        if run.get("status") != "completed":
            prior["state"] = "CI_PENDING"
        else:
            prior["state"] = "ABORTED" if run.get("conclusion") in {"cancelled", "timed_out"} else "FAILED"
    else:
        original = amo_artifact(root, target, f"qikvrt-amo-unlisted-{prior['head']}",
            {"ACCESS_PREFLIGHT.json", "AMO_ATTEMPT.json", "AMO_SIGNING_RECEIPT.json", "standard-signed.xpi"})
        if (not original or "ACCESS_PREFLIGHT.json" not in original) and signing_jobs[0].get("conclusion") in {"cancelled", "timed_out"}:
            prior["state"] = "ABORTED"
            value["last_attempt"] = prior
            return value
        if not original or "ACCESS_PREFLIGHT.json" not in original:
            raise ExecutorBlock("AMO_TARGET_ORIGINAL_PREFLIGHT_MISSING")
        access = _amo_object(original["ACCESS_PREFLIGHT.json"])
        if str(access.get("executor_run_id")) != str(prior.get("executor_run_id")):
            raise ExecutorBlock("AMO_TARGET_CALLER_READBACK_MISMATCH")
        boundary = access.get("first_boundary")
        if isinstance(boundary, str) and re.fullmatch(r"AMO_[A-Z0-9_]{1,100}", boundary):
            value["github_feedback"]["source_boundary"] = boundary
        signed = _amo_object(original["AMO_SIGNING_RECEIPT.json"]) if "AMO_SIGNING_RECEIPT.json" in original else {}
        if signed and (signed.get("source_head") != prior["head"]
                or signed.get("source_tree") != prior["tree"]
                or signed.get("unsigned_xpi_sha256") != prior["unsigned_xpi_sha256"]):
            raise ExecutorBlock("AMO_TARGET_COMPONENT_READBACK_MISMATCH")
        if isinstance(signed.get("state"), str) and re.fullmatch(r"[A-Z][A-Z0-9_]{1,150}", signed["state"]):
            value["github_feedback"]["signing_state"] = signed["state"]
        if signed.get("signed_original_returned") is True:
            signed_bytes = original.get("standard-signed.xpi")
            if (not signed_bytes or signed.get("xpi_sha256") != sha256_bytes(signed_bytes)
                    or signed.get("xpi_bytes") != len(signed_bytes)):
                raise ExecutorBlock("AMO_TARGET_SIGNED_ORIGINAL_BYTES_UNVERIFIED")
            prior["state"] = "SIGNED"
        elif signed.get("state") in {"PENDING_AMO_REVIEW_OR_SIGNING_READBACK_ONLY",
                                     "HOLD_AMO_EXISTING_VERSION_NOT_OBSERVED_READBACK_ONLY"}:
            prior["state"] = "READBACK_PENDING"
        elif access.get("first_boundary") == "AMO_DELEGATION_MAIN_HEAD_DRIFT":
            official = [s for s in signing_jobs[0].get("steps", [])
                        if s.get("name") == "Official source-bound unlisted signing and original-byte readback"]
            if len(official) != 1 or official[0].get("conclusion") != "skipped":
                raise ExecutorBlock("AMO_SOURCE_DRIFT_PRE_EFFECT_PROOF_REQUIRED")
            prior["state"] = "SOURCE_DRIFT"
        elif signing_jobs[0].get("conclusion") in {"cancelled", "timed_out"}:
            prior["state"] = "ABORTED"
        else:
            prior["state"] = "FAILED"
    value["last_attempt"] = prior
    return value


def amo_feedback(run: Mapping[str, Any], jobs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Only provider statuses and bounded diagnostics; cancellation cause may be absent."""
    statuses = {"queued", "in_progress", "completed", "waiting", "pending", "requested"}
    conclusions = {None, "success", "failure", "neutral", "cancelled", "skipped", "timed_out",
                   "action_required", "stale", "startup_failure"}
    def status(item):
        if item.get("status") not in statuses or item.get("conclusion") not in conclusions:
            raise ExecutorBlock("AMO_GITHUB_STATUS_UNRECOGNIZED")
        return {"status": item["status"], "conclusion": item.get("conclusion")}
    result = {"schema": "qikvrt-github-run-feedback/v1", "run_id": run["id"],
              "run_url": f"https://github.com/{AMO_REPOSITORY}/actions/runs/{run['id']}",
              **status(run), "reason": "NOT_EXPOSED_BY_GITHUB", "jobs": []}
    for job in jobs:
        if type(job.get("id")) is not int or not isinstance(job.get("name"), str) or len(job["name"]) > 200:
            raise ExecutorBlock("AMO_GITHUB_JOB_DIAGNOSTIC_INVALID")
        observed = {"id": job["id"], "name": job["name"], **status(job), "steps": []}
        for step in job.get("steps", []):
            if type(step.get("number")) is not int or not isinstance(step.get("name"), str) or len(step["name"]) > 200:
                raise ExecutorBlock("AMO_GITHUB_STEP_DIAGNOSTIC_INVALID")
            observed["steps"].append({"number": step["number"], "name": step["name"], **status(step)})
        result["jobs"].append(observed)
    return result


def github_failure_codes(raw: bytes) -> dict[str, Any]:
    """Return only closed diagnostic shapes, never arbitrary error or log text."""
    text = raw.decode("utf-8", errors="replace")
    failures = sorted({suite if suite.endswith("." + test) else f"{suite}.{test}" for test, suite in re.findall(
        r"\b(?:FAIL|ERROR): (test_[A-Za-z0-9_]{1,150}) \((tests\.[A-Za-z0-9_.]{1,200})\)", text)})
    exits = sorted({int(code) for code in re.findall(r"\bMAKE_TEST_EXIT=([0-9]{1,3})\b", text)
                    if 0 < int(code) < 256})
    result = {"failed_tests": failures[:100], "make_test_exit_codes": exits}
    if re.search(r"has exceeded the maximum execution time of [0-9]+ minutes", text):
        result["provider_reason_code"] = "GITHUB_JOB_EXECUTION_LIMIT"
    elif "Canceling since a higher priority waiting request" in text:
        result["provider_reason_code"] = "GITHUB_CONCURRENCY_SUPERSEDED"
    return result


def github_failure_feedback(root: Path, feedback: Mapping[str, Any]) -> dict[str, Any]:
    """One bounded original-log GET per failed job; no polling or raw-log output."""
    value = dict(feedback)
    value["jobs"] = [dict(job) for job in feedback["jobs"]]
    for job in value["jobs"]:
        if job["conclusion"] not in {"failure", "cancelled", "timed_out", "startup_failure"}:
            continue
        try:
            raw = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/jobs/{job['id']}/logs", binary=True)
            job["diagnostics"] = github_failure_codes(raw)
            job["diagnostics"]["source"] = "ORIGINAL_GITHUB_JOB_LOG"
            job["diagnostics"]["raw_log_returned"] = False
        except ExecutorBlock:
            job["diagnostics"] = {"state": "ORIGINAL_LOG_UNAVAILABLE", "raw_log_returned": False}
    return value


def amo_event(root: Path, context: Mapping[str, Any]) -> dict[str, Any] | None:
    """Authenticate GitHub's push notification by an independent original-run GET."""
    if context.get("event") != "workflow_run":
        return None
    try:
        raw = Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes()
        event = _amo_object(raw)
        source = event["workflow_run"]
        run_id = source["id"]
        if (event.get("action") != "completed" or event.get("repository", {}).get("full_name") != AMO_REPOSITORY
                or source.get("name") != "QIKVRT CI" or source.get("head_branch") != "main"
                or source.get("head_repository", {}).get("full_name") != AMO_REPOSITORY
                or source.get("event") != "workflow_dispatch" or source.get("status") != "completed"
                or type(run_id) is not int or run_id <= 0):
            raise ExecutorBlock("AMO_UNRELATED_GITHUB_COMPLETION_EVENT")
        original = amo_run(root, run_id, AMO_CI_WORKFLOW)
        if any(source.get(k) != original.get(k) for k in ("id", "head_sha", "status", "conclusion", "run_attempt", "event")):
            raise ExecutorBlock("AMO_GITHUB_COMPLETION_EVENT_MISMATCH")
        return original
    except (OSError, KeyError, TypeError):
        raise ExecutorBlock("AMO_GITHUB_COMPLETION_EVENT_UNVERIFIED") from None


CONTINUATION_WORKFLOWS = {
    ".github/workflows/qikvrt_ci.yml": "CI",
    ".github/workflows/qikvrt_temdd.yml": "CD",
    ".github/workflows/qikvrt_workflow_executor_watchdog.yml": "CO",
}


def continuation_graph(run: Mapping[str, Any], jobs: Sequence[Mapping[str, Any]],
                       tested_subject: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Adapt sibling priority from successful original jobs, retaining all gates.

    This is the QIK-VRT continuation graph, not a modification of GitHub's
    schema. Durations guide order only; they never transfer gate acceptance.
    Callers must independently read the original run and complete job inventory.
    """
    from datetime import datetime
    if (run.get("path") not in CONTINUATION_WORKFLOWS
            or type(run.get("id")) is not int or run["id"] <= 0
            or type(run.get("run_attempt")) is not int or run["run_attempt"] <= 0
            or not SHA_RE.fullmatch(str(run.get("head_sha", "")))
            or run.get("repository", {}).get("full_name") != AMO_REPOSITORY
            or run.get("head_repository", {}).get("full_name") != AMO_REPOSITORY
            or not 0 < len(jobs) < 100
            or any(type(j.get("id")) is not int or j["id"] <= 0 for j in jobs)
            or len({j["id"] for j in jobs}) != len(jobs)):
        raise ExecutorBlock("CONTINUATION_ORIGINAL_RUN_AND_JOBS_REQUIRED")
    succeeded = run.get("status") == "completed" and run.get("conclusion") == "success"
    timings = []
    for job in jobs:
        if (not isinstance(job.get("name"), str) or not 0 < len(job["name"]) <= 200
                or job.get("status") != "completed"):
            succeeded = False
        if job.get("conclusion") not in {"success", "skipped"}:
            succeeded = False
        if job.get("conclusion") == "success":
            try:
                start = datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
                seconds = (end - start).total_seconds()
                if start.tzinfo is None or end.tzinfo is None or not 0 <= seconds <= 86400:
                    raise ValueError("invalid job duration")
                timings.append({"job_id": job["id"], "name": job["name"], "seconds": seconds})
            except (KeyError, TypeError, ValueError, AttributeError):
                pass  # Unknown timing is never a synthetic zero-cost success.
    timings = sorted(timings, key=lambda j: (-j["seconds"], j["job_id"])) if succeeded else []
    parallel_ci = {"offline_browser (chromium)", "offline_browser (webkit)",
                   "Linux S1 native terminal production and smoke"}
    sibling_priority = ([j for j in timings if j["name"] in parallel_ci]
                        if run["path"] == AMO_CI_WORKFLOW else [])
    ordered_children = [j["name"] for j in sibling_priority]
    ordered_children += sorted(parallel_ci - set(ordered_children))
    required = {"test", "offline_browser (chromium)", "offline_browser (webkit)",
                "Linux S1 native terminal production and smoke"}
    accepted = {j.get("name") for j in jobs if j.get("conclusion") == "success"}
    bound = (isinstance(tested_subject, Mapping)
             and tested_subject.get("schema") == "qikvrt-ci-tested-subject/v1"
             and tested_subject.get("repository") == AMO_REPOSITORY
             and type(tested_subject.get("run_id")) is int and tested_subject["run_id"] == run["id"]
             and type(tested_subject.get("run_attempt")) is int
             and tested_subject["run_attempt"] == run.get("run_attempt")
             and all(SHA_RE.fullmatch(str(tested_subject.get(k, ""))) for k in ("head_sha", "tree_sha")))
    return {"schema": "qikvrt-continuation-graph/v1", "run_id": run["id"],
            "event_head_sha": run["head_sha"],
            "head_sha": tested_subject["head_sha"] if bound else run["head_sha"],
            "tree_sha": tested_subject["tree_sha"] if bound else None,
            "workflow_stage": CONTINUATION_WORKFLOWS[run["path"]],
            "provider_metadata_sha256": sha256_bytes(canonical_json_bytes({"run": run, "jobs": jobs})),
            "tested_subject": dict(tested_subject) if bound else None,
            "ci_verified": bool(bound and succeeded and run["path"] == AMO_CI_WORKFLOW and required <= accepted),
            "success_learning": succeeded, "successful_job_timings": timings,
            "sibling_priority": sibling_priority, "sibling_dependency": "test",
            "skipped_jobs": [j["id"] for j in jobs if j.get("conclusion") == "skipped"],
            "nodes": [{"id": "source", "requires": []},
                      {"id": "review", "requires": ["source"]},
                      {"id": "ci", "requires": ["source"], "mandatory_root": "test",
                       "independent_children": ordered_children},
                      {"id": "graphql-fallback", "requires": ["review", "ci"],
                       "operation": "markPullRequestReadyForReview", "never_prune": True},
                      {"id": "rest-merge", "requires": ["graphql-fallback"],
                       "fresh_expected_head_admission_required": True}],
            "learning_scope": "ORDER_INDEPENDENT_CI_SIBLINGS_ONLY; NEVER_SKIP_GATES",
            "graph_source_mutation": False, "effect_ack_done": False}


def continuation_frontier(graph: Mapping[str, Any], pr: Mapping[str, Any],
                          review: Mapping[str, Any]) -> dict[str, Any]:
    """Advance the retained graph from fresh source/review/CI/readiness evidence.

    A merge frontier requests the existing fresh merge admission; it never
    grants or executes a merge. Unknown or failed gates keep their branches.
    """
    value = json.loads(json.dumps(graph))
    admitted = graph.get("ci_verified") is True and review.get("gate_state") == "success"
    states = {"source": "VERIFIED", "review": "VERIFIED" if review.get("gate_state") == "success" else "OPEN",
              "ci": "VERIFIED" if graph.get("ci_verified") else "OPEN",
              "graphql-fallback": "VERIFIED" if pr.get("draft") is False else "READY" if admitted else "WAITING",
              "rest-merge": "RECHECK_REQUIRED" if admitted and pr.get("draft") is False else "WAITING"}
    for node in value["nodes"]:
        node["state"] = states[node["id"]]
    value["frontier"] = [n["id"] for n in value["nodes"] if n["state"] in {"READY", "RECHECK_REQUIRED"}]
    value["merge_admission_inferred"] = False
    return value


def github_completion_feedback(root: Path = ROOT) -> dict[str, Any]:
    """Read CI completion diagnostics without executing code from the triggering run."""
    context = amo_context()
    if (context["event"] != "workflow_run" or context["repository"] != AMO_REPOSITORY
            or context["ref"] != "refs/heads/main"
            or context["workflow_ref"] != f"{AMO_REPOSITORY}/{AMO_NATIVE_WORKFLOW}@refs/heads/main"):
        raise ExecutorBlock("AMO_TRUSTED_NATIVE_MAIN_REQUIRED")
    try:
        event = _amo_object(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes())
        source = event["workflow_run"]
        run_id = source["id"]
        if (event.get("action") != "completed" or event.get("repository", {}).get("full_name") != AMO_REPOSITORY
                or type(run_id) is not int or run_id <= 0
                or source.get("head_repository", {}).get("full_name") != AMO_REPOSITORY):
            raise ExecutorBlock("AMO_UNRELATED_GITHUB_COMPLETION_EVENT")
        run = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{run_id}")
        if (run.get("repository", {}).get("full_name") != AMO_REPOSITORY
                or run.get("head_repository", {}).get("full_name") != AMO_REPOSITORY
                or run.get("path") not in CONTINUATION_WORKFLOWS
                or run.get("status") != "completed"
                or any(run.get(k) != source.get(k) for k in ("id", "head_sha", "conclusion", "run_attempt", "event"))):
            raise ExecutorBlock("AMO_GITHUB_COMPLETION_EVENT_MISMATCH")
        jobs = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{run_id}/jobs?per_page=100")
        if jobs.get("total_count") != len(jobs.get("jobs", [])):
            raise ExecutorBlock("AMO_TARGET_JOB_INVENTORY_INCOMPLETE")
        feedback = github_failure_feedback(root, amo_feedback(run, jobs["jobs"]))
        try:
            tested = None
            if run.get("conclusion") == "success" and run.get("path") == AMO_CI_WORKFLOW:
                artifact = amo_artifact(root, run_id,
                    f"qikvrt-ci-tested-subject-{run_id}-{run['run_attempt']}", {"TESTED_SUBJECT.json"})
                if artifact is not None:
                    tested = _amo_object(artifact["TESTED_SUBJECT.json"])
            feedback["continuation_graph"] = continuation_graph(run, jobs["jobs"], tested)
        except ExecutorBlock:
            # A failed learner must not erase the original provider outcome.
            feedback["continuation_graph"] = {"schema": "qikvrt-continuation-graph/v1",
                "state": "UNVERIFIED", "ci_verified": False, "success_learning": False,
                "fallback_retained": True, "sibling_priority": [], "effect_ack_done": False}
        return feedback
    except (OSError, KeyError, TypeError):
        raise ExecutorBlock("AMO_GITHUB_COMPLETION_EVENT_UNVERIFIED") from None


def amo_context(environment: Mapping[str, str] = os.environ) -> dict[str, Any]:
    try:
        return {"repository": environment.get("GITHUB_REPOSITORY"), "ref": environment.get("GITHUB_REF"),
            "workflow_ref": environment.get("GITHUB_WORKFLOW_REF"), "event": environment.get("GITHUB_EVENT_NAME"),
            "head": environment.get("GITHUB_SHA"), "run_id": int(environment.get("GITHUB_RUN_ID", "0")),
            "run_attempt": int(environment.get("GITHUB_RUN_ATTEMPT", "0")),
            "issuer_present": environment.get("AMO_ISSUER_PRESENT") == "true",
            "secret_present": environment.get("AMO_SECRET_PRESENT") == "true",
            "binding_revision": environment.get("AMO_BINDING_REVISION", "initial") or "initial"}
    except ValueError:
        raise ExecutorBlock("AMO_NATIVE_CONTEXT_INVALID") from None


def amo_live_plan(root: Path = ROOT) -> dict[str, Any]:
    context = amo_context()
    previous, verified = None, False
    try:
        if (context["repository"] != AMO_REPOSITORY or context["ref"] != "refs/heads/main"
                or context["workflow_ref"] != f"{AMO_REPOSITORY}/{AMO_NATIVE_WORKFLOW}@refs/heads/main"
                or context["event"] not in {"workflow_run", "push", "workflow_dispatch"}
                or context["run_attempt"] != 1 or context["run_id"] <= 0):
            raise ExecutorBlock("AMO_TRUSTED_NATIVE_MAIN_REQUIRED")
        context["tree"] = _git(root, "rev-parse", "HEAD^{tree}")
        if _git(root, "rev-parse", "HEAD") != context["head"]:
            raise ExecutorBlock("AMO_LOCAL_MAIN_HEAD_DRIFT")
        event = amo_event(root, context)
        previous, verified = amo_previous(root, context["run_id"])
        if event is not None and (previous is None or not isinstance(previous.get("last_attempt"), dict)
                or previous["last_attempt"].get("target_run_id") != event["id"]):
            # Duplicate or out-of-order notifications cannot replace a newer attempt.
            raise ExecutorBlock("AMO_UNRELATED_OR_SUPERSEDED_COMPLETION_EVENT")
        authority = read_authority_main(root)
        branch = _amo_get(root, f"repos/{AMO_REPOSITORY}/branches/main")
        rules = _amo_get(root, f"repos/{AMO_REPOSITORY}/rules/branches/main")
        if not isinstance(rules, list):
            raise ExecutorBlock("AMO_NATIVE_RULES_INVALID")
        try:
            from tools import qikvrt_self_host as host
        except ModuleNotFoundError:
            import qikvrt_self_host as host
        _, subject = host.firefox_amo_input(root, context["head"], context["tree"])
        result = amo_intent(root, context, authority, branch, rules, subject, previous, verified)
        if (event is not None and result.get("dispatch") is True and result.get("readback_only") is not True
                and not (previous["last_attempt"].get("state") == "SOURCE_DRIFT"
                         and previous["last_attempt"].get("head") != context["head"])):
            result.update(state="NOOP_COMPLETION_EVENT_CANNOT_START_UPLOAD", dispatch=False)
        writers = load_contract(root)["dispatch_policy"]["writer_workflow_names"]
        if (result.get("dispatch") is True and not result.get("readback_only")
                and _amo_competing_writer(root, writers)):
            result.update(state="HOLD_COMPETING_AUTHORITY_WRITER", dispatch=False)
        return result
    except (ExecutorBlock, ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        code = str(exc)
        if not re.fullmatch(r"[A-Z][A-Z0-9_ ]{1,100}", code):
            code = "AMO_NATIVE_ADMISSION_UNVERIFIED"
        return {"schema": AMO_SCHEMA, "scope": AMO_SCOPE, "repository": AMO_REPOSITORY,
            "executor_run_id": context.get("run_id", 0), "head": context.get("head"),
            "history_verified": verified, "last_attempt": previous.get("last_attempt") if previous else None,
            "dispatch": False, "state": "HOLD", "first_boundary": code,
            "credential_delivery": amo_credential_delivery(context),
            "effect_ack_done": False, "public_production_verified": False}


def amo_validate_delegation(root: Path = ROOT) -> None:
    """Authenticate a bot invocation by the pre-published original Main intent."""
    env = os.environ
    try:
        caller_id, target_id = int(env.get("AMO_EXECUTOR_RUN_ID", "0")), int(env.get("GITHUB_RUN_ID", "0"))
    except ValueError:
        raise ExecutorBlock("AMO_DELEGATION_RUN_ID_INVALID") from None
    head, tree = env.get("EXPECTED_HEAD"), env.get("EXPECTED_TREE")
    if (caller_id <= 0 or target_id <= 0 or env.get("GITHUB_ACTOR") != "github-actions[bot]"
            or env.get("GITHUB_REPOSITORY") != AMO_REPOSITORY
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_WORKFLOW_REF") != f"{AMO_REPOSITORY}/{AMO_CI_WORKFLOW}@refs/heads/main"
            or env.get("GITHUB_RUN_ATTEMPT") != "1" or env.get("GITHUB_SHA") != head
            or not SHA_RE.fullmatch(str(head)) or not SHA_RE.fullmatch(str(tree))
            or _git(root, "rev-parse", "HEAD") != head or _git(root, "rev-parse", "HEAD^{tree}") != tree):
        raise ExecutorBlock("AMO_DELEGATION_NATIVE_MAIN_REQUIRED")
    live = _amo_get(root, f"repos/{AMO_REPOSITORY}/git/ref/heads/main")
    if live.get("object", {}).get("sha") != head:
        raise ExecutorBlock("AMO_DELEGATION_MAIN_HEAD_DRIFT")
    authority = read_authority_main(root)
    if authority.get("main_head") != head or authority.get("main_tree") != tree:
        raise ExecutorBlock("AMO_DELEGATION_MAIN_HEAD_DRIFT")
    amo_native_protection(_amo_get(root, f"repos/{AMO_REPOSITORY}/branches/main"),
                          _amo_get(root, f"repos/{AMO_REPOSITORY}/rules/branches/main"))
    caller = amo_run(root, caller_id, AMO_NATIVE_WORKFLOW)
    if caller.get("head_sha") != head:
        raise ExecutorBlock("AMO_DELEGATION_CALLER_SOURCE_DRIFT")
    original = amo_artifact(root, caller_id, f"qikvrt-amo-intent-{caller_id}", {"intent.json"})
    if not original or "intent.json" not in original:
        raise ExecutorBlock("AMO_DELEGATION_ORIGINAL_INTENT_REQUIRED")
    raw = original["intent.json"]
    if sha256_bytes(raw) != env.get("AMO_INTENT_SHA256"):
        raise ExecutorBlock("AMO_DELEGATION_INTENT_DIGEST_MISMATCH")
    intent = _amo_object(raw)
    request = amo_request(root)
    if (intent.get("schema") != AMO_SCHEMA or intent.get("scope") != AMO_SCOPE
            or intent.get("repository") != AMO_REPOSITORY or intent.get("ref") != "main"
            or intent.get("head") != head or intent.get("tree") != tree
            or intent.get("executor_run_id") != caller_id or intent.get("dispatch") is not True
            or intent.get("state") != "DISPATCH_CANDIDATE_READY"
            or intent.get("history_verified") is not True
            or intent.get("request_sha256") != sha256_bytes(canonical_json_bytes(request))
            or intent.get("unsigned_xpi_sha256") != request["unsigned_xpi_sha256"]):
        raise ExecutorBlock("AMO_DELEGATION_EXACT_INTENT_REQUIRED")
    try:
        from tools import qikvrt_self_host as host
    except ModuleNotFoundError:
        import qikvrt_self_host as host
    _, subject = host.firefox_amo_input(root, head, tree)
    if subject["unsigned_xpi_sha256"] != intent["unsigned_xpi_sha256"]:
        raise ExecutorBlock("AMO_DELEGATION_OWNER_PACKAGE_CHANGED")
    jobs = _amo_get(root, f"repos/{AMO_REPOSITORY}/actions/runs/{caller_id}/jobs?per_page=100")
    if jobs.get("total_count") != len(jobs.get("jobs", [])):
        raise ExecutorBlock("AMO_DELEGATION_CALLER_JOB_INVENTORY_INCOMPLETE")
    steps = [s for j in jobs.get("jobs", []) if j.get("name") == AMO_JOB
             for s in j.get("steps", []) if s.get("name") == AMO_DISPATCH_STEP]
    if len(steps) != 1 or not steps[0].get("started_at") or steps[0].get("conclusion") == "skipped":
        raise ExecutorBlock("AMO_DELEGATION_CALLER_DISPATCH_NOT_STARTED")
    if (env.get("AMO_READBACK_ONLY") == "true") is not intent.get("readback_only"):
        raise ExecutorBlock("AMO_DELEGATION_READBACK_MODE_MISMATCH")
    # The exact owner request and pre-published original intent grant this
    # capability. Do not wait for the caller to return or upload its later ACK.
    # Writer serialization and the existing pre-PUT journal remain mandatory.
    return


def amo_write(directory: Path, filename: str, raw: bytes) -> None:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or not directory.is_dir() or directory.stat().st_uid != os.getuid():
        raise ExecutorBlock("AMO_OWNED_OUTPUT_DIRECTORY_REQUIRED")
    temporary = directory / (".amo-" + os.urandom(16).hex())
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / filename)
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def amo_progress(directory: Path, receipt: Mapping[str, Any]) -> None:
    amo_write(directory, "receipt.json", canonical_json_bytes(receipt))
    signed = receipt.get("state") == "SIGNING_SOURCE_BOUND"
    attempt = receipt.get("last_attempt")
    accepted = isinstance(attempt, dict) and type(attempt.get("target_run_id")) is int and attempt["target_run_id"] > 0
    boundary = receipt.get("first_boundary") or receipt["state"]
    progress = {"schema": "qikvrt_human_machine_progress_v1", "repository": AMO_REPOSITORY,
        "operation": "Protected Firefox signing continuation; activation and public delivery remain unverified",
        "status": "BLOCK", "progressPercent": 67 if signed else (33 if accepted else 0),
        "gates": [
            {"name": "Protected exact-source signing dispatch", "state": "PASS" if accepted else "BLOCK",
             "evidence": str(receipt.get("executor_run_id", "unverified"))},
            {"name": "Original source-bound signed XPI", "state": "PASS" if signed else "BLOCK",
             "evidence": boundary},
            {"name": "Firefox activation and exact public domain delivery", "state": "BLOCK",
             "evidence": "Not established by signing, dispatch or completion feedback"}]}
    amo_write(directory, "AI_PROGRESS.json", canonical_json_bytes(progress))
    human = ("# Protected signing continuation\n\nState: " + receipt["state"]
        + "\n\nBoundary: " + boundary
        + "\n\nSigning admission and dispatch are separate from Firefox activation and public delivery.\n")
    amo_write(directory, "AI_STATUS.md", human.encode())
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write(human + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("amo-plan", "amo-pre-dispatch", "amo-record"):
        amo = subcommands.add_parser(name)
        amo.add_argument("--output-dir", type=Path, required=True)
    subcommands.add_parser("amo-delegation-check")
    feedback = subcommands.add_parser("github-completion-feedback")
    feedback.add_argument("--output-dir", type=Path, required=True)
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
        if arguments.command == "github-completion-feedback":
            value = github_completion_feedback()
            amo_write(arguments.output_dir, "GITHUB_RUN_FEEDBACK.json", canonical_json_bytes(value))
            print("GITHUB_ORIGINAL_CONCLUSION=" + str(value["conclusion"]))
            print("GITHUB_ABORT_REASON=" + value["reason"])
            return 0
        elif arguments.command == "amo-plan":
            value = amo_live_plan()
            amo_write(arguments.output_dir, "intent.json", canonical_json_bytes(value))
            amo_progress(arguments.output_dir, value)
            print("AMO_CONTINUATION_STATE=" + value["state"])
            return 0
        elif arguments.command == "amo-pre-dispatch":
            raw = (arguments.output_dir / "intent.json").read_bytes()
            intent = _amo_object(raw)
            fresh = amo_live_plan()
            if fresh.get("dispatch") is not True or canonical_json_bytes(fresh) != raw:
                amo_progress(arguments.output_dir, fresh)
                raise ExecutorBlock("AMO_DISPATCH_PREREQUISITES_CHANGED")
            body = amo_dispatch_body(intent, sha256_bytes(raw))
            amo_write(arguments.output_dir, "dispatch-input.json", canonical_json_bytes(body))
            print("AMO_EXACT_DISPATCH_ADMISSION=VERIFIED")
            return 0
        elif arguments.command == "amo-record":
            intent = _amo_object((arguments.output_dir / "intent.json").read_bytes())
            try:
                response = _amo_object((arguments.output_dir / "dispatch-response.json").read_bytes())
            except (OSError, ExecutorBlock):
                response = None
            value = amo_dispatch_record(intent, response)
            amo_progress(arguments.output_dir, value)
            print("AMO_CONTINUATION_STATE=" + value["state"])
            return 0
        elif arguments.command == "amo-delegation-check":
            amo_validate_delegation()
            print("AMO_NATIVE_DELEGATION=VERIFIED")
            return 0
        elif arguments.command == "roles":
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
