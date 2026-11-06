# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression: diagnose a refused GitHub ref write without exposing provider data or retrying."""
import subprocess
import unittest
from unittest.mock import patch

from tools import qikvrt_autonomous_self_heal as controller


class RESTFailureClassificationTests(unittest.TestCase):
    def test_classified_failures_remain_fail_closed(self):
        fixtures = (
            ("gh: You have exceeded a secondary rate limit. Please wait. (HTTP 403)",
             "SECONDARY_RATE_LIMIT"),
            ("gh: API rate limit exceeded for this installation. (HTTP 403)",
             "PRIMARY_RATE_LIMIT"),
            ("gh: Resource not accessible by integration (HTTP 403)",
             "INTEGRATION_PERMISSION_DENIED"),
            ("gh: Repository rule violations found (HTTP 403)",
             "REPOSITORY_POLICY_DENIED"),
            ("gh: Unidentified provider refusal: SECRET-CANARY (HTTP 403)",
             "FORBIDDEN_CAUSE_UNVERIFIED"),
        )
        for diagnostic, expected in fixtures:
            with self.subTest(expected=expected):
                failed = subprocess.CompletedProcess(
                    args=["gh"], returncode=1, stdout="", stderr=diagnostic
                )
                api = controller.GitHubREST("ingolf-lohmann/qik-vrt")
                with patch.object(controller.subprocess, "run", return_value=failed) as called:
                    with self.assertRaises(controller.SelfHealBlock) as captured:
                        api.call("POST", "git/refs", {"ref": "refs/qikvrt/pr-continuation/turns/160",
                                                       "sha": "a" * 40})
                message = str(captured.exception)
                self.assertIn("REST POST git/refs: 403;", message)
                self.assertIn("cause=" + expected, message)
                self.assertIn("no automatic retry", message)
                self.assertNotIn("SECRET-CANARY", message)
                self.assertEqual(called.call_count, 1)

    def test_no_false_permission_inference_from_bare_403(self):
        self.assertEqual(controller.classify_rest_failure("(HTTP 403)", "403"),
                         "FORBIDDEN_CAUSE_UNVERIFIED")
        self.assertEqual(controller.classify_rest_failure("(HTTP 429)", "429"),
                         "HTTP_FAILURE_UNCLASSIFIED")

    def test_successful_response_unchanged(self):
        accepted = subprocess.CompletedProcess(args=["gh"], returncode=0,
                                               stdout='{"ok": true}', stderr="")
        api = controller.GitHubREST("ingolf-lohmann/qik-vrt")
        with patch.object(controller.subprocess, "run", return_value=accepted) as called:
            result = api.call("GET", "git/ref/heads/main")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(called.call_count, 1)


if __name__ == "__main__":
    unittest.main()
