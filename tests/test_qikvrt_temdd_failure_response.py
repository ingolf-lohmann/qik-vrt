# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Negative TEMDD failure-observation tests: never convert CI into an effect receipt."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import qikvrt_temdd_failure_response as failure

SHA = "a" * 40


def event(conclusion="failure", sha=SHA):
    return {
        "action": "completed",
        "repository": {"full_name": "ingolf-lohmann/qik-vrt"},
        "workflow_run": {
            "name": "QIKVRT CI",
            "id": 42554304386,
            "run_attempt": 2,
            "status": "completed",
            "conclusion": conclusion,
            "head_sha": sha,
            "head_repository": {"full_name": "ingolf-lohmann/qik-vrt"},
            "html_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/42554304386",
        },
    }


def jobs():
    return {"jobs": [{"id": 129035462296, "name": "native S1", "conclusion": "failure",
                      "html_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/42554304386/job/129035462296"}]}


class MandatoryTEMDDFailureTests(unittest.TestCase):
    def test_good_regression_is_not_prod_receipt(self):
        r = failure.build_receipt(event(), jobs(), actual_head=SHA,
                                  test_exit="0", test_log=b"Ran 99 tests: OK")
        self.assertEqual(r["temdd_regression"], "PASS")
        self.assertEqual(r["state"], "HOLD")
        self.assertEqual(r["release_admission"], "BLOCKED")
        self.assertFalse(r["effect_ack_done"])
        self.assertFalse(r["specific_failed_step_reproduced"])
        self.assertEqual(r["source_head"], SHA)
        self.assertEqual(len(r["failed_jobs"]), 1)
        self.assertEqual([e["kind"] for e in r["events"]],
                         ["OBSERVE", "CLASSIFY", "ACTION", "READBACK", "HOLD"])

    def test_wrong_head_does_not_accept_test(self):
        r = failure.build_receipt(event(), jobs(), actual_head="b" * 40,
                                  test_exit="0", test_log=b"OK")
        self.assertEqual(r["temdd_regression"], "NOT_VERIFIED")
        self.assertIn("EXACT_FAILED_SOURCE_NOT_TESTED", r["events"][-1]["reasons"])

    def test_missing_jobs_keeps_hold(self):
        r = failure.build_receipt(event(), {}, actual_head=SHA,
                                  test_exit="0", test_log=b"OK")
        self.assertIn("FAILED_JOB_EVIDENCE_INCOMPLETE", r["events"][-1]["reasons"])
        self.assertEqual(r["state"], "HOLD")

    def test_failed_regression_cannot_pass(self):
        r = failure.build_receipt(event(), jobs(), actual_head=SHA,
                                  test_exit="1", test_log=b"FAIL")
        self.assertEqual(r["temdd_regression"], "FAIL")
        self.assertFalse(r["effect_ack_done"])

    def test_event_from_another_repository_is_not_verified(self):
        e = event()
        e["repository"]["full_name"] = "someone/else"
        r = failure.build_receipt(e, jobs(), actual_head=SHA,
                                  test_exit="0", test_log=b"OK")
        self.assertEqual(r["temdd_regression"], "NOT_VERIFIED")

    def test_action_required_is_unresolved_not_success(self):
        r = failure.build_receipt(event(conclusion="action_required"), {},
                                  actual_head="", test_exit="", test_log=b"")
        self.assertEqual(r["state"], "HOLD")
        self.assertEqual(r["temdd_regression"], "NOT_VERIFIED")

    def test_bad_inputs_hold_and_never_crash(self):
        for e in ({}, [], None, {"workflow_run": {"id": 1}}, event(sha="bad")):
            with self.subTest(e=e):
                r = failure.build_receipt(e, {}, actual_head=SHA,
                                          test_exit="", test_log=b"")
                self.assertEqual(r["state"], "HOLD")
                self.assertFalse(r["effect_ack_done"])

    def test_workflow_is_read_only_and_does_not_self_trigger(self):
        path = ROOT / ".github/workflows/qikvrt_temdd_failure_response.yml"
        source = path.read_text(encoding="utf-8")
        self.assertIn("workflow_run:", source)
        self.assertIn("types: [completed]", source)
        self.assertIn("permissions:\n  contents: read\n  actions: read", source)
        self.assertIn("persist-credentials: false", source)
        self.assertNotIn("- 'QIKVRT mandatory TEMDD failure response'", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("git push", source)
        self.assertNotIn("gh pr merge", source)


if __name__ == "__main__":
    unittest.main()
