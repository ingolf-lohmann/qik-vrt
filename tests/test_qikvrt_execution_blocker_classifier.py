# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""TEMDD regression tests for native GitHub execution-blocker classification."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("classifier", ROOT / "tools/qikvrt_execution_blocker_classifier.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEAD = "a" * 40


def observed(conclusion, jobs, status="completed"):
    return {"expected_head_sha": HEAD, "runs": [
        {"id": 7, "head_sha": HEAD, "status": status, "conclusion": conclusion, "jobs": jobs}]}


class ExecutionBlockerClassifierTests(unittest.TestCase):
    def test_action_required_without_jobs_is_admission_block(self):
        result = MODULE.classify(observed("action_required", []))
        self.assertEqual(result["findings"][0]["category"], "EXECUTION_ADMISSION_BLOCKED")
        self.assertEqual(result["state"], "HOLD")
        self.assertFalse(result["effect_ack_done"])
        self.assertFalse(result["native_execution_admitted"])

    def test_failed_executed_job_requires_temdd(self):
        result = MODULE.classify(observed("failure", [{"status": "completed"}]))
        self.assertEqual(result["findings"][0]["next_action"], "TEMDD_EXACT_HEAD_FAILURE_ANALYSIS")

    def test_failed_run_without_jobs_is_not_silent_success(self):
        result = MODULE.classify(observed("failure", []))
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["findings"][0]["category"], "FAILED_RUN_WITHOUT_JOB_EVIDENCE")
        self.assertEqual(result["findings"][0]["next_action"], "CHECK_GITHUB_NATIVE_JOB_READBACK")

    def test_cancelled_run_is_not_silent_success(self):
        result = MODULE.classify(observed("cancelled", []))
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["findings"][0]["category"], "NON_SUCCESS_TERMINAL_RUN")

    def test_pending_is_not_claimed_as_deadlock(self):
        result = MODULE.classify(observed(None, [], status="pending"))
        self.assertEqual(result["findings"][0]["category"], "ACTIVE_UNPROVEN_PROGRESS")

    def test_success_does_not_claim_effect_ack(self):
        result = MODULE.classify(observed("success", [{"status": "completed"}]))
        self.assertEqual(result["state"], "NO_BLOCKER_OBSERVED")
        self.assertFalse(result["effect_ack_done"])

    def test_drift_fails_closed(self):
        value = observed("action_required", [])
        value["runs"][0]["head_sha"] = "b" * 40
        with self.assertRaises(ValueError):
            MODULE.classify(value)

    def test_duplicate_run_fails_closed(self):
        value = observed("action_required", [])
        value["runs"].append(dict(value["runs"][0]))
        with self.assertRaises(ValueError):
            MODULE.classify(value)


if __name__ == "__main__":
    unittest.main()
