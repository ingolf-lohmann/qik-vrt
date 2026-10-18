from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md"
POLICY = ROOT / "policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json"


class PersonalFirefoxCapabilityBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = SPEC.read_text(encoding="utf-8")
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.roles = json.loads((ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json").read_text(encoding="utf-8"))

    def test_normative_boundary_matches_machine_contract(self) -> None:
        self.assertEqual(
            self.policy["schema"],
            "qikvrt_personal_firefox_capability_boundary_v1",
        )
        self.assertEqual(
            self.policy["source_subject"]["standard_repository"],
            self.roles["canonical_upstream"]["repository"],
        )
        self.assertEqual(self.policy["source_subject"]["mirror_repository"], self.roles["mirror"]["repository"])
        self.assertEqual(self.policy["source_subject"]["repository_roles_source"], "policy/CANONICAL_UPSTREAM_REMOTE_V1.json")
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
            with self.subTest(path=relative):
                self.assert_standard_payload(data)

    def assert_standard_payload(self, data: str) -> None:
        for marker in self.policy["standard_firefox_package"]["forbidden_personal_markers"]:
            self.assertNotIn(marker, data)

    def test_public_owner_binding_is_not_personal_payload(self) -> None:
        authority = self.roles["canonical_upstream"]["repository"]
        self.assert_standard_payload(f'const AUTHORITY = "{authority}";')
        self.assertNotIn(authority, self.policy["standard_firefox_package"]["forbidden_personal_markers"])
        self.assertIn("ordinary source bindings", self.spec)

    def test_personal_payload_and_credentials_still_fail_closed(self) -> None:
        for marker in (
            "personal/ingolf-lohmann/firefox-assistant/ui.js",
            "qikvrt_personal_assistant",
            "QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1",
            "QIKVRT_PERSONAL_FIREFOX",
            "OPENAI_API_KEY",
            "CHATGPT_ACCESS_TOKEN",
        ):
            with self.subTest(marker=marker), self.assertRaises(AssertionError):
                self.assert_standard_payload(marker)

    def test_standard_manifest_remains_standard_surface(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "browser/firefox/qikvrt-terminal/manifest.json"
            ).read_text(encoding="utf-8")
        )
        serialized = json.dumps(manifest, sort_keys=True)
        authority = self.roles["canonical_upstream"]["repository"]
        mirror = self.roles["mirror"]["repository"]
        self.assertIn(f"https://github.com/{authority}/*", manifest["host_permissions"])
        self.assertIn(f"https://github.com/{authority}/blob/main/AI*", manifest["content_scripts"][0]["matches"])
        self.assertIn(f"https://github.com/{mirror}/blob/main/AI*", manifest["content_scripts"][0]["matches"])
        self.assertCountEqual(manifest["permissions"], ["storage", "alarms", "activeTab", "scripting"])
        self.assertEqual(manifest["action"]["default_popup"], "options.html")
        self.assertNotIn("<all_urls>", serialized)
        self.assertNotIn("personal/ingolf-lohmann/", serialized)
        self.assertNotIn("chatgpt.com", serialized)
        self.assertNotIn("openai.com", serialized)

    def test_personal_release_stays_hold_until_fresh_runtime_evidence(self) -> None:
        candidate = self.policy["personal_release_acceptance"]["current_candidate"]
        self.assertTrue(candidate["boundary_contract_materialized"])
        self.assertTrue(candidate["personal_capability_manifest_materialized"])
        self.assertTrue((ROOT / candidate["personal_capability_manifest"]).is_file())
        self.assertFalse(candidate["normal_baseline_runtime_readback"])
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


if __name__ == "__main__":
    unittest.main()
