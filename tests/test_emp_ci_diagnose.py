import io
import json
import unittest
from unittest.mock import patch
from runtime.emp.ci_diagnose import inspect


class DiagnoseTests(unittest.TestCase):
    def test_no_token_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "token"):
            inspect(123, "")

    def test_invalid_run_fails_closed(self):
        with self.assertRaises(ValueError):
            inspect(0, "token")

    def test_failed_job_is_reported(self):
        payload = {"jobs": [{"id": 7, "name": "test", "conclusion": "failure",
                             "steps": [{"name": "pytest", "conclusion": "failure"}]}]}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = inspect(123, "token")
        self.assertTrue(result["temdd_required"])
        self.assertEqual(result["failed_jobs"][0]["failed_steps"][0]["name"], "pytest")
        self.assertFalse(result["repair_executed"])

    def test_success_does_not_claim_ack(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b'{"jobs":[]}')):
            result = inspect(123, "token")
        self.assertFalse(result["effect_ack_done"])

    def test_pagination_cap_fails_closed(self):
        jobs = [{"id": i, "conclusion": "success"} for i in range(100)]
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps({"jobs": jobs}).encode())):
            result = inspect(123, "token", max_pages=1)
        self.assertTrue(result["pagination_truncated"])
        self.assertTrue(result["temdd_required"])


if __name__ == "__main__":
    unittest.main()
