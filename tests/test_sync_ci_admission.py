"""Offline regression tests for the bounded exact-HEAD CI controller."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/qikvrt_sync_ci_admission.py"
spec = importlib.util.spec_from_file_location("qikvrt_sync_ci_admission", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
HEAD = "a" * 40


class AdmissionTests(unittest.TestCase):
    def fake(self, method, path, token, body=None):
        if "/commits/" in path:
            return {"sha": HEAD}
        if path.endswith("/dispatches"):
            return {}
        if "/jobs?" in path:
            return {"total_count": 1, "jobs": [{"conclusion": "success"}]}
        if "/actions/runs/17" in path:
            return {"head_sha": HEAD, "status": "completed", "conclusion": "success"}
        if "/runs?event=" in path:
            self.polls += 1
            return {"workflow_runs": [] if self.polls == 1 else [
                {"id": 17, "head_sha": HEAD, "event": "workflow_dispatch"}]}
        raise AssertionError(path)

    def test_exact_head_success_still_not_effect_ack(self):
        self.polls = 0
        with patch.object(mod, "request", side_effect=self.fake), patch.object(mod.time, "sleep"):
            result = mod.execute("ingolf-lohmann/qik-vrt", "main", HEAD, "token", interval=0)
        self.assertEqual(result["status"], "CI_VERIFIED")
        self.assertFalse(result["effect_ack_done"])

    def test_pre_dispatch_head_drift(self):
        with patch.object(mod, "request", return_value={"sha": "b" * 40}):
            with self.assertRaisesRegex(mod.AdmissionError, "HEAD_DRIFT"):
                mod.execute("ingolf-lohmann/qik-vrt", "main", HEAD, "token")

    def test_empty_job_list_is_not_success(self):
        self.polls = 0
        def no_jobs(method, path, token, body=None):
            if "/jobs?" in path:
                return {"total_count": 0, "jobs": []}
            return self.fake(method, path, token, body)
        with patch.object(mod, "request", side_effect=no_jobs), patch.object(mod.time, "sleep"):
            with self.assertRaisesRegex(mod.AdmissionError, "NO_COMPLETE_JOB_EVIDENCE"):
                mod.execute("ingolf-lohmann/qik-vrt", "main", HEAD, "token", interval=0)

    def test_action_required_is_blocked(self):
        self.polls = 0
        def blocked(method, path, token, body=None):
            if "/actions/runs/17" in path:
                return {"head_sha": HEAD, "status": "completed", "conclusion": "action_required"}
            return self.fake(method, path, token, body)
        with patch.object(mod, "request", side_effect=blocked), patch.object(mod.time, "sleep"):
            with self.assertRaisesRegex(mod.AdmissionError, "CI_action_required"):
                mod.execute("ingolf-lohmann/qik-vrt", "main", HEAD, "token", interval=0)


if __name__ == "__main__":
    unittest.main()
