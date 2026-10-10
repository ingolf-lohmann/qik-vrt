#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Execute the real writer and reader against a bounded Git-Data REST model."""
import base64
import copy
import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import qikvrt_mirror_node_lifecycle as live
from tools import qikvrt_seed_common as seed
from tests import test_seed_workflows as seed_tests
from tests.test_seed_workflows import GUID, SEED, NOW, FakeFetcher, remote_documents

REPOSITORY = 'ingolf-lohmann/qik-vrt'
SOURCE = 'a' * 40


class MemoryRest:
    """Models create-only refs and Git non-fast-forward rejection, including races."""
    def __init__(self, files):
        self.refs = {'main': SOURCE}
        self.blobs, self.trees = {}, {}
        self.commits = {SOURCE: {'sha': SOURCE, 'tree': {'sha': 'b' * 40}, 'parents': []}}
        self.source_files = files
        self.calls = []
        self.deny, self.ambiguous, self.race = None, None, False
        self.rules = [{'type': 'pull_request', 'parameters': {
            'required_approving_review_count': 1, 'require_code_owner_review': True,
            'dismiss_stale_reviews_on_push': True, 'require_last_push_approval': True}}]
        self.runs = {}

    def __call__(self, method, path, data=None):
        self.calls.append((method, path, copy.deepcopy(data)))
        if self.deny == (method, path):
            raise live.ApiError(403)
        result = self.respond(method, path, data)
        if self.ambiguous == (method, path):
            raise live.ApiError()
        return copy.deepcopy(result)

    def respond(self, method, path, data):
        if path == 'rules/branches/main':
            return self.rules
        if method == 'GET' and path.startswith('git/ref/heads/'):
            branch = path.removeprefix('git/ref/heads/')
            if branch not in self.refs:
                raise live.ApiError(404)
            return {'ref': 'refs/heads/' + branch, 'object': {'type': 'commit', 'sha': self.refs[branch]}}
        if method == 'GET' and path.startswith('git/commits/'):
            return self.commits[path.split('/')[-1]]
        if method == 'GET' and path.startswith('git/trees/'):
            return {'truncated': False, 'tree': self.trees[path.split('/')[-1]]}
        if method == 'GET' and path.startswith('contents/'):
            filename, head = path.removeprefix('contents/').split('?ref=')
            if head == SOURCE:
                raw = self.source_files[filename]
            else:
                tree = self.trees[self.commits[head]['tree']['sha']]
                blob = next(e['sha'] for e in tree if e['path'] == filename)
                raw = self.blobs[blob]
            return {'type': 'file', 'encoding': 'base64', 'sha': live.blob_id(raw),
                    'content': base64.b64encode(raw).decode()}
        if method == 'GET' and path.startswith('compare/'):
            return {'status': 'identical', 'behind_by': 0}
        if method == 'GET' and path.startswith('actions/runs/'):
            parts = path.split('/')
            run_id, attempt = int(parts[2]), int(parts[4])
            run = self.runs[(run_id, attempt)]
            if '/jobs?' in path:
                return {'total_count': 1, 'jobs': [{'head_sha': SOURCE,
                    'steps': [{'name': live.PUBLICATION_STEP, 'conclusion': 'success'}]}]}
            return run
        if method == 'POST' and path == 'git/blobs':
            raw = base64.b64decode(data['content']); sha = live.blob_id(raw)
            self.blobs[sha] = raw
            return {'sha': sha}
        if method == 'POST' and path == 'git/trees':
            entries = data['tree']
            raw = b''.join(e['mode'].encode() + b' ' + e['path'].encode() + b'\0' + bytes.fromhex(e['sha'])
                           for e in sorted(entries, key=lambda e: e['path']))
            sha = hashlib.sha1(b'tree ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            self.trees[sha] = entries
            return {'sha': sha}
        if method == 'POST' and path == 'git/commits':
            sha = hashlib.sha1(seed.canonical_json_bytes(data)).hexdigest()
            self.commits[sha] = {'sha': sha, 'tree': {'sha': data['tree']},
                                 'parents': [{'sha': p} for p in data['parents']]}
            return self.commits[sha]
        if method == 'POST' and path == 'git/refs':
            branch = data['ref'].removeprefix('refs/heads/')
            if self.race:
                self.refs[branch] = 'c' * 40
            if branch in self.refs:
                raise live.ApiError(422)
            self.refs[branch] = data['sha']
            return {'object': {'sha': data['sha']}}
        if method == 'PATCH' and path == 'git/refs/heads/' + live.LIVE_BRANCH:
            if self.race:
                self.refs[live.LIVE_BRANCH] = 'c' * 40
            parents = [p['sha'] for p in self.commits[data['sha']]['parents']]
            if data['force'] is not False or self.refs[live.LIVE_BRANCH] not in parents:
                raise live.ApiError(422)
            self.refs[live.LIVE_BRANCH] = data['sha']
            return {'object': {'sha': data['sha']}}
        raise AssertionError((method, path))


class LifecyclePublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.node = seed.NodeRecord(GUID, REPOSITORY, SEED, '', 'main', 1500, 'ACTIVE', '', 1)
        self.files = {p: ('fixture ' + p).encode() for p in live.SOURCE_PATHS}
        self.files[live.SOURCE_PATHS[-1]] = f'{GUID}\t{REPOSITORY}\t{SEED}\tindex\tentry\tmain\t1500\n'.encode()
        self.files['qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json'] = seed.canonical_json_bytes({
            'qikvrt_event': 'NODE_ACK_OF_SEED_ACCEPTANCE', 'guid': GUID, 'repository': REPOSITORY,
            'seed_repository': SEED, 'status': 'ACCEPTED_BY_SEED'})
        for p, b in self.files.items():
            q = self.root / p; q.parent.mkdir(parents=True, exist_ok=True); q.write_bytes(b)
        self.api = MemoryRest(self.files)
        self.make_pair()

    def make_pair(self, run='100-1', now=NOW):
        health = {'qikvrt_event': 'NODE_HEALTH_HEARTBEAT', 'guid': GUID, 'repository': REPOSITORY,
                  'seed_repository': SEED, 'node_branch': 'main', 'status': 'ACTIVE',
                  'heartbeat_utc': seed._format_utc(now), 'expires_utc': seed._format_utc(now + dt.timedelta(minutes=1500)),
                  'heartbeat_ttl_minutes': 1500, 'run_id': run,
                  'boundaries': {key: True for key in seed.BOUNDARY_KEYS}}
        renewal = {**health, 'qikvrt_event': 'NODE_REGISTRATION_RENEWAL', 'status': 'RENEWED',
                   'renewed_utc': health['heartbeat_utc'],
                   'next_renewal_due_utc': seed._format_utc(now + dt.timedelta(hours=24))}
        self.values = dict(zip(live.FILES[:2], (health, renewal)))
        self.write_pair()
        run_id, attempt = map(int, run.split('-'))
        self.api.runs[(run_id, attempt)] = {'id': run_id, 'run_attempt': attempt,
            'repository': {'full_name': REPOSITORY}, 'head_sha': SOURCE, 'head_branch': 'main',
            'path': live.WORKFLOW, 'event': 'schedule', 'run_started_at': seed._format_utc(now),
            'status': 'completed', 'conclusion': 'failure'}  # PR denial may fail the overall job.

    def write_pair(self):
        for name, value in self.values.items():
            (self.root / 'qikvrt/runtime/onboarding' / name).write_bytes(seed.canonical_json_bytes(value))

    def publish(self, run='100-1', now=NOW):
        result = live.publish(self.root, REPOSITORY, SOURCE, run, self.api, now)
        self.assertEqual(SOURCE, self.api.refs['main'])
        self.assertFalse(result['main_persisted'])
        return result

    def test_repeated_runs_remain_public_without_any_review_or_main_commit(self):
        previous = None
        for i in range(7):
            now = NOW + dt.timedelta(hours=6*i); run = f'{100+i}-1'
            self.make_pair(run, now); result = self.publish(run, now)
            documents, head = live.read_public(self.node, self.api, now)
            self.assertEqual(result['head'], head)
            self.assertEqual(run, documents[0].value['run_id'])
            if previous:
                self.assertIn(previous, [p['sha'] for p in self.api.commits[head]['parents']])
            previous = head
        self.assertFalse(any('pulls' in p or 'reviews' in p or p.endswith('heads/main') and m != 'GET'
                             for m, p, _ in self.api.calls))

    def test_replay_does_not_write_or_renew_time(self):
        first = self.publish(); count = len(self.api.calls)
        self.make_pair(now=NOW + dt.timedelta(hours=1))
        second = self.publish(now=NOW + dt.timedelta(hours=1))
        self.api.runs[(100,1)]['run_started_at'] = seed._format_utc(NOW)
        self.assertEqual('NOOP', second['state']); self.assertEqual(first['head'], second['head'])
        self.assertFalse(any(m != 'GET' for m, _, _ in self.api.calls[count:]))
        documents, _ = live.read_public(self.node, self.api, NOW + dt.timedelta(hours=1))
        self.assertEqual(seed._format_utc(NOW), documents[0].value['heartbeat_utc'])

    def test_parallel_first_writers_cannot_replace_create_only_ref(self):
        self.api.race = True
        with self.assertRaises(live.ApiError): self.publish()
        self.assertEqual('c'*40, self.api.refs[live.LIVE_BRANCH])
        self.assertEqual(1, sum(m == 'POST' and p == 'git/refs' for m,p,_ in self.api.calls))

    def test_parallel_successors_are_non_fast_forward_rejected_without_retry(self):
        self.publish(); self.make_pair('101-1', NOW + dt.timedelta(hours=6)); self.api.race = True
        with self.assertRaises(live.ApiError): self.publish('101-1', NOW + dt.timedelta(hours=6))
        writes = [d for m,p,d in self.api.calls if m == 'PATCH']
        self.assertEqual(1, len(writes)); self.assertIs(False, writes[0]['force'])

    def test_denied_ref_write_never_claims_publication(self):
        self.api.deny = ('POST', 'git/refs')
        with self.assertRaises(live.ApiError): self.publish()
        self.assertNotIn(live.LIVE_BRANCH, self.api.refs)

    def test_denied_update_retains_previous_public_snapshot(self):
        first = self.publish(); self.make_pair('101-1', NOW + dt.timedelta(hours=6))
        self.api.deny = ('PATCH', 'git/refs/heads/' + live.LIVE_BRANCH)
        with self.assertRaises(live.ApiError): self.publish('101-1', NOW + dt.timedelta(hours=6))
        self.assertEqual(first['head'], self.api.refs[live.LIVE_BRANCH])

    def test_lost_successful_ref_response_is_resolved_by_independent_get(self):
        self.api.ambiguous = ('POST', 'git/refs')
        self.assertEqual('PUBLIC_TELEMETRY_READ_BACK', self.publish()['state'])
        self.assertEqual(1, sum(m == 'POST' and p == 'git/refs' for m,p,_ in self.api.calls))

    def test_missing_enforcement_blocks_before_any_write(self):
        self.api.rules = []
        with self.assertRaisesRegex(live.Block, 'CODE_OWNER_RULE_NOT_ENFORCED'): self.publish()
        self.assertTrue(all(m == 'GET' for m,_,_ in self.api.calls))

    def test_health_and_registration_expiry_are_not_extended(self):
        self.publish()
        for hours in (24.01, 25.01):
            with self.assertRaisesRegex(live.Block, 'LIFECYCLE_EXPIRED'):
                live.read_public(self.node, self.api, NOW + dt.timedelta(hours=hours))

    def test_short_registry_ttl_remains_authoritative(self):
        self.publish()
        short = seed.dataclasses.replace(self.node, heartbeat_ttl_minutes=30)
        with self.assertRaisesRegex(live.Block, 'LIFECYCLE_EXPIRED'):
            live.read_public(short, self.api, NOW + dt.timedelta(minutes=31))

    def test_wrong_node_identity_rejected(self):
        self.values[live.FILES[0]]['guid'] = 'foreign'; self.write_pair()
        with self.assertRaises(seed.SeedError): self.publish()
        self.assertTrue(all(m == 'GET' for m,_,_ in self.api.calls))

    def test_pair_from_different_run_is_rejected(self):
        self.values[live.FILES[1]]['run_id'] = '99-1'; self.write_pair()
        with self.assertRaisesRegex(live.Block, 'PAIR_MISMATCH'): self.publish()

    def test_delayed_older_writer_does_not_regress_latest(self):
        self.publish(); self.make_pair('101-1', NOW - dt.timedelta(hours=1))
        with self.assertRaisesRegex(live.Block, 'OUT_OF_ORDER'): self.publish('101-1')

    def test_source_code_drift_blocks_before_publication(self):
        (self.root / live.SOURCE_PATHS[0]).write_text('changed')
        with self.assertRaisesRegex(live.Block, 'SOURCE_WORKTREE_MISMATCH'): self.publish()

    def test_foreign_failed_or_wrong_attempt_run_cannot_supply_provenance(self):
        self.publish()
        for key, value in [('head_sha', 'f'*40), ('event', 'pull_request'), ('head_branch', 'foreign'),
                           ('run_attempt', 2), ('path', '.github/workflows/other.yml')]:
            old = self.api.runs[(100,1)][key]; self.api.runs[(100,1)][key] = value
            with self.assertRaisesRegex(live.Block, 'RUN_PROVENANCE_INVALID'):
                live.read_public(self.node, self.api, NOW)
            self.api.runs[(100,1)][key] = old

    def test_missing_publication_step_success_is_not_replaced_by_run_success(self):
        self.publish()
        original = self.api.respond
        def respond(method, path, data):
            if '/jobs?' in path: return {'total_count': 1, 'jobs': [{'head_sha': SOURCE, 'steps': []}]}
            return original(method,path,data)
        self.api.respond = respond
        with self.assertRaisesRegex(live.Block, 'PUBLICATION_STEP_UNVERIFIED'):
            live.read_public(self.node, self.api, NOW)

    def test_public_read_uses_only_get_and_requires_no_credential(self):
        self.publish(); self.api.calls.clear()
        live.read_public(self.node, self.api, NOW)
        self.assertTrue(all(m == 'GET' for m,_,_ in self.api.calls))
        self.assertEqual('', live.Rest(REPOSITORY).token)

    def test_ref_drift_during_read_is_rejected(self):
        self.publish(); original = self.api.respond; count = 0
        def respond(method,path,data):
            nonlocal count
            if path == 'git/ref/heads/' + live.LIVE_BRANCH:
                count += 1
                if count == 2: self.api.refs[live.LIVE_BRANCH] = 'c'*40
            return original(method,path,data)
        self.api.respond = respond
        with self.assertRaisesRegex(live.Block, 'READ_DRIFT'):
            live.read_public(self.node,self.api,NOW)

    def test_transport_rejects_main_force_other_ref_and_redirect(self):
        api = live.Rest(REPOSITORY, 'secret-test-value')
        for method,path,payload in [('PATCH','git/refs/heads/main',{'force':False}),
            ('PATCH','git/refs/heads/'+live.LIVE_BRANCH,{'force':True}),
            ('POST','git/refs',{'ref':'refs/heads/main'}), ('POST','pulls',{})]:
            with self.assertRaises(live.Block): api(method,path,payload)
        self.assertIsNone(seed._NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.invalid'))

    def test_seed_uses_public_pair_and_fails_closed_without_legacy_fallback(self):
        fixture = seed_tests.SeedWorkflowTests(); fixture.setUp(); self.addCleanup(fixture.tearDown); fixture.accept()
        # Match the accepted fixture node; the resolver itself is separately exercised above.
        (fixture.root / 'registry/NODE_LIFECYCLE_TRANSPORT_V1.json').write_text(json.dumps({
            'schema': 'qikvrt_node_lifecycle_transport_v1', 'nodes': {GUID: {
                'repository':'example/node','transport':'PUBLIC_REST_SNAPSHOT_V1'}}}))
        fetch = FakeFetcher(remote_documents())
        with patch.object(live, 'read_public', side_effect=live.Block('LIFECYCLE_EXPIRED')):
            result = seed.run_maintenance(fixture.root,'public-expired',fetch,now=NOW,
                                          lifecycle_api_factory=lambda _: self.api)
        status = seed.read_json(fixture.root / 'registry/NODEMESH_STATUS.json')
        self.assertEqual('STALE', status['nodes'][0]['effective_status'])
        self.assertEqual([], fetch.calls)


class CandidateRestTests(unittest.TestCase):
    """Run candidate publication with real local Git objects; intercept REST only."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q'); self.git('config', 'user.name', 'fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.path = 'qikvrt/runtime/onboarding/NODE_HEALTH.json'
        p = self.root / self.path; p.parent.mkdir(parents=True); p.write_text('base\n')
        self.git('add', '.'); self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').strip()
        p.write_text('successor\n'); self.git('add', '.'); self.git('commit', '-qm', 'candidate')
        self.head = self.git('rev-parse', 'HEAD').strip(); self.tree = self.git('rev-parse', 'HEAD^{tree}').strip()
        self.branch = 'automation/mirror-lifecycle-' + '1'*24
        self.refs = {'main':self.base}; self.calls = []; self.denied = False

    def git(self, *args, raw=None, env=None):
        return subprocess.check_output(['git', *args], cwd=self.root, input=raw,
                                       env=env, stderr=subprocess.DEVNULL).decode()

    def api(self, method, path, data=None):
        self.calls.append((method,path))
        if method == 'GET' and path.startswith('git/ref/heads/'):
            branch = path.removeprefix('git/ref/heads/')
            if branch not in self.refs: raise live.ApiError(404)
            return {'ref':'refs/heads/'+branch,'object':{'type':'commit','sha':self.refs[branch]}}
        if method == 'GET' and path.startswith('git/commits/'):
            head = path.rsplit('/',1)[1]
            return {'sha':head,'tree':{'sha':self.git('show','-s','--format=%T',head).strip()},
                    'parents':[{'sha':p} for p in self.git('show','-s','--format=%P',head).split()]}
        if method == 'POST' and path == 'git/blobs':
            return {'sha':self.git('hash-object','-w','--stdin',raw=base64.b64decode(data['content'])).strip()}
        if method == 'POST' and path == 'git/trees':
            index = self.root / 'rest-index'
            env = {**os.environ,'GIT_INDEX_FILE':str(index)}
            self.git('read-tree',data['base_tree'],env=env)
            for e in data['tree']:
                self.git('update-index','--add','--cacheinfo',e['mode'],e['sha'],e['path'],env=env)
            tree = self.git('write-tree',env=env).strip(); index.unlink()
            return {'sha':tree}
        if method == 'POST' and path == 'git/commits':
            return {'sha':self.git('commit-tree',data['tree'],'-p',data['parents'][0],
                                   raw=(data['message']+'\n').encode()).strip()}
        if method == 'POST' and path == 'git/refs':
            if self.denied: raise live.ApiError(403)
            branch = data['ref'].removeprefix('refs/heads/')
            if branch in self.refs: raise live.ApiError(422)
            self.refs[branch] = data['sha']; return {'object':{'sha':data['sha']}}
        raise AssertionError((method,path))

    def execute(self):
        with patch.dict(os.environ, {'QIKVRT_RUN_ID':'100-1'}):
            return live.publish_candidate(self.root,REPOSITORY,self.base,self.head,self.tree,self.branch,self.api)

    def test_real_tree_roundtrip_and_repeated_candidate_reuse(self):
        head = self.execute()
        self.assertEqual(self.tree,self.api('GET','git/commits/'+head)['tree']['sha'])
        self.assertEqual(head,self.execute())
        self.assertEqual(1,self.calls.count(('POST','git/refs')))
        self.assertEqual(self.base,self.refs['main'])

    def test_denied_candidate_ref_never_writes_main_or_retries(self):
        self.denied = True
        with self.assertRaises(live.Block): self.execute()
        self.assertEqual(1,self.calls.count(('POST','git/refs')))
        self.assertEqual({'main':self.base},self.refs)

    def test_existing_foreign_candidate_tree_blocks(self):
        self.refs[self.branch] = self.base
        with self.assertRaisesRegex(live.Block,'READBACK_MISMATCH'): self.execute()
        self.assertEqual(self.base,self.refs[self.branch])

    def test_main_drift_blocks_before_object_writes(self):
        self.refs['main'] = self.head
        with self.assertRaisesRegex(live.Block,'BASE_DRIFT'): self.execute()
        self.assertTrue(all(m == 'GET' for m,_ in self.calls))

    def test_unrelated_candidate_delta_is_not_published(self):
        (self.root / 'unrelated.py').write_text('unrelated')
        self.git('add','.'); self.git('commit','-qm','unrelated')
        self.head = self.git('rev-parse','HEAD').strip(); self.tree = self.git('rev-parse','HEAD^{tree}').strip()
        with self.assertRaisesRegex(live.Block,'NON_ALLOWLISTED_DELTA'): self.execute()
        self.assertTrue(all(m == 'GET' for m,_ in self.calls))


if __name__ == '__main__':
    unittest.main()
