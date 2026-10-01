#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Provider contract tests; real Git CAS/refs and HTTP shim, not live GitHub."""
import base64
from concurrent.futures import ThreadPoolExecutor
import copy
from http.server import ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
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
            'gh api repos/x/y/git/refs -f ref=refs/heads/x\n',
            'github.rest.git.createRef({ref: "refs/heads/x"})\n',
            'curl https://api.github.com/repos/x/y/releases \\\n  --data @payload\n',
        ]
        for candidate in candidates:
            for path in ('tools/new_writer.sh', 'Makefile', 'tools/new_writer.cjs', 'package.json'):
                with self.subTest(candidate=candidate, path=path), tempfile.TemporaryDirectory() as directory:
                    root = self.fixture(directory, {path: candidate})
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
