#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Classify QIK-VRT continuation without confusing BLOCK/HOLD with HALT."""

from __future__ import annotations

import argparse
import hashlib
import re
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy/QIKVRT_RECURSIVE_HALTPOINT_V1.json"
HALT_REASONS = {
    "FINAL_IDLE",
    "REQUIRED_EXTERNAL_CAPABILITY_UNAVAILABLE",
    "REQUIRED_EXACT_HUMAN_AUTHORIZATION_UNAVAILABLE",
}


class HaltpointBlock(RuntimeError):
    pass


def load_policy() -> dict[str, Any]:
    value = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt_recursive_haltpoint_v1":
        raise HaltpointBlock("recursive haltpoint schema mismatch")
    if value.get("state") != "ACTIVE":
        raise HaltpointBlock("recursive haltpoint policy is not active")
    if set(value.get("halt_allowed_only_if", [])) != HALT_REASONS:
        raise HaltpointBlock("halt reasons differ from controller")
    exact = value.get("exact_subject", {})
    if exact.get("required") is not True or exact.get("predecessor_evidence_transfer") is not False:
        raise HaltpointBlock("exact-subject evidence boundary weakened")
    effect = value.get("effect_boundary", {})
    if effect.get("transport_ack_is_effect_ack") is not False:
        raise HaltpointBlock("transport/effect boundary weakened")
    return value


def _bool(value: Mapping[str, Any], key: str) -> bool:
    raw = value.get(key)
    if not isinstance(raw, bool):
        raise HaltpointBlock(f"{key} must be boolean")
    return raw


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    raw = value.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw:
        raise HaltpointBlock(f"{key} must be null or non-empty string")
    return raw


def _classify_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    load_policy()
    if observation.get("predecessor_evidence_transfer") is not False:
        raise HaltpointBlock("PREDECESSOR_EVIDENCE_TRANSFER must remain false")

    exact_subject_bound = _bool(observation, "exact_subject_bound")
    final_idle = _bool(observation, "final_idle")
    effect_ack_done = _bool(observation, "effect_ack_done")
    edge_authorized = _bool(observation, "edge_authorized")
    edge_callable = _bool(observation, "edge_callable")
    requires_external = _bool(observation, "requires_external_capability")
    external_available = _bool(observation, "external_capability_available")
    requires_human = _bool(observation, "requires_exact_human_authorization")
    human_available = _bool(observation, "exact_human_authorization_available")
    transport_ack = _bool(observation, "transport_ack")
    blocker = _optional_text(observation, "first_blocker")
    edge = _optional_text(observation, "productive_edge")

    if effect_ack_done and transport_ack is False:
        # Effect Ack is independent of transport; this is allowed.
        pass

    if not exact_subject_bound:
        return _result("WORK", False, "EXACT_SUBJECT_REBIND_REQUIRED", "REBIND_EXACT_HEAD_TREE", blocker, edge)

    if final_idle:
        if blocker is not None or edge is not None:
            raise HaltpointBlock("FINAL_IDLE cannot retain a blocker or productive edge")
        return _result("IDLE", True, "FINAL_IDLE", None, None, None)

    if blocker is None and edge is None:
        return _result("IDLE", False, "QUIESCENT_NOT_FINAL_IDLE", "REOBSERVE_AND_DERIVE_PRODUCTIVE_EDGE", None, None)

    if edge is None:
        return _result("WORK", False, "BLOCKER_REQUIRES_PRODUCTIVE_EDGE_DERIVATION", "DERIVE_FIRST_PRODUCTIVE_EDGE", blocker, None)

    if requires_external and not external_available:
        return _result("BLOCKADE", True, "REQUIRED_EXTERNAL_CAPABILITY_UNAVAILABLE", edge, blocker, edge)

    if requires_human and not human_available:
        return _result("BLOCKADE", True, "REQUIRED_EXACT_HUMAN_AUTHORIZATION_UNAVAILABLE", edge, blocker, edge)

    if edge_authorized and edge_callable:
        return _result("WORK", False, "AUTHORIZED_CALLABLE_PRODUCTIVE_EDGE", edge, blocker, edge)

    return _result(
        "WORK",
        False,
        "PRODUCTIVE_EDGE_PRESENT_REQUIRES_LOCAL_ADMISSION_OR_CAPABILITY_RESOLUTION",
        edge,
        blocker,
        edge,
    )


