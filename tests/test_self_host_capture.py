# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Private synthetic storage controls; no Railway access or live capture claim."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from tests import test_self_host_migration as fixtures
from tools import qikvrt_self_host_migration as migration


class CaptureControls(unittest.TestCase):
    setUpClass = classmethod(fixtures.MigrationTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.MigrationTests.tearDownClass.__func__)
    save_config = fixtures.MigrationTests.save_config
    stop = fixtures.MigrationTests.stop
    native_event = fixtures.MigrationTests.native_event
    seal = fixtures.MigrationTests.seal

    def setUp(self):
        if os.geteuid() != 0:
            self.fail('Privileged capture controls require the existing root Docker test carrier')
        fixtures.MigrationTests.setUp(self)
        # Actual Git source identity, historical ledger rows left untouched.
        binding = json.loads((self.snapshot / 'binding.json').read_bytes())
        binding.update(source_head=self.head, source_tree=self.tree)
        (self.snapshot / 'binding.json').write_bytes(migration.raw(binding))
        self.capture_root = self.work / 'captured'
        self.request_file = self.work / 'REQUEST.json'
        self.carrier = dict(migration.SOURCE_CARRIER, mount_path=str(self.snapshot))
        cut = migration.inspect_sqlite(self.snapshot, self.declaration['layout']['ledger'], self.native)
        self.request = {'schema': 'qikvrt-railway-capture-request/v1', 'carrier': self.carrier,
                        'deployment_id': 'SYNTHETIC_FIXTURE_NOT_RAILWAY', 'source_repository': 'Goldkelch/qik-vrt',
                        'source_head': self.head, 'source_tree': self.tree, 'snapshot_id': 'SYNTHETIC_CAPTURE_ONLY',
                        'expires_at': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)).isoformat(),
                        'layout': self.declaration['layout'],
                        'acknowledgements': {k: cut[k] for k in ('epoch', 'events', 'logical_sha256')},
                        'restart_fence_receipt_sha256': 'd' * 64}
        self.args = argparse.Namespace(operation='migration-capture-arm', root=self.export,
            source_root=self.source, live_volume=self.snapshot, capture_request=self.request_file,
            output=self.capture_root, manifest_sha256=self.pin, dry_run=False, bundle=None)
        self.save_request()
        for patcher in [mock.patch.object(migration, 'SOURCE_CARRIER', self.carrier),
                        mock.patch.object(migration.os.path, 'ismount', return_value=True),
                        # Explicit storage fixture boundary; this does not prove
                        # an actual provider namespace or stopped production PIDs.
                        mock.patch.object(migration, 'capture_processes', return_value=[{'synthetic': True}]),
                        mock.patch.dict(os.environ, {
                          'RAILWAY_PROJECT_ID': self.carrier['project_id'],
                          'RAILWAY_ENVIRONMENT_ID': self.carrier['environment_id'],
                          'RAILWAY_SERVICE_ID': self.carrier['service_id'],
                          'RAILWAY_VOLUME_ID': self.carrier['volume_id'],
                          'RAILWAY_DEPLOYMENT_ID': self.request['deployment_id']})]:
            patcher.start(); self.addCleanup(patcher.stop)

    def save_request(self):
        self.request_file.write_bytes(migration.raw(self.request)); self.request_file.chmod(0o600)
        self.args.capture_request_sha256 = migration.sha(self.request_file.read_bytes())

    def execute(self, operation):
        self.args.operation = operation
        return migration.execute(self.args, fixtures.host.verify, fixtures.host.load_source, fixtures.host.private_path)

    def arm(self):
        result = self.execute('migration-capture-arm')
        self.assertFalse(result['snapshot_created']); self.assertFalse(self.capture_root.exists())
        return result

    def test_complete_private_capture_then_original_source_export_verifiers(self):
        self.arm()
        before = migration.inventory(self.snapshot, privileged_capture=True)
        result = self.execute('migration-capture')
        self.assertEqual(result['state'], 'OFFLINE_CAPTURE_SEALED_PENDING_INDEPENDENT_VALIDATION')
        self.assertFalse(result['capture_consistency_independently_validated'])
        self.assertFalse(result['source_restart_permitted'])
        self.assertEqual(before, migration.inventory(self.snapshot, privileged_capture=True))
        source = self.capture_root / 'SOURCE.json'
        command = [sys.executable, '-B', str(self.export / 'tools/qikvrt_self_host.py'),
                   'migration-verify-source', '--root', str(self.export), '--manifest-sha256', self.pin,
                   '--snapshot', str(self.capture_root / 'snapshot'), '--source-declaration', str(source),
                   '--source-declaration-sha256', result['source_declaration_sha256']]
        # Source locator is synthetic only in this test; use the real carrier
        # shape in the declaration for the independent packaged CLI checks.
        declaration = json.loads(source.read_bytes())
        declaration['carrier'] = dict(self.carrier, mount_path='/var/lib/qikvrt')
        source.write_bytes(migration.raw(declaration)); command[-1] = migration.sha(source.read_bytes())
        for operation, extra in [('migration-verify-source', []), ('migration-export', ['--output', str(self.bundle)])]:
            command[3] = operation
            run = subprocess.run(command + extra, capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        pin = migration.sha((self.bundle / 'EXPORT.json').read_bytes())
        verify = command[:3] + ['migration-verify-export', '--root', str(self.export), '--manifest-sha256', self.pin,
                               '--bundle', str(self.bundle), '--export-sha256', pin]
        run = subprocess.run(verify, capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        for path in self.capture_root.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)
        self.assertEqual((self.capture_root / 'snapshot/receipts/acknowledged.json').read_bytes(),
                         (self.snapshot / 'receipts/acknowledged.json').read_bytes())

    def test_repeat_arm_cannot_be_second_dispatch(self):
        self.arm()
        with self.assertRaises(FileExistsError): self.arm()

    def test_composition_keeps_original_source_and_does_not_start_supervisor(self):
        original = (self.source / 'deploy/universal-terminal/cloud-entrypoint.sh').read_bytes()
        self.args.capture_output = self.capture_root
        self.args.output = self.work / 'supervisor.sh'
        result = self.execute('migration-capture-supervisor')
        self.assertEqual(result['state'], 'CAPTURE_SUPERVISOR_MATERIALIZED_NOT_STARTED')
        self.assertEqual(result['original_supervisor_sha256'], migration.sha(original))
        self.assertEqual((self.source / 'deploy/universal-terminal/cloud-entrypoint.sh').read_bytes(), original)
        self.assertFalse((self.snapshot / migration.CAPTURE_HOLD).exists())
        self.assertFalse(self.capture_root.exists())
        self.assertEqual(subprocess.run(['sh', '-n', str(self.args.output)]).returncode, 0)

    def test_mixed_original_owners_and_permissions_are_preserved_only_in_private_evidence(self):
        profile = self.snapshot / 'profile/storage.sqlite'
        os.chown(profile, 12345, 12346); profile.chmod(0o666)
        # Required in the existing isolated root Docker lane: positive real
        # namespace census, without the synthetic carrier/storage mocks.
        census = subprocess.run([sys.executable, '-B', '-c',
            'from tools.qikvrt_self_host_migration import capture_processes; capture_processes()'],
            cwd=fixtures.ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(census.returncode, 0, census.stderr)
        original = profile.read_bytes()
        self.arm(); self.execute('migration-capture')
        entry = json.loads((self.capture_root / 'CAPTURE.json').read_bytes())['source_inventory']['profile/storage.sqlite']
        self.assertEqual((entry['uid'], entry['gid'], entry['mode']), (12345, 12346, 0o666))
        copy = self.capture_root / 'snapshot/profile/storage.sqlite'
        self.assertEqual(copy.read_bytes(), original); self.assertEqual(copy.stat().st_mode & 0o777, 0o600)
        self.assertEqual(profile.stat().st_uid, 12345)

    def test_extended_metadata_requires_review_instead_of_being_lost(self):
        self.arm(); os.setxattr(self.snapshot / 'profile/storage.sqlite', 'user.qikvrt.synthetic', b'fixture')
        with self.assertRaisesRegex(ValueError, 'EXTENDED_METADATA_REQUIRES_REVIEW'): self.execute('migration-capture')
        self.assertFalse(self.capture_root.exists())

    def test_real_process_census_refuses_live_sibling_or_unobservable_namespace(self):
        writer = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            script = 'from tools.qikvrt_self_host_migration import capture_processes; capture_processes()'
            run = subprocess.run([sys.executable, '-B', '-c', script], cwd=fixtures.ROOT, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(run.returncode, 0)
            self.assertTrue(any(reason in run.stderr for reason in (
                'CAPTURE_UNKNOWN_OR_LIVE_PROCESS', 'CAPTURE_CONTAINER_PID_NAMESPACE_REQUIRED')), run.stderr)
        finally: writer.terminate(); writer.wait(timeout=5)

    def test_bad_pin_or_wrong_source_cannot_fence_or_stop_source(self):
        for change in ('pin', 'head', 'dry-run', 'untracked-source'):
            with self.subTest(change=change):
                self.request['source_head'] = self.head; self.args.dry_run = False
                self.save_request()
                if change == 'pin': self.args.capture_request_sha256 = '0' * 64
                elif change == 'head': self.request['source_head'] = '0' * 40; self.save_request()
                elif change == 'dry-run': self.args.dry_run = True
                else: (self.source / 'unknown.py').write_bytes(b'# synthetic unknown source\n')
                try:
                    with self.assertRaises(ValueError): self.execute('migration-capture-arm')
                finally:
                    if change == 'untracked-source': (self.source / 'unknown.py').unlink()
                self.assertFalse((self.snapshot / migration.CAPTURE_HOLD).exists())

    def test_stale_request_cannot_arm(self):
        self.request['expires_at'] = '2020-01-01T00:00:00Z'; self.save_request()
        with self.assertRaises(ValueError): self.arm()

    def test_missing_provider_identity_cannot_arm(self):
        with mock.patch.dict(os.environ, {'RAILWAY_VOLUME_ID': ''}):
            with self.assertRaises(ValueError): self.arm()

    def test_held_native_writer_cannot_create_snapshot(self):
        self.arm()
        with (self.snapshot / 'state/temdd/owner.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.execute('migration-capture')
        self.assertFalse(self.capture_root.exists())

    def test_unknown_live_process_cannot_create_snapshot(self):
        self.arm()
        with mock.patch.object(migration, 'capture_processes', side_effect=ValueError('CAPTURE_UNKNOWN_OR_LIVE_PROCESS')):
            with self.assertRaises(ValueError): self.execute('migration-capture')
        self.assertFalse(self.capture_root.exists())

    def test_acknowledged_history_mismatch_quarantines_copy_without_resuming(self):
        self.request['acknowledgements']['events'] += 1; self.save_request(); self.arm()
        with self.assertRaisesRegex(ValueError, 'ACKNOWLEDGEMENT_CUT_MISMATCH'): self.execute('migration-capture')
        self.assertTrue((self.capture_root / migration.HOLD).exists())
        self.assertTrue((self.snapshot / migration.CAPTURE_HOLD).exists())

    def test_private_profile_symlink_is_never_silently_omitted(self):
        self.arm(); (self.snapshot / 'profile/link').symlink_to('storage.sqlite')
        with self.assertRaises(ValueError): self.execute('migration-capture')
        self.assertFalse(self.capture_root.exists())

    def test_source_drift_during_copy_cannot_seal_source_declaration(self):
        self.arm(); original_copy = migration.copy_tree
        def drift(*args, **kwargs):
            original_copy(*args, **kwargs)
            (self.snapshot / 'receipts/acknowledged.json').write_bytes(b'changed synthetic data')
        with mock.patch.object(migration, 'copy_tree', side_effect=drift):
            with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED_AFTER_COPY'): self.execute('migration-capture')
        self.assertFalse((self.capture_root / 'SOURCE.json').exists())
        self.assertTrue((self.capture_root / migration.HOLD).exists())


if __name__ == '__main__': unittest.main()
