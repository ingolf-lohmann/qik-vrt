"""Fail-closed observer for GitHub writer/successor runs.

The observer cannot keep a ChatGPT request alive. It persists a typed handoff
so a new request or repository worker can resume without claiming completion.
"""
import argparse
import json
from pathlib import Path

TERMINAL = {"success", "failure", "cancelled", "skipped", "timed_out", "action_required"}
ACTIVE = {"queued", "pending", "waiting", "requested", "in_progress"}


def observe(previous, snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be object")
    required = ("repository", "writer_id", "work_unit_id", "head_sha", "runs")
    if any(k not in snapshot for k in required):
        raise ValueError("incomplete snapshot")
    if snapshot["repository"] != "ingolf-lohmann/qik-vrt":
        raise ValueError("authority mismatch")
    if not isinstance(snapshot["head_sha"], str) or len(snapshot["head_sha"]) != 40 or any(c not in "0123456789abcdef" for c in snapshot["head_sha"]):
        raise ValueError("invalid head")
    for key in ("writer_id", "work_unit_id"):
        if not isinstance(snapshot[key], str) or not snapshot[key].strip():
            raise ValueError("invalid identity")
    if previous is not None:
        for key in ("repository", "writer_id", "work_unit_id"):
            if previous.get(key) != snapshot[key]:
                raise ValueError("same-writer handoff mismatch")
        if previous.get("state") == "DONE":
            raise ValueError("terminal predecessor cannot be silently reopened")
        if previous.get("head_sha") != snapshot["head_sha"] and previous.get("successor_head_sha") != snapshot["head_sha"]:
            raise ValueError("unverified successor HEAD transition")
    runs = snapshot["runs"]
    if not isinstance(runs, list) or not runs:
        raise ValueError("missing workflow evidence")
    ids = set()
    active = []
    blocked = []
    for run in runs:
        if not isinstance(run, dict) or type(run.get("id")) is not int or run["id"] <= 0 or run["id"] in ids:
            raise ValueError("invalid or duplicate run")
        ids.add(run["id"])
        status, conclusion = run.get("status"), run.get("conclusion")
        if status in ACTIVE and conclusion is None:
            active.append(run["id"])
        elif status == "completed" and conclusion in TERMINAL:
            if conclusion != "success":
                blocked.append({"id": run["id"], "conclusion": conclusion})
        else:
            raise ValueError("unrecognized workflow state")
    # Successful workflow completion is not a product-effect acknowledgement.
    return {
        "schema": "qikvrt_writer_observation_v1",
        "repository": snapshot["repository"],
        "writer_id": snapshot["writer_id"],
        "work_unit_id": snapshot["work_unit_id"],
        "head_sha": snapshot["head_sha"],
        "state": "RUNNING" if active else "BLOCKED",
        "active_run_ids": active,
        "blocked_runs": blocked,
        "next_action": "READBACK" if active else "RECONCILE_SUCCESSOR",
        "effect_ack_done": False,
        "requires_independent_verification": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--previous")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text())
    previous = json.loads(Path(args.previous).read_text()) if args.previous else None
    result = observe(previous, snapshot)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    temporary.replace(target)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
