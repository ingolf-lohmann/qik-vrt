#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import unittest

from tools.qikvrt_eu_ai_act_evidence_gate import audit_text


GOOD_STATUS = """
Status: CLASSIFICATION OPEN · COMPLIANCE NOT ESTABLISHED
Classification result: MORE_FACTS_REQUIRED
See docs/regulatory/AI_ACT_REQUIREMENTS_CONTROL_EVIDENCE_REGISTER.md
"""
GOOD_REGISTER = """
Classification: MORE_FACTS_REQUIRED
Gates remain OPEN and controls may be NOT_EVIDENCED.
N/A is permitted only after a reasoned, signed applicability decision.
"""


class EvidenceGateTests(unittest.TestCase):
    def test_conservative_documentary_baseline_is_not_a_conformity_claim(self) -> None:
        result = audit_text(GOOD_STATUS, GOOD_REGISTER)
        self.assertEqual(result.result, "DOCUMENTARY_GUARDS_PASS")
        self.assertIn("no legal or operational conformity conclusion", result.scope)

    def test_missing_classification_marker_blocks(self) -> None:
        result = audit_text(GOOD_STATUS.replace("MORE_FACTS_REQUIRED", "UNKNOWN"), GOOD_REGISTER)
        self.assertEqual(result.result, "BLOCKED")
        self.assertTrue(any(f.code == "STATUS_CLASSIFICATION" and f.status == "BLOCK" for f in result.findings))

    def test_missing_evidence_or_open_gate_markers_block(self) -> None:
        result = audit_text(GOOD_STATUS, "Classification: MORE_FACTS_REQUIRED")
        self.assertEqual(result.result, "BLOCKED")
        codes = {f.code for f in result.findings if f.status == "BLOCK"}
        self.assertIn("REGISTER_OPEN_APPLICABILITY_GATES", codes)
        self.assertIn("REGISTER_MISSING_EVIDENCE_DISPOSITION", codes)
        self.assertIn("REGISTER_NO_SHORTCUT_TO_NOT_APPLICABLE", codes)

    def test_unsupported_green_claim_blocks(self) -> None:
        status = GOOD_STATUS + "\nAI Act compliance is established."
        result = audit_text(status, GOOD_REGISTER)
        self.assertEqual(result.result, "BLOCKED")
        self.assertTrue(any(f.code.startswith("UNSUPPORTED_GREEN_CLAIM") for f in result.findings))

    def test_ssot_does_not_equate_documentary_guard_pass_with_compliance(self) -> None:
        result = audit_text(GOOD_STATUS, GOOD_REGISTER)
        self.assertNotEqual(result.result, "PASS")
        self.assertNotIn("conformity established", result.scope)


if __name__ == "__main__":
    unittest.main()
