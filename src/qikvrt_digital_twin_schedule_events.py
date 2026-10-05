# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Repository-native schedule events; no network calls or job execution.

Reuse the existing private SQLite projection store. Native events add an
append-only CAS ledger, explicit civil-time policies and scoped sync evidence.
Source subjects and connector observations are supplied bindings, not attestations.
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import zoneinfo

try:  # Package import and the existing API shim's direct -S invocation.
    from .qikvrt_digital_twin_scheduling import SchedulingStore, ScheduleConflict, canonical, digest, stamp
except ImportError:
    from qikvrt_digital_twin_scheduling import SchedulingStore, ScheduleConflict, canonical, digest, stamp

BASE = "/api/digital-twin/v1/schedule-events"
SCHEMA = "qikvrt_digital_twin_schedule_events_v1"
OPERATION_SCHEMA = "qikvrt_schedule_operation_v1"
SYNC_SCHEMA = "qikvrt_schedule_sync_receipt_v1"
SNAPSHOT_SCHEMA = "qikvrt_schedule_snapshot_v1"
MAX_EVENTS = 1000
MAX_OPERATIONS = 10000
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


def closed(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("CLOSED_" + label + "_SCHEMA")
    return value


def identifier(value, label="IDENTITY", size=64):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{" + str(size) + "}", value) is None:
        raise ValueError("INVALID_" + label)
    return value


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("INVALID_" + label)
    return value


def text(value, limit, label):
    if not isinstance(value, str) or not 1 <= len(value.encode("utf-8")) <= limit:
        raise ValueError("INVALID_" + label)
    return value


def json_data(value, depth=0):
    if depth > 20:
        raise ValueError("JSON_DEPTH_EXCEEDED")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        integer(value, -(2**63), 2**63 - 1, "JSON_INTEGER")
    elif isinstance(value, str):
        if len(value.encode("utf-8")) > 131072:
            raise ValueError("JSON_STRING_TOO_LARGE")
    elif isinstance(value, (dict, list)):
        if len(value) > 10000:
            raise ValueError("JSON_CONTAINER_TOO_LARGE")
        if isinstance(value, dict):
            for key in value:
                text(key, 256, "JSON_KEY")
        for item in value.values() if isinstance(value, dict) else value:
            json_data(item, depth + 1)
    else:
        raise ValueError("NONCANONICAL_JSON_TYPE")


def decode(raw, *, canonical_required=False):
    if not isinstance(raw, bytes) or len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("INVALID_JSON_BYTES_OR_SIZE")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def reject(value):
        raise ValueError("NONCANONICAL_JSON_NUMBER")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                           parse_float=reject, parse_constant=reject)
        json_data(value)
        if canonical_required and canonical(value).encode("utf-8") != raw:
            raise ValueError("NONCANONICAL_SNAPSHOT_BYTES")
        return value
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("INVALID_JSON_ENCODING_OR_DEPTH") from exc


def identity(kind, namespace, key):
    """Stable, domain-separated identity independent of mutable configuration."""
    if kind not in {"event", "operation", "receipt"}:
        raise ValueError("INVALID_IDENTITY_KIND")
    return digest({"schema": "qikvrt_schedule_identity_v1", "kind": kind,
                   "namespace": text(namespace, 256, "NAMESPACE"), "key": text(key, 256, "KEY")})


