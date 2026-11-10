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
