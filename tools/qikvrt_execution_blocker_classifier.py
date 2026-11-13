# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed classification of GitHub execution blockers (read-only).

Input is an exact-head JSON observation, never an instruction to bypass GitHub
approval, repository policy, or effect-acknowledgement requirements.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ACTIVE = frozenset({"queued", "pending", "waiting", "requested", "in_progress"})
TERMINAL = frozenset({"success", "failure", "cancelled", "timed_out", "action_required", "startup_failure", "skipped"})


def classify(observation: dict) -> dict:
    if not isinstance(observation, dict):
        raise ValueError("observation must be an object")
    head = observation.get("expected_head_sha")
    if not isinstance(head, str) or len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise ValueError("expected_head_sha must be an exact lowercase SHA")
    runs = observation.get("runs")
    if not isinstance(runs, list):
        raise ValueError("runs must be an array")
    findings = []
    seen = set()
    for item in runs:
        if not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] <= 0 or item["id"] in seen:
            raise ValueError("invalid or duplicate run")
        seen.add(item["id"])
        if item.get("head_sha") != head:
            raise ValueError("run HEAD drift")
        status, conclusion, jobs = item.get("status"), item.get("conclusion"), item.get("jobs")
        if status not in ACTIVE | {"completed"} or not isinstance(jobs, list):
            raise ValueError("invalid run status or missing jobs observation")
        if status == "completed" and conclusion not in TERMINAL:
            raise ValueError("invalid terminal conclusion")
        if status != "completed" and conclusion is not None:
            raise ValueError("nonterminal run has conclusion")
        if any(not isinstance(job, dict) or job.get("status") not in ACTIVE | {"completed"} for job in jobs):
            raise ValueError("invalid job observation")
        if conclusion in {"action_required", "startup_failure"} and not jobs:
            category = "EXECUTION_ADMISSION_BLOCKED"
            action = "CHECK_GITHUB_NATIVE_EXECUTION_ADMISSION"
        elif conclusion in {"failure", "timed_out"}:
            category = "EXECUTED_JOB_FAILURE" if jobs else "FAILED_RUN_WITHOUT_JOB_EVIDENCE"
            action = "TEMDD_EXACT_HEAD_FAILURE_ANALYSIS" if jobs else "CHECK_GITHUB_NATIVE_JOB_READBACK"
        elif status in ACTIVE:
            category = "ACTIVE_UNPROVEN_PROGRESS"
            action = "OBSERVE_NEXT_NATIVE_TRANSITION"
        elif conclusion in {"action_required", "startup_failure"}:
            category = "EXECUTION_UNTRUSTED"
            action = "CHECK_GITHUB_NATIVE_EXECUTION_ADMISSION"
        elif conclusion in {"cancelled", "skipped"}:
            category = "NON_SUCCESS_TERMINAL_RUN"
            action = "CHECK_EXACT_HEAD_RUN_DISPOSITION"
        else:
            continue
        findings.append({"run_id": item["id"], "category": category, "next_action": action})
    return {"schema": "qikvrt_execution_blocker_classification_v1",
            "expected_head_sha": head, "state": "HOLD" if findings else "NO_BLOCKER_OBSERVED",
            "findings": findings, "effect_ack_done": False,
            "native_execution_admitted": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("observation", type=Path)
    args = parser.parse_args()
    try:
        result = classify(json.loads(args.observation.read_text(encoding="utf-8")))
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "HOLD", "first_blocker": "OBSERVATION_INVALID", "detail": str(exc),
                          "effect_ack_done": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
