#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Expected-head-bound QIK-VRT decision core and qualified GraphQL CAS adapter.

Evaluation and preparation are read-only. The explicit publish-graphql command
admits one updateRefs only after independent qualification, fresh native gates
and durable intent persistence. Reconciliation is GET-only. The trusted workflow
keeps automatic Main promotion disabled until separately reviewed activation.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence
if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.qikvrt_required_review_gate import GOVERNANCE_STATUS_CONTEXT, SCHEMA as REVIEW_GATE_SCHEMA

PROMOTION_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
SUCCESS_CONCLUSIONS = {"success"}
NON_ADVERSE_CONCLUSIONS = {"success", "skipped"}
ROOT = pathlib.Path(__file__).resolve().parents[1]
QUALIFICATION_PATH = ROOT / "state/autonomy/TARGET_REF_CAS_QUALIFICATION_V1.json"
GRAPHQL_UPDATE_REFS = """mutation QikvrtPromote($input: UpdateRefsInput!) {
  updateRefs(input: $input) { clientMutationId }
}"""
CAS_QUALIFICATION_CASES = frozenset({
    "wrong_old_head", "non_fast_forward", "missing_review", "stale_review",
    "withdrawn_review", "failed_required_check", "missing_required_check",
    "reviewed_head_drift", "approved_exact_merge", "ambiguous_response_no_replay",
})


