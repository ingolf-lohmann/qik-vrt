#!/usr/bin/env python3
"""Validate and print the repository's machine-readable AI handoff context.

Standard-library only. Read-only: this script does not modify repository or Git
state and performs no network access.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools.qikvrt_integrity import (
    PORTABLE_GIT_SOURCE_VERIFICATION_MODE,
    cross_check_portable_git_source_capsule,
    load_portable_git_source_capsule,
    portable_git_source_evidence,
)

CONTEXT_PATH = ROOT / "AI_CONTEXT.json"
SUPPORTED_CONTEXT_SCHEMAS = frozenset(
    {
        "qikvrt-ai-context/1.0",
        "qikvrt-ai-context/1.2",
        "qikvrt-ai-context/1.3",
    }
)


def fail(message: str) -> NoReturn:
    print(f"AI_HANDOFF_BLOCK: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"top-level value in {path} must be an object")
    return value


def require(obj: dict[str, Any], key: str, expected: type) -> Any:
    value = obj.get(key)
    if not isinstance(value, expected):
        fail(f"field {key!r} must be {expected.__name__}")
    return value


def git_value(*args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return proc.stdout.strip() or "unavailable"


def client_causal_key(value: dict[str, Any]) -> str:
    """Exclude observation clocks and unrelated repository lifecycle changes."""
    parts = {key: value.get(key) for key in ("subject", "error", "cause", "capability")}
    if any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)
           for v in parts.values()):
        fail("CLIENT_CAUSAL_EVIDENCE_INCOMPLETE")
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def validate_client_action(action: dict[str, Any], subject: dict[str, Any]) -> bool:
    if not isinstance(action, dict) or action.get("subject") != subject:
        fail("CLIENT_ACTION_SUBJECT_DRIFT")
    if action.get("route") not in ("connector", "cli", "mesh"):
        fail("CLIENT_ACTION_ROUTE_INVALID")
    if action.get("method") not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        fail("CLIENT_ACTION_METHOD_INVALID")
    service = str(action.get("service", "")).casefold()
    if service in ("github", "ionos"):
        policy = load_json(ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
        required_route = policy.get("client_continuation", {}).get(service + "_route")
        if required_route != "REST_API_ONLY":
            fail("CLIENT_" + service.upper() + "_ROUTE_POLICY_INVALID")
        if action.get("transport") != required_route:
            fail("CLIENT_" + service.upper() + "_ROUTE_FORBIDDEN")
    for key in ("operation", "evidence"):
        if not isinstance(action.get(key), str) or not action[key].strip():
            fail("CLIENT_ACTION_" + key.upper() + "_MISSING")
    predicates = ("authorized", "safe", "deterministic", "callable",
                  "authenticated", "permitted", "admitted")
    if any(type(action.get(key)) is not bool for key in predicates):
        fail("CLIENT_ACTION_PREDICATE_INVALID")
    if action["callable"] and (
        action.get("observed_method") != action["method"]
        or action.get("observed_operation") != action["operation"]
        or action.get("observed_repository") != subject["repository"]
    ):
        fail("CLIENT_CALLABLE_OPERATION_BINDING_MISMATCH")
    retry_changed = True
    if "retry" in action:
        retry = require(action, "retry", dict)
        retry_changed = (client_causal_key(require(retry, "current", dict))
                         != client_causal_key(require(retry, "previous", dict)))
    return all(action[key] for key in predicates) and retry_changed


def client_transition_plan(receipt: dict[str, Any]) -> dict[str, Any] | None:
    """Expose admitted preparation before a future effect becomes executable.

    This is a read-only plan, not an executor or an effect receipt. Historical
    receipts remain readable. A supplied plan must match the current subject
    and input identity; human corrections require re-evaluation before reuse.
    """
    if "transition_plan" not in receipt:
        return None
    plan = receipt["transition_plan"]
    if not isinstance(plan, dict):
        fail("CLIENT_TRANSITION_PLAN_INVALID")
    subject = require(receipt, "subject", dict)
    if plan.get("subject") != subject:
        fail("CLIENT_TRANSITION_SUBJECT_DRIFT")
    input_digest = receipt.get("input_sha256")
    if (not isinstance(input_digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", input_digest)
        or plan.get("input_sha256") != input_digest):
        fail("CLIENT_TRANSITION_INPUT_DRIFT")
    transitions = plan.get("transitions")
    if not isinstance(transitions, list):
        fail("CLIENT_TRANSITION_LIST_INVALID")
    ready: list[dict[str, Any]] = []
    waiting: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for transition in transitions:
        if not isinstance(transition, dict):
            fail("CLIENT_TRANSITION_INVALID")
        identifier = transition.get("id")
        if (not isinstance(identifier, str) or not identifier.strip()
            or identifier in identifiers):
            fail("CLIENT_TRANSITION_ID_INVALID")
        identifiers.add(identifier)
        evidence = transition.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            fail("CLIENT_TRANSITION_EVIDENCE_MISSING")
        activation = transition.get("activation")
        if not isinstance(activation, list) or not activation:
            fail("CLIENT_TRANSITION_ACTIVATION_INVALID")
        conditions: set[str] = set()
        missing: list[str] = []
        for condition in activation:
            if not isinstance(condition, dict):
                fail("CLIENT_TRANSITION_ACTIVATION_INVALID")
            condition_id = condition.get("id")
            if (not isinstance(condition_id, str) or not condition_id.strip()
                or condition_id in conditions
                or type(condition.get("satisfied")) is not bool
                or not isinstance(condition.get("evidence"), str)
                or not condition["evidence"].strip()):
                fail("CLIENT_TRANSITION_ACTIVATION_INVALID")
            conditions.add(condition_id)
            if not condition["satisfied"]:
                missing.append(condition_id)
        preparation = transition.get("preparation")
        if not isinstance(preparation, list):
            fail("CLIENT_TRANSITION_PREPARATION_INVALID")
        for index, action in enumerate(preparation):
            if validate_client_action(action, subject):
                ready.append({"transition_id": identifier, "stage": "PREPARE",
                              "index": index, "action": action})
        action = require(transition, "action", dict)
        admitted = validate_client_action(action, subject)
        if not missing and admitted:
            ready.append({"transition_id": identifier, "stage": "EXECUTE", "action": action})
        else:
            waiting.append({"transition_id": identifier, "activation": missing,
                            "action_admitted": admitted, "evidence": evidence})
    return {"input_sha256": input_digest, "ready": ready, "waiting": waiting,
            "scope": "PLANNING_ONLY_NOT_EXECUTION_OR_EFFECT_PROOF"}


def client_end_of_action_domain() -> str:
    """Reuse the exact Owner contract, not a second client governance policy."""
    policy = load_json(ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
    binding = policy.get("client_continuation", {}).get("end_of_action_rule", {})
    path = binding.get("path")
    if (not isinstance(path, str) or Path(path).is_absolute()
        or ".." in Path(path).parts):
        fail("CLIENT_OWNER_CLOSING_RULE_BINDING_INVALID")
    try:
        raw = (ROOT / path).read_bytes()
    except OSError:
        fail("CLIENT_OWNER_CLOSING_RULE_UNAVAILABLE")
    if hashlib.sha256(raw).hexdigest() != binding.get("sha256"):
        fail("CLIENT_OWNER_CLOSING_RULE_DIGEST_DRIFT")
    rule = load_json(ROOT / path)
    if (rule.get("delegation_id") != "OWNER-END-OF-ACTION-VERIFICATION-GRUNDREGEL-V1"
        or rule.get("state") != "ACTIVE"):
        fail("CLIENT_OWNER_CLOSING_RULE_INACTIVE")
    for duty in require(rule, "duties_at_end_of_every_action", list):
        if isinstance(duty, dict) and duty.get("id") == "REOBSERVE_RAUMZEITTERMINAL_DELIVERY_EVIDENCE":
            return require(duty, "domain", str)
    fail("CLIENT_OWNER_CLOSING_RULE_DOMAIN_MISSING")


def client_time(value: Any, code: str) -> dt.datetime:
    if not isinstance(value, str):
        fail(code)
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail(code)
    if result.utcoffset() is None:
        fail(code)
    return result


def client_public_url(value: Any, hostname: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and parsed.hostname == hostname
                and parsed.port in (None, 443) and parsed.username is None
                and parsed.password is None)
    except ValueError:
        return False


def validate_client_readback(readback: Any, subject: dict[str, Any], window: Any) -> None:
    """Check action-bound chronology; supplied receipts still need live verification."""
    if (not isinstance(window, dict) or not isinstance(window.get("id"), str)
        or not window["id"].strip()):
        fail("CLIENT_ACTION_WINDOW_INVALID")
    completed = client_time(window.get("completed_at"), "CLIENT_ACTION_WINDOW_INVALID")
    closed = client_time(window.get("closed_at"), "CLIENT_ACTION_WINDOW_INVALID")
    if closed <= completed:
        fail("CLIENT_ACTION_WINDOW_INVALID")
    if not isinstance(readback, dict):
        fail("CLIENT_CLOSING_READBACK_MISSING")
    repository = require(readback, "repository", dict)
    source = repository.get("source")
    if (repository.get("repository") != subject["repository"]
        or not isinstance(source, str) or not source.strip()):
        fail("CLIENT_REPOSITORY_READBACK_MISSING")
    for key in ("head", "tree"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(repository.get(key, ""))):
            fail("CLIENT_REPOSITORY_READBACK_INVALID")
    if any(repository.get(key) != subject[key] for key in ("ref", "head", "tree")):
        fail("CLIENT_REPOSITORY_READBACK_SUBJECT_DRIFT")
    delivery = require(readback, "delivery", dict)
    hostname = client_end_of_action_domain()
    source = delivery.get("source")
    if (delivery.get("hostname") != hostname
        or not isinstance(source, str) or not source.strip()):
        fail("CLIENT_EXACT_HOST_READBACK_MISSING")
    if delivery.get("state") not in ("UNKNOWN", "PENDING", "VERIFIED"):
        fail("CLIENT_DELIVERY_READBACK_INVALID")
    if delivery.get("method") != "GET" or not client_public_url(delivery.get("url"), hostname):
        fail("CLIENT_PUBLIC_DELIVERY_URL_INVALID")
    for kind in ("repository", "delivery"):
        observation = readback[kind]
        if observation.get("action_id") != window["id"]:
            fail("CLIENT_READBACK_ACTION_DRIFT:" + kind)
        observed = client_time(observation.get("observed_at"), "CLIENT_READBACK_TIME_INVALID:" + kind)
        if not completed < observed <= closed:
            fail("CLIENT_READBACK_NOT_FRESH:" + kind)
    if delivery["state"] == "VERIFIED":
        if (type(delivery.get("http_status")) is not int or delivery["http_status"] != 200
            or not isinstance(delivery.get("response_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", delivery["response_sha256"])
            or not client_public_url(delivery.get("final_url"), hostname)):
            fail("CLIENT_PUBLIC_DELIVERY_PROOF_INCOMPLETE")


def client_previous_receipt(receipt: dict[str, Any]) -> dict[str, Any] | None:
    """Read an explicitly pinned predecessor, without discovering other files."""
    previous = receipt.get("previous_run")
    if not isinstance(previous, dict):
        return None
    if not {"receipt_path", "receipt_sha256"} & previous.keys():
        return None
    relative, digest = previous.get("receipt_path"), previous.get("receipt_sha256")
    if (not isinstance(relative, str) or not relative.strip() or "\x00" in relative
        or Path(relative).is_absolute() or ".." in Path(relative).parts
        or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        fail("CLIENT_PREVIOUS_RECEIPT_BINDING_INVALID")
    path = ROOT / relative
    try:
        if path.resolve(strict=True) != path.absolute() or not path.is_file():
            fail("CLIENT_PREVIOUS_RECEIPT_BINDING_INVALID")
        with path.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
    except (OSError, ValueError, RuntimeError):
        fail("CLIENT_PREVIOUS_RECEIPT_UNAVAILABLE")
    if len(raw) > 2 * 1024 * 1024:
        fail("CLIENT_PREVIOUS_RECEIPT_TOO_LARGE")
    if hashlib.sha256(raw).hexdigest() != digest:
        fail("CLIENT_PREVIOUS_RECEIPT_DIGEST_DRIFT")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        fail("CLIENT_PREVIOUS_RECEIPT_INVALID")
    if (not isinstance(value, dict) or not previous.get("execution_id")
        or value.get("execution_id") != previous["execution_id"]):
        fail("CLIENT_PREVIOUS_RECEIPT_IDENTITY_DRIFT")
    return value


def client_knowledge_records(value: Any) -> dict[str, dict[str, Any]]:
    """Verify declared record identity and scope; hashes do not prove truth."""
    if not isinstance(value, list):
        fail("CLIENT_KNOWLEDGE_INVALID")
    records: dict[str, dict[str, Any]] = {}
    for record in value:
        if not isinstance(record, dict):
            fail("CLIENT_KNOWLEDGE_INVALID")
        for key in ("id", "epistemic_class", "scope", "statement"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                fail("CLIENT_KNOWLEDGE_INVALID")
        identifier = record["id"]
        if identifier in records or not isinstance(record.get("subject"), dict) or not record["subject"]:
            fail("CLIENT_KNOWLEDGE_ID_OR_SUBJECT_INVALID")
        evidence, supersedes = record.get("evidence"), record.get("supersedes", [])
        if (not isinstance(evidence, list) or not evidence
            or any(not isinstance(x, str) or not x.strip() for x in evidence)
            or not isinstance(supersedes, list)
            or any(not isinstance(x, str) or not x.strip() for x in supersedes)
            or len(set(supersedes)) != len(supersedes)):
            fail("CLIENT_KNOWLEDGE_EVIDENCE_OR_CORRECTION_INVALID")
        payload = {key: item for key, item in record.items() if key != "record_sha256"}
        try:
            wire = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (ValueError, TypeError, UnicodeError):
            fail("CLIENT_KNOWLEDGE_INVALID")
        if hashlib.sha256(wire).hexdigest() != record.get("record_sha256"):
            fail("CLIENT_KNOWLEDGE_DIGEST_DRIFT")
        records[identifier] = record
    visited: set[str] = set()
    visiting: set[str] = set()

    for identifier in records:
        stack = [(identifier, False)]
        while stack:
            current, leaving = stack.pop()
            if leaving:
                visiting.remove(current)
                visited.add(current)
                continue
            if current not in records:
                fail("CLIENT_KNOWLEDGE_CORRECTION_TARGET_MISSING")
            if current in visiting:
                fail("CLIENT_KNOWLEDGE_CORRECTION_CYCLE")
            if current in visited:
                continue
            visiting.add(current)
            stack.append((current, True))
            stack.extend((parent, False) for parent in records[current].get("supersedes", []))
    return records


def client_historical_knowledge_encodings(
    receipt: dict[str, Any], predecessor: dict[str, Any] | None,
) -> dict[str, tuple[dict[str, Any], str]]:
    """Admit only declared historical bytes from the already pinned predecessor.

    New records still require the canonical compact digest. This is an explicit
    versioned reader contract, never a try-both-encodings fallback or a rewrite
    of the stored predecessor. Its return value is a validation projection only.
    """
    migration = receipt.get("knowledge_encoding_migration")
    if migration is None:
        return {}
    policy = load_json(ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
    contract = policy.get("client_continuation", {}).get(
        "knowledge_continuity", {}).get("historical_encoding_migration", {})
    schema = "qikvrt-knowledge-historical-encoding-migration/v1"
    codec = "json-sorted-spaced-utf8/v1"
    if (not isinstance(contract, dict)
        or contract.get("schema") != schema or contract.get("codec") != codec
        or contract.get("scope") != "EXACT_PINNED_PREDECESSOR_RECORDS_ONLY"
        or contract.get("requires_pinned_predecessor") is not True
        or contract.get("new_records_remain_canonical") is not True):
        fail("CLIENT_KNOWLEDGE_MIGRATION_POLICY_UNAVAILABLE")
    if predecessor is None:
        fail("CLIENT_KNOWLEDGE_MIGRATION_PREDECESSOR_REQUIRED")
    previous = require(receipt, "previous_run", dict)
    if (not isinstance(migration, dict)
        or set(migration) != {"schema", "predecessor_sha256", "records"}
        or migration.get("schema") != schema
        or migration.get("predecessor_sha256") != previous.get("receipt_sha256")):
        fail("CLIENT_KNOWLEDGE_MIGRATION_BINDING_INVALID")
    entries = migration["records"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 128:
        fail("CLIENT_KNOWLEDGE_MIGRATION_RECORDS_INVALID")
    inherited = require(predecessor, "knowledge", list)
    current = require(receipt, "knowledge", list)
    accepted: dict[str, tuple[dict[str, Any], str]] = {}
    for entry in entries:
        if (not isinstance(entry, dict)
            or set(entry) != {"id", "codec", "record_sha256", "canonical_sha256"}
            or not isinstance(entry.get("id"), str) or not entry["id"].strip()
            or entry["id"] in accepted or entry.get("codec") != codec):
            fail("CLIENT_KNOWLEDGE_MIGRATION_RECORDS_INVALID")
        identifier = entry["id"]
        originals = [record for record in inherited
                     if isinstance(record, dict) and record.get("id") == identifier]
        successors = [record for record in current
                      if isinstance(record, dict) and record.get("id") == identifier]
        if len(originals) != 1 or len(successors) != 1:
            fail("CLIENT_KNOWLEDGE_MIGRATION_RECORD_NOT_IN_PREDECESSOR")
        original = originals[0]
        if successors[0] != original:
            fail("CLIENT_KNOWLEDGE_HISTORY_REWRITTEN")
        payload = {key: value for key, value in original.items() if key != "record_sha256"}
        try:
            historical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                    separators=(", ", ": "), allow_nan=False).encode("utf-8")
            canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (ValueError, TypeError, UnicodeError):
            fail("CLIENT_KNOWLEDGE_INVALID")
        old_digest = hashlib.sha256(historical).hexdigest()
        canonical_digest = hashlib.sha256(canonical).hexdigest()
        if (old_digest == canonical_digest or original.get("record_sha256") != old_digest
            or entry["record_sha256"] != old_digest
            or entry["canonical_sha256"] != canonical_digest):
            fail("CLIENT_KNOWLEDGE_MIGRATION_ENCODING_MISMATCH")
        accepted[identifier] = (original, canonical_digest)
    return accepted


def client_knowledge_validation_projection(
    records: Any, historical: dict[str, tuple[dict[str, Any], str]],
) -> Any:
    """Preserve source records; normalize only the explicitly verified reader view."""
    if not isinstance(records, list):
        return records  # The existing strict validator reports the schema error.
    projected = []
    for record in records:
        identifier = record.get("id") if isinstance(record, dict) else None
        binding = historical.get(identifier) if isinstance(identifier, str) else None
        if binding is None:
            projected.append(record)
            continue
        original, canonical_digest = binding
        if record != original:
            fail("CLIENT_KNOWLEDGE_HISTORY_REWRITTEN")
        projected.append(dict(record, record_sha256=canonical_digest))
    return projected


def validate_client_knowledge(receipt: dict[str, Any], predecessor: dict[str, Any] | None) -> None:
    """Preserve facts, unknowns and corrections without predecessor PASS transfer."""
    historical = client_historical_knowledge_encodings(receipt, predecessor)
    current = client_knowledge_records(client_knowledge_validation_projection(
        receipt.get("knowledge", []), historical))
    previous = receipt.get("previous_run")
    sources = [previous] if isinstance(previous, dict) else []
    if predecessor is not None:
        sources.append(predecessor)
    for source in sources:
        for identifier, record in client_knowledge_records(client_knowledge_validation_projection(
                source.get("knowledge", []), historical)).items():
            if identifier not in current:
                fail("CLIENT_PREDECESSOR_KNOWLEDGE_DROPPED")
            if current[identifier]["record_sha256"] != record["record_sha256"]:
                fail("CLIENT_KNOWLEDGE_HISTORY_REWRITTEN")


def validate_client_work(receipt: dict[str, Any], predecessor: dict[str, Any] | None = None) -> None:
    """An observed predecessor's open duties are work for its successor.

    Historical receipts without a predecessor remain readable. An explicitly
    supplied predecessor cannot be silently dropped; closing a carried duty
    requires evidence. This checks consistency, not evidence authenticity.
    """
    previous = receipt.get("previous_run")
    if previous is None and "work" not in receipt:
        return
    work = require(receipt, "work", list)
    tasks: dict[str, dict[str, Any]] = {}
    for task in work:
        if not isinstance(task, dict):
            fail("CLIENT_WORK_INVALID")
        identifier = task.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in tasks:
            fail("CLIENT_WORK_ID_INVALID")
        if task.get("state") not in ("OPEN", "VERIFIED"):
            fail("CLIENT_WORK_STATE_INVALID")
        if task["state"] == "VERIFIED":
            if not isinstance(task.get("evidence"), str) or not task["evidence"].strip():
                fail("CLIENT_WORK_CLOSED_WITHOUT_EVIDENCE")
        elif not isinstance(task.get("next_action"), str) or not task["next_action"].strip():
            fail("CLIENT_OPEN_WORK_WITHOUT_SUCCESSOR")
        tasks[identifier] = task
    if previous is not None:
        if not isinstance(previous, dict) or not isinstance(previous.get("execution_id"), str) or not previous["execution_id"].strip():
            fail("CLIENT_PREVIOUS_RUN_INVALID")
        inherited = require(previous, "open_work", list)
        if any(not isinstance(identifier, str) or not identifier.strip() for identifier in inherited):
            fail("CLIENT_PREVIOUS_RUN_INVALID")
        if len(set(inherited)) != len(inherited):
            fail("CLIENT_PREVIOUS_RUN_INVALID")
        if not set(inherited) <= set(tasks):
            fail("CLIENT_PREDECESSOR_OPEN_WORK_DROPPED")
    if predecessor is not None:
        prior_work = require(predecessor, "work", list)
        for task in prior_work:
            if not isinstance(task, dict) or task.get("state") not in ("OPEN", "VERIFIED"):
                fail("CLIENT_PREVIOUS_WORK_INVALID")
            if task["state"] == "OPEN" and task.get("id") not in tasks:
                fail("CLIENT_PREDECESSOR_OPEN_WORK_DROPPED")
    if receipt.get("state") == "DONE" and any(task["state"] == "OPEN" for task in work):
        fail("CLIENT_DONE_WITH_OPEN_WORK")


def session_rule_contract() -> dict[str, Any]:
    """Bind shared rules, independently of a client's credentials or transport.

    This is byte consistency, never authenticated peer adoption. The original
    Terminal/Transputer and Mirror outbox retain their acceptance authority.
    """
    protocol = load_json(ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
    policy = protocol.get("client_continuation", {}).get("session_harmonization")
    if not isinstance(policy, dict) or policy.get("schema") != "qikvrt-session-harmonization/1":
        fail("CLIENT_SHARED_RULE_POLICY_MISSING")
    registry = load_json(ROOT / "AI_ADAPTERS.json")
    bindings = {}
    paths = policy.get("rule_sources")
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        fail("CLIENT_SHARED_RULE_SOURCES_INVALID")
    for item in registry.get("adapters", []):
        path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(path, str) or path not in paths:
            fail("CLIENT_ADAPTER_NOT_BOUND_TO_SHARED_RULES")
    for path in paths:
        if (not isinstance(path, str) or Path(path).is_absolute()
                or ".." in Path(path).parts):
            fail("CLIENT_SHARED_RULE_PATH_INVALID")
        target = ROOT / path
        if not target.resolve().is_relative_to(ROOT.resolve()):
            fail("CLIENT_SHARED_RULE_PATH_INVALID")
        try:
            raw = target.read_bytes()
        except OSError:
            fail("CLIENT_SHARED_RULE_SOURCE_UNAVAILABLE:" + path)
        bindings[path] = hashlib.sha256(raw).hexdigest()
    value = {"schema": "qikvrt-session-rule-contract/1",
             "authority_repository": policy["authority_repository"],
             "rule_bindings": bindings}
    value["rules_sha256"] = hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode()).hexdigest()
    return value


def validate_session_harmonization(receipt: dict[str, Any], *, required: bool = False) -> None:
    if receipt.get("schema") == "qikvrt-client-continuation/1":
        if required or "session_contract" in receipt or "session" in receipt:
            fail("CLIENT_CURRENT_SESSION_REQUIRES_V2")
        return  # historical readability is not current session acceptance
    if receipt.get("session_contract") != session_rule_contract():
        fail("CLIENT_SHARED_RULE_CONTRACT_DRIFT")
    session = require(receipt, "session", dict)
    for key in ("id", "node_id", "evidence"):
        if not isinstance(session.get(key), str) or not session[key].strip():
            fail("CLIENT_SESSION_BINDING_MISSING:" + key)
    if session.get("repository") != receipt.get("subject", {}).get("repository"):
        fail("CLIENT_SESSION_REPOSITORY_MISMATCH")
    observations = require(session, "capability_observations", list)
    if not observations:
        fail("CLIENT_SESSION_CAPABILITY_INVENTORY_MISSING")
    seen = set()
    for item in observations:
        if not isinstance(item, dict):
            fail("CLIENT_CAPABILITY_OBSERVATION_INVALID")
        if (item.get("session_id") != session["id"]
                or item.get("node_id") != session["node_id"]
                or item.get("repository") != session["repository"]
                or item.get("scope") != "THIS_SESSION_ONLY"):
            fail("CLIENT_CAPABILITY_SCOPE_LEAK")
        for key in ("operation", "route", "evidence"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                fail("CLIENT_CAPABILITY_OBSERVATION_INVALID")
        if item.get("method") not in {"GET", "POST", "PUT", "PATCH", "DELETE", "IN_PROCESS"}:
            fail("CLIENT_CAPABILITY_METHOD_INVALID")
        if item.get("state") not in {"AVAILABLE", "UNAVAILABLE", "UNKNOWN"}:
            fail("CLIENT_CAPABILITY_STATE_INVALID")
        client_time(item.get("observed_at"), "CLIENT_CAPABILITY_TIME_INVALID")
        key = (item["route"], item["operation"], item["method"])
        if key in seen:
            fail("CLIENT_DUPLICATE_CAPABILITY_OBSERVATION")
        seen.add(key)
    # Client statements are not the original authenticated per-node return path.
    if session.get("all_nodes_adopted") is not False:
        fail("CLIENT_UNVERIFIED_GLOBAL_ADOPTION")


def validate_client_receipt(receipt: dict[str, Any], *, require_session_contract: bool = False) -> str:
    """Validate consistency; never authenticate a client or prove live effects."""
    if receipt.get("schema") not in {"qikvrt-client-continuation/1", "qikvrt-client-continuation/2"}:
        fail("CLIENT_RECEIPT_SCHEMA_INVALID")
    validate_session_harmonization(receipt, required=require_session_contract)
    subject = require(receipt, "subject", dict)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", str(subject.get("repository", ""))):
        fail("CLIENT_SUBJECT_INVALID")
    for key in ("head", "tree"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(subject.get(key, ""))):
            fail("CLIENT_SUBJECT_INVALID")
    if not isinstance(subject.get("ref"), str) or not subject["ref"].strip():
        fail("CLIENT_SUBJECT_INVALID")
    authorization = require(receipt, "authorization", dict)
    if (authorization.get("granted") is not True
        or not isinstance(authorization.get("source"), str)
        or not authorization["source"].strip()):
        fail("CLIENT_OWNER_AUTHORIZATION_MISSING")
    if receipt.get("requested_authorization_again") is not False:
        fail("CLIENT_REPEATED_AUTHORIZATION_REQUEST")
    inventory = require(receipt, "inventory", dict)
    for kind in ("repository", "connector", "cli", "mesh"):
        if not isinstance(inventory.get(kind), str) or not inventory[kind].strip():
            fail("CLIENT_EXISTING_ROUTE_NOT_INSPECTED:" + kind)
    attempts = require(receipt, "attempts", list)
    executed_keys: set[str] = set()
    closed_actions: set[str] = set()
    for attempt in attempts:
        if not isinstance(attempt, dict):
            fail("CLIENT_ATTEMPT_INVALID")
        count = attempt.get("effect_count")
        if isinstance(count, bool) or not isinstance(count, int) or count not in (0, 1):
            fail("CLIENT_EFFECT_COUNT_INVALID")
        if any(type(attempt.get(key)) is not bool
               for key in ("ambiguous_effect", "readback_before_effect")):
            fail("CLIENT_ATTEMPT_PREDICATE_INVALID")
        current = client_causal_key(require(attempt, "current", dict))
        previous = attempt.get("previous")
        if previous is not None:
            if not isinstance(previous, dict):
                fail("CLIENT_ATTEMPT_INVALID")
            if current == client_causal_key(previous) and count:
                fail("CLIENT_UNCHANGED_FAILURE_RETRIED")
        if attempt.get("ambiguous_effect") is not False:
            if attempt.get("readback_before_effect") is not True and count:
                fail("CLIENT_AMBIGUOUS_EFFECT_RETRIED_WITHOUT_READBACK")
        if count:
            if not validate_client_action(require(attempt, "action", dict), subject):
                fail("CLIENT_EFFECT_WITHOUT_ADMISSION")
            if current in executed_keys:
                fail("CLIENT_DUPLICATE_CAUSAL_ATTEMPT")
            executed_keys.add(current)
            validate_client_readback(attempt.get("readback"), subject, attempt.get("action_window"))
            action_id = attempt["action_window"]["id"]
            if action_id in closed_actions:
                fail("CLIENT_CLOSING_ACTION_REUSED")
            closed_actions.add(action_id)
    actions = require(receipt, "next_actions", list)
    executable = False
    for action in actions:
        executable |= validate_client_action(action, subject)
    transition_plan = client_transition_plan(receipt)
    if transition_plan is not None:
        executable |= bool(transition_plan["ready"])
    readback = receipt.get("readback")
    validate_client_readback(readback, subject, receipt.get("action_window"))
    repository = readback["repository"]
    delivery = readback["delivery"]
    state = receipt.get("state")
    if state not in ("CONTINUE", "BLOCK", "DONE", "OWNER_CHOICE"):
        fail("CLIENT_RETURN_STATE_INVALID")
    predecessor = client_previous_receipt(receipt)
    validate_client_work(receipt, predecessor)
    validate_client_knowledge(receipt, predecessor)
    if executable and state != "CONTINUE":
        fail("CLIENT_PREMATURE_RETURN_WITH_EXECUTABLE_SUCCESSOR")
    pending = receipt.get("pending_execution")
    if state == "CONTINUE" and not executable and (
        not isinstance(pending, str) or not pending.strip()
    ):
        fail("CLIENT_CONTINUATION_WITHOUT_SUCCESSOR_OR_EXECUTION")
    if state == "BLOCK":
        blocker = require(receipt, "blocker", dict)
        for key in ("operation", "reason", "evidence", "retry_condition", "next_action"):
            if not isinstance(blocker.get(key), str) or not blocker[key].strip():
                fail("CLIENT_BLOCKER_NOT_CONCRETE:" + key)
    if state == "OWNER_CHOICE":
        choices = require(receipt, "owner_choices", list)
        if len(choices) < 2 or any(not isinstance(c, str) or not c.strip() for c in choices) or len(set(choices)) != len(choices):
            fail("CLIENT_OWNER_CHOICE_INVALID")
    if state == "DONE":
        if transition_plan is not None and transition_plan["waiting"]:
            fail("CLIENT_DONE_WITH_PENDING_TRANSITION")
        if (repository.get("ref") != "main"
            or any(repository.get(key) != subject[key] for key in ("head", "tree"))
            or delivery.get("state") != "VERIFIED"
            or any(delivery.get(key) is not True for key in ("working_software", "tls", "independent"))
            or any(delivery.get(key) != subject[key] for key in ("head", "tree"))):
            fail("CLIENT_DONE_WITHOUT_EXACT_EFFECT_READBACK")
    return state

def validate_bound_file(
    receipt: dict[str, Any],
    path_key: str,
    sha_key: str,
    scope_id: str,
) -> None:
    path_value = receipt.get(path_key)
    sha_value = receipt.get(sha_key)
    if (
        not isinstance(path_value, str)
        or Path(path_value).is_absolute()
        or ".." in Path(path_value).parts
        or not isinstance(sha_value, str)
        or not re.fullmatch(r"[0-9a-f]{64}", sha_value)
    ):
        fail(f"AI progress DONE scope file binding is invalid: {scope_id}:{path_key}")
    try:
        actual = hashlib.sha256((ROOT / path_value).read_bytes()).hexdigest()
    except OSError as exc:
        fail(f"AI progress DONE scope bound file is unavailable: {scope_id}:{path_value}: {exc}")
    if actual != sha_value:
        fail(f"AI progress DONE scope bound file digest drift: {scope_id}:{path_value}")

def validate_progress(context: dict[str, Any]) -> str:
    protocol = require(context, "progress_protocol", dict)
    schema_path = ROOT / require(protocol, "machine_schema", str)
    progress_path = ROOT / require(protocol, "machine_state", str)
    schema = load_json(schema_path)
    progress = load_json(progress_path)
    durable = schema.get("$defs", {}).get("durableSnapshotV3")
    if not isinstance(durable, dict):
        fail("human-machine progress schema lacks durableSnapshotV3")
    required_fields = durable.get("required")
    if not isinstance(required_fields, list) or any(
        not isinstance(key, str) for key in required_fields
    ):
        fail("durable progress schema required-field contract is malformed")
    missing = [key for key in required_fields if key not in progress]
    if missing:
        fail("AI progress missing durable fields: " + ", ".join(sorted(missing)))
    if progress.get("schema") != "qikvrt-ai-progress/3.1":
        fail("AI progress must use qikvrt-ai-progress/3.1")
    source_sha = progress.get("source_sha")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        fail("AI progress source_sha is invalid")
    try:
        dt.datetime.fromisoformat(
            require(progress, "updated_at", str).replace("Z", "+00:00")
        )
    except ValueError as exc:
        fail(f"AI progress updated_at is invalid: {exc}")
    evidence = require(progress, "source_evidence", dict)
    if evidence.get("ref_name") != progress.get("ref_name"):
        fail("AI progress source evidence ref drift")
    if evidence.get("commit") != source_sha:
        fail("AI progress source evidence commit drift")
    blobs = require(evidence, "blobs", dict)
    if not blobs:
        fail("AI progress source evidence must bind at least one blob")
    for path, expected in blobs.items():
        if (
            not isinstance(path, str)
            or not path
            or Path(path).is_absolute()
            or ".." in Path(path).parts
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{40}", expected)
        ):
            fail(f"AI progress source blob binding is invalid: {path!r}")
    if evidence.get("verification_mode") != PORTABLE_GIT_SOURCE_VERIFICATION_MODE:
        fail("AI progress source evidence verification mode drift")
    capsule_binding = require(evidence, "capsule", dict)
    capsule_path = capsule_binding.get("path")
    if not isinstance(capsule_path, str):
        fail("AI progress source capsule path is invalid")
    try:
        capsule = load_portable_git_source_capsule(
            ROOT,
            capsule_path,
            expected_binding=capsule_binding,
        )
        cross_check_portable_git_source_capsule(ROOT, capsule)
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        fail(f"AI progress portable source capsule is invalid: {exc}")
    if evidence != portable_git_source_evidence(capsule):
        fail("AI progress source evidence does not match its portable Git closure")
    canonical_repositories = (
        context.get("project", {})
        .get("canonicality", {})
        .get("repositories", [])
    )
    if (
        not canonical_repositories
        or evidence.get("source_repository") != canonical_repositories[0]
    ):
        fail("AI progress portable source repository is not the Authority")
    scopes = require(progress, "scopes", dict)
    if not scopes:
        fail("AI progress must contain at least one bounded scope")
    incomplete = 0
    for scope_id, scope in scopes.items():
        if not isinstance(scope_id, str) or not isinstance(scope, dict):
            fail("AI progress scope contract is malformed")
        claims = require(scope, "claims", dict)
        release = tuple(claims.get(key) for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"))
        effect_state = scope.get("effect_state")
        if effect_state == "EFFECT_ACK_DONE":
            if scope.get("state") != "FINAL_PASS" or release != (True, True, True):
                fail(f"AI progress DONE scope is not FINAL_PASS: {scope_id}")
            pass_evidence = require(scope, "pass_evidence", dict)
            repositories = pass_evidence.get("repository")
            if not isinstance(repositories, list) or not repositories:
                fail(f"AI progress DONE scope lacks repository evidence: {scope_id}")
            for repository in repositories:
                if (
                    not isinstance(repository, dict)
                    or not isinstance(repository.get("repository"), str)
                    or not isinstance(repository.get("ref_name"), str)
                    or not re.fullmatch(
                        r"[0-9a-f]{40}", str(repository.get("source_sha", ""))
                    )
                ):
                    fail(f"AI progress DONE scope repository/ref/SHA evidence is invalid: {scope_id}")
            checks = pass_evidence.get("checks")
            if not isinstance(checks, dict) or not checks:
                fail(f"AI progress DONE scope lacks check evidence: {scope_id}")
            receipt = require(pass_evidence, "evidence", dict)
            validate_bound_file(receipt, "path", "sha256", scope_id)
            for path_key, sha_key in (
                ("finalization_input_path", "finalization_input_sha256"),
                ("exact_head_run_evidence_path", "exact_head_run_evidence_sha256"),
            ):
                if path_key in receipt or sha_key in receipt:
                    validate_bound_file(receipt, path_key, sha_key, scope_id)
            if scope_id == "qikvrt-global-claim-scope-v1":
                gate_matrix = checks.get("receipt_gate_matrix")
                exact_runs = checks.get("exact_head_runs")
                required_gates = {
                    "global_completion",
                    "manuscript_proof",
                    "mandatory_repository_gates",
                }
                if (
                    not isinstance(gate_matrix, dict)
                    or set(gate_matrix) != {"authority", "mirror"}
                    or any(
                        not isinstance(gate_matrix.get(side), dict)
                        or set(gate_matrix[side]) != required_gates
                        or any(
                            value != "success"
                            for value in gate_matrix[side].values()
                        )
                        for side in ("authority", "mirror")
                    )
                    or not isinstance(exact_runs, dict)
                    or set(exact_runs) != {"authority", "mirror"}
                ):
                    fail("AI progress global DONE gate matrix is invalid")
                run_ids: dict[str, int] = {}
                for side in ("authority", "mirror"):
                    run = exact_runs[side]
                    if (
                        not isinstance(run, dict)
                        or isinstance(run.get("run_id"), bool)
                        or not isinstance(run.get("run_id"), int)
                        or run["run_id"] <= 0
                        or isinstance(run.get("job_id"), bool)
                        or not isinstance(run.get("job_id"), int)
                        or run["job_id"] <= 0
                        or not isinstance(run.get("gate_steps"), dict)
                        or set(run["gate_steps"]) != required_gates
                        or any(
                            not isinstance(step, dict)
                            or step.get("conclusion") != "success"
                            for step in run["gate_steps"].values()
                        )
                    ):
                        fail(f"AI progress global DONE exact-head run is invalid: {side}")
                    run_ids[side] = run["run_id"]
                repository_by_name = {
                    item["repository"]: item
                    for item in repositories
                    if isinstance(item, dict)
                    and isinstance(item.get("repository"), str)
                }
                for side, name in (
                    ("authority", "Goldkelch/qik-vrt"),
                    ("mirror", "ingolf-lohmann/qik-vrt"),
                ):
                    item = repository_by_name.get(name)
                    if (
                        not isinstance(item, dict)
                        or item.get("ref_name")
                        != f"actions/runs/{run_ids[side]}"
                    ):
                        fail(
                            "AI progress global DONE run/ref binding is invalid: "
                            + side
                        )
        elif effect_state in {"EFFECT_ACK_CONTINUE", "EFFECT_ACK_BLOCK"}:
            incomplete += 1
            if release != (False, False, False):
                fail(f"AI progress incomplete scope inflates release: {scope_id}")
        else:
            fail(f"AI progress scope effect state is invalid: {scope_id}")
    if progress.get("incomplete_scope_count") != incomplete:
        fail("AI progress incomplete_scope_count is invalid")
    top_claims = require(progress, "claims", dict)
    if incomplete:
        if progress.get("effect_state") != "EFFECT_ACK_CONTINUE":
            fail("AI progress incomplete scopes require top-level CONTINUE")
        if tuple(top_claims.get(key) for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE")) != (False, False, False):
            fail("AI progress top-level release claims are inflated")
    elif (
        progress.get("state") != "PASS"
        or progress.get("effect_state") != "EFFECT_ACK_DONE"
        or tuple(
            top_claims.get(key)
            for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE")
        )
        != (True, True, True)
    ):
        fail("AI progress complete scopes require top-level PASS/DONE")
    effects = require(progress, "repository_effects", dict)
    if any(
        value != "NOT_EVALUATED"
        for key, value in effects.items()
        if key != "scope"
    ):
        fail("AI progress transient repository effects must remain unevaluated")
    owner = require(progress, "projection_owner", dict)
    owner_tool = owner.get("tool")
    owner_check = owner.get("check_command")
    if (
        not isinstance(owner_tool, str)
        or not owner_tool.startswith("tools/")
        or Path(owner_tool).is_absolute()
        or ".." in Path(owner_tool).parts
        or not (ROOT / owner_tool).is_file()
        or not isinstance(owner_check, str)
    ):
        fail("AI progress projection owner is invalid")
    try:
        command = shlex.split(owner_check)
    except ValueError as exc:
        fail(f"AI progress projection check is invalid: {exc}")
    if (
        len(command) != 4
        or command[0] != "python3"
        or command[1] != "-B"
        or command[2] != owner_tool
        or not command[3].startswith("--check")
    ):
        fail("AI progress projection check is outside the fail-closed command contract")
    try:
        checked = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"AI progress projection check failed to execute: {exc}")
    if checked.returncode != 0:
        detail = checked.stderr.strip() or checked.stdout.strip() or "no diagnostic"
        fail(f"AI progress projection is stale: {detail}")
    return owner_check


def validate_adapters(context: dict[str, Any]) -> tuple[str, int]:
    registry_name = require(context, "adapter_registry", str)
    registry = load_json(ROOT / registry_name)
    if require(registry, "schema", str) != "qikvrt-ai-adapters/1.0":
        fail("unsupported AI adapter registry schema")
    if require(registry, "canonical_entrypoint", str) != "AI":
        fail("AI adapter registry must bind canonical entrypoint AI")
    adapters = require(registry, "adapters", list)
    if not adapters:
        fail("AI adapter registry must contain at least one adapter")
    missing: list[str] = []
    for adapter in adapters:
        if not isinstance(adapter, dict):
            fail("every AI adapter entry must be an object")
        path = require(adapter, "path", str)
        if not (ROOT / path).is_file():
            missing.append(path)
    if missing:
        fail("missing AI adapter files: " + ", ".join(sorted(missing)))
    return registry_name, len(adapters)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-receipt", type=Path,
                        help="Validate a non-secret client continuation receipt; no live-effect proof")
    parser.add_argument("--session-contract", action="store_true",
                        help="Print the shared rule byte bindings; no peer adoption claim")
    parser.add_argument("--require-session-contract", action="store_true",
                        help="Reject legacy receipts at a current session boundary")
    parser.add_argument("--historical-client-receipt", action="store_true",
                        help="Read a legacy receipt as history, never as current session admission")
    args = parser.parse_args()
    if args.session_contract:
        if args.client_receipt is not None or args.require_session_contract or args.historical_client_receipt:
            parser.error("--session-contract cannot validate a receipt")
        print(json.dumps(session_rule_contract(), sort_keys=True, indent=2))
        return 0
    if args.require_session_contract and args.client_receipt is None:
        parser.error("--require-session-contract requires --client-receipt")
    if args.historical_client_receipt and (args.client_receipt is None or args.require_session_contract):
        parser.error("historical receipt mode requires --client-receipt and excludes current admission")
    if args.client_receipt is not None:
        receipt = load_json(args.client_receipt)
        state = validate_client_receipt(receipt, require_session_contract=not args.historical_client_receipt)
        print("CLIENT_HANDOFF_CONSISTENCY=VALID")
        print("CLIENT_STATE=" + state)
        print("CLIENT_SESSION_RULES=" + ("BYTE_CONSISTENT_NOT_PEER_ADOPTION"
              if receipt["schema"].endswith("/2") else "LEGACY_NOT_ASSESSED"))
        plan = client_transition_plan(receipt)
        if plan is not None:
            print("CLIENT_TRANSITION_PLAN=" + json.dumps(plan, sort_keys=True, separators=(",", ":")))
        print("LIVE_EFFECT_VERIFICATION=NOT_PERFORMED")
        return 0
    context = load_json(CONTEXT_PATH)
    schema = require(context, "schema", str)
    if schema not in SUPPORTED_CONTEXT_SCHEMAS:
        fail(f"unsupported schema {schema!r}")

    project = require(context, "project", dict)
    name = require(project, "name", str)
    canonicality = require(project, "canonicality", dict)
    repositories = require(canonicality, "repositories", list)
    if not repositories or not all(isinstance(x, str) and x for x in repositories):
        fail("canonical repositories must be a non-empty string list")

    read_order = require(context, "required_read_order", list)
    if not read_order or not all(isinstance(x, str) and x for x in read_order):
        fail("required_read_order must be a non-empty string list")

    missing = [path for path in read_order if not (ROOT / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    registry_name, adapter_count = validate_adapters(context)
    session_rule_contract()
    projection_check = validate_progress(context)

    licensing = require(context, "licensing_policy", dict)
    architecture = require(licensing, "architecture", dict)
    implementation = require(licensing, "implementation", dict)

    print("AI_HANDOFF_STATUS=VALID")
    print(f"PROJECT={name}")
    print(f"CONTEXT_ID={context.get('context_id', 'unknown')}")
    print(f"GIT_REF={git_value('rev-parse', '--abbrev-ref', 'HEAD')}")
    print(f"GIT_COMMIT={git_value('rev-parse', 'HEAD')}")
    print("CANONICAL_MODE=" + str(canonicality.get("mode", "unknown")))
    print("CANONICAL_REPOSITORIES=" + ",".join(repositories))
    print("READ_ORDER=" + " -> ".join(read_order))
    print(f"AI_ADAPTER_REGISTRY={registry_name}")
    print(f"AI_ADAPTER_COUNT={adapter_count}")
    print(f"AI_PROGRESS_CHECK={projection_check}")
    print("ARCHITECTURE_POLICY=" + str(architecture.get("intent", "unknown")))
    print("IMPLEMENTATION_POLICY=" + str(implementation.get("intent", "unknown")))
    print("NEXT_ACTION=Read required files, inspect task-relevant verified state, then continue without relying on chat memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
