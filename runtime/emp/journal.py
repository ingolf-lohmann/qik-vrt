"""EMP durable, fenced event admission. No external side effects.

SQLite serializes writers and persists decisions; an effect executor must be
integrated separately with authorization and independent EAP readback.
"""
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from .transition import Objective, transition


def admit(db_path: str, objective: Objective, event_id: str) -> dict:
    if not objective.objective_id or not event_id:
        raise ValueError("objective_id and event_id required")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=10, isolation_level=None) as db:
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS emp_events (
                objective_id TEXT NOT NULL, event_id TEXT NOT NULL,
                writer_epoch INTEGER NOT NULL, state TEXT NOT NULL,
                next_action TEXT NOT NULL, reason TEXT NOT NULL,
                objective_json TEXT NOT NULL,
                PRIMARY KEY(objective_id,event_id))""")
            prior = db.execute(
                "SELECT state,next_action,reason FROM emp_events WHERE objective_id=? AND event_id=?",
                (objective.objective_id, event_id)).fetchone()
            if prior:
                result = dict(zip(("state", "next_action", "reason"), prior))
                result["duplicate"] = True
            else:
                latest = db.execute(
                    "SELECT MAX(writer_epoch) FROM emp_events WHERE objective_id=?",
                    (objective.objective_id,)).fetchone()[0]
                if latest is not None and objective.writer_epoch < latest:
                    raise ValueError("stale writer epoch")
                decision = transition(objective, event_id)
                result = {"state": decision.state.value,
                          "next_action": decision.next_action,
                          "reason": decision.reason, "duplicate": False}
                db.execute(
                    "INSERT INTO emp_events VALUES (?,?,?,?,?,?,?)",
                    (objective.objective_id, event_id, objective.writer_epoch,
                     result["state"], result["next_action"], result["reason"],
                     json.dumps(asdict(objective), sort_keys=True)))
            db.execute("COMMIT")
            return result
        except BaseException:
            db.execute("ROLLBACK")
            raise
