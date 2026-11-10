#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only, exact-head pre-deadlock analysis for every QIK-VRT repository instance.

The controller models repository writers and runner pressure as a bounded
resource-allocation graph.  It emits an evidence receipt before a circular wait
or stale writer lease is allowed to become the next repository action.  It does
not cancel jobs, dispatch workflows, mutate refs, merge pull requests, or treat
watchdog terminality as gate success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
ACTIVE_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
WAITING_STATUSES = frozenset({"queued", "waiting", "requested", "pending"})
UNTRUSTED_CONCLUSIONS = frozenset({"action_required", "startup_failure"})
EXECUTED_FAILURE_CONCLUSIONS = frozenset({"failure", "timed_out"})
GATEWATCH_SCOPES = frozenset({"MAIN", "PULL_REQUEST_MAIN", "PULL_REQUEST_STACKED"})
MAX_JOB_READBACK_REQUESTS = 20
MAX_RUN_READBACK_PAGES = 10
MAX_WORK_READBACK_PAGES = 10
READBACK_PAGE_SIZE = 100
GATEWATCH_STATES = frozenset(
    {
        "SUCCESS",
        "FAILED",
        "MISSING",
        "ACTIVE",
        "UNTRUSTED",
        "NOT_OBSERVED",
        "NOT_APPLICABLE",
    }
)


