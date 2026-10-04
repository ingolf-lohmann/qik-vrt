# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exercise actual SQLite transactions, DST boundaries, ledger replay and HTTP."""
import copy
import json
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src import qikvrt_digital_twin_schedule_events as native
from src.qikvrt_digital_twin_scheduling import ScheduleConflict, canonical, digest, stamp
from tests import test_tcpip_e2e as tcpip


SOURCE = {"repository": "ingolf-lohmann/qik-vrt", "role": "MIRROR", "head": "1" * 40, "tree": "2" * 40}
EVENT = native.identity("event", "fixture", "one")


def configuration(local="2026-10-02T08:00:00", zone="Europe/Paris", fold=0):
    return {"title": "Private schedule", "payload": {"work_unit": "fixture-only"}, "enabled": True,
            "start": native.time_binding(local, zone, fold), "recurrence": None}


def recurring(value, frequency="DAILY", interval=1, weekdays=None, fold="FIRST"):
    return dict(value, recurrence={"frequency": frequency, "interval": interval,
                                  "weekdays": weekdays or [], "gap_policy": "SKIP", "fold_policy": fold})


def operation(kind="create", version=0, *, event=EVENT, key="create", value=None):
    return {"schema": native.OPERATION_SCHEMA, "operation_id": native.identity("operation", "fixture", key),
            "event_id": event, "kind": kind, "expected_version": version,
            "value": None if kind == "delete" else (configuration() if value is None else value)}


def receipt(event, *, key="sync", observed=True, source=None, revision="remote-revision-1", transport=True):
    return {"schema": native.SYNC_SCHEMA, "receipt_id": native.identity("receipt", "fixture", key),
            "source_subject": dict(source or SOURCE),
            "target": {"kind": "connector", "connector_id": "fixture-adapter", "resource_id": "fixture-object"},
            "event_id": event["event_id"], "event_version": event["version"], "event_sha256": digest(event),
            "transport_ack": transport,
            "observation": {"observed_at_utc": stamp(datetime.now(timezone.utc).replace(microsecond=0)),
                            "target_revision": revision, "readback": copy.deepcopy(event)} if observed else None}


