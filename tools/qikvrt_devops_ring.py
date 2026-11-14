# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Lossless, fail-closed DevOps ring planner. No repository write authority."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

STATES = {"queued", "in_progress", "completed", "waiting", "pending", "requested"}
def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def plan(observation, previous=None):
    if not isinstance(observation, dict) or not isinstance(observation.get("repository"), str):
        raise ValueError("INVALID_OBSERVATION")
    if not isinstance(observation.get("head"), str) or len(observation["head"]) != 40:
        raise ValueError("INVALID_HEAD")
    runs = observation.get("runs")
    work = observation.get("work")
    if not isinstance(runs, list) or not isinstance(work, list):
        raise ValueError("INCOMPLETE_INVENTORY")
    seen = set()
    evidence = []
    for kind, items in (("run", runs), ("work", work)):
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), (str, int)):
                raise ValueError("INVALID_IDENTITY")
            key = (kind, str(item["id"]))
            if key in seen:
                raise ValueError("DUPLICATE_IDENTITY")
            seen.add(key)
            evidence.append({"kind": kind, "id": str(item["id"]),
                             "sha256": hashlib.sha256(canonical(item)).hexdigest(),
                             "original": item})
    evidence.sort(key=lambda e: (e["kind"], e["id"]))
    active = [r for r in runs if r.get("status") in ("queued", "in_progress", "waiting", "pending", "requested")]
    failed = [r for r in runs if r.get("status") == "completed" and r.get("conclusion") in ("failure", "timed_out", "cancelled")]
    admission = [r for r in runs if r.get("status") == "completed" and
                 r.get("conclusion") in ("action_required", "startup_failure")]
    invalid = [r for r in runs if r.get("status") not in STATES or
               (r.get("status") == "completed" and not isinstance(r.get("conclusion"), str))]
    if invalid:
        raise ValueError("UNTRUSTED_RUN_STATE")
    pending = [w for w in work if w.get("state") not in ("verified", "done", "closed")]
    # No invented execution or automatic retry: the downstream trusted consumer
    # must independently verify eligibility, dependencies and writer admission.
    tasks = [{"kind": "TEMDD_DIAGNOSE", "run_id": str(r["id"]), "status": "HOLD",
              "requires": "original failed step, exact head and causal change"}
             for r in failed]
    tasks += [{"kind": "WORKFLOW_ADMISSION_REPAIR", "run_id": str(r["id"]),
               "status": "HOLD", "requires": "original exact-head admission; no substitute rerun"}
              for r in admission]
    tasks += [{"kind": "CONTINUATION_CANDIDATE", "work_id": str(w["id"]),
               "status": "REQUIRES_ADMISSION"} for w in pending]
    tasks.sort(key=lambda t: (t["kind"], t.get("run_id", t.get("work_id", ""))))
    fingerprint = hashlib.sha256(canonical({"repository": observation["repository"],
        "head": observation["head"], "evidence": evidence, "tasks": tasks})).hexdigest()
    prior = previous if isinstance(previous, dict) else {}
    return {"schema": "qikvrt_devops_ring_lossless_v1", "repository": observation["repository"],
            "head": observation["head"], "evidence": evidence, "evidence_count": len(evidence),
            "evidence_sha256": hashlib.sha256(canonical(evidence)).hexdigest(),
            "semantic_fingerprint": fingerprint,
            "changed": fingerprint != prior.get("semantic_fingerprint"),
            "state": "ACTIVE" if active else ("WORK_PENDING" if tasks else "IDLE"),
            "tasks": tasks, "dispatch_executed": False, "effect_ack_done": False,
            "next_action": "trusted continuation consumer admission" if tasks else "next scheduled wakeup"}


def execute_roundtrip(request, feature_catalog, observations):
    """Pure synchronous roundtrip: each transition is a content-addressed journal event.

    Runtime adapters own durable persistence and actual execution. This function
    never fabricates an ACK or silently drops a worker result.
    """
    if not isinstance(request, dict) or not request.get("id") or not isinstance(request.get("payload"), dict):
        raise ValueError("INVALID_INTAKE")
    if not isinstance(feature_catalog, list) or not feature_catalog:
        raise ValueError("EMPTY_FEATURE_CATALOG")
    if not isinstance(observations, list):
        raise ValueError("INVALID_OBSERVATIONS")
    catalog = {}
    for feature in feature_catalog:
        if not isinstance(feature, dict) or not isinstance(feature.get("id"), str) or not feature.get("id"):
            raise ValueError("INVALID_FEATURE")
        if feature["id"] in catalog:
            raise ValueError("DUPLICATE_FEATURE")
        catalog[feature["id"]] = feature
    journal = []
    def record(kind, payload):
        predecessor = journal[-1]["hash"] if journal else None
        event = {"sequence": len(journal), "previous": predecessor, "kind": kind, "payload": payload}
        event["hash"] = hashlib.sha256(canonical(event)).hexdigest()
        journal.append(event)
    record("INTAKE", request)
    assignments = request["payload"].get("assignments")
    if not isinstance(assignments, list):
        raise ValueError("INVALID_ASSIGNMENTS")
    dispatched = set()
    for item in assignments:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("feature"), str):
            raise ValueError("INVALID_ASSIGNMENT")
        if item["id"] in dispatched or item["feature"] not in catalog:
            raise ValueError("DUPLICATE_OR_UNKNOWN_ASSIGNMENT")
        dispatched.add(item["id"])
        record("DELEGATION_PLANNED", {"id": item["id"], "feature": item["feature"], "input": item.get("input")})
    observed = set()
    for observation in observations:
        if not isinstance(observation, dict) or observation.get("assignment_id") not in dispatched:
            raise ValueError("UNBOUND_OBSERVATION")
        if observation["assignment_id"] in observed:
            raise ValueError("DUPLICATE_OBSERVATION")
        observed.add(observation["assignment_id"])
        record("WORKER_OBSERVATION", observation)
    unresolved = sorted(dispatched - observed)
    failed = sorted(o["assignment_id"] for o in observations if o.get("status") != "VERIFIED")
    record("CONSOLIDATION", {"unresolved": unresolved, "unverified": failed,
                              "observation_count": len(observations)})
    return {"schema": "qikvrt_synchronous_roundtrip_v1", "request_id": request["id"],
            "journal": journal, "journal_head": journal[-1]["hash"],
            "response_status": "EVIDENCE_COMPLETE" if dispatched and not unresolved and not failed else "HOLD",
            "delegation_executed": False, "effect_ack_done": False,
            "artifacts": [o.get("artifact") for o in observations if o.get("artifact") is not None]}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--observation", required=True)
    p.add_argument("--previous")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    try:
        with open(a.observation, encoding="utf-8") as f: obs = json.load(f)
        previous = None
        if a.previous:
            with open(a.previous, encoding="utf-8") as f: previous = json.load(f)
        result = plan(obs, previous)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        result = {"schema": "qikvrt_devops_ring_lossless_v1", "state": "HOLD",
                  "reason": str(exc), "dispatch_executed": False, "effect_ack_done": False}
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")
    print(result["state"])
    return 0 if result["state"] != "HOLD" else 2

if __name__ == "__main__":
    sys.exit(main())

