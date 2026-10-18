# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Actual frozen CLI/process/SQLite/Node tests; no live Railway/Own-Host effect."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sqlite3
import subprocess
import sys
import unittest
from unittest import mock

from tests import test_self_host as fixtures
from tools import qikvrt_self_host_migration as migration
ROOT, host = fixtures.ROOT, fixtures.host


class MigrationTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.StandaloneTests.tearDownClass.__func__)
    save_config = fixtures.StandaloneTests.save_config
    command = fixtures.StandaloneTests.command
    denied = fixtures.StandaloneTests.denied
    stop = fixtures.StandaloneTests.stop

    def setUp(self):
        fixtures.StandaloneTests.setUp(self)
        self.volume.rmdir()  # The fixture target is deliberately create-only.
        self.config.update(terminal_profile="temdd", subject_pr=457,
                           source_repository="ingolf-lohmann/qik-vrt", node_id="fixture:railway")
        self.save_config()
        self.snapshot = self.work / "offline-snapshot"; self.snapshot.mkdir(mode=0o700)
        self.bundle = self.work / "transfer"
        self.witness = self.work / "capture.json"
        self.native = migration.native_source(self.export, host.load_source)
        self.subject = {"repository": "Goldkelch/qik-vrt", "pr": 1103, "head": "a" * 40, "tree": "b" * 40}
        (self.snapshot / "state").mkdir(mode=0o700)
        ledger = self.native.Ledger(self.snapshot / "state", self.subject)
        self.event = ledger.append(self.native_event("fixture:first")); ledger.close()
        def file(name, data): migration.write(self.snapshot / name, data)
        file("binding.json", migration.raw({"schema": "qikvrt-self-host-volume/v1",
            "node_id": self.config["node_id"], "source_head": self.subject["head"],
            "source_tree": self.subject["tree"], "manifest_sha256": "c" * 64, "config_sha256": "d" * 64}))
        file("node.lock", b"")
        file("receipts/acknowledged.json", b'{"fixture":"previously-acknowledged"}\n')
        file("state/live/QIKVRT_LIVE_EVENTS.jsonl", b'{"id":"legacy:1","fixture":true}\n')
        (self.snapshot / "empty-directory").mkdir(mode=0o700)
        (self.snapshot / "profile").mkdir(mode=0o700)
        with sqlite3.connect(self.snapshot / "profile/storage.sqlite") as db:
            db.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
            db.execute("INSERT INTO notes VALUES (1,?)", ("private synthetic fixture Ω",))
        (self.snapshot / "profile/storage.sqlite").chmod(0o600)
        program = """import {MonitorStore,VERSION} from %s;
import {createHash} from 'node:crypto';
const path=process.argv[1];const store=new MonitorStore(path,'fixture:railway');
const payload=Buffer.from('{"fixture":true}');
store.update({schema:'qikvrt-public-activity/v1',version:VERSION,fixture:true},
 {id:'fixture:delivery',event:'push',repository:'Goldkelch/qik-vrt',
 payload_base64:payload.toString('base64'),payload_sha256:createHash('sha256').update(payload).digest('hex'),
 observed_at:'2026-10-05T08:00:00Z',verification:'SYNTHETIC_FIXTURE'});
""" % json.dumps((self.export / "docs/monitor/server.mjs").as_uri())
        subprocess.run(["node", "--input-type=module", "-e", program, str(self.snapshot / "monitor/node.json")],
                       check=True, capture_output=True, timeout=10)
        self.seal()

    def native_event(self, identity):
        return {"schema": self.native.SCHEMA, "kind": "OBSERVE", "subject": self.subject,
            "provenance": {"source": "transputer", "native_event_id": identity},
            "observed_at": "2026-10-05T08:00:00Z", "message": "synthetic migration control Ω",
            "payload": {"fixture": True, "effect_ack_done": False}}

    def seal(self):
        self.before = migration.inventory(self.snapshot)
        self.declaration = {"schema": migration.SOURCE_SCHEMA, "carrier": migration.SOURCE_CARRIER,
            "source_repository": "Goldkelch/qik-vrt", "source_head": self.subject["head"], "source_tree": self.subject["tree"],
            "snapshot_id": "SYNTHETIC_LOCAL_FIXTURE_ONLY", "capture_evidence_sha256": "e" * 64,
            "consistency": "QUIESCED_OFFLINE_SNAPSHOT", "inventory_sha256": migration.sha(migration.raw(self.before)),
            "layout": {"ledger": "state/temdd/events.sqlite3", "monitor": "monitor/node.json", "binding": "binding.json",
                       "locks": ["state/temdd/owner.lock", "node.lock"], "jsonl": ["state/live/QIKVRT_LIVE_EVENTS.jsonl"]}}
        self.witness.write_bytes(migration.raw(self.declaration)); self.witness.chmod(0o600)
        self.source_pin = migration.sha(self.witness.read_bytes())

    def cli(self, operation, *extra, expected=0):
        command = [sys.executable, "-B", str(self.export / "tools/qikvrt_self_host.py"), operation,
                   "--root", str(self.export), "--manifest-sha256", self.pin]
        if operation in {"migration-inventory", "migration-verify-source", "migration-export"}:
            command += ["--snapshot", str(self.snapshot)]
        if operation in {"migration-verify-source", "migration-export"}:
            command += ["--source-declaration", str(self.witness), "--source-declaration-sha256", self.source_pin]
        if operation == "migration-export": command += ["--output", str(self.bundle)]
        if operation in {"migration-import", "migration-verify-export", "migration-verify-import", "migration-rollback"}:
            command += ["--bundle", str(self.bundle), "--export-sha256", self.export_pin]
        if operation in {"migration-import", "migration-verify-import", "migration-rollback"}:
            command += ["--output", str(self.volume), "--config", str(self.config_path)]
        if operation in {"migration-verify-import", "migration-rollback"}:
            command += ["--import-sha256", self.import_pin]
        result = subprocess.run(command + list(extra), capture_output=True, text=True, timeout=60,
                                env={"PATH": os.environ["PATH"], "LANG": "C.UTF-8"})
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value["effect_ack_done"])
        return value

    def exported(self):
        result = self.cli("migration-export"); self.export_pin = result["export_sha256"]
        self.config["migration_export_sha256"] = self.export_pin; self.save_config()
        self.assertEqual(migration.inventory(self.snapshot), self.before)
        return result

    def imported(self):
        self.exported(); result = self.cli("migration-import"); self.import_pin = result["import_sha256"]
        return result

    def test_inventory_does_not_attest_capture_consistency_or_create_target(self):
        result = self.cli("migration-inventory")
        self.assertFalse(result["capture_consistency_verified"])
        self.assertFalse(self.volume.exists()); self.assertFalse(self.bundle.exists())
        self.assertEqual(result["inventory_sha256"], self.declaration["inventory_sha256"])

    def test_independent_source_export_import_and_dry_run_with_nonempty_history(self):
        self.cli("migration-verify-source"); self.exported()
        bundle_before = migration.inventory(self.bundle)
        dry = self.cli("migration-import", "--dry-run")
        self.assertEqual(dry["state"], "DRY_RUN_VERIFIED_NO_TARGET_WRITE")
        self.assertFalse(self.volume.exists()); self.assertEqual(migration.inventory(self.bundle), bundle_before)
        result = self.cli("migration-import"); self.import_pin = result["import_sha256"]
        self.assertFalse(result["host_admission_verified"]); self.assertFalse(result["public_readback_verified"])
        self.assertFalse((self.volume / migration.HOLD).exists())
        for path in self.volume.rglob("*"):
            if path.is_dir(): self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700, str(path))
        self.cli("migration-verify-import")
        self.assertEqual(migration.inventory(self.snapshot), self.before)
        migration.same_bytes(self.volume / "legacy/railway", self.before)
        with sqlite3.connect((self.volume / "temdd/events.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
            row = db.execute("SELECT body,body_digest FROM events").fetchone()
            self.assertEqual(json.loads(row[0])["subject"], self.subject)
            self.assertEqual(row[1], self.event["ledger_digest"])
            self.assertEqual(dict(db.execute("SELECT key,value FROM meta"))["epoch"], self.event["id"].split(":")[0])
        binding = json.loads((self.volume / "binding.json").read_bytes())
        self.assertEqual(binding["source_head"], self.head); self.assertEqual(binding["config_sha256"], host.digest(self.config_path.read_bytes()))
        self.assertEqual((self.volume / "monitor/node.json").read_bytes(), (self.snapshot / "monitor/node.json").read_bytes())
        self.assertNotEqual(binding, self.declaration)

    def wal_snapshot(self):
        live = self.work / "synthetic-producer"; live.mkdir(mode=0o700)
        ledger = self.native.Ledger(live, self.subject)
        ledger.append(self.native_event("fixture:wal-only"))
        try:
            for suffix in ("", "-wal", "-shm"):
                source = live / ("temdd/events.sqlite3" + suffix)
                dest = self.snapshot / ("state/temdd/events.sqlite3" + suffix)
                shutil.copyfile(source, dest); dest.chmod(0o600)
        finally: ledger.close()
        self.seal()

    def test_committed_wal_is_recovered_only_in_copy_and_original_sidecars_survive(self):
        self.wal_snapshot(); self.imported()
        self.assertGreater((self.volume / "legacy/railway/state/temdd/events.sqlite3-wal").stat().st_size, 32)
        with sqlite3.connect(self.volume / "temdd/events.sqlite3") as db:
            self.assertEqual(db.execute("SELECT native_id FROM events").fetchall(), [("fixture:wal-only",)])
        self.assertEqual(migration.inventory(self.snapshot), self.before)

    def test_wal_truncation_and_checksum_damage_are_not_silently_ignored(self):
        self.wal_snapshot(); path = self.snapshot / "state/temdd/events.sqlite3-wal"; original = path.read_bytes()
        for damaged in (original[:-1], original[:-10] + bytes([original[-10] ^ 1]) + original[-9:]):
            with self.subTest(size=len(damaged)):
                path.write_bytes(damaged); self.seal()
                value = self.cli("migration-export", expected=2)
                self.assertIn("SQLITE_WAL", value["cause"]); self.assertFalse(self.bundle.exists())

    def test_missing_wal_source_pin_and_source_change_hold_without_writing_export(self):
        self.wal_snapshot()
        (self.snapshot / "state/temdd/events.sqlite3-wal").unlink()
        value = self.cli("migration-export", expected=2)
        self.assertIn("OFFLINE_SNAPSHOT", value["cause"]); self.assertFalse(self.bundle.exists())

    def test_native_body_corruption_detected_even_with_valid_sqlite_and_resealed_file_digest(self):
        with sqlite3.connect(self.snapshot / "state/temdd/events.sqlite3") as db:
            db.execute("UPDATE events SET body_digest=?", ("0" * 64,))
        self.seal()
        result = self.cli("migration-export", expected=2)
        self.assertIn("NATIVE_EVENT", result["cause"]); self.assertFalse(self.bundle.exists())

    def test_sqlite_corruption_hot_journal_or_orphan_sidecar_holds(self):
        path = self.snapshot / "state/temdd/events.sqlite3"; original = path.read_bytes()
        path.write_bytes(b"not sqlite" + original[10:]); self.seal()
        self.assertIn("SQLITE", self.cli("migration-export", expected=2)["cause"])
        path.write_bytes(original)
        journal = self.snapshot / "state/temdd/events.sqlite3-journal"
        journal.write_bytes(b"hot journal"); journal.chmod(0o600); self.seal()
        self.assertIn("ROLLBACK_JOURNAL", self.cli("migration-export", expected=2)["cause"])
        journal.unlink()
        orphan = self.snapshot / "orphan.db-wal"; orphan.write_bytes(b"orphan"); orphan.chmod(0o600); self.seal()
        self.assertIn("ORPHAN_SQLITE", self.cli("migration-export", expected=2)["cause"])

    def test_monitor_chain_and_jsonl_truncation_fail_closed_after_resealing(self):
        path = self.snapshot / "monitor/node.json"; original = path.read_bytes(); state = json.loads(original)
        state["deliveries"][0]["previous_digest"] = "f" * 64
        path.write_bytes(migration.raw(state)); self.seal()
        self.assertIn("MONITOR_JOURNAL", self.cli("migration-export", expected=2)["cause"])
        path.write_bytes(original)
        (self.snapshot / "state/live/QIKVRT_LIVE_EVENTS.jsonl").write_bytes(b'{"id":"partial"}')
        self.seal()
        self.assertIn("TRUNCATED_JSONL", self.cli("migration-export", expected=2)["cause"])

    def test_source_writer_lock_blocks_export(self):
        path = self.snapshot / "state/temdd/owner.lock"
        with path.open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.cli("migration-export", expected=2)
            self.assertIn("unavailable", result["cause"].lower()); self.assertFalse(self.bundle.exists())

    def test_symlink_hardlink_socket_and_unknown_private_bytes_are_never_skipped(self):
        original = self.snapshot / "receipts/acknowledged.json"
        link = self.snapshot / "unsafe"
        link.symlink_to(original)
        self.cli("migration-inventory", expected=2); link.unlink()
        os.link(original, link)
        self.cli("migration-inventory", expected=2); link.unlink()
        # Exercise a real Unix socket inode, without binding a service. Native
        # owner-ingress execution remains mandatory in the existing native lane.
        os.mknod(link, stat.S_IFSOCK | 0o600)
        self.cli("migration-inventory", expected=2)
        link.unlink()
        migration.write(self.snapshot / "unknown/unclassified.bin", b"\x00\xffextra fixture bytes")
        self.seal(); self.imported()
        self.assertEqual((self.volume / "legacy/railway/unknown/unclassified.bin").read_bytes(), b"\x00\xffextra fixture bytes")

    def test_wrong_export_pin_added_or_missing_payload_refuses_import_before_target_write(self):
        self.exported()
        self.cli("migration-import", "--export-sha256", "f" * 64, expected=2)
        added = self.bundle / "payload/unlisted"; added.write_bytes(b"extra"); added.chmod(0o600)
        self.cli("migration-import", expected=2); self.assertFalse(self.volume.exists())
        added.unlink(); (self.bundle / "payload/receipts/acknowledged.json").unlink()
        self.cli("migration-import", expected=2); self.assertFalse(self.volume.exists())

    def test_unsafe_paths_manifest_tampering_duplicate_json_and_wrong_mode_fail_closed(self):
        self.exported()
        path = self.bundle / "EXPORT.json"; original = path.read_bytes()
        value = json.loads(original); value["entries"]["../escaped"] = {"kind": "file", "mode": 0o600, "bytes": 0, "sha256": migration.sha(b"")}
        path.write_bytes(migration.raw(value)); self.export_pin = migration.sha(path.read_bytes())
        self.cli("migration-import", expected=2); self.assertFalse((self.work / "escaped").exists())
        path.write_bytes(original); self.export_pin = migration.sha(original)
        path.write_bytes(b'{"schema":"first","schema":"second"}')
        self.export_pin = migration.sha(path.read_bytes())
        self.assertIn("DUPLICATE_JSON", self.cli("migration-import", expected=2)["cause"])
        path.write_bytes(original); self.export_pin = migration.sha(original)
        payload = self.bundle / "payload/receipts/acknowledged.json"; payload.chmod(0o644)
        self.cli("migration-import", expected=2); self.assertFalse(self.volume.exists())

    def test_unverified_snapshot_declaration_and_export_verifier_drift_are_refused(self):
        self.declaration["consistency"] = "LIVE_COPY"
        self.witness.write_bytes(migration.raw(self.declaration)); self.source_pin = migration.sha(self.witness.read_bytes())
        self.assertIn("UNVERIFIED", self.cli("migration-export", expected=2)["cause"])
        self.assertFalse(self.bundle.exists())
        self.seal(); self.exported()
        path = self.bundle / "EXPORT.json"; value = json.loads(path.read_bytes()); value["verifier_sha256"] = "0" * 64
        path.write_bytes(migration.raw(value)); self.export_pin = migration.sha(path.read_bytes())
        self.assertIn("VERIFIER_MISMATCH", self.cli("migration-import", expected=2)["cause"])

    def test_existing_monitor_binding_and_journal_cannot_be_omitted_from_layout(self):
        for field in ("monitor", "binding", "jsonl"):
            with self.subTest(field=field):
                self.seal(); self.declaration["layout"][field] = [] if field == "jsonl" else None
                self.witness.write_bytes(migration.raw(self.declaration)); self.source_pin = migration.sha(self.witness.read_bytes())
                self.cli("migration-export", expected=2); self.assertFalse(self.bundle.exists())

    def test_dry_run_rejects_overlapping_or_symlinked_target_paths(self):
        self.exported()
        self.cli("migration-import", "--dry-run", "--output", str(self.bundle / "payload"), expected=2)
        self.volume.symlink_to(self.bundle)
        self.cli("migration-import", "--dry-run", expected=2)
        self.assertEqual(migration.inventory(self.snapshot), self.before)

    def test_existing_target_wrong_config_and_node_relabel_are_refused(self):
        self.exported()
        self.config["node_id"] = "fixture:unrelated"; self.save_config()
        self.assertIn("NODE_ID_CHANGE", self.cli("migration-import", expected=2)["cause"])
        self.config["node_id"] = "fixture:railway"; self.save_config()
        self.volume.mkdir(mode=0o700); marker = self.volume / "existing"; marker.write_bytes(b"do not replace")
        self.cli("migration-import", expected=2); self.assertEqual(marker.read_bytes(), b"do not replace")

    def test_failed_post_copy_verification_quarantines_target_and_original_launcher_refuses_it(self):
        self.exported()
        args = argparse.Namespace(operation="migration-import", root=self.export, manifest_sha256=self.pin,
            bundle=self.bundle, export_sha256=self.export_pin, output=self.volume, config=self.config_path,
            dry_run=False, snapshot=None, source_declaration=None, source_declaration_sha256=None, import_sha256=None)
        original = migration.independent
        def damaged(actual_args, operation, output=None):
            if operation == "migration-verify-import":
                (self.volume / "legacy/railway/receipts/acknowledged.json").write_bytes(b"corrupted after copy")
            return original(actual_args, operation, output)
        with mock.patch.object(migration, "independent", side_effect=damaged):
            with self.assertRaisesRegex(ValueError, "INDEPENDENT_MIGRATION_VERIFICATION"):
                migration.execute(args, host.verify, host.load_source, host.private_path)
        self.assertTrue((self.volume / migration.HOLD).is_file())
        self.assertIn("MIGRATION_TARGET_QUARANTINED", self.denied())
        self.assertEqual(migration.inventory(self.snapshot), self.before)
        (self.volume / migration.HOLD).unlink()
        self.assertIn("MIGRATION_VERIFIED_IMPORT_REQUIRED", self.denied())

    def test_missing_completion_receipt_cannot_initialize_fresh_migrated_state(self):
        self.exported(); self.volume.mkdir(mode=0o700)
        self.assertIn("MIGRATION_VERIFIED_IMPORT_REQUIRED", self.denied())
        self.assertFalse((self.volume / "binding.json").exists())
        self.assertFalse((self.volume / "temdd/events.sqlite3").exists())

    def test_completion_record_corruption_refuses_original_launcher(self):
        self.imported()
        (self.volume / migration.VERIFIED).write_bytes(b"{}\n")
        self.assertIn("MIGRATION_VERIFIED_IMPORT_REQUIRED", self.denied())

    def test_rollback_quarantines_without_data_deletion_or_route_or_source_restart(self):
        self.imported(); before = migration.target_inventory(self.volume)
        result = self.cli("migration-rollback")
        self.assertEqual(result["state"], "CANDIDATE_QUARANTINED_SOURCE_UNTOUCHED")
        self.assertFalse(result["target_deleted"]); self.assertFalse(result["routing_changed"])
        self.assertFalse(result["source_restart_authorized"])
        self.assertEqual(migration.target_inventory(self.volume), before)
        self.assertIn("MIGRATION_TARGET_QUARANTINED", self.denied())

    def test_rollback_with_post_import_write_never_silently_restores_stale_source(self):
        self.imported()
        migration.write(self.volume / "receipts/after-import.json", b'{"fixture":"new-write"}\n')
        result = self.cli("migration-rollback")
        self.assertEqual(result["state"], "HOLD_TARGET_DRIFT_RECONCILIATION_REQUIRED")
        self.assertEqual((self.volume / "receipts/after-import.json").read_bytes(), b'{"fixture":"new-write"}\n')
        self.assertEqual(migration.inventory(self.snapshot), self.before)

    def test_rollback_cannot_quarantine_a_live_locked_target(self):
        self.imported()
        with (self.volume / "node.lock").open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.cli("migration-rollback", expected=2)
        self.assertFalse((self.volume / migration.HOLD).exists())


if __name__ == "__main__": unittest.main()
