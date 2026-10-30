#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed decision core for requested-review execution.

The module is deliberately GitHub-write-free. A workflow supplies one live,
exact-head-bound snapshot; this core returns WAIT, APPROVE, REQUEST_CHANGES,
or COMMENT_WITH_BLOCKER. The workflow persists the disposition and an
exact-head commit status without impersonating a requested GitHub identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

SUCCESS = {"success"}
NON_ADVERSE = {"success", "skipped"}
SELF_WORKFLOW = "QIKVRT requested review executor"
TECHNICAL_STATUS_CONTEXT = "QIKVRT requested review disposition"


class ReviewSnapshotError(ValueError):
    pass


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ReviewSnapshotError(f"{label} is not a Git SHA-1")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ReviewSnapshotError(f"{label} is not lowercase hexadecimal")
    return value


def _run_number(run: Mapping[str, Any]) -> int:
    value = run.get("run_number", -1)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReviewSnapshotError("workflow run_number must be an integer")
    return value


def collapse_latest(runs: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        name = run.get("name")
        if not isinstance(name, str) or not name:
            raise ReviewSnapshotError("workflow run name is missing")
        if name == SELF_WORKFLOW:
            continue
        current = latest.get(name)
        if current is None or _run_number(run) > _run_number(current):
            latest[name] = run
    return latest


def _result(snapshot: Mapping[str, Any], state: str, blocker: str | None, detail: str) -> dict[str, Any]:
    return {
        "schema": "qikvrt_requested_review_decision_v1",
        "state": state,
        "first_blocker": blocker,
        "detail": detail,
        "repository": snapshot.get("repository"),
        "pr_number": snapshot.get("pr_number"),
        "base_sha": snapshot.get("base_sha"),
        "head_sha": snapshot.get("head_sha"),
        "tree_sha": snapshot.get("tree_sha"),
        "reviewed_scope": snapshot.get("changed_paths", []),
        "status_scope": "TECHNICAL_DISPOSITION_ONLY",
        "review_route": snapshot.get("review_route", "REQUESTED_REVIEW"),
        "semantic_ai_review_performed": False,
        "native_approval_mutation": "FORBIDDEN_FOR_AUTOMATED_EXECUTOR",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "INDEPENDENT_CODE_OWNER_APPROVAL": False,
            "NATIVE_RULE_ENFORCEMENT": False,
        },
    }


def native_review_enabled(policy: Mapping[str, Any], repository: str) -> bool:
    """Resolve routing from trusted Main policy; this is not an authority grant."""
    route = policy.get("review_executor", {}).get("provider_routing", {})
    return (repository in policy.get("repositories", [])
            and route.get("enabled") is True
            and route.get("default") == "QIKVRT_NATIVE"
            and route.get("scope") == "OPEN_NON_DRAFT_MAIN_PULL_REQUESTS"
            and route.get("copilot_required") is False)


def native_review_candidate(pr: Mapping[str, Any], policy: Mapping[str, Any], repository: str) -> bool:
    return (native_review_enabled(policy, repository)
            and pr.get("state") == "open" and pr.get("draft") is False
            and pr.get("base", {}).get("ref") == "main")


def snapshot_from_reads(repository, number, policy, required, one, pages):
    """Reuse the original bounded REST reads for selection and final recheck."""
    pr = one(f"repos/{repository}/pulls/{number}")
    main = one(f"repos/{repository}/commits/main")["sha"]
    head = pr["head"]["sha"]
    observed = one(f"repos/{repository}/pulls/{number}")["head"]["sha"]
    tree = one(f"repos/{repository}/git/commits/{head}")["tree"]["sha"]
    files = pages(f"repos/{repository}/pulls/{number}/files?per_page=100")
    runs = pages(f"repos/{repository}/actions/runs?head_sha={head}&event=pull_request&per_page=100")
    comments = pages(f"repos/{repository}/pulls/{number}/comments?per_page=100")
    return {"repository": repository, "pr_number": number, "current_main_sha": main,
            "base_sha": pr["base"]["sha"], "head_sha": head, "observed_head_sha": observed,
            "tree_sha": tree, "draft": bool(pr.get("draft")),
            "requested_reviewers": [x["login"] for x in pr.get("requested_reviewers", []) if x.get("login")],
            "requested_team_reviewers": [x["slug"] for x in pr.get("requested_teams", []) if x.get("slug")],
            "changed_paths": sorted(x["filename"] for x in files),
            "review_route": "QIKVRT_NATIVE" if native_review_candidate(pr, policy, repository) else "REQUESTED_REVIEW",
            "review_threads_complete": not bool(comments), "unresolved_review_threads": 0,
            "required_gates": required, "workflow_runs": [
                {key: run.get(key) for key in ("name", "status", "conclusion", "run_number")} for run in runs]}


