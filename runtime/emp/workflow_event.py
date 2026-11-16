"""Read-only EMP GitHub workflow event adapter.

Processes an authenticated GitHub Actions workflow_run event payload supplied by
GitHub Actions, persists a fail-closed decision, and emits a machine-readable
next-action record. No repository mutation or privileged dispatch is performed.
"""
import argparse
import json
from pathlib import Path
from runtime.emp.journal import admit
from runtime.emp.transition import Objective


def process(payload: dict, db_path: str) -> dict:
    run = payload.get("workflow_run")
    if not isinstance(run, dict) or not isinstance(run.get("id"), int):
        raise ValueError("workflow_run.id missing")
    if run.get("status") != "completed":
        raise ValueError("workflow_run not completed")
    repository = payload.get("repository", {}).get("full_name")
    if repository != "ingolf-lohmann/qik-vrt":
        raise ValueError("repository authority mismatch")
    conclusion = run.get("conclusion")
    if conclusion not in ("success", "failure", "cancelled", "timed_out", "action_required"):
        raise ValueError("unknown workflow conclusion")
    event_id = f"workflow_run:{run['id']}:{conclusion}"
    objective = Objective(
        objective_id=f"ci:{run['id']}",
        authorized=True,  # read-only diagnosis only, NOT effect authorization
        ci_failed=conclusion != "success",
        external_blocker="" if conclusion != "success" else "EAP verification required",
        writer_epoch=0,
    )
    result = admit(db_path, objective, event_id)
    return {"repository": repository, "event_id": event_id,
            "run_url": run.get("html_url"), "conclusion": conclusion,
            "decision": result, "effect_authorized": False,
            "effect_ack_done": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.event).read_text(encoding="utf-8"))
    result = process(payload, args.db)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
