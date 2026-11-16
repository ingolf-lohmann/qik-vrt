#!/usr/bin/env python3
"""Persist a fail-closed diagnostic successor receipt, without authorizing effects.

The caller supplies the exact repository work-unit receipt and the adapter decision.
This tool writes an atomic, deterministic per-writer recovery record. It does not
claim a repair, GitHub admission, merge or EAP acknowledgement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

SHA = re.compile(r"^[0-9a-f]{40}$")
IDENTITY = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def materialize(receipt, decision, directory):
    if not isinstance(receipt, dict) or not isinstance(decision, dict):
        raise ValueError("receipt and decision must be objects")
    for field in ("repository", "work_unit_id", "writer_id", "head_sha"):
        if receipt.get(field) != decision.get(field):
            raise ValueError("identity mismatch: " + field)
    if receipt["repository"] != "ingolf-lohmann/qik-vrt":
        raise ValueError("authority mismatch")
    if not SHA.fullmatch(receipt["head_sha"]):
        raise ValueError("invalid exact HEAD")
    if not all(IDENTITY.fullmatch(receipt[field]) for field in ("work_unit_id", "writer_id")):
        raise ValueError("unsafe work-unit identity")
    if decision.get("effect_ack_done") is not False:
        raise ValueError("unverified acknowledgement")
    if decision.get("disposition") not in ("CONTINUE_DIAGNOSIS", "HOLD_EXTERNAL"):
        raise ValueError("only blocked successors may be persisted")
    fingerprint = hashlib.sha256(json.dumps(
        {"receipt": receipt, "decision": decision}, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    record = {
        "schema": "qikvrt_diagnostic_successor_v1",
        "repository": receipt["repository"],
        "work_unit_id": receipt["work_unit_id"],
        "writer_id": receipt["writer_id"],
        "head_sha": receipt["head_sha"],
        "fingerprint_sha256": fingerprint,
        "status": "OPEN",
        "disposition": decision["disposition"],
        "blocker": decision.get("blocked_on") or receipt.get("blocker") or "UNKNOWN",
        "next_action": "READBACK" if decision["disposition"] == "CONTINUE_DIAGNOSIS" else None,
        "effect_ack_done": False,
        "requires_independent_verification": True,
    }
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    path = root / (receipt["writer_id"] + "-" + receipt["work_unit_id"] + ".json")
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous == record:
            return path
        if previous.get("status") == "OPEN" and previous.get("head_sha") != record["head_sha"]:
            raise ValueError("unresolved predecessor: explicit successor reconciliation required")
    fd, temporary = tempfile.mkstemp(prefix=".successor-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def resume(directory, writer_id, work_unit_id, expected_head):
    """Read back the exact persisted successor without claiming effect or repair."""
    if not all(isinstance(x, str) and IDENTITY.fullmatch(x)
               for x in (writer_id, work_unit_id)):
        raise ValueError("unsafe identity")
    if not isinstance(expected_head, str) or not SHA.fullmatch(expected_head):
        raise ValueError("invalid exact HEAD")
    path = Path(directory) / (writer_id + "-" + work_unit_id + ".json")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (record.get("schema") != "qikvrt_diagnostic_successor_v1"
            or record.get("repository") != "ingolf-lohmann/qik-vrt"
            or record.get("writer_id") != writer_id
            or record.get("work_unit_id") != work_unit_id
            or record.get("head_sha") != expected_head
            or record.get("status") != "OPEN"
            or record.get("effect_ack_done") is not False
            or record.get("requires_independent_verification") is not True):
        raise ValueError("successor readback mismatch")
    if record.get("disposition") == "HOLD_EXTERNAL":
        if record.get("next_action") is not None:
            raise ValueError("external gate cannot execute")
        return {"state": "HOLD_EXTERNAL", "next_action": None,
                "writer_id": writer_id, "head_sha": expected_head}
    if record.get("disposition") != "CONTINUE_DIAGNOSIS" or record.get("next_action") != "READBACK":
        raise ValueError("unsafe successor action")
    return {"state": "CONTINUE_DIAGNOSIS", "next_action": "READBACK",
            "writer_id": writer_id, "head_sha": expected_head,
            "effect_ack_done": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--writer-id")
    parser.add_argument("--work-unit-id")
    parser.add_argument("--expect-head")
    parser.add_argument("--receipt")
    parser.add_argument("--decision")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.resume:
        print(json.dumps(resume(args.output_dir, args.writer_id,
                                args.work_unit_id, args.expect_head), sort_keys=True))
        return
    if not args.receipt or not args.decision:
        parser.error("--receipt and --decision required for materialization")
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    print(materialize(receipt, decision, args.output_dir))


if __name__ == "__main__":
    main()
