#!/usr/bin/env python3
"""Deterministic reference model for the QIK-VRT Digital Twin REST adapter."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TwinState:
    twin_id: str
    version: int
    position_m: float
    velocity_mps: float
    temperature_c: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TwinState":
        return cls(
            twin_id=str(value["twin_id"]),
            version=int(value["version"]),
            position_m=float(value["position_m"]),
            velocity_mps=float(value["velocity_mps"]),
            temperature_c=float(value["temperature_c"]),
        )


def digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def observe(state: TwinState) -> dict[str, Any]:
    body = asdict(state)
    return {"state": body, "state_sha256": digest(body)}


def prepare(state: TwinState, *, target_velocity_mps: float) -> dict[str, Any]:
    target = float(target_velocity_mps)
    if not 0.0 <= target <= 100.0:
        raise ValueError("TARGET_VELOCITY_OUT_OF_RANGE")
    return {
        "expected_version": state.version,
        "target_velocity_mps": target,
        "before_state_sha256": digest(asdict(state)),
    }


def commit_simulated(state: TwinState, prepared: dict[str, Any]) -> tuple[TwinState, dict[str, Any]]:
    if prepared.get("expected_version") != state.version:
        raise ValueError("STALE_EXACT_TWIN_VERSION")
    if prepared.get("before_state_sha256") != digest(asdict(state)):
        raise ValueError("STALE_EXACT_TWIN_STATE")
    target = float(prepared["target_velocity_mps"])
    after = TwinState(
        twin_id=state.twin_id,
        version=state.version + 1,
        position_m=state.position_m,
        velocity_mps=target,
        temperature_c=state.temperature_c,
    )
    return after, {
        "kind": "SIMULATED_REFERENCE_TRANSITION",
        "before_version": state.version,
        "after_version": after.version,
        "target_velocity_mps": target,
        "physical_effect": False,
    }


def reobserve(before: TwinState, after: TwinState, effect: dict[str, Any]) -> dict[str, Any]:
    before_sha = digest(asdict(before))
    after_sha = digest(asdict(after))
    effect_ack = (
        effect.get("kind") == "SIMULATED_REFERENCE_TRANSITION"
        and effect.get("before_version") == before.version
        and effect.get("after_version") == after.version
        and after.version == before.version + 1
        and after.twin_id == before.twin_id
        and after.position_m == before.position_m
        and after.temperature_c == before.temperature_c
        and effect.get("target_velocity_mps") == after.velocity_mps
        and after_sha != before_sha
    )
    return {
        "before_state_sha256": before_sha,
        "after_state_sha256": after_sha,
        "effect_ack": effect_ack,
        "physical_effect_ack": False,
    }
