#!/usr/bin/env python3
"""Fail-closed Digital Twin evidence gate for the existing QIK-VRT Sites surface.

Run: python3 scripts/check_digital_twin_stall.py --self-test
     python3 scripts/check_digital_twin_stall.py evidence.json

No network, timers, writes, dispatch or implied effect acknowledgements.
"""
import argparse
import json
import sys
import unittest

EXPECTED_SITE = "appgprj_6ae30a1da6248191aac4823d1fa9c108"


def evaluate(record):
    """Return a stable state and reasons; never conflate evidence-store and UI writes."""
    reasons = []
    if record.get("github_workflow_conclusion") == "action_required":
        reasons.append("GITHUB_WORKFLOW_ADMISSION_REQUIRED")
    if record.get("site_project_id") != EXPECTED_SITE:
        reasons.append("SITE_IDENTITY_UNVERIFIED")
    if record.get("request_repeated") and not record.get("verified_ui_delta"):
        reasons.append("STALL_DETECTED")
    if record.get("editor_available") is not True:
        reasons.append("CAPABILITY_BLOCKED")
    if record.get("source_head") != record.get("readback_head") or not record.get("source_head"):
        reasons.append("EXACT_HEAD_DRIFT_OR_UNKNOWN")
    if not record.get("sites_write_receipt") or not record.get("sites_readback_receipt"):
        reasons.append("UI_PERSISTENCE_UNVERIFIED")
    elif record["sites_write_receipt"].get("digest") != record["sites_readback_receipt"].get("digest"):
        reasons.append("UI_READBACK_MISMATCH")
    if not record.get("principal_authorized"):
        reasons.append("PRINCIPAL_AUTHORIZATION_UNVERIFIED")
    if not record.get("emp_execution_receipt"):
        reasons.append("EMP_EXECUTION_UNVERIFIED")
    if not record.get("independent_eap_ack"):
        reasons.append("EAP_EFFECT_UNVERIFIED")
    if record.get("active_work_unit") and record.get("context_transition"):
        receipt = record.get("continuation_receipt")
        if not isinstance(receipt, dict):
            reasons.append("CONTEXT_HANDOFF_BLOCKED")
        else:
            required = ("work_unit_id", "head", "tree", "writer_fence", "next_idempotent_step", "evidence_sha256")
            if any(not receipt.get(k) for k in required):
                reasons.append("CONTEXT_HANDOFF_BLOCKED")
            elif receipt["head"] != record.get("source_head") or receipt.get("writer_fence") != record.get("current_writer_fence"):
                reasons.append("CONTEXT_REENTRY_REVALIDATION_REQUIRED")
    # A handoff receipt is not an execution receipt: require a distinct successor
    # observation before claiming recovery. Missing successor remains fail-closed.
    if record.get("active_work_unit") and record.get("context_transition"):
        successor = record.get("successor_execution_receipt")
        continuation = record.get("continuation_receipt")
        if not isinstance(successor, dict):
            reasons.append("SUCCESSOR_EXECUTION_UNVERIFIED")
        elif not isinstance(continuation, dict) or (
            successor.get("work_unit_id") != continuation.get("work_unit_id")
            or successor.get("source_head") != record.get("source_head")
            or successor.get("writer_fence") != record.get("current_writer_fence")
            or successor.get("step") != continuation.get("next_idempotent_step")
            or not successor.get("evidence_sha256")
        ):
            reasons.append("SUCCESSOR_EXECUTION_MISMATCH")
    # A complete specification is not a kernel proof or an implementation
    # refinement. Missing proof links are first-class, durable blockers.
    if record.get("formal_claims_in_scope"):
        for claim in record["formal_claims_in_scope"]:
            if not isinstance(claim, dict) or not claim.get("specification_id"):
                reasons.append("PROOF_TRACEABILITY_MISSING")
                continue
            if not claim.get("lean_declaration") or not claim.get("kernel_checked_exact_head"):
                reasons.append("LEAN_PROOF_UNVERIFIED")
            if not claim.get("axiom_audit_receipt"):
                reasons.append("AXIOM_AUDIT_UNVERIFIED")
            if not claim.get("implementation_refinement_receipt"):
                reasons.append("IMPLEMENTATION_REFINEMENT_UNVERIFIED")
    elif record.get("formal_proof_required"):
        reasons.append("PROOF_OBLIGATION_REGISTER_MISSING")
    if reasons:
        return {"status": "BLOCKED", "reasons": reasons}
    return {"status": "VERIFIED", "reasons": []}


