#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Provider contract tests; real Git CAS/refs and HTTP shim, not live GitHub."""
import base64
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
            return 200, {'sha': sha, 'tree': {'sha': '0' * 40 if self.wrong_tree else tree}}
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
        env = {'GITHUB_TOKEN': 'github-test-token-abcdefghijklmnopqrstuvwxyz',
               'QIKVRT_GITHUB_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z'}
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
            for raw, url in ((env['GITHUB_TOKEN'].encode(), None), (b'{}', 'https://other.invalid/'),
                             (b'{"duplicate":1,"duplicate":2}', None), (b'[]', None),
                             (b'x' * (shim.MAX_RESPONSE_BYTES + 1), None)):
                opener.return_value.open.return_value = response(raw, url=url)
                with self.assertRaises(transition.TransitionError):
                    adapter._request('GET', 'git/refs')
            with mock.patch.dict(os.environ, {'QIKVRT_GITHUB_TOKEN_EXPIRES_UTC': '2000-01-01T00:00:00Z'}):
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
        env = {'GITHUB_TOKEN': 'github-test-token-abcdefghijklmnopqrstuvwxyz',
               'QIKVRT_GITHUB_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z'}
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



class ProjectGitHubFixture:
    """Actual Git receive/upload-pack and durable repositories behind HTTP fixtures."""
    def __init__(self, node, root):
        from tests.test_qikvrt_digital_twin_rest import TwinGitProviderFixture
        self.root = root
        subject = {'repository': shim.PROVIDER_REPOSITORY, 'pr': 437,
                   'head': recovery.git_command(node / 'repository.git', 'rev-parse', 'HEAD')}
        self.authority = TwinGitProviderFixture(node, root / 'fixture-goldkelch.git', subject)
        self.source = TwinGitProviderFixture(node, root / 'fixture-source.git', subject)
        self.target = root / 'fixture-project.git'
        self.metadata = None
        self.calls = []
        self.mutations = 0
        self.after_create = None
        self.after_seed = None
        self.atomic = True
        self.org_create_status = 201
        self.root_collision = False

    def open(self, request, timeout):
        self.calls.append((request.method, request.full_url))
        method, data = request.method, request.data
        if request.full_url.startswith('https://api.github.com/'):
            path = request.full_url.removeprefix('https://api.github.com/')
            payload = json.loads(data) if data is not None else None
            if method == 'POST':
                self.mutations += 1
            if path == 'repos/Goldkelch/qik-vrt':
                status, value = 200, {'full_name': recovery.ROOT_REPOSITORY, 'permissions': {'push': True}}
            elif path == 'repos/Goldkelch/project-fixture':
                status, value = (200, copy.deepcopy(self.metadata)) if self.metadata else (404, {})
            elif path == 'orgs/Goldkelch/repos':
                if self.metadata or self.org_create_status != 201:
                    status, value = 422 if self.metadata else self.org_create_status, {}
                else:
                    recovery.git_command(self.root, 'init', '--bare', '--initial-branch=main', str(self.target))
                    self.metadata = {'id': 71, 'full_name': 'Goldkelch/project-fixture', 'private': payload['private'],
                                     'description': payload['description'], 'default_branch': 'main',
                                     'owner': {'login': 'Goldkelch', 'type': 'Organization'}}
                    if self.after_create:
                        self.after_create()
                    status, value = 201, copy.deepcopy(self.metadata)
            elif path.startswith('repos/Goldkelch/qik-vrt/'):
                suffix = path.removeprefix('repos/Goldkelch/qik-vrt/')
                if self.root_collision and suffix.startswith('git/ref/'):
                    status, value = 200, {}
                else:
                    status, value = self.authority.request(method, suffix, payload)
            elif path.startswith('repos/' + shim.PROVIDER_REPOSITORY + '/'):
                status, value = self.source.request(method, path.removeprefix('repos/' + shim.PROVIDER_REPOSITORY + '/'), payload)
            else:
                raise AssertionError(path)
            raw = json.dumps(value).encode()
        else:
            prefix = 'https://github.com/Goldkelch/project-fixture.git/'
            assert request.full_url.startswith(prefix)
            path = request.full_url.removeprefix(prefix)
            service = path.split('service=')[-1] if method == 'GET' else path
            command = ['git', '-C', str(self.target), service.removeprefix('git-'), '--stateless-rpc']
            if method == 'GET':
                command.append('--advertise-refs')
            else:
                if service == 'git-receive-pack':
                    self.mutations += 1
            command.append('.')
            result = subprocess.run(command, input=data, capture_output=True, timeout=10)
            assert result.returncode == 0, result.stderr.decode()
            raw = result.stdout
            if method == 'GET':
                raw = shim.GitHubAuthorityProvider._packet(('# service=' + service + '\n').encode()) + b'0000' + raw
                if not self.atomic:
                    # Reframe the changed capability packet, retaining valid protocol.
                    header, rest = shim.GitHubAuthorityProvider._packets(raw)
                    lines, _ = shim.GitHubAuthorityProvider._packets(rest)
                    lines[0] = lines[0].replace(b' atomic', b'')
                    raw = b''.join(shim.GitHubAuthorityProvider._packet(p) for p in header) + b'0000' + b''.join(shim.GitHubAuthorityProvider._packet(p) for p in lines) + b'0000'
            elif service == 'git-receive-pack' and self.after_seed:
                self.after_seed()
            status = 200
        response = io.BytesIO(raw)
        response.status = status
        response.geturl = lambda: request.full_url
        return response


