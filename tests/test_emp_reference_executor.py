import hashlib
import tempfile
import unittest
from pathlib import Path
from runtime.emp.reference_executor import execute_file_effect


class ReferenceExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.payload = b"EMP effect fixture"
        self.digest = hashlib.sha256(self.payload).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def test_authorized_effect_and_readback(self):
        r = execute_file_effect(str(self.root), "out/effect.txt", self.payload,
                                authorized=True, expected_sha256=self.digest)
        self.assertTrue(r["observed"])
        self.assertFalse(r["effect_ack_done"])
        self.assertEqual((self.root / "out/effect.txt").read_bytes(), self.payload)

    def test_unauthorized_effect_rejected(self):
        with self.assertRaises(PermissionError):
            execute_file_effect(str(self.root), "out.txt", self.payload,
                                authorized=False, expected_sha256=self.digest)
        self.assertFalse((self.root / "out.txt").exists())

    def test_wrong_hash_rejected(self):
        with self.assertRaises(ValueError):
            execute_file_effect(str(self.root), "out.txt", self.payload,
                                authorized=True, expected_sha256="0" * 64)

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            execute_file_effect(str(self.root), "../escape.txt", self.payload,
                                authorized=True, expected_sha256=self.digest)

    def test_symlink_escape_rejected(self):
        outside = self.root.parent / "outside-emp"
        (self.root / "link").symlink_to(outside)
        with self.assertRaises(ValueError):
            execute_file_effect(str(self.root), "link/out.txt", self.payload,
                                authorized=True, expected_sha256=self.digest)


if __name__ == "__main__":
    unittest.main()
