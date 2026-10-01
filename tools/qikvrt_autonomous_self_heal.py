#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded repository-native QIK-VRT self-healing controller."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
DEPENDENCY_POLICY = ROOT / "policy/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION_V1.json"
DELEGATION = (
    ROOT
    / "state/authorization/delegations/"
    "OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json"
)
PROMOTION_CONDITIONS = (
    "CURRENT_BASE_REOBSERVED",
    "HEAD_UNCHANGED",
    "DIFF_ALLOWLISTED",
    "NO_EXTERNAL_EFFECT",
    "ALL_APPLICABLE_GATES_TERMINAL_GREEN",
    "NO_COMPETING_WRITER",
)


class SelfHealBlock(RuntimeError):
    pass


# A trusted workflow copies this controller before checking out a candidate.
# Generated projections/data are outside the control plane. New workflow/test/
# policy/tool paths are included automatically, so additions cannot evade it.
PIPELINE_PREFIXES = (
    ".github/workflows/", "tools/", "tests/", "runtime/toolchains/",
    "policy/", "state/autonomy/", "state/authorization/", "src/",
)
PIPELINE_FILES = {".gitattributes", "AI", "AI_CONTEXT.json", "AGENTS.md", "AI_ADAPTERS.json", "Makefile"}
PIPELINE_REQUIRED = {"Makefile", "AGENTS.md", "tools/qikvrt_autonomous_self_heal.py"}
PIPELINE_SCHEMA = "qikvrt_pipeline_binding_v1"


def _pipeline_path(path: str) -> bool:
    return path in PIPELINE_FILES or path.startswith(PIPELINE_PREFIXES)


