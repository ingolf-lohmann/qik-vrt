# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Durable, version-bound scheduling projection of an existing executor.

The registry never creates another executor or calls an external platform.
A local change is prepared, applied by the authorized adapter, then confirmed
by importing its fresh source readback. Unsupported schedules fail closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA = "qikvrt_digital_twin_scheduling_v1"
BASE = "/api/digital-twin/v1/schedules"
CONFIG_FIELDS = ("id", "title", "prompt", "schedule", "default_timezone", "timing_mode", "is_enabled")
SOURCE_FIELDS = {*CONFIG_FIELDS, "updated_at", "last_run_time", "next_run_time"}
MODES = {"exact_schedule", "flexible_schedule", "condition_watch"}
WEEKDAYS = {name: i for i, name in enumerate(("MO", "TU", "WE", "TH", "FR", "SA", "SU"))}


class ScheduleConflict(ValueError):
    """A stale or inconsistent readback must not overwrite the current state."""


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def utc(raw):
    if not isinstance(raw, str) or len(raw) > 40:
        raise ValueError("TIMEZONE_AWARE_TIMESTAMP_REQUIRED")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    if value.tzinfo is None:
        raise ValueError("TIMEZONE_AWARE_TIMESTAMP_REQUIRED")
    return value.astimezone(timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_schedule(raw, timezone_name):
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 4096 or "\r" in raw:
        raise ValueError("UNSUPPORTED_SCHEDULE")
    try:
        zone = ZoneInfo(timezone_name)
    except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("UNKNOWN_IANA_TIMEZONE") from exc
    lines = raw.splitlines()
    if len(lines) != 4 or lines[0] != "BEGIN:VEVENT" or lines[-1] != "END:VEVENT":
        raise ValueError("DTSTART_AND_RECURRING_RRULE_REQUIRED")
    start_line = re.fullmatch(r"DTSTART(?:;TZID=([^:]+))?:(\d{8}T\d{6})(Z?)", lines[1])
    if not start_line or not lines[2].startswith("RRULE:"):
        raise ValueError("UNSUPPORTED_SCHEDULE")
    tzid, date, zulu = start_line.groups()
    if (tzid and (tzid != timezone_name or zulu)) or (not tzid and not zulu):
        raise ValueError("EXPLICIT_MATCHING_TIMEZONE_REQUIRED")
    start_zone = timezone.utc if zulu else zone
    try:
        start = datetime.strptime(date, "%Y%m%dT%H%M%S").replace(tzinfo=start_zone, fold=0)
    except ValueError as exc:
        raise ValueError("INVALID_DTSTART") from exc
    if start.astimezone(timezone.utc).astimezone(start_zone).replace(tzinfo=None) != start.replace(tzinfo=None):
        raise ValueError("NONEXISTENT_DTSTART")
    rule = {}
    for field in lines[2][6:].split(";"):
        parts = field.split("=")
        if len(parts) != 2 or parts[0] in rule:
            raise ValueError("INVALID_OR_DUPLICATE_RRULE_FIELD")
        rule[parts[0]] = parts[1]
    if set(rule) - {"FREQ", "INTERVAL", "BYDAY", "BYHOUR", "BYMINUTE", "BYSECOND"}:
        raise ValueError("UNSUPPORTED_RRULE_FIELD")
    frequency = rule.get("FREQ")
    if frequency not in {"HOURLY", "DAILY", "WEEKLY"}:
        raise ValueError("UNSUPPORTED_FREQUENCY")
    for key in ("INTERVAL", "BYHOUR", "BYMINUTE", "BYSECOND"):
        if key in rule and not re.fullmatch(r"[0-9]{1,3}", rule[key]):
            raise ValueError("UNSUPPORTED_RRULE_VALUE")
    interval = int(rule.get("INTERVAL", "1"))
    hour = int(rule.get("BYHOUR", str(start.hour)))
    minute = int(rule.get("BYMINUTE", str(start.minute)))
    second = int(rule.get("BYSECOND", str(start.second)))
    if not 1 <= interval <= 366 or not 0 <= hour <= 23 or not 0 <= minute <= 59 or not 0 <= second <= 59:
        raise ValueError("RRULE_VALUE_OUT_OF_RANGE")
    if frequency == "HOURLY" and any(key in rule for key in ("BYDAY", "BYHOUR", "BYMINUTE", "BYSECOND")):
        raise ValueError("HOURLY_USES_DTSTART_PHASE_ONLY")
    weekdays = rule.get("BYDAY", "").split(",") if "BYDAY" in rule else []
    if weekdays and (frequency != "WEEKLY" or any(day not in WEEKDAYS for day in weekdays) or len(set(weekdays)) != len(weekdays)):
        raise ValueError("UNSUPPORTED_BYDAY")
    # DTSTART with Z binds recurrence to UTC, even when the executor also has
    # a non-UTC default timezone. TZID schedules retain their local clock.
    return start, start_zone, frequency, interval, hour, minute, second, {WEEKDAYS[day] for day in weekdays}


def next_due(task, after):
    """Return a planned slot, never a claim about the hosted executor's clock."""
    if not task["is_enabled"]:
        return None
    start, zone, frequency, interval, hour, minute, second, days = parse_schedule(task["schedule"], task["default_timezone"])
    after = utc(after) if isinstance(after, str) else after
    if after.tzinfo is None:
        raise ValueError("TIMEZONE_AWARE_TIMESTAMP_REQUIRED")
    after = after.astimezone(timezone.utc)
    if frequency == "HOURLY":
        anchor = start.astimezone(timezone.utc)
        slots = max(0, int((after - anchor).total_seconds() // (interval * 3600)) + 1)
        return stamp(anchor + timedelta(hours=slots * interval))
    anchor = start.astimezone(zone).date()
    first = max(anchor, after.astimezone(zone).date())
    for offset in range(7 * 366 + 8):
        day = first + timedelta(days=offset)
        if frequency == "DAILY" and (day - anchor).days % interval:
            continue
        if frequency == "WEEKLY":
            week = anchor - timedelta(days=anchor.weekday())
            if ((day - week).days // 7) % interval or day.weekday() not in (days or {anchor.weekday()}):
                continue
        candidate = datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=zone, fold=0)
        actual = candidate.astimezone(timezone.utc)
        # Skip nonexistent local slots; an ambiguous slot uses its first fold.
        if actual.astimezone(zone).replace(tzinfo=None) != candidate.replace(tzinfo=None):
            continue
        if actual >= start.astimezone(timezone.utc) and actual > after:
            return stamp(actual)
    raise ValueError("NO_SLOT_WITHIN_BOUNDED_HORIZON")


def normalize_task(task):
    if not isinstance(task, dict) or set(task) - SOURCE_FIELDS or not (set(CONFIG_FIELDS) | {"updated_at"}) <= set(task):
        raise ValueError("CLOSED_SOURCE_TASK_SCHEMA")
    if not isinstance(task["id"], str) or not re.fullmatch(r"[0-9a-f]{32}", task["id"]):
        raise ValueError("INVALID_EXECUTOR_TASK_ID")
    for field, maximum in (("title", 256), ("prompt", 131072)):
        if not isinstance(task[field], str) or not 1 <= len(task[field].encode("utf-8")) <= maximum:
            raise ValueError("INVALID_" + field.upper())
    if not isinstance(task["is_enabled"], bool) or not isinstance(task["timing_mode"], str) or task["timing_mode"] not in MODES:
        raise ValueError("INVALID_EXECUTOR_CONFIGURATION")
    parse_schedule(task["schedule"], task["default_timezone"])
    utc(task["updated_at"])
    value = dict(task)
    for field in ("last_run_time", "next_run_time"):
        value.setdefault(field, None)
        if value[field] is not None:
            utc(value[field])
    return value


def config(task):
    return {key: task[key] for key in CONFIG_FIELDS}


class SchedulingStore:
    """Private per-repository/principal SQLite state with atomic CAS writes."""

    def __init__(self, root, repository, principal, *, namespace=None):
        root = Path(root).absolute()
        if not repository or not principal or root.is_symlink() or not root.is_dir():
            raise ValueError("EXACT_SCHEDULER_SCOPE_REQUIRED")
        parent = root
        for part in (".qikvrt", "api", "schedules"):
            parent = parent / part
            parent.mkdir(mode=0o700, exist_ok=True)
            if parent.is_symlink() or not parent.is_dir():
                raise ValueError("UNSAFE_SCHEDULE_STATE_DIRECTORY")
        scope = repository + "\n" + principal
        if namespace is not None:
            scope += "\n" + namespace
        key = hashlib.sha256(scope.encode()).hexdigest()
        self.path = parent / (key + ".sqlite3")
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            status = self.path.lstat()
            if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1 or stat.S_IMODE(status.st_mode) != 0o600:
                raise ValueError("UNSAFE_SCHEDULE_DATABASE")
        else:
            os.close(fd)
        self.repository = repository
        self.principal = principal
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schedules (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, task TEXT NOT NULL, observed TEXT NOT NULL, pending TEXT)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level="IMMEDIATE")
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def projection(self, row):
        task = json.loads(row["task"])
        return {"schema": SCHEMA, "task": task, "revision": row["revision"],
                "configuration_sha256": digest(config(task)), "observed_at": row["observed"],
                "state": "AWAIT_EXECUTOR_READBACK" if row["pending"] else "SOURCE_SNAPSHOT_STORED",
                "pending_configuration_sha256": digest(json.loads(row["pending"])) if row["pending"] else None,
                "executor": "chatgpt_automations", "local_dispatch_authorized": False,
                "continuous_bridge_verified": False, "effect_ack_done": False}

    def read(self, task_id=None):
        with self.connect() as db:
            if task_id is None:
                return {"schema": SCHEMA, "repository": self.repository, "principal": self.principal,
                        "tasks": [self.projection(row) for row in db.execute("SELECT * FROM schedules ORDER BY id")],
                        "effect_ack_done": False}
            row = db.execute("SELECT * FROM schedules WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError("SCHEDULE_NOT_FOUND")
            return self.projection(row)

    @staticmethod
    def require_revision(expected, actual):
        if isinstance(expected, bool) or not isinstance(expected, int) or expected != actual:
            raise ScheduleConflict("STALE_EXACT_SCHEDULE_REVISION")

    def reconcile(self, *, expected_revision, observed_at, task):
        task = normalize_task(task)
        observed = utc(observed_at)
        now = datetime.now(timezone.utc)
        if observed > now + timedelta(seconds=30) or now - observed > timedelta(minutes=5) or utc(task["updated_at"]) > observed:
            raise ScheduleConflict("FRESH_SOURCE_OBSERVATION_REQUIRED")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM schedules WHERE id=?", (task["id"],)).fetchone()
            self.require_revision(expected_revision, row["revision"] if row else 0)
            previous = json.loads(row["task"]) if row else None
            if previous is not None:
                old_time, new_time = utc(previous["updated_at"]), utc(task["updated_at"])
                if new_time < old_time or observed < utc(row["observed"]):
                    raise ScheduleConflict("STALE_EXECUTOR_READBACK")
                if new_time == old_time and config(previous) != config(task):
                    raise ScheduleConflict("EXECUTOR_VERSION_COLLISION")
                if row["pending"] and digest(config(task)) != digest(json.loads(row["pending"])):
                    raise ScheduleConflict("PREPARED_CHANGE_READBACK_MISMATCH")
            elif db.execute("SELECT COUNT(*) FROM schedules").fetchone()[0] >= 1000:
                raise ValueError("SCHEDULE_CAPACITY_EXCEEDED")
            changed = previous is None or config(previous) != config(task) or bool(row["pending"])
            revision = (row["revision"] if row else 0) + int(changed)
            db.execute("INSERT OR REPLACE INTO schedules VALUES (?,?,?,?,NULL)",
                       (task["id"], revision, canonical(task), stamp(observed)))
        result = self.read(task["id"])
        if result["task"] != task or result["revision"] != revision:
            raise ScheduleConflict("LOCAL_POST_WRITE_READBACK_CHANGED")
        result["readback_scope"] = "provided_source_snapshot_and_local_registry"
        result["remote_snapshot_authenticity"] = "caller_responsibility"
        return result

    def prepare(self, *, task_id, expected_revision, changes):
        allowed = set(CONFIG_FIELDS) - {"id", "timing_mode"}
        if not isinstance(changes, dict) or not changes or set(changes) - allowed:
            raise ValueError("CLOSED_SCHEDULE_CHANGE_SCHEMA")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM schedules WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError("SCHEDULE_NOT_FOUND")
            self.require_revision(expected_revision, row["revision"])
            if row["pending"]:
                raise ScheduleConflict("PREPARED_CHANGE_ALREADY_PENDING")
            task = json.loads(row["task"])
            desired = normalize_task(dict(task, **changes))
            if config(desired) == config(task):
                raise ValueError("NO_CONFIGURATION_CHANGE")
            revision = row["revision"] + 1
            db.execute("UPDATE schedules SET revision=?,pending=? WHERE id=?",
                       (revision, canonical(config(desired)), task_id))
        return {"schema": SCHEMA, "task_id": task_id, "revision": revision,
                "state": "AWAIT_EXECUTOR_READBACK", "desired_configuration_sha256": digest(config(desired)),
                "executor_operation": {"tool": "automations.update", "arguments": {"jawbone_id": task_id, **changes}},
                "executor_mutation_performed": False, "effect_ack_done": False}

    def due(self, *, at):
        now = utc(at)
        tasks = []
        for item in self.read()["tasks"]:
            task = item["task"]
            slot = None if item["state"] == "AWAIT_EXECUTOR_READBACK" else next_due(task, now)
            tasks.append({"task_id": task["id"], "revision": item["revision"],
                          "planned_next_slot_utc": slot, "hosted_next_run_time": task["next_run_time"],
                          "executor": item["executor"], "local_dispatch_authorized": False})
        return {"schema": SCHEMA, "planned_at": stamp(now), "tasks": tasks, "effect_ack_done": False}


def main():
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("action", choices=("read", "reconcile", "prepare", "plan"))
    parser.add_argument("--task-id")
    args = parser.parse_args()
    try:
        store = SchedulingStore(args.root, args.repository, args.principal)
        if args.action == "read":
            value = store.read(args.task_id)
        else:
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError("DUPLICATE_JSON_FIELD")
                    value[key] = item
                return value
            def reject_constant(value):
                raise ValueError("NONFINITE_JSON_VALUE")
            raw = sys.stdin.buffer.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("REQUEST_TOO_LARGE")
            body = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject_constant)
            methods = {"reconcile": ({"expected_revision", "observed_at", "task"}, store.reconcile),
                       "prepare": ({"task_id", "expected_revision", "changes"}, store.prepare),
                       "plan": ({"at"}, store.due)}
            fields, operation = methods[args.action]
            if not isinstance(body, dict) or set(body) != fields:
                raise ValueError("CLOSED_SCHEDULE_REQUEST_SCHEMA")
            value = operation(**body)
        print(canonical(value))
        return 0
    except (ValueError, KeyError, OSError, sqlite3.Error, TypeError) as exc:
        print(canonical({"schema": SCHEMA, "state": "HOLD", "reason": str(exc), "effect_ack_done": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