class ProjectManifestationTests(unittest.TestCase):
    setUp_authority = transition_tests.AuthorityTransitionTests.setUp
    take = transition_tests.AuthorityTransitionTests.take
    activate = transition_tests.AuthorityTransitionTests.activate

    def setUp(self):
        self.setUp_authority()
        self.permit = self.activate()
        # The retained mirror checkpoint precedes the fixture's root mutation.
        self.package = self.root / 'checkpoint'
        self.project = recovery.plan_effect(self.package, self.manifest, 'Goldkelch/project-fixture')
        self.plan_sha = recovery.digest(canonical_json_bytes(self.project))
        self.remote = ProjectGitHubFixture(self.node, self.root)
        self.environment = mock.patch.dict(os.environ, {'GITHUB_TOKEN': 'github-project-fixture-abcdefghijklmnopqrstuvwxyz',
                'QIKVRT_GITHUB_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.opener = mock.patch.object(shim.urllib.request, 'build_opener')
        self.opener.start().return_value.open.side_effect = self.remote.open
        self.addCleanup(self.opener.stop)
        self.adapter = shim.GitHubAuthorityProvider(self.cp, shim.PROVIDER_REPOSITORY, project_fixture=True)

    def grant(self, *, operations=None, expires=None):
        import time
        return self.cp.authorize_project(ADMIN, NEW_TOKEN, self.permit, self.project, self.plan_sha,
                recovery.digest(self.adapter._credential().encode()), expires or time.time_ns() + 600_000_000_000,
                operations if operations is not None else transition.PROJECT_CAPABILITY_OPERATIONS)

    def operation(self, *, readback=False, key='fixture-project'):
        return {'operation': 'readback_project' if readback else 'manifest_project', 'effect_id': key,
                'project_plan': self.project, 'project_plan_sha256': self.plan_sha, 'checkpoint': str(self.package)}

    def execute(self, *, readback=False, key='fixture-project', permit=None):
        return self.adapter.execute(NEW_TOKEN, permit or self.permit, self.operation(readback=readback, key=key))

    def journal(self):
        with self.cp.transaction() as db:
            return db.execute("SELECT status, document, receipt FROM provider_effects WHERE id='project:fixture-project'").fetchone()

    def test_native_atomic_history_seed_and_double_fresh_root_readback_are_fixture_only(self):
        self.grant()
        result = self.execute()
        self.assertEqual(self.journal()[0], 'VERIFIED')
        self.assertEqual(self.remote.mutations, 6)
        self.assertTrue(result['fresh_fixture_readback'])
        self.assertTrue(result['history_and_checkpoint_bytes_verified'])
        for field in ('remote_repository_created', 'root_registration_verified', 'fresh_provider_readback', 'live_runtime_verified', 'full_node_admitted', 'effect_ack_done'):
            self.assertIs(result[field], False)
        self.assertEqual(result['state'], 'HOLD_PRODUCTIVE_PROJECT_ACCEPTANCE')
        for ref, oid in self.project['source_git']['refs'].items():
            self.assertEqual(recovery.git_command(self.remote.target, 'rev-parse', ref), oid)
        self.assertEqual(recovery.git_command(self.remote.target, 'rev-list', '--parents', '-n', '1', result['seed_commit']).split(), [result['seed_commit'], self.project['source_git']['head']])
        doc = transition.decode(self.journal()[1])
        owner = doc['seed_descriptor']['scheduler']['schedules'][0]['owner_node_id']
        self.assertEqual(owner, self.project['new_node_id'])
        root_gets = [url for method, url in self.remote.calls if method == 'GET' and '/git/blobs/' in url]
        self.assertGreaterEqual(len(root_gets), 3)

    def test_missing_organization_capability_is_exact_hold_with_no_provider_call(self):
        result = self.execute()
        self.assertEqual(result['state'], 'HOLD')
        self.assertEqual(result['reason'], 'GOLDKELCH_CREATE_CAPABILITY_REQUIRED')
        self.assertEqual(self.remote.calls, [])
        self.assertFalse(result['remote_repository_created'])
        self.assertFalse(result['effect_ack_done'])
        with self.assertRaises(transition.ProjectCapabilityRequired):
            self.grant(operations=transition.PROJECT_CAPABILITY_OPERATIONS[:1])

    def test_owner_capability_cannot_be_replaced_by_writer_or_source_token(self):
        import time
        with self.assertRaises(transition.TransitionError):
            self.cp.authorize_project(NEW_TOKEN, NEW_TOKEN, self.permit, self.project, self.plan_sha,
                recovery.digest(self.adapter._credential().encode()), time.time_ns() + 600_000_000_000,
                transition.PROJECT_CAPABILITY_OPERATIONS)
        self.assertEqual(self.remote.calls, [])

    def test_existing_name_or_root_slot_is_never_adopted_or_overwritten(self):
        self.grant()
        self.remote.metadata = {'id': 71}
        result = self.execute()
        self.assertIn('COLLISION', result['reason'])
        self.assertEqual(self.remote.mutations, 0)
        self.assertEqual(self.journal()[0], 'REJECTED')

    def test_existing_root_registration_blocks_repository_creation(self):
        self.grant()
        self.remote.root_collision = True
        result = self.execute()
        self.assertIn('COLLISION', result['reason'])
        self.assertEqual(self.remote.mutations, 0)

    def test_stale_permit_and_credential_drift_are_rejected_before_dispatch(self):
        self.grant()
        stale = {**self.permit, 'fence': 'f' * 64}
        with self.assertRaises(transition.TransitionError):
            self.execute(permit=stale)
        with mock.patch.dict(os.environ, {'GITHUB_TOKEN': 'different-fixture-credential-abcdefghijklmnopqrstuvwxyz'}):
            result = self.execute()
        self.assertEqual(result['state'], 'HOLD')
        self.assertEqual(self.remote.calls, [])

    def test_expired_capability_or_clock_rollback_cannot_dispatch(self):
        self.grant()
        with self.cp.transaction() as db:
            raw = db.execute('SELECT document FROM provider_project_grants').fetchone()[0]
            document = transition.decode(raw)
        for now in (document['issued_ns'] - 1, document['expires_ns']):
            with mock.patch.object(transition.time, 'time_ns', return_value=now):
                self.assertEqual(self.execute()['state'], 'HOLD')
        self.assertEqual(self.remote.calls, [])

    def test_replay_is_read_only_and_does_not_mint_a_second_effect(self):
        self.grant()
        first = self.execute()
        count = self.remote.mutations
        self.assertEqual(self.execute()['reason'], 'PROJECT_REPLAY_READBACK_ONLY')
        with self.assertRaises(transition.TransitionError):
            self.execute(key='another-effect')
        self.adapter = shim.GitHubAuthorityProvider(transition.AuthorityControlPlane(self.cp.path), shim.PROVIDER_REPOSITORY, project_fixture=True)
        fresh = self.execute(readback=True)
        self.assertEqual({k:v for k,v in fresh.items() if k != 'observed_utc'}, {k:v for k,v in first.items() if k != 'observed_utc'})
        self.assertEqual(self.remote.mutations, count)

    def test_partially_created_repository_holds_and_blocks_takeover_without_seed_retry(self):
        self.grant()
        self.remote.after_create = lambda: (_ for _ in ()).throw(SystemExit('fixture process loss'))
        with self.assertRaises(SystemExit):
            self.execute()
        self.assertTrue(self.remote.target.exists())
        self.assertEqual(self.journal()[0], 'PENDING')
        count = self.remote.mutations
        self.assertEqual(self.execute(readback=True)['reason'], 'PARTIAL_PROJECT_INTENT_READBACK_ONLY')
        self.assertEqual(self.remote.mutations, count)
        with self.assertRaisesRegex(transition.TransitionError, 'unresolved provider'):
            self.take(self.competitor, COMPETITOR_TOKEN)

    def test_lost_seed_ack_is_recovered_only_by_actual_fresh_pack_and_register_reads(self):
        self.grant()
        self.remote.after_seed = lambda: (_ for _ in ()).throw(SystemExit('fixture ack loss'))
        with self.assertRaises(SystemExit):
            self.execute()
        count = self.remote.mutations
        self.assertEqual(self.journal()[0], 'PENDING')
        self.assertTrue(self.execute(readback=True)['fresh_fixture_readback'])
        self.assertEqual(self.journal()[0], 'VERIFIED')
        self.assertEqual(self.remote.mutations, count)

    def test_false_parent_checkpoint_or_lineage_is_rejected_even_with_new_plan_digest(self):
        original = copy.deepcopy(self.project)
        cases = [('parent_node_id', 'f' * 64), ('source_checkpoint_sha256', '0' * 64),
                 ('lineage', [recovery.ROOT_REPOSITORY, 'Goldkelch/foreign-parent', 'Goldkelch/project-fixture']),
                 ('source_git', {**original['source_git'], 'tree': '0' * 40})]
        for field, value in cases:
            with self.subTest(field=field):
                project = {**original, field: value}
                with self.assertRaises(transition.TransitionError):
                    recovery.verify_project_plan(self.package, self.manifest, project, recovery.digest(canonical_json_bytes(project)))
        self.assertEqual(self.remote.calls, [])

    def test_historical_offline_checkpoint_cannot_bypass_current_cqf_project_admission(self):
        manifest = recovery.verify_checkpoint(self.package, self.manifest)
        policy_asset = next(a for a in manifest['plan']['assets']
                            if a['path'] == recovery.INDEPENDENCE_POLICY_PATH)
        policy_path = self.package / 'payload' / policy_asset['path']
        policy = json.loads(policy_path.read_bytes())
        del policy['post_binding_repository_mirroring']
        raw = canonical_json_bytes(policy)
        policy_path.write_bytes(raw)
        policy_asset.update(bytes=len(raw), sha256=recovery.digest(raw))
        manifest['closure_plan_sha256'] = recovery.digest(canonical_json_bytes(manifest['plan']))
        raw = canonical_json_bytes(manifest)
        (self.package / 'manifest.json').write_bytes(raw)
        historical_sha = recovery.digest(raw)
        recovery.verify_checkpoint(self.package, historical_sha)
        project = recovery.plan_effect(self.package, historical_sha, self.project['target_repository'])
        with self.assertRaisesRegex(recovery.RecoveryError, 'CQF'):
            recovery.verify_project_plan(self.package, historical_sha, project,
                                         recovery.digest(canonical_json_bytes(project)))
        self.assertEqual(self.remote.calls, [])

    def test_semantically_wrong_owner_admitted_lineage_is_still_rejected(self):
        self.project['lineage'] = [recovery.ROOT_REPOSITORY, 'Goldkelch/foreign-parent', 'Goldkelch/project-fixture']
        self.plan_sha = recovery.digest(canonical_json_bytes(self.project))
        self.grant()
        with self.assertRaises(transition.TransitionError):
            self.execute()
        self.assertEqual(self.remote.calls, [])

    def test_root_byte_readback_drift_cannot_be_promoted_to_verified(self):
        self.grant()
        self.execute()
        self.remote.authority.wrong_bytes = True
        count = self.remote.mutations
        with self.assertRaisesRegex(transition.TransitionError, 'ROOT_REGISTER_BYTE'):
            self.execute(readback=True)
        self.assertEqual(self.remote.mutations, count)

    def test_repository_or_seed_ref_readback_drift_cannot_reuse_old_receipt(self):
        self.grant()
        result = self.execute()
        self.remote.metadata['private'] = False
        with self.assertRaisesRegex(transition.TransitionError, 'REPOSITORY_READBACK'):
            self.execute(readback=True)
        self.remote.metadata['private'] = True
        recovery.git_command(self.remote.target, 'update-ref', result['seed_ref'], self.project['source_git']['head'])
        with self.assertRaisesRegex(transition.TransitionError, 'SEED_REF_READBACK'):
            self.execute(readback=True)

    def test_missing_atomic_capability_never_falls_back_to_separate_ref_writes(self):
        self.grant()
        self.remote.atomic = False
        with self.assertRaisesRegex(transition.TransitionError, 'ATOMIC_CREATE'):
            self.execute()
        self.assertEqual(self.remote.mutations, 5)
        self.assertEqual(self.journal()[0], 'PENDING')
        self.assertEqual(recovery.git_command(self.remote.target, 'for-each-ref'), '')

    def test_definitive_organization_rejection_is_not_adopted_on_replay(self):
        self.grant()
        self.remote.org_create_status = 403
        self.assertIn('NATIVE_CREATE_REJECTED', self.execute()['reason'])
        self.assertEqual(self.journal()[0], 'REJECTED')
        count = self.remote.mutations
        self.assertEqual(self.execute(readback=True)['reason'], 'PROJECT_INTENT_NOT_DISPATCHED_OR_REJECTED')
        self.assertEqual(self.remote.mutations, count)

    def test_direct_project_and_raw_transports_cannot_bypass_existing_admission(self):
        for method, path in [('POST', 'orgs/Goldkelch/repos'), ('PATCH', 'repos/Goldkelch/project-fixture'), ('POST', 'orgs/other/repos')]:
            with self.assertRaises(transition.TransitionError):
                self.adapter._request(method, '', {}, project_path=path)
            with self.assertRaises(transition.TransitionError):
                self.adapter._raw_provider_request('https://api.github.com/' + path, method, b'{}', 'application/json', 'application/json', project_path=path)
        self.assertEqual(self.remote.calls, [])

    def test_existing_cli_missing_capability_returns_hold_exit_20_without_network(self):
        token, permit, plan = self.root / 'writer-token', self.root / 'permit.json', self.root / 'project.json'
        token.write_text(NEW_TOKEN)
        token.chmod(0o600)
        permit.write_bytes(canonical_json_bytes(self.permit))
        plan.write_bytes(canonical_json_bytes(self.project))
        result = subprocess.run([sys.executable, '-B', str(recovery.ROOT / 'tools/qikvrt_mesh_recovery.py'), 'execute-project',
            '--checkpoint', str(self.package), '--expect-manifest-sha256', self.manifest,
            '--project-plan', str(plan), '--expect-project-plan-sha256', self.plan_sha,
            '--control-plane', str(self.cp.path), '--token-file', str(token), '--permit', str(permit),
            '--effect-id', 'cli-fixture'], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 20, result.stderr.decode())
        body = json.loads(result.stdout)
        self.assertEqual(body['reason'], 'GOLDKELCH_CREATE_CAPABILITY_REQUIRED')
        self.assertEqual(body['state'], 'HOLD')
        self.assertFalse(body['remote_repository_created'])
        self.assertNotIn(NEW_TOKEN.encode(), result.stdout)
        self.assertEqual(self.remote.calls, [])

    def test_existing_authenticated_http_route_reports_hold_and_rejects_old_writer(self):
        from http.client import HTTPConnection
        api_token = 'b64url:' + base64.urlsafe_b64encode(b'p' * 32).rstrip(b'=').decode()
        environment = {'QIKVRT_API_TOKEN': api_token, 'QIKVRT_API_TOKEN_EXPIRES_UTC': '2099-01-01T00:00:00Z',
            'QIKVRT_API_PRINCIPAL': 'project-fixture', 'QIKVRT_ALLOWED_REPOSITORY': shim.PROVIDER_REPOSITORY,
            'QIKVRT_AUTHORITY_CONTROL_PLANE': str(self.cp.path), 'QIKVRT_RATE_LIMIT_PER_MINUTE': '10000'}
        with mock.patch.dict(os.environ, environment):
            server = ThreadingHTTPServer(('127.0.0.1', 0), shim.QikvrtGitHubApiShim)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                for writer, expected in ((NEW_TOKEN, 200), (OLD_TOKEN, 409)):
                    connection = HTTPConnection('127.0.0.1', server.server_port, timeout=10)
                    connection.request('POST', f'/repos/{shim.PROVIDER_REPOSITORY}/qikvrt/authority/effects',
                        canonical_json_bytes({'writer_capability': writer, 'permit': self.permit, 'operation': self.operation()}),
                        {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_token})
                    response = connection.getresponse()
                    raw = response.read()
                    self.assertEqual(response.status, expected)
                    self.assertNotIn(writer.encode(), raw)
                    if expected == 200:
                        self.assertEqual(json.loads(raw)['status'], 'HOLD')
                        self.assertEqual(json.loads(raw)['provider_result']['reason'], 'GOLDKELCH_CREATE_CAPABILITY_REQUIRED')
                    connection.close()
            finally:
                server.shutdown()
                thread.join(5)
                server.server_close()
        self.assertEqual(self.remote.calls, [])

    def test_durable_receipt_corruption_cannot_use_provider_success_as_replacement(self):
        self.grant()
        self.execute()
        with self.cp.transaction() as db:
            db.execute("UPDATE provider_effects SET receipt=? WHERE id='project:fixture-project'", (b'{}\n',))
        count = self.remote.mutations
        with self.assertRaisesRegex(transition.TransitionError, 'DURABLE_RECEIPT'):
            self.execute(readback=True)
        self.assertEqual(self.remote.mutations, count)

    def test_project_protocol_unknown_fields_and_direct_target_provider_are_denied(self):
        self.grant()
        for field, value in (('owner_token', 'untrusted'), ('force', True), ('target_repository', 'other/project')):
            with self.subTest(field=field), self.assertRaises(transition.TransitionError):
                self.adapter.execute(NEW_TOKEN, self.permit, {**self.operation(), field: value})
        with self.assertRaises(transition.TransitionError):
            shim.GitHubAuthorityProvider(self.cp, self.project['target_repository'])
        self.assertEqual(self.remote.calls, [])

    def test_durable_intent_cannot_be_retargeted_even_with_canonical_json(self):
        self.grant()
        self.execute()
        with self.cp.transaction() as db:
            doc = transition.decode(db.execute("SELECT document FROM provider_effects WHERE id='project:fixture-project'").fetchone()[0])
            doc['steps'][4]['payload']['name'] = 'unadmitted-target'
            db.execute("UPDATE provider_effects SET document=? WHERE id='project:fixture-project'", (canonical_json_bytes(doc),))
        count = self.remote.mutations
        with self.assertRaisesRegex(transition.TransitionError, 'DURABLE_INTENT'):
            self.execute(readback=True)
        self.assertEqual(self.remote.mutations, count)

    def test_bound_fixture_roundtrip_persists_no_credentials(self):
        self.grant()
        self.execute()
        raw = self.cp.path.read_bytes()
        for token in (ADMIN, OLD_TOKEN, NEW_TOKEN, self.adapter._credential()):
            self.assertNotIn(token.encode(), raw)

    def test_mock_http_fixture_cannot_claim_live_creation_without_explicit_fixture_flag(self):
        self.grant()
        self.adapter = shim.GitHubAuthorityProvider(self.cp, shim.PROVIDER_REPOSITORY)
        result = self.execute()
        self.assertEqual(result['evidence_class'], 'LOCAL_PROVIDER_FIXTURE_READBACK')
        self.assertFalse(result['remote_repository_created'])
        self.assertFalse(result['fresh_provider_readback'])
        self.assertFalse(result['effect_ack_done'])

    def test_readback_timestamp_is_freshly_recorded_and_read_from_same_durable_sink(self):
        self.grant()
        first = self.execute()
        fresh = self.execute(readback=True)
        self.assertGreater(fresh['observed_utc'], first['observed_utc'])
        receipt = transition.decode(self.journal()[2])
        self.assertEqual(receipt['observed_utc'], fresh['observed_utc'])

    def test_grant_cli_uses_same_issuer_and_exact_scope_before_any_provider_call(self):
        import time
        paths = {}
        for name, value in {'admin': ADMIN.encode(), 'token': NEW_TOKEN.encode(),
                            'permit': canonical_json_bytes(self.permit), 'project': canonical_json_bytes(self.project),
                            'scope': canonical_json_bytes({'schema': 'qikvrt_owner_provisioned_project_capability_scope_v1',
                                'operations': transition.PROJECT_CAPABILITY_OPERATIONS, 'expires_ns': time.time_ns() + 600_000_000_000})}.items():
            paths[name] = self.root / (name + '.json')
            paths[name].write_bytes(value)
            paths[name].chmod(0o600)
        arguments = ['grant-project', '--control-plane', str(self.cp.path), '--token-file', str(paths['token']),
                     '--admin-token-file', str(paths['admin']), '--permit', str(paths['permit']), '--checkpoint', str(self.package),
                     '--expect-manifest-sha256', self.manifest, '--project-plan', str(paths['project']),
                     '--expect-project-plan-sha256', self.plan_sha, '--payload', str(paths['scope'])]
        result = subprocess.run([sys.executable, '-B', str(recovery.ROOT / 'tools/qikvrt_authority_transition.py'), *arguments],
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        grant = json.loads(result.stdout)
        self.assertEqual(grant['project_plan_sha256'], self.plan_sha)
        self.assertFalse(grant['provider_permissions_verified'])
        self.assertFalse(grant['effect_ack_done'])
        self.assertEqual(self.remote.calls, [])


if __name__ == '__main__':
    unittest.main()
