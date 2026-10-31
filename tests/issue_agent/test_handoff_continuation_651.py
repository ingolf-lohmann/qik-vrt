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

    def test_handoff_must_not_report_green_from_noop(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Recover unchanged issue review handoff", source)
        self.assertIn("HANDOFF_RECOVERY", source)
        self.assertIn("remote_head=", source)
        self.assertIn('"$remote_head" != "$PREVIOUS_BRANCH_HEAD"', source)
        self.assertIn("BLOCK: persisted handoff subject differs from remote branch HEAD", source)


if __name__ == "__main__":
    unittest.main()
