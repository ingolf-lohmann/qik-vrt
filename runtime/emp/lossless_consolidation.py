"""Lossless EMP event consolidation: append-only, ordered, content-addressed.

A materialized summary is a view, never a substitute for source events.
SQLite transactions serialize writers. Every original payload is retained as
bytes, and the hash chain makes omission, reordering or alteration detectable
during full replay. This is not a cryptographic signature or EAP acknowledgement.
"""
import hashlib
import json
import sqlite3
from pathlib import Path


def _digest(previous: str, event_id: str, payload: bytes) -> str:
    h = hashlib.sha256()
    for part in (previous.encode("ascii"), event_id.encode("utf-8"), payload):
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return h.hexdigest()


def append(db_path: str, stream: str, event_id: str, payload: bytes) -> dict:
    if not stream or not event_id or not isinstance(payload, bytes):
        raise ValueError("stream, event_id and byte payload required")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=10, isolation_level=None) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS emp_lossless_events (
                stream TEXT NOT NULL, sequence INTEGER NOT NULL,
                event_id TEXT NOT NULL, payload BLOB NOT NULL,
                previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL,
                PRIMARY KEY(stream, sequence), UNIQUE(stream, event_id))""")
            prior = db.execute(
                "SELECT sequence,payload,event_hash FROM emp_lossless_events "
                "WHERE stream=? AND event_id=?", (stream, event_id)).fetchone()
            if prior:
                if bytes(prior[1]) != payload:
                    raise ValueError("event id collision with different payload")
                result = {"sequence": prior[0], "event_hash": prior[2], "duplicate": True}
            else:
                last = db.execute(
                    "SELECT sequence,event_hash FROM emp_lossless_events "
                    "WHERE stream=? ORDER BY sequence DESC LIMIT 1", (stream,)).fetchone()
                sequence = last[0] + 1 if last else 1
                previous = last[1] if last else "0" * 64
                digest = _digest(previous, event_id, payload)
                db.execute("INSERT INTO emp_lossless_events VALUES (?,?,?,?,?,?)",
                           (stream, sequence, event_id, payload, previous, digest))
                result = {"sequence": sequence, "event_hash": digest, "duplicate": False}
            db.execute("COMMIT")
            return result
        except BaseException:
            db.execute("ROLLBACK")
            raise


def replay(db_path: str, stream: str) -> dict:
    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT sequence,event_id,payload,previous_hash,event_hash "
            "FROM emp_lossless_events WHERE stream=? ORDER BY sequence", (stream,)).fetchall()
    previous = "0" * 64
    events = []
    for expected, (sequence, event_id, payload, prev, digest) in enumerate(rows, 1):
        payload = bytes(payload)
        if sequence != expected or prev != previous or digest != _digest(prev, event_id, payload):
            raise ValueError("lossless chain verification failed")
        events.append({"sequence": sequence, "event_id": event_id,
                       "payload_hex": payload.hex(), "event_hash": digest})
        previous = digest
    return {"stream": stream, "count": len(events), "head": previous,
            "events": events, "effect_ack_done": False}


def consolidate(db_path: str, stream: str) -> dict:
    """Deterministic compact index retaining replay access to every original byte."""
    verified = replay(db_path, stream)
    return {"stream": stream, "count": verified["count"], "head": verified["head"],
            "event_ids": [e["event_id"] for e in verified["events"]],
            "lossless_replay_required": True, "effect_ack_done": False}
