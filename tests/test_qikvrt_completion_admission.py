# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Negative admission tests: analysis/commit/PR cannot mean completion."""
import unittest
from tools.qikvrt_completion_admission import (
    REQUIRED_GATES, completion_admitted, completion_disposition,
)


class CompletionAdmissionTests(unittest.TestCase):
    def test_only_all_independently_confirmed_gates_admit(self):
        complete = {gate: True for gate in REQUIRED_GATES}
        self.assertTrue(completion_admitted(complete))
        self.assertEqual(completion_disposition(complete), "ADMITTED")
        for gate in REQUIRED_GATES:
            for invalid in (None, False, "true", "asserted", "unknown", 1):
                evidence = dict(complete)
                evidence[gate] = invalid
                self.assertFalse(completion_admitted(evidence), (gate, invalid))
                self.assertEqual(completion_disposition(evidence), "HOLD")

    def test_no_report_or_commit_substitutes_for_evidence(self):
        for evidence in (None, {}, [], {"analysis": "complete"},
                         {"commit": "abc", "pr": 743, "status": "done"}):
            self.assertFalse(completion_admitted(evidence))


if __name__ == "__main__":
    unittest.main()
