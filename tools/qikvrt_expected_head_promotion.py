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
import sys
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.qikvrt_required_review_gate import evaluate_required_review

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
        if current is None or _run_key(run) > _run_key(current):
            latest[name] = run
    return latest


def _run_key(run: Mapping[str, Any]) -> tuple[int, int, int]:
    values = [run.get("run_attempt", 0), run.get("id", 0)]
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise PromotionBlock("run attempt and id must be non-negative integers")
    return _run_number(run), values[0], values[1]


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


def evaluate_promotion(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one promotion candidate against the live fail-closed contract."""
    if not isinstance(snapshot, Mapping):
        raise PromotionBlock("snapshot must be an object")

    current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    expected_head = _sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    current_head = _sha(snapshot.get("current_head_sha"), "current_head_sha")
    expected_tree = _sha(snapshot.get("expected_tree_sha"), "expected_tree_sha")
    current_tree = _sha(snapshot.get("current_tree_sha"), "current_tree_sha")
    repository = snapshot.get("repository")
    pr_number = snapshot.get("pr_number")
    if (not isinstance(repository, str) or repository.count("/") != 1 or
            not all(repository.split("/")) or isinstance(pr_number, bool) or
            not isinstance(pr_number, int) or pr_number < 1):
        raise PromotionBlock("repository and positive pull-request number are required")

    if current_main != base:
        return _blocked(snapshot, "BASE_DRIFT", f"current main {current_main} != candidate base {base}")
    if current_head != expected_head:
        return _blocked(snapshot, "HEAD_DRIFT", f"current head {current_head} != expected head {expected_head}")
    if current_tree != expected_tree:
        return _blocked(snapshot, "TREE_DRIFT", "current tree differs from the bound candidate tree")
    if snapshot.get("mergeable") is not True:
        return _blocked(snapshot, "NOT_MERGEABLE", "candidate is not currently mergeable")
    if snapshot.get("external_effect") != "NONE":
        return _blocked(snapshot, "EXTERNAL_EFFECT_BOUNDARY", "candidate crosses an external-effect boundary")

    overlaps = snapshot.get("competing_writer_overlaps", [])
    if not isinstance(overlaps, list):
        raise PromotionBlock("competing_writer_overlaps must be a list")
    if overlaps:
        return _blocked(snapshot, "COMPETING_WRITER_OVERLAP", f"overlapping open writer(s): {overlaps}")

    observation = snapshot.get("review_observation")
    if not isinstance(observation, Mapping) or not isinstance(observation.get("pr"), Mapping):
        return _blocked(snapshot, "INDEPENDENT_REVIEW_OBSERVATION_MISSING", "raw native review observation is required")
    review_pr = observation["pr"]
    review_head, review_base = review_pr.get("head"), review_pr.get("base")
    if not isinstance(review_head, Mapping) or not isinstance(review_base, Mapping):
        return _blocked(snapshot, "REVIEW_SUBJECT_BINDING_MISMATCH", "review subject is malformed")
    review_repository = review_head.get("repo")
    if (review_pr.get("number") != pr_number or
            review_head.get("sha") != expected_head or not isinstance(review_repository, Mapping) or
            review_repository.get("full_name") != repository or review_base.get("sha") != base):
        return _blocked(snapshot, "REVIEW_SUBJECT_BINDING_MISMATCH", "review belongs to a different subject")
    try:
        review = evaluate_required_review(review_pr, observation.get("rules"), observation.get("reviews"))
    except ValueError as exc:
        raise PromotionBlock(f"invalid native review observation: {exc}") from exc
    if review["gate_state"] != "success":
        return _blocked(snapshot, review["first_blocker"], review["detail"])

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
        blocker = _execution_blocker(run, repository, expected_head, pr_number, required=True)
        if blocker:
            return _blocked(snapshot, blocker, f"required workflow lacks bound execution evidence: {gate}")

    for name, run in sorted(latest.items()):
        if name in required:
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_TERMINAL", f"workflow is not terminal: {name}")
        if conclusion not in NON_ADVERSE_CONCLUSIONS:
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_GREEN", f"workflow is adverse: {name}={conclusion}")
        blocker = _execution_blocker(run, repository, expected_head, pr_number, required=False)
        if blocker:
            return _blocked(snapshot, blocker, f"applicable workflow lacks bound execution evidence: {name}")

    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "PROMOTABLE",
        "first_blocker": None,
        "detail": "all exact-head promotion conditions are satisfied",
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": expected_head,
        "current_main_sha": current_main,
        "expected_tree_sha": expected_tree,
        "repository": repository,
        "independent_review": review,
        "latest_workflows": {
            name: {
                "run_number": _run_number(run),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "id": run.get("id"),
                "run_attempt": run.get("run_attempt"),
                "head_sha": run.get("head_sha"),
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


def _load_snapshot(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise PromotionBlock("snapshot JSON must be an object")
    return value


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
    parser.add_argument("command", choices=("evaluate", "verify-readback"))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        snapshot = _load_snapshot(args.input)
        result = evaluate_promotion(snapshot) if args.command == "evaluate" else verify_promotion_readback(snapshot)
    except (OSError, ValueError, json.JSONDecodeError, PromotionBlock) as exc:
        result = {
            "schema": "qikvrt_expected_head_promotion_decision_v1",
            "state": "BLOCK",
            "first_blocker": "INVALID_PROMOTION_SNAPSHOT",
            "detail": str(exc),
            "external_effect": "NONE",
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"PROMOTABLE", "PROMOTION_EFFECT_BOUND_REVALIDATION_PENDING"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
