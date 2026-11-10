#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Read-only TEMDD observation of a failed CI/CD workflow, never effect admission."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

SHA1 = re.compile(r"^[0-9a-f]{40}$")
FAILED = frozenset({"failure", "timed_out", "cancelled", "action_required"})
SCHEMA = "qikvrt_temdd_failed_ci_observation_v1"


def _integer(value):
    return value if type(value) is int and value > 0 else None


def build_receipt(event, jobs, *, actual_head="", test_exit="", test_log=b""):
    """Model OBSERVE -> CLASSIFY -> TEST -> READBACK -> HOLD without inventing DONE."""
    run = event.get("workflow_run", {}) if isinstance(event, dict) else {}
    run = run if isinstance(run, dict) else {}
    repository = (event.get("repository") or {}).get("full_name") if isinstance(event, dict) and isinstance(event.get("repository"), dict) else None
    head_repo_obj = run.get("head_repository")
    head_repository = head_repo_obj.get("full_name") if isinstance(head_repo_obj, dict) else None
    source_head = run.get("head_sha")
    exact_head = isinstance(source_head, str) and bool(SHA1.fullmatch(source_head))
    identity_valid = (
        event.get("action") == "completed"
        and run.get("status") == "completed"
        and run.get("conclusion") in FAILED
        and repository == "ingolf-lohmann/qik-vrt"
        and _integer(run.get("id")) is not None
        and _integer(run.get("run_attempt")) is not None
        and exact_head
    ) if isinstance(event, dict) else False

    listed = jobs.get("jobs") if isinstance(jobs, dict) else None
    failed_jobs = []
    if isinstance(listed, list):
        for job in listed:
            if isinstance(job, dict) and job.get("conclusion") in FAILED:
                failed_jobs.append({
                    "job_id": _integer(job.get("id")),
                    "name": str(job.get("name", ""))[:200],
                    "conclusion": job.get("conclusion"),
                    "html_url": str(job.get("html_url", ""))[:500],
                })
    failed_jobs.sort(key=lambda job: (str(job["job_id"]), job["name"]))
    try:
        exit_code = int(test_exit)
    except (ValueError, TypeError, OverflowError):
        exit_code = None
    # A green TEMDD regression never proves that the failed CI/CD step was fixed.
    same_source = bool(identity_valid and actual_head == source_head
                       and head_repository == repository)
    tested = same_source and exit_code is not None and bool(test_log)
    regression = "PASS" if tested and exit_code == 0 else ("FAIL" if tested else "NOT_VERIFIED")
    reasons = []
    if not identity_valid:
        reasons.append("UNVERIFIED_FAILURE_EVENT_OR_AUTHORITY")
    if not same_source:
        reasons.append("EXACT_FAILED_SOURCE_NOT_TESTED")
    if not isinstance(listed, list) or not failed_jobs:
        reasons.append("FAILED_JOB_EVIDENCE_INCOMPLETE")
    if not tested:
        reasons.append("TEMDD_REGRESSION_NOT_EXECUTED")
    elif exit_code != 0:
        reasons.append("TEMDD_REGRESSION_FAILED")
    reasons.append("ORIGINAL_FAILURE_NOT_REPRODUCED_AND_INDEPENDENTLY_RESOLVED")
    record = {
        "schema": SCHEMA,
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": repository,
        "source_head": source_head if exact_head else None,
        "source_repository": head_repository,
        "workflow": str(run.get("name", ""))[:200],
        "run_id": _integer(run.get("id")),
        "run_attempt": _integer(run.get("run_attempt")),
        "run_conclusion": run.get("conclusion"),
        "run_url": str(run.get("html_url", ""))[:500],
        "failed_jobs": failed_jobs,
        "events": [
            {"kind": "OBSERVE", "evidence": "workflow_run completed event"},
            {"kind": "CLASSIFY", "result": "UNRESOLVED_CI_CD_FAILURE"},
            {"kind": "ACTION", "method": "EXACT_HEAD_TEMDD_REGRESSIONS", "verified": tested},
            {"kind": "READBACK", "test_exit_code": exit_code if tested else None,
             "log_sha256": hashlib.sha256(test_log).hexdigest() if tested else None,
             "scope": "TEMDD_REGRESSION_ONLY"},
            {"kind": "HOLD", "reasons": reasons},
        ],
        "temdd_regression": regression,
        "specific_failed_step_reproduced": False,
        "independent_effect_verification": False,
        "original_host_readback": False,
        "effect_ack_done": False,
        "release_admission": "BLOCKED",
        "state": "HOLD",
        "next_action": "REPRODUCE_FAILED_STEP_AT_EXACT_HEAD_THEN_TEST_SMALLEST_REVERSIBLE_FIX",
    }
    record["observation_sha256"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True, type=Path)
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--actual-head", default="")
    parser.add_argument("--test-exit", default="")
    parser.add_argument("--test-log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        event = json.loads(args.event.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        event = {}
    try:
        jobs = json.loads(args.jobs.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        jobs = {}
    try:
        log = args.test_log.read_bytes()
    except OSError:
        log = b""
    receipt = build_receipt(event, jobs, actual_head=args.actual_head,
                            test_exit=args.test_exit, test_log=log)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"state": receipt["state"], "run_id": receipt["run_id"],
                      "temdd_regression": receipt["temdd_regression"],
                      "receipt_sha256": receipt["observation_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
