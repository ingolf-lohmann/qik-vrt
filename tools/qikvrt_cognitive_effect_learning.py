#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Pure and fail-closed source-conformance model; NEVER a native EAP verifier.

No network, Git, host, release or other side effects. Neither caller-supplied
booleans nor passing tests authenticate a receipt or establish EFFECT_ACK_DONE.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/QIKVRT_COGNITIVE_EFFECT_LEARNING_V1.json"
REQUIRED = (
    "observationBound", "modelBound", "decisionAuthorized",
    "receiptAuthenticated", "independentEffectReadback",
    "durableJournal", "writerFenced",
)
SCHEMA = "qikvrt_cognitive_effect_learning_policy_v1"


def validate_policy(policy: object) -> dict:
    if not isinstance(policy, dict) or policy.get("schema") != SCHEMA:
        raise ValueError("POLICY_SCHEMA_MISMATCH")
    if policy.get("authority") != "ingolf-lohmann/qik-vrt":
        raise ValueError("WRONG_AUTHORITY")
    if policy.get("model_evidence_flags") != list(REQUIRED):
        raise ValueError("EVIDENCE_FLAGS_MISMATCH")
    if (policy.get("effect_ack_done") is not False or
            policy.get("release_admission") != "BLOCKED" or
            policy.get("workflow_purpose") != "SOURCE_TEST_AND_LEAN_KERNEL_ONLY" or
            policy.get("competitive_superiority_over_all_systems") != "NOT_PROVEN"):
        raise ValueError("UNADMITTED_EFFECT_OR_COMPARATIVE_CLAIM")
    phases = policy.get("roundtrip")
    if not isinstance(phases, list) or phases != [
        "DISTINGUISH", "OBSERVE", "INFORM", "MODEL", "DECIDE", "AUTHORIZE", "ACT",
        "INDEPENDENT_EFFECT_READBACK", "PERSIST", "LEARN", "NEXT_DIFFERENCE",
    ]:
        raise ValueError("ROUNDTRIP_CHANGED")
    return policy


def evaluate(evidence: object) -> dict:
    """Evaluate the abstract predicate, never a productive authorization."""
    if not isinstance(evidence, dict) or set(evidence) != set(REQUIRED):
        raise ValueError("MISSING_OR_UNKNOWN_GATE")
    if any(type(evidence[key]) is not bool for key in REQUIRED):
        raise ValueError("NON_BOOLEAN_GATE")
    missing = [key for key in REQUIRED if evidence[key] is False]
    return {
        "schema": "qikvrt_cognitive_effect_learning_model_receipt_v1",
        "abstract_model_satisfies_gates": not missing,
        "missing_model_gates": missing,
        "state": "HOLD",
        "release_admission": "BLOCKED",
        "effect_ack_done": False,
        "native_execution": False,
        "external_effect_authenticated": False,
        "scope": "ABSTRACT_ONLY_NOT_NATIVE_READBACK",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(POLICY))
    args = parser.parse_args()
    validate_policy(json.loads(Path(args.policy).read_text(encoding="utf-8")))
    print(json.dumps({"policy_valid": True, "effect_ack_done": False,
                      "release_admission": "BLOCKED"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
