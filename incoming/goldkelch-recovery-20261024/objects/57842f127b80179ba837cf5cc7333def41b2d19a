#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Real persistent sink effects and destructive-source fenced takeover tests."""
import copy
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest import mock

from tests import test_qikvrt_mesh_recovery as recovery_fixtures
from tools import qikvrt_authority_transition as transition
from tools import qikvrt_mesh_recovery as recovery
from tools.qikvrt_seed_common import canonical_json_bytes

ADMIN = '1' * 64
OLD_TOKEN = '2' * 64
NEW_TOKEN = '3' * 64
COMPETITOR_TOKEN = '4' * 64


class AuthorityTransitionTests(unittest.TestCase):
    def setUp(self):
        fixture = recovery_fixtures.MeshRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        self.manifest = fixture.create()
        self.node = self.root / 'mirror-restored'
        recovery.restore_checkpoint(fixture.package, self.node, self.manifest)
        self.competitor = self.root / 'competitor'
        recovery.restore_checkpoint(fixture.package, self.competitor, self.manifest, clone=True)
        # Previous active Authority has the same accepted Git/scheduler watermark,
        # but a different node identity and repository at the permanent root.
        fixture.plan['node_id'] = 'b' * 64
        fixture.plan['repository'] = recovery.ROOT_REPOSITORY
        fixture.plan['lineage'] = [recovery.ROOT_REPOSITORY]
        fixture.plan['role'] = 'AUTHORITY'
        fixture.scheduler['schedules'][0]['owner_node_id'] = fixture.plan['node_id']
        scheduler_bytes = canonical_json_bytes(fixture.scheduler)
        (fixture.payload / 'scheduler.bin').write_bytes(scheduler_bytes)
        for asset in fixture.plan['assets']:
            if asset['category'] == 'scheduler':
                asset.update(bytes=len(scheduler_bytes), sha256=recovery.digest(scheduler_bytes))
        fixture.package = self.root / 'old-checkpoint'
        old_manifest = fixture.create()
        self.old_node = self.root / 'old-authority'
        recovery.restore_checkpoint(fixture.package, self.old_node, old_manifest)
        private = self.root / 'control-plane'
        private.mkdir(mode=0o700)
        self.cp = transition.AuthorityControlPlane(private / 'authority.sqlite')
        initial = self.cp.initialize(self.old_node, old_manifest, 7, ADMIN, OLD_TOKEN)
        self.old_permit = self.cp.permit(initial['state'])
        self.cp.authorize_recovery(self.node, self.manifest, ADMIN, NEW_TOKEN)
        self.cp.authorize_recovery(self.competitor, self.manifest, ADMIN, COMPETITOR_TOKEN)
        self.fixture = fixture

    def take(self, node=None, token=NEW_TOKEN):
        node = node or self.node
        observation = self.cp.observe(node, self.manifest, token)
        return self.cp.takeover(node, self.manifest, token, observation)['permit']

    def activate(self):
        permit = self.take()
        result = self.cp.activate(self.node, self.manifest, NEW_TOKEN, permit)
        self.assertTrue(result['writer_enabled'])
        self.assertFalse(result['effect_ack_done'])
        return permit

    def assert_old_rejected(self):
        with self.assertRaisesRegex(transition.TransitionError, 'old writer rejected'):
            self.cp.commit_write(OLD_TOKEN, self.old_permit, 'forbidden', b'old')
        with self.cp.transaction() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM effects WHERE id='forbidden'").fetchone())

    def test_complete_authority_loss_takeover_and_actual_sink_effect(self):
        shutil.rmtree(self.old_node)
        shutil.rmtree(self.fixture.source)
        shutil.rmtree(self.fixture.payload)
        # No former Authority, remote, source or package is required by takeover.
        for path in (self.root / 'checkpoint', self.root / 'old-checkpoint'):
            shutil.rmtree(path)
        permit = self.activate()
        result = self.cp.commit_write(NEW_TOKEN, permit, 'effect:43', b'actual bytes')
        self.assertTrue(result['fresh_sink_readback'])
        state = self.cp.readback(NEW_TOKEN)['state']
        self.assertEqual(state['authority_epoch'], 8)
        self.assertEqual(state['binding']['repository'], 'ingolf-lohmann/qik-vrt')
        self.assertEqual(state['root_repository'], 'Goldkelch/qik-vrt')
        self.assert_old_rejected()

    def test_pending_cas_fences_both_writers_until_separate_fresh_readback(self):
        permit = self.take()
        self.assert_old_rejected()
        with self.assertRaisesRegex(transition.TransitionError, 'fresh activation'):
            self.cp.commit_write(NEW_TOKEN, permit, 'pending', b'x')
        restarted = transition.AuthorityControlPlane(self.cp.path)
        result = restarted.activate(self.node, self.manifest, NEW_TOKEN, permit)
        self.assertTrue(result['writer_enabled'])
        self.assertEqual(result['state']['phase'], 'ACTIVE')

    def test_concurrent_takeover_only_one_cas_wins(self):
        observations = [self.cp.observe(n, self.manifest, t) for n, t in
                        [(self.node, NEW_TOKEN), (self.competitor, COMPETITOR_TOKEN)]]
        barrier = threading.Barrier(2)
        def race(node, token, observation):
            barrier.wait(timeout=10)
            try:
                return self.cp.takeover(node, self.manifest, token, observation)
            except transition.TransitionError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(race, n, t, o) for n, t, o in zip(
                (self.node, self.competitor), (NEW_TOKEN, COMPETITOR_TOKEN), observations)]
            results = [f.result(timeout=15) for f in futures]
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(self.cp.readback(NEW_TOKEN)['state']['authority_epoch'], 8)
        self.assert_old_rejected()

    def test_stale_epoch_cannot_overwrite_competing_successor(self):
        stale = self.cp.observe(self.competitor, self.manifest, COMPETITOR_TOKEN)
        self.activate()
        before = self.cp.readback(NEW_TOKEN)['state']
        with self.assertRaisesRegex(transition.TransitionError, 'stale epoch'):
            self.cp.takeover(self.competitor, self.manifest, COMPETITOR_TOKEN, stale)
        self.assertEqual(self.cp.readback(NEW_TOKEN)['state'], before)

    def test_losing_recovery_grant_cannot_take_a_later_epoch_without_owner_renewal(self):
        self.activate()
        observation = self.cp.observe(self.competitor, self.manifest, COMPETITOR_TOKEN)
        with self.assertRaisesRegex(transition.TransitionError, 'grant requires renewal'):
            self.cp.takeover(self.competitor, self.manifest, COMPETITOR_TOKEN, observation)
        self.cp.authorize_recovery(self.competitor, self.manifest, ADMIN, '5' * 64)
        permit = self.take(self.competitor, '5' * 64)
        self.assertEqual(permit['authority_epoch'], 9)

    def test_old_authority_rejoins_as_fenced_mirror_without_admission_inflation(self):
        self.activate()
        result = self.cp.rejoin(OLD_TOKEN, self.old_permit)
        self.assertEqual(result['role'], 'MIRROR')
        self.assertFalse(result['writer_enabled'])
        self.assertFalse(result['full_node_admitted'])
        self.assertTrue(result['catch_up_required'])
        self.assert_old_rejected()

    def test_old_writer_cannot_borrow_new_public_fence_or_replay_completed_effect(self):
        permit = self.activate()
        with self.assertRaises(transition.TransitionError):
            self.cp.commit_write(OLD_TOKEN, permit, 'effect:43', b'x')
        self.assert_old_rejected()

    def test_sink_write_race_and_takeover_have_one_transaction_order(self):
        observation = self.cp.observe(self.node, self.manifest, NEW_TOKEN)
        barrier = threading.Barrier(2)
        def write():
            barrier.wait(timeout=10)
            try:
                return self.cp.commit_write(OLD_TOKEN, self.old_permit, 'racing', b'bytes')
            except transition.TransitionError:
                return None
        def take():
            barrier.wait(timeout=10)
            try:
                return self.cp.takeover(self.node, self.manifest, NEW_TOKEN, observation)
            except transition.TransitionError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(write), pool.submit(take)
            write_result, take_result = a.result(timeout=15), b.result(timeout=15)
        with self.cp.transaction() as db:
            committed = db.execute("SELECT 1 FROM effects WHERE id='racing'").fetchone() is not None
        # If write commits first, revision CAS rejects takeover; if takeover
        # commits first the old writer cannot commit. Readback may be superseded.
        self.assertNotEqual(committed, take_result is not None)
        if committed:
            self.assertIsNotNone(write_result)
        else:
            self.assertIsNone(write_result)

    def test_expired_altered_foreign_and_consumed_observations_fail_closed(self):
        observation = self.cp.observe(self.node, self.manifest, NEW_TOKEN)
        for delta in (-1, transition.OBSERVATION_TTL_NS + 1):
            with mock.patch.object(transition.time, 'time_ns', return_value=observation['issued_ns'] + delta):
                with self.assertRaisesRegex(transition.TransitionError, 'stale observation'):
                    self.cp.takeover(self.node, self.manifest, NEW_TOKEN, observation)
        altered = {**observation, 'authority_epoch': 999}
        with self.assertRaisesRegex(transition.TransitionError, 'altered'):
            self.cp.takeover(self.node, self.manifest, NEW_TOKEN, altered)
        with self.assertRaisesRegex(transition.TransitionError, 'unknown'):
            self.cp.takeover(self.competitor, self.manifest, COMPETITOR_TOKEN, observation)
        self.cp.takeover(self.node, self.manifest, NEW_TOKEN, observation)
        with self.assertRaisesRegex(transition.TransitionError, 'unknown'):
            self.cp.takeover(self.node, self.manifest, NEW_TOKEN, observation)

    def test_checkpoint_epoch_is_not_current_observation_and_bad_capability_is_rejected(self):
        with self.cp.transaction() as db:
            state = self.cp.state(db)
            state['authority_epoch'] = 41
            state['revision'] += 1
            self.cp.store(db, state)
        self.cp.authorize_recovery(self.node, self.manifest, ADMIN, '5' * 64)
        observation = self.cp.observe(self.node, self.manifest, '5' * 64)
        self.assertEqual(observation['authority_epoch'], 41)
        result = self.cp.takeover(self.node, self.manifest, '5' * 64, observation)
        self.assertEqual(result['permit']['authority_epoch'], 42)
        with self.assertRaisesRegex(transition.TransitionError, 'not authorized'):
            self.cp.observe(self.node, self.manifest, 'f' * 64)
        with self.assertRaisesRegex(transition.TransitionError, 'admin capability'):
            self.cp.authorize_recovery(self.node, self.manifest, 'f' * 64, '5' * 64)

    def test_post_cas_target_and_scheduler_tampering_never_enables_writer(self):
        permit = self.take()
        payload = self.node / 'payload/scheduler.bin'
        original = payload.read_bytes()
        payload.write_bytes(original.replace(b'done:42', b'done:41'))
        with self.assertRaises(transition.TransitionError):
            self.cp.activate(self.node, self.manifest, NEW_TOKEN, permit)
        self.assertEqual(self.cp.readback(NEW_TOKEN)['state']['phase'], 'PENDING_READBACK')
        payload.write_bytes(original)
        recovery.git_command(self.node / 'repository.git', 'branch', 'unaccepted')
        with self.assertRaisesRegex(transition.TransitionError, 'HEAD/TREE/ref drift'):
            self.cp.activate(self.node, self.manifest, NEW_TOKEN, permit)
        self.assert_old_rejected()

    def test_readback_mismatch_and_superseded_activation_fail_closed(self):
        permit = self.take()
        with self.cp.transaction() as db:
            state = self.cp.state(db)
            state['scheduler']['schedules'][0]['last_completed_cursor'] = 'foreign'
            self.cp.store(db, state)
        with self.assertRaisesRegex(transition.TransitionError, 'readback mismatch'):
            self.cp.activate(self.node, self.manifest, NEW_TOKEN, permit)
        self.assert_old_rejected()

    def test_activation_superseded_before_final_readback_cannot_return_enabled(self):
        permit = self.take()
        readback = self.cp.readback
        def supersede(token):
            self.cp.authorize_recovery(self.competitor, self.manifest, ADMIN, '5' * 64)
            self.take(self.competitor, '5' * 64)
            return readback(token)
        with mock.patch.object(self.cp, 'readback', side_effect=supersede):
            with self.assertRaisesRegex(transition.TransitionError, 'old writer rejected'):
                self.cp.activate(self.node, self.manifest, NEW_TOKEN, permit)
        with self.assertRaises(transition.TransitionError):
            self.cp.commit_write(NEW_TOKEN, permit, 'superseded', b'x')

    def test_accepted_head_and_scheduler_cannot_regress_at_takeover(self):
        with self.cp.transaction() as db:
            state = self.cp.state(db)
            state['binding']['head'] = 'c' * 40
            self.cp.store(db, state)
        observation = self.cp.observe(self.node, self.manifest, NEW_TOKEN)
        with self.assertRaisesRegex(transition.TransitionError, 'behind or diverges'):
            self.cp.takeover(self.node, self.manifest, NEW_TOKEN, observation)
        with self.cp.transaction() as db:
            state = self.cp.state(db)
            state['binding']['head'] = recovery.git_command(self.node / 'repository.git', 'rev-parse', 'HEAD')
            state['scheduler']['schedules'][0]['last_completed_cursor'] = 'done:99'
            self.cp.store(db, state)
        observation = self.cp.observe(self.node, self.manifest, NEW_TOKEN)
        with self.assertRaisesRegex(transition.TransitionError, 'checkpoint drift'):
            self.cp.takeover(self.node, self.manifest, NEW_TOKEN, observation)

    def test_scheduler_rebinding_and_exact_once_sink_replay_survive_takeover(self):
        self.cp.commit_write(OLD_TOKEN, self.old_permit, 'effect:43', b'completed')
        permit = self.activate()
        state = self.cp.readback(NEW_TOKEN)['state']
        schedule = state['scheduler']['schedules'][0]
        self.assertEqual(schedule['owner_node_id'], state['binding']['node_id'])
        self.assertEqual(schedule['last_completed_cursor'], 'done:42')
        self.assertEqual(schedule['pending_work'][0]['idempotency_key'], 'effect:43')
        self.assertTrue(self.cp.commit_write(NEW_TOKEN, permit, 'effect:43', b'completed')['replayed'])
        with self.assertRaisesRegex(transition.TransitionError, 'payload conflict'):
            self.cp.commit_write(NEW_TOKEN, permit, 'effect:43', b'different')
        with self.cp.transaction() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM effects').fetchone()[0], 1)

    def test_missing_recreated_symlink_or_public_control_plane_is_not_auto_recovered(self):
        missing = transition.AuthorityControlPlane(self.cp.path.parent / 'missing.sqlite')
        with self.assertRaises(transition.TransitionError):
            missing.readback(NEW_TOKEN)
        self.assertFalse(missing.path.exists())
        linked = self.cp.path.parent / 'linked.sqlite'
        linked.symlink_to(self.cp.path)
        with self.assertRaises(transition.TransitionError):
            transition.AuthorityControlPlane(linked).readback(NEW_TOKEN)
        os.chmod(self.cp.path, 0o644)
        with self.assertRaisesRegex(transition.TransitionError, '0600'):
            self.cp.readback(NEW_TOKEN)
        os.chmod(self.cp.path, 0o600)
        other = transition.AuthorityControlPlane(self.cp.path.parent / 'different.sqlite')
        other.initialize(self.node, self.manifest, 7, ADMIN, NEW_TOKEN)
        with self.assertRaisesRegex(transition.TransitionError, 'old writer rejected'):
            other.commit_write(NEW_TOKEN, self.old_permit, 'foreign', b'x')

    def test_epoch_capacity_exhaustion_does_not_materialize_an_unreadable_successor(self):
        with self.cp.transaction() as db:
            state = self.cp.state(db)
            state['authority_epoch'] = 2**63 - 2
            self.cp.store(db, state)
        self.cp.authorize_recovery(self.node, self.manifest, ADMIN, '5' * 64)
        observation = self.cp.observe(self.node, self.manifest, '5' * 64)
        with self.assertRaisesRegex(transition.TransitionError, 'epoch exhausted'):
            self.cp.takeover(self.node, self.manifest, '5' * 64, observation)
        self.assertEqual(self.cp.readback(NEW_TOKEN)['state']['phase'], 'ACTIVE')

    def test_busy_control_plane_blocks_without_unfencing_or_hidden_retry(self):
        db = sqlite3.connect(self.cp.path)
        db.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaisesRegex(transition.TransitionError, 'transaction failed or unavailable'):
                self.cp.readback(NEW_TOKEN)
        finally:
            db.rollback()
            db.close()
        self.assertEqual(self.cp.readback(NEW_TOKEN)['state']['authority_epoch'], 7)

    def test_executable_cli_observe_takeover_activate_write_readback(self):
        token_file = self.root / 'token'
        token_file.write_text(NEW_TOKEN)
        token_file.chmod(0o600)
        base = [sys.executable, '-B', str(transition.ROOT / 'tools/qikvrt_authority_transition.py')]
        common = ['--control-plane', str(self.cp.path), '--token-file', str(token_file)]
        target = ['--node', str(self.node), '--expect-manifest-sha256', self.manifest]
        def command(operation, extra):
            result = subprocess.run(base + [operation] + common + extra, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout)
            return transition.decode(result.stdout)
        observation = command('observe', target)
        observation_file = self.root / 'observation.json'
        observation_file.write_bytes(canonical_json_bytes(observation))
        takeover = command('takeover', target + ['--observation', str(observation_file)])
        permit_file = self.root / 'permit.json'
        permit_file.write_bytes(canonical_json_bytes(takeover['permit']))
        command('activate', target + ['--permit', str(permit_file)])
        payload = self.root / 'effect.bin'
        payload.write_bytes(b'cli actual effect')
        result = command('write', ['--permit', str(permit_file), '--effect-id', 'cli', '--payload', str(payload)])
        self.assertTrue(result['fresh_sink_readback'])
        self.assertEqual(command('readback', [])['node_role'], 'AUTHORITY')


if __name__ == '__main__':
    unittest.main()
