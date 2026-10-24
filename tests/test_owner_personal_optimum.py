# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Reject lost provenance, invented chronology and evidence-free acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import ai_runtime_bootloader as boot
from tools.qikvrt_perfect_optimum import evaluate, load_policy

ROOT = Path(__file__).resolve().parents[1]


class PersonalOptimumBindingTests(unittest.TestCase):
    def setUp(self):
        self.context = json.loads((ROOT / 'AI_CONTEXT.json').read_text())
        self.policy = json.loads((ROOT / 'policy/OWNER_PERSONAL_OPTIMUM_V1.json').read_text())

    def check(self, policy=None, context=None):
        with patch.object(boot, 'load_json_object', return_value=policy or self.policy):
            return boot.load_personal_optimum(context or self.context)

    def test_longstanding_goal_does_not_invent_a_start_date(self):
        p = self.check()
        self.assertTrue(p['chronology']['longstanding_personal_optimum'])
        self.assertIsNone(p['chronology']['inception_date'])
        self.assertFalse(p['chronology']['recording_date_is_inception_date'])

    def test_wrong_author_is_rejected(self):
        p = copy.deepcopy(self.policy)
        p['owner'] = 'Another author'
        with self.assertRaisesRegex(boot.BootBlock, 'owner'):
            self.check(p)

    def test_quote_cannot_be_silently_changed(self):
        p = copy.deepcopy(self.policy)
        p['original_statement']['text'] += ' altered'
        with self.assertRaisesRegex(boot.BootBlock, 'identity'):
            self.check(p)

    def test_rehashing_a_changed_quote_does_not_change_the_context_pin(self):
        p = copy.deepcopy(self.policy)
        p['original_statement']['text'] += ' altered'
        p['original_statement']['utf8_sha256'] = hashlib.sha256(
            p['original_statement']['text'].encode()).hexdigest()
        with self.assertRaisesRegex(boot.BootBlock, 'identity'):
            self.check(p)

    def test_recording_date_cannot_be_used_as_inception(self):
        p = copy.deepcopy(self.policy)
        p['chronology']['inception_date'] = p['chronology']['recorded_on']
        with self.assertRaisesRegex(boot.BootBlock, 'origin'):
            self.check(p)

    def test_ai_read_order_cannot_drop_the_goal(self):
        c = copy.deepcopy(self.context)
        c['required_read_order'].remove('policy/OWNER_PERSONAL_OPTIMUM_V1.json')
        with self.assertRaisesRegex(boot.BootBlock, 'read order'):
            self.check(context=c)

    def test_reading_the_goal_cannot_be_claimed_as_peer_adoption(self):
        p = copy.deepcopy(self.policy)
        p['completion_claims']['ALL_CLIENTS_ADOPTED'] = True
        with self.assertRaisesRegex(boot.BootBlock, 'unobserved'):
            self.check(p)

    def test_historical_policy_is_restored_with_exact_original_bytes(self):
        data = (ROOT / 'policy/PERFECT_OPTIMUM_V1.json').read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        self.assertEqual(blob, 'b9019a5abeb1e8a56c118128d3fdd91da54af37c')

    def test_canonical_entrypoint_remains_a_file(self):
        self.assertTrue((ROOT / 'AI').is_file())
        self.assertIn(self.policy['original_statement']['text'], (ROOT / 'AI').read_text())


class ImprovementEvidenceRegressionTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(ROOT / 'policy/PERFECT_OPTIMUM_V1.json')
        self.before = {m['id']: m.get('target', 2) for m in self.policy['bound_metrics']}
        self.after = dict(self.before, deterministic_blockers=1)
        self.checks = {k: True for k in self.policy['hard_invariants']}

    def test_empty_checks_cannot_vacuously_authorize_an_improvement(self):
        self.assertEqual(evaluate(self.before, self.after, {}, self.policy)['decision'], 'HOLD')

    def test_one_missing_invariant_blocks_the_candidate(self):
        self.checks.pop('evidence_before_claim')
        self.assertEqual(evaluate(self.before, self.after, self.checks, self.policy)['decision'], 'HOLD')

    def test_truthy_strings_are_not_evidence(self):
        self.checks['evidence_before_claim'] = 'false'
        self.assertEqual(evaluate(self.before, self.after, self.checks, self.policy)['decision'], 'HOLD')

    def test_unknown_invariant_cannot_be_smuggled_in(self):
        self.checks['unreviewed_override'] = True
        self.assertEqual(evaluate(self.before, self.after, self.checks, self.policy)['decision'], 'HOLD')

    def test_nan_is_not_a_non_regressing_measurement(self):
        self.after['avoidable_human_interventions'] = float('nan')
        self.assertEqual(evaluate(self.before, self.after, self.checks, self.policy)['decision'], 'HOLD')

    def test_boolean_is_not_a_numeric_measurement(self):
        self.after['productive_writer_count'] = True
        self.assertEqual(evaluate(self.before, self.after, self.checks, self.policy)['decision'], 'HOLD')

    def test_complete_bound_progress_is_still_admitted(self):
        self.assertEqual(evaluate(self.before, self.after, self.checks, self.policy)['decision'], 'ACCEPT_CANDIDATE')


