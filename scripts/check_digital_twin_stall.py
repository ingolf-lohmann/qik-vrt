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
    if reasons:
        return {"status": "BLOCKED", "reasons": reasons}
    return {"status": "VERIFIED", "reasons": []}


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
        self.assertEqual(evaluate(r)["status"], "VERIFIED")

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
        result = evaluate(json.load(f))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    sys.exit(main())