class ReflexiveWatchdogBlock(RuntimeError):
    """A malformed or drifted observation that must fail closed."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReflexiveWatchdogBlock(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReflexiveWatchdogBlock(f"{label} must be a non-empty string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ReflexiveWatchdogBlock(f"{label} must be a positive integer")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ReflexiveWatchdogBlock(f"{label} must be a {'possibly empty ' if allow_empty else 'non-empty '}list")
    if any(not isinstance(item, str) or not item for item in value):
        raise ReflexiveWatchdogBlock(f"{label} must contain non-empty strings")
    if len(set(value)) != len(value):
        raise ReflexiveWatchdogBlock(f"{label} must not contain duplicates")
    return list(value)


def _relative_path(value: Any, label: str) -> Path:
    path = Path(_string(value, label))
    if path.is_absolute() or ".." in path.parts:
        raise ReflexiveWatchdogBlock(f"{label} must be a repository-relative path")
    return path


def _head_sha(value: Any, label: str) -> str:
    text = _string(value, label)
    if len(text) != 40 or any(character not in "0123456789abcdef" for character in text):
        raise ReflexiveWatchdogBlock(f"{label} must be a lowercase forty-character Git SHA")
    return text


def _timestamp(value: Any, label: str) -> datetime:
    text = _string(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReflexiveWatchdogBlock(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReflexiveWatchdogBlock(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def merge_run_pages(value: Any) -> dict[str, Any]:
    """Merge gh api --paginate --slurp output; never conceal inconsistent pages."""
    if not isinstance(value, list) or not value:
        raise ReflexiveWatchdogBlock("RUN_INVENTORY_INVALID: expected a non-empty page list")
    runs: list[Any] = []
    total = None
    for page in value:
        page = _mapping(page, "workflow run page")
        count = page.get("total_count")
        if type(count) is not int or count < 0 or not isinstance(page.get("workflow_runs"), list):
            raise ReflexiveWatchdogBlock("RUN_INVENTORY_INVALID: malformed page")
        if total is not None and count != total:
            raise ReflexiveWatchdogBlock("RUN_INVENTORY_INCOMPLETE: page totals changed during readback")
        if page.get("truncated", False) is not False:
            raise ReflexiveWatchdogBlock("RUN_INVENTORY_INCOMPLETE: truncated page")
        total = count
        runs.extend(page["workflow_runs"])
    return {"total_count": total, "workflow_runs": runs, "page_count": len(value)}


def job_readback_budget(
    value: Any, *, expected_head: str, required_jobs_only: bool = False
) -> dict[str, Any]:
    """Admit a complete, exact-head run page before any per-run job request."""
    expected_head = _head_sha(expected_head, "expected head")
    value = _mapping(value, "workflow run page")
    runs = value.get("workflow_runs")
    total = value.get("total_count")
    blocker = None
    run_ids = []
    if (not isinstance(runs, list) or not isinstance(total, int)
            or isinstance(total, bool) or total < 0):
        blocker = "RUN_INVENTORY_INVALID"
    elif value.get("truncated", False) is not False or len(runs) != total:
        blocker = "RUN_INVENTORY_INCOMPLETE"
    elif not required_jobs_only and total > MAX_JOB_READBACK_REQUESTS:
        blocker = "JOB_READBACK_REQUEST_BUDGET_EXCEEDED"
    else:
        for run in runs:
            if (not isinstance(run, Mapping) or type(run.get("id")) is not int
                    or run["id"] <= 0 or run["id"] in run_ids
                    or run.get("head_sha") != expected_head):
                blocker = "RUN_INVENTORY_INVALID"
                break
            run_ids.append(run["id"])
    metadata_only_ids: list[int] = []
    if required_jobs_only and blocker is None:
        try:
            for run in runs:
                _string(run.get("name"), "workflow name")
                _positive_int(run.get("run_attempt"), "run attempt")
                if run.get("status") not in ACTIVE_STATUSES | {"completed"}:
                    raise ReflexiveWatchdogBlock("invalid run status")
                _run_created_time(run)
                _run_transition_time(run)
            required = {run["id"] for run in _latest_by_name(runs)}
            required.update(run["id"] for run in runs if run["status"] in ACTIVE_STATUSES)
            metadata_only_ids = sorted(set(run_ids) - required)
            run_ids = sorted(required)
            if len(run_ids) > MAX_JOB_READBACK_REQUESTS:
                blocker = "JOB_READBACK_REQUEST_BUDGET_EXCEEDED"
        except ReflexiveWatchdogBlock:
            blocker = "RUN_INVENTORY_INVALID"
    result = {
        "schema": "qikvrt_job_readback_budget_v1",
        "state": "HOLD" if blocker else "READY",
        "first_blocker": blocker,
        "expected_head_sha": expected_head,
        "reported_run_count": total if type(total) is int else None,
        "returned_run_count": len(runs) if isinstance(runs, list) else None,
        "max_job_requests": MAX_JOB_READBACK_REQUESTS,
        "run_ids": [] if blocker else run_ids,
        "effect_ack_done": False,
    }
    if required_jobs_only:
        result.update(
            selection="LATEST_PER_WORKFLOW_AND_ALL_ACTIVE_V1",
            inventory_sha256=sha256_bytes(canonical_json_bytes(value)),
            required_job_request_count=(len(run_ids) if blocker in
                {None, "JOB_READBACK_REQUEST_BUDGET_EXCEEDED"} else None),
            metadata_only_run_ids=metadata_only_ids if blocker is None else [],
        )
    return result


def _readback_page(endpoint: str, destination: Path, *, allow_list: bool = False) -> Any:
    """One original gh REST call, no automatic retry; retain the response bytes."""
    try:
        result = subprocess.run(["gh", "api", endpoint], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReflexiveWatchdogBlock(f"REST readback unavailable: {exc}") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result.stdout)
    destination.with_suffix(".stderr").write_bytes(result.stderr)
    if result.returncode:
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        raise ReflexiveWatchdogBlock(f"REST readback failed (exit {result.returncode})")
    try:
        value = json.loads(result.stdout)
        return value if allow_list and isinstance(value, list) else _mapping(value, "REST readback page")
    except (ValueError, UnicodeError) as exc:
        raise ReflexiveWatchdogBlock("REST readback is not JSON") from exc


def _collect_pages(endpoint: str, key: str, directory: Path, *, max_requests: int,
                   expected_head: str | None = None,
                   expected_run_id: int | None = None,
                   expected_run_attempt: int | None = None) -> tuple[dict[str, Any], int]:
    items: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    total = None
    blocker = None
    requests = 0
    for page in range(1, max_requests + 1):
        value = _readback_page(
            f"{endpoint}&per_page={READBACK_PAGE_SIZE}&page={page}",
            directory / f"{page}.json",
        )
        requests += 1
        count, entries = value.get("total_count"), value.get(key)
        if type(count) is not int or count < 0 or not isinstance(entries, list):
            blocker = "READBACK_PAGE_INVALID"
            break
        if total is None:
            total = count
        if count != total or value.get("truncated", False) is not False:
            blocker = "READBACK_INVENTORY_CHANGED_OR_TRUNCATED"
            break
        if len(entries) != min(READBACK_PAGE_SIZE, total - len(items)):
            blocker = "READBACK_INVENTORY_INCOMPLETE"
            break
        for entry in entries:
            if (not isinstance(entry, Mapping) or type(entry.get("id")) is not int
                    or entry["id"] <= 0 or entry["id"] in seen
                    or (expected_head is not None and entry.get("head_sha") != expected_head)
                    or (expected_run_id is not None and entry.get("run_id") != expected_run_id)
                    or (expected_run_attempt is not None
                        and entry.get("run_attempt") != expected_run_attempt)
                    or (key == "jobs" and entry.get("status") not in ACTIVE_STATUSES | {"completed"})):
                blocker = "READBACK_ENTRY_INVALID_OR_DUPLICATED"
                break
            seen.add(entry["id"])
            items.append(entry)
        if blocker or len(items) == total:
            break
    if blocker is None and (total is None or len(items) != total):
        blocker = "READBACK_REQUEST_BUDGET_EXCEEDED"
    return {"total_count": total, key: items, "truncated": blocker is not None,
            "first_blocker": blocker, "page_requests": requests}, requests


def _repository(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ReflexiveWatchdogBlock("invalid readback repository")
    return value


def collect_runs(*, repository: str, expected_head: str, directory: Path) -> dict[str, Any]:
    endpoint = (f"repos/{_repository(repository)}/actions/runs?head_sha="
                + _head_sha(expected_head, "expected head"))
    value, _ = _collect_pages(endpoint, "workflow_runs", directory,
                              max_requests=MAX_RUN_READBACK_PAGES, expected_head=expected_head)
    return value


def collect_work(*, repository: str, expected_head: str, directory: Path,
                 now: datetime) -> dict[str, Any]:
    """Bounded GET-only inventory; issue text is data, never execution authority.

    The issues endpoint includes pull requests. A short terminal page and a
    stable first page are required. An access error stops immediately, without
    retrying or treating an unreadable queue as empty.
    """
    repository = _repository(repository)
    expected_head = _head_sha(expected_head, "expected head")
    prefix = f"repos/{repository}/issues?state=open&sort=created&direction=asc"
    items: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    seen_numbers: set[int] = set()
    first_page: list[Any] | None = None
    complete = False
    blocker = "WORK_READBACK_REQUEST_BUDGET_EXCEEDED"
    requests = 0
    for page in range(1, MAX_WORK_READBACK_PAGES + 1):
        entries = _readback_page(f"{prefix}&per_page={READBACK_PAGE_SIZE}&page={page}",
                                 directory / f"{page}.json", allow_list=True)
        requests += 1
        if not isinstance(entries, list) or len(entries) > READBACK_PAGE_SIZE:
            raise ReflexiveWatchdogBlock("WORK_READBACK_PAGE_INVALID")
        if first_page is None:
            first_page = entries
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ReflexiveWatchdogBlock("WORK_READBACK_ENTRY_INVALID")
            identifier = _positive_int(entry.get("id"), "work ID")
            number = _positive_int(entry.get("number"), "work number")
            if (identifier in seen_ids or number in seen_numbers or entry.get("state") != "open"
                    or entry.get("url") != f"https://api.github.com/repos/{repository}/issues/{number}"):
                raise ReflexiveWatchdogBlock("WORK_READBACK_ENTRY_INVALID_OR_DUPLICATED")
            seen_ids.add(identifier)
            seen_numbers.add(number)
            items.append({"id": identifier, "number": number,
                          "kind": "PULL_REQUEST" if "pull_request" in entry else "ISSUE"})
        if len(entries) < READBACK_PAGE_SIZE:
            check = _readback_page(f"{prefix}&per_page={READBACK_PAGE_SIZE}&page=1",
                                   directory / "first-page-readback.json", allow_list=True)
            requests += 1
            if check != first_page:
                blocker = "WORK_READBACK_CHANGED_DURING_COLLECTION"
            else:
                complete, blocker = True, None
            break
    return {"schema": "qikvrt_open_work_inventory_v1", "repository": repository,
            "head_sha": expected_head, "observed_at": _iso(now),
            "complete": complete, "truncated": not complete,
            "total_count": len(items), "items": sorted(items, key=lambda item: item["number"]),
            "page_requests": requests, "first_blocker": blocker,
            "scope": "OPEN_GITHUB_ISSUES_AND_PULL_REQUESTS", "effect_ack_done": False}


def _open_work(value: Any, *, repository: str, head: str, now: datetime,
               freshness: int) -> dict[str, Any]:
    if value is None:
        return {"state": "UNKNOWN", "first_blocker": "OPEN_WORK_INVENTORY_MISSING",
                "total_count": None, "items": [], "complete": False}
    value = _mapping(value, "open work inventory")
    if (value.get("schema") != "qikvrt_open_work_inventory_v1"
            or value.get("repository") != repository or value.get("head_sha") != head):
        raise ReflexiveWatchdogBlock("OPEN_WORK_INVENTORY_SUBJECT_DRIFT")
    observed = _timestamp(value.get("observed_at"), "work inventory observation")
    age = int((now - observed).total_seconds())
    if age < 0 or age > freshness:
        raise ReflexiveWatchdogBlock("OPEN_WORK_INVENTORY_STALE_OR_FUTURE")
    if value.get("complete") is not True or value.get("truncated") is not False:
        return {"state": "UNKNOWN", "first_blocker": "OPEN_WORK_INVENTORY_INCOMPLETE",
                "total_count": None, "items": [], "complete": False}
    items = value.get("items")
    if (not isinstance(items, list) or type(value.get("total_count")) is not int
            or value["total_count"] != len(items)):
        raise ReflexiveWatchdogBlock("OPEN_WORK_INVENTORY_COUNT_DRIFT")
    ids, numbers = set(), set()
    for item in items:
        item = _mapping(item, "open work item")
        identifier = _positive_int(item.get("id"), "open work ID")
        number = _positive_int(item.get("number"), "open work number")
        if identifier in ids or number in numbers or item.get("kind") not in {"ISSUE", "PULL_REQUEST"}:
            raise ReflexiveWatchdogBlock("OPEN_WORK_INVENTORY_INVALID_OR_DUPLICATED")
        ids.add(identifier)
        numbers.add(number)
    return {"state": "OPEN" if items else "EMPTY", "first_blocker": None,
            "total_count": len(items), "items": sorted(items, key=lambda item: item["number"]),
            "complete": True, "inventory_sha256": sha256_bytes(canonical_json_bytes(value))}


def _progress_markers(runs: Sequence[Mapping[str, Any]],
                      jobs_by_run: Mapping[str, Sequence[Mapping[str, Any]]],
                      observer_names: set[str]) -> list[str]:
    """Only executed terminal job/step evidence advances the progress clock.

    IDs, attempts, heartbeat timestamps, queued/running state, repeated identical
    failures and observer activity cannot manufacture useful progress.
    """
    markers = set()
    for run in runs:
        if run.get("name") in observer_names:
            continue
        workflow = run.get("path") or run.get("name")
        for job in jobs_by_run.get(_run_id(run), []):
            records = []
            if job.get("status") == "completed" and job.get("conclusion") in {"success", "failure", "timed_out"}:
                records.append({"job": job.get("name"), "conclusion": job.get("conclusion")})
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                raise ReflexiveWatchdogBlock("PROGRESS_STEP_EVIDENCE_INVALID")
            for step in steps:
                if (isinstance(step, Mapping) and step.get("status") == "completed"
                        and step.get("conclusion") in {"success", "failure", "timed_out"}):
                    records.append({"job": job.get("name"), "step": step.get("number"),
                                    "name": step.get("name"), "conclusion": step.get("conclusion")})
            for record in records:
                markers.add(sha256_bytes(canonical_json_bytes({"workflow": workflow, **record})))
    return sorted(markers)


def collect_jobs(runs: Any, *, repository: str, expected_head: str,
                 directory: Path) -> dict[str, Any]:
    plan = job_readback_budget(runs, expected_head=expected_head, required_jobs_only=True)
    receipt = {"state": plan["state"], "first_blocker": plan["first_blocker"],
               "run_inventory_sha256": plan["inventory_sha256"],
               "max_job_requests": MAX_JOB_READBACK_REQUESTS, "job_requests": 0,
               "completed_run_ids": [], "effect_ack_done": False}
    _repository(repository)
    if receipt["state"] == "HOLD":
        return receipt
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.glob("*.json")):
        raise ReflexiveWatchdogBlock("job observation directory is not empty")
    for run_id in plan["run_ids"]:
        run = next(run for run in runs["workflow_runs"] if run["id"] == run_id)
        attempt = _positive_int(run.get("run_attempt"), "selected run attempt")
        remaining = MAX_JOB_READBACK_REQUESTS - receipt["job_requests"]
        value, requests = _collect_pages(
            f"repos/{repository}/actions/runs/{run_id}/jobs?filter=latest", "jobs",
            directory / "pages" / str(run_id), max_requests=remaining,
            expected_head=expected_head, expected_run_id=run_id, expected_run_attempt=attempt,
        )
        receipt["job_requests"] += requests
        (directory / f"{run_id}.json").write_bytes(canonical_json_bytes(value))
        if value["truncated"]:
            receipt.update(state="HOLD", first_blocker=value["first_blocker"])
            break
        receipt["completed_run_ids"].append(run_id)
    return receipt


def _run_order(run: Mapping[str, Any]) -> tuple[datetime, int, str]:
    run_id = _run_id(run)
    return (_run_created_time(run), int(run_id) if run_id.isdecimal() else -1, run_id)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    path = root / CONTRACT_RELATIVE_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReflexiveWatchdogBlock(f"cannot load workflow executor contract: {exc}") from exc
    contract = dict(_mapping(value, "workflow executor contract"))
    if contract.get("schema") != "qikvrt_workflow_executor_mesh_contract_v1":
        raise ReflexiveWatchdogBlock("workflow executor contract schema is not v1")
    try:
        try:
            from tools.qikvrt_workflow_executor import authority_repository, ExecutorBlock
        except ModuleNotFoundError:
            from qikvrt_workflow_executor import authority_repository, ExecutorBlock
        authority_repository(contract, root)
    except ExecutorBlock as exc:
        raise ReflexiveWatchdogBlock(str(exc)) from exc
    prevention = _mapping(
        contract.get("reflexive_deadlock_prevention"),
        "reflexive deadlock prevention contract",
    )
    if prevention.get("enabled") is not True:
        raise ReflexiveWatchdogBlock("reflexive deadlock prevention is not enabled")
    if prevention.get("applies_to") != ["AUTHORITY", "MIRROR", "EVERY_FUTURE_MESH_NODE"]:
        raise ReflexiveWatchdogBlock("reflexive watchdog is not bound to every repository instance")
    if prevention.get("admission_policy") != "PREEMPTIVE_HOLD_BEFORE_SECOND_WRITER":
        raise ReflexiveWatchdogBlock("reflexive watchdog admission policy is not fail-closed")
    work_progress = _mapping(prevention.get("open_work_progress"), "open work progress contract")
    for key, expected in {"enabled": True, "inventory_required_before_quiescence": True,
            "heartbeat_resets_progress_clock": False, "identical_retry_resets_progress_clock": False,
            "existing_authorization_and_writer_guards_preserved": True,
            "universal_liveness_proved": False}.items():
        if work_progress.get(key) is not expected:
            raise ReflexiveWatchdogBlock("open work progress contract absent or weakened: " + key)
    for key in (
        "writer_lease_seconds",
        "queue_lease_seconds",
        "progress_lease_seconds",
        "max_simultaneous_active_writers",
        "max_queued_productive_runs",
    ):
        _positive_int(prevention.get(key), f"reflexive deadlock prevention.{key}")
    gatewatch = _mapping(prevention.get("gatewatch"), "reflexive gatewatch profile")
    if gatewatch.get("enabled") is not True:
        raise ReflexiveWatchdogBlock("reflexive gatewatch profile is not enabled")
    _string(gatewatch.get("receipt_path"), "reflexive gatewatch receipt path")
    _positive_int(
        gatewatch.get("observation_freshness_seconds"),
        "reflexive gatewatch observation freshness",
    )
    observed_names = _string_list(
        gatewatch.get("observed_workflow_names"),
        "reflexive gatewatch observed workflow names",
    )
    if set(_string_list(gatewatch.get("gate_states"), "reflexive gatewatch states")) != GATEWATCH_STATES:
        raise ReflexiveWatchdogBlock("reflexive gatewatch states do not match the controller")
    required_by_scope = _mapping(
        gatewatch.get("required_workflow_names_by_scope"),
        "reflexive gatewatch required workflow names by scope",
    )
    if set(required_by_scope) != GATEWATCH_SCOPES:
        raise ReflexiveWatchdogBlock("reflexive gatewatch scopes are incomplete")
    for scope in sorted(GATEWATCH_SCOPES):
        required = _string_list(
            required_by_scope.get(scope),
            f"reflexive gatewatch required workflow names for {scope}",
            allow_empty=True,
        )
        if any(item not in observed_names for item in required):
            raise ReflexiveWatchdogBlock(
                f"reflexive gatewatch required workflow for {scope} is not observed"
            )
    liveness = _mapping(gatewatch.get("node_liveness"), "reflexive gatewatch node liveness")
    if liveness.get("enabled") is not True:
        raise ReflexiveWatchdogBlock("reflexive gatewatch node liveness is not enabled")
    records_root = _relative_path(liveness.get("records_root"), "node liveness records root")
    for key in ("seed_acceptance_path", "renewal_path", "health_path"):
        record_path = _relative_path(liveness.get(key), f"node liveness {key}")
        if record_path.parent != records_root:
            raise ReflexiveWatchdogBlock(f"node liveness {key} is outside the records root")
    declared_authority = _mapping(contract.get("authority"), "contract authority")
    authority_repository = _string(declared_authority.get("repository"), "authority repository")
    if liveness.get("authority_repository") != authority_repository:
        raise ReflexiveWatchdogBlock("node liveness and executor Authority repositories disagree")
    mirrors = _string_list(declared_authority.get("mirror_repositories"), "mirror repositories")
    if authority_repository.casefold() in {item.casefold() for item in mirrors}:
        raise ReflexiveWatchdogBlock("Authority and Mirror repositories must be distinct")
    _positive_int(liveness.get("warning_seconds"), "node liveness warning seconds")
    if liveness.get("all_records_absent_state") != "NOT_APPLICABLE":
        raise ReflexiveWatchdogBlock("node liveness all-records-absent state must be NOT_APPLICABLE")
    if liveness.get("expired_or_overdue_disposition") != "HOLD":
        raise ReflexiveWatchdogBlock("node liveness expired-or-overdue disposition must be HOLD")
    if liveness.get("authority_head_mismatch_disposition") != "HOLD":
        raise ReflexiveWatchdogBlock("node liveness authority-head-mismatch disposition must be HOLD")
    if liveness.get("artifact_only_materialization") is not True:
        raise ReflexiveWatchdogBlock("node liveness materialization must remain artifact-only")
    return contract


def _runs(value: Mapping[str, Any] | Sequence[Any]) -> list[Mapping[str, Any]]:
    raw: Any = value.get("workflow_runs") if isinstance(value, Mapping) else value
    if not isinstance(raw, list):
        raise ReflexiveWatchdogBlock("workflow run observation must contain workflow_runs")
    return [item for item in raw if isinstance(item, Mapping)]


def _jobs_by_run(value: Mapping[str, Any] | None, *, strict: bool = False) -> dict[str, list[Mapping[str, Any]]]:
    if value is None:
        return {}
    raw = value.get("jobs_by_run", value)
    if not isinstance(raw, Mapping):
        raise ReflexiveWatchdogBlock("job observation must be an object keyed by run id")
    result: dict[str, list[Mapping[str, Any]]] = {}
    for run_id, jobs in raw.items():
        if not isinstance(run_id, str) or not isinstance(jobs, list):
            raise ReflexiveWatchdogBlock("job observation contains an invalid run entry")
        if strict:
            ids = set()
            for job in jobs:
                if (not isinstance(job, Mapping) or type(job.get("id")) is not int
                        or job["id"] <= 0 or job["id"] in ids
                        or job.get("status") not in ACTIVE_STATUSES | {"completed"}):
                    raise ReflexiveWatchdogBlock("JOB_INVENTORY_INVALID: malformed selected job")
                ids.add(job["id"])
        result[run_id] = [item for item in jobs if isinstance(item, Mapping)]
    return result


def load_jobs_directory(path: Path, *, strict: bool = False) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {}
    if not path.exists():
        return result
    for item in sorted(path.glob("*.json")):
        try:
            value = json.loads(item.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReflexiveWatchdogBlock(f"cannot load job observation {item.name}: {exc}") from exc
        jobs = _mapping(value, f"job observation {item.name}").get("jobs")
        if not isinstance(jobs, list):
            raise ReflexiveWatchdogBlock(f"job observation {item.name} does not contain jobs")
        if strict:
            ids = set()
            if (type(value.get("total_count")) is not int or value["total_count"] != len(jobs)
                    or value.get("truncated", False) is not False):
                raise ReflexiveWatchdogBlock(f"JOB_INVENTORY_INCOMPLETE: {item.name}")
            for job in jobs:
                if (not isinstance(job, Mapping) or type(job.get("id")) is not int
                        or job["id"] <= 0 or job["id"] in ids
                        or job.get("status") not in ACTIVE_STATUSES | {"completed"}
                        or ("run_id" in job and str(job["run_id"]) != item.stem)):
                    raise ReflexiveWatchdogBlock(f"JOB_INVENTORY_INVALID: {item.name}")
                ids.add(job["id"])
        result[item.stem] = [entry for entry in jobs if isinstance(entry, Mapping)]
    return result


def validate_job_plan(
    runs_value: Any, jobs_by_run: Mapping[str, Sequence[Mapping[str, Any]]],
    plan: Any, *, expected_head: str,
) -> None:
    expected = job_readback_budget(runs_value, expected_head=expected_head, required_jobs_only=True)
    if expected["state"] != "READY" or plan != expected:
        raise ReflexiveWatchdogBlock("JOB_READBACK_PLAN_INVALID: rederive from the complete exact-head inventory")
    if set(jobs_by_run) != {str(run_id) for run_id in expected["run_ids"]}:
        raise ReflexiveWatchdogBlock("JOB_INVENTORY_INCOMPLETE: selected run job files do not match the plan")
    for run in _runs(runs_value):
        for job in jobs_by_run.get(_run_id(run), []):
            if (job.get("head_sha") != expected_head or job.get("run_id") != run["id"]
                    or job.get("run_attempt") != run.get("run_attempt")):
                raise ReflexiveWatchdogBlock("JOB_INVENTORY_INVALID: job head or attempt drifted")
        if run["status"] == "completed" and any(
            job.get("status") in ACTIVE_STATUSES for job in jobs_by_run.get(_run_id(run), [])
        ):
            raise ReflexiveWatchdogBlock("JOB_INVENTORY_INVALID: terminal run has active jobs")


def _run_time(run: Mapping[str, Any], field: str) -> datetime | None:
    value = run.get(field)
    if not isinstance(value, str) or not value:
        return None
    return _timestamp(value, f"run {run.get('id', '?')} {field}")


def _run_transition_time(run: Mapping[str, Any]) -> datetime:
    for field in ("updated_at", "run_started_at", "created_at"):
        value = _run_time(run, field)
        if value is not None:
            return value
    raise ReflexiveWatchdogBlock(f"run {run.get('id', '?')} has no transition timestamp")


def _run_created_time(run: Mapping[str, Any]) -> datetime:
    value = _run_time(run, "created_at")
    return value if value is not None else _run_transition_time(run)


def _age_seconds(now: datetime, transition: datetime) -> int:
    return max(0, int((now - transition).total_seconds()))


def _run_id(run: Mapping[str, Any]) -> str:
    value = run.get("id")
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str) and value:
        return value
    raise ReflexiveWatchdogBlock("workflow run has no usable id")


def _latest_by_name(runs: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        name = run.get("name")
        if not isinstance(name, str) or not name:
            continue
        current = latest.get(name)
        if current is None or _run_order(run) > _run_order(current):
            latest[name] = run
    return sorted(latest.values(), key=lambda item: str(item.get("name")))


def _job_summary(jobs: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    summary = {
        "total": len(jobs),
        "queued": 0,
        "in_progress": 0,
        "success": 0,
        "skipped": 0,
        "executed_failures": 0,
        "other_terminal": 0,
    }
    for job in jobs:
        status = job.get("status")
        conclusion = job.get("conclusion")
        if status in WAITING_STATUSES:
            summary["queued"] += 1
        elif status == "in_progress":
            summary["in_progress"] += 1
        elif status == "completed":
            if conclusion == "success":
                summary["success"] += 1
            elif conclusion == "skipped":
                summary["skipped"] += 1
            elif conclusion in EXECUTED_FAILURE_CONCLUSIONS:
                summary["executed_failures"] += 1
            else:
                summary["other_terminal"] += 1
        else:
            summary["other_terminal"] += 1
    return summary


def _normalize_run(run: Mapping[str, Any], jobs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "id": _run_id(run),
        "name": run.get("name"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "event": run.get("event"),
        "head_sha": run.get("head_sha"),
        "created_at": _iso(_run_created_time(run)),
        "updated_at": _iso(_run_transition_time(run)),
        "jobs": _job_summary(jobs),
    }


def _latest_by_exact_name(
    runs: Sequence[Mapping[str, Any]], name: str
) -> Mapping[str, Any] | None:
    candidates = [run for run in runs if run.get("name") == name]
    if not candidates:
        return None
    return max(candidates, key=_run_order)


def _gate_state_for_run(
    run: Mapping[str, Any] | None,
    jobs_by_run: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    required: bool,
) -> dict[str, Any]:
    if run is None:
        return {
            "state": "MISSING" if required else "NOT_OBSERVED",
            "reason": "NO_EXACT_HEAD_RUN" if required else "NO_EXACT_HEAD_RUN_NOT_REQUIRED",
            "run": None,
        }
    run_id = _run_id(run)
    jobs = list(jobs_by_run.get(run_id, []))
    summary = _job_summary(jobs)
    status = run.get("status")
    conclusion = run.get("conclusion")
    state: str
    reason: str
    if status in ACTIVE_STATUSES:
        state = "ACTIVE"
        reason = "RUN_NOT_TERMINAL"
    elif status != "completed":
        state = "UNTRUSTED"
        reason = "UNRECOGNIZED_RUN_STATUS"
    elif conclusion in EXECUTED_FAILURE_CONCLUSIONS or summary["executed_failures"]:
        state = "FAILED"
        reason = "EXECUTED_FAILURE"
    elif (conclusion == "success" and summary["total"] and summary["success"]
          and not summary["other_terminal"] and not summary["queued"]
          and not summary["in_progress"]):
        state = "SUCCESS"
        reason = "TERMINAL_SUCCESS_WITH_EXECUTED_JOB_EVIDENCE"
    elif conclusion in UNTRUSTED_CONCLUSIONS:
        state = "UNTRUSTED"
        reason = "ACTION_REQUIRED_OR_STARTUP_FAILURE"
    elif not jobs:
        state = "UNTRUSTED"
        reason = "ZERO_JOB_TERMINAL_RUN"
    else:
        state = "UNTRUSTED"
        reason = "TERMINAL_RUN_LACKS_TRUSTED_SUCCESS_EVIDENCE"
    return {
        "state": state,
        "reason": reason,
        "run": {
            "id": run_id,
            "status": status,
            "conclusion": conclusion,
            "created_at": _iso(_run_created_time(run)),
            "updated_at": _iso(_run_transition_time(run)),
            "jobs": summary,
        },
    }


def _gatewatch_observation(
    contract: Mapping[str, Any],
    runs: Sequence[Mapping[str, Any]],
    jobs_by_run: Mapping[str, Sequence[Mapping[str, Any]]],
    scope: str,
) -> dict[str, Any]:
    if scope not in GATEWATCH_SCOPES:
        raise ReflexiveWatchdogBlock(f"gatewatch observation scope is invalid: {scope}")
    prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
    profile = _mapping(prevention["gatewatch"], "reflexive gatewatch profile")
    observed_names = _string_list(
        profile["observed_workflow_names"], "reflexive gatewatch observed workflow names"
    )
    required_by_scope = _mapping(
        profile["required_workflow_names_by_scope"],
        "reflexive gatewatch required workflow names by scope",
    )
    required_names = set(
        _string_list(
            required_by_scope[scope],
            f"reflexive gatewatch required workflow names for {scope}",
            allow_empty=True,
        )
    )
    gates = []
    for name in observed_names:
        gate = _gate_state_for_run(
            _latest_by_exact_name(runs, name), jobs_by_run, required=name in required_names
        )
        if gate["state"] not in GATEWATCH_STATES:
            raise ReflexiveWatchdogBlock("gatewatch produced an undeclared gate state")
        gates.append({"name": name, "required": name in required_names, **gate})
    failures = [gate for gate in gates if gate["state"] == "FAILED"]
    required_gaps = [
        gate
        for gate in gates
        if gate["required"] and gate["state"] in {"MISSING", "UNTRUSTED"}
    ]
    active_required = [gate for gate in gates if gate["required"] and gate["state"] == "ACTIVE"]
    return {
        "schema": "qikvrt_exact_head_trusted_gate_matrix_v1",
        "scope": scope,
        "required_workflow_names": sorted(required_names),
        "gates": gates,
        "executed_failures": failures,
        "required_evidence_gaps": required_gaps,
        "active_required_gates": active_required,
    }


def _record_bytes(path: Path, label: str) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    if not path.exists():
        return None, {"path": path.as_posix(), "present": False}
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, {
            "path": path.as_posix(),
            "present": True,
            "state": "INVALID",
            "reason": f"MALFORMED_{label.upper()}_RECORD",
        }
    if not isinstance(value, Mapping):
        return None, {
            "path": path.as_posix(),
            "present": True,
            "state": "INVALID",
            "reason": f"MALFORMED_{label.upper()}_RECORD",
        }
    return value, {
        "path": path.as_posix(),
        "present": True,
        "content_sha256": sha256_bytes(raw),
    }


def _node_liveness_observation(
    contract: Mapping[str, Any],
    *,
    root: Path,
    directory: Path | None,
    authority_head: str | None,
    now: datetime,
) -> dict[str, Any]:
    prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
    profile = _mapping(
        _mapping(prevention["gatewatch"], "reflexive gatewatch profile")["node_liveness"],
        "reflexive gatewatch node liveness",
    )
    records_root = directory if directory is not None else root / _relative_path(
        profile["records_root"], "node liveness records root"
    )
    paths = {
        "seed_acceptance": records_root / Path(profile["seed_acceptance_path"]).name,
        "renewal": records_root / Path(profile["renewal_path"]).name,
        "health": records_root / Path(profile["health_path"]).name,
    }
    loaded = {name: _record_bytes(path, name) for name, path in paths.items()}
    records = {name: dict(metadata) for name, (_, metadata) in loaded.items()}
    present_count = sum(1 for value in records.values() if value["present"])
    if present_count == 0:
        for value in records.values():
            value["state"] = "NOT_APPLICABLE"
            value["reason"] = "NO_NODE_LOCAL_LIVENESS_RECORDS"
        return {
            "schema": "qikvrt_node_liveness_gatewatch_v1",
            "state": "NOT_APPLICABLE",
            "records_root": records_root.as_posix(),
            "authority_head": authority_head,
            "records": records,
            "blocking_records": [],
        }
    if present_count != len(records):
        for value in records.values():
            if not value["present"]:
                value["state"] = "MISSING"
                value["reason"] = "PARTIAL_NODE_LIVENESS_RECORD_SET"
        return {
            "schema": "qikvrt_node_liveness_gatewatch_v1",
            "state": "HOLD",
            "records_root": records_root.as_posix(),
            "authority_head": authority_head,
            "records": records,
            "blocking_records": [
                {"record": name, "reason": value.get("reason")}
                for name, value in records.items()
                if value.get("state") in {"MISSING", "INVALID"}
            ],
        }

    invalid = [
        {"record": name, "reason": metadata.get("reason", "MALFORMED_NODE_LIVENESS_RECORD")}
        for name, (document, metadata) in loaded.items()
        if document is None
    ]
    if invalid:
        return {
            "schema": "qikvrt_node_liveness_gatewatch_v1",
            "state": "HOLD",
            "records_root": records_root.as_posix(),
            "authority_head": authority_head,
            "records": records,
            "blocking_records": invalid,
        }

    acceptance, _ = loaded["seed_acceptance"]
    renewal, _ = loaded["renewal"]
    health, _ = loaded["health"]
    acceptance_metadata = records["seed_acceptance"]
    renewal_metadata = records["renewal"]
    health_metadata = records["health"]
    assert acceptance is not None and renewal is not None and health is not None
    warning_seconds = _positive_int(profile["warning_seconds"], "node liveness warning seconds")
    blocking: list[dict[str, str]] = []

    # Equal Git commits across repositories do not establish equal roles.
    # Keep historical Seed receipts unchanged and reject their stale role binding.
    receipt_repositories = [acceptance[key] for key in ("authority_repository", "seed_repository") if key in acceptance]
    if not receipt_repositories or any(item != profile["authority_repository"] for item in receipt_repositories):
        acceptance_metadata["state"] = "UNTRUSTED"
        acceptance_metadata["reason"] = "SEED_ACCEPTANCE_AUTHORITY_REPOSITORY_MISMATCH"
        blocking.append({"record": "seed_acceptance", "reason": "SEED_ACCEPTANCE_AUTHORITY_REPOSITORY_MISMATCH"})
    elif authority_head is None:
        acceptance_metadata["state"] = "UNTRUSTED"
        acceptance_metadata["reason"] = "AUTHORITY_HEAD_UNOBSERVED"
        blocking.append({"record": "seed_acceptance", "reason": "AUTHORITY_HEAD_UNOBSERVED"})
    else:
        observed = acceptance.get("observed_authority_commit")
        if observed == authority_head:
            acceptance_metadata["state"] = "FRESH"
            acceptance_metadata["reason"] = "AUTHORITY_HEAD_EXACTLY_BOUND"
        else:
            acceptance_metadata["state"] = "STALE"
            acceptance_metadata["reason"] = "SEED_ACCEPTANCE_AUTHORITY_HEAD_STALE"
            acceptance_metadata["observed_authority_commit"] = observed
            blocking.append(
                {"record": "seed_acceptance", "reason": "SEED_ACCEPTANCE_AUTHORITY_HEAD_STALE"}
            )

    try:
        due = _timestamp(renewal.get("next_renewal_due_utc"), "node renewal due")
        renewal_metadata["next_renewal_due_utc"] = _iso(due)
        seconds = int((due - now).total_seconds())
        if seconds <= 0:
            renewal_metadata["state"] = "OVERDUE"
            renewal_metadata["reason"] = "NODE_REGISTRATION_RENEWAL_OVERDUE"
            blocking.append({"record": "renewal", "reason": "NODE_REGISTRATION_RENEWAL_OVERDUE"})
        elif seconds <= warning_seconds:
            renewal_metadata["state"] = "EXPIRING"
            renewal_metadata["reason"] = "NODE_REGISTRATION_RENEWAL_DUE_SOON"
        else:
            renewal_metadata["state"] = "FRESH"
            renewal_metadata["reason"] = "NODE_REGISTRATION_RENEWAL_CURRENT"
    except ReflexiveWatchdogBlock:
        renewal_metadata["state"] = "INVALID"
        renewal_metadata["reason"] = "MALFORMED_RENEWAL_DUE"
        blocking.append({"record": "renewal", "reason": "MALFORMED_RENEWAL_DUE"})

    try:
        expires = _timestamp(health.get("expires_utc"), "node health expiry")
        health_metadata["expires_utc"] = _iso(expires)
        seconds = int((expires - now).total_seconds())
        if seconds <= 0:
            health_metadata["state"] = "EXPIRED"
            health_metadata["reason"] = "NODE_HEALTH_EXPIRED"
            blocking.append({"record": "health", "reason": "NODE_HEALTH_EXPIRED"})
        elif seconds <= warning_seconds:
            health_metadata["state"] = "EXPIRING"
            health_metadata["reason"] = "NODE_HEALTH_EXPIRING_SOON"
        else:
            health_metadata["state"] = "FRESH"
            health_metadata["reason"] = "NODE_HEALTH_CURRENT"
    except ReflexiveWatchdogBlock:
        health_metadata["state"] = "INVALID"
        health_metadata["reason"] = "MALFORMED_HEALTH_EXPIRY"
        blocking.append({"record": "health", "reason": "MALFORMED_HEALTH_EXPIRY"})

    return {
        "schema": "qikvrt_node_liveness_gatewatch_v1",
        "state": "HOLD" if blocking else "OBSERVE",
        "records_root": records_root.as_posix(),
        "authority_head": authority_head,
        "records": records,
        "blocking_records": blocking,
    }


def _resource_graph(
    active_writers: Sequence[Mapping[str, Any]],
    waiting_productive: Sequence[Mapping[str, Any]],
    active_productive: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    writer_ids = [_run_id(run) for run in active_writers]
    waiting_ids = [_run_id(run) for run in waiting_productive]
    running_ids = [_run_id(run) for run in active_productive if run.get("status") == "in_progress"]
    return {
        "schema": "qikvrt_repository_resource_graph_v1",
        "resources": [
            {
                "resource": "REPOSITORY_WRITE_LEASE",
                "capacity": 1,
                "holders": writer_ids[:1],
                "conflicting_holders_or_requesters": writer_ids[1:],
            },
            {
                "resource": "RUNNER_CAPACITY",
                "capacity": "PLATFORM_MANAGED_UNKNOWN",
                "observed_holders": running_ids,
                "observed_waiters": waiting_ids,
            },
        ],
        "cycle_detected": False,
        "pre_cycle_conflict_detected": len(writer_ids) > 1,
    }


def authority_repository_binding(contract: Mapping[str, Any]) -> str:
    from tools.qikvrt_workflow_executor import load_repository_roles
    repository = _mapping(contract.get("authority"), "authority").get("repository")
    liveness = contract["reflexive_deadlock_prevention"]["gatewatch"]["node_liveness"]
    if repository != load_repository_roles()["AUTHORITY"] or liveness.get("authority_repository") != repository:
        raise ReflexiveWatchdogBlock("authority repository binding is invalid")
    return repository


def observe_authority(*, root: Path = ROOT) -> dict[str, Any]:
    repository = authority_repository_binding(load_contract(root))
    endpoint = f"repos/{repository}/git/ref/heads/main"
    command = ["gh", "api", "--method", "GET", "--include", endpoint]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    statuses = re.findall(r"^HTTP/[^ ]+ ([0-9]{3})", result.stdout, re.MULTILINE)
    status = int(statuses[-1]) if statuses else None
    observation = {
        "schema": "qikvrt_authority_readback_v1", "repository": repository,
        "endpoint": endpoint, "method": "GET", "http_status": status,
        "exit_code": result.returncode, "response_sha256": sha256_bytes(result.stdout.encode()),
        "diagnostic_sha256": sha256_bytes(result.stderr.encode()),
        "cause": "UNESTABLISHED", "authority_destroyed": False,
        "takeover_allowed": False, "writer_admission_allowed": False, "effect_ack_done": False,
    }
    if result.returncode != 0 and status in {401, 403, 404, 429, 500, 502, 503, 504}:
        return {**observation, "state": "AUTHORITY_UNAVAILABLE", "disposition": "HOLD",
                "capability_blocker": "AUTHORITY_MAIN_READ_CAPABILITY_UNAVAILABLE", "head_sha": None}
    if result.returncode != 0 or status != 200:
        raise ReflexiveWatchdogBlock("unclassified authority readback failure")
    try:
        body = result.stdout.replace("\r\n", "\n").split("\n\n", 1)[1]
        value = json.loads(body)
        if value.get("ref") != "refs/heads/main" or value["object"].get("type") != "commit":
            raise ReflexiveWatchdogBlock("authority ref binding is invalid")
        head = _head_sha(value["object"]["sha"], "authority head")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ReflexiveWatchdogBlock("malformed authority readback") from exc
    return {**observation, "state": "AUTHORITY_OBSERVED", "disposition": "OBSERVE",
            "capability_blocker": None, "head_sha": head}


def validate_authority_observation(value: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    repository = authority_repository_binding(contract)
    if (value.get("schema") != "qikvrt_authority_readback_v1"
        or value.get("repository") != repository
        or value.get("endpoint") != f"repos/{repository}/git/ref/heads/main"
        or value.get("method") != "GET"
        or any(value.get(key) is not False for key in
               ("authority_destroyed", "takeover_allowed", "writer_admission_allowed", "effect_ack_done"))):
        raise ReflexiveWatchdogBlock("authority observation binding or effect boundary is invalid")
    if value.get("state") == "AUTHORITY_UNAVAILABLE":
        if (value.get("http_status") not in {401,403,404,429,500,502,503,504}
            or type(value.get("exit_code")) is not int or value["exit_code"] <= 0
            or value.get("head_sha") is not None or value.get("disposition") != "HOLD"
            or value.get("cause") != "UNESTABLISHED"
            or value.get("capability_blocker") != "AUTHORITY_MAIN_READ_CAPABILITY_UNAVAILABLE"):
            raise ReflexiveWatchdogBlock("invalid authority capability HOLD")
    elif value.get("state") == "AUTHORITY_OBSERVED":
        if value.get("http_status") != 200 or value.get("exit_code") != 0:
            raise ReflexiveWatchdogBlock("invalid successful authority observation")
        _head_sha(value.get("head_sha"), "authority head")
    else:
        raise ReflexiveWatchdogBlock("invalid authority observation state")
    return dict(value)


def analyze(
    runs_value: Mapping[str, Any] | Sequence[Any],
    jobs_value: Mapping[str, Any] | None,
    *,
    expected_head: str,
    expected_tree: str,
    repository: str,
    now: datetime,
    baseline: Mapping[str, Any] | None = None,
    root: Path = ROOT,
    observation_scope: str = "MAIN",
    node_liveness_dir: Path | None = None,
    authority_head: str | None = None,
    authority_observation: Mapping[str, Any] | None = None,
    job_plan: Mapping[str, Any] | None = None,
    work_value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = load_contract(root)
    if authority_observation is not None:
        authority_observation = validate_authority_observation(authority_observation, contract)
        if authority_head is not None and authority_head != authority_observation.get("head_sha"):
            raise ReflexiveWatchdogBlock("conflicting authority head observations")
        authority_head = authority_observation.get("head_sha")
    if authority_head is not None:
        authority_head = _head_sha(authority_head, "authority head observation")
    prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
    writer_names = set(
        _mapping(contract["dispatch_policy"], "dispatch policy").get("writer_workflow_names", [])
    )
    observer_names = set(prevention.get("observer_workflow_names", []))
    if not writer_names or any(not isinstance(item, str) or not item for item in writer_names):
        raise ReflexiveWatchdogBlock("writer workflow names are invalid")
    if any(not isinstance(item, str) or not item for item in observer_names):
        raise ReflexiveWatchdogBlock("observer workflow names are invalid")

    runs = [run for run in _runs(runs_value) if run.get("head_sha") == expected_head]
    jobs_by_run = _jobs_by_run(jobs_value, strict=job_plan is not None)
    if job_plan is not None:
        validate_job_plan(runs_value, jobs_by_run, job_plan, expected_head=expected_head)
    normalized = [
        _normalize_run(run, jobs_by_run.get(_run_id(run), []))
        for run in sorted(runs, key=lambda item: (_run_created_time(item), _run_id(item)))
    ]
    if job_plan is not None:
        for item in normalized:
            item["jobs_observed"] = item["id"] in jobs_by_run
            if not item["jobs_observed"]:
                item["jobs"] = None
    productive = [run for run in runs if run.get("name") not in observer_names]
    active_productive = [run for run in productive if run.get("status") in ACTIVE_STATUSES]
    waiting_productive = [run for run in productive if run.get("status") in WAITING_STATUSES]
    active_writers = [
        run for run in runs if run.get("name") in writer_names and run.get("status") in ACTIVE_STATUSES
    ]

    writer_lease = _positive_int(prevention["writer_lease_seconds"], "writer lease")
    queue_lease = _positive_int(prevention["queue_lease_seconds"], "queue lease")
    progress_lease = _positive_int(prevention["progress_lease_seconds"], "progress lease")
    max_writers = _positive_int(
        prevention["max_simultaneous_active_writers"], "maximum simultaneous active writers"
    )
    max_queued = _positive_int(
        prevention["max_queued_productive_runs"], "maximum queued productive runs"
    )

    stale_writers = [
        {
            "id": _run_id(run),
            "name": run.get("name"),
            "age_seconds": _age_seconds(now, _run_transition_time(run)),
        }
        for run in active_writers
        if _age_seconds(now, _run_transition_time(run)) >= writer_lease
    ]
    queue_ages = [
        {
            "id": _run_id(run),
            "name": run.get("name"),
            "age_seconds": _age_seconds(now, _run_created_time(run)),
        }
        for run in waiting_productive
    ]
    stale_queue = [item for item in queue_ages if item["age_seconds"] >= queue_lease]

    latest = _latest_by_name(runs)
    untrusted = []
    for run in latest:
        if run.get("name") in observer_names or run.get("status") != "completed":
            continue
        run_jobs = jobs_by_run.get(_run_id(run), [])
        conclusion = run.get("conclusion")
        if conclusion in UNTRUSTED_CONCLUSIONS or not run_jobs:
            untrusted.append(
                {
                    "id": _run_id(run),
                    "name": run.get("name"),
                    "conclusion": conclusion,
                    "job_count": len(run_jobs),
                    "reason": (
                        "ACTION_REQUIRED_OR_STARTUP_FAILURE"
                        if conclusion in UNTRUSTED_CONCLUSIONS
                        else "ZERO_JOB_TERMINAL_RUN"
                    ),
                }
            )

    gatewatch = _gatewatch_observation(contract, runs, jobs_by_run, observation_scope)
    liveness = _node_liveness_observation(
        contract,
        root=root,
        directory=node_liveness_dir,
        authority_head=authority_head,
        now=now,
    )

    work = _open_work(work_value, repository=repository, head=expected_head, now=now,
                      freshness=prevention["gatewatch"]["observation_freshness_seconds"])
    progress_markers = _progress_markers(runs, jobs_by_run, observer_names)
    last_progress_at = now
    progress_clock_basis = "FIRST_VERIFIED_OBSERVATION"
    baseline_same = False
    baseline_binding_same = False
    baseline_age = None
    if baseline is not None:
        previous_fingerprint = baseline.get("progress_fingerprint")
        previous_observed = baseline.get("observed_at")
        previous_head = baseline.get("head_sha")
        previous_tree = baseline.get("tree_sha")
        if (
            isinstance(previous_fingerprint, str)
            and isinstance(previous_observed, str)
            and previous_head == expected_head
            and previous_tree == expected_tree
            and baseline.get("repository", repository) == repository
            and _mapping(baseline.get("gatewatch", {}), "baseline gatewatch").get("scope", observation_scope) == observation_scope
        ):
            baseline_binding_same = True
            previous_time = _timestamp(previous_observed, "baseline observed_at")
            if previous_time > now:
                raise ReflexiveWatchdogBlock("BASELINE_OBSERVATION_FROM_FUTURE")
            baseline_age = _age_seconds(now, previous_time)
            previous_markers = baseline.get("progress_markers")
            if previous_markers is not None:
                if (not isinstance(previous_markers, list) or len(previous_markers) > 50000
                        or any(not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item)
                               for item in previous_markers)
                        or len(set(previous_markers)) != len(previous_markers)
                        or previous_fingerprint != sha256_bytes(canonical_json_bytes(sorted(previous_markers)))):
                    raise ReflexiveWatchdogBlock("BASELINE_PROGRESS_MARKERS_INVALID")
                baseline_same = not set(progress_markers).difference(previous_markers)
                progress_markers = sorted(set(progress_markers).union(previous_markers))
            else:
                # Historical receipts supply no invented cumulative clock.
                baseline_same = previous_fingerprint == sha256_bytes(canonical_json_bytes(progress_markers))
            if baseline_same:
                progress_clock_basis = "CARRIED_EXACT_SUBJECT_BASELINE"
                last_progress_at = _timestamp(baseline.get("last_progress_at", previous_observed),
                                              "baseline last useful progress")
                if last_progress_at > previous_time:
                    raise ReflexiveWatchdogBlock("BASELINE_PROGRESS_CLOCK_INVALID")
            else:
                progress_clock_basis = "NEW_EXECUTED_EVIDENCE_OBSERVED"
    progress_fingerprint = sha256_bytes(canonical_json_bytes(progress_markers))
    unchanged_for = _age_seconds(now, last_progress_at)

    blocker: str | None = None
    state = "SAFE_PROGRESS"
    disposition = "OBSERVE"
    productive_edge = "CONTINUE_REFLEXIVE_OBSERVATION"
    safe_continuation = "Preserve one writer, exact-head evidence, and original state-transition observations."

    if authority_observation is not None and authority_observation["state"] == "AUTHORITY_UNAVAILABLE":
        state = "AUTHORITY_UNAVAILABLE"
        blocker = authority_observation["capability_blocker"]
        disposition = "HOLD"
        productive_edge = "RESTORE_AUTHORITY_READ_CAPABILITY_AND_REOBSERVE"
        safe_continuation = "Continue read-only subject observation; no takeover or writer admission."
    elif len(active_writers) > max_writers:
        state = "PREEMPTIVE_HOLD_COMPETING_WRITERS"
        blocker = "MORE_THAN_ONE_ACTIVE_REPOSITORY_WRITER"
        disposition = "HOLD"
        productive_edge = "SERIALIZE_TO_ONE_EXPECTED_HEAD_WRITER"
        safe_continuation = "Do not start or promote a second writer; retain only one exact-head-bound writer."
    elif stale_writers:
        state = "PREEMPTIVE_HOLD_STALE_WRITER_LEASE"
        blocker = "ACTIVE_WRITER_EXCEEDED_PROGRESS_LEASE"
        disposition = "HOLD"
        productive_edge = "REOBSERVE_STALE_WRITER_JOBS_STEPS_AND_RECEIPT"
        safe_continuation = "Keep the writer lease exclusive and diagnose its first deterministic stalled step."
    elif work["state"] == "UNKNOWN":
        state = "PREEMPTIVE_HOLD_WORK_INVENTORY"
        blocker = work["first_blocker"]
        disposition = "HOLD"
        productive_edge = "RESTORE_COMPLETE_OPEN_WORK_READBACK"
        safe_continuation = "Restore the original queue read path; an unavailable inventory is not an empty queue."
    elif (active_productive or work["state"] == "OPEN") and baseline_same and unchanged_for >= progress_lease:
        state = "PREEMPTIVE_HOLD_NO_PROGRESS_TRANSITION"
        blocker = ("OPEN_WORK_WITHOUT_USEFUL_PROGRESS" if work["state"] == "OPEN"
                   else "ACTIVE_TOPOLOGY_UNCHANGED_BEYOND_PROGRESS_LEASE")
        disposition = "HOLD"
        productive_edge = "REOBSERVE_EXACT_RUN_JOBS_BEFORE_ANY_NEW_WRITER"
        safe_continuation = "Diagnose the first stalled edge and continue an admitted repair; preserve writer fencing and causal retry guards."
    elif work["state"] == "OPEN" and not active_productive:
        state = "CONTINUATION_REQUIRED_OPEN_WORK"
        blocker = "OPEN_WORK_WITHOUT_PRODUCTIVE_EXECUTION"
        disposition = "HOLD"
        productive_edge = "RESUME_ADMITTED_OPEN_WORK_THROUGH_EXISTING_CONTINUATION"
        safe_continuation = "Triage preserved open work in the existing consumer and execute only an already admitted successor."
    elif len(waiting_productive) > max_queued or stale_queue:
        state = "PREEMPTIVE_HOLD_QUEUE_PRESSURE"
        blocker = "RUNNER_QUEUE_EXCEEDED_PREVENTION_THRESHOLD"
        disposition = "HOLD"
        productive_edge = "COALESCE_OBSERVERS_AND_PRESERVE_WRITER_SERIALIZATION"
        safe_continuation = "Cancel only superseded observer runs; do not add another productive writer."
    elif gatewatch["executed_failures"]:
        state = "PREEMPTIVE_HOLD_EXECUTED_GATE_FAILURE"
        blocker = "TRUSTED_GATE_EXECUTED_FAILURE"
        disposition = "HOLD"
        productive_edge = "REPAIR_OR_REOBSERVE_FIRST_FAILED_TRUSTED_GATE"
        safe_continuation = "Do not infer a terminal gate success; retain the exact failed run and job evidence."
    elif liveness["blocking_records"]:
        first_liveness_blocker = liveness["blocking_records"][0]
        state = "PREEMPTIVE_HOLD_NODE_LIVENESS"
        blocker = first_liveness_blocker["reason"]
        disposition = "HOLD"
        productive_edge = "RENEW_OR_REOBSERVE_FIRST_BLOCKING_NODE_LIVENESS_RECORD"
        safe_continuation = "Keep the gatewatch read-only; do not fabricate a liveness renewal or acceptance record."
    elif gatewatch["required_evidence_gaps"]:
        state = "PREEMPTIVE_HOLD_REQUIRED_GATE_EVIDENCE"
        blocker = "REQUIRED_TRUSTED_GATE_EVIDENCE_MISSING_OR_UNTRUSTED"
        disposition = "HOLD"
        productive_edge = "OBTAIN_TRUSTED_EXACT_HEAD_REQUIRED_GATE_EVIDENCE"
        safe_continuation = "Wait for an exact-head required gate with executed trusted job evidence."
    elif (
        baseline_binding_same
        and baseline_age is not None
        and baseline_age >= _positive_int(
            _mapping(prevention["gatewatch"], "reflexive gatewatch profile")[
                "observation_freshness_seconds"
            ],
            "reflexive gatewatch observation freshness",
        )
    ):
        state = "PREEMPTIVE_HOLD_OBSERVATION_CADENCE_BREACH"
        blocker = "EXACT_HEAD_GATEWATCH_RECEIPT_EXCEEDED_FRESHNESS_BOUND"
        disposition = "HOLD"
        productive_edge = "REESTABLISH_EXACT_HEAD_FIVE_MINUTE_GATEWATCH_RECEIPT"
        safe_continuation = "Do not infer a continuous observer tick from an old receipt; reobserve the exact head."
    elif untrusted:
        state = "UNTRUSTED_EXECUTION_GAP"
        blocker = "LATEST_TERMINAL_RUN_LACKS_TRUSTED_JOB_EVIDENCE"
        disposition = "HOLD"
        productive_edge = "OBTAIN_TRUSTED_EXACT_HEAD_JOB_EVIDENCE"
        safe_continuation = "Use a repository-declared trusted exact-head verification path; do not infer success."
    elif not active_productive:
        state = "QUIESCENT_OBSERVATION"
        productive_edge = "KEEP_REFLEXIVE_OBSERVER_FRESH"
        safe_continuation = "Retain the complete GitHub queue observation and continue on native state transitions; other task stores and product completion remain unverified."

    resource_graph = _resource_graph(active_writers, waiting_productive, active_productive)
    observed_at = _iso(now)
    receipt = {
        "schema": "qikvrt_reflexive_repository_watchdog_receipt_v1",
        "contract_id": contract["contract_id"],
        "repository": repository,
        "head_sha": expected_head,
        "tree_sha": expected_tree,
        "observed_at": observed_at,
        "state": state,
        "disposition": disposition,
        "first_blocker": blocker,
        "productive_edge": productive_edge,
        "safe_continuation": safe_continuation,
        "effect_already_occurred": False,
        "effect_ack_done": False,
        "authority_observation": authority_observation,
        "progress_fingerprint": progress_fingerprint,
        "progress_markers": progress_markers,
        "last_progress_at": _iso(last_progress_at),
        "progress_clock_basis": progress_clock_basis,
        "unchanged_for_seconds": unchanged_for,
        "open_work": work,
        "continuation_obligation": {
            "required": work["state"] == "OPEN",
            "inventory_verified": work["complete"],
            "productive_execution_observed": bool(active_productive),
            "silent_idle_allowed": work["state"] == "EMPTY",
            "next_action": productive_edge,
            "effect_permission": False,
        },
        "baseline": {
            "available": baseline is not None,
            "same_head_and_tree": baseline_binding_same,
            "same_progress_fingerprint": baseline_same,
            "age_seconds": baseline_age,
        },
        "leases": {
            "writer_lease_seconds": writer_lease,
            "queue_lease_seconds": queue_lease,
            "progress_lease_seconds": progress_lease,
        },
        "observations": {
            "exact_head_run_count": len(runs),
            "active_productive_runs": [_run_id(run) for run in active_productive],
            "active_writers": [_run_id(run) for run in active_writers],
            "stale_writers": stale_writers,
            "waiting_productive_runs": queue_ages,
            "untrusted_terminal_runs": untrusted,
            "runs": normalized,
            "job_readback_plan": job_plan,
            "run_job_evidence": [{"run": dict(run), "jobs": jobs_by_run.get(_run_id(run), [])}
                                 for run in runs if job_plan is None or _run_id(run) in jobs_by_run]
                                if authority_observation is not None else [],
        },
        "gatewatch": {
            **gatewatch,
            "observation_freshness_seconds": _positive_int(
                _mapping(prevention["gatewatch"], "reflexive gatewatch profile")[
                    "observation_freshness_seconds"
                ],
                "reflexive gatewatch observation freshness",
            ),
            "node_liveness": liveness,
        },
        "resource_graph": resource_graph,
        "boundaries": {
            "watchdog_terminality_is_gate_success": False,
            "no_active_runner_is_pipeline_empty": False,
            "action_required_is_trusted_execution": False,
            "zero_job_is_trusted_execution": False,
            "gatewatch_terminality_is_gate_success": False,
            "liveness_record_observation_mutates_repository": False,
            "automatic_writer_cancellation": False,
            "repository_mutation": False,
            "external_effect": False,
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
            "DEADLOCK_FREEDOM_PROVED": False,
        },
    }
    receipt["semantic_fingerprint"] = sha256_bytes(
        canonical_json_bytes(
            {
                key: value
                for key, value in receipt.items()
                if key not in {"observed_at", "semantic_fingerprint"}
            }
        )
    )
    return receipt


def observation_failure_receipt(
    *,
    expected_head: str,
    observed_head: str,
    observed_tree: str,
    repository: str,
    now: datetime,
    run_id: int,
    run_attempt: int,
    stage: str,
    exit_code: int,
) -> dict[str, Any]:
    """Preserve an observation error without inventing live state or progress."""
    expected_head = _head_sha(expected_head, "expected head")
    observed_head = _head_sha(observed_head, "checkout head")
    observed_tree = _head_sha(observed_tree, "checkout tree")
    repository = _string(repository, "repository")
    stage = _string(stage, "failed observation stage")
    exit_code = _positive_int(exit_code, "failed observation exit code")
    if exit_code > 255:
        raise ReflexiveWatchdogBlock("failed observation exit code must be at most 255")
    receipt = {
        "schema": "qikvrt_reflexive_observation_failure_receipt_v1",
        "repository": repository,
        "head_sha": observed_head,
        "tree_sha": observed_tree,
        "expected_head_sha": expected_head,
        "expected_head_matches_checkout": expected_head == observed_head,
        "observed_at": _iso(now),
        "run_id": _positive_int(run_id, "workflow run ID"),
        "run_attempt": _positive_int(run_attempt, "workflow run attempt"),
        "state": "OBSERVATION_FAILED",
        "disposition": "HOLD",
        "first_blocker": "REPOSITORY_REOBSERVATION_FAILED",
        "failure": {"stage": stage, "exit_code": exit_code},
        "live_subject_reobserved": False,
        "pipeline_progress": "UNKNOWN",
        "productive_edge": False,
        "safe_continuation": False,
        "effect_already_occurred": False,
        "effect_ack_done": False,
        "next_action": "RESTORE_FAILED_READ_PATH_THEN_REOBSERVE_EXISTING_WORK_UNIT",
        "retry_condition": "FAILED_READ_PATH_RECOVERED_AND_EXACT_SUBJECT_REOBSERVED",
        "boundaries": {
            "observation_failure_is_quiescence": False,
            "artifact_upload_is_gate_success": False,
            "historical_receipt_is_fresh_evidence": False,
            "repository_mutation": False,
            "external_effect": False,
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
        },
    }
    receipt["semantic_fingerprint"] = sha256_bytes(
        canonical_json_bytes({key: value for key, value in receipt.items() if key != "observed_at"})
    )
    return receipt


def _read_json(path: Path, label: str) -> Mapping[str, Any] | Sequence[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReflexiveWatchdogBlock(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, (Mapping, list)):
        raise ReflexiveWatchdogBlock(f"{label} must be an object or list")
    return value


def repair_handoff(analysis_bytes: bytes, *, run_id: int, run_attempt: int,
                   producer_event: str, parent_workflow: str = "") -> dict[str, Any]:
    """Carry exact observation bytes as data; never turn a diagnosis into permission."""
    analysis = json.loads(analysis_bytes)
    _mapping(analysis, "watchdog analysis")
    if analysis.get("schema") not in {
        "qikvrt_reflexive_repository_watchdog_receipt_v1",
        "qikvrt_reflexive_observation_failure_receipt_v1",
    }:
        raise ReflexiveWatchdogBlock("unsupported repair source")
    subject = {"repository": _string(analysis.get("repository"), "repository"),
               "head": _head_sha(analysis.get("head_sha"), "head"),
               "tree": _head_sha(analysis.get("tree_sha"), "tree")}
    # A consumer completion must not recursively manufacture another work ring.
    feedback = (producer_event == "workflow_run" and
                parent_workflow == "QIK-VRT autonomous draft-PR continuation")
    needed = analysis.get("disposition") == "HOLD" and not feedback
    digest = sha256_bytes(analysis_bytes)
    origin = {"run_id": _positive_int(run_id, "producer run"),
              "run_attempt": _positive_int(run_attempt, "producer attempt"),
              "workflow_path": ".github/workflows/qikvrt_reflexive_repository_watchdog.yml",
              "event": _string(producer_event, "producer event")}
    identity = sha256_bytes(canonical_json_bytes({"subject": subject,
                        "origin": origin, "analysis_sha256": digest}))
    return {"schema": "qikvrt_error_analysis_handoff_v1", "subject": subject,
            "origin": origin, "work_unit_id": identity,
            "analysis_sha256": digest, "analysis_utf8": analysis_bytes.decode("utf-8"),
            "consumer": "tools/qikvrt_autonomous_self_heal.py:repair-consume",
            "state": "REPAIR_INPUT_REQUIRED" if needed else "NOOP",
            "causal_status": "OBSERVATION_NOT_ESTABLISHED_CAUSE",
            "hop_count": 1, "effect_permission": False, "effect_ack_done": False}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    runs_parser = subcommands.add_parser("collect-runs")
    runs_parser.add_argument("--repository", required=True)
    runs_parser.add_argument("--expect-head", required=True)
    runs_parser.add_argument("--pages-dir", type=Path, required=True)
    runs_parser.add_argument("--json", action="store_true")
    work_parser = subcommands.add_parser("collect-work")
    work_parser.add_argument("--repository", required=True)
    work_parser.add_argument("--expect-head", required=True)
    work_parser.add_argument("--pages-dir", type=Path, required=True)
    work_parser.add_argument("--now", required=True)
    work_parser.add_argument("--json", action="store_true")
    jobs_parser = subcommands.add_parser("collect-jobs")
    jobs_parser.add_argument("--runs-file", type=Path, required=True)
    jobs_parser.add_argument("--repository", required=True)
    jobs_parser.add_argument("--expect-head", required=True)
    jobs_parser.add_argument("--jobs-dir", type=Path, required=True)
    jobs_parser.add_argument("--json", action="store_true")
    budget_parser = subcommands.add_parser("job-readback-budget")
    budget_parser.add_argument("--runs-file", type=Path, required=True)
    budget_parser.add_argument("--expect-head", required=True)
    budget_parser.add_argument("--required-jobs-only", action="store_true")
    budget_parser.add_argument("--inventory-output", type=Path)
    budget_parser.add_argument("--jobs-dir", type=Path)
    budget_parser.add_argument("--json", action="store_true")
    analyze_parser = subcommands.add_parser("analyze")
    analyze_parser.add_argument("--runs-file", type=Path, required=True)
    analyze_parser.add_argument("--jobs-dir", type=Path, required=True)
    analyze_parser.add_argument("--job-plan-file", type=Path)
    analyze_parser.add_argument("--baseline", type=Path)
    analyze_parser.add_argument("--work-file", type=Path)
    analyze_parser.add_argument("--expect-head", required=True)
    analyze_parser.add_argument("--expect-tree", required=True)
    analyze_parser.add_argument("--repository", required=True)
    analyze_parser.add_argument("--now", required=True)
    analyze_parser.add_argument("--observation-scope", choices=sorted(GATEWATCH_SCOPES), default="MAIN")
    analyze_parser.add_argument("--node-liveness-dir", type=Path)
    analyze_parser.add_argument("--authority-head-file", type=Path)
    analyze_parser.add_argument("--authority-observation-file", type=Path)
    authority_parser = subcommands.add_parser("observe-authority")
    authority_parser.add_argument("--json", action="store_true")
    analyze_parser.add_argument("--json", action="store_true")
    check_parser = subcommands.add_parser("check-contract")
    check_parser.add_argument("--json", action="store_true")
    failure_parser = subcommands.add_parser("observation-failure")
    failure_parser.add_argument("--expect-head", required=True)
    failure_parser.add_argument("--observed-head", required=True)
    failure_parser.add_argument("--observed-tree", required=True)
    failure_parser.add_argument("--repository", required=True)
    failure_parser.add_argument("--now", required=True)
    failure_parser.add_argument("--run-id", required=True, type=int)
    failure_parser.add_argument("--run-attempt", required=True, type=int)
    failure_parser.add_argument("--failed-stage", required=True)
    failure_parser.add_argument("--exit-code", required=True, type=int)
    failure_parser.add_argument("--json", action="store_true")
    handoff_parser = subcommands.add_parser("repair-handoff")
    handoff_parser.add_argument("--analysis-file", type=Path, required=True)
    handoff_parser.add_argument("--run-id", type=int, required=True)
    handoff_parser.add_argument("--run-attempt", type=int, required=True)
    handoff_parser.add_argument("--event", required=True)
    handoff_parser.add_argument("--parent-workflow", default="")
    handoff_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "collect-runs":
            value = collect_runs(repository=arguments.repository,
                                 expected_head=arguments.expect_head,
                                 directory=arguments.pages_dir)
        elif arguments.command == "collect-work":
            value = collect_work(repository=arguments.repository,
                                 expected_head=arguments.expect_head,
                                 directory=arguments.pages_dir,
                                 now=_timestamp(arguments.now, "observation time"))
        elif arguments.command == "collect-jobs":
            value = collect_jobs(_read_json(arguments.runs_file, "workflow runs"),
                                 repository=arguments.repository,
                                 expected_head=arguments.expect_head,
                                 directory=arguments.jobs_dir)
        elif arguments.command == "job-readback-budget":
            runs = _read_json(arguments.runs_file, "workflow run page")
            if arguments.inventory_output:
                if not arguments.required_jobs_only:
                    raise ReflexiveWatchdogBlock("paginated inventory requires the explicit job selection policy")
                runs = merge_run_pages(runs)
                arguments.inventory_output.write_bytes(canonical_json_bytes(runs))
            value = job_readback_budget(
                runs,
                expected_head=arguments.expect_head,
                required_jobs_only=arguments.required_jobs_only,
            )
            if arguments.jobs_dir is not None:
                if not arguments.required_jobs_only:
                    raise ReflexiveWatchdogBlock("job completeness requires the explicit job selection policy")
                validate_job_plan(runs, load_jobs_directory(arguments.jobs_dir, strict=True),
                                  value, expected_head=arguments.expect_head)
        elif arguments.command == "repair-handoff":
            value = repair_handoff(arguments.analysis_file.read_bytes(),
                run_id=arguments.run_id, run_attempt=arguments.run_attempt,
                producer_event=arguments.event, parent_workflow=arguments.parent_workflow)
        elif arguments.command == "observe-authority":
            value = observe_authority()
        elif arguments.command == "check-contract":
            contract = load_contract()
            prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
            value = {
                "schema": "qikvrt_reflexive_watchdog_contract_check_v1",
                "state": "CONTRACT_BOUND",
                "contract_id": contract["contract_id"],
                "workflow_path": prevention["workflow_path"],
                "controller_path": prevention["controller_path"],
            }
        elif arguments.command == "observation-failure":
            value = observation_failure_receipt(
                expected_head=arguments.expect_head,
                observed_head=arguments.observed_head,
                observed_tree=arguments.observed_tree,
                repository=arguments.repository,
                now=_timestamp(arguments.now, "observation time"),
                run_id=arguments.run_id,
                run_attempt=arguments.run_attempt,
                stage=arguments.failed_stage,
                exit_code=arguments.exit_code,
            )
        else:
            runs = _read_json(arguments.runs_file, "workflow runs")
            job_plan = (_mapping(_read_json(arguments.job_plan_file, "job readback plan"),
                                 "job readback plan") if arguments.job_plan_file else None)
            jobs = {"jobs_by_run": load_jobs_directory(arguments.jobs_dir, strict=job_plan is not None)}
            baseline = _read_json(arguments.baseline, "baseline") if arguments.baseline else None
            if baseline is not None and not isinstance(baseline, Mapping):
                raise ReflexiveWatchdogBlock("baseline must be an object")
            authority_head = None
            if arguments.authority_head_file is not None:
                try:
                    authority_head = arguments.authority_head_file.read_text(encoding="utf-8").strip()
                except (OSError, UnicodeError) as exc:
                    raise ReflexiveWatchdogBlock(f"cannot load authority head observation: {exc}") from exc
                authority_head = _head_sha(authority_head, "authority head observation")
            value = analyze(
                runs,
                jobs,
                expected_head=arguments.expect_head,
                expected_tree=arguments.expect_tree,
                repository=arguments.repository,
                now=_timestamp(arguments.now, "observation time"),
                baseline=baseline,
                observation_scope=arguments.observation_scope,
                node_liveness_dir=arguments.node_liveness_dir,
                authority_head=authority_head,
                authority_observation=(_read_json(arguments.authority_observation_file, "authority observation")
                    if arguments.authority_observation_file else None),
                job_plan=job_plan,
                work_value=(_read_json(arguments.work_file, "open work inventory")
                            if arguments.work_file else None),
            )
        if arguments.json:
            print(canonical_json_bytes(value).decode("utf-8"), end="")
        else:
            state = value.get("state", "HOLD" if value.get("truncated") else "READY")
            print(f"{state} first_blocker={value.get('first_blocker')}")
        return 2 if ((arguments.command == "collect-work" and not value["complete"])
                     or (arguments.command in {"job-readback-budget", "collect-jobs"}
                         and value["state"] == "HOLD")) else 0
    except ReflexiveWatchdogBlock as exc:
        print(f"BLOCK REFLEXIVE_REPOSITORY_WATCHDOG {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