def select_successor(result, record):
    """Deterministic fail-closed next step; no implied external authorization."""
    reasons = result["reasons"]
    if not reasons:
        return {"disposition": "DONE", "step": "NONE", "requires_external_admission": False}
    if "EXACT_HEAD_DRIFT_OR_UNKNOWN" in reasons or "CONTEXT_REENTRY_REVALIDATION_REQUIRED" in reasons:
        step = "REOBSERVE_EXACT_HEAD_AND_FENCE"
    elif "CAPABILITY_BLOCKED" in reasons:
        step = "REPAIR_EXISTING_SITES_ADAPTER_AND_READBACK"
    elif "UI_PERSISTENCE_UNVERIFIED" in reasons or "UI_READBACK_MISMATCH" in reasons:
        step = "VERIFY_EXISTING_SITES_WRITE_AND_INDEPENDENT_READBACK"
    elif "SUCCESSOR_EXECUTION_UNVERIFIED" in reasons or "CONTEXT_HANDOFF_BLOCKED" in reasons:
        step = "EXECUTE_FENCED_SUCCESSOR_AND_RECORD_RECEIPT"
    elif "EMP_EXECUTION_UNVERIFIED" in reasons or "EAP_EFFECT_UNVERIFIED" in reasons:
        step = "EXECUTE_ADMITTED_EMP_AND_VERIFY_EAP"
    else:
        step = "REPAIR_FIRST_UNVERIFIED_GATE"
    # GitHub workflow approval is a platform permission, never a token to invent.
    admission = record.get("github_workflow_conclusion") == "action_required"
    if admission:
        step = "AWAIT_GITHUB_MAINTAINER_ADMISSION_THEN_REOBSERVE"
    return {
        "disposition": "EXTERNAL_ADMISSION_REQUIRED" if admission else "REPAIR_REQUIRED",
        "step": step,
        "requires_external_admission": admission,
        "source_head": record.get("source_head"),
        "writer_fence": record.get("current_writer_fence"),
        "work_unit_id": record.get("work_unit_id"),
        "effect_verified": False,
    }


