#!/usr/bin/env python3
"""Fail-closed COMMIT intent/effect gate for the existing QIK-VRT writer.

This is a pure validation component, not a second controller or scheduler.
The existing writer must persist records and invoke this gate at its output boundary.
"""
import argparse
import json
import sys

STATES = ("RECEIVED", "PERSISTED", "ADMITTED", "EXECUTING",
          "EFFECT_VERIFIED", "BLOCKED", "REPAIR_REQUIRED")
TRANSITIONS = {
    "RECEIVED": {"PERSISTED", "BLOCKED"},
    "PERSISTED": {"ADMITTED", "BLOCKED", "REPAIR_REQUIRED"},
    "ADMITTED": {"EXECUTING", "BLOCKED", "REPAIR_REQUIRED"},
    "EXECUTING": {"EFFECT_VERIFIED", "BLOCKED", "REPAIR_REQUIRED"},
    "BLOCKED": {"PERSISTED", "REPAIR_REQUIRED"},
    "REPAIR_REQUIRED": {"PERSISTED", "ADMITTED"},
    "EFFECT_VERIFIED": set(),
}

def validate(record):
    """Return (accepted, reason); reject unproven success."""
    if not isinstance(record, dict):
        return False, "invalid_record"
    if not all(isinstance(record.get(k), str) and record[k] for k in
               ("intent_id", "principal_authorization", "authority_repo", "exact_head")):
        return False, "missing_durable_identity_or_authorization"
    events = record.get("events")
    if not isinstance(events, list) or not events:
        return False, "missing_persisted_event_history"
    previous = None
    for event in events:
        if not isinstance(event, dict) or event.get("state") not in STATES:
            return False, "invalid_event"
        state = event["state"]
        if previous is None and state != "RECEIVED":
            return False, "missing_received_event"
        if previous is not None and state not in TRANSITIONS[previous]:
            return False, "illegal_state_transition"
        previous = state
    if previous != "EFFECT_VERIFIED":
        return False, "effect_not_verified"
    if not all(isinstance(record.get(k), str) and record[k] for k in
               ("commit_sha", "readback_sha", "eap_receipt_id", "writer_lease_id")):
        return False, "missing_effect_evidence"
    if record["commit_sha"] != record["readback_sha"]:
        return False, "commit_readback_mismatch"
    if record["authority_repo"] != "ingolf-lohmann/qik-vrt":
        return False, "wrong_authority"
    return True, "effect_verified"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("record", help="persisted JSON intent/effect record")
    args = p.parse_args()
    with open(args.record, encoding="utf-8") as f:
        record = json.load(f)
    accepted, reason = validate(record)
    print(json.dumps({"effect_ack_done": accepted, "reason": reason}))
    return 0 if accepted else 2

if __name__ == "__main__":
    sys.exit(main())
