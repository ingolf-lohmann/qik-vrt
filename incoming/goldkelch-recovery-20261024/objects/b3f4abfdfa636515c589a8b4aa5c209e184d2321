# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"


class AutonomousExactHeadVerifyWorkflowTests(unittest.TestCase):
    def test_exact_base_contract_is_available_before_validation(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        base_checkout = "- name: Check out exact base validation contract"
        validation = "- name: Validate dispatch envelope"
        contract_read = "'state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json'"
        candidate_checkout = "- name: Check out exact candidate head"

        self.assertIn(
            "ref: ${{ github.event.client_payload.base_sha }}",
            workflow,
        )
        self.assertIn(
            'test "$(git rev-parse --verify HEAD^{commit})" = "$TARGET_BASE_SHA"',
            workflow,
        )
        self.assertLess(workflow.index(base_checkout), workflow.index(validation))
        self.assertLess(workflow.index(base_checkout), workflow.index(contract_read))
        self.assertLess(workflow.index(validation), workflow.index(candidate_checkout))

    def test_canonical_status_binds_the_pr_and_base(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            'VERIFIER_STATUS_CONTEXT: "QIK-VRT autonomous exact-head verification"',
            workflow,
        )
        self.assertEqual(workflow.count('-f context="$VERIFIER_STATUS_CONTEXT"'), 2)
        self.assertIn(
            '-f description="Exact-head verified: pr=${TARGET_PR}; base=${TARGET_BASE_SHA}"',
            workflow,
        )
        self.assertIn(
            '-f description="Exact-head blocked: pr=${TARGET_PR}; base=${TARGET_BASE_SHA}"',
            workflow,
        )
        self.assertNotIn("QIKVRT autonomous exact-head verification", workflow)


if __name__ == "__main__":
    unittest.main()