class RecoveredSourceIntakeTests(unittest.TestCase):
    def setUp(self):
        self.context = json.loads((ROOT / 'AI_CONTEXT.json').read_text())
        self.index = json.loads((ROOT / self.context['recovered_goldkelch_sources']['index']).read_text())
        self.original_loader = boot.load_json_object

    def load_with(self, index=None, mutate_page=None):
        def loader(path, label):
            if path.name == 'INDEX.json':
                return index or self.index
            value = self.original_loader(path, label)
            if mutate_page and path.name == self.index['file_pages'][0]:
                mutate_page(value)
            return value
        with patch.object(boot, 'load_json_object', side_effect=loader):
            return boot.load_recovered_sources(self.context)

    def test_all_preserved_original_bytes_are_independently_verified(self):
        result = self.load_with()
        self.assertEqual(result['inactive_objects_byte_verified'], 1637)
        self.assertEqual(result['historical_refs_bound'], 1028)
        self.assertFalse(result['archived_source_executed'])

    def test_old_workflows_cannot_be_activated_by_the_catalog(self):
        index = copy.deepcopy(self.index)
        index['activation_contract']['activate_historical_workflows'] = True
        with self.assertRaisesRegex(boot.BootBlock, 'execution authority'):
            self.load_with(index=index)

    def test_binary_review_digest_cannot_drift(self):
        index = copy.deepcopy(self.index)
        index['payload_retention_review']['sha256'] = '0' * 64
        with self.assertRaisesRegex(boot.BootBlock, 'review identity changed'):
            self.load_with(index=index)

    def test_binary_review_cannot_grant_execution(self):
        def loader(path, label):
            value = self.original_loader(path, label)
            if path.name == 'payload-review-20261024.json':
                value['archived_programs_executed'] = True
            return value
        with patch.object(boot, 'load_json_object', side_effect=loader):
            with self.assertRaisesRegex(boot.BootBlock, 'cannot grant execution authority'):
                boot.load_recovered_sources(self.context)

    def test_binary_review_cannot_drop_a_payload(self):
        def loader(path, label):
            value = self.original_loader(path, label)
            if path.name == 'payload-review-20261024.json':
                value['payloads'] = value['payloads'][1:]
            return value
        with patch.object(boot, 'load_json_object', side_effect=loader):
            with self.assertRaisesRegex(boot.BootBlock, 'review coverage changed'):
                boot.load_recovered_sources(self.context)

    def test_bounded_archive_cannot_claim_live_completeness(self):
        index = copy.deepcopy(self.index)
        index['completion_claims']['ALL_GOLDKELCH_LIVE_DATA_RECOVERED'] = True
        with self.assertRaisesRegex(boot.BootBlock, 'unobserved completeness'):
            self.load_with(index=index)

    def test_index_cannot_hide_a_missing_source_page(self):
        index = copy.deepcopy(self.index)
        index['file_pages'] = index['file_pages'][1:]
        with self.assertRaisesRegex(boot.BootBlock, 'coverage'):
            self.load_with(index=index)

    def test_original_object_path_cannot_escape_the_catalog(self):
        def mutate(page):
            item = next(v for v in page['entries'] if v['disposition'] == 'PRESERVED_INACTIVE_SOURCE_NOT_EXECUTED')
            item['object_path'] = '../' + item['source_blob']
        with self.assertRaisesRegex(boot.BootBlock, 'object binding'):
            self.load_with(mutate_page=mutate)

    def test_rehashed_index_cannot_change_source_blob_identity(self):
        def mutate(page):
            item = next(v for v in page['entries'] if v['disposition'] == 'PRESERVED_INACTIVE_SOURCE_NOT_EXECUTED')
            item['sha256'] = '0' * 64
        with self.assertRaisesRegex(boot.BootBlock, 'bytes changed'):
            self.load_with(mutate_page=mutate)


if __name__ == '__main__':
    unittest.main()
