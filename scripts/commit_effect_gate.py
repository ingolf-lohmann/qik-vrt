#!/usr/bin/env python3
"""Fail-closed COMMIT intent/effect gate for the existing QIK-VRT writer.

This is a pure validation component, not a second controller or scheduler.
The existing writer must persist records and invoke this gate at its output boundary.
"""
import argparse
import json
import re
import sys

STATES = ("RECEIVED", "PERSISTED", "ADMITTED", "EXECUTING",
          "EFFECT_VERIFIED", "BLOCKED", "REPAIR_REQUIRED")
TRANSITIONS = {
    "RECEIVED": {"PERSISTED", "BLOCKED"},
    "PERSISTED": {"ADMITTED", "BLOCKED", "REPAIR_REQUIRED"},
    "ADMITTED": {"EXECUTING", "BLOCKED", "REPAIR_REQUIRED"},
    "EXECUTING": {"EFFECT_VERIFIED", "BLOCKED", "REPAIR_REQUIRED"},
    "BLOCKED": {"PERSISTED", "REPAIR_REQUIRED"},
    "REPAIR_REQUIRED": {"PERSISTED"},
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
               ("commit_sha", "readback_sha", "eap_receipt_id", "writer_lease_id",
                "writer_identity", "writer_claim_id")):
        return False, "missing_effect_evidence"
    # A lease label cannot substitute for a positive writer fencing token.
    if type(record.get("writer_fencing_token")) is not int or record["writer_fencing_token"] < 1:
        return False, "missing_writer_fencing"
    if not all(re.fullmatch(r"[0-9a-f]{40}", record[k]) for k in
               ("exact_head", "commit_sha", "readback_sha")):
        return False, "invalid_commit_identity"
    if record["commit_sha"] != record["readback_sha"]:
        return False, "commit_readback_mismatch"
    if record["authority_repo"] != "ingolf-lohmann/qik-vrt":
        return False, "wrong_authority"
    # Check binding, not provenance. The caller still has to authenticate this
    # observation independently; this JSON record is not an EAP effect proof.
    ack = record.get("eap_readback")
    if (not isinstance(ack, dict) or ack.get("effect_ack_done") is not True
            or ack.get("receipt_id") != record["eap_receipt_id"]
            or ack.get("commit_sha") != record["commit_sha"]
            or ack.get("writer_claim_id") != record["writer_claim_id"]
            or ack.get("writer_fencing_token") != record["writer_fencing_token"]):
        return False, "unbound_eap_readback"
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
