# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Static SSO admission and Digital Twin public-exposure contract tests."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DigitalTwinSSOGateTests(unittest.TestCase):
    def test_sso_is_mandatory_for_all_privileged_lifecycle_transitions(self):
        policy = json.loads((ROOT / "policy/QIKVRT_DIGITAL_TWIN_SSO_AUTHORITY_V1.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["identity"]["protocol"], "OIDC_AUTHORIZATION_CODE_PKCE_S256")
        self.assertEqual(policy["authorization"]["on_sso_unavailable"], "HOLD_SSO_SESSION_NOT_ESTABLISHED")
        self.assertIn("VALIDATED_CURRENT_SSO_IDENTITY", policy["authorization"]["grant_requires"])
        self.assertIn("CURRENT_VALIDATED_SSO_IDENTITY", policy["authorization"]["expand_requires"])
        self.assertIn("UNEXPIRED_OR_VALIDLY_REFRESHED_SSO_SESSION", policy["authorization"]["retain_requires"])
        self.assertTrue(policy["identity"]["no_manual_password_collection"])
        self.assertFalse(policy["implementation_status"]["digital_twin_rest_sso_enforced"])
        self.assertFalse(policy["implementation_status"]["effect_ack_done"])

    def test_no_remote_digital_twin_reference_without_validated_sso(self):
        source = (ROOT / "src/qikvrt_digital_twin_rest.py").read_text(encoding="utf-8")
        self.assertIn('ns.bind not in ("127.0.0.1", "::1")', source)
        self.assertIn("HOLD_SSO_SESSION_NOT_ESTABLISHED", source)

    def test_public_question_access_does_not_inherit_owner_privileges(self):
        policy = json.loads((ROOT / "policy/QIKVRT_DIGITAL_TWIN_SSO_AUTHORITY_V1.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["subjects"]["public_anonymous_question_access"], "ALLOWED_WITHOUT_DIGITAL_TWIN_PRIVILEGES")
        self.assertEqual(policy["subjects"]["personal_digital_twin"], "SSO_REQUIRED")
        self.assertTrue(policy["operations"]["sso_does_not_bypass_code_owner_review"])
        self.assertTrue(policy["operations"]["sso_does_not_imply_dns_api_permission"])


if __name__ == "__main__":
    unittest.main()
