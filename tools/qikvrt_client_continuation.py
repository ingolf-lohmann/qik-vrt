#!/usr/bin/env python3
"""QIK-VRT-owned client continuation decision. No network or side effects.

Input: a repository-produced JSON work-unit receipt on stdin.
Output: one canonical JSON decision on stdout.
The client never promotes an unverified effect into a completion.
"""
import argparse
import json
import re
import sys

SHA = re.compile(r"^[0-9a-f]{40}$")
STATES = {"OPEN", "RUNNING", "BLOCKED", "DONE"}
ACTIONS = {"READBACK", "REPAIR", "TEST", "REVIEW", "MERGE", "DEPLOY", "VERIFY"}
BLOCKERS = {"AUTHORIZATION", "INTEGRITY", "CI", "REVIEW", "HOST", "RUNTIME", "UNKNOWN"}


def decide(receipt):
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    required = ("schema", "repository", "work_unit_id", "writer_id",
                "head_sha", "state", "next_action", "effect_ack_done")
    if any(key not in receipt for key in required):
        raise ValueError("missing mandatory receipt fields")
    if receipt["schema"] != "qikvrt_client_continuation_v1":
        raise ValueError("unknown schema")
    if receipt["repository"] != "ingolf-lohmann/qik-vrt":
        raise ValueError("authority repository mismatch")
    if not isinstance(receipt["work_unit_id"], str) or not receipt["work_unit_id"].strip():
        raise ValueError("missing work-unit identity")
    if not isinstance(receipt["writer_id"], str) or not receipt["writer_id"].strip():
        raise ValueError("missing writer identity")
    if not isinstance(receipt["head_sha"], str) or not SHA.fullmatch(receipt["head_sha"]):
        raise ValueError("invalid exact head")
    if receipt["state"] not in STATES or receipt["next_action"] not in ACTIONS:
        raise ValueError("unknown state or action")
    if type(receipt["effect_ack_done"]) is not bool:
        raise ValueError("effect acknowledgement must be boolean")
    if receipt["state"] == "DONE" and not receipt["effect_ack_done"]:
        raise ValueError("DONE without independent effect acknowledgement")
    if receipt["effect_ack_done"] and receipt["state"] != "DONE":
        raise ValueError("effect acknowledgement conflicts with state")
    if receipt["state"] == "BLOCKED":
        if receipt.get("blocker") not in BLOCKERS:
            raise ValueError("blocked state requires typed blocker")
        disposition = "HOLD_EXTERNAL" if receipt["blocker"] == "AUTHORIZATION" else "CONTINUE_DIAGNOSIS"
    elif receipt["state"] == "DONE":
        disposition = "ACKNOWLEDGED"
    else:
        disposition = "CONTINUE"
    return {
        "schema": "qikvrt_client_decision_v1",
        "repository": receipt["repository"],
        "work_unit_id": receipt["work_unit_id"],
        "writer_id": receipt["writer_id"],
        "head_sha": receipt["head_sha"],
        "disposition": disposition,
        "next_action": None if disposition == "ACKNOWLEDGED" else receipt["next_action"],
        "effect_ack_done": receipt["effect_ack_done"],
    }


def selftest():
    base = dict(schema="qikvrt_client_continuation_v1",
                repository="ingolf-lohmann/qik-vrt", work_unit_id="unit-1",
                writer_id="writer-1", head_sha="a" * 40, state="RUNNING",
                next_action="TEST", effect_ack_done=False)
    assert decide(base)["disposition"] == "CONTINUE"
    assert decide(dict(base, state="BLOCKED", blocker="AUTHORIZATION"))["disposition"] == "HOLD_EXTERNAL"
    assert decide(dict(base, state="BLOCKED", blocker="CI"))["disposition"] == "CONTINUE_DIAGNOSIS"
    assert decide(dict(base, state="DONE", effect_ack_done=True))["disposition"] == "ACKNOWLEDGED"
    for bad in (dict(base, state="DONE"), dict(base, repository="other/repo"),
                dict(base, head_sha="bad"), dict(base, effect_ack_done="true")):
        try:
            decide(bad)
        except ValueError:
            continue
        raise AssertionError("unsafe receipt accepted")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        selftest()
        print("PASS")
        return 0
    try:
        receipt = json.load(sys.stdin)
        print(json.dumps(decide(receipt), sort_keys=True, separators=(",", ":")))
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "qikvrt_client_decision_v1", "disposition": "HOLD_INVALID",
                          "effect_ack_done": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
