# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Real persistence, clock, concurrency and authenticated API regressions."""
import os
import json
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
import threading
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.qikvrt_digital_twin_scheduling import (
    BASE, ScheduleConflict, SchedulingStore, config, digest, next_due,
    normalize_task, stamp, SchedulingBridge, HttpScheduleExecutor, canonical,
)
from tests import test_tcpip_e2e as tcpip


def fixture():
    return {"id": "1" * 32, "title": "Regulatory watch", "prompt": "Report material changes only.",
            "schedule": "BEGIN:VEVENT\nDTSTART;TZID=Europe/Paris:20261002T080000\nRRULE:FREQ=DAILY;BYHOUR=8;BYMINUTE=0;BYSECOND=0\nEND:VEVENT",
            "default_timezone": "Europe/Paris", "timing_mode": "condition_watch", "is_enabled": True,
            "updated_at": stamp(datetime.now(timezone.utc) - timedelta(seconds=30)),
            "last_run_time": None, "next_run_time": None}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = SchedulingStore(self.root, "owner/repo", "operator")
        self.task = fixture()

    def tearDown(self):
        self.temp.cleanup()

    def apply(self, task=None, revision=0, observed=None):
        return self.store.reconcile(expected_revision=revision, task=task or self.task,
                                    observed_at=observed or stamp(datetime.now(timezone.utc)))

    def test_roundtrip_restart_and_no_duplicate_executor(self):
        result = self.apply()
        reopened = SchedulingStore(self.root, "owner/repo", "operator")
        actual = reopened.read(self.task["id"])
        self.assertEqual(actual["task"], self.task)
        self.assertEqual(actual["configuration_sha256"], digest(config(self.task)))
        self.assertEqual(actual["revision"], 1)
        self.assertFalse(actual["local_dispatch_authorized"])
        self.assertFalse(actual["continuous_bridge_verified"])
        self.assertFalse(result["effect_ack_done"])
        self.assertEqual(os.stat(reopened.path).st_mode & 0o777, 0o600)

    def test_reobservation_noop_and_cas(self):
        self.apply()
        self.assertEqual(self.apply(revision=1)["revision"], 1)
        self.assertEqual(len(self.store.read()["tasks"]), 1)
        with self.assertRaisesRegex(ScheduleConflict, "STALE_EXACT"):
            self.apply(revision=0)
        with self.assertRaises(ScheduleConflict):
            self.apply(revision=True)

    def test_pause_prepare_and_matching_executor_readback(self):
        self.apply()
        plan = self.store.prepare(task_id=self.task["id"], expected_revision=1, changes={"is_enabled": False})
        self.assertEqual(plan["executor_operation"]["arguments"], {"jawbone_id": self.task["id"], "is_enabled": False})
        self.assertEqual(self.store.read(self.task["id"])["state"], "AWAIT_EXECUTOR_READBACK")
        self.assertIsNone(self.store.due(at="2026-10-01T12:00:00Z")["tasks"][0]["planned_next_slot_utc"])
        with self.assertRaisesRegex(ScheduleConflict, "READBACK_MISMATCH"):
            self.apply(revision=2)
        paused = dict(self.task, is_enabled=False, updated_at=stamp(datetime.now(timezone.utc)))
        result = self.apply(paused, revision=2)
        self.assertEqual(result["revision"], 3)
        self.assertEqual(result["state"], "SOURCE_SNAPSHOT_STORED")
        self.assertIsNone(next_due(paused, "2026-10-01T12:00:00Z"))

    def test_prompt_and_timezone_changes_are_bound(self):
        self.apply()
        changes = {"prompt": "Updated scope.", "default_timezone": "UTC",
                   "schedule": "BEGIN:VEVENT\nDTSTART;TZID=UTC:20261002T080000\nRRULE:FREQ=DAILY\nEND:VEVENT"}
        plan = self.store.prepare(task_id=self.task["id"], expected_revision=1, changes=changes)
        changed = dict(self.task, **changes, updated_at=stamp(datetime.now(timezone.utc)))
        out = self.apply(changed, revision=plan["revision"])
        self.assertEqual(out["configuration_sha256"], digest(config(changed)))
        self.assertEqual(next_due(changed, "2026-10-01T12:00:00Z"), "2026-10-02T08:00:00Z")

    def test_stale_timestamp_and_version_collision(self):
        self.apply()
        old = dict(self.task, updated_at=stamp(datetime.now(timezone.utc) - timedelta(minutes=1)))
        with self.assertRaisesRegex(ScheduleConflict, "STALE_EXECUTOR"):
            self.apply(old, revision=1)
        with self.assertRaisesRegex(ScheduleConflict, "VERSION_COLLISION"):
            self.apply(dict(self.task, prompt="tampered"), revision=1)
        self.assertEqual(self.store.read(self.task["id"])["task"], self.task)

    def test_old_future_and_out_of_order_observations_fail_closed(self):
        for delta in (timedelta(minutes=-6), timedelta(minutes=1)):
            with self.assertRaisesRegex(ScheduleConflict, "FRESH_SOURCE"):
                self.apply(observed=stamp(datetime.now(timezone.utc) + delta))
        self.apply()
        observed = stamp(datetime.now(timezone.utc) - timedelta(seconds=1))
        with self.assertRaisesRegex(ScheduleConflict, "STALE_EXECUTOR"):
            self.apply(revision=1, observed=observed)

    def test_concurrent_writers_one_cas_successor(self):
        self.apply()
        barrier = threading.Barrier(2)
        def change(enabled):
            barrier.wait(timeout=3)
            try:
                self.store.prepare(task_id=self.task["id"], expected_revision=1,
                                   changes={"prompt": "new " + str(enabled)})
                return "success"
            except ScheduleConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(change, (True, False)))
        self.assertEqual(sorted(results), ["conflict", "success"])
        self.assertEqual(self.store.read(self.task["id"])["revision"], 2)

    def test_principal_repository_isolation(self):
        self.apply()
        for repository, principal in (("other/repo", "operator"), ("owner/repo", "other")):
            other = SchedulingStore(self.root, repository, principal)
            self.assertEqual(other.read()["tasks"], [])

    def test_symlink_and_world_readable_database_rejected(self):
        os.chmod(self.store.path, 0o644)
        with self.assertRaisesRegex(ValueError, "UNSAFE_SCHEDULE_DATABASE"):
            SchedulingStore(self.root, "owner/repo", "operator")
        with tempfile.TemporaryDirectory() as other:
            link = Path(other) / ".qikvrt"
            link.symlink_to(self.root / ".qikvrt", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "UNSAFE_SCHEDULE_STATE_DIRECTORY"):
                SchedulingStore(Path(other), "owner/repo", "operator")

    def test_closed_schema_and_invalid_types(self):
        for changes in ({"id": "bad"}, {"is_enabled": 1}, {"timing_mode": []}, {"unexpected": True}, {"updated_at": "2026-01-01"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                normalize_task(dict(self.task, **changes))


class MemoryExecutor:
    """Test authority with atomic CAS; never an external-effect witness."""
    def __init__(self, task=None):
        self.task = dict(task or fixture())
        self.version = 1
        self.authenticated = True
        self.cas_available = True
        self.calls = 0
        self.lock = threading.Lock()
        self.after_update = None
        self.before_update = None
        self.observation_offset = timedelta(0)

    def require_authentication(self):
        if not self.authenticated:
            raise ScheduleConflict("EXECUTOR_AUTHENTICATION_REQUIRED")

    def read_existing(self, task_id):
        self.require_authentication()
        with self.lock:
            return {"task": dict(self.task), "version": "v" + str(self.version),
                    "observed_at": stamp(datetime.now(timezone.utc) + self.observation_offset),
                    "conditional_update": self.cas_available}

    def update_existing(self, task_id, *, expected_version, changes, idempotency_key):
        self.require_authentication()
        if self.before_update:
            self.before_update()
        with self.lock:
            self.calls += 1
            if expected_version != "v" + str(self.version):
                raise ScheduleConflict("REMOTE_CAS_CONFLICT")
            self.task.update(changes, updated_at=stamp(datetime.now(timezone.utc)))
            self.version += 1
        if self.after_update:
            self.after_update()


class BridgeTests(unittest.TestCase):
    tearDown = StoreTests.tearDown
    apply = StoreTests.apply

    def setUp(self):
        StoreTests.setUp(self)
        self.executor = MemoryExecutor(self.task)
        self.bridge = SchedulingBridge(self.store, self.executor)

    def sync(self, event="event-1", revision=0, changes=None):
        return self.bridge.sync(task_id=self.task["id"], event_id=event,
                                expected_revision=revision, changes=changes or {})

    def test_bridge_import_pause_resume_and_idempotent_replay(self):
        first = self.sync()
        paused = self.sync("pause", first["revision"], {"is_enabled": False})
        self.assertFalse(self.store.read(self.task["id"])["task"]["is_enabled"])
        repeated = self.sync("pause", first["revision"], {"is_enabled": False})
        self.assertEqual(repeated["revision"], paused["revision"])
        resumed = self.sync("resume", paused["revision"], {"is_enabled": True})
        self.assertTrue(self.store.read(self.task["id"])["task"]["is_enabled"])
        self.assertEqual(self.executor.calls, 2)
        self.assertFalse(resumed["continuous_bridge_verified"])
        self.assertFalse(resumed["local_dispatch_authorized"])
        self.assertFalse(resumed["effect_ack_done"])

    def test_restart_after_remote_effect_never_repeats_update(self):
        class Crash(BaseException):
            pass
        def crash():
            raise Crash()
        self.executor.after_update = crash
        with self.assertRaises(Crash):
            self.sync(changes={"is_enabled": False})
        self.executor.after_update = None
        self.store = SchedulingStore(self.root, "owner/repo", "operator")
        self.bridge = SchedulingBridge(self.store, self.executor)
        receipt = self.sync(changes={"is_enabled": False})
        self.assertEqual(self.executor.calls, 1)
        self.assertEqual(receipt["state"], "CONFIGURATION_READBACK_VERIFIED")

    def test_restart_after_reconcile_before_journal_verification(self):
        original = self.store.reconcile
        class Crash(BaseException):
            pass
        def reconcile(**kwargs):
            original(**kwargs)
            raise Crash()
        with patch.object(self.store, "reconcile", side_effect=reconcile), self.assertRaises(Crash):
            self.sync(changes={"is_enabled": False})
        self.bridge = SchedulingBridge(SchedulingStore(self.root, "owner/repo", "operator"), self.executor)
        self.assertEqual(self.sync(changes={"is_enabled": False})["revision"], 3)
        self.assertEqual(self.executor.calls, 1)

    def test_ambiguous_failure_without_effect_holds_without_retry(self):
        def fail(*args, **kwargs):
            self.executor.calls += 1
            raise OSError("connection lost before effect; location unknown")
        with patch.object(self.executor, "update_existing", side_effect=fail):
            with self.assertRaisesRegex(ScheduleConflict, "AMBIGUOUS"):
                self.sync(changes={"is_enabled": False})
            with self.assertRaisesRegex(ScheduleConflict, "AMBIGUOUS"):
                self.sync(changes={"is_enabled": False})
        self.assertEqual(self.executor.calls, 1)
        with self.assertRaisesRegex(ScheduleConflict, "WRITER_ACTIVE"):
            self.store.prepare(task_id=self.task["id"], expected_revision=2, changes={"prompt": "other"})
        with self.assertRaisesRegex(ScheduleConflict, "WRITER_ACTIVE"):
            self.apply(revision=2)

    def test_lost_ack_after_effect_recovers_by_source_readback(self):
        def lost_ack():
            raise OSError("ack lost")
        self.executor.after_update = lost_ack
        result = self.sync(changes={"is_enabled": False})
        self.assertEqual(result["state"], "CONFIGURATION_READBACK_VERIFIED")
        self.assertFalse(result["executor_mutation_acknowledged"])
        self.assertEqual(self.executor.calls, 1)

    def test_external_writer_between_read_and_cas_is_not_overwritten(self):
        def external_change():
            self.executor.task.update(prompt="concurrent human change", updated_at=stamp(datetime.now(timezone.utc)))
            self.executor.version += 1
        self.executor.before_update = external_change
        with self.assertRaisesRegex(ScheduleConflict, "AMBIGUOUS"):
            self.sync(changes={"is_enabled": False})
        self.assertTrue(self.executor.task["is_enabled"])
        self.assertEqual(self.executor.task["prompt"], "concurrent human change")

    def test_two_concurrent_bridge_writers_have_one_successor(self):
        self.sync()
        barrier = threading.Barrier(2)
        def writer(i):
            barrier.wait(timeout=3)
            try:
                self.sync("writer-" + str(i), 1, {"prompt": "writer " + str(i)})
                return "success"
            except ScheduleConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(writer, (1, 2)))
        self.assertEqual(sorted(results), ["conflict", "success"])
        self.assertEqual(self.executor.calls, 1)

    def test_reordered_events_and_collision_do_not_mutate(self):
        self.sync()
        self.sync("new", 1, {"prompt": "new"})
        with self.assertRaisesRegex(ScheduleConflict, "STALE_EXACT"):
            self.sync("old", 1, {"prompt": "old"})
        with self.assertRaisesRegex(ScheduleConflict, "COLLISION"):
            self.sync("new", 1, {"prompt": "different"})
        self.assertEqual(self.executor.calls, 1)

    def test_authentication_and_missing_atomic_cas_fail_closed(self):
        self.executor.authenticated = False
        with self.assertRaisesRegex(ScheduleConflict, "AUTHENTICATION"):
            self.sync()
        self.executor.authenticated = True
        self.executor.cas_available = False
        with self.assertRaisesRegex(ScheduleConflict, "CAS_UNAVAILABLE"):
            self.sync(changes={"is_enabled": False})
        self.assertEqual(self.store.read()["tasks"], [])
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.sync()["revision"], 1)

    def test_stale_observation_version_collision_and_task_identity(self):
        self.executor.observation_offset = timedelta(seconds=-1)
        with self.assertRaisesRegex(ScheduleConflict, "FRESH_BRIDGE"):
            self.sync()
        self.executor.observation_offset = timedelta(0)
        self.sync()
        self.executor.task["prompt"] = "tampered"
        with self.assertRaisesRegex(ScheduleConflict, "CONTRADICTORY"):
            self.sync("new", 1)
        self.executor.task["id"] = "2" * 32
        with self.assertRaisesRegex(ScheduleConflict, "TASK_ID_MISMATCH"):
            self.sync("new", 1)
        self.assertEqual(self.executor.calls, 0)

    def test_source_version_rollback_and_local_readback_tamper(self):
        self.sync()
        self.executor.task["updated_at"] = stamp(datetime.now(timezone.utc) - timedelta(hours=1))
        with self.assertRaisesRegex(ScheduleConflict, "STALE_EXECUTOR"):
            self.sync("new", 1)
        self.executor.task["updated_at"] = self.task["updated_at"]
        original = self.store.read
        def tampered(task_id=None):
            result = original(task_id)
            if task_id:
                result["configuration_sha256"] = "0" * 64
            return result
        with patch.object(self.store, "read", side_effect=tampered), self.assertRaisesRegex(ScheduleConflict, "DRIFT"):
            self.sync()

    def test_source_events_import_external_pause_and_refresh_run_metadata(self):
        result = self.sync()
        self.executor.task.update(is_enabled=False, updated_at=stamp(datetime.now(timezone.utc)))
        self.executor.version += 1
        result = self.sync("external-pause", result["revision"])
        self.executor.task["last_run_time"] = stamp(datetime.now(timezone.utc))
        result = self.sync("external-pause", 1)
        self.assertEqual(self.store.read(self.task["id"])["task"]["last_run_time"], self.executor.task["last_run_time"])
        self.assertEqual(self.executor.calls, 0)

    def test_same_event_concurrent_calls_do_not_duplicate_update(self):
        self.sync()
        barrier = threading.Barrier(2)
        def writer(_):
            barrier.wait(timeout=3)
            try:
                self.sync("same", 1, {"is_enabled": False})
                return "success"
            except ScheduleConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(writer, (1, 2)))
        self.assertIn("success", results)
        self.assertEqual(self.executor.calls, 1)

    def test_prepared_restart_and_expired_auth_do_not_dispatch(self):
        original = self.bridge.source_read
        calls = 0
        class Crash(BaseException):
            pass
        def crash_after_prepare(task_id):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise Crash()
            return original(task_id)
        with patch.object(self.bridge, "source_read", side_effect=crash_after_prepare), self.assertRaises(Crash):
            self.sync(changes={"is_enabled": False})
        self.executor.authenticated = False
        with self.assertRaisesRegex(ScheduleConflict, "AUTHENTICATION"):
            self.sync(changes={"is_enabled": False})
        self.assertEqual(self.executor.calls, 0)
        self.executor.authenticated = True
        self.assertEqual(self.sync(changes={"is_enabled": False})["revision"], 3)
        self.assertEqual(self.executor.calls, 1)

    def test_source_drift_before_claim_holds(self):
        self.sync()
        original = self.bridge.source_read
        calls = 0
        def drift(task_id):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.executor.task.update(prompt="external", updated_at=stamp(datetime.now(timezone.utc)))
                self.executor.version += 1
            return original(task_id)
        with patch.object(self.bridge, "source_read", side_effect=drift), self.assertRaisesRegex(ScheduleConflict, "DRIFT"):
            self.sync("change", 1, {"is_enabled": False})
        self.assertEqual(self.executor.calls, 0)

    def test_bridge_dst_gap_and_fold_preserve_one_executor(self):
        self.sync()
        schedule = "BEGIN:VEVENT\nDTSTART;TZID=Europe/Paris:20261002T023000\nRRULE:FREQ=DAILY\nEND:VEVENT"
        self.sync("dst", 1, {"schedule": schedule})
        task = self.store.read(self.task["id"])["task"]
        self.assertEqual(next_due(task, "2027-03-27T01:30:00Z"), "2027-03-29T00:30:00Z")
        self.assertEqual(next_due(task, "2026-10-25T00:30:00Z"), "2026-10-26T01:30:00Z")
        self.assertEqual(self.executor.calls, 1)


