from __future__ import annotations

import json
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

from tools.qikvrt_firefox_windows_witness import (
    target_matches, provision_driver, verify_effect_readback,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md"
POLICY = ROOT / "policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json"


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


if __name__ == "__main__":
    unittest.main()
