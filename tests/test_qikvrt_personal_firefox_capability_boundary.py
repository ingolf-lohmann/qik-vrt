from __future__ import annotations

import json
import unittest
import tempfile
import hashlib
import io
import os
import urllib.error
from contextlib import chdir
from email.message import Message
from unittest.mock import patch
from pathlib import Path
from pathlib import PureWindowsPath

from tools.qikvrt_firefox_windows_witness import (
    target_matches, provision_driver, verify_effect_readback,
    public_http_readback, evaluate_public_url_readback, NoPublicRedirect,
    CANONICAL_PRODUCT_URL, PUBLIC_BODY_LIMIT,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md"
POLICY = ROOT / "policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json"


class AuthorityPagesObserverTests(unittest.TestCase):
    workflow = ROOT / '.github/workflows/qikvrt_mesh_authority_edge.yml'

    def inline_python(self, step):
        block = self.workflow.read_text().split('      - name: ' + step, 1)[1]
        block = block.split("          python3 - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
        return '\n'.join(line[10:] for line in block.splitlines())

    def run_observer(self, *, token='', app_outcome='skipped', authority_head=None):
        candidate_head, candidate_tree = 'a' * 40, 'b' * 40
        authority_head = authority_head if authority_head is not None else 'c' * 40
        requests = []

        def open_request(request, timeout):
            requests.append(request)
            url = request.full_url
            status, value = 404, {'message': 'Not Found'}
            if url.endswith('/git/commits/' + candidate_head):
                status, value = 200, {'tree': {'sha': candidate_tree}}
            elif url.startswith('https://api.github.com/repos/Goldkelch/qik-vrt/') and token:
                status, value = 200, {'source': {'branch': 'main', 'path': '/docs'}}
                if url.endswith('/branches/main'):
                    value = {'commit': {'sha': authority_head}}
                elif '/git/commits/' in url:
                    value = {'tree': {'sha': 'd' * 40}}
                elif '/git/trees/' in url:
                    value = {'tree': [], 'truncated': False}
            return urllib.error.HTTPError(url, status, 'fixture', Message(),
                                          io.BytesIO(json.dumps(value).encode()))

        env = {'CANDIDATE_HEAD': candidate_head, 'OBSERVER_TOKEN': 'fixture-observer',
               'OBSERVER_RUN_ID': 'fixture-run', 'OBSERVER_RUN_ATTEMPT': '1',
               'APP_TOKEN': token, 'APP_TOKEN_OUTCOME': app_outcome}
        with tempfile.TemporaryDirectory() as temp, chdir(temp), patch.dict(os.environ, env, clear=True), \
                patch('urllib.request.build_opener') as build:
            Path('PAGES_APP_BINDING.json').write_text(json.dumps({
                'app_id_present': bool(token) or app_outcome == 'failure',
                'private_key_present': bool(token) or app_outcome == 'failure'}))
            build.return_value.open.side_effect = open_request
            exec(compile(self.inline_python('Read fixed Authority Pages contract without publishing'),
                         str(self.workflow), 'exec'), {})
            receipt = json.loads(Path('PAGES_REST_READBACK.json').read_text())
        return receipt, requests

    def test_empty_bindings_and_failed_mint_remain_hold_without_authority_requests(self):
        for outcome in ('skipped', 'failure'):
            with self.subTest(outcome=outcome):
                receipt, requests = self.run_observer(app_outcome=outcome)
                self.assertEqual(receipt['state'], 'HOLD_AUTHORITY_PAGES_READ_UNAVAILABLE')
                self.assertEqual(receipt['authority_reads'], {})
                self.assertIsNone(receipt['credential_route'])
                self.assertFalse(receipt['credential_present'])
                self.assertEqual(receipt['credential_route_probes']['APP_TOKEN']['mint_outcome'], outcome)
                self.assertFalse(any('/repos/Goldkelch/' in req.full_url for req in requests))

    def test_app_route_reads_exact_authority_source_without_credential_transfer(self):
        receipt, requests = self.run_observer(token='fixture-app-secret', app_outcome='success')
        self.assertEqual(receipt['candidate_head'], 'a' * 40)
        self.assertEqual(receipt['candidate_tree'], 'b' * 40)
        self.assertEqual(receipt['credential_route'], 'APP_TOKEN')
        self.assertEqual(receipt['state'], 'OBSERVED_AUTHORITY_PAGES')
        self.assertIn('source_commit', receipt['authority_reads'])
        self.assertIn('source_inventory', receipt['authority_reads'])
        for req in requests:
            authorization = req.get_header('Authorization')
            if req.full_url.startswith('https://goldkelch.github.io/'):
                self.assertIsNone(authorization)
            elif '/repos/Goldkelch/' in req.full_url:
                self.assertEqual(authorization, 'Bearer fixture-app-secret')
                if '/contents/' in req.full_url:
                    self.assertTrue(req.full_url.endswith('?ref=' + 'c' * 40))
        self.assertNotIn('fixture-app-secret', json.dumps(receipt))
        self.assertNotIn('fixture-observer', json.dumps(receipt))
        for field in ('publication_mutated', 'deployed_candidate_head_tree_verified',
                      'persistent_signed_installation_verified', 'authenticated_runtime_readback',
                      'personal_release_effect_ack_done'):
            self.assertFalse(receipt[field])

    def test_substituted_authority_head_is_not_used_as_source_path(self):
        receipt, _ = self.run_observer(token='fixture-app-secret', app_outcome='success',
                                      authority_head='../substitution')
        self.assertNotIn('source_commit', receipt['authority_reads'])
        self.assertNotIn('source_inventory', receipt['authority_reads'])

    def test_app_requires_both_existing_bindings_and_requests_only_read_permissions(self):
        for values, available in (({}, False), ({'RULESET_APP_ID': 'fixture-id'}, False),
                                  ({'RULESET_APP_PRIVATE_KEY': 'fixture-key'}, False),
                                  ({'RULESET_APP_ID': 'fixture-id',
                                    'RULESET_APP_PRIVATE_KEY': 'fixture-key'}, True)):
            with self.subTest(values=list(values)), tempfile.TemporaryDirectory() as temp, chdir(temp), \
                    patch.dict(os.environ, values | {'GITHUB_OUTPUT': str(Path(temp) / 'output')}, clear=True):
                exec(compile(self.inline_python('Observe existing Authority App binding without retaining secrets'),
                             str(self.workflow), 'exec'), {})
                output = Path('output').read_text()
                binding = json.loads(Path('PAGES_APP_BINDING.json').read_text())
                self.assertEqual(output, 'available=' + str(available).lower() + '\n')
                self.assertEqual(binding['target_repository'], 'Goldkelch/qik-vrt')
                self.assertEqual(binding['requested_permissions'], {'pages': 'read', 'contents': 'read'})
                self.assertNotIn('fixture-key', json.dumps(binding))
        app_step = self.workflow.read_text().split('      - name: Mint read-only token', 1)[1]
        app_step = app_step.split('      - name:', 1)[0]
        self.assertIn('owner: Goldkelch', app_step)
        self.assertIn('repositories: qik-vrt', app_step)
        self.assertIn('permission-pages: read', app_step)
        self.assertIn('permission-contents: read', app_step)
        self.assertNotIn('permission-administration:', app_step)
        self.assertNotIn(': write', app_step)


class PersonalFirefoxCapabilityBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = SPEC.read_text(encoding="utf-8")
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_normative_boundary_matches_machine_contract(self) -> None:
        self.assertEqual(
            self.policy["schema"],
            "qikvrt_personal_firefox_capability_boundary_v1",
        )
        self.assertEqual(
            self.policy["source_subject"]["standard_repository"],
            "Goldkelch/qik-vrt",
        )
        self.assertEqual(
            self.policy["source_subject"]["personal_repository"],
            "ingolf-lohmann/qik-vrt",
        )
        self.assertFalse(
            self.policy["source_subject"]["predecessor_evidence_transfer"]
        )
        expected = {
            "STANDARD_TO_PERSONAL": "ALLOW_WITH_FRESH_BINDING",
            "PERSONAL_TO_STANDARD": "DENY_BY_DEFAULT",
            "PERSONAL_CAPABILITY_LEAK_TO_STANDARD": "DENY",
            "PERSONAL_STATE_LEAK_TO_STANDARD": "DENY",
            "PERSONAL_CREDENTIAL_LEAK_TO_REPOSITORY": "DENY",
            "PERSONAL_EVIDENCE_TRANSFER_TO_STANDARD": "DENY",
            "CHATGPT_RUNTIME_INTEGRATION": "AUTHENTICATED_EXTERNAL_SERVICE",
            "CHATGPT_PROPRIETARY_RUNTIME_REDISTRIBUTION": "DENY",
            "PREDECESSOR_EVIDENCE_TRANSFER": "FALSE",
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertIn(f"{key}", self.spec)
                self.assertIn(f"= {value}", self.spec)

    def test_standard_package_has_no_ingolf_specific_payload(self) -> None:
        package = self.policy["standard_firefox_package"]
        root = ROOT / package["root"]
        files = package["files"]
        self.assertEqual(len(files), len(set(files)))
        self.assertNotIn(
            "spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md",
            files,
        )
        for relative in files:
            path = root / relative
            self.assertTrue(path.is_file(), relative)
            data = path.read_text(encoding="utf-8")
            for marker in package["forbidden_personal_markers"]:
                with self.subTest(path=relative, marker=marker):
                    self.assertNotIn(marker, data)

    def test_standard_manifest_remains_standard_surface(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "browser/firefox/qikvrt-terminal/manifest.json"
            ).read_text(encoding="utf-8")
        )
        serialized = json.dumps(manifest, sort_keys=True)
        self.assertIn("https://github.com/Goldkelch/qik-vrt/*", serialized)
        self.assertNotIn("ingolf-lohmann", serialized)
        self.assertNotIn("chatgpt.com", serialized)
        self.assertNotIn("openai.com", serialized)

    def test_personal_release_stays_hold_until_fresh_runtime_evidence(self) -> None:
        candidate = self.policy["personal_release_acceptance"]["current_candidate"]
        self.assertTrue(candidate["boundary_contract_materialized"])
        self.assertFalse(candidate["personal_capability_manifest_materialized"])
        self.assertFalse(candidate["authenticated_runtime_readback"])
        self.assertFalse(candidate["personal_release_effect_ack_done"])
        self.assertEqual(candidate["state"], "HOLD")
        self.assertIn(
            "A successor mutation invalidates predecessor release evidence.",
            self.spec,
        )

    def test_runtime_integration_does_not_redistribute_service_internals(self) -> None:
        self.assertIn(
            "authenticated runtime integration",
            self.spec,
        )
        for marker in (
            "model weights",
            "hidden system configuration",
            "credentials",
            "non-redistributable service internals",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.spec)
        self.assertIn(
            "Runtime secrets MUST come from an OS/browser secret store",
            self.spec,
        )

    def test_windows_target_rejects_server_stale_build_and_expired_support(self) -> None:
        target = self.policy['windows_acceptance']['product_target']
        observed = {'product_type': 1, 'build': 26200,
                    'display_version': '25H2', 'edition': 'Enterprise',
                    'architecture': 'ARM64'}
        self.assertTrue(target_matches(observed, target, '2026-10-01'))
        for change in ({'product_type': 3}, {'product_type': 2},
                       {'build': 26100}, {'display_version': '24H2'},
                       {'edition': 'ServerStandard'}, {'architecture': 'x86'}):
            with self.subTest(change=change):
                self.assertFalse(target_matches(observed | change, target, '2026-10-01'))
        self.assertFalse(target_matches(observed, target, target['support_until']))
        self.assertFalse(target_matches({}, target, '2026-10-01'))

    def test_cache_authority_uses_repository_paths_on_windows(self) -> None:
        from tools import qikvrt_tool_cache as cache
        root = PureWindowsPath('C:/qik-vrt')
        with patch.object(cache, 'ROOT', root), \
                patch.object(cache, 'LOCK_PATH', root / 'runtime/toolchains/TOOLCHAIN.lock.tsv'), \
                patch.object(cache, 'COVERAGE_PATH', root / 'runtime/toolchains/CACHE_COVERAGE.json'):
            self.assertEqual(cache.read_registry()['lock_authority'],
                             'runtime/toolchains/TOOLCHAIN.lock.tsv')

    def test_corrupt_driver_download_never_executes(self) -> None:
        import io
        contract = self.policy['windows_acceptance']
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            with patch('urllib.request.urlopen', return_value=io.BytesIO(b'not a driver')), \
                    patch('subprocess.check_output') as execute:
                with self.assertRaisesRegex(RuntimeError, 'DRIVER_ARCHIVE_HASH_MISMATCH'):
                    provision_driver(contract, cache, 'ARM64')
                execute.assert_not_called()
            self.assertFalse((cache / 'geckodriver.exe').exists())

    def test_hardware_holds_are_not_browser_requirements(self) -> None:
        windows = self.policy['windows_acceptance']
        self.assertFalse(windows['hardware_acceptance']['browser_blocking'])
        self.assertEqual(windows['hardware_acceptance']['required_for_browser'], [])
        self.assertFalse(windows['hardware_acceptance']['hardware_proof_implied'])
        self.assertFalse(windows['loopback_is_authenticated_personal_runtime'])
        self.assertFalse(windows['temporary_install_is_release_install'])
        self.assertIn('authenticated_runtime_readback', windows['release_additional_requires'])
        self.assertIn('release_signed_persistent_installation', windows['release_additional_requires'])

    def test_fresh_readback_requires_exact_real_record_and_request_hashes(self) -> None:
        import sys
        import copy
        sys.path.insert(0, str(ROOT / 'src'))
        from qikvrt_effect_ack_http_terminal import State, canonical_json, sha256
        request = {'schema': 'qikvrt_terminal_input_v1', 'text': 'fresh-witness'}
        input_hash = sha256(canonical_json(request))
        state = State()
        record_hash, record = state.record(state='EFFECT_ACK_DONE', input_hash=input_hash,
                                           ordinary_release=True, reason='test')
        prepared = {'full_record': record, 'effect_ack': {'record_hash': record_hash}}
        before = {'events': 0}
        subject = {'head': 'a' * 40, 'tree': 'b' * 40}
        after = {'events': 1, 'repository_head': subject['head'],
                 'repository_tree': subject['tree'], 'last_event': {
                     'text': request['text'], 'input_hash': input_hash, 'record_hash': record_hash}}
        self.assertTrue(verify_effect_readback(before, after, prepared, request, subject))
        for field in ('text', 'input_hash', 'record_hash'):
            changed = copy.deepcopy(after)
            changed['last_event'][field] = 'substitution'
            self.assertFalse(verify_effect_readback(before, changed, prepared, request, subject))
        for field in ('repository_head', 'repository_tree'):
            self.assertFalse(verify_effect_readback(before, after | {field: 'c' * 40}, prepared, request, subject))
        self.assertFalse(verify_effect_readback(before, after | {'events': 0}, prepared, request, subject))

    def test_public_url_contract_preserves_authority_and_separate_release_gates(self) -> None:
        windows = self.policy['windows_acceptance']
        public = windows['public_url_acceptance']
        self.assertEqual(public['canonical_url'], CANONICAL_PRODUCT_URL)
        self.assertEqual(windows['terminal_url'], CANONICAL_PRODUCT_URL)
        self.assertEqual(public['authority_repository'], 'Goldkelch/qik-vrt')
        self.assertEqual(public['documented_publishing_source']['branch'], 'main')
        self.assertEqual(public['documented_publishing_source']['path'], '/docs')
        self.assertEqual(public['http_body_limit_bytes'], PUBLIC_BODY_LIMIT)
        self.assertFalse(public['public_root_readback_proves_full_candidate_deployment'])
        self.assertFalse(public['public_root_readback_accepts_personal_release'])
        self.assertIn('public_url_fresh_readback', windows['release_additional_requires'])
        hold = json.loads((ROOT / 'state/work_units/QIKVRT_FIREFOX_WINDOWS_SCOPE_20261001.json')
                          .read_text())['public_pages_continuation']
        self.assertEqual(hold['state'], 'HOLD_AUTHORITY_PAGES_CAPABILITY_UNAVAILABLE')
        self.assertIsNone(hold['actual_publishing_source'])
        self.assertFalse(hold['authority_pages_mutated'])

    def test_public_url_rejects_error_page_substitution_redirect_and_stale_bytes(self) -> None:
        public = self.policy['windows_acceptance']['public_url_acceptance']
        expected = hashlib.sha256(b'candidate root bytes').hexdigest()
        http = {'status': 200, 'final_url': CANONICAL_PRODUCT_URL,
                'body_sha256': expected, 'body_truncated': False, 'response_observed': True}
        browser = {'url': CANONICAL_PRODUCT_URL, 'title': public['expected_document_title'],
                   'product_main_present': True, 'github_pages_404': False,
                   'navigation_response_status': 200, 'extension_installed': False}
        result = evaluate_public_url_readback(http, browser, expected, public)
        self.assertTrue(result['public_url_fresh_readback'])
        self.assertFalse(result['personal_release_effect_ack_done'])
        self.assertFalse(result['deployed_candidate_head_tree_verified'])
        for change in ({'status': 404}, {'status': None}, {'body_truncated': True},
                       {'body_sha256': '0' * 64}, {'response_observed': False},
                       {'error': 'HTTP transport incomplete'},
                       {'final_url': 'https://ingolf-lohmann.github.io/qik-vrt/'},
                       {'final_url': CANONICAL_PRODUCT_URL + '?substitute=1'}):
            with self.subTest(http=change):
                self.assertFalse(evaluate_public_url_readback(
                    http | change, browser, expected, public)['public_url_fresh_readback'])
        for change in ({'title': 'Site not found · GitHub Pages'},
                       {'github_pages_404': True}, {'product_main_present': False},
                       {'navigation_response_status': 404}, {'url': 'about:blank'},
                       {'extension_installed': True}, {'error': 'Browser incomplete'},
                       {'url': 'https://ingolf-lohmann.github.io/qik-vrt/'}):
            with self.subTest(browser=change):
                self.assertFalse(evaluate_public_url_readback(
                    http, browser | change, expected, public)['public_url_fresh_readback'])

    def test_http_404_retains_fresh_exact_response_body_and_status(self) -> None:
        body = b'There is no GitHub Pages site here.'
        headers = Message()
        headers['Content-Type'] = 'text/html'
        error = urllib.error.HTTPError(CANONICAL_PRODUCT_URL, 404, 'Not Found',
                                       headers, io.BytesIO(body))
        with tempfile.TemporaryDirectory() as temp, \
                patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = error
            output = Path(temp)
            result = public_http_readback(CANONICAL_PRODUCT_URL, output)
            self.assertEqual(result['status'], 404)
            self.assertEqual(result['final_url'], CANONICAL_PRODUCT_URL)
            self.assertEqual(result['body_sha256'], hashlib.sha256(body).hexdigest())
            self.assertEqual((output / result['body_artifact']).read_bytes(), body)
            self.assertTrue(result['response_observed'])
            self.assertFalse(result['redirects_followed'])
            self.assertLessEqual(result['started_at'], result['finished_at'])
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header('Cache-control'), 'no-cache')

    def test_public_http_forbids_host_substitution_and_bounds_response_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, 'CANONICAL_PRODUCT_URL_MISMATCH'):
                public_http_readback('https://ingolf-lohmann.github.io/qik-vrt/', Path(temp))
            body = b'x' * (PUBLIC_BODY_LIMIT + 2)
            error = urllib.error.HTTPError(CANONICAL_PRODUCT_URL, 200, 'OK',
                                           Message(), io.BytesIO(body))
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.side_effect = error
                result = public_http_readback(CANONICAL_PRODUCT_URL, Path(temp))
            self.assertTrue(result['body_truncated'])
            self.assertEqual(result['body_bytes'], PUBLIC_BODY_LIMIT + 1)
        self.assertIsNone(NoPublicRedirect().redirect_request(
            None, None, 302, 'Found', {}, 'https://example.com/'))


if __name__ == "__main__":
    unittest.main()
