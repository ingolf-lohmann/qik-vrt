#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Classify QIK-VRT continuation without confusing BLOCK/HOLD with HALT."""

from __future__ import annotations

import argparse
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


def classify(observation: Mapping[str, Any]) -> dict[str, Any]:
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
