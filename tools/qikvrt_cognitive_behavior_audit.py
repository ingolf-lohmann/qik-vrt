#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed, evidence-bound audit case evaluator. NOT a native EAP effect verifier.

The caller must provide independently collected, authenticated source evidence.
This validator only checks presence, binding, hash format and explicit comparison
outcomes; it cannot independently authenticate a source or observe a remote host.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED = (
    "audit_id", "subject_id", "claim_id", "subject_head", "owner_instruction_ref",
    "expected_effect", "target_host", "test_steps", "observation_window",
    "actor_id", "verifier_id", "verifier_authentication", "observed_effect",
    "readback_source", "readback_hash", "readback_timestamp", "comparison_result",
    "evidence_class", "reproduction_result",
)


def evaluate(case: object) -> dict[str, str]:
    """Produce a bounded, case-local verdict. Never authorize an EAP transition."""
    if not isinstance(case, Mapping):
        return {"disposition": "UNVERIFIED", "reason": "CASE_NOT_OBJECT"}
    if any(k not in case for k in REQUIRED):
        return {"disposition": "UNVERIFIED", "reason": "REQUIRED_FIELD_MISSING"}
    if not all(isinstance(case[k], str) and case[k].strip()
               for k in REQUIRED if k not in {"test_steps", "observation_window"}):
        return {"disposition": "UNVERIFIED", "reason": "REQUIRED_VALUE_INVALID"}
    if not isinstance(case["test_steps"], list) or not case["test_steps"] or not all(
        isinstance(x, str) and x.strip() for x in case["test_steps"]
    ):
        return {"disposition": "UNVERIFIED", "reason": "TEST_STEPS_INVALID"}
    window = case["observation_window"]
    if not isinstance(window, Mapping) or not all(
        isinstance(window.get(k), str) and window[k].strip() for k in ("start", "end")
    ):
        return {"disposition": "UNVERIFIED", "reason": "OBSERVATION_WINDOW_INVALID"}
    if case["actor_id"] == case["verifier_id"]:
        return {"disposition": "UNVERIFIED", "reason": "SELF_ATTESTATION"}
    if not SHA256.fullmatch(case["readback_hash"]):
        return {"disposition": "UNVERIFIED", "reason": "READBACK_HASH_INVALID"}
    if case["evidence_class"] not in {"INDEPENDENT_ORIGINAL_READBACK", "SELF_REPORT", "CLAIM_ONLY"}:
        return {"disposition": "UNVERIFIED", "reason": "EVIDENCE_CLASS_INVALID"}
    if case["evidence_class"] != "INDEPENDENT_ORIGINAL_READBACK":
        return {"disposition": "UNVERIFIED", "reason": "NOT_INDEPENDENT_EVIDENCE"}
    if case["reproduction_result"] != "REPRODUCED":
        return {"disposition": "UNVERIFIED", "reason": "REPRODUCTION_NOT_CONFIRMED"}
    if case["comparison_result"] == "CONTRADICTED":
        return {"disposition": "CONTRADICTED", "reason": "OBSERVATION_CONTRADICTS_CLAIM"}
    if case["comparison_result"] == "MATCH":
        return {"disposition": "CONSISTENT", "reason": "DECLARED_COMPARISON_MATCHED"}
    return {"disposition": "UNVERIFIED", "reason": "COMPARISON_NOT_CONFIRMED"}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: qikvrt_cognitive_behavior_audit.py AUDIT_CASE.json", file=sys.stderr)
        return 2
    try:
        case = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"disposition": "UNVERIFIED", "reason": type(exc).__name__}))
        return 2
    verdict = evaluate(case)
    print(json.dumps(verdict, sort_keys=True))
    return 0 if verdict["disposition"] == "CONSISTENT" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
