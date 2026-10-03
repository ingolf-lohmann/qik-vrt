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
    """Pages observation reuses the same target/installation-bound source carrier."""
    def run_observer(self, *, token='', outcome='skipped', head=None):
        from tools import qikvrt_authority_url_probe as p
        from tests.test_qikvrt_authority_url_probe import AuthorityURLProbeTests, BINDING, HEAD
        fixture = AuthorityURLProbeTests()
        values = {
            f"/repos/{p.AUTHORITY}/pages": (200, {"source": {"branch": "main", "path": "/docs"}}),
            f"/repos/{p.AUTHORITY}/pages/builds/latest": (200, {"commit": HEAD}),
        }
        if head is not None:
            values[f"/repos/{p.AUTHORITY}/git/ref/heads/main"] = (200, {
                "ref": "refs/heads/main", "object": {"type": "commit", "sha": head}})
        binding = dict(BINDING, requested_permissions={"contents": "read", "pages": "read"})
        result = p.probe(token, "QIKVRT_AUTHORITY_APP_TOKEN" if token else None,
                         {"repository": p.MIRROR, "head": "c" * 40, "tree": "d" * 40},
                         binding=binding if outcome == "success" else None,
                         transport=fixture.transport(values),
                         public_reader=lambda url: (200, b"public Pages fixture"), pages=True)
        return result, fixture.paths

    def test_empty_bindings_and_failed_mint_remain_hold_without_authority_requests(self):
        for outcome in ("skipped", "failure"):
            result, requests = self.run_observer(outcome=outcome)
            self.assertEqual(result["authority_pages_state"], "HOLD_AUTHORITY_PAGES_READ_UNAVAILABLE")
            self.assertEqual(result["authority_reads"], {})
            self.assertEqual(requests, [])
            self.assertFalse(result["git_object_closure_verified"])

    def test_app_route_reads_exact_authority_source_without_credential_transfer(self):
        from tools import qikvrt_authority_url_probe as p
        result, requests = self.run_observer(token="fixture-pages-secret-123456", outcome="success")
        self.assertEqual(result["state"], "OBSERVED_AUTHORITY_PAGES")
        self.assertIn("source_commit", result["authority_reads"])
        self.assertIn("source_inventory", result["authority_reads"])
        self.assertIn(f"/repos/{p.AUTHORITY}/pages", requests)
        self.assertTrue(all(item["authentication"] == "anonymous" for item in result["public_readbacks"]))
        self.assertNotIn("fixture-pages-secret-123456", json.dumps(result))
        for field in ("publication_mutated", "deployed_candidate_head_tree_verified",
                      "persistent_signed_installation_verified", "authenticated_runtime_readback",
                      "personal_release_effect_ack_done", "git_object_closure_verified"):
            self.assertFalse(result[field])

    def test_substituted_authority_head_is_not_used_as_source_path(self):
        result, requests = self.run_observer(token="fixture-pages-secret-123456", outcome="success",
                                            head="../substitution")
        self.assertEqual(result["first_blocker"], "AUTHORITY_MAIN_SUBJECT_NOT_VERIFIED")
        self.assertNotIn("source_commit", result["authority_reads"])
        self.assertFalse(any("/git/commits/" in path for path in requests))

    def test_app_requires_existing_binding_and_pages_permissions_stay_in_pages_mode(self):
        from tools import qikvrt_authority_url_probe as p
        from tests.test_qikvrt_authority_url_probe import BINDING
        self.assertFalse(p.valid_binding(BINDING, pages=True))
        self.assertTrue(p.valid_binding(dict(BINDING,
            requested_permissions={"contents": "read", "pages": "read"}), pages=True))
        source = (ROOT / p.WORKFLOW).read_text()
        self.assertEqual(source.count("uses: " + p.APP_ACTION), 1)
        self.assertIn("permission-pages: \u0024{{ env.QIKVRT_AUTHORITY_OPERATION == 'authority_pages_readback'", source)
        self.assertIn("owner: Goldkelch", source)
        self.assertIn("repositories: qik-vrt", source)
        self.assertNotIn("permission-administration:", source)
        self.assertNotIn("pages-readback:", source)


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

    def test_windows_acceptance_requires_seed_and_durable_restart_without_release_promotion(self):
        windows = self.policy['windows_acceptance']
        linux = self.policy['linux_ring_acceptance']
        data = (ROOT / windows['seed_path']).read_bytes()
        self.assertEqual(len(data), 400)
        self.assertEqual(hashlib.sha256(data).hexdigest(), windows['seed_sha256'])
        self.assertEqual(windows['seed_sha256'], linux['seed_sha256'])
        required = windows['functional_witness_requires']
        self.assertIn('canonical_400_byte_seed_admission_and_full_record_binding', required)
        self.assertIn('durable_state.single_use_replay_after_restart', required)
        self.assertIn('durable_state.seed_mismatch_and_corrupt_or_truncated_state_refusal', required)
        self.assertEqual(windows['durable_state']['architecture_evidence_transfer'], 'DENY')
        self.assertFalse(windows['durable_state']['power_loss_tested'])
        self.assertFalse(self.policy['personal_release_acceptance']['current_candidate']['personal_release_effect_ack_done'])

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
