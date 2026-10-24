# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Nested test scripts may not mutate their caller's diagnostic artifacts."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CIFixtureIsolation(unittest.TestCase):
    def test_release_test_process_cannot_overwrite_outer_runner_logs(self):
        # Execute the production Make recipe, replacing only the test executable.
        # A nested fixture deliberately writes the same log names as the CI.
        import sys
        source = (ROOT / "Makefile").read_text()
        recipe = source.split("release-automation:\n", 1)[1].split("\n\n", 1)[0]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            outer = root / "outer-runner"
            outer.mkdir()
            sentinel = outer / "qikvrt-ci-final/final-make.log"
            sentinel.parent.mkdir()
            sentinel.write_text("OUTER EVIDENCE MUST SURVIVE\n")
            recorder = root / "runner-path.txt"
            fake = root / "fake_python.py"
            fake.write_text(
                "import os\nfrom pathlib import Path\n"
                "scratch=Path(os.environ['RUNNER_TEMP'])\n"
                "target=scratch/'qikvrt-ci-final/final-make.log'\n"
                "target.parent.mkdir(parents=True,exist_ok=True)\n"
                "target.write_text('NESTED FIXTURE LOG\\n')\n"
                "Path(os.environ['FIXTURE_RUNNER_PATH']).write_text(str(scratch))\n"
                "raise SystemExit(int(os.environ['FIXTURE_TEST_EXIT']))\n")
            makefile = root / "Makefile"
            makefile.write_text("release-automation:\n" + recipe.split("\n\tPYTHONDONT", 1)[0] + "\n")
            env = dict(os.environ, RUNNER_TEMP=str(outer), FIXTURE_RUNNER_PATH=str(recorder))
            for code in ("0", "17"):
                result = subprocess.run(
                    ["make", "release-automation", f"PYTHON={sys.executable} -S -B {fake}"],
                    cwd=root, env={**env, "FIXTURE_TEST_EXIT": code},
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode == 0, code == "0", result.stderr)
                self.assertEqual(sentinel.read_text(), "OUTER EVIDENCE MUST SURVIVE\n")
                isolated = Path(recorder.read_text())
                self.assertNotEqual(isolated, outer)
                self.assertFalse(isolated.exists(), "fixture scratch must be cleaned on success/failure")
            # Historical non-isolated recipe must fail the preservation predicate.
            makefile.write_text("release-automation:\n\t$(PYTHON) -m unittest\n")
            result = subprocess.run(
                ["make", "release-automation", f"PYTHON={sys.executable} -S -B {fake}"],
                cwd=root, env={**env, "FIXTURE_TEST_EXIT": "0"},
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertNotEqual(sentinel.read_text(), "OUTER EVIDENCE MUST SURVIVE\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
