# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Regression: an early API failure must retain a non-admitted receipt."""
import json
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml"


class BootstrapFailureReceiptTests(unittest.TestCase):
    def test_exact_checkout_failure_preserves_machine_readable_receipt(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        checkout = source.split("      - name: Check out exact current main through GitHub REST\n", 1)[1]
        checkout = checkout.split("\n      - name:", 1)[0]
        script = checkout.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] for line in script.splitlines() if line)
        self.assertIn("trap record_bootstrap_failure EXIT", script)
        self.assertIn("mkdir -p \"$repair_root\"", script)
        with tempfile.TemporaryDirectory() as temp:
            # The command under test is the exact workflow shell with a fake
            # gh executable: no real network calls, no production effects.
            bin_dir = pathlib.Path(temp) / "bin"
            bin_dir.mkdir()
            gh = bin_dir / "gh"
            gh.write_text("#!/bin/sh\necho 'API rate limit exceeded' >&2\nexit 1\n")
            gh.chmod(0o755)
            import os
            env = dict(os.environ, GITHUB_EVENT_NAME="workflow_run",
                       GITHUB_REPOSITORY="ingolf-lohmann/qik-vrt",
                       RUNNER_TEMP=temp, GITHUB_WORKSPACE=temp,
                       PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
            result = subprocess.run(["bash", "-e"], input=script, text=True,
                                    env=env, capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            receipt = pathlib.Path(temp) / "qikvrt-watchdog-repair-input/bootstrap-failure.json"
            self.assertTrue(receipt.is_file(), result.stderr)
            value = json.loads(receipt.read_text())
            self.assertEqual(value["stage"], "exact-main-checkout")
            self.assertEqual(value["exit_code"], result.returncode)
            self.assertIs(value["admitted"], False)
            self.assertIn("rate limit", result.stderr.lower())

    def test_artifact_is_retained_without_admitting_failed_input(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("if-no-files-found: error", source)
        self.assertIn("trap record_bootstrap_failure EXIT", source)
        self.assertIn('if [[ "${GITHUB_EVENT_NAME}" == "workflow_run" ]]', source)


if __name__ == "__main__":
    unittest.main()
