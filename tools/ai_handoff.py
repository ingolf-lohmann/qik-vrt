#!/usr/bin/env python3
"""Validate and print the repository's machine-readable AI handoff context.

Standard-library only. Read-only: this script does not modify repository or Git
state and performs no network access.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
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


def validate_client_tool_selection(action: dict[str, Any]) -> str:
    """Check current Owner decisions before capability or transport selection.

    This checks declared routing metadata, not the truth of a client's claims.
    It performs no service discovery, authentication or external operation.
    """
    path = ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json"
    policy = load_json(path)
    continuation = policy.get("client_continuation")
    if not isinstance(continuation, dict):
        fail("CLIENT_TOOL_SELECTION_POLICY_INVALID")
    selection = continuation.get("tool_selection")
    if (not isinstance(selection, dict)
            or selection.get("schema") != "qikvrt-client-tool-selection/v1"
            or selection.get("before_external_tool_call") is not True
            or not isinstance(selection.get("disconnected_providers"), dict)):
        fail("CLIENT_TOOL_SELECTION_POLICY_INVALID")
    pin = hashlib.sha256(path.read_bytes()).hexdigest()
    if "route_policy_sha256" in action and action["route_policy_sha256"] != pin:
        fail("CLIENT_TOOL_SELECTION_POLICY_CHANGED")
    for provider, rule in selection["disconnected_providers"].items():
        if (not isinstance(provider, str) or not re.fullmatch(r"[a-z0-9_-]+", provider)
                or not isinstance(rule, dict) or rule.get("state") != "DISCONNECTED"
                or any(not isinstance(rule.get(key), list) or not rule[key]
                       or any(not isinstance(value, str) or not value for value in rule[key])
                       for key in ("service_aliases", "tool_prefixes", "endpoint_domains"))):
            fail("CLIENT_TOOL_SELECTION_POLICY_INVALID")
        services = {str(action.get(key, "")).strip().casefold()
                    for key in ("service", "provider")}
        tool = str(action.get("tool", "")).strip().casefold()
        matches = bool(services.intersection(value.casefold() for value in rule["service_aliases"]))
        matches |= any(tool.startswith(value.casefold()) for value in rule["tool_prefixes"])
        for key in ("url", "endpoint", "base_url", "target"):
            value = action.get(key)
            if not isinstance(value, str) or not value:
                continue
            try:
                address = value if "://" in value else "//" + value
                hostname = (urlsplit(address).hostname or "").casefold().rstrip(".")
            except ValueError:
                fail("CLIENT_ACTION_ENDPOINT_INVALID")
            matches |= any(hostname == domain.casefold()
                           or hostname.endswith("." + domain.casefold())
                           for domain in rule["endpoint_domains"])
        if matches:
            # GET/read-only, current tool availability and generic authorization
            # cannot supersede the Owner's disconnected-provider decision.
            fail("CLIENT_DISCONNECTED_PROVIDER_ROUTE_FORBIDDEN:" + provider)
    return pin


def github_graphql_fallback_allowed(action: dict[str, Any], policy: dict[str, Any]) -> bool:
    """Check the later Owner decision without relabeling GraphQL as REST.

    This checks declared routing metadata, not credential scope or live effect.
    An ambiguous REST effect cannot be retried through the fallback.
    """
    fallback = policy.get("client_continuation", {}).get("github_fallback", {})
    try:
        source = "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json"
        if fallback.get("source") != source:
            return False
        owner = json.loads((ROOT / source).read_bytes())
        decision = owner["graphql_fallback_decision"]
        encoded = json.dumps(decision, sort_keys=True, separators=(",", ":")).encode()
        pin = hashlib.sha256(encoded).hexdigest()
        instruction = decision["source_instruction"]
        return (decision.get("state") == "ACTIVE"
            and decision.get("repository") == action.get("subject", {}).get("repository")
            and instruction["sha256"] == hashlib.sha256(instruction["text"].encode()).hexdigest()
            and pin == fallback.get("decision_sha256") == action.get("owner_decision_sha256")
            and decision.get("fallback_must_be_retained") is True
            and action.get("operation") in fallback.get("allowed_operations", [])
            and action.get("operation") in decision.get("allowed_operations", [])
            and action.get("method") == "POST"
            and action.get("endpoint") == "https://api.github.com/graphql"
            and action.get("fallback_reason") == "REST_OPERATION_UNAVAILABLE"
            and action.get("rest_effect_state") == "NOT_ATTEMPTED")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def validate_client_action(action: dict[str, Any], subject: dict[str, Any]) -> bool:
    if not isinstance(action, dict) or action.get("subject") != subject:
        fail("CLIENT_ACTION_SUBJECT_DRIFT")
    validate_client_tool_selection(action)
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
        fallback = (service == "github" and action.get("transport") == "GRAPHQL_FALLBACK"
                    and github_graphql_fallback_allowed(action, policy))
        if action.get("transport") != required_route and not fallback:
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
    result = {"input_sha256": input_digest, "ready": ready, "waiting": waiting,
              "scope": "PLANNING_ONLY_NOT_EXECUTION_OR_EFFECT_PROOF"}
    if "blocking_repairs" in plan:
        repairs = plan["blocking_repairs"]
        if (not isinstance(repairs, list)
            or any(not isinstance(x, str) or not x.strip() for x in repairs)
            or len(set(repairs)) != len(repairs)):
            fail("CLIENT_BLOCKING_REPAIR_LIST_INVALID")
        if not set(repairs) <= identifiers:
            fail("CLIENT_BLOCKING_REPAIR_TRANSITION_MISSING")
        result["blocking_repairs"] = repairs
        result["deferred"] = []
        if repairs:
            # An unavailable repair remains the priority. Do not silently
            # substitute optimization or unrelated work, and retain its plan.
            result["deferred"] = [item for item in ready
                                  if item["transition_id"] not in repairs]
            result["ready"] = [item for item in ready
                               if item["transition_id"] in repairs]
    return result


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


def validate_client_remote_readback(
    remote: dict[str, Any], sent: dict[str, Any], receipt: dict[str, Any],
) -> None:
    """Reject local/failed/replayed observations; declarations still need verification."""
    hostname = remote.get("target_host")
    if not isinstance(hostname, str) or not hostname or hostname != hostname.lower():
        fail("CLIENT_COMMUNICATION_REMOTE_READBACK_INVALID")
    if hostname == "localhost" or hostname.endswith((".localhost", ".")):
        fail("CLIENT_COMMUNICATION_REMOTE_READBACK_INVALID")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None:
        address = getattr(address, "ipv4_mapped", None) or address
    dns_name = re.fullmatch(
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", hostname,
    )
    if ((address is None and not dns_name)
        or (address is not None and (address.is_loopback or address.is_unspecified
                                    or address.is_link_local or address.is_multicast))):
        fail("CLIENT_COMMUNICATION_REMOTE_READBACK_INVALID")
    status = remote.get("http_status")
    response = remote.get("response_sha256")
    ref = remote.get("authority_ref_sha")
    if (sent.get("target_host") != hostname
        or not client_public_url(remote.get("url"), hostname)
        or not client_public_url(remote.get("final_url"), hostname)
        or type(status) is not int or not 200 <= status < 300
        or remote.get("independent") is not True
        or remote.get("authority_identity_verified") is not True
        or remote.get("evidence") == sent.get("evidence")
        or not ((isinstance(response, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", response))
                or (isinstance(ref, str) and re.fullmatch(r"[0-9a-f]{40}", ref)))):
        fail("CLIENT_COMMUNICATION_REMOTE_READBACK_INVALID")
    window = require(receipt, "action_window", dict)
    observed = client_time(remote.get("observed_at"), "CLIENT_COMMUNICATION_REMOTE_READBACK_INVALID")
    completed = client_time(window.get("completed_at"), "CLIENT_ACTION_WINDOW_INVALID")
    closed = client_time(window.get("closed_at"), "CLIENT_ACTION_WINDOW_INVALID")
    if remote.get("action_id") != window.get("id") or not completed < observed <= closed:
        fail("CLIENT_COMMUNICATION_REMOTE_READBACK_NOT_FRESH")


def validate_client_communications(receipt: dict[str, Any], subject: dict[str, Any]) -> None:
    """Check declared evidence scope, without issuing an Effect-Ack assessment.

    Historical receipts without this field remain readable. These consistency
    checks neither run the original outbox tool nor authenticate its evidence.
    """
    records = receipt.get("communications", [])
    if not isinstance(records, list):
        fail("CLIENT_COMMUNICATION_INVALID")
    identifiers: set[str] = set()
    scopes = {"NOT_SENT", "SENT", "RECEIVED", "APPLIED", "RECEIVER_NACK", "PRINCIPAL_RETURN"}
    for record in records:
        if (not isinstance(record, dict)
            or set(record) != {"id", "message_sha256", "sender", "recipient", "claim", "evidence"}
            or any(not isinstance(record.get(key), str) or not record[key].strip()
                   for key in ("id", "sender"))
            or record["id"] in identifiers
            or not isinstance(record.get("claim"), str)
            or record.get("claim") not in scopes
            or not isinstance(record.get("message_sha256"), str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", record["message_sha256"])
            or not isinstance(record.get("evidence"), dict)):
            fail("CLIENT_COMMUNICATION_INVALID")
        identifiers.add(record["id"])
        claim, evidence = record["claim"], record["evidence"]
        if set(evidence) - {"send", "ingress", "outbox_claim", "application", "readback", "return", "remote_readback"}:
            fail("CLIENT_COMMUNICATION_INVALID")
        if claim == "NOT_SENT":
            if evidence:
                fail("CLIENT_UNSENT_WITH_DELIVERY_EVIDENCE")
            if not isinstance(record["recipient"], str) or not record["recipient"].strip():
                fail("CLIENT_COMMUNICATION_INVALID")
            continue
        if claim == "PRINCIPAL_RETURN":
            if record["recipient"] is not None or set(evidence) != {"return"}:
                fail("CLIENT_PRINCIPAL_RETURN_RECEIVER_INFERRED")
            returned = evidence["return"]
            if (not isinstance(returned, dict)
                or returned.get("message_sha256") != record["message_sha256"]
                or not isinstance(returned.get("evidence"), str) or not returned["evidence"].strip()):
                fail("CLIENT_COMMUNICATION_EVIDENCE_BINDING_MISMATCH")
            continue
        if not isinstance(record["recipient"], str) or not record["recipient"].strip():
            fail("CLIENT_COMMUNICATION_INVALID")

        def proof(kind: str) -> dict[str, Any]:
            value = evidence.get(kind)
            if (not isinstance(value, dict) or not isinstance(value.get("evidence"), str)
                or not value["evidence"].strip()):
                fail("CLIENT_COMMUNICATION_" + kind.upper() + "_REQUIRED")
            if (value.get("message_sha256") != record["message_sha256"]
                or value.get("node") != record["recipient"]):
                fail("CLIENT_COMMUNICATION_EVIDENCE_BINDING_MISMATCH")
            return value

        sent = proof("send")
        if (sent.get("sender") != record["sender"]
            or not isinstance(sent.get("channel"), str) or not sent["channel"].strip()):
            fail("CLIENT_COMMUNICATION_EVIDENCE_BINDING_MISMATCH")
        if claim == "SENT":
            continue
        remote = proof("remote_readback")
        validate_client_remote_readback(remote, sent, receipt)
        outbox = proof("outbox_claim")
        if (outbox.get("tool") != "node-tools/qikvrt_mirror_emit.py claim"
            or not isinstance(outbox.get("record_sha256"), str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", outbox["record_sha256"])):
            fail("CLIENT_COMMUNICATION_OUTBOX_CLAIM_REQUIRED")
        if claim in ("RECEIVED", "APPLIED"):
            proof("ingress")
        if claim == "APPLIED":
            applied, readback = proof("application"), proof("readback")
            if (applied.get("subject") != subject
                or not isinstance(applied.get("native_event_id"), str)
                or not applied["native_event_id"].strip()
                or not isinstance(applied.get("ledger_digest"), str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", applied["ledger_digest"])
                or readback.get("independent") is not True
                or any(readback.get(key) != applied.get(key)
                       for key in ("subject", "native_event_id", "ledger_digest"))
                or readback["evidence"] == applied["evidence"]):
                fail("CLIENT_COMMUNICATION_APPLICATION_READBACK_MISMATCH")
            if any(remote.get(key) != applied.get(key)
                   for key in ("subject", "native_event_id", "ledger_digest")):
                fail("CLIENT_COMMUNICATION_REMOTE_APPLICATION_MISMATCH")


def validate_client_receipt(receipt: dict[str, Any]) -> str:
    """Validate consistency; never authenticate a client or prove live effects."""
    if receipt.get("schema") != "qikvrt-client-continuation/1":
        fail("CLIENT_RECEIPT_SCHEMA_INVALID")
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
        if not count and "action" in attempt:
            validate_client_action(require(attempt, "action", dict), subject)
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
    transition_plan = client_transition_plan(receipt)
    repairs = transition_plan.get("blocking_repairs", []) if transition_plan else []
    repair_actions = ([item["action"] for item in transition_plan["ready"]]
                      if repairs else [])
    executable = False
    for action in actions:
        admitted = validate_client_action(action, subject)
        if admitted and repairs and action not in repair_actions:
            fail("CLIENT_ACTION_OUTSIDE_BLOCKING_REPAIR_SCOPE")
        executable |= admitted
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
    validate_client_communications(receipt, subject)
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--client-receipt", type=Path,
                        help="Validate a non-secret client continuation receipt; no live-effect proof")
    mode.add_argument("--client-action", type=Path,
                      help="Check one declared action against current Owner routing decisions before any external call")
    args = parser.parse_args()
    if args.client_action is not None:
        action = load_json(args.client_action)
        subject = require(action, "subject", dict)
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", str(subject.get("repository", "")))
                or any(not re.fullmatch(r"[0-9a-f]{40}", str(subject.get(key, "")))
                       for key in ("head", "tree"))
                or not isinstance(subject.get("ref"), str) or not subject["ref"].strip()):
            fail("CLIENT_SUBJECT_INVALID")
        ready = validate_client_action(action, subject)
        print("CLIENT_ACTION_CONSISTENCY=VALID")
        print("CLIENT_ROUTE_POLICY_SHA256=" + validate_client_tool_selection(action))
        print("CLIENT_DECLARED_ACTION=" + ("READY" if ready else "HOLD"))
        print("LIVE_EFFECT_VERIFICATION=NOT_PERFORMED")
        return 0 if ready else 2
    if args.client_receipt is not None:
        receipt = load_json(args.client_receipt)
        state = validate_client_receipt(receipt)
        print("CLIENT_HANDOFF_CONSISTENCY=VALID")
        print("CLIENT_STATE=" + state)
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
