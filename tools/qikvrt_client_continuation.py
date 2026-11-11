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
BLOCKERS = {"AUTHORIZATION", "INTEGRITY", "CI", "REVIEW", "HOST", "RUNTIME", "UNKNOWN", "WORKFLOW_APPROVAL"}


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
    if (not isinstance(receipt["state"], str) or not isinstance(receipt["next_action"], str)\n            or receipt["state"] not in STATES or receipt["next_action"] not in ACTIONS):
        raise ValueError("unknown state or action")
    if type(receipt["effect_ack_done"]) is not bool:
        raise ValueError("effect acknowledgement must be boolean")
    if receipt["state"] == "DONE" and receipt["effect_ack_done"]:
        raise ValueError("unverified external effect acknowledgement: independent EAP verifier required")
    if receipt["state"] == "DONE" and not receipt["effect_ack_done"]:
        raise ValueError("DONE without independent effect acknowledgement")
    if receipt["effect_ack_done"] and receipt["state"] != "DONE":
        raise ValueError("effect acknowledgement conflicts with state")
    if receipt["state"] == "BLOCKED":
        if not isinstance(receipt.get("blocker"), str) or receipt["blocker"] not in BLOCKERS:
            raise ValueError("blocked state requires typed blocker")
        disposition = ("HOLD_EXTERNAL" if receipt["blocker"] in {"AUTHORIZATION", "WORKFLOW_APPROVAL"}
                       else "CONTINUE_DIAGNOSIS")
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
        "next_action": (None if disposition in {"ACKNOWLEDGED", "HOLD_EXTERNAL"}
                        else ("READBACK" if disposition == "CONTINUE_DIAGNOSIS" else receipt["next_action"])),
        "blocked_on": (receipt["blocker"] if disposition == "HOLD_EXTERNAL" else None),
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
    approval = decide(dict(base, state="BLOCKED", blocker="WORKFLOW_APPROVAL"))
    assert approval["disposition"] == "HOLD_EXTERNAL"
    assert approval["next_action"] is None and approval["blocked_on"] == "WORKFLOW_APPROVAL"
    try:
        decide(dict(base, state="DONE", effect_ack_done=True))
    except ValueError:
        pass
    else:
        raise AssertionError("unverified DONE accepted")
    for bad in (dict(base, state="DONE"), dict(base, state=[]),
                dict(base, next_action={}), dict(base, repository="other/repo"),
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
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "qikvrt_client_decision_v1",
                          "disposition": "CONTINUE_DIAGNOSIS",
                          "next_action": None, "effect_ack_done": False,
                          "blocker": "INVALID_RECEIPT", "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
