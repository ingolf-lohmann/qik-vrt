#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import unittest
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from tools.qikvrt_eu_ai_act_evidence_gate import ARTICLE_IDS, SUBJECT_FIELDS, audit_bundle, audit_text, strict_json


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

    def test_architecture_register_green_warning_terms_require_review(self):
        for claim in ("EU AI Act compliant", "fully compliant", "audit passed",
                      "conformity established", "regulatory approval achieved"):
            with self.subTest(claim=claim):
                self.assertEqual(audit_text(GOOD_STATUS + "\n" + claim, GOOD_REGISTER).result, "BLOCKED")

    def test_ssot_does_not_equate_documentary_guard_pass_with_compliance(self) -> None:
        result = audit_text(GOOD_STATUS, GOOD_REGISTER)
        self.assertNotEqual(result.result, "PASS")
        self.assertNotIn("conformity established", result.scope)


class EvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.root.joinpath("receipt.txt").write_bytes(b"original evidence\n")
        self.subject = {key: "value" for key in SUBJECT_FIELDS}
        self.subject.update(source_commit="a" * 40, source_tree="b" * 40, purpose_sha256="c" * 64)
        self.ref = {"state": "BOUND", "path": "receipt.txt",
                    "sha256": hashlib.sha256(b"original evidence\n").hexdigest()}
        self.bundle = {"schema": "qikvrt_ai_act_evidence_bundle_v1", "subject": self.subject,
                       "artifacts": [dict(self.ref, id="receipt")],
                       "controls": [{"requirement_id": key, "applicability": "OPEN",
                                     "evidence_status": "NOT_EVIDENCED", "evidence": []}
                                    for key in sorted(ARTICLE_IDS)]}
        self.now = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)

    def audit(self, bundle=None, subject=None):
        return audit_bundle(self.bundle if bundle is None else bundle, self.root,
                            self.subject if subject is None else subject, now=self.now)

    def test_honest_open_register_is_incomplete_and_never_compliant(self):
        r = self.audit()
        self.assertEqual(r["result"], "BINDINGS_INCOMPLETE")
        self.assertEqual(r["compliance_status"], "COMPLIANCE_NOT_ESTABLISHED")

    def test_changed_actual_bytes_invalidate_evidence(self):
        self.root.joinpath("receipt.txt").write_bytes(b"changed")
        self.assertEqual(self.audit()["result"], "BINDINGS_INVALID")

    def test_every_context_change_invalidates_predecessor(self):
        for field in SUBJECT_FIELDS:
            with self.subTest(field=field):
                current = dict(self.subject, **{field: "changed"})
                self.assertEqual(self.audit(subject=current)["result"], "BINDINGS_INVALID")

    def test_missing_context_field_is_invalid(self):
        expected = dict(self.subject)
        del expected["law_version"]
        self.assertEqual(self.audit(subject=expected)["result"], "BINDINGS_INVALID")

    def test_unknown_configuration_stays_open(self):
        self.subject["deployment_configuration"] = None
        self.assertTrue(any(f["code"] == "SUBJECT_deployment_configuration" and f["status"] == "OPEN"
                            for f in self.audit()["findings"]))

    def test_unresolved_original_artifact_is_not_replaced_by_a_same_named_file(self):
        self.bundle["artifacts"] = [{"id": "original", "state": "UNRESOLVED",
                                     "reason": "Original source version not supplied."}]
        self.assertEqual(self.audit()["result"], "BINDINGS_INCOMPLETE")

    def test_symlink_and_path_escape_are_rejected(self):
        self.root.joinpath("link").symlink_to(self.root / "receipt.txt")
        for path in ("link", "../receipt.txt", "/receipt.txt", "a//b", "./receipt.txt", "a\\b"):
            with self.subTest(path=path):
                self.bundle["artifacts"][0]["path"] = path
                self.assertEqual(self.audit()["result"], "BINDINGS_INVALID")

    def test_symlink_parent_is_rejected(self):
        self.root.joinpath("dirlink").symlink_to(self.root, target_is_directory=True)
        self.bundle["artifacts"][0]["path"] = "dirlink/receipt.txt"
        self.assertEqual(self.audit()["result"], "BINDINGS_INVALID")

    def test_missing_file_and_wrong_digest_are_rejected(self):
        for update in ({"path": "absent"}, {"sha256": "d" * 64}, {"sha256": None}):
            bundle = copy.deepcopy(self.bundle)
            bundle["artifacts"][0].update(update)
            self.assertEqual(self.audit(bundle)["result"], "BINDINGS_INVALID")

    def test_duplicate_artifact_and_requirement_ids_are_rejected(self):
        for field in ("artifacts", "controls"):
            bundle = copy.deepcopy(self.bundle)
            bundle[field].append(copy.deepcopy(bundle[field][0]))
            self.assertEqual(self.audit(bundle)["result"], "BINDINGS_INVALID")

    def test_oversize_evidence_is_rejected_before_reading(self):
        with self.root.joinpath("large").open("wb") as output:
            output.truncate(32 * 1024 * 1024 + 1)
        self.bundle["artifacts"][0]["path"] = "large"
        self.assertEqual(self.audit()["result"], "BINDINGS_INVALID")

    def test_not_applicable_requires_a_bound_accountable_decision(self):
        self.bundle["controls"][0]["applicability"] = "NOT_APPLICABLE"
        self.assertEqual(self.audit()["result"], "BINDINGS_INVALID")

    def test_pass_is_not_an_accepted_evidence_disposition(self):
        self.bundle["controls"][0]["evidence_status"] = "PASS"
        self.assertEqual(self.audit()["result"], "BINDINGS_INVALID")

    def receipt(self):
        return {"kind": "TEST", "subject": dict(self.subject), "artifact": dict(self.ref),
                "command": "python3 -m unittest", "exit_code": 0, "environment": "test-only",
                "observed_at": "2026-10-22T10:00:00Z", "valid_until": "2026-10-23T10:00:00Z"}

    def test_future_expired_naive_and_failed_test_receipts_are_rejected(self):
        for update in ({"observed_at": "2026-10-23T10:00:00Z"},
                       {"valid_until": "2026-10-22T11:00:00Z"},
                       {"observed_at": "2026-10-22T10:00:00"},
                       {"valid_until": None}, {"exit_code": 1}, {"exit_code": False}, {"environment": ""}):
            bundle = copy.deepcopy(self.bundle)
            receipt = self.receipt()
            receipt.update(update)
            bundle["controls"][0]["evidence"] = [receipt]
            self.assertEqual(self.audit(bundle)["result"], "BINDINGS_INVALID")

    def test_receipt_for_another_model_or_release_is_rejected(self):
        receipt = self.receipt()
        receipt["subject"]["model_configuration"] = "other-model"
        self.bundle["controls"][0]["evidence"] = [receipt]
        self.assertEqual(self.audit()["result"], "BINDINGS_INVALID")

    def test_missing_requirement_remains_open(self):
        self.bundle["controls"].pop()
        self.assertTrue(any(f["detail"].startswith("Requirement missing") for f in self.audit()["findings"]))

    def test_even_all_bound_records_never_establish_legal_conformity(self):
        for control in self.bundle["controls"]:
            control.update(applicability="APPLIES", evidence_status="EVIDENCED",
                           applicability_decision={"reviewer": "fixture-only", "rationale": "test fixture",
                                                   "record": dict(self.ref)},
                           evidence=[self.receipt()])
        result = self.audit()
        self.assertEqual(result["result"], "BINDINGS_VALID")
        self.assertEqual(result["compliance_status"], "COMPLIANCE_NOT_ESTABLISHED")

    def test_untrusted_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for text in ('{"status":"OPEN","status":"PASS"}', '{"value":NaN}', '{"value":Infinity}'):
            with self.assertRaises(ValueError):
                strict_json(text)

    def test_malformed_shapes_are_invalid_without_crashing(self):
        for value in (None, [], {}, {"schema": "wrong"}, {"schema": "qikvrt_ai_act_evidence_bundle_v1",
                      "subject": dict(self.subject), "artifacts": [None], "controls": [None]}):
            self.assertEqual(audit_bundle(value, self.root, self.subject, now=self.now)["result"], "BINDINGS_INVALID")


if __name__ == "__main__":
    unittest.main()