def subject(value):
    closed(value, {"repository", "role", "head", "tree"}, "SUBJECT")
    if not isinstance(value["repository"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", value["repository"]):
        raise ValueError("INVALID_SUBJECT_REPOSITORY")
    if value["role"] not in ("AUTHORITY", "MIRROR"):
        raise ValueError("INVALID_SUBJECT_ROLE")
    identifier(value["head"], "HEAD", 40)
    identifier(value["tree"], "TREE", 40)
    return dict(value)


def instant(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError("CANONICAL_UTC_SECONDS_REQUIRED")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def zone_binding(key):
    """Load and hash the same TZif bytes, bypassing ZoneInfo's mutable cache."""
    if not isinstance(key, str) or not re.fullmatch(r"(?:UTC|[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+)+)", key) or key.startswith(("posix/", "right/")):
        raise ValueError("INVALID_IANA_TIMEZONE_KEY")
    import hashlib
    for base in zoneinfo.TZPATH:
        path = Path(base) / key
        if path.is_file():
            if not path.resolve().is_relative_to(Path(base).resolve()):
                raise ValueError("TIMEZONE_OUTSIDE_PROVIDER")
            with path.open("rb") as stream:
                raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024 or not raw.startswith(b"TZif"):
                raise ValueError("INVALID_TZIF_PROVIDER")
            return zoneinfo.ZoneInfo.from_file(io.BytesIO(raw), key=key), hashlib.sha256(raw).hexdigest()
    raise ValueError("EXACT_TZIF_PROVIDER_UNAVAILABLE")


def civil(local, zone, fold):
    if not isinstance(local, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", local):
        raise ValueError("CANONICAL_LOCAL_SECONDS_REQUIRED")
    integer(fold, 0, 1, "FOLD")
    candidate = datetime.strptime(local, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=zone, fold=fold)
    restored = candidate.astimezone(timezone.utc).astimezone(zone)
    if restored.replace(tzinfo=None) != candidate.replace(tzinfo=None):
        raise ValueError("NONEXISTENT_LOCAL_TIME")
    if restored.fold != fold:
        raise ValueError("NONCANONICAL_FOLD_FOR_UNAMBIGUOUS_TIME")
    return candidate


def time_binding(local, timezone_name, fold=0):
    zone, sha = zone_binding(timezone_name)
    candidate = civil(local, zone, fold)
    return {"local": local, "timezone": timezone_name, "fold": fold,
            "utc": stamp(candidate), "tzif_sha256": sha}


def validate_value(value):
    closed(value, {"title", "payload", "enabled", "start", "recurrence"}, "SCHEDULE_VALUE")
    text(value["title"], 256, "TITLE")
    # Reserve depth for ledger and sync-readback envelopes in a full snapshot.
    json_data(value["payload"], depth=8)
    if len(canonical(value["payload"]).encode("utf-8")) > 131072:
        raise ValueError("SCHEDULE_PAYLOAD_TOO_LARGE")
    if type(value["enabled"]) is not bool:
        raise ValueError("BOOLEAN_ENABLED_REQUIRED")
    start = closed(value["start"], {"local", "timezone", "fold", "utc", "tzif_sha256"}, "START")
    identifier(start["tzif_sha256"], "TZIF_HASH")
    actual = time_binding(start["local"], start["timezone"], start["fold"])
    if actual != start:
        raise ValueError("TIME_BINDING_OR_TZIF_DRIFT")
    recurrence = value["recurrence"]
    if recurrence is not None:
        closed(recurrence, {"frequency", "interval", "weekdays", "gap_policy", "fold_policy"}, "RECURRENCE")
        if recurrence["frequency"] not in ("HOURLY", "DAILY", "WEEKLY"):
            raise ValueError("UNSUPPORTED_RECURRENCE_FREQUENCY")
        integer(recurrence["interval"], 1, 366, "INTERVAL")
        days = recurrence["weekdays"]
        if not isinstance(days, list):
            raise ValueError("CANONICAL_WEEKDAY_LIST_REQUIRED")
        for day in days:
            integer(day, 0, 6, "WEEKDAY")
        if sorted(set(days)) != days or (bool(days) != (recurrence["frequency"] == "WEEKLY")):
            raise ValueError("CANONICAL_WEEKDAY_LIST_REQUIRED")
        if recurrence["gap_policy"] != "SKIP" or recurrence["fold_policy"] not in ("FIRST", "SECOND"):
            raise ValueError("EXPLICIT_DST_POLICIES_REQUIRED")
    return decode(canonical(value).encode("utf-8"))


def next_slot(value, after):
    """Plan one future slot. It is neither a dispatch nor an execution receipt."""
    value = validate_value(value)
    now = instant(after)
    if not value["enabled"]:
        return None
    start = instant(value["start"]["utc"])
    rule = value["recurrence"]
    if rule is None:
        return stamp(start) if start > now else None
    interval = rule["interval"]
    if rule["frequency"] == "HOURLY":
        slots = max(0, int((now - start).total_seconds() // (3600 * interval)) + 1)
        return stamp(start + timedelta(hours=slots * interval))
    zone, _ = zone_binding(value["start"]["timezone"])
    local_start = start.astimezone(zone)
    anchor = local_start.date()
    first = max(anchor, now.astimezone(zone).date())
    for offset in range(7 * 366 + 8):
        day = first + timedelta(days=offset)
        if rule["frequency"] == "DAILY" and (day - anchor).days % interval:
            continue
        if rule["frequency"] == "WEEKLY":
            monday = anchor - timedelta(days=anchor.weekday())
            if ((day - monday).days // 7) % interval or day.weekday() not in rule["weekdays"]:
                continue
        candidate = datetime.combine(day, local_start.time().replace(tzinfo=None)).replace(tzinfo=zone)
        # SECOND applies only to ambiguous slots; ordinary slots have fold=0.
        second = candidate.replace(fold=1)
        if rule["fold_policy"] == "SECOND" and candidate.utcoffset() != second.utcoffset():
            candidate = second
        actual = candidate.astimezone(timezone.utc)
        if actual.astimezone(zone).replace(tzinfo=None) != candidate.replace(tzinfo=None):
            continue
        if actual >= start and actual > now:
            return stamp(actual)
    raise ValueError("NO_SLOT_WITHIN_BOUNDED_HORIZON")


def operation(value):
    closed(value, {"schema", "operation_id", "event_id", "kind", "expected_version", "value"}, "OPERATION")
    if value["schema"] != OPERATION_SCHEMA or value["kind"] not in ("create", "update", "delete"):
        raise ValueError("UNSUPPORTED_OPERATION")
    identifier(value["event_id"], "EVENT_ID")
    identifier(value["operation_id"], "OPERATION_ID")
    integer(value["expected_version"], 0, 2**63 - 2, "EXPECTED_VERSION")
    if value["kind"] == "delete":
        if value["value"] is not None:
            raise ValueError("DELETE_VALUE_MUST_BE_NULL")
    else:
        validate_value(value["value"])
    return decode(canonical(value).encode("utf-8"))


def successor(request, previous, source, committed_at):
    actual = previous["version"] if previous else 0
    if request["expected_version"] != actual:
        raise ScheduleConflict("STALE_EXPECTED_EVENT_VERSION")
    if request["kind"] == "create":
        if previous is not None:
            raise ScheduleConflict("EVENT_ID_ALREADY_USED_OR_TOMBSTONED")
    elif previous is None or previous["deleted"]:
        raise ScheduleConflict("LIVE_EVENT_REQUIRED")
    instant(committed_at)
    if previous and committed_at < previous["modified_at_utc"]:
        raise ScheduleConflict("NONMONOTONIC_COMMIT_TIME")
    return {"schema": SCHEMA, "event_id": request["event_id"], "version": actual + 1,
            "deleted": request["kind"] == "delete", "value": request["value"],
            "last_operation_id": request["operation_id"], "last_subject": source,
            "modified_at_utc": committed_at}


def event_order(event):
    return (event["deleted"], event["value"]["start"]["utc"] if not event["deleted"] else "", event["event_id"])


def target_binding(value):
    if not isinstance(value, dict):
        raise ValueError("INVALID_SYNC_TARGET")
    if value.get("kind") == "repository":
        closed(value, {"kind", "subject"}, "REPOSITORY_TARGET")
        subject(value["subject"])
    elif value.get("kind") == "connector":
        closed(value, {"kind", "connector_id", "resource_id"}, "CONNECTOR_TARGET")
        for field in ("connector_id", "resource_id"):
            text(value[field], 256, field.upper())
    else:
        raise ValueError("UNSUPPORTED_SYNC_TARGET")
    return value


def sync_receipt(value, event, source, *, now=None):
    closed(value, {"schema", "receipt_id", "source_subject", "target", "event_id", "event_version",
                  "event_sha256", "transport_ack", "observation"}, "SYNC_RECEIPT")
    if value["schema"] != SYNC_SCHEMA or type(value["transport_ack"]) is not bool:
        raise ValueError("INVALID_SYNC_RECEIPT")
    identifier(value["receipt_id"], "RECEIPT_ID")
    identifier(value["event_id"], "EVENT_ID")
    identifier(value["event_sha256"], "EVENT_HASH")
    integer(value["event_version"], 1, 2**63 - 1, "EVENT_VERSION")
    if subject(value["source_subject"]) != source or value["event_id"] != event["event_id"] or value["event_version"] != event["version"] or value["event_sha256"] != digest(event):
        raise ScheduleConflict("SYNC_EXACT_SUBJECT_OR_EVENT_MISMATCH")
    target = target_binding(value["target"])
    if target["kind"] == "repository" and target["subject"] == source:
        raise ValueError("DISTINCT_SOURCE_AND_TARGET_REQUIRED")
    observation = value["observation"]
    if observation is not None:
        closed(observation, {"observed_at_utc", "target_revision", "readback"}, "SYNC_OBSERVATION")
        text(observation["target_revision"], 256, "TARGET_REVISION")
        observed = instant(observation["observed_at_utc"])
        if canonical(observation["readback"]) != canonical(event) or observed < instant(event["modified_at_utc"]):
            raise ScheduleConflict("CONTRADICTORY_POST_EFFECT_READBACK")
        if now is not None and (observed > now + timedelta(seconds=30) or now - observed > timedelta(seconds=300)):
            raise ScheduleConflict("FRESH_SYNC_OBSERVATION_REQUIRED")
    return decode(canonical(value).encode("utf-8"))


def validate_snapshot(raw):
    packet = closed(decode(raw, canonical_required=True), {"schema", "subject", "events", "operations", "sync_receipts"}, "SNAPSHOT")
    if packet["schema"] != SNAPSHOT_SCHEMA:
        raise ValueError("UNSUPPORTED_SNAPSHOT_VERSION")
    source = subject(packet["subject"])
    for field, limit in (("events", MAX_EVENTS), ("operations", MAX_OPERATIONS), ("sync_receipts", MAX_OPERATIONS)):
        if not isinstance(packet[field], list) or len(packet[field]) > limit:
            raise ValueError("SNAPSHOT_CAPACITY_EXCEEDED")
    events, versions, operation_ids = {}, {}, set()
    for sequence, record in enumerate(packet["operations"], 1):
        closed(record, {"sequence", "subject", "request", "before_sha256", "event", "committed_at_utc"}, "LEDGER_RECORD")
        integer(record["sequence"], sequence, sequence, "LEDGER_SEQUENCE")
        bound = subject(record["subject"])
        if (bound["repository"], bound["role"]) != (source["repository"], source["role"]):
            raise ScheduleConflict("CROSS_POLE_LEDGER_REPLAY_FORBIDDEN")
        request = operation(record["request"])
        if request["operation_id"] in operation_ids:
            raise ScheduleConflict("DUPLICATE_OPERATION_ID")
        previous = events.get(request["event_id"])
        if record["before_sha256"] != (digest(previous) if previous else None):
            raise ScheduleConflict("BROKEN_REPLAY_PREDECESSOR_HASH")
        event = successor(request, previous, bound, record["committed_at_utc"])
        if canonical(event) != canonical(record["event"]):
            raise ScheduleConflict("REPLAY_SUCCESSOR_MISMATCH")
        events[event["event_id"]] = event
        versions[(event["event_id"], event["version"])] = event
        operation_ids.add(request["operation_id"])
    if len(events) > MAX_EVENTS or canonical(sorted(events.values(), key=event_order)) != canonical(packet["events"]):
        raise ScheduleConflict("NONCANONICAL_OR_DUPLICATE_EVENT_ORDER")
    receipt_ids, revisions = set(), {}
    if any(not isinstance(r, dict) for r in packet["sync_receipts"]):
        raise ValueError("INVALID_SYNC_RECEIPT")
    if sorted(packet["sync_receipts"], key=lambda r: str(r.get("receipt_id", ""))) != packet["sync_receipts"]:
        raise ValueError("NONCANONICAL_RECEIPT_ORDER")
    for receipt in packet["sync_receipts"]:
        if not isinstance(receipt, dict):
            raise ValueError("INVALID_SYNC_RECEIPT")
        event = versions.get((receipt.get("event_id"), receipt.get("event_version")))
        if event is None:
            raise ScheduleConflict("UNBOUND_REPLAY_SYNC_RECEIPT")
        bound = subject(receipt.get("source_subject"))
        if (bound["repository"], bound["role"]) != (source["repository"], source["role"]):
            raise ScheduleConflict("CROSS_POLE_RECEIPT_REPLAY_FORBIDDEN")
        sync_receipt(receipt, event, bound)
        if receipt["receipt_id"] in receipt_ids:
            raise ScheduleConflict("DUPLICATE_RECEIPT_ID")
        receipt_ids.add(receipt["receipt_id"])
        _check_target_revision(receipt, revisions)
    return packet


def _check_target_revision(receipt, revisions):
    observation = receipt["observation"]
    if observation is not None:
        key = (digest(receipt["target"]), observation["target_revision"])
        if key in revisions and revisions[key] != receipt["event_sha256"]:
            raise ScheduleConflict("CONTRADICTORY_TARGET_REVISION")
        revisions[key] = receipt["event_sha256"]


class ScheduleEventStore(SchedulingStore):
    """Atomic private native events, isolated by repository/principal/role."""

    def __init__(self, root, source_subject, principal):
        self._subject = subject(source_subject)
        # A role switch cannot inherit the old role's events or evidence.
        super().__init__(root, self.subject["repository"], principal,
                         namespace="native-events-v1:" + self.subject["role"])
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS schedule_events (id TEXT PRIMARY KEY, event TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS schedule_operations (sequence INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, record TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS schedule_sync_receipts (id TEXT PRIMARY KEY, receipt TEXT NOT NULL)")

    @property
    def subject(self):
        return dict(self._subject)

    def _events(self, db):
        return sorted((json.loads(r[0]) for r in db.execute("SELECT event FROM schedule_events")), key=event_order)

    def _receipts(self, db):
        return [json.loads(r[0]) for r in db.execute("SELECT receipt FROM schedule_sync_receipts ORDER BY id")]

    def _packet(self, db):
        return {"schema": SNAPSHOT_SCHEMA, "subject": self.subject, "events": self._events(db),
                "operations": [json.loads(r[0]) for r in db.execute("SELECT record FROM schedule_operations ORDER BY sequence")],
                "sync_receipts": self._receipts(db)}

    def _require_snapshot_capacity(self, db):
        if len(canonical(self._packet(db)).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("SNAPSHOT_CAPACITY_EXCEEDED")

    def _event(self, db, event_id):
        row = db.execute("SELECT event FROM schedule_events WHERE id=?", (event_id,)).fetchone()
        if row is None:
            raise KeyError("SCHEDULE_EVENT_NOT_FOUND")
        return json.loads(row[0])

    def read(self, event_id=None):
        if event_id is not None:
            identifier(event_id, "EVENT_ID")
        with self.connect() as db:
            db.execute("BEGIN")
            events = [self._event(db, event_id)] if event_id is not None else self._events(db)
            active = {e["event_id"]: e for e in events}
            receipts = [r for r in self._receipts(db) if r["source_subject"] == self.subject
                        and r["event_id"] in active and r["event_version"] == active[r["event_id"]]["version"]
                        and r["event_sha256"] == digest(active[r["event_id"]])]
        return {"schema": SCHEMA, "subject": self.subject, "events": events, "sync_receipts": receipts,
                "connector_observation_authenticity_verified": False, "pole_equality_claim": False,
                "predecessor_evidence_transfer": False, "external_effect_verified": False, "effect_ack_done": False}

    def apply(self, raw_request):
        request = operation(raw_request)
        replay = False
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT record FROM schedule_operations WHERE id=?", (request["operation_id"],)).fetchone()
            if prior is not None:
                record = json.loads(prior[0])
                if digest(record["request"]) != digest(request):
                    raise ScheduleConflict("OPERATION_ID_CONTENT_COLLISION")
                replay = True
            else:
                if db.execute("SELECT COUNT(*) FROM schedule_operations").fetchone()[0] >= MAX_OPERATIONS:
                    raise ValueError("OPERATION_CAPACITY_EXCEEDED")
                row = db.execute("SELECT event FROM schedule_events WHERE id=?", (request["event_id"],)).fetchone()
                previous = json.loads(row[0]) if row else None
                if previous is None and db.execute("SELECT COUNT(*) FROM schedule_events").fetchone()[0] >= MAX_EVENTS:
                    raise ValueError("EVENT_CAPACITY_EXCEEDED")
                committed = stamp(datetime.now(timezone.utc).replace(microsecond=0))
                if previous:
                    committed = max(committed, previous["modified_at_utc"])
                event = successor(request, previous, self.subject, committed)
                sequence = db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM schedule_operations").fetchone()[0]
                record = {"sequence": sequence, "subject": self.subject, "request": request,
                          "before_sha256": digest(previous) if previous else None, "event": event,
                          "committed_at_utc": committed}
                db.execute("INSERT OR REPLACE INTO schedule_events VALUES (?,?)", (event["event_id"], canonical(event)))
                db.execute("INSERT INTO schedule_operations VALUES (?,?,?)", (sequence, request["operation_id"], canonical(record)))
                self._require_snapshot_capacity(db)
        # Independent post-commit read: a competing successor must be visible.
        readback = self.read(request["event_id"])
        matches = digest(readback["events"][0]) == digest(record["event"]) and record["subject"] == self.subject
        if not replay and not matches:
            raise ScheduleConflict("POST_EFFECT_READBACK_CHANGED")
        return {"schema": SCHEMA, "operation_id": request["operation_id"], "operation_sha256": digest(request),
                "original_record": record, "readback": readback, "replay": replay, "historical_only": replay or not matches,
                "current_readback_matches_original": matches, "local_post_effect_readback_verified": matches and not replay,
                "external_effect_verified": False, "effect_ack_done": False}

    def record_sync(self, raw_receipt):
        receipt = decode(canonical(raw_receipt).encode("utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("INVALID_SYNC_RECEIPT")
        identifier(receipt.get("event_id"), "EVENT_ID")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            event = self._event(db, receipt["event_id"])
            # Even an identical replay must remain bound to the current event.
            receipt = sync_receipt(receipt, event, self.subject, now=datetime.now(timezone.utc))
            existing = db.execute("SELECT receipt FROM schedule_sync_receipts WHERE id=?", (receipt["receipt_id"],)).fetchone()
            if existing and digest(json.loads(existing[0])) != digest(receipt):
                raise ScheduleConflict("RECEIPT_ID_CONTENT_COLLISION")
            all_receipts = self._receipts(db)
            revisions = {}
            for prior in all_receipts:
                _check_target_revision(prior, revisions)
            _check_target_revision(receipt, revisions)
            if not existing:
                if len(all_receipts) >= MAX_OPERATIONS:
                    raise ValueError("SYNC_RECEIPT_CAPACITY_EXCEEDED")
                db.execute("INSERT INTO schedule_sync_receipts VALUES (?,?)", (receipt["receipt_id"], canonical(receipt)))
                self._require_snapshot_capacity(db)
        readback = self.read(receipt["event_id"])
        if not any(digest(receipt) == digest(r) for r in readback["sync_receipts"]):
            raise ScheduleConflict("SYNC_POST_WRITE_READBACK_CHANGED")
        return {"schema": SYNC_SCHEMA, "receipt": receipt, "readback": readback,
                "state": "PROVIDED_READBACK_MATCH" if receipt["observation"] else "TRANSPORT_ONLY",
                "connector_observation_authenticity_verified": False, "external_effect_verified": False,
                "effect_ack_done": False}

    def export(self):
        with self.connect() as db:
            db.execute("BEGIN")
            packet = self._packet(db)
        raw = canonical(packet).encode("utf-8")
        validate_snapshot(raw)
        return raw

    def restore(self, raw):
        packet = validate_snapshot(raw)
        if packet["subject"] != self.subject:
            raise ScheduleConflict("EXACT_SNAPSHOT_SUBJECT_REQUIRED")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if any(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] for table in
                   ("schedule_events", "schedule_operations", "schedule_sync_receipts")):
                raise ScheduleConflict("REPLAY_REQUIRES_EMPTY_NATIVE_STORE")
            db.executemany("INSERT INTO schedule_events VALUES (?,?)", [(e["event_id"], canonical(e)) for e in packet["events"]])
            db.executemany("INSERT INTO schedule_operations VALUES (?,?,?)", [(r["sequence"], r["request"]["operation_id"], canonical(r)) for r in packet["operations"]])
            db.executemany("INSERT INTO schedule_sync_receipts VALUES (?,?)", [(r["receipt_id"], canonical(r)) for r in packet["sync_receipts"]])
        if self.export() != raw:
            raise ScheduleConflict("REPLAY_POST_WRITE_READBACK_CHANGED")
        return {"schema": SNAPSHOT_SCHEMA, "state": "LOCAL_HISTORY_RECONSTRUCTED",
                "snapshot_sha256": digest(packet), "post_write_readback_verified": True,
                "replay_establishes_external_effect": False, "effect_ack_done": False}

    def plan(self, after):
        instant(after)
        entries = []
        for event in self.read()["events"]:
            if not event["deleted"]:
                slot = next_slot(event["value"], after)
                if slot is not None:
                    entries.append({"event_id": event["event_id"], "version": event["version"], "next_slot_utc": slot})
        return {"schema": SCHEMA, "subject": self.subject, "planned_after_utc": after,
                "entries": sorted(entries, key=lambda e: (e["next_slot_utc"], e["event_id"])),
                "dispatch_performed": False, "effect_ack_done": False}
