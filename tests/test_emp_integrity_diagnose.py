import unittest
from unittest.mock import patch
from pathlib import Path
from tools.emp_integrity_diagnose import diagnose


class IntegrityDiagnoseTests(unittest.TestCase):
    @patch("tools.emp_integrity_diagnose.integrity._regular_file_bytes")
    @patch("tools.emp_integrity_diagnose.integrity.build_outputs")
    def test_no_drift(self, build, read):
        build.return_value = (b"{}", b"index", b"detached", {})
        read.side_effect = [b"{}", b"index", b"detached"]
        result = diagnose(Path("/tmp"))
        self.assertTrue(result["integrity_match"])
        self.assertFalse(result["effect_ack_done"])

    @patch("tools.emp_integrity_diagnose.integrity._regular_file_bytes")
    @patch("tools.emp_integrity_diagnose.integrity.build_outputs")
    def test_added_path_detected_without_mutation(self, build, read):
        old = b'{"files":[]}'
        new = b'{"files":[{"path":"runtime/emp/transition.py","immutable":true}]}'
        build.return_value = (new, b"index", b"detached", {})
        read.side_effect = [old, b"index", b"detached"]
        result = diagnose(Path("/tmp"))
        self.assertFalse(result["integrity_match"])
        self.assertEqual(result["differences"][0]["added_paths"], ["runtime/emp/transition.py"])
        self.assertFalse(result["manifest_modified"])


if __name__ == "__main__":
    unittest.main()
