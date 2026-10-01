#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Provider contract tests; real Git CAS/refs and HTTP shim, not live GitHub."""
import base64
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
from http.server import ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.request

from tests import test_qikvrt_authority_transition as transition_tests
ADMIN = transition_tests.ADMIN
OLD_TOKEN = transition_tests.OLD_TOKEN
NEW_TOKEN = transition_tests.NEW_TOKEN
COMPETITOR_TOKEN = transition_tests.COMPETITOR_TOKEN
from src import qikvrt_github_api_shim as shim
from tools import qikvrt_authority_transition as transition
from tools import qikvrt_mesh_recovery as recovery
from tools.qikvrt_seed_common import canonical_json_bytes


class GitProviderFixture:
    """Independent durable bare Git provider; create-only update-ref CAS."""
    def __init__(self, node: Path, destination: Path):
        shutil.copytree(node / 'repository.git', destination)
        self.repository = destination
        self.posts = 0
        self.calls = []
        self.before_post = None
        self.after_post = None
        self.hide_ref = False
        self.wrong_tree = False

    def request(self, method, suffix, payload=None, *, admission=None):
        self.calls.append((method, suffix))
        if suffix.startswith('git/trees/'):
            oid = suffix.removeprefix('git/trees/')
            raw = subprocess.check_output(['git', '-C', str(self.repository), 'ls-tree', '-z', oid])
            entries = []
            for line in raw.split(b'\0'):
                if line:
                    metadata, name = line.split(b'\t', 1)
                    mode, kind, sha = metadata.decode().split()
                    entries.append({'path': name.decode(), 'mode': mode, 'type': kind, 'sha': sha})
            return 200, {'sha': oid, 'truncated': False, 'tree': entries}
        if suffix.startswith('git/blobs/'):
            oid = suffix.removeprefix('git/blobs/')
            raw = subprocess.check_output(['git', '-C', str(self.repository), 'cat-file', 'blob', oid])
            return 200, {'sha': oid, 'encoding': 'base64', 'content': base64.b64encode(raw).decode(), 'size': len(raw)}
        if suffix == 'graphql':
            self.posts += 1
            value = payload['variables']['input']
            ref = 'refs/heads/' + value['branch']['branchName']
            if self.before_post:
                self.before_post({'ref': ref, 'sha': value['expectedHeadOid']})
            with tempfile.TemporaryDirectory() as directory:
                env = {**os.environ, 'GIT_INDEX_FILE': str(Path(directory)/'index'),
                    'GIT_AUTHOR_NAME': 'Provider fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                    'GIT_COMMITTER_NAME': 'Provider fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
                git = ['git', '-C', str(self.repository)]
                subprocess.run(git+['read-tree', value['expectedHeadOid']], env=env, check=True, capture_output=True)
                for addition in value['fileChanges']['additions']:
                    blob = subprocess.check_output(git+['hash-object', '-w', '--stdin'], input=base64.b64decode(addition['contents']), env=env).decode().strip()
                    subprocess.run(git+['update-index', '--add', '--cacheinfo', '100644', blob, addition['path']], env=env, check=True, capture_output=True)
                tree = subprocess.check_output(git+['write-tree'], env=env).decode().strip()
                sha = subprocess.check_output(git+['commit-tree', tree, '-p', value['expectedHeadOid']],
                    input=(value['message']['headline']+'\n').encode(), env=env).decode().strip()
                result = subprocess.run(git+['update-ref', ref, sha, value['expectedHeadOid']], capture_output=True)
                if result.returncode:
                    return 422, {}
            if self.after_post:
                self.after_post()
            return 200, {'data': {'createCommitOnBranch': {'clientMutationId': value['clientMutationId'],
                'commit': {'oid': sha, 'tree': {'oid': tree}}}}}
        if method == 'POST':
            self.posts += 1
            if self.before_post:
                self.before_post(payload)
            result = subprocess.run(['git', '-C', str(self.repository), 'update-ref',
                payload['ref'], payload['sha'], '0' * 40], capture_output=True, timeout=10)
            if result.returncode:
                return 422, {}
            if self.after_post:
                self.after_post()
            return 201, {'ref': payload['ref'], 'object': {'type': 'commit', 'sha': payload['sha']}}
        if suffix.startswith('git/ref/'):
            ref = 'refs/' + suffix.removeprefix('git/ref/')
            result = subprocess.run(['git', '-C', str(self.repository), 'rev-parse', '--verify', ref],
                                    capture_output=True, timeout=10)
            if result.returncode or self.hide_ref:
                return 404, {}
            return 200, {'ref': ref, 'object': {'type': 'commit', 'sha': result.stdout.decode().strip()}}
        if suffix.startswith('git/commits/'):
            sha = suffix.removeprefix('git/commits/')
            tree = recovery.git_command(self.repository, 'rev-parse', sha + '^{tree}').strip()
            parents = recovery.git_command(self.repository, 'show', '-s', '--format=%P', sha).split()
            message = recovery.git_command(self.repository, 'show', '-s', '--format=%B', sha)
            return 200, {'sha': sha, 'tree': {'sha': '0' * 40 if self.wrong_tree else tree},
                'parents': [{'sha': p} for p in parents], 'message': message}
        raise AssertionError((method, suffix))


class GitHubAuthorityProviderTests(unittest.TestCase):
    setUp = transition_tests.AuthorityTransitionTests.setUp
    take = transition_tests.AuthorityTransitionTests.take
    activate = transition_tests.AuthorityTransitionTests.activate

    def provider(self, *, restart=False):
        if not hasattr(self, 'remote'):
            self.remote = GitProviderFixture(self.node, self.root / 'github-provider.git')
        cp = transition.AuthorityControlPlane(self.cp.path) if restart else self.cp
        adapter = shim.GitHubAuthorityProvider(cp, shim.PROVIDER_REPOSITORY)
        adapter._request = self.remote.request
        return adapter

    def execute(self, adapter, permit, key='mirror-effect', token=NEW_TOKEN):
        return adapter.execute(token, permit, {'operation': 'create_ref', 'effect_id': key})

    def journal(self, key='mirror-effect'):
        with self.cp.transaction() as db:
            row = db.execute('SELECT status, document FROM provider_effects WHERE id=?', (key,)).fetchone()
            return row[0], transition.decode(row[1])

    def test_successful_bound_mirror_effect_and_fresh_idempotent_replay(self):
        permit = self.activate()
        adapter = self.provider()
        result = self.execute(adapter, permit)
        self.assertTrue(result['fresh_provider_readback'])
        self.assertFalse(result['effect_ack_done'])
        self.assertFalse(result['provider_authority_fencing_verified'])
        self.assertEqual(result['repository'], 'ingolf-lohmann/qik-vrt')
        self.assertEqual(result['permit'], permit)
        for field in ('control_plane_epoch', 'node_id', 'fence'):
            self.assertIn(permit[field], result['ref'])
        actual = recovery.git_command(self.remote.repository, 'rev-parse', result['ref']).strip()
        self.assertEqual(actual, result['binding']['head'])
        replay = self.execute(self.provider(restart=True), permit)
        self.assertTrue(replay['replayed'])
        self.assertEqual(self.remote.posts, 1)
        self.assertEqual(self.journal()[0], 'VERIFIED')
        raw = self.cp.path.read_bytes()
        self.assertNotIn(NEW_TOKEN.encode(), raw)

    def test_old_writer_after_takeover_and_rejoin_never_calls_provider(self):
        permit = self.activate()
        adapter = self.provider()
        self.cp.rejoin(OLD_TOKEN, self.old_permit)
        for presented in (self.old_permit, permit):
            with self.assertRaises(transition.TransitionError):
                self.execute(adapter, presented, token=OLD_TOKEN)
        self.assertEqual(self.remote.calls, [])

    def test_stale_permit_each_epoch_node_fence_and_boolean_epoch(self):
        permit = self.activate()
        adapter = self.provider()
        for field in permit:
            stale = dict(permit)
            stale[field] = permit[field] - 1 if field == 'authority_epoch' else '0' * 64
            with self.assertRaises(transition.TransitionError):
                self.execute(adapter, stale)
        stale = {**permit, 'authority_epoch': True}
        with self.assertRaises(transition.TransitionError):
            self.execute(adapter, stale)
        self.assertEqual(self.remote.calls, [])

    def test_pending_activation_has_no_provider_access(self):
        permit = self.take()
        adapter = self.provider()
        with self.assertRaises(transition.TransitionError):
            self.execute(adapter, permit)
        self.assertEqual(self.remote.calls, [])

    def test_concurrent_takeover_loser_cannot_touch_provider(self):
        observations = [self.cp.observe(n, self.manifest, t) for n, t in
                       ((self.node, NEW_TOKEN), (self.competitor, COMPETITOR_TOKEN))]
        barrier = threading.Barrier(2)
        def run(node, token, observation):
            barrier.wait(timeout=10)
            try:
                permit = self.cp.takeover(node, self.manifest, token, observation)['permit']
                self.cp.activate(node, self.manifest, token, permit)
                return token, permit
            except transition.TransitionError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda x: run(*x), zip((self.node, self.competitor),
                (NEW_TOKEN, COMPETITOR_TOKEN), observations)))
        winners = [x for x in results if x]
        self.assertEqual(len(winners), 1)
        adapter = self.provider()
        token, permit = winners[0]
        loser = COMPETITOR_TOKEN if token == NEW_TOKEN else NEW_TOKEN
        with self.assertRaises(transition.TransitionError):
            self.execute(adapter, permit, token=loser)
        self.assertEqual(self.remote.calls, [])
        self.assertTrue(self.execute(adapter, permit, token=token)['fresh_provider_readback'])

    def test_provider_preexisting_ref_is_cas_conflict_never_accepted_as_our_effect(self):
        permit = self.activate()
        adapter = self.provider()
        ref = adapter.ref_name(permit, 'mirror-effect')
        head = self.cp.readback(NEW_TOKEN)['state']['binding']['head']
        recovery.git_command(self.remote.repository, 'update-ref', ref, head)
        with self.assertRaisesRegex(transition.TransitionError, 'CAS conflict'):
            self.execute(adapter, permit)
        with self.assertRaisesRegex(transition.TransitionError, 'rejected'):
            self.execute(self.provider(restart=True), permit)
        self.assertEqual(self.remote.posts, 0)
        self.assertEqual(self.journal()[0], 'REJECTED')

    def test_provider_native_cas_race_preserves_competing_ref(self):
        permit = self.activate()
        adapter = self.provider()
        other = recovery.git_command(self.remote.repository, 'rev-parse', 'HEAD^').strip()
        self.remote.before_post = lambda p: recovery.git_command(self.remote.repository,
            'update-ref', p['ref'], other)
        with self.assertRaises(transition.TransitionError):
            self.execute(adapter, permit)
        with self.assertRaisesRegex(transition.TransitionError, 'rejected'):
            self.execute(self.provider(restart=True), permit)
        ref = adapter.ref_name(permit, 'mirror-effect')
        self.assertEqual(recovery.git_command(self.remote.repository, 'rev-parse', ref).strip(), other)
        self.assertEqual(self.remote.posts, 1)
        self.assertEqual(self.journal()[0], 'REJECTED')

    def test_restart_after_committed_effect_before_transport_ack_is_get_only(self):
        permit = self.activate()
        adapter = self.provider()
        def crash():
            raise SystemExit('simulated process death')
        self.remote.after_post = crash
        with self.assertRaises(SystemExit):
            self.execute(adapter, permit)
        self.assertEqual(self.journal()[0], 'PENDING')
        result = self.execute(self.provider(restart=True), permit)
        self.assertTrue(result['fresh_provider_readback'])
        self.assertEqual(self.remote.posts, 1)
        self.assertEqual(self.journal()[0], 'VERIFIED')

    def test_restart_during_preflight_can_resume_without_losing_intent(self):
        permit = self.activate()
        adapter = self.provider()
        adapter._request = mock.Mock(side_effect=SystemExit('preflight process death'))
        with self.assertRaises(SystemExit):
            self.execute(adapter, permit)
        self.assertEqual(self.journal()[0], 'PREPARED')
        self.assertEqual(self.remote.posts, 0)
        result = self.execute(self.provider(restart=True), permit)
        self.assertTrue(result['fresh_provider_readback'])
        self.assertEqual(self.remote.posts, 1)

    def test_definite_cas_rejection_is_not_laundered_by_matching_competitor(self):
        permit = self.activate()
        adapter = self.provider()
        self.remote.before_post = lambda p: recovery.git_command(self.remote.repository,
            'update-ref', p['ref'], p['sha'])
        with self.assertRaisesRegex(transition.TransitionError, 'CAS conflict'):
            self.execute(adapter, permit)
        self.assertEqual(self.journal()[0], 'REJECTED')
        with self.assertRaisesRegex(transition.TransitionError, 'rejected'):
            self.execute(self.provider(restart=True), permit)
        self.assertEqual(self.remote.posts, 1)

    def test_same_key_concurrent_requests_have_at_most_one_provider_post(self):
        permit = self.activate()
        self.provider()
        barrier = threading.Barrier(2)
        def race():
            adapter = self.provider(restart=True)
            barrier.wait(timeout=10)
            try:
                return self.execute(adapter, permit)
            except transition.TransitionError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: race(), (1, 2)))
        self.assertTrue(any(r is not None for r in results))
        self.assertEqual(self.remote.posts, 1)
        self.assertEqual(self.journal()[0], 'VERIFIED')

    def test_timeout_without_observed_effect_never_retries_and_blocks_takeover(self):
        permit = self.activate()
        adapter = self.provider()
        def timeout(payload):
            raise transition.TransitionError('ambiguous provider timeout')
        self.remote.before_post = timeout
        with self.assertRaises(transition.TransitionError):
            self.execute(adapter, permit)
        self.remote.before_post = None
        with self.assertRaisesRegex(transition.TransitionError, 'not freshly observed'):
            self.execute(self.provider(restart=True), permit)
        self.assertEqual(self.remote.posts, 1)
        self.cp.authorize_recovery(self.competitor, self.manifest, ADMIN, '5' * 64)
        observation = self.cp.observe(self.competitor, self.manifest, '5' * 64)
        with self.assertRaisesRegex(transition.TransitionError, 'unresolved provider'):
            self.cp.takeover(self.competitor, self.manifest, '5' * 64, observation)
        with self.assertRaisesRegex(transition.TransitionError, 'unresolved provider'):
            self.execute(adapter, permit, key='another-effect')

    def test_takeover_cannot_interleave_with_outbound_post(self):
        permit = self.activate()
        adapter = self.provider()
        self.cp.authorize_recovery(self.competitor, self.manifest, ADMIN, '5' * 64)
        attempted = threading.Event()
        outcomes = []
        def other_takeover():
            attempted.set()
            try:
                observation = self.cp.observe(self.competitor, self.manifest, '5' * 64)
                outcomes.append(self.cp.takeover(self.competitor, self.manifest, '5' * 64, observation))
            except transition.TransitionError:
                outcomes.append(None)
        def while_post(payload):
            thread = threading.Thread(target=other_takeover)
            thread.start()
            self.addCleanup(thread.join, 10)
            self.assertTrue(attempted.wait(5))
            # Independent connection must remain locked across the provider CAS.
            with self.assertRaises(transition.TransitionError):
                with transition.AuthorityControlPlane(self.cp.path).transaction():
                    pass
            self.assertEqual(outcomes, [])
        self.remote.before_post = while_post
        try:
            result = self.execute(adapter, permit)
            self.assertTrue(result['fresh_provider_readback'])
        except transition.TransitionError:
            # A takeover after the verified effect and before the separate
            # ledger readback must reject the old receipt, never report success.
            self.assertEqual(self.journal()[0], 'VERIFIED')
        self.assertEqual(self.remote.posts, 1)

    def test_actual_readback_is_required_even_after_201(self):
        permit = self.activate()
        adapter = self.provider()
        self.remote.after_post = lambda: setattr(self.remote, 'hide_ref', True)
        with self.assertRaisesRegex(transition.TransitionError, 'not freshly observed'):
            self.execute(adapter, permit)
        self.assertEqual(self.journal()[0], 'PENDING')
        self.remote.hide_ref = False
        self.assertTrue(self.execute(adapter, permit)['fresh_provider_readback'])
        self.assertEqual(self.remote.posts, 1)

    def test_target_tree_drift_rejected_before_mutation(self):
        permit = self.activate()
        adapter = self.provider()
        self.remote.wrong_tree = True
        with self.assertRaises(transition.TransitionError):
            self.execute(adapter, permit)
        self.assertEqual(self.remote.posts, 0)
        self.assertEqual(self.journal()[0], 'REJECTED')

    def test_unknown_operations_fields_and_authority_root_are_denied(self):
        permit = self.activate()
        adapter = self.provider()
        for operation in ('update_ref', 'delete_ref', 'create_pr', 'merge_pr',
                          'create_branch', 'dispatch', 'ruleset_update'):
            with self.assertRaises(transition.TransitionError):
                adapter.execute(NEW_TOKEN, permit, {'operation': operation, 'effect_id': 'x'})
        with self.assertRaises(transition.TransitionError):
            adapter.execute(NEW_TOKEN, permit, {'operation': 'create_ref', 'effect_id': 'x', 'sha': '0' * 40})
        with self.assertRaises(transition.TransitionError):
            shim.GitHubAuthorityProvider(self.cp, 'Goldkelch/qik-vrt')
        self.assertEqual(self.remote.calls, [])

    def test_provider_idempotency_key_is_bound_across_epochs(self):
        permit = self.activate()
        adapter = self.provider()
        self.execute(adapter, permit)
        self.cp.authorize_recovery(self.competitor, self.manifest, ADMIN, '5' * 64)
        successor = self.take(self.competitor, '5' * 64)
        self.cp.activate(self.competitor, self.manifest, '5' * 64, successor)
        with self.assertRaisesRegex(transition.TransitionError, 'binding conflict'):
            self.execute(adapter, successor, token='5' * 64)
        self.assertEqual(self.remote.posts, 1)
        self.assertTrue(self.execute(adapter, successor, key='successor-effect', token='5' * 64)['fresh_provider_readback'])

    def test_missing_control_plane_is_not_recreated(self):
        permit = self.activate()
        adapter = self.provider()
        self.cp.path.unlink()
        with self.assertRaises(transition.TransitionError):
            self.execute(adapter, permit)
        self.assertFalse(self.cp.path.exists())
        self.assertEqual(self.remote.calls, [])

    def test_authenticated_existing_shim_route_has_real_http_readback_and_redaction(self):
        permit = self.activate()
        self.provider()
        api_token = 'b64url:' + base64.urlsafe_b64encode(b'a' * 32).rstrip(b'=').decode()
        environment = {'QIKVRT_API_TOKEN': api_token, 'QIKVRT_API_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z',
            'QIKVRT_API_PRINCIPAL': 'test-broker', 'QIKVRT_ALLOWED_REPOSITORY': shim.PROVIDER_REPOSITORY,
            'QIKVRT_AUTHORITY_CONTROL_PLANE': str(self.cp.path), 'QIKVRT_RATE_LIMIT_PER_MINUTE': '10000'}
        with mock.patch.dict(os.environ, environment), mock.patch.object(shim.GitHubAuthorityProvider,
                '_request', side_effect=self.remote.request):
            server = ThreadingHTTPServer(('127.0.0.1', 0), shim.QikvrtGitHubApiShim)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/repos/{shim.PROVIDER_REPOSITORY}/qikvrt/authority/effects'
                def send(writer=NEW_TOKEN, bearer=api_token):
                    body = {'writer_capability': writer, 'permit': permit,
                            'operation': {'operation': 'create_ref', 'effect_id': 'http-effect'}}
                    req = urllib.request.Request(url, data=canonical_json_bytes(body), headers={
                        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + bearer})
                    try:
                        response = urllib.request.urlopen(req, timeout=10)
                    except urllib.error.HTTPError as exc:
                        response = exc
                    with response:
                        return response.status, response.read()
                status, raw = send()
                self.assertEqual(status, 200)
                self.assertTrue(json.loads(raw)['provider_result']['fresh_provider_readback'])
                self.assertNotIn(NEW_TOKEN.encode(), raw)
                status, raw = send(OLD_TOKEN)
                self.assertEqual(status, 409)
                self.assertNotIn(OLD_TOKEN.encode(), raw)
                self.assertEqual(send(bearer='invalid')[0], 401)
                self.assertEqual(self.remote.posts, 1)
            finally:
                server.shutdown()
                thread.join(5)
                server.server_close()

    def test_transport_pins_origin_token_expiry_no_redirect_and_bounded_json(self):
        adapter = shim.GitHubAuthorityProvider(self.cp, shim.PROVIDER_REPOSITORY)
        env = {'QIKVRT_GITHUB_BROKER_TOKEN': 'github-test-token-abcdefghijklmnopqrstuvwxyz',
               'QIKVRT_GITHUB_BROKER_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z'}
        def response(raw=b'{"sha":"test"}', status=200, url=None):
            r = io.BytesIO(raw)
            r.status = status
            r.geturl = lambda: url or f'https://api.github.com/repos/{shim.PROVIDER_REPOSITORY}/git/refs'
            return r
        with mock.patch.dict(os.environ, env), mock.patch.object(shim.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = response()
            self.assertEqual(adapter._request('GET', 'git/refs')[0], 200)
            with self.assertRaises(transition.TransitionError):
                adapter._request('POST', 'git/refs', {'ref': 'refs/heads/main', 'sha': '0' * 40})
            self.assertIsInstance(opener.call_args.args[0], shim.NoRedirectHandler)
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, f'https://api.github.com/repos/{shim.PROVIDER_REPOSITORY}/git/refs')
            for raw, url in ((env['QIKVRT_GITHUB_BROKER_TOKEN'].encode(), None), (b'{}', 'https://other.invalid/'),
                             (b'{"duplicate":1,"duplicate":2}', None), (b'[]', None),
                             (b'x' * (shim.MAX_RESPONSE_BYTES + 1), None)):
                opener.return_value.open.return_value = response(raw, url=url)
                with self.assertRaises(transition.TransitionError):
                    adapter._request('GET', 'git/refs')
            with mock.patch.dict(os.environ, {'QIKVRT_GITHUB_BROKER_TOKEN_EXPIRES_UTC': '2000-01-01T00:00:00Z'}):
                with self.assertRaises(transition.TransitionError):
                    adapter._request('POST', 'git/refs', {})
            for method, suffix in (('DELETE', 'git/refs'), ('PATCH', 'git/refs'),
                                   ('POST', '../Goldkelch/qik-vrt/git/refs')):
                with self.assertRaises(transition.TransitionError):
                    adapter._request(method, suffix, {})

    def test_complete_production_http_transport_contract_with_locked_admission(self):
        permit = self.activate()
        self.provider()
        adapter = shim.GitHubAuthorityProvider(self.cp, shim.PROVIDER_REPOSITORY)
        prefix = f'https://api.github.com/repos/{shim.PROVIDER_REPOSITORY}/'
        env = {'QIKVRT_GITHUB_BROKER_TOKEN': 'github-test-token-abcdefghijklmnopqrstuvwxyz',
               'QIKVRT_GITHUB_BROKER_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z'}
        def open_request(request, timeout):
            self.assertEqual(timeout, 10)
            self.assertTrue(request.full_url.startswith(prefix))
            suffix = request.full_url.removeprefix(prefix)
            payload = json.loads(request.data) if request.data else None
            status, body = self.remote.request(request.method, suffix, payload)
            response = io.BytesIO(json.dumps(body).encode())
            response.status = status
            response.geturl = lambda: request.full_url
            return response
        with mock.patch.dict(os.environ, env), mock.patch.object(shim.urllib.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = open_request
            result = self.execute(adapter, permit)
            self.assertTrue(result['fresh_provider_readback'])
            self.assertEqual(self.remote.posts, 1)
            self.assertEqual(len(self.remote.calls), 5)
            self.assertTrue(self.execute(adapter, permit)['replayed'])
            self.assertEqual(self.remote.posts, 1)


class MaterializeSuccessorTests(unittest.TestCase):
    setUp = GitHubAuthorityProviderTests.setUp
    activate = GitHubAuthorityProviderTests.activate
    take = GitHubAuthorityProviderTests.take
    provider = GitHubAuthorityProviderTests.provider
    journal = GitHubAuthorityProviderTests.journal
    """Both necessary effects use the SAME fixture, sink, native CAS and journal."""
    def operation(self, profile="ci_integrity", key="ci-successor", head=None, tree=None):
        adapter = self.provider()
        state = self.cp.readback(NEW_TOKEN)["state"]
        head = head or state["binding"]["head"]
        tree = tree or state["binding"]["tree"]
        ref = "refs/heads/work/materializer-fixture"
        if not hasattr(self, 'successor_ref_initialized'):
            recovery.git_command(self.remote.repository, "update-ref", ref, head)
            self.successor_ref_initialized = True
        raw = b'{"materialized":true}\n'
        path = "REPOSITORY_FILE_MANIFEST.json" if profile == "ci_integrity" else "AI_STATUS.md"
        file = {"path": path, "contents": base64.b64encode(raw).decode(),
            "sha256": hashlib.sha256(raw).hexdigest(), "blob": adapter._git_oid("blob", raw)}
        desired = adapter._patched_tree(tree, [file])
        self.remote.calls.clear()
        return {"operation": "materialize_successor", "effect_id": key, "profile": profile,
            "ref": ref, "expected_head": head, "expected_tree": tree, "tree": desired, "files": [file]}

    def test_both_profiles_native_cas_bytes_durable_readback_and_replay(self):
        permit = self.activate()
        for profile in ("ci_integrity", "repository_evidence"):
            operation = self.operation(profile, key=profile)
            if profile == "repository_evidence":
                previous = self.result
                operation = self.operation(profile, key=profile, head=previous["sha"], tree=previous["tree"])
            self.result = self.provider().execute(NEW_TOKEN, permit, operation)
            self.assertTrue(self.result["native_ref_commit_tree_bytes_verified"])
            self.assertTrue(self.result["durable_ledger_readback"])
            self.assertFalse(self.result["effect_ack_done"])
            replay = self.provider(restart=True).execute(NEW_TOKEN, permit, operation)
            self.assertTrue(replay["replayed"])
            with self.cp.transaction() as db:
                self.assertEqual(db.execute("SELECT status FROM provider_effects WHERE id=?", (profile,)).fetchone(), ("VERIFIED",))
        self.assertEqual(self.remote.posts, 2)
        self.assertNotIn(NEW_TOKEN.encode(), self.cp.path.read_bytes())

    def test_missing_capability_and_each_stale_permit_never_reach_provider(self):
        permit = self.activate()
        operation = self.operation()
        for token, candidate in [("x" * 32, permit)] + [(NEW_TOKEN, {**permit, field:
            permit[field] - 1 if field == "authority_epoch" else "0" * 64}) for field in permit]:
            with self.assertRaises(transition.TransitionError):
                self.provider().execute(token, candidate, operation)
        self.assertEqual(self.remote.calls, [])

    def test_missing_private_provider_capability_persists_prepared_intent_no_transport(self):
        permit = self.activate()
        operation = self.operation()
        adapter = shim.GitHubAuthorityProvider(self.cp, shim.PROVIDER_REPOSITORY)
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(shim.urllib.request, "build_opener") as opener:
            with self.assertRaises(transition.TransitionError):
                adapter.execute(NEW_TOKEN, permit, operation)
            opener.assert_not_called()
        self.assertEqual(self.journal("ci-successor")[0], "PREPARED")

    def test_preexisting_advanced_ref_and_atomic_competing_writer_are_rejected(self):
        permit = self.activate()
        operation = self.operation()
        adapter = self.provider()
        other = recovery.git_command(self.remote.repository, "rev-parse", "HEAD^").strip()
        self.remote.before_post = lambda p: recovery.git_command(self.remote.repository, "update-ref", p["ref"], other)
        with self.assertRaises(transition.TransitionError):
            adapter.execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.journal("ci-successor")[0], "REJECTED")
        with self.assertRaises(transition.TransitionError):
            self.provider(restart=True).execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.remote.posts, 1)
        self.assertEqual(recovery.git_command(self.remote.repository, "rev-parse", operation["ref"]), other)

    def test_crash_after_effect_get_only_recovery_no_duplicate(self):
        permit = self.activate()
        operation = self.operation()
        self.remote.after_post = lambda: (_ for _ in ()).throw(SystemExit("lost response"))
        with self.assertRaises(SystemExit):
            self.provider().execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.journal("ci-successor")[0], "PENDING")
        recovered = self.provider(restart=True).execute(NEW_TOKEN, permit, operation)
        self.assertTrue(recovered["native_ref_commit_tree_bytes_verified"])
        self.assertEqual(self.remote.posts, 1)

    def test_ambiguous_transport_before_effect_stays_pending_and_blocks_other_writer(self):
        permit = self.activate()
        operation = self.operation()
        def lost_before_write(payload):
            raise transition.TransitionError("transport unknown")
        self.remote.before_post = lost_before_write
        with self.assertRaises(transition.TransitionError):
            self.provider().execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.journal("ci-successor")[0], "PENDING")
        for candidate in (operation, {**operation, "effect_id": "other"}):
            with self.assertRaises(transition.TransitionError):
                self.provider(restart=True).execute(NEW_TOKEN, permit, candidate)
        self.assertEqual(self.remote.posts, 1)

    def test_replay_with_different_binding_is_rejected_before_transport(self):
        permit = self.activate()
        operation = self.operation()
        self.provider().execute(NEW_TOKEN, permit, operation)
        self.remote.calls.clear()
        for changed in ({**operation, "ref": "refs/heads/work/other"},
                        {**operation, "expected_head": "0" * 40}):
            with self.assertRaises(transition.TransitionError):
                self.provider(restart=True).execute(NEW_TOKEN, permit, changed)
        self.assertEqual(self.remote.calls, [])

    def test_wrong_native_bytes_after_effect_stays_pending(self):
        permit = self.activate()
        operation = self.operation()
        adapter = self.provider()
        original = adapter._request
        def wrong_bytes(method, suffix, payload=None, **kwargs):
            status, body = original(method, suffix, payload, **kwargs)
            if suffix.startswith("git/blobs/"):
                body["content"] = base64.b64encode(b"wrong").decode()
            return status, body
        adapter._request = wrong_bytes
        with self.assertRaises(transition.TransitionError):
            adapter.execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.journal("ci-successor")[0], "PENDING")
        self.assertEqual(self.remote.posts, 1)

    def test_wrong_post_effect_commit_tree_and_ref_drift_never_verify(self):
        permit = self.activate()
        operation = self.operation()
        self.remote.after_post = lambda: setattr(self.remote, "wrong_tree", True)
        with self.assertRaises(transition.TransitionError):
            self.provider().execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.journal("ci-successor")[0], "PENDING")
        self.assertEqual(self.remote.posts, 1)

    def test_source_path_tree_and_byte_tampering_cannot_expand_effect(self):
        permit = self.activate()
        operation = self.operation()
        for bad in ({**operation, "tree": "0" * 40},
            {**operation, "files": [{**operation["files"][0], "path": ".github/workflows/writer.yml"}]},
            {**operation, "files": [{**operation["files"][0], "contents": "eA=="}]},
            {**operation, "ref": "refs/heads/main"}):
            with self.assertRaises(transition.TransitionError):
                self.provider().execute(NEW_TOKEN, permit, bad)
        self.assertEqual(self.remote.posts, 0)

    def test_real_http_transport_uses_only_fixed_graphql_and_native_gets(self):
        permit = self.activate()
        operation = self.operation()
        adapter = shim.GitHubAuthorityProvider(self.cp, shim.PROVIDER_REPOSITORY)
        env = {'QIKVRT_GITHUB_BROKER_TOKEN': 'github-test-token-abcdefghijklmnopqrstuvwxyz',
            'QIKVRT_GITHUB_BROKER_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z'}
        def transport(request, timeout):
            suffix = 'graphql' if request.full_url == 'https://api.github.com/graphql' else request.full_url.removeprefix(
                'https://api.github.com/repos/' + shim.PROVIDER_REPOSITORY + '/')
            payload = json.loads(request.data) if request.data else None
            if suffix == 'graphql':
                self.assertEqual(payload['query'], adapter.SUCCESSOR_QUERY)
                self.assertEqual(payload['variables']['input']['expectedHeadOid'], operation['expected_head'])
            status, body = self.remote.request(request.method, suffix, payload)
            response = io.BytesIO(json.dumps(body).encode())
            response.status = status
            response.geturl = lambda: request.full_url
            return response
        with mock.patch.dict(os.environ, env), mock.patch.object(shim.urllib.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = transport
            result = adapter.execute(NEW_TOKEN, permit, operation)
        self.assertTrue(result['durable_ledger_readback'])
        self.assertEqual(self.remote.posts, 1)

    def test_ambient_native_workflow_token_is_not_a_broker_capability(self):
        adapter = shim.GitHubAuthorityProvider(self.cp, shim.PROVIDER_REPOSITORY)
        with mock.patch.dict(os.environ, {'GITHUB_TOKEN': 'x'*40,
                'QIKVRT_GITHUB_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z'}, clear=True), \
                mock.patch.object(shim.urllib.request, 'build_opener') as opener:
            with self.assertRaises(transition.TransitionError):
                adapter._request('GET', 'git/refs')
            opener.assert_not_called()

    def test_concurrent_same_key_has_one_native_effect(self):
        permit = self.activate()
        operation = self.operation()
        barrier = threading.Barrier(2)
        def request(_):
            barrier.wait(timeout=10)
            try:
                return self.provider(restart=True).execute(NEW_TOKEN, permit, operation)
            except transition.TransitionError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(request, (1, 2)))
        self.assertTrue(any(result is not None for result in results))
        self.assertEqual(self.remote.posts, 1)
        self.assertEqual(self.journal('ci-successor')[0], 'VERIFIED')

    def test_native_commit_parent_and_intent_message_are_required(self):
        permit = self.activate()
        operation = self.operation()
        adapter = self.provider()
        original = adapter._request
        def altered(method, suffix, payload=None, **kwargs):
            status, body = original(method, suffix, payload, **kwargs)
            if suffix.startswith('git/commits/') and self.remote.posts:
                body['parents'] = [{'sha': '0'*40}]
                body['message'] = 'unrelated writer'
            return status, body
        adapter._request = altered
        with self.assertRaises(transition.TransitionError):
            adapter.execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.journal('ci-successor')[0], 'PENDING')

    def test_separate_durable_ledger_readback_is_required(self):
        from contextlib import contextmanager
        permit = self.activate()
        operation = self.operation()
        adapter = self.provider()
        original = self.cp.transaction
        count = 0
        @contextmanager
        def corrupt_durable_read():
            nonlocal count
            count += 1
            with original() as db:
                if count == 4:
                    db.execute("UPDATE provider_effects SET receipt=? WHERE id=?", (b'{}', operation['effect_id']))
                yield db
        with mock.patch.object(self.cp, 'transaction', corrupt_durable_read):
            with self.assertRaisesRegex(transition.TransitionError, 'ledger readback'):
                adapter.execute(NEW_TOKEN, permit, operation)
        self.assertEqual(self.remote.posts, 1)

    def client_roundtrip(self, files, *, native_transport=False):
        permit = self.activate()
        self.provider()
        checkout = self.root/'cli-checkout'
        subprocess.run(['git', 'clone', '-q', str(self.node/'repository.git'), str(checkout)], check=True)
        head = recovery.git_command(checkout, 'rev-parse', 'HEAD')
        ref = 'refs/heads/work/cli-fixture'
        recovery.git_command(self.remote.repository, 'update-ref', ref, head)
        for path, raw in files.items():
            (checkout/path).write_bytes(raw)
        recovery.git_command(checkout, 'add', *sorted(files))
        private = self.root/'client-private'
        private.mkdir(mode=0o700)
        api_token = 'b64url:' + base64.urlsafe_b64encode(b'a'*32).rstrip(b'=').decode()
        for name, content in [('api', api_token.encode()), ('writer', NEW_TOKEN.encode()),
                              ('permit', canonical_json_bytes(permit))]:
            path = private/name
            path.write_bytes(content)
            path.chmod(0o600)
        env = {'QIKVRT_API_TOKEN': api_token, 'QIKVRT_API_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z',
            'QIKVRT_API_PRINCIPAL': 'fixture-broker', 'QIKVRT_ALLOWED_REPOSITORY': shim.PROVIDER_REPOSITORY,
            'QIKVRT_AUTHORITY_CONTROL_PLANE': str(self.cp.path),
            'QIKVRT_AUTHORITY_API_TOKEN_FILE': str(private/'api'),
            'QIKVRT_AUTHORITY_WRITER_FILE': str(private/'writer'),
            'QIKVRT_AUTHORITY_PERMIT_FILE': str(private/'permit')}
        if native_transport:
            env.update(QIKVRT_GITHUB_BROKER_TOKEN='provider-test-token-abcdefghijklmnopqrstuvwxyz',
                       QIKVRT_GITHUB_BROKER_TOKEN_EXPIRES_UTC='2099-01-01T00:00:00Z')
        with ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, env))
            stack.enter_context(mock.patch.object(transition, 'ROOT', checkout))
            if native_transport:
                real_opener = urllib.request.build_opener(shim.NoRedirectHandler())
                def route(request, timeout):
                    if not request.full_url.startswith('https://api.github.com/'):
                        self.assertNotIn(env['QIKVRT_GITHUB_BROKER_TOKEN'].encode(), request.data)
                        return real_opener.open(request, timeout=timeout)
                    suffix = ('graphql' if request.full_url == 'https://api.github.com/graphql' else
                        request.full_url.removeprefix('https://api.github.com/repos/'+shim.PROVIDER_REPOSITORY+'/'))
                    status, body = self.remote.request(request.method, suffix,
                        json.loads(request.data) if request.data else None)
                    response = io.BytesIO(json.dumps(body).encode())
                    response.status = status
                    response.geturl = lambda: request.full_url
                    return response
                opener = mock.Mock()
                opener.open.side_effect = route
                stack.enter_context(mock.patch.object(urllib.request, 'build_opener', return_value=opener))
            else:
                stack.enter_context(mock.patch.object(shim.GitHubAuthorityProvider, '_request', side_effect=self.remote.request))
            server = ThreadingHTTPServer(('127.0.0.1', 0), shim.QikvrtGitHubApiShim)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                receipt = checkout/'.qikvrt/receipt.json'
                args = ['--profile', 'ci_integrity', '--target-ref', 'work/cli-fixture',
                    '--expected-head', head, '--receipt', str(receipt)]
                with mock.patch.dict(os.environ, {'QIKVRT_AUTHORITY_BROKER_URL': f'http://127.0.0.1:{server.server_port}'}):
                    self.assertEqual(transition.publish_successor(args), 0)
                    self.assertEqual(transition.publish_successor(args), 0)
                result = json.loads(receipt.read_bytes())
                self.assertTrue(result['replayed'])
                self.assertTrue(result['durable_ledger_readback'])
                self.assertFalse(result['effect_ack_done'])
                self.assertEqual(self.remote.posts, 1)
                for path, raw in files.items():
                    actual = subprocess.check_output(['git', '-C', str(self.remote.repository), 'show',
                        result['sha']+':'+path])
                    self.assertEqual(actual, raw)
            finally:
                server.shutdown()
                thread.join(5)
                server.server_close()

    def test_staged_workflow_client_existing_http_shim_provider_and_ledger_end_to_end(self):
        self.client_roundtrip({'REPOSITORY_FILE_MANIFEST.json': b'byte-exact\x00\xff\n'})

    def test_actual_three_integrity_files_fit_the_complete_http_cas_byte_ledger_path(self):
        files = {path: (transition.ROOT/path).read_bytes() for path in shim.GitHubAuthorityProvider.INTEGRITY_PATHS}
        self.assertGreater(sum(map(len, files.values())), 1024*1024)
        self.client_roundtrip(files, native_transport=True)

    def test_scoped_large_intent_decoder_stays_bounded_canonical_and_strict(self):
        adapter = self.provider()
        raw = canonical_json_bytes({'payload': 'x'*(1024*1024)})
        self.assertEqual(adapter._decode_materialization_intent(raw)['payload'], 'x'*(1024*1024))
        for bad in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'{"x":1}',
                    b'x'*(shim.AUTHORITY_REQUEST_BYTES+1)):
            with self.assertRaises(transition.TransitionError):
                adapter._decode_materialization_intent(bad)

    def test_capacity_and_accidental_shell_terminator_path_fail_before_provider(self):
        permit = self.activate()
        operation = self.operation()
        self.remote.calls.clear()
        raw = b'x'*(shim.MATERIALIZATION_FILE_BYTES+1)
        file = {**operation['files'][0], 'contents': base64.b64encode(raw).decode(),
            'blob': shim.GitHubAuthorityProvider._git_oid('blob', raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        with self.assertRaises(transition.TransitionError):
            self.provider().execute(NEW_TOKEN, permit, {**operation, 'files': [file]})
        self.assertFalse(shim.GitHubAuthorityProvider.successor_path_allowed('repository_evidence', 'fi'))
        raw = b'x'*shim.MATERIALIZATION_FILE_BYTES
        files = [{'path': path, 'contents': base64.b64encode(raw).decode(),
            'blob': shim.GitHubAuthorityProvider._git_oid('blob', raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for path in sorted(shim.GitHubAuthorityProvider.INTEGRITY_PATHS)]
        with self.assertRaises(transition.TransitionError):
            self.provider().execute(NEW_TOKEN, permit, {**operation, 'files': files})
        self.assertEqual(self.remote.calls, [])

    def test_workflow_cli_missing_provision_returns_hold_without_provider(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {}, clear=True):
            receipt = Path(directory)/"receipt.json"
            with mock.patch.object(shim.GitHubAuthorityProvider, "execute") as execute:
                self.assertEqual(transition.publish_successor(["--profile", "ci_integrity",
                    "--target-ref", "work/x", "--expected-head", "0"*40, "--receipt", str(receipt)]), 78)
                execute.assert_not_called()
            result = json.loads(receipt.read_bytes())
            self.assertEqual(result['state'], 'HOLD')
            self.assertFalse(result['productive_provider_effect'])
            self.assertFalse(result['effect_ack_done'])


class RepositoryNoBypassTests(unittest.TestCase):
    def fixture(self, directory, files):
        root = Path(directory)
        subprocess.run(['git', 'init', '-q', str(root)], check=True, timeout=10)
        for relative, source in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)
        return root

    def test_actual_candidate_source_has_no_admitted_raw_writer(self):
        result = transition.audit_repository_writers()
        self.assertEqual(result['violations'], [])
        self.assertEqual(result['state'], 'PASS')
        self.assertFalse(result['production_bypass_capabilities_revoked'])
        self.assertFalse(result['provider_authority_fencing_verified'])
        self.assertFalse(result['effect_ack_done'])
        paths = {record['path']: record['classification'] for record in result['records']}
        self.assertEqual(paths['QIKVRT_V45_11_REAL_GITHUB_RELEASE.cmd'], 'DISABLED_ENTRYPOINT')
        self.assertEqual(paths['QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd'], 'DISABLED_ENTRYPOINT')
        self.assertEqual(paths['scripts/qikvrt_github_api_client.sh'], 'DISABLED_ENTRYPOINT')
        self.assertEqual(paths['tools/qikvrt_zenodo_publish.py'], 'GET_ONLY_GITHUB_TRANSPORT')

    def test_untracked_and_tracked_new_raw_writers_fail_closed(self):
        candidates = [
            'git push origin HEAD:main\n',
            'git -c http.extraheader="$GITHUB_TOKEN" push origin main\n',
            'git send-pack origin main\n',
            'gh api --method POST repos/x/y/git/refs -f ref=refs/heads/x\n',
            'curl -X PATCH https://api.github.com/repos/x/y/git/refs/heads/main\n',
            'curl --data @payload https://api.github.com/repos/x/y/releases\n',
            'import requests\nrequests.post("https://api.github.com/repos/x/y/releases")\n',
            'import os\ntoken = os.environ["GITHUB_TOKEN"]\n',
            'import os\ntoken = os.environ["QIKVRT_GITHUB_BROKER_TOKEN"]\n',
            'gh api repos/x/y/git/refs -f ref=refs/heads/x\n',
            'github.rest.git.createRef({ref: "refs/heads/x"})\n',
            'curl https://api.github.com/repos/x/y/releases \\\n  --data @payload\n',
        ]
        for candidate in candidates:
            for path in ('tools/new_writer.sh', 'Makefile', 'tools/new_writer.cjs', 'package.json', 'tools/new-writer'):
                with self.subTest(candidate=candidate, path=path), tempfile.TemporaryDirectory() as directory:
                    root = self.fixture(directory, {path: '#!/bin/sh\n' + candidate})
                    self.assertEqual(transition.audit_repository_writers(root)['state'], 'BLOCK')
                    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True, timeout=10)
                    self.assertEqual(transition.audit_repository_writers(root)['state'], 'BLOCK')

    def test_incoming_documentation_and_tests_cannot_launder_active_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory, {'incoming/old.sh': 'git push origin main\n',
                'docs/example.sh': 'gh release create v1\n', 'tests/fixture.py': 'method="POST"\n'})
            result = transition.audit_repository_writers(root)
            self.assertEqual(result['state'], 'PASS')
            self.assertEqual({r['classification'] for r in result['records']}, {
                'HISTORICAL_INCOMING_NOT_ADMITTED', 'DOCUMENTARY_NOT_ADMITTED', 'TEST_FIXTURE_NOT_PRODUCTION'})
            (root/'tools').mkdir()
            (root/'tools/caller.sh').write_text('sh incoming/old.sh\n# GITHUB_TOKEN\n')
            self.assertEqual(transition.audit_repository_writers(root)['state'], 'BLOCK')

    def test_packaged_writers_preserve_original_bytes_but_cannot_execute_or_reenter(self):
        root = transition.ROOT
        record = json.loads((root/'state/work_units/QIKVRT_PR428_PACKAGED_WRITER_QUARANTINE_20261001_V1.json').read_bytes())
        self.assertEqual(len(record['records']), 57)
        for item in record['records']:
            raw = (root/item['historical_path']).read_bytes()
            self.assertEqual(len(raw), item['original_bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item['original_sha256'])
            self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(), item['original_git_blob'])
            self.assertEqual((root/item['active_path']).read_text(), transition.PACKAGED_WRITER_STUB)
            result = subprocess.run([sys.executable, str(root/item['active_path']), '--remote', 'https://invalid.example/repo'], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 78)
            self.assertIn(b'NO_BYPASS', result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(directory, {'payload/monthly_content/PAYLOAD_FILENAME_MAP_V36.json': json.dumps({'items': [{'new_name': 'writer.bin', 'old_name': 'writer.py'}]}),
                'payload/monthly_content/writer.bin': 'import subprocess\nsubprocess.run(["git", "push", "origin", "main"])\n'})
            self.assertEqual(transition.audit_repository_writers(fixture)['state'], 'BLOCK')
            (fixture/'payload/monthly_content/writer.bin').write_text(transition.PACKAGED_WRITER_STUB)
            self.assertEqual(transition.audit_repository_writers(fixture)['state'], 'PASS')
            (fixture/'incoming').mkdir()
            (fixture/'incoming/writer.py').write_text('import subprocess\nsubprocess.run(["git", "push", "origin", "main"])\n')
            (fixture/'active').mkdir()
            (fixture/'active/reenter').write_text('#!/bin/sh\npython3 incoming/writer.py\n')
            self.assertEqual(transition.audit_repository_writers(fixture)['state'], 'BLOCK')

    def test_literal_disabled_job_has_no_write_capability_and_cannot_be_reenabled(self):
        prefix = 'name: writer\non: workflow_dispatch\npermissions:\n  contents: read\njobs:\n'
        body = '  writer:\n    if: ${{ false }} # NO_BYPASS: unsupported provider writer disabled\n    permissions: {}\n    runs-on: ubuntu-latest\n    steps:\n      - run: git push origin main\n'
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory, {'.github/workflows/writer.yml': prefix+body})
            self.assertEqual(transition.audit_repository_writers(root)['state'], 'PASS')
            p = root/'.github/workflows/writer.yml'
            for changed in (body.replace('${{ false }}', '${{ inputs.enabled }}'),
                    body.replace('permissions: {}', 'permissions:\n      contents: write'),
                    body.replace('    permissions: {}', '    if: true\n    permissions: {}'),
                    body.replace('    permissions: {}', '    permissions: {}\n    permissions:\n      contents: write')):
                p.write_text(prefix+changed)
                self.assertEqual(transition.audit_repository_writers(root)['state'], 'BLOCK')

    def test_write_permission_or_checkout_credential_alone_blocks_admission(self):
        for source in [
            'name: x\non: push\npermissions:\n  contents: write\njobs:\n  read:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo read\n',
            'name: x\non: push\npermissions: read-all\njobs:\n  read:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@abcdef\n',
            'name: x\non: push\npermissions: {contents: write}\njobs:\n  read:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo read\n',
        ]:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                root = self.fixture(directory, {'.github/workflows/x.yml': source})
                self.assertEqual(transition.audit_repository_writers(root)['state'], 'BLOCK')

    def test_denial_guard_removal_and_motion_after_transport_are_detected(self):
        source = (transition.ROOT/'tools/qikvrt_vrtcore_h3_e1_recovery.py').read_text()
        self.assertTrue(transition._guarded_request(source, 'request'))
        self.assertFalse(transition._guarded_request(source.replace('method != "GET"', 'method == "GET"'), 'request'))
        self.assertFalse(transition._guarded_request(source.replace('        if method != "GET":',
            '        self._transport("POST", "/repos/x/y/releases")\n        if method != "GET":'), 'request'))

    def test_legacy_bearers_and_acceptance_flags_never_reenable_rest_after_restart(self):
        from tools import qikvrt_vrtcore_h3_e1_recovery as h3
        from tools import qikvrt_zenodo_publish as publication
        for restart in (False, True):
            transport = mock.Mock()
            client = h3.GitHubAPI('x'*30, transport=transport)
            with mock.patch.dict(os.environ, {'GITHUB_TOKEN': 'x'*30,
                    'QIKVRT_ENABLE_REAL_GITHUB_EFFECTS': 'YES', 'QIKVRT_EXTERNAL_EFFECTS': 'enabled'}):
                for method in ('POST', 'PATCH', 'PUT', 'DELETE'):
                    with self.subTest(restart=restart, method=method), self.assertRaises(transition.TransitionError):
                        client.request(method, '/repos/Goldkelch/qik-vrt/git/refs', payload={})
                    with mock.patch.object(publication.urllib.request, 'build_opener') as opener:
                        with self.assertRaises(transition.TransitionError):
                            publication._github_api_request(method, '/repos/Goldkelch/qik-vrt/git/refs', 'x'*30)
                        opener.assert_not_called()
            transport.assert_not_called()
            transport.return_value = (200, {})
            self.assertEqual(client.request('GET', '/repos/Goldkelch/qik-vrt/git/ref/heads/main'), (200, {}))

    def test_publication_execute_and_direct_helper_deny_before_transport(self):
        from tools import qikvrt_cicd_publish as publication
        for command, effect in [(['git','push','origin','main'], 'github_push'),
                (['gh','release','create','v1'], 'github_release')]:
            with mock.patch.object(publication, 'run_bounded') as runner:
                self.assertEqual(publication._run(command)['returncode'], 20)
                code, steps, detail = publication.execute_plan({'actions':[{'effect':effect,'command':command}]})
                self.assertEqual(code, 20)
                self.assertEqual(steps, [])
                self.assertIn('NO_BYPASS', detail)
                runner.assert_not_called()

    def test_https_github_dry_dispatch_still_cannot_reach_provider(self):
        from scripts import qikvrt_api_client as client
        import contextlib, sys
        with mock.patch.dict(os.environ, {'QIKVRT_API_TOKEN':'x'*30}), \
                mock.patch.object(sys, 'argv', ['client', '--owner','ingolf-lohmann', '--repo','qik-vrt',
                    '--base-url','https://api.github.com', '--dry-run','true', '--request-id','dry-dispatch']), \
                contextlib.redirect_stderr(io.StringIO()), mock.patch.object(client.urllib.request, 'build_opener') as opener:
            with self.assertRaises(SystemExit) as raised:
                client.main()
            self.assertEqual(raised.exception.code, 2)
            opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
