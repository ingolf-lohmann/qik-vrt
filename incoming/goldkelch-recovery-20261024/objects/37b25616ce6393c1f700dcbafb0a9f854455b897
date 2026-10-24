# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Real persistence, clock, concurrency and authenticated API regressions."""
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.qikvrt_digital_twin_scheduling import (
    BASE, ScheduleConflict, SchedulingStore, config, digest, next_due,
    normalize_task, stamp,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