class RegressionTests(unittest.TestCase):
    def valid(self):
        return {
            "site_project_id": EXPECTED_SITE,
            "request_repeated": False, "verified_ui_delta": True,
            "editor_available": True, "source_head": "a" * 40,
            "readback_head": "a" * 40,
            "sites_write_receipt": {"digest": "b" * 64},
            "sites_readback_receipt": {"digest": "b" * 64},
            "principal_authorized": True,
            "emp_execution_receipt": {"id": "emp"},
            "independent_eap_ack": {"id": "eap"},
        }

    def test_blocked_requires_action_not_done(self):
        r = self.valid()
        r["editor_available"] = False
        outcome = evaluate(r)
        next_step = select_successor(outcome, r)
        self.assertEqual(next_step["disposition"], "REPAIR_REQUIRED")
        self.assertEqual(next_step["step"], "REPAIR_EXISTING_SITES_ADAPTER_AND_READBACK")
        self.assertFalse(next_step["effect_verified"])

    def test_admission_blocks_otherwise_valid_evidence(self):
        r = self.valid()
        r["github_workflow_conclusion"] = "action_required"
        self.assertIn("GITHUB_WORKFLOW_ADMISSION_REQUIRED", evaluate(r)["reasons"])
        self.assertEqual(select_successor(evaluate(r), r)["disposition"], "EXTERNAL_ADMISSION_REQUIRED")

    def test_github_admission_never_bypassed(self):
        r = self.valid()
        r.update(github_workflow_conclusion="action_required", sites_write_receipt=None)
        step = select_successor(evaluate(r), r)
        self.assertEqual(step["disposition"], "EXTERNAL_ADMISSION_REQUIRED")
        self.assertTrue(step["requires_external_admission"])
        self.assertFalse(step["effect_verified"])

    def test_head_drift_prioritized_over_adapter(self):
        r = self.valid()
        r.update(readback_head="f" * 40, editor_available=False)
        self.assertEqual(select_successor(evaluate(r), r)["step"],
                         "REOBSERVE_EXACT_HEAD_AND_FENCE")

    def test_verified_has_no_successor(self):
        r = self.valid()
        self.assertEqual(select_successor(evaluate(r), r)["disposition"], "DONE")

    def test_positive_fixture(self):
        self.assertEqual(evaluate(self.valid())["status"], "VERIFIED")

    def test_repeated_request_without_delta(self):
        r = self.valid()
        r.update(request_repeated=True, verified_ui_delta=False)
        self.assertIn("STALL_DETECTED", evaluate(r)["reasons"])

    def test_editor_missing(self):
        r = self.valid()
        r["editor_available"] = False
        self.assertIn("CAPABILITY_BLOCKED", evaluate(r)["reasons"])

    def test_d1_snapshot_not_ui_receipt(self):
        r = self.valid()
        r["d1_snapshot_sha256"] = "c" * 64
        r["sites_write_receipt"] = None
        self.assertIn("UI_PERSISTENCE_UNVERIFIED", evaluate(r)["reasons"])

    def test_principal_not_emp_eap(self):
        r = self.valid()
        r["emp_execution_receipt"] = None
        r["independent_eap_ack"] = None
        self.assertIn("EMP_EXECUTION_UNVERIFIED", evaluate(r)["reasons"])
        self.assertIn("EAP_EFFECT_UNVERIFIED", evaluate(r)["reasons"])

    def test_exact_head_drift(self):
        r = self.valid()
        r["readback_head"] = "d" * 40
        self.assertIn("EXACT_HEAD_DRIFT_OR_UNKNOWN", evaluate(r)["reasons"])

    def test_receipt_mismatch(self):
        r = self.valid()
        r["sites_readback_receipt"]["digest"] = "d" * 64
        self.assertIn("UI_READBACK_MISMATCH", evaluate(r)["reasons"])

    def test_context_switch_without_receipt(self):
        r = self.valid()
        r.update(active_work_unit=True, context_transition=True)
        self.assertIn("CONTEXT_HANDOFF_BLOCKED", evaluate(r)["reasons"])

    def test_context_switch_with_stale_fence(self):
        r = self.valid()
        r.update(active_work_unit=True, context_transition=True, current_writer_fence="new",
                 continuation_receipt={"work_unit_id": "748", "head": "a" * 40,
                                       "tree": "b" * 40, "writer_fence": "old",
                                       "next_idempotent_step": "verify", "evidence_sha256": "c" * 64})
        self.assertIn("CONTEXT_REENTRY_REVALIDATION_REQUIRED", evaluate(r)["reasons"])

    def test_context_switch_with_valid_receipt(self):
        r = self.valid()
        r.update(active_work_unit=True, context_transition=True, current_writer_fence="lease-1",
                 continuation_receipt={"work_unit_id": "748", "head": "a" * 40,
                                       "tree": "b" * 40, "writer_fence": "lease-1",
                                       "next_idempotent_step": "verify", "evidence_sha256": "c" * 64})
        self.assertIn("SUCCESSOR_EXECUTION_UNVERIFIED", evaluate(r)["reasons"])

    def test_handoff_receipt_without_successor_is_not_recovery(self):
        r = self.valid()
        r.update(active_work_unit=True, context_transition=True, current_writer_fence="lease-1",
                 continuation_receipt={"work_unit_id": "748", "head": "a" * 40,
                                       "tree": "b" * 40, "writer_fence": "lease-1",
                                       "next_idempotent_step": "verify", "evidence_sha256": "c" * 64})
        self.assertIn("SUCCESSOR_EXECUTION_UNVERIFIED", evaluate(r)["reasons"])

    def test_handoff_successor_wrong_writer_is_blocked(self):
        r = self.valid()
        r.update(active_work_unit=True, context_transition=True, current_writer_fence="lease-1",
                 continuation_receipt={"work_unit_id": "748", "head": "a" * 40,
                                       "tree": "b" * 40, "writer_fence": "lease-1",
                                       "next_idempotent_step": "verify", "evidence_sha256": "c" * 64},
                 successor_execution_receipt={"work_unit_id": "748", "source_head": "a" * 40,
                                              "writer_fence": "other", "step": "verify",
                                              "evidence_sha256": "d" * 64})
        self.assertIn("SUCCESSOR_EXECUTION_MISMATCH", evaluate(r)["reasons"])

    def test_proof_requirement_without_register_fails_closed(self):
        r = self.valid()
        r["formal_proof_required"] = True
        self.assertIn("PROOF_OBLIGATION_REGISTER_MISSING", evaluate(r)["reasons"])

    def test_kernel_evidence_without_refinement_is_insufficient(self):
        r = self.valid()
        r["formal_claims_in_scope"] = [{
            "specification_id": "QIK-AUTONOMY-SAFETY-1",
            "lean_declaration": "QIKVRT.Autonomy.noFalseCompletion",
            "kernel_checked_exact_head": "a" * 40,
            "axiom_audit_receipt": {"sha256": "b" * 64},
        }]
        self.assertIn("IMPLEMENTATION_REFINEMENT_UNVERIFIED", evaluate(r)["reasons"])

    def test_claim_without_kernel_proof_is_not_verified(self):
        r = self.valid()
        r["formal_claims_in_scope"] = [{
            "specification_id": "QIK-AUTONOMY-SAFETY-1",
            "implementation_refinement_receipt": {"sha256": "b" * 64},
        }]
        self.assertIn("LEAN_PROOF_UNVERIFIED", evaluate(r)["reasons"])
        self.assertIn("AXIOM_AUDIT_UNVERIFIED", evaluate(r)["reasons"])

    def test_wrong_site_identity(self):
        r = self.valid()
        r["site_project_id"] = "new-site"
        self.assertIn("SITE_IDENTITY_UNVERIFIED", evaluate(r)["reasons"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(RegressionTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if not args.evidence:
        parser.error("provide evidence JSON or --self-test")
    with open(args.evidence, encoding="utf-8") as f:
        record = json.load(f)\n        result = evaluate(record)
    result["successor"] = select_successor(result, record)\n    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    sys.exit(main())