def _result(
    classification: str,
    halt: bool,
    reason: str,
    next_action: str | None,
    blocker: str | None,
    edge: str | None,
) -> dict[str, Any]:
    if halt and reason not in HALT_REASONS:
        raise HaltpointBlock("controller attempted an undeclared halt")
    return {
        "schema": "qikvrt_recursive_haltpoint_result_v1",
        "classification": classification,
        "halt": halt,
        "reason": reason,
        "first_blocker": blocker,
        "productive_edge": edge,
        "next_action": next_action,
        "recursive_continuation": not halt,
        "predecessor_evidence_transfer": False,
        "transport_ack_is_effect_ack": False,
    }


# One planner inside the existing controller, not another executor.
# Inputs are non-secret, exact-subject observations supplied by trusted readers.
CAPABILITY_CHECKS = (
    "owner_authorized", "tool_callable", "effective_permission",
    "credential_delivered", "target_scope_bound", "node_live",
    "role_fence_valid", "idempotency_bound", "readback_callable",
)
CONTEXT_FIELDS = (
    "repository", "head", "tree", "operation", "intent_id", "input_contract", "output_contract",
    "principal_id", "integration_id", "credential_epoch", "tool_epoch", "role_epoch", "authorization_epoch",
)
LESSONS_PATH = "docs/operations/CAPABILITY_PATH_LESSONS_20261004.md"
MAX_ROUTES, MAX_STEPS, MAX_AGE_SECONDS = 32, 16, 60


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_./:-]{1,200}", value) is None:
        raise HaltpointBlock("invalid non-secret identifier")
    return value


def _hex(value: Any, length: int) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{%d}" % length, value) is None:
        raise HaltpointBlock("invalid evidence digest")
    return value


