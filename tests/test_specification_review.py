#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Failure injection for the live specification preflight; isolated evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import ai_handoff as gate


class SpecificationReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'source.txt').write_bytes(b'isolated source fixture')
        self.subject = dict(repository='ingolf-lohmann/qik-vrt', ref='refs/heads/main',
                            head='1' * 40, tree='2' * 40)
        item = dict(id='effect-ack', family='effect-ack', selected_revision='03',
                    latest_revision='03', disposition='APPLY', reason='core specification',
                    source_path='source.txt', sha256=hashlib.sha256(b'isolated source fixture').hexdigest())
        channels = [dict(name=name, locator='fixture:' + name, author_id='fixture:author',
                         from_cache=False, truncated=False, next=None, total=1,
                         verification='DIRECT_PRIMARY_READBACK', observed_utc=1000,
                         items=[copy.deepcopy(item)]) for name in ('ietf', 'zenodo', 'authority')]
        self.action = dict(method='POST', specification_use='CURRENT',
                           specification_claims=['effect-ack'], specification_review=dict(
                               schema='qikvrt-specification-review/v1', subject=self.subject,
                               claims=['effect-ack'], observed_utc=1000, valid_until_utc=1100,
                               channels=channels))
        self.patcher = patch.object(gate, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def check(self, action=None, now=1001):
        gate.validate_specification_use(self.action if action is None else action,
                                        self.subject, now=now)

    def test_complete_bound_review_and_current_revision(self):
        self.check()

    def test_missing_live_mutation_classification_blocks(self):
        with self.assertRaises(SystemExit):
            self.check(dict(method='POST'))

    def test_read_only_discovery_can_recover_missing_review(self):
        self.check(dict(method='GET'))
        with self.assertRaises(SystemExit):
            self.check(dict(method='POST', specification_use='DISCOVERY_ONLY'))

    def test_current_claim_cannot_hide_as_discovery_or_history(self):
        for use in ('DISCOVERY_ONLY', 'HISTORICAL_EXACT', None):
            action = copy.deepcopy(self.action)
            action['specification_use'] = use
            action['specification_basis'] = dict(subject=self.subject, reason='repair')
            with self.subTest(use=use), self.assertRaises(SystemExit):
                self.check(action)

    def test_exact_historical_repair_is_not_a_currentness_claim(self):
        self.check(dict(method='POST', specification_use='HISTORICAL_EXACT',
                        specification_claims=[], specification_basis=dict(
                            subject=self.subject, reason='repair frozen source only')))

    def test_review_missing_wrong_subject_or_claim_blocks(self):
        for key, value in [('subject', {}), ('claims', ['other']), ('schema', 'unknown')]:
            a = copy.deepcopy(self.action)
            a['specification_review'][key] = value
            with self.subTest(key=key), self.assertRaises(SystemExit):
                self.check(a)

    def test_expired_future_and_unbounded_review_blocks(self):
        for stamp, expiry in [(1002, 1100), (1000, 1001), (1000, 4601), (True, 1100)]:
            a = copy.deepcopy(self.action)
            a['specification_review'].update(observed_utc=stamp, valid_until_utc=expiry)
            with self.subTest(stamp=stamp, expiry=expiry), self.assertRaises(SystemExit):
                self.check(a)

    def test_missing_or_duplicate_channel_blocks(self):
        for names in [('ietf', 'zenodo'), ('ietf', 'ietf', 'authority')]:
            a = copy.deepcopy(self.action)
            a['specification_review']['channels'] = [
                dict(a['specification_review']['channels'][0], name=n) for n in names]
            with self.subTest(names=names), self.assertRaises(SystemExit):
                self.check(a)

    def test_incomplete_cached_or_failed_inventory_blocks(self):
        mutations = [('total', 42), ('next', 'page2'), ('truncated', True),
                     ('from_cache', True), ('verification', 'UNVERIFIED'),
                     ('observed_utc', 999), ('items', []), ('author_id', '')]
        for key, value in mutations:
            a = copy.deepcopy(self.action)
            a['specification_review']['channels'][0][key] = value
            with self.subTest(key=key), self.assertRaises(SystemExit):
                self.check(a)

    def test_newer_revision_and_unresolved_companion_block(self):
        for key, value in [('latest_revision', '04'), ('disposition', 'OPEN')]:
            a = copy.deepcopy(self.action)
            a['specification_review']['channels'][0]['items'][0][key] = value
            with self.subTest(key=key), self.assertRaises(SystemExit):
                self.check(a)

    def test_companion_is_separate_family(self):
        a = copy.deepcopy(self.action)
        companion = copy.deepcopy(a['specification_review']['channels'][0]['items'][0])
        companion.update(id='epistemic-status', family='epistemic-status',
                         selected_revision='00', latest_revision='00', reason='companion')
        a['specification_review']['channels'][0]['items'].append(companion)
        a['specification_review']['channels'][0]['total'] = 2
        self.check(a)

    def test_source_substitution_missing_source_and_path_escape_block(self):
        for key, value in [('sha256', '0' * 64), ('source_path', 'missing'),
                           ('source_path', '../source.txt'), ('source_path', '/tmp/source')]:
            a = copy.deepcopy(self.action)
            a['specification_review']['channels'][0]['items'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(SystemExit):
                self.check(a)

    def test_live_cli_blocks_before_any_mutation(self):
        p = self.root / 'action.json'
        p.write_text(json.dumps(dict(subject=self.subject, method='POST')))
        result = subprocess.run([sys.executable, '-B', str(Path(gate.__file__)),
                                 '--client-action', str(p)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('SPECIFICATION_USE_REQUIRED', result.stderr)
        self.assertNotIn('READY', result.stdout)

    def test_unavailable_checker_read_does_not_become_success(self):
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('fixture')):
            with self.assertRaises(SystemExit):
                self.check()

    def test_missing_review_and_uncovered_claim_block(self):
        for mutation in ('missing', 'uncovered'):
            a = copy.deepcopy(self.action)
            if mutation == 'missing':
                del a['specification_review']
            else:
                a['specification_claims'] = ['unseen']
                a['specification_review']['claims'] = ['unseen']
            with self.subTest(mutation=mutation), self.assertRaises(SystemExit):
                self.check(a)

    def test_empty_source_or_symlink_is_not_a_readback(self):
        (self.root / 'source.txt').write_bytes(b'')
        with self.assertRaises(SystemExit):
            self.check()
        (self.root / 'source.txt').unlink()
        (self.root / 'other.txt').write_bytes(b'isolated source fixture')
        (self.root / 'source.txt').symlink_to(self.root / 'other.txt')
        with self.assertRaises(SystemExit):
            self.check()


if __name__ == '__main__':
    unittest.main()