class TimeTests(unittest.TestCase):
    def test_explicit_both_dst_folds_and_unknown_or_nonexistent_time(self):
        first = native.time_binding("2026-10-25T02:30:00", "Europe/Paris", 0)
        second = native.time_binding("2026-10-25T02:30:00", "Europe/Paris", 1)
        self.assertEqual((first["utc"], second["utc"]), ("2026-10-25T00:30:00Z", "2026-10-25T01:30:00Z"))
        for local, zone, fold in (("2026-03-29T02:30:00", "Europe/Paris", 0),
                                  ("2026-10-02T08:00:00", "Europe/Paris", 1),
                                  ("2026-10-02T08:00:00", "Unknown/Zone", 0),
                                  ("2026-10-02T08:00:00", "../UTC", 0)):
            with self.subTest(local=local, zone=zone, fold=fold), self.assertRaises(ValueError):
                native.time_binding(local, zone, fold)

    def test_canonical_seconds_offset_and_pinned_timezone_bytes(self):
        value = configuration()
        for field, content in (("utc", "2026-10-02T06:00:00+00:00"),
                               ("utc", "2026-10-02T06:00:00.000Z"),
                               ("local", "2026-10-02 08:00:00"), ("tzif_sha256", "a" * 64), ("fold", True)):
            bad = copy.deepcopy(value)
            bad["start"][field] = content
            with self.subTest(field=field), self.assertRaises(ValueError):
                native.validate_value(bad)
        actual_zone, _ = native.zone_binding("Europe/Paris")
        with patch.object(native, "zone_binding", return_value=(actual_zone, "b" * 64)), self.assertRaisesRegex(ValueError, "TZIF_DRIFT"):
            native.validate_value(value)

    def test_wall_clock_dst_daily_and_gap_skip(self):
        daily = recurring(configuration())
        self.assertEqual(native.next_slot(daily, "2026-10-24T06:00:00Z"), "2026-10-25T07:00:00Z")
        self.assertEqual(native.next_slot(daily, "2027-03-27T07:00:00Z"), "2027-03-28T06:00:00Z")
        gap = recurring(configuration("2026-10-02T02:30:00"))
        self.assertEqual(native.next_slot(gap, "2027-03-27T01:30:00Z"), "2027-03-29T00:30:00Z")

    def test_recurrence_fold_policy_and_no_double_execution_slot(self):
        daily = recurring(configuration("2026-10-02T02:30:00"))
        self.assertEqual(native.next_slot(daily, "2026-10-24T23:00:00Z"), "2026-10-25T00:30:00Z")
        self.assertEqual(native.next_slot(daily, "2026-10-25T00:30:00Z"), "2026-10-26T01:30:00Z")
        second = recurring(configuration("2026-10-02T02:30:00"), fold="SECOND")
        self.assertEqual(native.next_slot(second, "2026-10-25T00:30:00Z"), "2026-10-25T01:30:00Z")
        self.assertEqual(native.next_slot(second, "2026-10-25T01:30:00Z"), "2026-10-26T01:30:00Z")

    def test_hourly_elapsed_weekly_interval_and_non_hour_offset(self):
        hourly = recurring(configuration("2026-10-24T08:00:00"), frequency="HOURLY", interval=4)
        self.assertEqual(native.next_slot(hourly, "2026-10-25T00:00:00Z"), "2026-10-25T02:00:00Z")
        weekly = recurring(configuration(), frequency="WEEKLY", interval=2, weekdays=[4, 5])
        self.assertEqual(native.next_slot(weekly, "2026-10-03T06:00:00Z"), "2026-10-16T06:00:00Z")
        value = configuration(zone="Asia/Kolkata")
        self.assertEqual(value["start"]["utc"], "2026-10-02T02:30:00Z")
        self.assertEqual(native.next_slot(value, "2026-10-02T02:30:00Z"), None)
        self.assertEqual(native.next_slot(dict(value, enabled=False), "2026-10-01T00:00:00Z"), None)

    def test_noncanonical_or_unsupported_recurrence_fails_closed(self):
        base = recurring(configuration(), frequency="WEEKLY", weekdays=[0, 4])
        for change in ({"weekdays": [4, 0]}, {"weekdays": [0, 0]}, {"weekdays": [True]},
                       {"interval": 0}, {"interval": True}, {"frequency": "MONTHLY"},
                       {"gap_policy": "SHIFT"}, {"fold_policy": "BOTH"}, {"until": "2028-01-01"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                native.validate_value(dict(base, recurrence=dict(base["recurrence"], **change)))


class EventStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = native.ScheduleEventStore(self.root, SOURCE, "fixture-principal")

    def tearDown(self):
        self.temp.cleanup()

    def event(self):
        return self.store.read(EVENT)["events"][0]

    def test_identity_is_stable_domain_separated_and_content_independent(self):
        self.assertEqual(EVENT, native.identity("event", "fixture", "one"))
        self.assertNotEqual(EVENT, native.identity("operation", "fixture", "one"))
        self.assertNotEqual(EVENT, native.identity("event", "another-origin", "one"))
        self.store.apply(operation())
        self.store.apply(operation("update", 1, key="rename", value=dict(configuration(), title="Changed")))
        self.assertEqual(self.event()["event_id"], EVENT)
        self.assertEqual(self.event()["version"], 2)

    def test_roundtrip_restart_byte_identity_and_local_post_effect_readback(self):
        result = self.store.apply(operation())
        self.assertTrue(result["local_post_effect_readback_verified"])
        self.assertFalse(result["effect_ack_done"])
        snapshot = self.store.export()
        reopened = native.ScheduleEventStore(self.root, SOURCE, "fixture-principal")
        self.assertEqual(reopened.export(), snapshot)
        with tempfile.TemporaryDirectory() as restored:
            target = native.ScheduleEventStore(restored, SOURCE, "fixture-principal")
            receipt = target.restore(snapshot)
            self.assertTrue(receipt["post_write_readback_verified"])
            self.assertFalse(receipt["replay_establishes_external_effect"])
            self.assertEqual(target.export(), snapshot)
            self.assertEqual(target.read(), reopened.read())

    def test_readback_cannot_mutate_store_subject_binding(self):
        result = self.store.apply(operation())
        result["readback"]["subject"]["role"] = "AUTHORITY"
        result["original_record"]["event"]["last_subject"]["head"] = "f" * 40
        self.assertEqual(self.store.subject, SOURCE)
        self.assertEqual(self.event()["last_subject"], SOURCE)

    def test_idempotency_content_collision_and_historical_replay(self):
        request = operation()
        self.store.apply(request)
        replay = self.store.apply(request)
        self.assertTrue(replay["replay"])
        self.assertTrue(replay["current_readback_matches_original"])
        self.assertFalse(replay["local_post_effect_readback_verified"])
        self.assertEqual(self.event()["version"], 1)
        with self.assertRaisesRegex(ScheduleConflict, "CONTENT_COLLISION"):
            self.store.apply(dict(request, value=dict(configuration(), title="tamper")))
        self.store.apply(operation("update", 1, key="update"))
        replay = self.store.apply(request)
        self.assertTrue(replay["historical_only"])
        self.assertFalse(replay["local_post_effect_readback_verified"])
        self.assertEqual(len(native.validate_snapshot(self.store.export())["operations"]), 2)

    def test_expected_version_types_unknown_fields_and_duplicate_ids(self):
        for change in ({"expected_version": True}, {"expected_version": 0.0},
                       {"expected_version": -1}, {"extra": True}, {"schema": "v999"}, {"event_id": "x"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.store.apply(dict(operation(), **change))
        self.store.apply(operation())
        for request in (operation(key="duplicate"), operation("create", 1, key="duplicate2"), operation("update", 0, key="stale")):
            with self.assertRaises(ScheduleConflict):
                self.store.apply(request)
        self.assertEqual(self.event()["version"], 1)

    def test_bool_integer_aliases_cannot_forge_byte_identity(self):
        request = operation(value=dict(configuration(), payload={"bit": 1}))
        self.store.apply(request)
        bad = copy.deepcopy(request)
        bad["value"]["payload"]["bit"] = True
        with self.assertRaisesRegex(ScheduleConflict, "CONTENT_COLLISION"):
            self.store.apply(bad)
        bad_receipt = receipt(self.event())
        bad_receipt["observation"]["readback"]["version"] = True
        with self.assertRaisesRegex(ScheduleConflict, "CONTRADICTORY"):
            self.store.record_sync(bad_receipt)
        packet = native.validate_snapshot(self.store.export())
        packet["events"][0]["version"] = True
        with self.assertRaises(ScheduleConflict):
            native.validate_snapshot(canonical(packet).encode())

    def test_concurrent_independent_connections_only_one_cas_successor(self):
        self.store.apply(operation())
        other = native.ScheduleEventStore(self.root, SOURCE, "fixture-principal")
        barrier = threading.Barrier(2)
        def writer(pair):
            store, key = pair
            barrier.wait(timeout=3)
            try:
                store.apply(operation("update", 1, key=key, value=dict(configuration(), title=key)))
                return "accepted"
            except ScheduleConflict:
                return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(writer, ((self.store, "one"), (other, "two"))))
        self.assertEqual(sorted(results), ["accepted", "conflict"])
        self.assertEqual(self.event()["version"], 2)

    def test_post_commit_competing_writer_prevents_success_receipt(self):
        other = native.ScheduleEventStore(self.root, SOURCE, "fixture-principal")
        original_read = self.store.read
        def raced_read(event_id):
            other.apply(operation("update", 1, key="competing"))
            return original_read(event_id)
        with patch.object(self.store, "read", side_effect=raced_read), self.assertRaisesRegex(ScheduleConflict, "POST_EFFECT_READBACK_CHANGED"):
            self.store.apply(operation())
        self.assertEqual(self.event()["version"], 2)
        self.assertEqual(len(native.validate_snapshot(self.store.export())["operations"]), 2)

    def test_out_of_order_operations_fail_then_reordered_retry_is_idempotent(self):
        update = operation("update", 1, key="update")
        with self.assertRaises(ScheduleConflict):
            self.store.apply(update)
        self.store.apply(operation())
        with self.assertRaises(ScheduleConflict):
            self.store.apply(operation("update", 2, key="ahead"))
        self.store.apply(update)
        self.assertTrue(self.store.apply(operation())["historical_only"])
        self.assertTrue(self.store.apply(update)["replay"])
        self.assertEqual(self.event()["version"], 2)

    def test_deterministic_event_and_due_order_do_not_depend_on_insertion(self):
        ids = [native.identity("event", "order", str(i)) for i in range(3)]
        for event_id in sorted(ids, reverse=True):
            self.store.apply(operation(event=event_id, key=event_id))
        self.assertEqual([e["event_id"] for e in self.store.read()["events"]], sorted(ids))
        plan = self.store.plan("2026-10-01T00:00:00Z")
        self.assertEqual([e["event_id"] for e in plan["entries"]], sorted(ids))
        self.assertFalse(plan["dispatch_performed"])

    def test_delete_tombstone_is_durable_and_cannot_resurrect_identity(self):
        self.store.apply(operation())
        deletion = operation("delete", 1, key="delete")
        self.store.apply(deletion)
        tombstone = self.event()
        self.assertTrue(tombstone["deleted"])
        self.assertIsNone(tombstone["value"])
        self.assertEqual(tombstone["version"], 2)
        self.assertTrue(self.store.apply(deletion)["replay"])
        for request in (operation("create", 2, key="resurrect"), operation("update", 2, key="resurrect2")):
            with self.assertRaises(ScheduleConflict):
                self.store.apply(request)
        self.assertEqual(self.store.plan("2026-10-01T00:00:00Z")["entries"], [])
        self.assertEqual(native.validate_snapshot(self.store.export())["events"], [tombstone])
        synced = self.store.record_sync(receipt(tombstone))
        self.assertEqual(synced["state"], "PROVIDED_READBACK_MATCH")
        self.assertFalse(synced["external_effect_verified"])

    def test_transport_ack_is_not_effect_and_observation_is_only_imported_evidence(self):
        self.store.apply(operation())
        transport = self.store.record_sync(receipt(self.event(), key="transport", observed=False))
        self.assertEqual(transport["state"], "TRANSPORT_ONLY")
        for key in ("external_effect_verified", "effect_ack_done", "connector_observation_authenticity_verified"):
            self.assertFalse(transport[key])
        evidence = self.store.record_sync(receipt(self.event(), transport=False))
        self.assertEqual(evidence["state"], "PROVIDED_READBACK_MATCH")
        self.assertFalse(evidence["effect_ack_done"])
        self.assertFalse(evidence["connector_observation_authenticity_verified"])

    def test_contradictory_sync_fields_fail_closed_without_writes(self):
        self.store.apply(operation())
        good = receipt(self.event())
        variants = []
        for field, value in (("event_sha256", "a" * 64), ("event_version", 2), ("transport_ack", 1)):
            variants.append(dict(good, **{field: value}))
        variants += [dict(good, source_subject=dict(SOURCE, role="AUTHORITY")),
                     dict(good, source_subject=dict(SOURCE, head="a" * 40)),
                     dict(good, effect_ack_done=True)]
        wrong_readback = copy.deepcopy(good)
        wrong_readback["observation"]["readback"]["deleted"] = True
        variants.append(wrong_readback)
        for delta in (timedelta(minutes=-6), timedelta(minutes=1)):
            bad = copy.deepcopy(good)
            bad["observation"]["observed_at_utc"] = stamp((datetime.now(timezone.utc) + delta).replace(microsecond=0))
            variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.store.record_sync(bad)
        self.assertEqual(self.store.read()["sync_receipts"], [])

    def test_sync_idempotency_collision_and_mutation_invalidates_old_receipts(self):
        self.store.apply(operation())
        good = receipt(self.event())
        self.store.record_sync(good)
        self.store.record_sync(good)
        self.assertEqual(len(self.store.read()["sync_receipts"]), 1)
        changed = copy.deepcopy(good)
        changed["observation"]["target_revision"] = "collision"
        with self.assertRaisesRegex(ScheduleConflict, "RECEIPT_ID_CONTENT_COLLISION"):
            self.store.record_sync(changed)
        self.store.apply(operation("update", 1, key="update"))
        self.assertEqual(self.store.read()["sync_receipts"], [])
        with self.assertRaisesRegex(ScheduleConflict, "EXACT_SUBJECT_OR_EVENT"):
            self.store.record_sync(good)
        with self.assertRaisesRegex(ScheduleConflict, "CONTRADICTORY_TARGET_REVISION"):
            self.store.record_sync(receipt(self.event(), key="conflict"))
        self.store.record_sync(receipt(self.event(), key="successor", revision="remote-revision-2"))
        packet = native.validate_snapshot(self.store.export())
        self.assertEqual(len(packet["sync_receipts"]), 2)

    def test_authority_mirror_head_and_principal_evidence_are_separate(self):
        self.store.apply(operation())
        good = receipt(self.event())
        self.store.record_sync(good)
        authority = native.ScheduleEventStore(self.root, dict(SOURCE, role="AUTHORITY"), "fixture-principal")
        principal = native.ScheduleEventStore(self.root, SOURCE, "another-principal")
        repository = native.ScheduleEventStore(self.root, dict(SOURCE, repository="other/repo"), "fixture-principal")
        for other in (authority, principal, repository):
            self.assertEqual(other.read()["events"], [])
        for other in (authority, repository):
            with self.assertRaises(ScheduleConflict):
                other.restore(self.store.export())
        principal.restore(self.store.export())
        with self.assertRaises(ScheduleConflict):
            principal.restore(self.store.export())
        successor = native.ScheduleEventStore(self.root, dict(SOURCE, head="b" * 40, tree="c" * 40), "fixture-principal")
        self.assertEqual(len(successor.read()["events"]), 1)
        self.assertEqual(successor.read()["sync_receipts"], [])
        self.assertTrue(successor.apply(operation())["historical_only"])
        with self.assertRaises(ScheduleConflict):
            successor.record_sync(good)
        fresh = receipt(self.event(), key="fresh", source=successor.subject)
        successor.record_sync(fresh)
        self.assertEqual(len(successor.read()["sync_receipts"]), 1)
        self.assertFalse(successor.read()["pole_equality_claim"])

    def test_replayed_history_never_becomes_a_new_effect_receipt(self):
        self.store.apply(operation())
        with tempfile.TemporaryDirectory() as directory:
            target = native.ScheduleEventStore(directory, SOURCE, "fixture-principal")
            target.restore(self.store.export())
            replay = target.apply(operation())
            self.assertTrue(replay["historical_only"])
            self.assertTrue(replay["current_readback_matches_original"])
            self.assertFalse(replay["local_post_effect_readback_verified"])
            self.assertFalse(replay["effect_ack_done"])

    def test_missing_tzif_provider_does_not_approximate_local_time(self):
        request = operation()
        with patch.object(native.zoneinfo, "TZPATH", ()), self.assertRaisesRegex(ValueError, "TZIF_PROVIDER_UNAVAILABLE"):
            self.store.apply(request)
        self.assertEqual(self.store.read()["events"], [])

    def test_snapshot_tamper_duplicate_reorder_unknown_and_noncanonical_json(self):
        self.store.apply(operation())
        self.store.apply(operation("update", 1, key="update"))
        packet = native.validate_snapshot(self.store.export())
        variants = []
        for field in ("events", "operations"):
            bad = copy.deepcopy(packet)
            bad[field].append(copy.deepcopy(bad[field][0]))
            variants.append(bad)
        bad = copy.deepcopy(packet)
        bad["operations"].reverse()
        variants.append(bad)
        bad = copy.deepcopy(packet)
        bad["operations"][1]["before_sha256"] = "0" * 64
        variants.append(bad)
        bad = copy.deepcopy(packet)
        bad["events"][0]["version"] = 99
        variants.append(bad)
        variants.append(dict(packet, unknown=True))
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                native.validate_snapshot(canonical(bad).encode())
        for raw in (json.dumps(packet, indent=2).encode(), b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":1.0}', b'\xef\xbb\xbf{}'):
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                native.validate_snapshot(raw)

    def test_snapshot_conflicting_sync_receipts_fail_closed_on_restore(self):
        self.store.apply(operation())
        good = receipt(self.event())
        self.store.record_sync(good)
        packet = native.validate_snapshot(self.store.export())
        conflicting = copy.deepcopy(good)
        conflicting["receipt_id"] = native.identity("receipt", "fixture", "tampered")
        conflicting["observation"]["readback"]["value"]["title"] = "not the stored event"
        packet["sync_receipts"].append(conflicting)
        packet["sync_receipts"].sort(key=lambda r: r["receipt_id"])
        with tempfile.TemporaryDirectory() as directory:
            target = native.ScheduleEventStore(directory, SOURCE, "fixture-principal")
            with self.assertRaises(ScheduleConflict):
                target.restore(canonical(packet).encode())
            self.assertEqual(target.read()["events"], [])

    def test_snapshot_capacity_rejection_rolls_back_entire_cas_write(self):
        self.store.apply(operation())
        prior = self.store.export()
        with patch.object(native, "MAX_SNAPSHOT_BYTES", len(prior) + 128), self.assertRaisesRegex(ValueError, "SNAPSHOT_CAPACITY"):
            self.store.apply(operation("update", 1, key="capacity"))
        self.assertEqual(self.store.export(), prior)

    def test_payload_depth_budget_keeps_every_accepted_history_exportable(self):
        payload = "leaf"
        for _ in range(12):
            payload = [payload]
        self.store.apply(operation(value=dict(configuration(), payload=payload)))
        native.validate_snapshot(self.store.export())
        with self.assertRaisesRegex(ValueError, "DEPTH"):
            self.store.apply(operation("update", 1, key="too-deep", value=dict(configuration(), payload=[payload])))
        self.assertEqual(self.event()["version"], 1)


class NativeHttpTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"QIKVRT_SCHEDULE_ROLE": "MIRROR", "QIKVRT_SCHEDULE_HEAD": "1" * 40,
                                           "QIKVRT_SCHEDULE_TREE": "2" * 40})
        self.env.start()
        self.client = tcpip.TcpIpEndToEndTests()
        self.client.setUp()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.client.tearDown)

    def test_authenticated_create_update_delete_sync_snapshot_and_contract(self):
        request = operation()
        code, result = self.client.request("POST", native.BASE + "/operations", request)
        self.assertEqual(code, 200, result)
        self.assertTrue(result["local_post_effect_readback_verified"])
        self.assertEqual(self.client.request("POST", native.BASE + "/operations", request)[0], 200)
        code, readback = self.client.request("GET", native.BASE + "/" + EVENT)
        self.assertEqual(code, 200, readback)
        source = dict(SOURCE, repository="owner/repo")
        code, sync = self.client.request("POST", native.BASE + "/sync-receipts", receipt(readback["events"][0], source=source))
        self.assertEqual(code, 200, sync)
        self.assertFalse(sync["external_effect_verified"])
        self.assertEqual(self.client.request("POST", native.BASE + "/operations", operation("update", 1, key="update"))[0], 200)
        self.assertEqual(self.client.request("POST", native.BASE + "/operations", operation("delete", 2, key="delete"))[0], 200)
        code, snapshot = self.client.request("GET", native.BASE + "/snapshot")
        self.assertEqual(code, 200, snapshot)
        self.assertTrue(native.validate_snapshot(snapshot["snapshot"].encode())["events"][0]["deleted"])
        code, contract = self.client.request("GET", native.BASE + "/contract")
        self.assertEqual(code, 200, contract)
        self.assertEqual(contract["base_path"], native.BASE)
        self.assertFalse(contract["invariants"]["predecessor_evidence_transfer"])

    def test_auth_closed_requests_stale_cas_and_query_rejection(self):
        for method, path, body in (("GET", native.BASE, None), ("POST", native.BASE + "/operations", operation())):
            self.assertEqual(self.client.request(method, path, body, token=False)[0], 401)
        self.assertEqual(self.client.request("POST", native.BASE + "/operations", dict(operation(), extra=True))[0], 400)
        self.assertEqual(self.client.request("POST", native.BASE + "/operations", operation())[0], 200)
        self.assertEqual(self.client.request("POST", native.BASE + "/operations", operation(key="stale"))[0], 409)
        self.assertEqual(self.client.request("GET", native.BASE + "?role=AUTHORITY")[0], 404)
        self.assertEqual(self.client.request("POST", native.BASE + "/plan", {"after_utc": "2026-10-01T00:00:00Z"})[0], 200)

    def test_http_roundtrip_replay_larger_than_normal_request_limit(self):
        value = dict(configuration(), payload={"opaque_data": "x" * 100000})
        for i in range(4):
            code, response = self.client.request("POST", native.BASE + "/operations",
                                                operation(event=native.identity("event", "large", str(i)), key="large" + str(i), value=value))
            self.assertEqual(code, 200, response)
        code, exported = self.client.request("GET", native.BASE + "/snapshot")
        self.assertEqual(code, 200)
        self.assertGreater(len(exported["snapshot"].encode()), 1024 * 1024)
        other = tcpip.TcpIpEndToEndTests()
        other.setUp()
        try:
            code, restored = other.request("POST", native.BASE + "/replay", {"snapshot": exported["snapshot"]})
            self.assertEqual(code, 200, restored)
            self.assertFalse(restored["effect_ack_done"])
            self.assertEqual(other.request("GET", native.BASE + "/snapshot")[1]["snapshot"], exported["snapshot"])
        finally:
            other.tearDown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
