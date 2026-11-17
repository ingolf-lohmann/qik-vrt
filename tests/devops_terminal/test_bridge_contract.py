"""Fail-closed acceptance checks for the terminal bridge (stdlib only)."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("terminal_bridge", ROOT / "interfaces" / "devops_terminal_bridge.py")
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)

class BridgeContractTests(unittest.TestCase):
    def test_missing_github_credential_is_not_success(self):
        with patch.object(bridge, "TOKEN", ""):
            with self.assertRaisesRegex(RuntimeError, "GITHUB_TOKEN_NOT_CONFIGURED"):
                bridge.fetch("/issues/651")

    def test_snapshot_preserves_effect_boundary(self):
        pr = {"head": {"sha": "a"*40}, "html_url": "https://github.com/example/pr/1",
              "number": 653, "merged": False}
        issue = {"number": 651, "state": "open"}
        runs = {"workflow_runs": [
            {"head_sha": "a"*40, "name": "CI", "conclusion": "success"},
            {"head_sha": "b"*40, "name": "CI", "conclusion": "success"}]}
        with patch.object(bridge, "fetch", side_effect=[pr, issue, runs]):
            result = bridge.snapshot()
        self.assertEqual(len(result["runs"]), 1)
        self.assertEqual(result["head_sha"], "a"*40)
        self.assertEqual(result["effect"]["status"], "UNVERIFIED")
        self.assertFalse(result["pr"]["merged"])

    def test_served_html_path_exists(self):
        source = (ROOT / "interfaces" / "devops_terminal_bridge.py").read_text()
        self.assertIn("devops_terminal_client.html", source)
        self.assertTrue((ROOT / "interfaces" / "devops_terminal_client.html").is_file())

    def test_command_admission_is_fail_closed(self):
        source = (ROOT / "interfaces" / "devops_terminal_bridge.py").read_text()
        self.assertIn("ORIGINAL_TERMINAL_TRANSPUTER_ADAPTER_NOT_ADMITTED", source)
        self.assertIn("SESSION_REQUIRED", source)
        self.assertIn("ORIGIN_NOT_ADMITTED", source)

if __name__ == "__main__":
    unittest.main()