class PromotionBlock(ValueError):
    """Raised when a snapshot is structurally invalid rather than merely blocked."""


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise PromotionBlock(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise PromotionBlock(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _nonzero_sha(value: Any, label: str) -> str:
    value = _sha(value, label)
    if value == "0" * 40:
        raise PromotionBlock(f"{label} must not create or delete a reference")
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _run_number(run: Mapping[str, Any]) -> int:
    value = run.get("run_number", -1)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PromotionBlock("workflow run_number must be an integer")
    return value


def collapse_latest_runs(runs: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Return the newest run per workflow name.

    Trusted exact-head proxy execution can legitimately supersede an older
    action_required/zero-job registration on the same commit. Promotion must
    therefore use the newest observed execution for each workflow name rather
    than treating historical registrations as permanently adverse.
    """
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        if not isinstance(run, Mapping):
            raise PromotionBlock("workflow run must be an object")
        name = run.get("name")
        if not isinstance(name, str) or not name:
            raise PromotionBlock("workflow run name is missing")
        current = latest.get(name)
        if current is None or _run_number(run) > _run_number(current):
            latest[name] = run
    return latest


def _execution_blocker(run: Mapping[str, Any], repository: str, head: str, pr: int, *, required: bool) -> str | None:
    """Validate raw observed run/jobs; an API name or success label is insufficient."""
    run_repository, pulls = run.get("repository"), run.get("pull_requests")
    if (run.get("head_sha") != head or not isinstance(run_repository, Mapping) or
            run_repository.get("full_name") != repository or not isinstance(pulls, list) or
            run.get("event") != "pull_request" or
            not any(isinstance(item, Mapping) and item.get("number") == pr
                    for item in pulls)):
        return "WORKFLOW_SUBJECT_BINDING_MISMATCH"
    run_id, attempt = run.get("id"), run.get("run_attempt")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
           for value in (run_id, attempt)):
        return "WORKFLOW_EXECUTION_ID_MISSING"
    if not required and run.get("conclusion") == "skipped":
        return None  # Non-adverse only; never satisfies a required success gate.
    jobs = run.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        return "WORKFLOW_EXECUTED_JOB_EVIDENCE_MISSING"
    seen = set()
    executed = False
    for job in jobs:
        if not isinstance(job, Mapping):
            return "WORKFLOW_JOB_BINDING_MISMATCH"
        job_id = job.get("id")
        if (isinstance(job_id, bool) or not isinstance(job_id, int) or job_id < 1
                or job_id in seen or job.get("run_id") != run_id
                or type(job.get("run_id")) is not int or type(job.get("run_attempt")) is not int
                or job.get("run_attempt") != attempt or job.get("head_sha") != head):
            return "WORKFLOW_JOB_BINDING_MISMATCH"
        seen.add(job_id)
        if job.get("status") != "completed" or job.get("conclusion") not in NON_ADVERSE_CONCLUSIONS:
            return "WORKFLOW_JOB_NOT_TERMINAL_GREEN"
        if job.get("conclusion") == "success":
            steps = job.get("steps")
            if (not isinstance(steps, list) or not steps or
                    not any(isinstance(step, Mapping) and step.get("status") == "completed"
                            and step.get("conclusion") == "success" for step in steps) or
                    any(not isinstance(step, Mapping) or step.get("status") != "completed"
                        or step.get("conclusion") not in NON_ADVERSE_CONCLUSIONS for step in steps)):
                return "WORKFLOW_EXECUTED_STEP_EVIDENCE_MISSING"
            executed = True
    return None if executed else "WORKFLOW_EXECUTED_JOB_EVIDENCE_MISSING"


def _blocked(snapshot: Mapping[str, Any], failure_class: str, detail: str) -> dict[str, Any]:
    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "BLOCK",
        "first_blocker": failure_class,
        "detail": detail,
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": snapshot.get("expected_head_sha"),
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
        },
    }


def _hold(snapshot: Mapping[str, Any], failure_class: str, detail: str) -> dict[str, Any]:
    result = _blocked(snapshot, failure_class, detail)
    result["state"] = "HOLD"
    return result


def check_target_ref_cas(snapshot: Mapping[str, Any]) -> dict[str, Any] | None:
    """Validate the trusted executor's capability binding, never perform a write.

    A client-side GET followed by PATCH, workflow concurrency, or the PR merge
    API's head-SHA precondition does not establish an atomic old-Main predicate.
    This input must come from a verified executor adapter, not a candidate PR.
    The existing GitHub merge adapter declares the capability unavailable.
    """
    cas = snapshot.get("target_ref_cas")
    repository = snapshot.get("repository")
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise PromotionBlock("repository must be an owner/name binding")
    if not isinstance(cas, Mapping) or cas.get("state") != "VERIFIED":
        return _hold(snapshot, "ATOMIC_TARGET_REF_CAS_UNVERIFIED", "no verified server-side expected-old-HEAD ref operation")
    expected = {
        "repository": repository,
        "ref": "refs/heads/main",
        "operation": "SERVER_ATOMIC_REF_COMPARE_AND_SWAP",
        "comparison_scope": "TARGET_REF",
        "expected_old_sha": snapshot.get("base_sha"),
        "candidate_head_sha": snapshot.get("expected_head_sha"),
        "candidate_tree_sha": snapshot.get("expected_tree_sha"),
    }
    if any(cas.get(key) != value for key, value in expected.items()):
        return _hold(snapshot, "TARGET_REF_CAS_SUBJECT_MISMATCH", "CAS does not bind this repository, ref, base and candidate")
    if cas.get("server_atomic_compare_and_update") is not True or cas.get("force_update") is not False:
        return _hold(snapshot, "ATOMIC_TARGET_REF_CAS_UNVERIFIED", "atomic comparison and non-force update must be verified together")
    evidence = cas.get("evidence_sha256")
    if not isinstance(evidence, str) or not re.fullmatch(r"[0-9a-f]{64}", evidence):
        return _hold(snapshot, "TARGET_REF_CAS_EVIDENCE_MISSING", "the verified executor evidence must be digest-bound")
    return None


def qualify_target_ref_cas(snapshot: Mapping[str, Any], qualification: Mapping[str, Any],
                           *, adapter_sha256: str | None = None) -> dict[str, Any]:
    """Consume independently reviewed DEFAULT-BRANCH evidence, never certify it.

    No qualification is generated by unit tests or by the PR being promoted.
    This is an admission contract, not cryptographic proof of the attestations.
    """
    result = {
        "state": "UNAVAILABLE", "repository": snapshot.get("repository"),
        "ref": "refs/heads/main", "operation": "SERVER_ATOMIC_REF_COMPARE_AND_SWAP",
        "comparison_scope": "TARGET_REF", "expected_old_sha": snapshot.get("base_sha"),
        "candidate_head_sha": snapshot.get("expected_head_sha"),
        "candidate_tree_sha": snapshot.get("expected_tree_sha"),
        "server_atomic_compare_and_update": False, "force_update": False,
        "evidence_sha256": None,
    }
    adapter_sha256 = adapter_sha256 or hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    if not isinstance(qualification, Mapping):
        return result
    expected = {
        "schema": "qikvrt_graphql_ref_cas_qualification_v1", "state": "VERIFIED",
        "repository": snapshot.get("repository"), "target_ref": "refs/heads/main",
        "endpoint": "https://api.github.com/graphql", "adapter_sha256": adapter_sha256,
        "native_governance_independently_verified": True, "executor_bypass": False,
    }
    if any(qualification.get(k) != v for k, v in expected.items()):
        return result
    test_ref = qualification.get("protected_test_ref")
    principal = qualification.get("executor_login")
    verifier = qualification.get("independent_verifier")
    if (not isinstance(test_ref, str) or not test_ref.startswith("refs/heads/")
            or test_ref == "refs/heads/main" or not principal or not verifier
            or not isinstance(principal, str) or not isinstance(verifier, str)
            or principal.casefold() == verifier.casefold()):
        return result
    for key in ("effective_rules_sha256", "rulesets_sha256", "test_policy_sha256", "evidence_sha256"):
        if not isinstance(qualification.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", qualification[key]):
            return result
    if qualification["test_policy_sha256"] != qualification["effective_rules_sha256"]:
        return result
    cases = qualification.get("cases")
    if not isinstance(cases, Mapping) or set(cases) != CAS_QUALIFICATION_CASES:
        return result
    for name, case in cases.items():
        if (not isinstance(case, Mapping) or case.get("result") != "PASS"
                or case.get("repository") != qualification["repository"]
                or case.get("ref") != test_ref
                or not isinstance(case.get("receipt_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", case["receipt_sha256"])
                or not isinstance(case.get("receipt_url"), str)
                or not case["receipt_url"].startswith("https://")):
            return result
        if name not in {"approved_exact_merge", "ambiguous_response_no_replay"} and case.get("ref_unchanged") is not True:
            return result
    result.update(state="VERIFIED", server_atomic_compare_and_update=True,
                  evidence_sha256=_digest(qualification))
    return result


def _evaluate_promotion(snapshot: Mapping[str, Any], *, require_target_ref_cas: bool) -> dict[str, Any]:
    """Evaluate one promotion candidate against the live fail-closed contract."""
    if not isinstance(snapshot, Mapping):
        raise PromotionBlock("snapshot must be an object")

    current_main = _nonzero_sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _nonzero_sha(snapshot.get("base_sha"), "base_sha")
    expected_head = _nonzero_sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    current_head = _nonzero_sha(snapshot.get("current_head_sha"), "current_head_sha")

    if current_main != base:
        return _blocked(snapshot, "BASE_DRIFT", f"current main {current_main} != candidate base {base}")
    if current_head != expected_head:
        return _blocked(snapshot, "HEAD_DRIFT", f"current head {current_head} != expected head {expected_head}")
    if snapshot.get("mergeable") is not True:
        return _blocked(snapshot, "NOT_MERGEABLE", "candidate is not currently mergeable")
    if snapshot.get("external_effect") != "NONE":
        return _blocked(snapshot, "EXTERNAL_EFFECT_BOUNDARY", "candidate crosses an external-effect boundary")

    overlaps = snapshot.get("competing_writer_overlaps", [])
    if not isinstance(overlaps, list):
        raise PromotionBlock("competing_writer_overlaps must be a list")
    if overlaps:
        return _blocked(snapshot, "COMPETING_WRITER_OVERLAP", f"overlapping open writer(s): {overlaps}")

    governance = snapshot.get("governance_projection")
    if not isinstance(governance, Mapping):
        return _blocked(snapshot, "NATIVE_GOVERNANCE_EVIDENCE_MISSING", "execution checks cannot substitute for fresh native rules and reviews")
    native = governance.get("native_review_gate")
    if (
        governance.get("schema") != "qikvrt_governance_projection_v1"
        or governance.get("head_sha") != expected_head
        or governance.get("base_sha") != base
        or governance.get("pr_number") != snapshot.get("pr_number")
        or governance.get("status_context") != GOVERNANCE_STATUS_CONTEXT
        or not isinstance(native, Mapping)
        or native.get("schema") != REVIEW_GATE_SCHEMA
        or native.get("head_sha") != expected_head
        or native.get("pr_number") != snapshot.get("pr_number")
    ):
        return _blocked(snapshot, "NATIVE_GOVERNANCE_EVIDENCE_MISMATCH", "native governance evidence is not bound to this PR, head, base and status context")
    if governance.get("gate_state") != "success" or native.get("gate_state") != "success" or governance.get("acceptance") not in {"NATIVE_GOVERNANCE_SATISFIED", "OWNER_PRINCIPAL_REVIEW_SATISFIED"}:
        return _blocked(snapshot, governance.get("first_blocker") or "NATIVE_GOVERNANCE_NOT_SATISFIED", "a current-head Principal review or enforced independent native Code Owner approval is required")

    required = snapshot.get("required_gates")
    if not isinstance(required, list) or not required or not all(
        isinstance(name, str) and name for name in required
    ):
        raise PromotionBlock("required_gates must be a non-empty list of names")
    runs = snapshot.get("workflow_runs")
    if not isinstance(runs, list):
        raise PromotionBlock("workflow_runs must be a list")
    latest = collapse_latest_runs(runs)

    for gate in required:
        run = latest.get(gate)
        if run is None:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_MISSING", f"required workflow is absent: {gate}")
        if run.get("status") != "completed":
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_TERMINAL", f"required workflow is not terminal: {gate}")
        if run.get("conclusion") not in SUCCESS_CONCLUSIONS:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN", f"required workflow is not successful: {gate}={run.get('conclusion')}")

    for name, run in sorted(latest.items()):
        if name in required:
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_TERMINAL", f"workflow is not terminal: {name}")
        if conclusion not in NON_ADVERSE_CONCLUSIONS:
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_GREEN", f"workflow is adverse: {name}={conclusion}")

    if require_target_ref_cas:
        boundary = check_target_ref_cas(snapshot)
        if boundary is not None:
            return boundary
    expected_tree = _nonzero_sha(snapshot.get("expected_tree_sha"), "expected_tree_sha")

    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "PROMOTABLE",
        "first_blocker": None,
        "detail": "all exact-head promotion conditions are satisfied",
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": expected_head,
        "current_main_sha": current_main,
        "repository": snapshot["repository"],
        "expected_tree_sha": expected_tree,
        "target_ref_cas": dict(snapshot["target_ref_cas"]) if require_target_ref_cas else None,
        "merge_route": "QUALIFIED_TARGET_REF_CAS" if require_target_ref_cas else "OWNER_CONDITIONAL_REST_MERGE",
        "latest_workflows": {
            name: {
                "run_number": _run_number(run),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
            }
            for name, run in sorted(latest.items())
        },
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
        },
    }


def evaluate_promotion(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve the existing qualified target-ref CAS admission."""
    return _evaluate_promotion(snapshot, require_target_ref_cas=True)


def evaluate_conditional_rest_merge(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Use the later Owner REST grant, retaining current review and source gates.

    This pure evaluator grants no credentials and performs no mutation. The
    original closure engine reobserves the subject immediately before its one
    expected-HEAD-bound native merge and independently reads back its effect.
    """
    from tools.qikvrt_workflow_executor import load_repository_roles
    from tools.qikvrt_required_review_gate import project_governance
    decision = json.loads((ROOT / "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json").read_bytes())["conditional_merge_decision"]
    instruction = decision.get("source_instruction", {})
    if (decision.get("state") != "ACTIVE"
            or decision.get("repository") != snapshot.get("repository")
            or snapshot.get("repository") != load_repository_roles()["AUTHORITY"]
            or decision.get("authorizes", {}).get("conflict_free_green_test_pull_request_merge") is not True
            or hashlib.sha256(instruction.get("text", "").encode()).hexdigest()
               != "8dde795ae3a11aab14ad95d9b30b8884e2cf8cf57cee56b59514a1873778711a"
            or snapshot.get("draft") is not False):
        return _blocked(snapshot, "OWNER_REST_MERGE_NOT_ADMITTED", "current authority and active exact Owner decision required")
    raw = snapshot.get("review_observation")
    if not isinstance(raw, Mapping):
        return _blocked(snapshot, "NATIVE_GOVERNANCE_EVIDENCE_MISSING", "original review observation required")
    bound = dict(snapshot)
    bound["governance_projection"] = project_governance(raw["pr"], raw["rules"], raw["reviews"], raw["statuses"])
    for name, run in collapse_latest_runs(snapshot.get("workflow_runs", [])).items():
        blocker = _execution_blocker(run, snapshot["repository"], snapshot["expected_head_sha"],
                                     snapshot["pr_number"], required=name in snapshot.get("required_gates", []))
        if blocker:
            return _blocked(snapshot, blocker, "original workflow/job/step evidence is not bound to this subject")
    return _evaluate_promotion(bound, require_target_ref_cas=False)


def _gh_json(path: str) -> Mapping[str, Any]:
    value = json.loads(subprocess.check_output(["gh", "api", "--method", "GET", path], text=True, timeout=30))
    if not isinstance(value, Mapping):
        raise PromotionBlock("REST readback must be an object")
    return value


def verify_publication_readback(
    snapshot: Mapping[str, Any],
    read_json: Callable[[str], Mapping[str, Any]] = _gh_json,
) -> dict[str, Any]:
    """Read ref -> exact commit -> ref; no ref mutation or automatic retry.

    CONTINUE is limited to this publication's closure. The digest-bound CAS
    capability is a trusted-producer prerequisite, not proved by readback.
    A read failure after an effect preserves the merge SHA for reconciliation.
    """
    boundary = check_target_ref_cas(snapshot)
    if boundary is not None:
        return boundary
    base = _sha(snapshot.get("base_sha"), "base_sha")
    head = _sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    tree = _sha(snapshot.get("expected_tree_sha"), "expected_tree_sha")
    publication = snapshot.get("ref_publication")
    if publication is not None:
        expected = {"operation": "GITHUB_GRAPHQL_UPDATE_REFS", "repository": snapshot["repository"],
                    "ref": "refs/heads/main", "before_sha": base, "candidate_head_sha": head,
                    "tree_sha": tree, "after_sha": snapshot.get("merge_commit_sha")}
        if not isinstance(publication, Mapping) or any(publication.get(k) != v for k, v in expected.items()):
            return _hold(snapshot, "REF_PUBLICATION_SUBJECT_MISMATCH", "recorded updateRefs subject is not this promotion")
        published = _nonzero_sha(publication.get("after_sha"), "ref_publication.after_sha")
    else:
        response = snapshot.get("merge_response")
        if not isinstance(response, Mapping) or response.get("merged") is not True:
            return _hold(snapshot, "MERGE_EFFECT_NOT_ESTABLISHED", "transport response does not establish a merge")
        published = _sha(response.get("sha"), "merge_response.sha")
    repo = snapshot["repository"]
    ref_path = f"repos/{repo}/git/ref/heads/main"
    commit_path = f"repos/{repo}/git/commits/{published}"
    result = _hold(snapshot, "PUBLICATION_READBACK_UNAVAILABLE", "reconcile the recorded effect; do not redispatch")
    result.update({"schema": "qikvrt_ref_publication_readback_v1", "repository": repo,
                   "ref": "refs/heads/main", "published_head_sha": published,
                   "expected_tree_sha": tree, "automatic_retry": False})
    try:
        before = read_json(ref_path)
        commit = read_json(commit_path)
        after = read_json(ref_path)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result["detail"] = f"readback failed ({type(exc).__name__}); reconcile {published} before any new effect"
        return result
    if not all(isinstance(value, Mapping) for value in (before, commit, after)):
        result["detail"] = "REST readback returned an invalid observation; preserve the recorded effect for reconciliation"
        return result
    for observation in (before, after):
        obj = observation.get("object")
        if (observation.get("ref") != "refs/heads/main" or not isinstance(obj, Mapping)
                or obj.get("type") != "commit" or obj.get("sha") != published):
            result.update(first_blocker="PUBLISHED_REF_HEAD_DRIFT", detail="fresh ref reads do not both bind the returned merge commit")
            return result
    commit_tree = commit.get("tree")
    if (commit.get("sha") != published or not isinstance(commit_tree, Mapping)
            or commit_tree.get("sha") != tree):
        result.update(first_blocker="PUBLISHED_COMMIT_TREE_MISMATCH", detail="exact published commit does not bind the verified candidate tree")
        return result
    parents = commit.get("parents")
    if not isinstance(parents, list) or [p.get("sha") if isinstance(p, Mapping) else None for p in parents] != [base, head]:
        result.update(first_blocker="PUBLISHED_MERGE_PARENT_MISMATCH", detail="normal merge does not bind the expected old Main and reviewed head")
        return result
    result.update(state="CONTINUE", first_blocker=None, detail="this exact ref publication has fresh HEAD/TREE readback",
                  scope="EXACT_REF_PUBLICATION_ONLY", read_paths=[ref_path, commit_path, ref_path])
    return result


def _gh_observation(path: str) -> Any:
    """GET only; completely collect paginated reviews, statuses and checks."""
    command = ["gh", "api", "--hostname", "github.com", "--method", "GET", path]
    if "per_page=" not in path:
        return json.loads(subprocess.check_output(command, text=True, timeout=30))
    pages = json.loads(subprocess.check_output(command + ["--paginate", "--slurp"], text=True, timeout=30))
    if not isinstance(pages, list) or not pages:
        raise PromotionBlock("empty paginated REST observation")
    if all(isinstance(p, list) for p in pages):
        return [item for page in pages for item in page]
    if all(isinstance(p, Mapping) and isinstance(p.get("check_runs"), list) for p in pages):
        checks = [item for page in pages for item in page["check_runs"]]
        if any(p.get("total_count") != len(checks) for p in pages):
            raise PromotionBlock("incomplete or drifting check-run inventory")
        return {"total_count": len(checks), "check_runs": checks}
    raise PromotionBlock("unexpected paginated REST observation")


def _gh_graphql(request: Mapping[str, Any]) -> Mapping[str, Any]:
    """One authenticated request, no token arguments, retries or fallback writer."""
    raw = subprocess.check_output(
        ["gh", "api", "--hostname", "github.com", "--method", "POST", "graphql", "--input", "-"],
        input=json.dumps(request, allow_nan=False), text=True, timeout=30)
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PromotionBlock("duplicate GraphQL JSON key")
            result[key] = value
        return result
    def reject_constant(value):
        raise PromotionBlock("non-finite GraphQL JSON value")
    try:
        value = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
        if not isinstance(value, Mapping):
            raise PromotionBlock("GraphQL response must be an object")
        return value
    except ValueError as exc:
        return {"raw_response": raw, "parse_error": type(exc).__name__}


def _required_checks_green(sha: str, rules: Sequence[Mapping[str, Any]],
                           read_json: Callable[[str], Any], repo: str) -> bool:
    check_rules = [r for r in rules if r.get("type") == "required_status_checks"]
    specs = [s for r in check_rules for s in r.get("parameters", {}).get("required_status_checks", [])]
    if not {"test", "QIKVRT required code-owner review"}.issubset({s.get("context") for s in specs}):
        return False
    statuses = read_json(f"repos/{repo}/commits/{sha}/statuses?per_page=100")
    checks = read_json(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")
    if not isinstance(statuses, list) or not isinstance(checks, Mapping):
        return False
    runs = checks.get("check_runs")
    if (not isinstance(runs, list) or checks.get("total_count") != len(runs)
            or not all(isinstance(x, Mapping) for x in statuses + runs)):
        return False
    for spec in specs:
        context = spec.get("context")
        source = spec.get("integration_id")
        matching_statuses = [s for s in statuses if s.get("context") == context]
        matching_checks = [c for c in runs if c.get("name") == context]
        observed = []
        if matching_statuses:
            s = max(matching_statuses, key=lambda x: (x.get("created_at", ""), x.get("id", 0)))
            # Commit-status REST records do not attest an App integration id.
            observed.append(source in (None, 0) and s.get("sha") == sha and s.get("state") == "success")
        if matching_checks:
            c = max(matching_checks, key=lambda x: (x.get("started_at", ""), x.get("id", 0)))
            observed.append(c.get("head_sha") == sha and c.get("status") == "completed"
                            and c.get("conclusion") == "success"
                            and (source in (None, 0) or c.get("app", {}).get("id") == source))
        if not observed or not all(observed):
            return False
    return True


def _live_graphql_admission(snapshot: Mapping[str, Any], qualification: Mapping[str, Any],
                            read_json: Callable[[str], Any]) -> dict[str, Any]:
    """Re-use the native review gate, and independently read its policy source."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.qikvrt_required_review_gate import evaluate_required_review, resolve_required_code_owner

    repo = snapshot["repository"]
    number = snapshot.get("pr_number")
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise PromotionBlock("pr_number must be a positive integer")
    base = _nonzero_sha(snapshot.get("base_sha"), "base_sha")
    head = _nonzero_sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    tree = _nonzero_sha(snapshot.get("expected_tree_sha"), "expected_tree_sha")
    repository = read_json(f"repos/{repo}")
    if (repository.get("full_name") != repo or not qualification.get("repository_node_id")
            or repository.get("node_id") != qualification["repository_node_id"]):
        raise PromotionBlock("REPOSITORY_NODE_ID_MISMATCH")
    pr_path = f"repos/{repo}/pulls/{number}"
    pr = read_json(pr_path)
    if (pr.get("number") != number or pr.get("state") != "open" or pr.get("merged") is not False
            or pr.get("draft") is not False or pr.get("mergeable") is not True
            or pr.get("base", {}).get("ref") != "main"
            or pr.get("base", {}).get("repo", {}).get("full_name") != repo
            or pr.get("head", {}).get("repo", {}).get("full_name") != repo
            or pr.get("base", {}).get("sha") != base or pr.get("head", {}).get("sha") != head):
        raise PromotionBlock("LIVE_PR_BINDING_OR_REVIEW_STATE_CHANGED")
    rules = read_json(f"repos/{repo}/rules/branches/main")
    if not isinstance(rules, list) or not rules or not all(isinstance(r, Mapping) for r in rules):
        raise PromotionBlock("NATIVE_GOVERNANCE_NOT_ENFORCED")
    ids = {r.get("ruleset_id") for r in rules}
    if any(isinstance(i, bool) or not isinstance(i, int) or i <= 0 for i in ids):
        raise PromotionBlock("APPLIED_RULESET_ORIGIN_MISSING")
    rulesets = [read_json(f"repos/{repo}/rulesets/{i}") for i in sorted(ids)]
    if (any(not isinstance(r, Mapping) or r.get("enforcement") != "active"
            or r.get("bypass_actors") != [] for r in rulesets)
            or {r.get("id") for r in rulesets} != ids
            or _digest(rules) != qualification.get("effective_rules_sha256")
            or _digest(rulesets) != qualification.get("rulesets_sha256")
            or not any(r.get("type") == "non_fast_forward" for r in rules)):
        raise PromotionBlock("NATIVE_POLICY_DRIFT_OR_BYPASS")
    reviews = read_json(f"repos/{repo}/pulls/{number}/reviews?per_page=100")
    review = evaluate_required_review(pr, rules, reviews,
                                      required_code_owner=resolve_required_code_owner(repo, pr_author=pr["user"]["login"]))
    if review["gate_state"] != "success":
        raise PromotionBlock(review["first_blocker"])
    if (review.get("review_basis") != "OWNER_PRINCIPAL_REVIEW"
            and review["required_code_owner"].casefold() == qualification["executor_login"].casefold()):
        raise PromotionBlock("EXECUTOR_REVIEW_NOT_INDEPENDENT")
    if not _required_checks_green(head, rules, read_json, repo):
        raise PromotionBlock("NATIVE_REQUIRED_CHECKS_NOT_GREEN")
    merge = _nonzero_sha(pr.get("merge_commit_sha"), "merge_commit_sha")
    if merge in {base, head}:
        raise PromotionBlock("INVALID_TWO_PARENT_MERGE")
    merge_ref = read_json(f"repos/{repo}/git/ref/pull/{number}/merge")
    if (merge_ref.get("ref") != f"refs/pull/{number}/merge"
            or merge_ref.get("object", {}).get("type") != "commit"
            or merge_ref.get("object", {}).get("sha") != merge):
        raise PromotionBlock("GITHUB_TEST_MERGE_REF_MISMATCH")
    commit = read_json(f"repos/{repo}/git/commits/{merge}")
    if (commit.get("sha") != merge or commit.get("tree", {}).get("sha") != tree
            or [p.get("sha") for p in commit.get("parents", [])] != [base, head]):
        raise PromotionBlock("CANDIDATE_MERGE_TREE_OR_PARENT_MISMATCH")
    # M is a fast-forward descendant of B by its independently read first parent.
    # Required checks on H alone do not establish protection admission for M.
    if not _required_checks_green(merge, rules, read_json, repo):
        raise PromotionBlock("MERGE_RESULT_REQUIRED_CHECKS_NOT_GREEN")
    ref = read_json(f"repos/{repo}/git/ref/heads/main")
    again = read_json(pr_path)
    if (ref.get("ref") != "refs/heads/main" or ref.get("object", {}).get("type") != "commit"
            or ref.get("object", {}).get("sha") != base or again != pr):
        raise PromotionBlock("PRE_EFFECT_SUBJECT_DRIFT")
    return {"repository_node_id": repository["node_id"], "merge_commit_sha": merge,
            "review": review, "effective_rules_sha256": _digest(rules), "rulesets_sha256": _digest(rulesets)}


def prepare_graphql_promotion(snapshot: Mapping[str, Any], qualification: Mapping[str, Any],
                               read_json: Callable[[str], Any] = _gh_observation) -> dict[str, Any]:
    """Prepare one exact updateRefs request after all existing and native gates."""
    value = dict(snapshot)
    value["target_ref_cas"] = qualify_target_ref_cas(value, qualification)
    decision = evaluate_promotion(value)
    if decision["state"] != "PROMOTABLE":
        return decision
    try:
        live = _live_graphql_admission(value, qualification, read_json)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, subprocess.SubprocessError) as exc:
        return _hold(value, "GRAPHQL_CAS_LIVE_ADMISSION_FAILED", f"{type(exc).__name__}: {exc}")
    value["merge_commit_sha"] = live["merge_commit_sha"]
    identifier = _digest({"repository": value["repository"], "base": value["base_sha"],
                          "head": value["expected_head_sha"], "tree": value["expected_tree_sha"],
                          "merge": live["merge_commit_sha"], "qualification": _digest(qualification)})
    request = {"query": GRAPHQL_UPDATE_REFS, "variables": {"input": {
        "repositoryId": live["repository_node_id"], "clientMutationId": identifier,
        "refUpdates": [{"name": "refs/heads/main", "beforeOid": value["base_sha"],
                        "afterOid": live["merge_commit_sha"], "force": False}],
    }}}
    value["ref_publication"] = {
        "operation": "GITHUB_GRAPHQL_UPDATE_REFS", "repository": value["repository"],
        "ref": "refs/heads/main", "before_sha": value["base_sha"],
        "after_sha": live["merge_commit_sha"], "candidate_head_sha": value["expected_head_sha"],
        "tree_sha": value["expected_tree_sha"], "client_mutation_id": identifier,
    }
    return {"schema": "qikvrt_graphql_ref_cas_attempt_v1", "state": "PREPARED",
            "request": request, "request_sha256": _digest(request), "snapshot": value,
            "qualification_sha256": _digest(qualification), "live_admission": live,
            "automatic_retry": False, "completion_claims": decision["completion_claims"]}


def execute_graphql_promotion(snapshot: Mapping[str, Any], qualification: Mapping[str, Any],
                               attempt_file: pathlib.Path,
                               read_json: Callable[[str], Any] = _gh_observation,
                               graphql: Callable[[Mapping[str, Any]], Any] = _gh_graphql) -> dict[str, Any]:
    """Create and fsync the intent BEFORE a single write; always reconcile after it.

    clientMutationId is correlation only. It does not make updateRefs idempotent.
    The caller must retain this create-only journal across restarts/invocations.
    """
    if attempt_file.exists():
        return _hold(snapshot, "CAS_ATTEMPT_ALREADY_RECORDED", "reconcile the durable attempt; no repeat mutation")
    attempt = prepare_graphql_promotion(snapshot, qualification, read_json)
    if attempt["state"] != "PREPARED":
        return attempt
    try:
        viewer = graphql({"query": "query QikvrtExecutor { viewer { login } }"})
        if (not isinstance(viewer, Mapping) or viewer.get("errors")
                or viewer.get("data", {}).get("viewer", {}).get("login") != qualification["executor_login"]):
            return _hold(snapshot, "GRAPHQL_EXECUTOR_IDENTITY_UNVERIFIED", "authenticated viewer does not match the qualified executor")
        # Identity lookup is read-only; re-admit after it, immediately before CAS.
        refreshed = prepare_graphql_promotion(snapshot, qualification, read_json)
        if refreshed != attempt:
            return _hold(snapshot, "PRE_EFFECT_SUBJECT_DRIFT", "subject or native gates changed during executor identification")
        with attempt_file.open("x", encoding="utf-8") as stream:
            json.dump(attempt, stream, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(attempt_file.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, subprocess.SubprocessError) as exc:
        return _hold(snapshot, "CAS_INTENT_OR_IDENTITY_UNAVAILABLE", f"no mutation; {type(exc).__name__}")
    response: Any = None
    transport_error = None
    try:
        response = graphql(attempt["request"])
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        transport_error = type(exc).__name__
        if isinstance(exc, json.JSONDecodeError):
            response = exc.doc
        elif isinstance(exc, subprocess.CalledProcessError) and exc.output:
            response = exc.output.decode() if isinstance(exc.output, bytes) else exc.output
    readback = verify_publication_readback(attempt["snapshot"], read_json)
    expected_id = attempt["request"]["variables"]["input"]["clientMutationId"]
    clean = (isinstance(response, Mapping) and "errors" not in response
             and isinstance(response.get("data"), Mapping)
             and set(response["data"]) == {"updateRefs"}
             and isinstance(response["data"].get("updateRefs"), Mapping)
             and set(response["data"]["updateRefs"]) == {"clientMutationId"}
             and response["data"]["updateRefs"].get("clientMutationId") == expected_id
             and transport_error is None)
    result = dict(readback)
    result.update(request_sha256=attempt["request_sha256"], graphql_response=response,
                  transport_error=transport_error, readback=readback, automatic_retry=False,
                  attempt_file=str(attempt_file), pr_merge_state="NOT_INFERRED")
    if not clean:
        result.update(state="HOLD", first_blocker="GRAPHQL_CAS_RESPONSE_AMBIGUOUS_OR_REJECTED",
                      detail="response/errors retained; independent readback only, never replay updateRefs")
    return result


def _load_snapshot(path: str) -> Mapping[str, Any]:
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise PromotionBlock("duplicate snapshot member: " + key)
            value[key] = item
        return value

    def reject_constant(value):
        raise PromotionBlock("non-finite snapshot number: " + value)

    if path == "-":
        value = json.load(sys.stdin, object_pairs_hook=unique_object, parse_constant=reject_constant)
    else:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"),
                           object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(value, Mapping):
        raise PromotionBlock("snapshot JSON must be an object")
    return value


def reconcile_graphql_attempt(attempt: Mapping[str, Any], qualification: Mapping[str, Any],
                                read_json: Callable[[str], Any] = _gh_observation) -> dict[str, Any]:
    """Validate the original intent, then GET-only reconcile; never resend it."""
    snapshot = attempt.get("snapshot")
    if not isinstance(snapshot, Mapping):
        raise PromotionBlock("attempt snapshot is missing")
    cas = qualify_target_ref_cas(snapshot, qualification)
    if (attempt.get("schema") != "qikvrt_graphql_ref_cas_attempt_v1"
            or cas.get("state") != "VERIFIED" or snapshot.get("target_ref_cas") != cas
            or attempt.get("qualification_sha256") != _digest(qualification)):
        return _hold(snapshot, "CAS_ATTEMPT_QUALIFICATION_MISMATCH", "reconciliation intent is not bound to the trusted qualification")
    identifier = _digest({"repository": snapshot["repository"], "base": snapshot["base_sha"],
                          "head": snapshot["expected_head_sha"], "tree": snapshot["expected_tree_sha"],
                          "merge": snapshot.get("merge_commit_sha"), "qualification": _digest(qualification)})
    expected_request = {"query": GRAPHQL_UPDATE_REFS, "variables": {"input": {
        "repositoryId": qualification.get("repository_node_id"), "clientMutationId": identifier,
        "refUpdates": [{"name": "refs/heads/main", "beforeOid": snapshot["base_sha"],
                        "afterOid": snapshot.get("merge_commit_sha"), "force": False}],
    }}}
    if (attempt.get("request") != expected_request or attempt.get("request_sha256") != _digest(expected_request)
            or attempt.get("automatic_retry") is not False):
        return _hold(snapshot, "CAS_ATTEMPT_REQUEST_MISMATCH", "request digest or exact single-ref intent differs")
    result = verify_publication_readback(snapshot, read_json)
    result.update(request_sha256=attempt["request_sha256"], automatic_retry=False,
                  pr_merge_state="NOT_INFERRED", scope="EXACT_REF_PUBLICATION_ONLY")
    return result


def evaluate_closure(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Check externally verified closure observations; no effect permission.

    The caller must authenticate and verify every supplied fact at its source.
    This pure core validates bindings and acceptance completeness, not the
    truth of an arbitrary JSON document. A positive result is review readiness.
    """
    result = {
        "schema": "qikvrt_reciprocal_devops_closure_decision_v1",
        "state": "BLOCK", "first_blocker": None, "external_effect": "NONE",
        "ordinary_release": False,
        "completion_claims": {"EFFECT_ACK_DONE": False, "TARGET_REACHED": False},
    }

    def require(condition: bool, failure: str) -> None:
        if not condition:
            raise PromotionBlock(failure)

    def timestamp(raw: Any) -> datetime.datetime:
        require(isinstance(raw, str) and raw.endswith("Z"), "INVALID_UTC_TIME")
        try:
            return datetime.datetime.fromisoformat(raw[:-1] + "+00:00")
        except ValueError as exc:
            raise PromotionBlock("INVALID_UTC_TIME") from exc

    def records(raw: Any, key: str) -> dict[Any, Mapping[str, Any]]:
        require(isinstance(raw, list), "INVENTORY_NOT_A_LIST")
        indexed = {}
        for item in raw:
            require(isinstance(item, Mapping), "INVALID_INVENTORY_RECORD")
            identity = item.get(key)
            require(isinstance(identity, (int, str)) and not isinstance(identity, bool)
                    and bool(identity), "INVALID_INVENTORY_ID")
            require(identity not in indexed, "DUPLICATE_INVENTORY_ID")
            indexed[identity] = item
        return indexed

    try:
        require(isinstance(snapshot, Mapping), "INVALID_CLOSURE_SNAPSHOT")
        require(snapshot.get("schema") == "qikvrt_reciprocal_devops_closure_snapshot_v1",
                "UNSUPPORTED_CLOSURE_VERSION")
        now = timestamp(snapshot.get("evaluated_utc"))
        age = snapshot.get("max_observation_age_seconds")
        require(type(age) is int and 0 < age <= 300, "INVALID_FRESHNESS_BUDGET")
        nodes = records(snapshot.get("nodes"), "repository")
        from tools.qikvrt_workflow_executor import load_repository_roles
        expected = {repository: role for role, repository in load_repository_roles().items()}
        require(set(nodes) == set(expected), "BOTH_NODES_REQUIRED")
        for repository, role in expected.items():
            node = nodes[repository]
            require(node.get("role") == role, "REPOSITORY_ROLE_MISMATCH")
            require(node.get("accessible") is True, "NODE_ACCESS_NOT_ESTABLISHED")
            head = _sha(node.get("main_sha"), "main_sha")
            tree = _sha(node.get("main_tree"), "main_tree")
            require(0 <= (now - timestamp(node.get("observed_utc"))).total_seconds() <= age,
                    "STALE_OR_FUTURE_OBSERVATION")
            require(node.get("inventory_complete") is True, "INVENTORY_INCOMPLETE")
            require(node.get("inventory_stable") is True, "INVENTORY_DRIFT")
            require(node.get("origin_verified") is True, "ORIGIN_NOT_VERIFIED")
            initial = records(node.get("initial_branches"), "name")
            final = records(node.get("final_branches"), "name")
            require("main" in initial, "INITIAL_MAIN_BINDING_MISSING")
            require("main" in final and final["main"].get("sha") == head,
                    "MAIN_REF_BINDING_MISMATCH")
            for branch in list(initial.values()) + list(final.values()):
                _sha(branch.get("sha"), "branch tip")
                require(branch.get("reachable_from_main") is True and
                        branch.get("verified_against_main") == head and
                        branch.get("object_closure_verified") is True,
                        "BRANCH_HISTORY_NOT_RETAINED")
            for pr in records(node.get("initial_pull_requests"), "number").values():
                _sha(pr.get("head_sha"), "original PR head")
                _sha(pr.get("merge_commit_sha"), "PR merge commit")
                require(pr.get("merged") is True and pr.get("head_reachable_from_main") is True
                        and pr.get("merge_reachable_from_main") is True
                        and pr.get("verified_against_main") == head,
                        "PR_NOT_LOSSLESSLY_MERGED")
            require(node.get("final_open_pull_requests") == [], "OPEN_PULL_REQUESTS_REMAIN")
            quality = node.get("quality")
            require(isinstance(quality, Mapping), "QUALITY_PROFILE_MISSING")
            require(quality.get("head_sha") == head and quality.get("tree_sha") == tree,
                    "QUALITY_SUBJECT_DRIFT")
            require(isinstance(quality.get("profile_id"), str) and bool(quality["profile_id"])
                    and type(quality.get("profile_version")) is int and quality["profile_version"] > 0,
                    "QUALITY_PROFILE_UNVERSIONED")
            for check in ("all_applicable_gates_green", "native_code_owner_rule_enforced",
                          "independent_exact_head_approval", "provenance_rights_security_verified",
                          "no_unaccepted_known_defects", "fresh_main_readback"):
                require(quality.get(check) is True, "QUALITY_NOT_ESTABLISHED:" + check)
        witnesses = snapshot.get("reciprocal_witnesses")
        require(isinstance(witnesses, list) and len(witnesses) == 2, "BOTH_DIRECTIONS_REQUIRED")
        seen = set()
        for witness in witnesses:
            require(isinstance(witness, Mapping), "INVALID_DIRECTION_WITNESS")
            source, target = witness.get("source"), witness.get("target")
            require(source in nodes and target in nodes and source != target,
                    "INVALID_DIRECTION")
            require((source, target) not in seen, "DUPLICATE_DIRECTION")
            seen.add((source, target))
            require(witness.get("source_head") == nodes[source]["main_sha"] and
                    witness.get("target_after") == nodes[target]["main_sha"],
                    "DIRECTION_SUBJECT_DRIFT")
            _sha(witness.get("target_before"), "target_before")
            for check in ("authenticated_executor", "accepted_scoped_effect_ack_chain",
                          "post_effect_readback", "lossless_history_verified"):
                require(witness.get(check) is True, "DIRECTION_UNVERIFIED:" + check)
        public = records(snapshot.get("public_evidence"), "kind")
        require(set(public) == {"REPOSITORY", "IETF", "ZENODO"}, "PUBLIC_EVIDENCE_INCOMPLETE")
        for item in public.values():
            require(isinstance(item.get("url"), str) and item["url"].startswith("https://"),
                    "PUBLIC_URL_MISSING")
            digest = item.get("sha256")
            require(isinstance(digest, str) and len(digest) == 64 and
                    all(c in "0123456789abcdef" for c in digest), "PUBLIC_DIGEST_INVALID")
            require(item.get("public_byte_readback_verified") is True,
                    "PUBLIC_BYTE_READBACK_UNVERIFIED")
            if item["kind"] != "IETF":
                require(item.get("subject_heads") == {k: n["main_sha"] for k, n in nodes.items()},
                        "PUBLIC_EVIDENCE_SUBJECT_DRIFT")
            else:
                require(item.get("document") == "draft-lohmann-qikvrt-effect-ack-03",
                        "PROTOCOL_VERSION_MISMATCH")
        result.update(state="CLOSURE_READY_FOR_ACCEPTANCE", first_blocker=None)
    except (PromotionBlock, TypeError, KeyError) as exc:
        result["first_blocker"] = str(exc)
    result["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return result


def verify_promotion_readback(value: Mapping[str, Any]) -> dict[str, Any]:
    """Bind the observed merge effect; merged-tree validation remains separate."""
    head = _sha(value.get("expected_head_sha"), "expected_head_sha")
    base = _sha(value.get("expected_base_sha"), "expected_base_sha")
    tree = _sha(value.get("expected_tree_sha"), "expected_tree_sha")
    response, pr, commit = (value.get(key) for key in ("merge_response", "pull_request", "main_commit"))
    if not all(isinstance(item, Mapping) for item in (response, pr, commit)):
        raise PromotionBlock("merge response, pull request and main commit observations are required")
    merged = response.get("sha")
    _sha(merged, "merge_response.sha")
    parents = commit.get("parents")
    commit_tree = commit.get("tree")
    repository, pr_number = value.get("repository"), value.get("pr_number")
    if not isinstance(repository, str) or isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
        raise PromotionBlock("readback repository and pull-request number are required")
    pr_head = pr.get("head")
    bound = (response.get("merged") is True and pr.get("merged") is True
             and pr.get("number") == pr_number
             and isinstance(merged, str) and commit.get("sha") == merged
             and pr.get("merge_commit_sha") == merged
             and isinstance(pr_head, Mapping) and pr_head.get("sha") == head
             and isinstance(pr_head.get("repo"), Mapping) and pr_head["repo"].get("full_name") == repository
             and isinstance(parents, list)
             and [item.get("sha") if isinstance(item, Mapping) else None for item in parents] == [base, head]
             and isinstance(commit_tree, Mapping) and isinstance(commit_tree.get("sha"), str))
    return {
        "schema": "qikvrt_expected_head_promotion_readback_v1",
        "state": "PROMOTION_EFFECT_BOUND_REVALIDATION_PENDING" if bound else "HOLD",
        "first_blocker": None if bound else "PROMOTION_EFFECT_READBACK_MISMATCH",
        "expected_head_sha": head, "expected_base_sha": base,
        "repository": repository, "pr_number": pr_number,
        "promoted_main_sha": commit.get("sha"),
        "promoted_tree_sha": commit_tree.get("sha") if isinstance(commit_tree, Mapping) else None,
        "candidate_tree_matches": bound and commit_tree["sha"] == tree,
        "fresh_main_validation": "REQUIRED_NOT_ESTABLISHED_BY_MERGE",
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate", "evaluate-closure", "verify-readback", "verify-publication", "qualify-cas",
                                           "prepare-graphql", "publish-graphql", "reconcile-graphql"))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    parser.add_argument("--qualification", default=str(QUALIFICATION_PATH),
                        help="independently reviewed trusted executor qualification, never a candidate file")
    parser.add_argument("--attempt-file", help="create-only durable intent journal; retain across invocations/restarts")
    args = parser.parse_args(argv)
    try:
        snapshot = _load_snapshot(args.input)
        if args.command == "evaluate":
            result = evaluate_promotion(snapshot)
        elif args.command == "evaluate-closure":
            result = evaluate_closure(snapshot)
        elif args.command == "verify-readback":
            result = verify_promotion_readback(snapshot)
        elif args.command == "verify-publication":
            result = verify_publication_readback(snapshot)
        else:
            qualification = _load_snapshot(args.qualification)
            if args.command == "qualify-cas":
                result = qualify_target_ref_cas(snapshot, qualification)
            elif args.command == "prepare-graphql":
                result = prepare_graphql_promotion(snapshot, qualification)
            elif args.command == "reconcile-graphql":
                result = reconcile_graphql_attempt(snapshot, qualification)
            else:
                if not args.attempt_file:
                    raise PromotionBlock("publish-graphql requires a durable --attempt-file")
                result = execute_graphql_promotion(snapshot, qualification, pathlib.Path(args.attempt_file))
    except (OSError, ValueError, json.JSONDecodeError, PromotionBlock) as exc:
        result = {
            "schema": ("qikvrt_reciprocal_devops_closure_decision_v1" if args.command == "evaluate-closure"
                       else "qikvrt_expected_head_promotion_readback_v1" if args.command == "verify-readback"
                       else "qikvrt_expected_head_promotion_decision_v1"),
            "state": "BLOCK",
            "first_blocker": "INVALID_PROMOTION_SNAPSHOT",
            "detail": str(exc),
            "external_effect": "NONE",
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"PROMOTABLE", "CONTINUE", "PREPARED", "VERIFIED", "CLOSURE_READY_FOR_ACCEPTANCE", "PROMOTION_EFFECT_BOUND_REVALIDATION_PENDING"} else (20 if result.get("state") in {"HOLD", "UNAVAILABLE"} else 2)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