def pipeline_binding(repository: pathlib.Path, reference: str | None = None) -> dict[str, Any]:
    """Bounded read-only inventory of exact Git checkout bytes and modes.

    A reference is an externally selected trusted full SHA, never candidate data.
    Without a reference, include tracked and untracked protected working files.
    This local filesystem/Git observation does not authenticate an external node.
    """
    root = repository.resolve(strict=True)
    if reference is not None and (len(reference) != 40
            or any(c not in "0123456789abcdef" for c in reference)):
        raise SelfHealBlock("pipeline reference must be a full Git SHA-1")
    command = (["git", "ls-tree", "-r", "-l", "-z", "--full-tree", reference]
               if reference else ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"])
    try:
        raw = subprocess.check_output(command, cwd=root, timeout=60, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise SelfHealBlock("pipeline Git observation failed") from exc
    if len(raw) > 4 * 1024 * 1024:
        raise SelfHealBlock("pipeline inventory bound exceeded")
    entries = {}
    total_bytes = 0
    for item in raw.split(b"\0"):
        if not item:
            continue
        if reference:
            metadata, path_raw = item.split(b"\t", 1)
            mode, kind, blob, raw_size = metadata.decode("ascii").split()
            path = path_raw.decode("utf-8")
        else:
            path = item.decode("utf-8")
        if not _pipeline_path(path):
            continue
        if reference:
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise SelfHealBlock("pipeline requires regular files: " + path)
            if int(raw_size) > 16 * 1024 * 1024:
                raise SelfHealBlock("pipeline reference file size rejected: " + path)
            try:
                # Reference bytes must use the trusted checkout's Git attributes:
                # e.g. LF blobs become CRLF PowerShell files on checkout. This
                # runs before candidate checkout under trusted runner Git config.
                content = subprocess.check_output(
                    ["git", "cat-file", "--filters", reference + ":" + path],
                    cwd=root, timeout=60, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as exc:
                raise SelfHealBlock("pipeline reference checkout observation failed") from exc
            if len(content) > 16 * 1024 * 1024:
                raise SelfHealBlock("pipeline filtered file size rejected: " + path)
        else:
            file = root / path
            if any(parent.is_symlink() for parent in file.parents if parent != root):
                raise SelfHealBlock("pipeline parent symlink: " + path)
            before = file.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_size > 16 * 1024 * 1024:
                raise SelfHealBlock("pipeline file type/size rejected: " + path)
            content = file.read_bytes()
            after = file.lstat()
            if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
                    after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode):
                raise SelfHealBlock("pipeline file changed while reading: " + path)
            mode = "100755" if before.st_mode & 0o111 else "100644"
        total_bytes += len(content)
        if total_bytes > 256 * 1024 * 1024:
            raise SelfHealBlock("pipeline total byte bound exceeded")
        blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        entries[path] = {"path": path, "mode": mode, "blob": blob}
    if not PIPELINE_REQUIRED <= set(entries) or len(entries) > 10000:
        raise SelfHealBlock("pipeline inventory incomplete or excessive")
    records = [entries[path] for path in sorted(entries)]
    digest = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema": PIPELINE_SCHEMA, "records": records, "sha256": digest}


def verify_pipeline_binding(expected: Any, observed: Any) -> None:
    for binding in (expected, observed):
        if (not isinstance(binding, dict) or set(binding) != {"schema", "records", "sha256"}
                or binding["schema"] != PIPELINE_SCHEMA or not isinstance(binding["records"], list)):
            raise SelfHealBlock("malformed pipeline binding")
        records = binding["records"]
        if len(records) > 10000 or any(not isinstance(r, dict)
                or set(r) != {"path", "mode", "blob"} or not isinstance(r["path"], str)
                or r["mode"] not in {"100644", "100755"} or not isinstance(r["blob"], str)
                or len(r["blob"]) != 40 or any(c not in "0123456789abcdef" for c in r["blob"])
                for r in records):
            raise SelfHealBlock("malformed pipeline records")
        paths = [r["path"] for r in records]
        if (paths != sorted(set(paths)) or not PIPELINE_REQUIRED <= set(paths)
                or any(not _pipeline_path(p) for p in paths)):
            raise SelfHealBlock("pipeline record coverage/order differs")
        digest = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if binding["sha256"] != digest:
            raise SelfHealBlock("pipeline binding digest mismatch")
    if expected != observed:
        raise SelfHealBlock("PIPELINE_INVARIANT_MISMATCH_REQUIRES_SEPARATE_REVIEW")


def continuation_verification_decision(statuses: Any) -> str:
    """A clean NOOP still needs its dedicated verifier. Never blind redispatch.

    Statuses must come from the authenticated exact-commit status GET. Existing
    status is only a readback obligation, never acceptance or independent review.
    """
    if not isinstance(statuses, list) or any(not isinstance(s, dict) for s in statuses):
        raise SelfHealBlock("malformed exact-head status response")
    existing = [s for s in statuses if s.get("context") == "QIKVRT autonomous exact-head verification"]
    if len(existing) > 1:
        raise SelfHealBlock("ambiguous dedicated verifier status")
    if not existing:
        return "DISPATCH_REQUIRED"
    if existing[0].get("state") not in {"pending", "success", "failure", "error"}:
        raise SelfHealBlock("unknown dedicated verifier state")
    return "EXISTING_VERIFICATION_REQUIRES_READBACK"


def ci_continuation_receipt(repository: pathlib.Path, reference: str | None,
                            outcome: str | None, repository_name: str | None,
                            event: str | None, run_id: int | None,
                            run_attempt: int | None) -> dict[str, Any]:
    """Consume the repository command; retain a finite run's next obligation.

    This read-only receipt neither dispatches a writer nor accepts the product.
    A failed test stays failed while the native continuation remains obligated.
    """
    if (reference is None or len(reference) != 40
            or any(c not in "0123456789abcdef" for c in reference)):
        raise SelfHealBlock("CI continuation requires an exact current HEAD")
    if (outcome not in {"success", "failure", "cancelled", "skipped"}
            or event not in {"push", "pull_request", "workflow_dispatch"}
            or type(run_id) is not int or run_id < 1
            or type(run_attempt) is not int or run_attempt < 1
            or not isinstance(repository_name, str) or repository_name.count("/") != 1):
        raise SelfHealBlock("CI execution witness is incomplete")
    root = repository.resolve(strict=True)
    if root != ROOT.resolve():
        raise SelfHealBlock("CI must consume its own repository-native controller")

    def git(*arguments: str) -> bytes:
        return subprocess.check_output(["git", *arguments], cwd=root,
                                       timeout=60, stderr=subprocess.PIPE)

    head, tree = git("rev-parse", "HEAD", "HEAD^{tree}").decode("ascii").splitlines()
    if head != reference:
        raise SelfHealBlock("CI continuation subject changed; fresh binding required")
    contract = load_contract()
    # Bind actual executed bytes, not the stale commit identity of a dirty tree.
    for path in (CONTRACT.relative_to(ROOT).as_posix(), DEPENDENCY_POLICY.relative_to(ROOT).as_posix(),
                 "tools/qikvrt_autonomous_self_heal.py", "tools/qikvrt_mesh_recovery.py",
                 "tools/qikvrt_seed_common.py", "tools/qikvrt_subprocess.py",
                 "tools/qikvrt_workflow_executor.py"):
        if git("show", head + ":" + path) != (root / path).read_bytes():
            raise SelfHealBlock("CI command bytes differ from the bound subject")
    if git("rev-parse", "HEAD").decode("ascii").strip() != head:
        raise SelfHealBlock("CI continuation subject changed during readback")
    return {
        "schema": "qikvrt_native_ci_continuation_receipt_v1",
        "owner_command": contract["continuous_integration"]["owner_command"],
        "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        "execution_routing": contract["execution_routing"],
        "dependency_policy_sha256": hashlib.sha256(DEPENDENCY_POLICY.read_bytes()).hexdigest(),
        "repository": repository_name, "head": head, "tree": tree,
        "execution": {"event": event, "run_id": run_id,
                      "run_attempt": run_attempt, "terminal_test_outcome": outcome},
        "state": "EFFECT_ACK_CONTINUE", "global_ci_stop": False,
        "next_required_action": ("REOBSERVE_ADMITTED_NATIVE_CONTINUATION"
                                 if outcome == "success" else
                                 "CLASSIFY_FAILURE_AND_EXECUTE_ONLY_ADMITTED_REPAIR"),
        "continuation_workflow": contract["pull_request_continuation"]["workflow_path"],
        "predecessor_evidence_transfer": False, "writer_authorization_implied": False,
        "ordinary_release": False, "effect_ack_done": False,
    }


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run(command: Sequence[str], timeout: int = 900) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(
        tuple(command),
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def _load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SelfHealBlock(f"{label} cannot be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise SelfHealBlock(f"{label} must be a JSON object")
    return value


def _validate_promotion_policy(
    policy: Any,
    *,
    proposal_workflow_may_merge: bool | None,
    standing_delegation: bool | None,
) -> Mapping[str, Any]:
    if not isinstance(policy, Mapping):
        raise SelfHealBlock("promotion policy is absent")
    if policy.get("unconditional_automatic_merge") != "FORBIDDEN":
        raise SelfHealBlock("unconditional automatic merge must remain forbidden")
    if policy.get("expected_head_bound_promotion") != "ALLOWED_ONLY_IF":
        raise SelfHealBlock("expected-head-bound promotion policy differs")
    if policy.get("conditions") != list(PROMOTION_CONDITIONS):
        raise SelfHealBlock("expected-head-bound promotion conditions differ")
    if policy.get("requires_existing_repository_bound_promotion_contract") is not True:
        raise SelfHealBlock("repository-bound promotion contract is required")
    if policy.get("general_auto_merge_authorization") is not False:
        raise SelfHealBlock("general automatic-merge authorization is forbidden")
    if (
        proposal_workflow_may_merge is not None
        and policy.get("proposal_workflow_may_merge")
        is not proposal_workflow_may_merge
    ):
        raise SelfHealBlock("proposal workflow promotion boundary differs")
    if (
        standing_delegation is not None
        and policy.get("standing_delegation") is not standing_delegation
    ):
        raise SelfHealBlock("standing promotion delegation differs")
    return policy


def load_delegation() -> dict[str, Any]:
    value = _load_json(DELEGATION, "autonomous continuation delegation")
    if value.get("schema") != "qikvrt_owner_autonomous_repository_continuation_v2":
        raise SelfHealBlock("delegation schema mismatch")
    if value.get("authorization_scope", {}).get("state") != "ACTIVE":
        raise SelfHealBlock("autonomous continuation delegation is not active")
    _validate_promotion_policy(
        value.get("promotion_policy"),
        proposal_workflow_may_merge=None,
        standing_delegation=True,
    )
    if "unconditional_automatic_merge_or_unbound_promotion" not in set(
        value.get("not_authorized", [])
    ):
        raise SelfHealBlock("delegation does not forbid unbound promotion")
    return value


def _validate_handlers(handlers: Any) -> list[dict[str, Any]]:
    if not isinstance(handlers, list) or not handlers:
        raise SelfHealBlock("allowlisted_handlers must be a non-empty list")
    result: list[dict[str, Any]] = []
    failure_classes: set[str] = set()
    for raw in handlers:
        if not isinstance(raw, dict):
            raise SelfHealBlock("each repair handler must be an object")
        failure_class = raw.get("failure_class")
        if not isinstance(failure_class, str) or not failure_class:
            raise SelfHealBlock("repair handler failure_class is missing")
        if failure_class in failure_classes:
            raise SelfHealBlock(f"duplicate repair handler: {failure_class}")
        failure_classes.add(failure_class)
        for key in ("probe", "repair", "mutable_paths"):
            value = raw.get(key)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item for item in value
            ):
                raise SelfHealBlock(f"{failure_class} has invalid {key}")
        signature = raw.get("failure_signature")
        if signature is not None and (
            not isinstance(signature, str) or not signature
        ):
            raise SelfHealBlock(f"{failure_class} has invalid failure_signature")
        result.append(raw)
    order = [handler["failure_class"] for handler in result]
    if (
        "PUBLICATION_OVERVIEW_DRIFT" in order
        and "REPOSITORY_NATIVE_INTEGRITY_STALE" in order
        and order.index("PUBLICATION_OVERVIEW_DRIFT")
        > order.index("REPOSITORY_NATIVE_INTEGRITY_STALE")
    ):
        raise SelfHealBlock("publication overview repair must precede integrity repair")
    return result


def load_contract() -> dict[str, Any]:
    value = _load_json(CONTRACT, "autonomous self-healing contract")
    if value.get("schema") != "qikvrt_autonomous_self_healing_contract_v1":
        raise SelfHealBlock("contract schema mismatch")
    routing = value.get("execution_routing", {})
    routing_required = {
        "rule_id": "QIKVRT_REPOSITORY_OWNS_EXECUTION_V1",
        "repository_tasks_executor": "REPOSITORY_NATIVE_CI_CD_AND_ADMITTED_MESH_EXECUTORS",
        "external_trigger_owns_repository_execution": False,
        "external_schedule_required_for_repository_liveness": False,
        "dependency_mirroring_policy": DEPENDENCY_POLICY.relative_to(ROOT).as_posix(),
        "dependency_mirroring_rule_id": "QIKVRT_CQF_POST_BINDING_REPOSITORY_MIRRORING_V1",
        "all_other_external_dependencies_in_scope": True,
        "external_dependency_after_successful_binding": "REPLACE_WITH_VERIFIED_REPOSITORY_MIRROR",
    }
    if (not isinstance(routing, dict) or any(type(routing.get(k)) is not type(v)
            or routing.get(k) != v for k, v in routing_required.items())):
        raise SelfHealBlock("repository execution and CQF mirroring invariant is absent or weakened")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from tools.qikvrt_mesh_recovery import RecoveryError, validate_dependency_mirroring_requirement
    except ImportError as exc:
        raise SelfHealBlock("repository dependency verifier closure is missing") from exc
    try:
        validate_dependency_mirroring_requirement(
            _load_json(DEPENDENCY_POLICY, "dependency mirroring policy"), required=True)
    except RecoveryError as exc:
        raise SelfHealBlock(str(exc)) from exc
    continuous = value.get("continuous_integration", {})
    owner = continuous.get("owner_command", {})
    if (owner.get("literal") != "Never stop CI" or owner.get("issuer") != "Ingolf Lohmann"
            or continuous.get("scope") != "REPOSITORY_NATIVE_CI"
            or continuous.get("active") is not True
            or any(continuous.get(key) is not False for key in (
                "first_success_terminal", "first_failure_terminal",
                "release_done_stops_ci", "blocked_lane_stops_global_ci"))
            or continuous.get("bounded_jobs_and_fail_closed_writers") is not True):
        raise SelfHealBlock("repository-native Never stop CI invariant is absent or weakened")
    execution_model = value.get("execution_model", {})
    if execution_model.get("promotion") != "expected_head_bound_only":
        raise SelfHealBlock("promotion must remain expected-head-bound")
    contract_policy = _validate_promotion_policy(
        value.get("promotion_policy"),
        proposal_workflow_may_merge=False,
        standing_delegation=None,
    )
    delegation = load_delegation()
    delegation_policy = delegation["promotion_policy"]
    if contract_policy["conditions"] != delegation_policy["conditions"]:
        raise SelfHealBlock("contract and delegation promotion conditions differ")
    if value.get("promotion_gate_order") != [
        "NEW_CURRENT_MAIN_DRAFT",
        "REPOSITORY_NATIVE_INTEGRITY_MATERIALIZATION",
        "EXACT_HEAD_GATES",
        "EXPECTED_HEAD_BOUND_PROMOTION",
    ]:
        raise SelfHealBlock("promotion gate order differs")
    forbidden = set(value.get("forbidden_effects", []))
    if not {
        "unconditional_automatic_merge",
        "unbound_or_stale_head_promotion",
        "force_push",
        "zenodo_mutation",
        "ietf_mutation",
        "deployment",
    }.issubset(forbidden):
        raise SelfHealBlock("forbidden-effect boundary differs")
    candidate = value.get("candidate_contract", {})
    if (
        candidate.get("pull_request_mode") != "draft"
        or candidate.get("deduplicate_by")
        != "base_revision_and_semantic_fingerprint"
        or candidate.get("proposal_workflow_may_merge") is not False
    ):
        raise SelfHealBlock("candidate review boundary differs")
    value["allowlisted_handlers"] = _validate_handlers(
        value.get("allowlisted_handlers")
    )
    return value


def allowed_paths(contract: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for handler in contract["allowlisted_handlers"]:
        result.update(handler["mutable_paths"])
    return result


def changed_paths() -> list[str]:
    result = run(("git", "diff", "--name-only", "--"), timeout=60)
    if result.returncode:
        raise SelfHealBlock(result.stderr.strip() or "git diff failed")
    return sorted(line for line in result.stdout.splitlines() if line)


def semantic_fingerprint(paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        payload = (ROOT / path).read_bytes()
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def candidate_identity(base_revision: str, fingerprint: str) -> str:
    if (
        len(base_revision) != 40
        or any(character not in "0123456789abcdef" for character in base_revision)
    ):
        raise SelfHealBlock("base revision is not a Git SHA-1")
    if (
        len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        raise SelfHealBlock("semantic fingerprint is not a SHA-256")
    payload = (
        base_revision.encode("ascii")
        + b"\0"
        + fingerprint.encode("ascii")
    )
    return hashlib.sha256(payload).hexdigest()


def observed_base_revision() -> str:
    result = run(("git", "rev-parse", "--verify", "HEAD^{commit}"), timeout=60)
    value = result.stdout.strip()
    if result.returncode or len(value) != 40:
        raise SelfHealBlock(result.stderr.strip() or "cannot bind current HEAD")
    return value


def repair_handler(handler: dict[str, Any]) -> dict[str, Any]:
    probe = run(tuple(handler["probe"]))
    if probe.returncode == 0:
        return {"failure_class": handler["failure_class"], "state": "NOOP"}
    combined = probe.stdout + "\n" + probe.stderr
    signature = handler.get("failure_signature")
    if signature and signature not in combined:
        raise SelfHealBlock(
            f"{handler['failure_class']} probe did not emit its exact failure signature"
        )
    if (
        handler["failure_class"] == "ANTICIPATION_PROJECTION_DRIFT"
        and "projection drift:" not in combined
    ):
        raise SelfHealBlock(
            "anticipation failure is not an allowlisted projection drift"
        )
    repair = run(tuple(handler["repair"]))
    if repair.returncode:
        raise SelfHealBlock(
            f"repair failed for {handler['failure_class']}: "
            f"{repair.stderr.strip() or repair.stdout.strip()}"
        )
    return {"failure_class": handler["failure_class"], "state": "REPAIRED"}


def execute(apply: bool) -> dict[str, Any]:
    contract = load_contract()
    initial = run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        timeout=60,
    )
    if initial.returncode or initial.stdout.strip():
        raise SelfHealBlock("controller requires a clean repository")
    base_revision = observed_base_revision()
    before_pipeline = pipeline_binding(ROOT)
    boot = run(
        (
            "python3",
            "-B",
            "tools/ai_runtime_bootloader.py",
            "--profile",
            "all",
            "--json",
        )
    )
    if boot.returncode not in (0, 2):
        raise SelfHealBlock("AI runtime bootloader returned an unrecognized state")
    actions: list[dict[str, Any]] = []
    if apply:
        for handler in contract["allowlisted_handlers"]:
            actions.append(repair_handler(handler))
    paths = changed_paths()
    unexpected = sorted(set(paths) - allowed_paths(contract))
    if unexpected:
        raise SelfHealBlock(f"non-allowlisted mutation: {unexpected}")
    verify_pipeline_binding(before_pipeline, pipeline_binding(ROOT))
    fingerprint = semantic_fingerprint(paths) if paths else None
    candidate_id = (
        candidate_identity(base_revision, fingerprint)
        if fingerprint is not None
        else None
    )
    state = "CANDIDATE_READY" if paths else "NOOP"
    return {
        "schema": "qikvrt_autonomous_self_heal_result_v1",
        "state": state,
        "observed_base_revision": base_revision,
        "semantic_fingerprint": fingerprint,
        "candidate_identity": candidate_id,
        "changed_paths": paths,
        "actions": actions,
        "pipeline_binding_sha256": before_pipeline["sha256"],
        "pipeline_invariant_verified": True,
        "external_effect": "NONE",
        "promotion_policy": {
            "unconditional_automatic_merge": "FORBIDDEN",
            "expected_head_bound_promotion": "ALLOWED_ONLY_IF",
            "conditions": list(PROMOTION_CONDITIONS),
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "FULL_SYNC": False,
            "SYMMETRIC_CANONICALITY": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "apply", "pipeline-bind", "pipeline-verify", "verification-decision", "ci-continuation"))
    parser.add_argument("--repository", type=pathlib.Path, default=ROOT)
    parser.add_argument("--reference")
    parser.add_argument("--binding", type=pathlib.Path)
    parser.add_argument("--statuses", type=pathlib.Path)
    parser.add_argument("--test-outcome")
    parser.add_argument("--repository-name")
    parser.add_argument("--event")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--run-attempt", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "ci-continuation":
            result = ci_continuation_receipt(args.repository, args.reference,
                args.test_outcome, args.repository_name, args.event,
                args.run_id, args.run_attempt)
        elif args.command == "pipeline-bind":
            result = pipeline_binding(args.repository, args.reference)
        elif args.command == "pipeline-verify":
            if args.binding is None:
                raise SelfHealBlock("trusted pipeline binding required")
            expected = _load_json(args.binding, "trusted pipeline binding")
            verify_pipeline_binding(expected, pipeline_binding(args.repository))
            result = {"state": "PIPELINE_INVARIANT_VERIFIED", "sha256": expected["sha256"],
                      "effect_ack_done": False}
        elif args.command == "verification-decision":
            if args.statuses is None:
                raise SelfHealBlock("authenticated exact-head statuses required")
            value = _load_json(args.statuses, "exact-head statuses")
            count = value.get("total_count")
            statuses = value.get("statuses")
            if (type(count) is not int or count < 0 or not isinstance(statuses, list)
                    or count != len(statuses)):
                raise SelfHealBlock("incomplete exact-head status inventory; readback required")
            result = {"state": continuation_verification_decision(statuses),
                      "effect_ack_done": False}
        else:
            result = execute(args.command == "apply")
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        SelfHealBlock,
    ) as exc:
        print(
            json.dumps(
                {
                    "state": "BLOCK",
                    "failure_class": "AUTONOMOUS_SELF_HEAL_BLOCKED",
                    "detail": str(exc),
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
