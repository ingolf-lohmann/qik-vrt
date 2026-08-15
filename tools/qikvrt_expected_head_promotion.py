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

PROMOTION_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
SUCCESS_CONCLUSIONS = {"success"}
NON_ADVERSE_CONCLUSIONS = {"success", "skipped"}
INTEGRITY_TRIO = {
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
}
SELF_HEAL_BRANCH_PREFIX = "automation/self-heal-"
EXACT_HEAD_VERIFIER = "QIK-VRT autonomous exact-head verification"
EXACT_HEAD_VERIFIER_WORKFLOW_PATH = ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"
EXACT_HEAD_VERIFIER_SUCCESS_DESCRIPTION = "Exact-head verified: pr={pr}; base={base}"


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


def _exact_head_verifier_block(
    snapshot: Mapping[str, Any], expected_head: str, base: str
) -> tuple[str, str] | None:
    """Validate the candidate status and its linked dispatch-run receipt.

    A repository_dispatch workflow executes from main rather than the pull
    request head. It is consequently not present in the ordinary
    head_sha-filtered workflow-run list. The verifier publishes a canonical
    commit status on the candidate head after validating the dispatch
    envelope; the status must in turn resolve to the successful, canonical
    repository_dispatch run that produced it.
    """
    statuses = snapshot.get("exact_head_verifier_statuses")
    if statuses is None or statuses == []:
        return (
            "EXACT_HEAD_VERIFIER_MISSING",
            "the trusted repository-dispatch verifier status is absent",
        )
    if not isinstance(statuses, list):
        return (
            "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
            "exact-head verifier statuses must be a list",
        )

    canonical_statuses: list[Mapping[str, Any]] = []
    for status in statuses:
        if not isinstance(status, Mapping):
            return (
                "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
                "exact-head verifier status must be an object",
            )
        if status.get("context") != EXACT_HEAD_VERIFIER:
            continue
        identifier = status.get("id")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
            return (
                "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
                "exact-head verifier status id must be a positive integer",
            )
        canonical_statuses.append(status)

    if not canonical_statuses:
        return (
            "EXACT_HEAD_VERIFIER_MISSING",
            "the canonical exact-head verifier status is absent",
        )

    status = max(canonical_statuses, key=lambda entry: int(entry["id"]))
    pr_number = snapshot.get("pr_number")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number <= 0:
        return (
            "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
            "pull-request number is not a positive integer",
        )
    if (
        snapshot.get("commit_status_sha") != expected_head
        or status.get("sha") != expected_head
    ):
        return (
            "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
            "the verifier status is not bound to the expected candidate head",
        )
    if status.get("state") != "success":
        return (
            "EXACT_HEAD_VERIFIER_NOT_GREEN",
            "the newest exact-head verifier status is not successful",
        )
    expected_description = EXACT_HEAD_VERIFIER_SUCCESS_DESCRIPTION.format(
        pr=pr_number, base=base
    )
    if status.get("description") != expected_description:
        return (
            "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
            "the verifier status does not bind the current pull request and base",
        )

    run = status.get("workflow_run")
    if not isinstance(run, Mapping):
        return (
            "EXACT_HEAD_VERIFIER_UNTRUSTED_WORKFLOW",
            "the verifier status does not resolve to an Actions workflow run",
        )
    run_id = run.get("id")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
        return (
            "EXACT_HEAD_VERIFIER_UNTRUSTED_WORKFLOW",
            "the linked verifier workflow run id is invalid",
        )
    repository = snapshot.get("repository")
    github_server_url = snapshot.get("github_server_url")
    if (
        not isinstance(repository, str)
        or not repository
        or not isinstance(github_server_url, str)
        or not github_server_url
    ):
        return (
            "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
            "repository or GitHub server identity is absent",
        )
    expected_run_url = (
        f"{github_server_url.rstrip('/')}/{repository}/actions/runs/{run_id}"
    )
    if (
        status.get("target_url") != expected_run_url
        or run.get("html_url") != expected_run_url
    ):
        return (
            "EXACT_HEAD_VERIFIER_STATUS_BINDING_MISMATCH",
            "the verifier status does not link exactly to its workflow run",
        )
    if (
        run.get("name") != EXACT_HEAD_VERIFIER
        or run.get("path") != EXACT_HEAD_VERIFIER_WORKFLOW_PATH
        or run.get("repository") != repository
        or run.get("head_repository") != repository
        or run.get("head_branch") != "main"
        or run.get("head_sha") != base
    ):
        return (
            "EXACT_HEAD_VERIFIER_UNTRUSTED_WORKFLOW",
            "the linked workflow is not the canonical main-bound verifier",
        )
    if run.get("event") != "repository_dispatch":
        return (
            "EXACT_HEAD_VERIFIER_UNTRUSTED_EVENT",
            "the exact-head verifier was not invoked by repository dispatch",
        )
    if (
        run.get("status") != "completed"
        or run.get("conclusion") not in SUCCESS_CONCLUSIONS
    ):
        return (
            "EXACT_HEAD_VERIFIER_NOT_GREEN",
            "the linked exact-head verifier workflow is not terminal success",
        )
    return None


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

    if current_main != base:
        return _blocked(snapshot, "BASE_DRIFT", f"current main {current_main} != candidate base {base}")
    if current_head != expected_head:
        return _blocked(snapshot, "HEAD_DRIFT", f"current head {current_head} != expected head {expected_head}")
    if snapshot.get("mergeable") is not True:
        return _blocked(snapshot, "NOT_MERGEABLE", "candidate is not currently mergeable")
    if snapshot.get("external_effect") != "NONE":
        return _blocked(snapshot, "EXTERNAL_EFFECT_BOUNDARY", "candidate crosses an external-effect boundary")
    if snapshot.get("same_repository") is not True:
        return _blocked(
            snapshot,
            "CANDIDATE_NOT_SAME_REPOSITORY",
            "candidate head must be owned by this repository",
        )
    if snapshot.get("marker_in_pr_body") is not True:
        return _blocked(
            snapshot,
            "CANDIDATE_NOT_EXPLICITLY_OPTED_IN",
            "expected-head marker must occur in the pull-request body",
        )
    head_ref = snapshot.get("head_ref")
    if not isinstance(head_ref, str) or not head_ref.startswith(
        SELF_HEAL_BRANCH_PREFIX
    ):
        return _blocked(
            snapshot,
            "CANDIDATE_BRANCH_NOT_AUTONOMOUS_SELF_HEAL",
            "candidate head is not a bounded self-heal branch",
        )
    candidate_files = snapshot.get("candidate_files")
    allowed_paths = snapshot.get("allowed_paths")
    if not isinstance(candidate_files, list) or not candidate_files or not all(
        isinstance(path, str) and path for path in candidate_files
    ):
        raise PromotionBlock("candidate_files must be a non-empty list of paths")
    if not isinstance(allowed_paths, list) or not allowed_paths or not all(
        isinstance(path, str) and path for path in allowed_paths
    ):
        raise PromotionBlock("allowed_paths must be a non-empty list of paths")
    candidate_path_set = set(candidate_files)
    non_allowlisted = sorted(candidate_path_set - set(allowed_paths))
    if non_allowlisted:
        return _blocked(
            snapshot,
            "CANDIDATE_DIFF_NOT_ALLOWLISTED",
            f"candidate changes non-allowlisted path(s): {non_allowlisted}",
        )
    missing_integrity = sorted(INTEGRITY_TRIO - candidate_path_set)
    if missing_integrity:
        return _blocked(
            snapshot,
            "CANDIDATE_INTEGRITY_TRIO_MISSING",
            f"candidate lacks repository-native integrity path(s): {missing_integrity}",
        )

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

    verifier_block = _exact_head_verifier_block(snapshot, expected_head, base)
    if verifier_block is not None:
        return _blocked(snapshot, *verifier_block)

    for name, run in sorted(latest.items()):
        if name in required or name == EXACT_HEAD_VERIFIER:
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_TERMINAL", f"workflow is not terminal: {name}")
        if conclusion not in NON_ADVERSE_CONCLUSIONS:
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_GREEN", f"workflow is adverse: {name}={conclusion}")

    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "PROMOTABLE",
        "first_blocker": None,
        "detail": "all exact-head promotion conditions are satisfied",
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": expected_head,
        "current_main_sha": current_main,
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
    parser.add_argument("command", choices=("evaluate",))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        result = evaluate_promotion(_load_snapshot(args.input))
    except (OSError, ValueError, json.JSONDecodeError, PromotionBlock) as exc:
        result = {
            "schema": "qikvrt_expected_head_promotion_decision_v1",
            "state": "BLOCK",
            "first_blocker": "INVALID_PROMOTION_SNAPSHOT",
            "detail": str(exc),
            "external_effect": "NONE",
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") == "PROMOTABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
