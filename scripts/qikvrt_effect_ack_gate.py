# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed Effect Acknowledgement Protocol state gate.

A successful build or claim never implies deployment or an acknowledged effect.
Every stage requires an independently supplied, exact-subject evidence record.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

STAGES = (
    "intake", "claimed", "implemented", "local_tested",
    "native_ci", "governance", "merged", "deployed", "effect_ack",
)
EVIDENCE_KEYS = {
    "intake": ("issue",),
    "claimed": ("claim_run",),
    "implemented": ("head", "tree"),
    "local_tested": ("head", "tree", "test_run"),
    "native_ci": ("head", "tree", "ci_run"),
    "governance": ("head", "tree", "approval"),
    "merged": ("merge_commit",),
    "deployed": ("deployment_id", "target", "readback"),
    "effect_ack": ("effect_id", "observation", "readback"),
}


def validate(record: dict) -> tuple[bool, str]:
    if not isinstance(record, dict) or not isinstance(record.get("events"), list):
        return False, "missing ordered events"
    events = record["events"]
    if not events:
        return False, "empty evidence chain"
    subject = None
    for index, event in enumerate(events):
        if not isinstance(event, dict) or index >= len(STAGES):
            return False, "invalid event or too many events"
        stage = STAGES[index]
        if event.get("stage") != stage:
            return False, f"expected {stage} at index {index}"
        if not all(isinstance(event.get(key), str) and event[key].strip()
                   for key in EVIDENCE_KEYS[stage]):
            return False, f"missing evidence for {stage}"
        if stage == "implemented":
            subject = (event["head"], event["tree"])
        if stage in ("local_tested", "native_ci", "governance"):
            if (event["head"], event["tree"]) != subject:
                return False, f"subject drift at {stage}"
        if stage == "effect_ack" and event.get("effect_ack_done") is not True:
            return False, "effect not acknowledged"
    return True, events[-1]["stage"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("--require-dod", action="store_true")
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
        valid, state = validate(record)
    except (OSError, ValueError, TypeError) as exc:
        print(f"EAP_BLOCK invalid record: {exc}")
        return 2
    print(f"EAP_{'VALID' if valid else 'BLOCK'} {state}")
    if not valid:
        return 2
    if args.require_dod and state != "effect_ack":
        print("EAP_BLOCK definition of done not reached")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
