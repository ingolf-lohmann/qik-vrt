#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed decision core for expected-head-bound QIK-VRT promotion.

This module intentionally does not mutate GitHub. It evaluates an exact live
snapshot and returns either PROMOTABLE or the first deterministic blocker.
The GitHub workflow is responsible for reobserving the same head/base again
immediately before changing draft state or merging.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence

PROMOTION_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
SUCCESS_CONCLUSIONS = {"success"}
NON_ADVERSE_CONCLUSIONS = {"success", "skipped"}


class PromotionBlock(ValueError):
    """Raised when a snapshot is structurally invalid rather than merely blocked."""


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise PromotionBlock(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise PromotionBlock(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


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
    }
    if any(cas.get(key) != value for key, value in expected.items()):
        return _hold(snapshot, "TARGET_REF_CAS_SUBJECT_MISMATCH", "CAS does not bind this repository, ref, base and candidate")
    if cas.get("server_atomic_compare_and_update") is not True or cas.get("force_update") is not False:
        return _hold(snapshot, "ATOMIC_TARGET_REF_CAS_UNVERIFIED", "atomic comparison and non-force update must be verified together")
    evidence = cas.get("evidence_sha256")
    if not isinstance(evidence, str) or not re.fullmatch(r"[0-9a-f]{64}", evidence):
        return _hold(snapshot, "TARGET_REF_CAS_EVIDENCE_MISSING", "the verified executor evidence must be digest-bound")
    return None


def evaluate_promotion(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one promotion candidate against the live fail-closed contract."""
    if not isinstance(snapshot, Mapping):
        raise PromotionBlock("snapshot must be an object")

    current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    expected_head = _sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    current_head = _sha(snapshot.get("current_head_sha"), "current_head_sha")

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

    boundary = check_target_ref_cas(snapshot)
    if boundary is not None:
        return boundary
    expected_tree = _sha(snapshot.get("expected_tree_sha"), "expected_tree_sha")

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
        "target_ref_cas": dict(snapshot["target_ref_cas"]),
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


def _load_snapshot(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise PromotionBlock("snapshot JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate", "verify-publication"))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        snapshot = _load_snapshot(args.input)
        result = (evaluate_promotion(snapshot) if args.command == "evaluate"
                  else verify_publication_readback(snapshot))
    except (OSError, ValueError, json.JSONDecodeError, PromotionBlock) as exc:
        result = {
            "schema": "qikvrt_expected_head_promotion_decision_v1",
            "state": "BLOCK",
            "first_blocker": "INVALID_PROMOTION_SNAPSHOT",
            "detail": str(exc),
            "external_effect": "NONE",
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"PROMOTABLE", "CONTINUE"} else (20 if result.get("state") == "HOLD" else 2)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
