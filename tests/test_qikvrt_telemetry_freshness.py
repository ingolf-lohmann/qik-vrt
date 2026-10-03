# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Local Git fixtures exercise receipt clocks and exact-subject readback."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import qikvrt_reflexive_repository_watchdog as collector

REPOSITORY = "ingolf-lohmann/qik-vrt"
NOW = "2026-09-30T13:00:00Z"
RECEIPT = {
    "qikvrt_event": "NODE_HEALTH_EVIDENCE", "repository": REPOSITORY,
    "guid": "fixture-node", "run_id": "trial-1", "status": "PASS",
    "heartbeat_utc": "2026-09-30T12:00:00Z", "expires_utc": "2026-09-30T14:00:00Z",
}


class TelemetryFreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.git("init", "--quiet")
        (self.root / "policy").mkdir()
        (self.root / "policy/PIPELINE_KPI_TREE_V1.json").write_bytes(
            (ROOT / "policy/PIPELINE_KPI_TREE_V1.json").read_bytes()
        )
        (self.root / "evidence/node_health").mkdir(parents=True)
        self.write_receipt(RECEIPT)
        self.commit()

    def git(self, *arguments: str) -> str:
        return subprocess.check_output(
            ["git", "--no-optional-locks", "-C", str(self.root), *arguments],
            text=True, stderr=subprocess.PIPE,
        ).strip()

    def commit(self) -> None:
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--quiet", "--allow-empty", "-m", "fixture")
        self.head = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")

    def write_receipt(self, receipt: object, *, raw: bytes | None = None) -> bytes:
        data = raw if raw is not None else (json.dumps(receipt) + "\n").encode()
        for name in ("LATEST.json", "trial-1.json"):
            (self.root / "evidence/node_health" / name).write_bytes(data)
        return data

    def collect(self, **overrides: object) -> dict[str, object]:
        arguments = dict(root=self.root, expected_head=self.head, expected_tree=self.tree,
                         repository=REPOSITORY, now=NOW)
        arguments.update(overrides)
        record = collector.collect_telemetry_freshness(**arguments)
        self.assert_record_schema(record)
        encoded = collector.canonical_json_bytes(record)
        decoded = collector._telemetry_json(encoded)
        self.assertEqual(decoded, record)
        self.assertEqual(collector.canonical_json_bytes(decoded), encoded)
        return record

    def assert_record_schema(self, record: dict[str, object]) -> None:
        """Validate the existing versioned KPI record contract on every case."""
        policy = json.loads((ROOT / "policy/PIPELINE_KPI_TREE_V1.json").read_bytes())
        contract = policy["record_contract"]
        self.assertTrue(set(contract["required"]).issubset(record))
        self.assertIn(record["status"], contract["status_enum"])
        self.assertEqual(record["schema"], "qikvrt_telemetry_freshness_v1")
        self.assertEqual(record["metric_id"], "telemetry_freshness")
        self.assertEqual(record["unit"], "seconds")
        self.assertIn(record["freshness"], ("FRESH", "STALE", "UNKNOWN"))
        self.assertRegex(record["subject_head"], r"^[0-9a-f]{40}$")
        self.assertRegex(record["subject_tree"], r"^[0-9a-f]{40}$")
        self.assertRegex(record["policy_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(record["policy_hash"], record["policy_ref"]["sha256"])
        for field in ("observed_at_utc", "window_start_utc", "window_end_utc"):
            collector._telemetry_time(record[field], field)
            self.assertEqual(record[field], record["observed_at_utc"])
        for field in ("age_seconds", "value", "raw_numerator"):
            value = record[field]
            if value is not None:
                self.assertIn(type(value), (int, float))
                self.assertTrue(math.isfinite(value))
        self.assertEqual(record["raw_numerator"], record["age_seconds"])
        self.assertIs(type(record["raw_denominator_or_sample_count"]), int)
        self.assertIn(record["raw_denominator_or_sample_count"], (0, 1))
        self.assertIsNone(record["target"])
        self.assertIsNone(record["coverage"])
        self.assertEqual(record["slo_verdict"], "UNKNOWN")
        self.assertEqual(record["threshold_status"], "UNSET_REQUIRES_VERSIONED_SERVICE_CONTRACT")
        self.assertIs(record["clock_accuracy_verified"], False)
        self.assertIs(record["PREDECESSOR_EVIDENCE_TRANSFER"], False)
        if record["status"] == "MEASURED":
            self.assertIn(record["freshness"], ("FRESH", "STALE"))
            self.assertEqual(record["value"], record["age_seconds"])
            self.assertGreaterEqual(record["value"], 0)
        else:
            self.assertEqual(record["freshness"], "UNKNOWN")
            self.assertIsNone(record["value"])
        self.assertIsInstance(record["source_refs"], list)
        self.assertGreaterEqual(len(record["source_refs"]), 1)
        for ref in record["source_refs"]:
            self.assertEqual(set(ref), {"path", "git_blob_sha1", "sha256", "bytes", "read_status"})
            if ref["read_status"] == "READ":
                self.assertRegex(ref["git_blob_sha1"], r"^[0-9a-f]{40}$")
                self.assertRegex(ref["sha256"], r"^[0-9a-f]{64}$")
                self.assertIs(type(ref["bytes"]), int)
                self.assertGreaterEqual(ref["bytes"], 0)
        if record["evaluator_state"] == "COMMITTED_EXACT_BYTES":
            self.assertRegex(record["evaluator_commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(record["evaluator_tree"], r"^[0-9a-f]{40}$")
        else:
            self.assertEqual(record["evaluator_state"], "UNCOMMITTED_CANDIDATE")
            self.assertIsNone(record["evaluator_commit"])
            self.assertIsNone(record["evaluator_tree"])

    def test_fresh_receipt_and_all_kpi_record_fields(self) -> None:
        record = self.collect()
        self.assertEqual((record["freshness"], record["status"], record["value"]),
                         ("FRESH", "MEASURED", 3600))
        self.assertEqual(record["observed_at_utc"], NOW)
        self.assertEqual(record["subject_head"], self.head)
        self.assertEqual(record["subject_tree"], self.tree)
        policy = json.loads((ROOT / "policy/PIPELINE_KPI_TREE_V1.json").read_bytes())
        self.assertTrue(set(policy["record_contract"]["required"]).issubset(record))
        self.assertIsNone(record["target"])
        self.assertEqual(record["threshold_status"], "UNSET_REQUIRES_VERSIONED_SERVICE_CONTRACT")
        self.assertEqual(record["slo_verdict"], "UNKNOWN")
        self.assertFalse(record["clock_accuracy_verified"])

    def test_expiry_boundary_and_stale_preserve_real_age(self) -> None:
        for now, age in (("2026-09-30T14:00:00Z", 7200), ("2026-10-02T12:00:00Z", 172800)):
            with self.subTest(now=now):
                record = self.collect(now=now)
                self.assertEqual((record["freshness"], record["status"], record["age_seconds"]),
                                 ("STALE", "MEASURED", age))

    def test_missing_receipt_is_unknown_not_zero(self) -> None:
        for path in (self.root / "evidence/node_health").iterdir():
            path.unlink()
        self.commit()
        record = self.collect()
        self.assertEqual((record["freshness"], record["status"], record["reason"]),
                         ("UNKNOWN", "UNKNOWN", "MISSING_RECEIPT"))
        self.assertIsNone(record["value"])
        self.assertIsNone(record["age_seconds"])
        self.assertIsNone(record["source_refs"][0]["sha256"])

    def test_missing_timestamp_preserves_source_and_partial_age(self) -> None:
        for field in ("heartbeat_utc", "expires_utc"):
            for missing in ("absent", "null"):
                with self.subTest(field=field, missing=missing):
                    receipt = copy.deepcopy(RECEIPT)
                    if missing == "absent":
                        del receipt[field]
                    else:
                        receipt[field] = None
                    self.write_receipt(receipt)
                    self.commit()
                    record = self.collect()
                    self.assertEqual((record["freshness"], record["status"]), ("UNKNOWN", "UNKNOWN"))
                    self.assertEqual(record["source_receipt"], receipt)
                    self.assertIsNone(record["value"])
                    self.assertEqual(record["age_seconds"], 3600 if field == "expires_utc" else None)

    def test_malformed_timestamps_are_invalid_and_not_coerced(self) -> None:
        bad_values = ["not-a-time", "2026-09-30T12:00:00", "2026-02-30T12:00:00Z",
                      "2026-09-30 12:00:00Z", "2026-09-30T12:00:00-00:00",
                      "2026-09-30T12:00:00+00:60", "0001-01-01T00:00:00+23:00",
                      "", 0, False, [], {}]
        for field in ("heartbeat_utc", "expires_utc"):
            for invalid in bad_values:
                with self.subTest(field=field, invalid=invalid):
                    receipt = dict(RECEIPT, **{field: invalid})
                    self.write_receipt(receipt)
                    self.commit()
                    record = self.collect()
                    self.assertEqual((record["freshness"], record["status"]), ("UNKNOWN", "INVALID"))
                    self.assertEqual(record["source_receipt"][field], invalid)
                    self.assertIsNone(record["value"])
                    self.assertEqual(record["age_seconds"], 3600 if field == "expires_utc" else None)

    def test_malformed_evidence_keeps_exact_byte_binding(self) -> None:
        for raw in (b"{", b"\xff\n", b"[]", b'{"heartbeat_utc":0,"heartbeat_utc":1}',
                    b'{"x":NaN}', b'{"x":1e999}',
                    b'{"x":"\\ud800"}', b'{"x":' + b'[' * 1200 + b'0' + b']' * 1200 + b'}'):
            with self.subTest(raw=raw):
                self.write_receipt(None, raw=raw)
                self.commit()
                record = self.collect()
                self.assertEqual((record["freshness"], record["status"], record["reason"]),
                                 ("UNKNOWN", "INVALID", "MALFORMED_RECEIPT"))
                self.assertIsNone(record["value"])
                ref = record["source_refs"][0]
                self.assertEqual(ref["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(ref["bytes"], len(raw))
                self.assertEqual(ref["git_blob_sha1"], self.git("rev-parse", f"{self.head}:evidence/node_health/LATEST.json"))

    def test_future_and_reversed_clocks_are_not_fresh(self) -> None:
        for changes in ({"heartbeat_utc": "2026-09-30T13:00:01Z"},
                        {"expires_utc": RECEIPT["heartbeat_utc"]},
                        {"expires_utc": "2026-09-30T11:59:59Z"}):
            with self.subTest(changes=changes):
                self.write_receipt(dict(RECEIPT, **changes))
                self.commit()
                record = self.collect()
                self.assertEqual((record["freshness"], record["status"]), ("UNKNOWN", "INVALID"))
                self.assertIsNone(record["value"])
                if "heartbeat_utc" in changes:
                    self.assertEqual(record["age_seconds"], -1)

    def test_fractional_and_offset_clocks_preserve_precision(self) -> None:
        self.write_receipt(dict(RECEIPT, heartbeat_utc="2026-09-30T14:00:00.125+02:00"))
        self.commit()
        record = self.collect(now="2026-09-30T13:00:00.375Z")
        self.assertEqual(record["age_seconds"], 3600.25)
        self.assertEqual(record["observed_at_utc"], "2026-09-30T13:00:00.375Z")
        self.assertEqual(record["freshness"], "FRESH")

    def test_wrong_subject_and_bad_readback_time_block(self) -> None:
        for changes in ({"expected_tree": "0" * 40}, {"expected_head": "main"},
                        {"expected_head": "0" * 40}, {"now": "yesterday"},
                        {"now": "2026-09-30T13:00:00"}, {"run_id": "../LATEST"}):
            with self.subTest(changes=changes):
                with self.assertRaises(collector.ReflexiveWatchdogBlock):
                    self.collect(**changes)

    def test_receipt_identity_must_match_requested_node_repository_and_run(self) -> None:
        for changes in ({"repository": "Goldkelch/qik-vrt"}, {"guid": ""},
                        {"qikvrt_event": "OTHER"}, {"run_id": "../elsewhere"}):
            with self.subTest(changes=changes):
                self.write_receipt(dict(RECEIPT, **changes))
                self.commit()
                record = self.collect()
                self.assertEqual((record["freshness"], record["status"]), ("UNKNOWN", "INVALID"))

    def test_latest_requires_byte_identical_run_receipt(self) -> None:
        path = self.root / "evidence/node_health/trial-1.json"
        path.write_text(json.dumps(dict(RECEIPT, status="OTHER")))
        self.commit()
        record = self.collect()
        self.assertEqual((record["freshness"], record["status"]), ("UNKNOWN", "INVALID"))
        path.unlink()
        self.commit()
        record = self.collect()
        self.assertEqual((record["freshness"], record["status"]), ("UNKNOWN", "UNKNOWN"))

    def test_explicit_run_receipt_is_independent_of_latest(self) -> None:
        (self.root / "evidence/node_health/LATEST.json").unlink()
        self.commit()
        record = self.collect(run_id="trial-1")
        self.assertEqual(record["freshness"], "FRESH")
        self.assertEqual(len(record["source_refs"]), 1)

    def test_explicit_run_identity_mismatch_is_invalid(self) -> None:
        self.write_receipt(dict(RECEIPT, run_id="different-2"))
        self.commit()
        record = self.collect(run_id="trial-1")
        self.assertEqual(record["reason"], "RECEIPT_RUN_ID_MISMATCH")
        self.assertEqual(record["status"], "INVALID")

    def test_oversized_receipt_is_not_measured(self) -> None:
        self.write_receipt(None, raw=b" " * 262145)
        self.commit()
        record = self.collect()
        self.assertEqual((record["status"], record["reason"]), ("INVALID", "OVERSIZED"))
        self.assertEqual(record["source_refs"][0]["bytes"], 262145)

    def test_missing_malformed_and_changed_metric_policy_fail_closed(self) -> None:
        path = self.root / "policy/PIPELINE_KPI_TREE_V1.json"
        original = path.read_bytes()
        for raw in (None, b"{", b'{"metrics":[]}',
                    b'{"metrics":[{"id":"telemetry_freshness","unit":"seconds",'
                    b'"target":1,"threshold_status":"UNSET_REQUIRES_VERSIONED_SERVICE_CONTRACT"}]}'):
            with self.subTest(raw=raw):
                if raw is None:
                    path.unlink()
                else:
                    path.write_bytes(raw)
                self.commit()
                with self.assertRaises(collector.ReflexiveWatchdogBlock):
                    self.collect()
                path.write_bytes(original)

    def test_roundtrip_schema_for_all_measurement_states(self) -> None:
        self.assertEqual(self.collect()["freshness"], "FRESH")
        self.assertEqual(self.collect(now="2026-09-30T14:00:00Z")["freshness"], "STALE")
        self.write_receipt(dict(RECEIPT, expires_utc=None))
        self.commit()
        self.assertEqual(self.collect()["status"], "UNKNOWN")
        self.write_receipt(dict(RECEIPT, expires_utc="invalid"))
        self.commit()
        self.assertEqual(self.collect()["status"], "INVALID")

    def test_canonical_serializer_rejects_nonfinite_output(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                record = self.collect()
                record["value"] = value
                with self.assertRaises(ValueError):
                    collector.canonical_json_bytes(record)

    def test_no_worktree_evidence_or_predecessor_transfer(self) -> None:
        predecessor_head, predecessor_tree = self.head, self.tree
        (self.root / "evidence/node_health/LATEST.json").write_bytes(b"malformed dirty data")
        record = self.collect()
        self.assertEqual(record["freshness"], "FRESH")
        self.commit()
        self.assertEqual(self.collect()["status"], "INVALID")
        previous = self.collect(expected_head=predecessor_head, expected_tree=predecessor_tree)
        self.assertEqual(previous["subject_head"], predecessor_head)
        self.assertEqual(previous["freshness"], "FRESH")
        self.assertFalse(previous["PREDECESSOR_EVIDENCE_TRANSFER"])

    def test_symlink_evidence_is_unknown_invalid(self) -> None:
        path = self.root / "evidence/node_health/LATEST.json"
        path.unlink()
        path.symlink_to("trial-1.json")
        self.commit()
        self.assertEqual((self.collect()["freshness"], self.collect()["status"]), ("UNKNOWN", "INVALID"))

    def test_evaluator_ref_movement_cannot_mix_commit_and_tree(self) -> None:
        (self.root / "tools").mkdir()
        for name in ("qikvrt_reflexive_repository_watchdog.py", "qikvrt_subprocess.py"):
            (self.root / "tools" / name).write_bytes((ROOT / "tools" / name).read_bytes())
        self.commit()
        subject_head, subject_tree = self.head, self.tree
        git_reader = collector._telemetry_git

        def competing_writer(root: pathlib.Path, *arguments: str) -> bytes:
            result = git_reader(root, *arguments)
            if arguments == ("rev-parse", "HEAD"):
                (self.root / "unrelated.txt").write_text("another writer moved the ref\n")
                self.commit()
            return result

        with mock.patch.object(collector, "ROOT", self.root), mock.patch.object(
            collector, "_telemetry_git", competing_writer
        ):
            record = self.collect(expected_head=subject_head, expected_tree=subject_tree)
        self.assertNotEqual(self.head, subject_head)
        self.assertEqual(record["evaluator_commit"], subject_head)
        self.assertEqual(record["evaluator_tree"], subject_tree)
        self.assertEqual(record["evaluator_state"], "COMMITTED_EXACT_BYTES")

    def test_cli_deterministic_readback_and_no_repository_mutation(self) -> None:
        before = self.git("status", "--porcelain=v1", "--untracked-files=all")
        before_tree = self.git("write-tree")
        command = [sys.executable, "-B", str(ROOT / "tools/qikvrt_reflexive_repository_watchdog.py"),
                   "telemetry-freshness", "--root", str(self.root), "--expect-head", self.head,
                   "--expect-tree", self.tree, "--repository", REPOSITORY, "--now", NOW]
        first = subprocess.check_output(command)
        second = subprocess.check_output(command)
        self.assertEqual(first, second)
        self.assertEqual(first, collector.canonical_json_bytes(self.collect()))
        self.assertEqual(self.git("status", "--porcelain=v1", "--untracked-files=all"), before)
        self.assertEqual(self.git("write-tree"), before_tree)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)


if __name__ == "__main__":
    unittest.main()