def technical_update_plan(snapshot, reviews, statuses, marker):
    """Refresh changed technical evidence without another semantic review.

    The original review remains untouched. Clocks and unrelated run counters
    do not create another update. This plan neither writes nor proves a gate.
    """
    if (not isinstance(reviews, list) or not isinstance(statuses, list)
            or any(not isinstance(x, Mapping) for x in [*reviews, *statuses])):
        raise ReviewSnapshotError("technical history is unavailable or malformed")
    for records, actor_key in ((reviews, "user"), (statuses, "creator")):
        if any(not isinstance(x.get(actor_key), Mapping)
               or not isinstance(x[actor_key].get("login"), str) for x in records):
            raise ReviewSnapshotError("technical history actor identity is unavailable")
    decision = evaluate(snapshot)
    key = hashlib.sha256(json.dumps(
        {"schema": "qikvrt_technical_review_input/v1", "decision": decision},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    state = "success" if decision["state"] == "APPROVE" else "pending" if decision["state"] == "WAIT" else "failure"
    description = f"technical={decision['state']}; evidence={key}; approval NOT_IMPLIED"
    prefix = f"<!-- {marker} head={snapshot['head_sha']} "
    prior = any(x.get("commit_id") == snapshot["head_sha"]
                and (x.get("user") or {}).get("login") == "github-actions[bot]"
                and isinstance(x.get("body"), str) and x["body"].startswith(prefix) for x in reviews)
    review_required = not prior and decision["state"] != "WAIT"
    trusted = [x for x in statuses if x.get("context") == TECHNICAL_STATUS_CONTEXT
               and (x.get("creator") or {}).get("login") == "github-actions[bot]"]
    latest = max(trusted, key=lambda x: (str(x.get("created_at", "")), int(x.get("id", 0))), default={})
    same = latest.get("state") == state and latest.get("description") == description
    action = "NOOP" if same and not review_required else "REVIEW_AND_STATUS" if review_required else "STATUS_ONLY"
    return {"schema": "qikvrt_technical_review_update/v1", "action": action,
            "review_required": review_required, "evidence_sha256": key,
            "status_state": state, "status_description": description, "decision": decision}


def evaluate(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise ReviewSnapshotError("snapshot must be an object")

    current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    head = _sha(snapshot.get("head_sha"), "head_sha")
    observed_head = _sha(snapshot.get("observed_head_sha"), "observed_head_sha")
    _sha(snapshot.get("tree_sha"), "tree_sha")

    if base != current_main:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "BASE_DRIFT", f"base {base} != current main {current_main}")
    if observed_head != head:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "HEAD_DRIFT", f"observed head {observed_head} != bound head {head}")
    if snapshot.get("draft") is True:
        return _result(snapshot, "WAIT", "DRAFT", "requested candidate is still draft")

    requested = snapshot.get("requested_reviewers", [])
    requested_teams = snapshot.get("requested_team_reviewers", [])
    if not isinstance(requested, list) or not isinstance(requested_teams, list):
        raise ReviewSnapshotError("requested reviewer collections must be lists")
    if not requested and not requested_teams and snapshot.get("review_route") != "QIKVRT_NATIVE":
        return _result(snapshot, "WAIT", "NO_ACTIVE_REVIEW_REQUEST", "no requested reviewer remains")

    changed_paths = snapshot.get("changed_paths")
    if not isinstance(changed_paths, list) or not all(isinstance(path, str) and path for path in changed_paths):
        raise ReviewSnapshotError("changed_paths must be a list of non-empty strings")
    if not changed_paths:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "EMPTY_SCOPE", "requested review has no changed paths")

    if snapshot.get("review_threads_complete") is False:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "REVIEW_THREAD_STATE_UNAVAILABLE",
                       "REST inline comments exist; thread resolution is not established")

    unresolved = snapshot.get("unresolved_review_threads", 0)
    if isinstance(unresolved, bool) or not isinstance(unresolved, int) or unresolved < 0:
        raise ReviewSnapshotError("unresolved_review_threads must be a non-negative integer")
    if unresolved:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "UNRESOLVED_REVIEW_THREADS", f"{unresolved} unresolved review thread(s)")

    required = snapshot.get("required_gates")
    runs = snapshot.get("workflow_runs")
    if not isinstance(required, list) or not required or not all(isinstance(name, str) and name for name in required):
        raise ReviewSnapshotError("required_gates must be a non-empty list")
    if not isinstance(runs, list):
        raise ReviewSnapshotError("workflow_runs must be a list")
    latest = collapse_latest(runs)

    for gate in required:
        run = latest.get(gate)
        if run is None:
            return _result(snapshot, "WAIT", "REQUIRED_GATE_MISSING", f"required exact-head gate is absent: {gate}")
        if run.get("status") != "completed":
            return _result(snapshot, "WAIT", "REQUIRED_GATE_NOT_TERMINAL", f"required exact-head gate is not terminal: {gate}")
        if run.get("conclusion") not in SUCCESS:
            return _result(snapshot, "REQUEST_CHANGES", "REQUIRED_GATE_FAILED", f"required exact-head gate failed: {gate}={run.get('conclusion')}")

    for name, run in sorted(latest.items()):
        if name in required:
            continue
        if run.get("status") != "completed":
            return _result(snapshot, "WAIT", "APPLICABLE_GATE_NOT_TERMINAL", f"applicable exact-head gate is not terminal: {name}")
        if run.get("conclusion") not in NON_ADVERSE:
            return _result(snapshot, "REQUEST_CHANGES", "APPLICABLE_GATE_FAILED", f"applicable exact-head gate is adverse: {name}={run.get('conclusion')}")

    return _result(snapshot, "APPROVE", None, "all observed applicable gates are terminal non-adverse and no unresolved review thread is reported; semantic inspection is separate")


def _load(path: str) -> Mapping[str, Any]:
    value = json.load(sys.stdin) if path == "-" else json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ReviewSnapshotError("snapshot JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate",))
    parser.add_argument("--input", default="-")
    args = parser.parse_args(argv)
    try:
        result = evaluate(_load(args.input))
    except (OSError, ValueError, json.JSONDecodeError, ReviewSnapshotError) as exc:
        result = {
            "schema": "qikvrt_requested_review_decision_v1",
            "state": "COMMENT_WITH_BLOCKER",
            "first_blocker": "INVALID_REVIEW_SNAPSHOT",
            "detail": str(exc),
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"WAIT", "APPROVE"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
