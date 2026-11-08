"""Offline contract tests for provider-independent evidence collector."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "qikvrt_native_evidence.py"
spec = importlib.util.spec_from_file_location("qikvrt_native_evidence", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class EvidenceTests(unittest.TestCase):
    def test_missing_git_and_release_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(module, "git", side_effect=OSError("missing")), \
                 patch.object(module, "http_json", side_effect=OSError("offline")), \
                 patch.object(module.urllib.request, "urlopen", side_effect=OSError("offline")):
                data = module.collect(Path(tmp), "https://example.invalid/")
        self.assertEqual(data["dod"], "OPEN/BLOCKED")
        self.assertEqual(data["checks"]["release"]["state"], "unknown")
        self.assertEqual(data["checks"]["exact_head_tree"]["state"], "unknown")
        self.assertEqual(data["checks"]["public_tls"]["state"], "unknown")
        self.assertEqual(data["checks"]["effect_ack_done"]["state"], "unknown")
        self.assertEqual(data["prs"]["703"]["state"], "unknown")

    def test_blocked_release_stays_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "interfaces").mkdir()
            (root / "interfaces" / "client-release.json").write_text(
                json.dumps({"admission": "BLOCKED", "ci": "UNVERIFIED",
                            "governance": "UNVERIFIED", "integrity": "UNVERIFIED"}))
            with patch.object(module, "git", return_value="abc"), \
                 patch.object(module, "http_json", side_effect=OSError("offline")), \
                 patch.object(module.urllib.request, "urlopen", side_effect=OSError("offline")):
                data = module.collect(root, "https://example.invalid/")
        self.assertEqual(data["checks"]["release"]["state"], "open")
        self.assertEqual(data["dod"], "OPEN/BLOCKED")

if __name__ == "__main__":
    unittest.main()
