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
        self.check(dict(method='POST', service='github',
                        endpoint='https://api.github.com/repos/ingolf-lohmann/qik-vrt/git/trees',
                        specification_use='HISTORICAL_EXACT',
                        specification_claims=[], specification_basis=dict(
                            subject=self.subject, scope='SOURCE_REPAIR_ONLY',
                            reason='repair frozen source only')))

    def readonly_retry(self):
        path = '.github/workflows/qikvrt_reflexive_repository_watchdog.yml'
        original = Path(__file__).resolve().parents[1] / path
        target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(original.read_bytes())
        before = dict(schema='qikvrt_job_readback_budget_v1', expected_head_sha=self.subject['head'],
            selection='LATEST_PER_WORKFLOW_AND_ALL_ACTIVE_V1', state='HOLD',
            first_blocker='JOB_READBACK_REQUEST_BUDGET_EXCEEDED', max_job_requests=20,
            reported_run_count=22, returned_run_count=22, required_job_request_count=22,
            inventory_sha256='a'*64, run_ids=[], metadata_only_run_ids=[])
        after = dict(before, state='READY', first_blocker=None, required_job_request_count=20,
            inventory_sha256='b'*64, run_ids=list(range(1,21)), metadata_only_run_ids=[21,22])
        return dict(method='POST', service='github', transport='REST_API_ONLY',
            tool='github_rerun_failed_workflow_run_jobs',
            endpoint='https://api.github.com/repos/ingolf-lohmann/qik-vrt/actions/runs/7/rerun-failed-jobs',
            specification_use='HISTORICAL_EXACT', specification_claims=[],
            specification_basis=dict(subject=self.subject, scope='SOURCE_REPAIR_ONLY', reason='exact read-only source verification'),
            verification_retry=dict(schema='qikvrt-readonly-watchdog-budget-recovery/v1',
                run=dict(id=7, workflow_id=331355883, path=path, head_sha=self.subject['head'],
                         status='completed', conclusion='failure', run_attempt=1),
                failure_receipt=dict(schema='qikvrt_reflexive_observation_failure_receipt_v1',
                    repository=self.subject['repository'],head_sha=self.subject['head'],tree_sha=self.subject['tree'],
                    run_id=7,run_attempt=1,state='OBSERVATION_FAILED',disposition='HOLD',
                    failure=dict(stage='JOBS_BUDGET_PREFLIGHT',exit_code=2),effect_ack_done=False),
                previous_budget=before, current_budget=after))

    def test_readonly_frozen_watchdog_retry_requires_actual_budget_recovery(self):
        self.check(self.readonly_retry())

    def test_readonly_retry_rejects_unchanged_or_over_budget_observation(self):
        a = self.readonly_retry()
        for change in ('same', 'over', 'incomplete', 'duplicate', 'raised_cap'):
            x = copy.deepcopy(a); b = x['verification_retry']['current_budget']
            if change == 'same': b['inventory_sha256'] = 'a'*64
            if change == 'over': b['required_job_request_count'] = 22
            if change == 'incomplete': b['returned_run_count'] = 21
            if change == 'duplicate': b['run_ids'][0] = b['run_ids'][1]
            if change == 'raised_cap': b['max_job_requests'] = 22
            with self.subTest(change=change), self.assertRaises(SystemExit): self.check(x)

    def test_readonly_retry_rejects_other_workflow_source_identity_and_approval(self):
        a = self.readonly_retry()
        for key, value in [('workflow_id', 1), ('path', '.github/workflows/deploy.yml'),
                           ('head_sha', 'f'*40), ('conclusion', 'action_required'),
                           ('id', 8), ('run_attempt', True), ('run_attempt', 2), ('status', 'in_progress')]:
            x = copy.deepcopy(a); x['verification_retry']['run'][key] = value
            with self.subTest(key=key), self.assertRaises(SystemExit): self.check(x)

    def test_readonly_retry_cannot_dispatch_deploy_or_execute_a_changed_recipe(self):
        a = self.readonly_retry()
        for change in ('dispatch', 'query', 'tool', 'current_claim', 'recipe'):
            x = copy.deepcopy(a)
            if change == 'dispatch': x['endpoint'] = x['endpoint'].replace('/runs/7/rerun-failed-jobs', '/workflows/deploy/dispatches')
            if change == 'query': x['endpoint'] += '?enable_debug_logging=true'
            if change == 'tool': x['tool'] = 'github_rerun_workflow_job'
            if change == 'current_claim': x['specification_claims'] = ['effect-ack']
            if change == 'recipe':
                p = self.root / x['verification_retry']['run']['path']; p.write_bytes(p.read_bytes() + b'\n# changed\n')
            with self.subTest(change=change), self.assertRaises(SystemExit): self.check(x)

    def native_api_retry(self):
        action = self.readonly_retry()
        for path in ('.github/workflows/qikvrt_ci.yml', 'tools/qikvrt_self_host_container.py', 'tools/qikvrt_self_host.py'):
            target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((Path(__file__).resolve().parents[1] / path).read_bytes())
        proof = action['verification_retry']; proof.pop('previous_budget')
        proof['schema'] = 'qikvrt-readonly-watchdog-native-api-recovery/v1'
        proof['failure_receipt'].update(failure=dict(stage='BASELINE_READBACK', exit_code=5),
                                       observed_at='1970-01-01T00:15:00Z')
        proof['failed_job'] = dict(id=70, run_id=7, run_attempt=1, head_sha=self.subject['head'], status='completed', conclusion='failure')
        proof['failure_log_sha256'] = 'c'*64
        proof['failure_log_excerpt'] = 'gh: API rate limit exceeded for installation (HTTP 403)'
        proof['native_api_witness'] = dict(
            run=dict(id=8, run_attempt=1, path='.github/workflows/qikvrt_ci.yml',
                repository=dict(full_name=self.subject['repository']), head_sha=self.subject['head'],
                head_commit=dict(tree_id=self.subject['tree']), status='completed', conclusion='success'),
            job=dict(id=80, run_id=8, run_attempt=1, head_sha=self.subject['head'],
                name='Linux S1 native terminal production and smoke', status='completed', conclusion='success',
                completed_at='1970-01-01T00:16:40Z', steps=[dict(
                    name='Verify and reuse original PR494 Docker carrier', status='completed', conclusion='success',
                    started_at='1970-01-01T00:16:30Z', completed_at='1970-01-01T00:16:35Z')]))
        return action

    def test_native_api_retry_requires_later_exact_native_rest_success(self):
        self.check(self.native_api_retry())
        for change in ('old', 'future', 'stale', 'step', 'duplicate', 'source', 'tree', 'repo',
                       'attempt', 'boolean_attempt', 'budget', 'error', 'failure', 'job', 'native_run', 'recipe'):
            action = self.native_api_retry(); proof = action['verification_retry']
            witness = proof['native_api_witness']; job = witness['job']; step = job['steps'][0]
            if change == 'old': step['started_at'] = '1970-01-01T00:14:00Z'
            if change == 'future': job['completed_at'] = '1970-01-01T00:20:00Z'
            if change == 'step': step['conclusion'] = 'skipped'
            if change == 'duplicate': job['steps'].append(copy.deepcopy(step))
            if change == 'source': witness['run']['head_sha'] = 'f'*40
            if change == 'tree': witness['run']['head_commit']['tree_id'] = 'f'*40
            if change == 'repo': witness['run']['repository']['full_name'] = 'other/repo'
            if change == 'attempt': proof['failed_job']['run_attempt'] = 2
            if change == 'boolean_attempt': job['run_attempt'] = True
            if change == 'budget': proof['current_budget']['max_job_requests'] = 21
            if change == 'error': proof['failure_log_excerpt'] = 'unrelated HTTP 403'
            if change == 'failure': proof['failure_receipt']['failure']['stage'] = 'SUBJECT_READBACK'
            if change == 'job': job['conclusion'] = 'failure'
            if change == 'native_run': witness['run']['conclusion'] = 'failure'
            if change == 'recipe':
                p = self.root / 'tools/qikvrt_self_host_container.py'; p.write_bytes(p.read_bytes() + b'\n')
            with self.subTest(change=change), self.assertRaises(SystemExit):
                self.check(action, now=5000 if change == 'stale' else 1001)

    def test_historical_label_cannot_bypass_currentness_for_productive_effect(self):
        for endpoint in ('https://raumzeitterminal.de/api/eap/effect',
                         'https://api.github.com/repos/other/repo/git/trees',
                         'https://api.github.com/repos/ingolf-lohmann/qik-vrt/actions/workflows/deploy/dispatches',
                         'https://api.github.com.evil.example/repos/ingolf-lohmann/qik-vrt/git/trees'):
            a = dict(method='POST', service='github', endpoint=endpoint,
                     specification_use='HISTORICAL_EXACT', specification_claims=[],
                     specification_basis=dict(subject=self.subject, scope='SOURCE_REPAIR_ONLY', reason='fixture'))
            with self.subTest(endpoint=endpoint), self.assertRaises(SystemExit):
                self.check(a)

    def test_existing_private_journal_route_can_retain_repair_evidence(self):
        self.check(dict(method='POST', service='workspace',
                        tool='qik_vrt_kognitiver_arbeitsraum_update_task',
                        endpoint='https://qikvrt-cognition-workspace.ingolf-lohmann.chatgpt.site/mcp',
                        specification_use='HISTORICAL_EXACT', specification_claims=[],
                        specification_basis=dict(subject=self.subject, scope='SOURCE_REPAIR_ONLY', reason='journal')))

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
