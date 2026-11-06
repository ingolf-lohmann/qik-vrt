#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Synthetic structural safety tests; no real provider access is implied."""
import unittest

from tools.qikvrt_external_account_binding_preflight import preflight


BASE = {
    "schema": "qikvrt_external_binding_preflight_v1",
    "binding_ref": "candidate-1",
    "provider": "linkedin",
    "capability": "identity.read",
    "consent_method": "OAUTH_2_0_OIDC",
    "subject_digest": "a" * 64,
    "evidence_digest": "b" * 64,
    "exact_scope": "openid profile email",
    "consent_expiry": "2026-11-06T12:00:00Z",
    "source_ref": "provider-original-readback-pending",
    "revocation_ref": "revocation-handle-pending",
    "original_host_ref": "qik-vrt-authority-host-pending",
}


class BindingPreflightTests(unittest.TestCase):
    def test_linkedin_identity_shape_is_untrusted(self):
        r = preflight(BASE)
        self.assertEqual(r["classification"], "STRUCTURALLY_COMPLETE_UNTRUSTED")
        self.assertEqual(r["effect_ack_done"], "NOT_CLAIMED")

    def test_linkedin_write_requires_separate_scope(self):
        r = preflight(dict(BASE, capability="posts.write"))
        self.assertEqual(r["reason"], "CONSENT_METHOD_MISMATCH")

    def test_apple_identity_is_not_icloud_drive(self):
        r = preflight(dict(BASE, provider="apple_account",
                           capability="files.read_selected"))
        self.assertEqual(r["classification"], "BLOCKED")

    def test_icloud_selected_read_shape_only(self):
        r = preflight(dict(BASE, provider="icloud_drive", capability="files.read_selected",
                           consent_method="OS_FILE_PROVIDER_PICKER",
                           exact_scope="user_selected_file_read"))
        self.assertEqual(r["classification"], "STRUCTURALLY_COMPLETE_UNTRUSTED")
        self.assertNotEqual(r["effect_ack_done"], "true")

    def test_icloud_read_cannot_write(self):
        r = preflight(dict(BASE, provider="icloud_drive", capability="files.write_selected",
                           consent_method="OS_FILE_PROVIDER_PICKER",
                           exact_scope="user_selected_file_read"))
        self.assertEqual(r["reason"], "SCOPE_CAPABILITY_MISMATCH")

    def test_raw_token_rejected(self):
        r = preflight(dict(BASE, access_token="never-put-this-in-source"))
        self.assertEqual(r["reason"], "SECRET_FIELD_FORBIDDEN")

    def test_raw_apple_bookmark_rejected(self):
        r = preflight(dict(BASE, security_scoped_bookmark="private"))
        self.assertEqual(r["reason"], "SECRET_FIELD_FORBIDDEN")

    def test_missing_evidence_digest_rejected(self):
        r = dict(BASE)
        r.pop("evidence_digest")
        self.assertEqual(preflight(r)["classification"], "BLOCKED")

    def test_bad_sha256_rejected(self):
        self.assertEqual(preflight(dict(BASE, subject_digest="bad"))["reason"],
                         "EVIDENCE_DIGEST_INVALID")

    def test_unlisted_permission_rejected(self):
        self.assertEqual(preflight(dict(BASE, capability="private_messages.read"))["reason"],
                         "CAPABILITY_NOT_ALLOWED")

    def test_no_global_done_in_any_case(self):
        for case in (BASE, {}, {"password": "bad"}, None):
            self.assertNotEqual(preflight(case)["effect_ack_done"], "true")


if __name__ == "__main__":
    unittest.main()
