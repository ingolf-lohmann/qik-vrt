"""Reference EMP-to-lossless-evidence bridge; no production EAP claim.

A single SQLite transaction is not shared with the existing EMP journal:
this adapter therefore records intent BEFORE calling admission and records
outcome AFTER. Interrupted outcomes remain explicitly unresolved for replay.
"""
import json
from dataclasses import asdict
from .journal import admit
from .lossless_consolidation import append, replay
from .transition import Objective


def submit(db_path: str, objective: Objective, event_id: str) -> dict:
    stream = "emp:" + objective.objective_id
    intent = json.dumps({"event_id": event_id, "objective": asdict(objective)},
                        sort_keys=True, separators=(",", ":")).encode("utf-8")
    append(db_path, stream, event_id + ":intent", intent)
    result = admit(db_path, objective, event_id)
    outcome = json.dumps({"event_id": event_id, "decision": {k: v for k, v in result.items() if k != "duplicate"}},
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    append(db_path, stream, event_id + ":outcome", outcome)
    return {"decision": result, "evidence": replay(db_path, stream),
            "effect_ack_done": False}
