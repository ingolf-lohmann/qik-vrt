#!/usr/bin/env python3
"""Regression: unchanged source must not suppress an unverified effect handoff."""
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/issue-autonomous-processing.yml"


class HandoffContinuationContract(unittest.TestCase):
    def test_unchanged_input_does_not_suppress_handoff(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("steps.admission.outputs.execute == 'false'", source)
        self.assertIn("Recover unchanged issue review handoff", source)
        self.assertIn("--previous-ref", source)

    def test_integrity_verification_result_is_enforced(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("generated = generate(Path.cwd())", source)
        self.assertIn("verified = verify(Path.cwd())", source)
        self.assertIn("if not generated.ok or not verified.ok:", source)
        self.assertIn("BLOCK: canonical issue-branch integrity generation or verification failed", source)

    def test_remote_head_guard_rejects_stale_subject(self):
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", directory], check=True)
            subprocess.run(["git", "-C", directory, "config", "user.email", "ci@example.invalid"], check=True)
            subprocess.run(["git", "-C", directory, "config", "user.name", "CI"], check=True)
            subprocess.run(["git", "-C", directory, "commit", "--allow-empty", "-qm", "first"], check=True)
            first = subprocess.check_output(["git", "-C", directory, "rev-parse", "HEAD"], text=True).strip()
            subprocess.run(["git", "-C", directory, "commit", "--allow-empty", "-qm", "second"], check=True)
            second = subprocess.check_output(["git", "-C", directory, "rev-parse", "HEAD"], text=True).strip()
            guard = 'remote_head="$1"; PREVIOUS_BRANCH_HEAD="$2"; if [ "$remote_head" != "$PREVIOUS_BRANCH_HEAD" ]; then echo "BLOCK: persisted handoff subject differs from remote branch HEAD" >&2; exit 1; fi'
            stale = subprocess.run(["bash", "-c", guard, "guard", second, first], capture_output=True, text=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("BLOCK: persisted handoff subject differs", stale.stderr)
            matching = subprocess.run(["bash", "-c", guard, "guard", second, second], capture_output=True, text=True)
            self.assertEqual(matching.returncode, 0)

    def test_handoff_must_not_report_green_from_noop(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Recover unchanged issue review handoff", source)
        self.assertIn("HANDOFF_RECOVERY", source)
        self.assertIn("remote_head=", source)
        self.assertIn('"$remote_head" != "$PREVIOUS_BRANCH_HEAD"', source)
        self.assertIn("BLOCK: persisted handoff subject differs from remote branch HEAD", source)


if __name__ == "__main__":
    unittest.main()