class CalendarTests(unittest.TestCase):
    def test_first_slot_and_dst_wall_clock(self):
        task = fixture()
        self.assertEqual(next_due(task, "2026-10-01T23:00:00Z"), "2026-10-02T06:00:00Z")
        self.assertEqual(next_due(task, "2026-10-24T06:00:00Z"), "2026-10-25T07:00:00Z")
        self.assertEqual(next_due(task, "2027-03-27T07:00:00Z"), "2027-03-28T06:00:00Z")

    def test_weekly_days_and_interval(self):
        task = fixture()
        task["schedule"] = "BEGIN:VEVENT\nDTSTART;TZID=Europe/Paris:20261002T080000\nRRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=FR,SA\nEND:VEVENT"
        self.assertEqual(next_due(task, "2026-10-02T06:00:00Z"), "2026-10-03T06:00:00Z")
        self.assertEqual(next_due(task, "2026-10-03T06:00:00Z"), "2026-10-16T06:00:00Z")

    def test_hourly_utc_phase(self):
        task = fixture()
        task["schedule"] = "BEGIN:VEVENT\nDTSTART:20261001T060000Z\nRRULE:FREQ=HOURLY;INTERVAL=4\nEND:VEVENT"
        self.assertEqual(next_due(task, "2026-10-01T09:00:00Z"), "2026-10-01T10:00:00Z")

    def test_zulu_daily_rule_keeps_utc_clock_across_dst(self):
        task = fixture()
        task["schedule"] = "BEGIN:VEVENT\nDTSTART:20261002T080000Z\nRRULE:FREQ=DAILY;BYHOUR=8\nEND:VEVENT"
        self.assertEqual(next_due(task, "2026-10-01T12:00:00Z"), "2026-10-02T08:00:00Z")
        self.assertEqual(next_due(task, "2026-10-24T08:00:00Z"), "2026-10-25T08:00:00Z")

    def test_nonexistent_slot_skipped_and_fold_not_duplicated(self):
        task = fixture()
        task["schedule"] = "BEGIN:VEVENT\nDTSTART;TZID=Europe/Paris:20261002T023000\nRRULE:FREQ=DAILY\nEND:VEVENT"
        self.assertEqual(next_due(task, "2027-03-27T01:30:00Z"), "2027-03-29T00:30:00Z")
        self.assertEqual(next_due(task, "2026-10-25T00:30:00Z"), "2026-10-26T01:30:00Z")

    def test_unsupported_and_noncanonical_rules_rejected(self):
        task = fixture()
        rules = ["FREQ=MINUTELY", "FREQ=DAILY;FREQ=WEEKLY", "FREQ=DAILY;UNTIL=20270101T000000Z", "FREQ=DAILY;INTERVAL=0", "FREQ=DAILY;BYHOUR=24", "FREQ=HOURLY;BYHOUR=8"]
        for rule in rules:
            bad = dict(task, schedule="BEGIN:VEVENT\nDTSTART;TZID=Europe/Paris:20261002T080000\nRRULE:" + rule + "\nEND:VEVENT")
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                normalize_task(bad)
        for zone in ("No/SuchZone", "UTC", "../UTC"):
            with self.subTest(zone=zone), self.assertRaises(ValueError):
                normalize_task(dict(task, default_timezone=zone))


