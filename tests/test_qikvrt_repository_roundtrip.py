# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import hashlib
import pathlib
import subprocess
import tempfile
import unittest

from tools.qikvrt_repository_roundtrip import RoundtripError, roundtrip


class RepositoryRoundtripTests(unittest.TestCase):
    def test_binary_symlink_executable_and_unicode_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root).decode().strip()
            git("init", "-q")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Roundtrip Test")
            (root / "binary.bin").write_bytes(bytes(range(256)) + b"\x00\xff")
            (root / "über.txt").write_text("Grüße 🌈\n", encoding="utf-8")
            executable = root / "run.sh"
            executable.write_bytes(b"#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
            (root / "shortcut").symlink_to("binary.bin")
            git("add", ".")
            git("commit", "-qm", "fixture")
            head = git("rev-parse", "HEAD")
            output = root / "roundtrip.ndjson"
            result = roundtrip(root, head, output)
            self.assertEqual(result["files"], 4)
            self.assertEqual(result["roundtrip"], "PASS")
            self.assertFalse(result["effect_ack_done"])
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),
                             result["serialized_sha256"])

    def test_non_commit_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RoundtripError):
                roundtrip(pathlib.Path(tmp), "main", pathlib.Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
