#!/usr/bin/env python3
"""Fail-closed, monotonic EAP receipt mirror. No infrastructure mutations."""
import argparse
import hashlib
import json
from pathlib import Path


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def validate(previous, candidate):
    """Accept a successor only if the acknowledged effect prefix remains intact."""
    required = ("source_head", "source_tree", "writer_fence", "effect_id",
                "effect_sha256", "readback_sha256", "sequence")
    if not isinstance(candidate, dict) or any(not candidate.get(k) for k in required):
        return False, "MISSING_EFFECT_BINDING"
    if type(candidate["sequence"]) is not int or candidate["sequence"] < 1:
        return False, "INVALID_SEQUENCE"
    if candidate.get("emp_execution") != "CONFIRMED" or candidate.get("eap_readback") != "CONFIRMED":
        return False, "EFFECT_NOT_INDEPENDENTLY_CONFIRMED"
    if candidate.get("effect_ack_done") is not True:
        return False, "EFFECT_ACK_NOT_DONE"
    if any(not isinstance(candidate[k], str) or len(candidate[k]) != 64 or
           any(c not in "0123456789abcdef" for c in candidate[k])
           for k in ("source_head", "source_tree", "effect_sha256", "readback_sha256")):
        # Git HEAD/TREE are 40-character SHA-1 or 64-character SHA-256, depending on repository.
        for k in ("source_head", "source_tree"):
            v = candidate[k]
            if not isinstance(v, str) or len(v) not in (40, 64) or any(c not in "0123456789abcdef" for c in v):
                return False, "INVALID_SOURCE_PIN"
        for k in ("effect_sha256", "readback_sha256"):
            v = candidate[k]
            if not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
                return False, "INVALID_EFFECT_DIGEST"
    if candidate["effect_sha256"] != candidate["readback_sha256"]:
        return False, "EFFECT_READBACK_MISMATCH"
    if previous is None:
        if candidate["sequence"] != 1 or candidate.get("previous_receipt_sha256") is not None:
            return False, "INVALID_GENESIS"
        return True, "GENESIS_CONFIRMED"
    ok, reason = validate_chain_entry(previous)
    if not ok:
        return False, reason
    if candidate["sequence"] != previous["sequence"] + 1:
        return False, "NON_MONOTONIC_SEQUENCE"
    if candidate.get("previous_receipt_sha256") != hashlib.sha256(canonical(previous)).hexdigest():
        return False, "BROKEN_RECEIPT_CHAIN"
    if candidate["effect_id"] == previous["effect_id"]:
        return False, "DUPLICATE_EFFECT"
    if candidate["source_head"] != previous["source_head"] or candidate["source_tree"] != previous["source_tree"]:
        return False, "SOURCE_PIN_CHANGED"
    if candidate["writer_fence"] != previous["writer_fence"] and candidate.get("fence_handoff_receipt_sha256") != hashlib.sha256(canonical(previous)).hexdigest():
        return False, "UNVERIFIED_FENCE_HANDOFF"
    return True, "SUCCESSOR_CONFIRMED"


def validate_chain_entry(receipt):
    if not isinstance(receipt, dict):
        return False, "INVALID_PREDECESSOR"
    if type(receipt.get("sequence")) is not int or receipt["sequence"] < 1:
        return False, "INVALID_PREDECESSOR_SEQUENCE"
    # This verifies receipt shape only; full ancestry and authentic signatures must
    # be verified against the trusted journal before production admission.
    return validate(None, {**receipt, "sequence": 1, "previous_receipt_sha256": None})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    try:
        previous = json.loads(args.previous.read_text()) if args.previous else None
        candidate = json.loads(args.candidate.read_text())
        ok, reason = validate(previous, candidate)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        ok, reason = False, type(exc).__name__
    print(json.dumps({"admitted": ok, "reason": reason, "effect_ack_done": ok}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