class HttpTests(unittest.TestCase):
    def setUp(self):
        # Reuse the real -S API-server harness rather than a second server.
        self.client = tcpip.TcpIpEndToEndTests()
        self.client.setUp()

    def tearDown(self):
        self.client.tearDown()

    def request(self, method, path, body=None, token=True):
        return self.client.request(method, path, body, token=token)

    def test_authenticated_create_read_plan_pause_and_source_confirmation(self):
        task = fixture()
        body = {"expected_revision": 0, "observed_at": stamp(datetime.now(timezone.utc)), "task": task}
        code, result = self.request("POST", BASE + "/reconcile", body)
        self.assertEqual(code, 200, result)
        code, read = self.request("GET", BASE + "/" + task["id"])
        self.assertEqual((code, read["task"]), (200, task))
        code, plan = self.request("POST", BASE + "/plan", {"at": "2026-10-01T12:00:00Z"})
        self.assertEqual(code, 200)
        self.assertEqual(plan["tasks"][0]["planned_next_slot_utc"], "2026-10-02T06:00:00Z")
        code, prepared = self.request("POST", BASE + "/prepare", {"task_id": task["id"], "expected_revision": 1, "changes": {"is_enabled": False}})
        self.assertEqual(code, 200)
        body.update(expected_revision=prepared["revision"], task=dict(task, is_enabled=False, updated_at=stamp(datetime.now(timezone.utc))), observed_at=stamp(datetime.now(timezone.utc)))
        code, out = self.request("POST", BASE + "/reconcile", body)
        self.assertEqual(code, 200, out)
        self.assertFalse(out["task"]["is_enabled"])
        self.assertFalse(out["effect_ack_done"])

    def test_unauthorized_reads_and_writes(self):
        for method, path, body in (("GET", BASE, None), ("POST", BASE + "/reconcile", {})):
            code, _ = self.request(method, path, body, token=False)
            self.assertEqual(code, 401)

    def test_unknown_fields_and_stale_revision_rejected(self):
        task = fixture()
        body = {"expected_revision": 0, "observed_at": stamp(datetime.now(timezone.utc)), "task": task}
        self.assertEqual(self.request("POST", BASE + "/reconcile", dict(body, extra=True))[0], 400)
        self.assertEqual(self.request("POST", BASE + "/reconcile", body)[0], 200)
        self.assertEqual(self.request("POST", BASE + "/reconcile", body)[0], 409)
        self.assertEqual(self.request("GET", BASE + "?all=true")[0], 404)

    def test_bridge_missing_provider_and_unauthorized_fail_closed(self):
        body = {"task_id": "1" * 32, "event_id": "source-event", "expected_revision": 0, "changes": {}}
        self.assertEqual(self.request("POST", BASE + "/bridge", body, token=False)[0], 401)
        code, result = self.request("POST", BASE + "/bridge", body)
        self.assertEqual(code, 409)
        self.assertEqual(result["reason"], "AUTHENTICATED_EXECUTOR_GATEWAY_NOT_CONFIGURED")
        self.assertEqual(self.request("GET", BASE)[1]["tasks"], [])