def _integer(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise HaltpointBlock("non-negative integer required")
    return value


def route_key(context: Mapping[str, Any], route: Mapping[str, Any]) -> str:
    """Cache only observations, never tokens, approvals, or execution permission."""
    if not isinstance(context, Mapping) or not isinstance(route, Mapping):
        raise HaltpointBlock("route/context objects required")
    binding = {key: _identifier(context.get(key)) for key in CONTEXT_FIELDS}
    _hex(binding["head"], 40)
    _hex(binding["tree"], 40)
    _hex(binding["input_contract"], 64)
    _hex(binding["output_contract"], 64)
    steps = route.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise HaltpointBlock("bounded non-empty composition required")
    contracts = []
    for step in steps:
        if not isinstance(step, Mapping):
            raise HaltpointBlock("step object required")
        contracts.append({
            "component": _identifier(step.get("component")),
            "source_blob": _hex(step.get("source_blob"), 40),
            "input_contract": _hex(step.get("input_contract"), 64),
            "output_contract": _hex(step.get("output_contract"), 64),
        })
    return _digest({"binding": binding, "route": _identifier(route.get("id")),
                    "contracts": contracts,
                    "policy": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest()})


def resolve_capability_routes(request: Mapping[str, Any]) -> dict[str, Any]:
    """Select a compatible existing path; execute zero effects and zero retries.

    A plan is not proof that future steps ran. Reobserve after EACH step and
    after any source, principal, credential, tool, policy, role or intent change.
    """
    if not isinstance(request, Mapping):
        raise HaltpointBlock("capability request object required")
    load_policy()
    now = _integer(request.get("now"))
    context = request.get("context")
    if not isinstance(context, Mapping):
        raise HaltpointBlock("exact capability context required")
    routes = request.get("routes")
    if not isinstance(routes, list) or len(routes) > MAX_ROUTES:
        raise HaltpointBlock("bounded route inventory required")
    state = request.get("intent_state")
    if state not in ("NOT_STARTED", "UNKNOWN_EFFECT", "ACKNOWLEDGED"):
        raise HaltpointBlock("explicit intent state required")
    # Validate context even for an empty inventory; no unbound success/NOOP.
    for key in CONTEXT_FIELDS:
        _identifier(context.get(key))
    _hex(context["head"], 40)
    _hex(context["tree"], 40)
    _hex(context["input_contract"], 64)
    _hex(context["output_contract"], 64)
    result = {"schema": "qikvrt_capability_route_resolution_v1",
              "scope": "SUPPLIED_INVENTORY_ONLY", "selected_route": None,
              "planned_steps": [], "blocked_routes": [], "negative_cache": [],
              "effect_permission": False, "effect_ack_done": False,
              "predecessor_evidence_transfer": False,
              "next_action": "OBSERVE_EXISTING_CAPABILITY_PATHS"}
    if state != "NOT_STARTED":
        _hex(request.get("intent_receipt_sha256"), 64)
        result.update(state="READBACK_ONLY", next_action="READBACK_EXISTING_INTENT_NO_REPLAY")
        return result
    cache = request.get("negative_cache", [])
    if not isinstance(cache, list) or len(cache) > MAX_ROUTES:
        raise HaltpointBlock("bounded negative cache required")
    blocked_keys = set()
    for entry in cache:
        if not isinstance(entry, Mapping):
            raise HaltpointBlock("negative cache entry required")
        key = _hex(entry.get("key"), 64)
        timestamp = _integer(entry.get("observed_at"))
        _hex(entry.get("receipt_sha256"), 64)
        if 0 <= now - timestamp < MAX_AGE_SECONDS:
            blocked_keys.add(key)
    choices, seen = [], set()
    for route in routes:
        key = route_key(context, route)
        name = route["id"]
        if name in seen:
            raise HaltpointBlock("duplicate route identifier")
        seen.add(name)
        reason = None
        if key in blocked_keys:
            reason = "UNCHANGED_DENIAL_NO_RETRY"
        previous = context["input_contract"]
        for step in route["steps"]:
            if previous is not None and previous != step["input_contract"]:
                reason = reason or "INTERFACE_CONTRACT_MISMATCH"
            previous = step["output_contract"]
            checks = step.get("checks")
            if not isinstance(checks, Mapping) or set(checks) != set(CAPABILITY_CHECKS):
                raise HaltpointBlock("complete separated capability checks required")
            for check in CAPABILITY_CHECKS:
                value = checks[check]
                if value is not None and type(value) is not bool:
                    raise HaltpointBlock("capability check must be boolean or unknown")
            evidence = step.get("evidence")
            if not isinstance(evidence, Mapping):
                raise HaltpointBlock("step evidence binding required")
            receipt = _hex(evidence.get("receipt_sha256"), 64)
            timestamp = _integer(evidence.get("observed_at"))
            if evidence.get("key") != key or not 0 <= now - timestamp < MAX_AGE_SECONDS:
                reason = reason or "REOBSERVE_CHANGED_OR_STALE_CAPABILITY"
            else:
                for check in CAPABILITY_CHECKS:
                    if checks[check] is not True:
                        reason = reason or ("UNOBSERVED:" if checks[check] is None else "DENIED:") + check
                        if checks[check] is False and key not in blocked_keys:
                            result["negative_cache"].append({"key": key, "observed_at": timestamp,
                                                             "receipt_sha256": receipt})
                            blocked_keys.add(key)
                        break
        if previous != context["output_contract"]:
            reason = reason or "OUTPUT_CONTRACT_MISMATCH"
        cost = _integer(route.get("measured_latency_ms"))
        if reason:
            result["blocked_routes"].append({"id": name, "reason": reason, "key": key})
        else:
            choices.append((cost, name, [step["component"] for step in route["steps"]]))
    if choices:
        _, name, steps = min(choices)
        result.update(state="PLAN_CANDIDATE", selected_route=name, planned_steps=steps,
                      next_action="REOBSERVE_AND_ADMIT_FIRST_STEP")
    else:
        result.update(state="CAPABILITY_PATH_UNRESOLVED",
                      next_action="REPAIR_FIRST_MISSING_CAPABILITY_OR_BIND_ALTERNATIVE")
    return result


def classify(observation: Mapping[str, Any]) -> dict[str, Any]:
    result = _classify_observation(observation)
    # Legacy callers also receive the mandatory preflight boundary. Their
    # booleans have never constituted a writer grant.
    result["effect_permission"] = False
    result["capability_contract"] = LESSONS_PATH
    result["capability_resolution"] = {"state": "UNOBSERVED_NOT_EXECUTION_AUTHORITY"}
    request = observation.get("capability_routes")
    if request is None:
        return result
    if observation["final_idle"]:
        raise HaltpointBlock("FINAL_IDLE cannot request route composition")
    if not observation["exact_subject_bound"]:
        return result
    if not isinstance(request, Mapping) or not isinstance(request.get("context"), Mapping):
        raise HaltpointBlock("exact capability context required")
    if observation.get("subject") != {
        key: request.get("context", {}).get(key) for key in ("repository", "head", "tree")
    }:
        raise HaltpointBlock("route and observation subjects differ")
    resolution = resolve_capability_routes(request)
    result["capability_resolution"] = resolution
    if observation["requires_exact_human_authorization"] and not observation["exact_human_authorization_available"]:
        return result
    if resolution["state"] in ("PLAN_CANDIDATE", "READBACK_ONLY"):
        result.update(classification="WORK", halt=False, recursive_continuation=True,
                      reason="CAPABILITY_ROUTE_REOBSERVATION_REQUIRED",
                      next_action=resolution["next_action"])
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.observation.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise HaltpointBlock("observation must be an object")
        result = classify(value)
    except (OSError, ValueError, json.JSONDecodeError, HaltpointBlock) as exc:
        print(json.dumps({"state": "BLOCK", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