class BridgeHttpTests(unittest.TestCase):
    """Real shim -> authenticated test gateway -> CAS -> SQLite readback."""
    def setUp(self):
        self.executor = MemoryExecutor()
        self.requests = []
        self.bad_scope = False
        self.raw_response = None
        self.redirect = False
        self.token = "b64url:" + base64.urlsafe_b64encode(b"gateway-fixture-secret-32-bytes-!!").decode().rstrip("=")
        case = self
        class Gateway(BaseHTTPRequestHandler):
            def do_GET(self):
                self.respond(False)
            def do_PATCH(self):
                self.respond(True)
            def respond(self, write):
                case.requests.append((self.command, self.path, self.headers.get("If-Match"), self.headers.get("Idempotency-Key")))
                if self.headers.get("Authorization") != "Bearer " + case.token:
                    self.send_error(401)
                    return
                if self.path != "/tasks/" + case.executor.task["id"]:
                    self.send_error(404)
                    return
                if case.redirect:
                    self.send_response(302)
                    self.send_header("Location", "/stolen-token")
                    self.end_headers()
                    return
                if write:
                    body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    try:
                        case.executor.update_existing(case.executor.task["id"], expected_version=self.headers["If-Match"].strip('"'), changes=body["changes"], idempotency_key=self.headers["Idempotency-Key"])
                    except ScheduleConflict:
                        self.send_error(412)
                        return
                value = {"repository": "wrong/repo" if case.bad_scope else self.headers.get("X-QIKVRT-Repository"),
                         "principal": self.headers.get("X-QIKVRT-Principal"), "executor": "chatgpt_automations",
                         "observation": case.executor.read_existing(case.executor.task["id"])}
                raw = case.raw_response if case.raw_response is not None else canonical(value).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        self.gateway = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        self.thread = threading.Thread(target=self.gateway.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.gateway.server_port) + "/tasks"
        self.client = tcpip.TcpIpEndToEndTests()
        with patch.dict(os.environ, {"QIKVRT_SCHEDULE_EXECUTOR_URL": self.url, "QIKVRT_SCHEDULE_EXECUTOR_TOKEN": self.token,
                                     "QIKVRT_SCHEDULE_EXECUTOR_TOKEN_EXPIRES_UTC": "2099-01-01T00:00:00Z"}):
            self.client.setUp()

    def tearDown(self):
        self.client.tearDown()
        self.gateway.shutdown()
        self.gateway.server_close()
        self.thread.join(timeout=2)

    def sync(self, event="http-event", revision=0, changes=None, token=True):
        return self.client.request("POST", BASE + "/bridge", {"task_id": self.executor.task["id"],
                                   "event_id": event, "expected_revision": revision, "changes": changes or {}}, token=token)

    def test_real_http_authenticated_cas_readback_and_replay(self):
        code, result = self.sync(changes={"is_enabled": False})
        self.assertEqual(code, 200, result)
        self.assertEqual(result["revision"], 3)
        self.assertEqual(self.executor.calls, 1)
        writes = [entry for entry in self.requests if entry[0] == "PATCH"]
        self.assertEqual(writes, [("PATCH", "/tasks/" + self.executor.task["id"], '"v1"', "http-event")])
        code, local = self.client.request("GET", BASE + "/" + self.executor.task["id"])
        self.assertEqual(code, 200)
        self.assertEqual(local["task"], self.executor.task)
        self.assertFalse(local["continuous_bridge_verified"])
        self.assertEqual(self.sync(changes={"is_enabled": False})[0], 200)
        self.assertEqual(self.executor.calls, 1)

    def test_auth_scope_stale_response_and_redirect_fail_closed(self):
        self.assertEqual(self.sync(token=False)[0], 401)
        self.assertEqual(self.requests, [])
        self.bad_scope = True
        self.assertEqual(self.sync()[0], 409)
        self.bad_scope = False
        self.executor.observation_offset = timedelta(minutes=-10)
        self.assertEqual(self.sync()[0], 409)
        self.executor.observation_offset = timedelta(0)
        self.redirect = True
        self.assertEqual(self.sync()[0], 500)
        self.assertFalse(any(request[1] == "/stolen-token" for request in self.requests))
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.client.request("GET", BASE)[1]["tasks"], [])

    def test_duplicate_json_large_response_and_expired_token(self):
        self.raw_response = b'{"repository":"owner/repo","repository":"evil/repo"}'
        self.assertEqual(self.sync()[0], 400)
        self.raw_response = b" " * (1024 * 1024 + 1)
        self.assertEqual(self.sync()[0], 400)
        adapter = HttpScheduleExecutor(self.url, self.token, "2000-01-01T00:00:00Z", "owner/repo", "operator")
        before = len(self.requests)
        with self.assertRaisesRegex(ScheduleConflict, "EXPIRED"):
            adapter.read_existing(self.executor.task["id"])
        self.assertEqual(len(self.requests), before)
        for url in ("http://external.example/tasks", "https://user:secret@example.org/tasks", "https://example.org/tasks?token=x"):
            with self.assertRaises(ValueError):
                HttpScheduleExecutor(url, self.token, "2099-01-01T00:00:00Z", "owner/repo", "operator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
