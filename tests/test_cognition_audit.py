#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Isolated documentary fixtures, not a live behavioral certification."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from src.qikvrt_cognition_audit import (
    CRITERIA, MAX_DOCUMENT, SCHEMA, assess_cognition_audit, bind_cognition_audit,
)
from src.qikvrt_effect_ack import (
    ConnectionDecision, EffectAckRequest, EffectState, RiskLevel, effect_ack_sync,
    verify_protocol,
)

ROOT = Path(__file__).resolve().parents[1]


class CognitionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = int(time.time())
        self.subject = {"system_id": "fixture-system", "version": "fixture-v1",
                        "configuration_sha256": "a" * 64, "purpose": "isolated test",
                        "actor_id": "fixture-artificial-actor"}
        content = "Human: Pruefe den Einwand.\nMachine: Der Fehler ist korrigiert.\nRetest: 2 + 2 = 4.\n"
        self.data = content.encode()
        (self.root / "transcript.txt").write_bytes(self.data)
        self.audit = {
            "schema": SCHEMA, "audit_id": "fixture-audit-1", "subject": self.subject,
            "window": {"start_utc": self.now - 40, "end_utc": self.now - 10},
            "valid_until_utc": self.now + 100,
            "review": {"reviewer_id": "fixture-human", "kind": "human",
                       "reviewed_utc": self.now - 5, "decision": "PASS",
                       "rationale": "Synthetic human-review binding for gate tests only."},
            "transcripts": [{"path": "transcript.txt",
                             "sha256": hashlib.sha256(self.data).hexdigest()}],
            "cases": [], "predecessor": None, "corrections": [], "open_findings": [],
        }
        for i, criterion in enumerate(sorted(CRITERIA)):
            evidence = [self.excerpt("human_statement", "Human: Pruefe den Einwand."),
                        self.excerpt("machine_response", "Machine: Der Fehler ist korrigiert.")]
            if criterion == "HCA-05":
                evidence.extend(self.excerpt(role, quote) for role, quote in (
                    ("prior_error", "Human: Pruefe den Einwand."),
                    ("correction", "Machine: Der Fehler ist korrigiert."),
                    ("retest", "Retest: 2 + 2 = 4.")))
            self.audit["cases"].append({
                "case_id": f"fixture-{i}", "criterion": criterion,
                "session_id": f"session-{i % 2}", "observed_utc": self.now - 30 + i,
                "result": "PASS", "rationale": "Synthetic expected judgment, no semantic inference.",
                "evidence": evidence})

    def excerpt(self, role, quote):
        start = self.data.index(quote.encode())
        return {"artifact": "transcript.txt", "role": role, "start_byte": start,
                "end_byte": start + len(quote.encode()), "quote": quote}

    def raw(self):
        return json.dumps(self.audit, ensure_ascii=False).encode()

    def assess(self, *, trusted=True, raw=None, **overrides):
        raw = self.raw() if raw is None else raw
        kwargs = {"evidence_root": self.root, "expected_subject": self.subject,
                  "now": self.now, "trusted_review_sha256":
                  [hashlib.sha256(raw).hexdigest()] if trusted else []}
        kwargs.update(overrides)
        return assess_cognition_audit(raw, **kwargs)

    def unknown(self, reason):
        result = self.assess()
        self.assertEqual(result.outcome, "UNVERIFIED")
        self.assertIn(reason, result.reasons)
        self.assertFalse(result.admissible)

    def request(self, **changes):
        request = EffectAckRequest(
            protocol_root_id="fixture-root", input_id="fixture-input", payload=b"fixture",
            transport_ack=True, origin_checked=True, context_checked=True,
            semantics_reconstructed=True, effect_anticipated=True, risk_classified=True,
            risk_level=RiskLevel.LOW, responsibility_assigned=True,
            responsibility_owner="fixture-owner", connection_decision=ConnectionDecision.RELEASE,
            policy_allows_release=True)
        return replace(request, **changes)

    def bind(self, request, *, trusted=True):
        raw = self.raw()
        return bind_cognition_audit(
            request, raw, evidence_root=self.root, expected_subject=self.subject, now=self.now,
            trusted_review_sha256=[hashlib.sha256(raw).hexdigest()] if trusted else [])

    def test_complete_pinned_fixture_passes_only_scoped_documentary_gate(self):
        self.assertEqual(self.assess().outcome, "VERIFIED")

    def test_self_declared_human_and_all_pass_are_insufficient(self):
        self.assertEqual(self.assess(trusted=False).outcome, "UNVERIFIED")

    def test_changed_approved_bytes_do_not_inherit_trust(self):
        pin = hashlib.sha256(self.raw()).hexdigest()
        self.audit["review"]["rationale"] = "changed"
        self.assertEqual(self.assess(trusted_review_sha256=[pin]).outcome, "UNVERIFIED")

    def test_an_authenticated_violation_cannot_be_averaged_away(self):
        self.audit["cases"][0]["result"] = "FAIL"
        self.assertEqual(self.assess().outcome, "FAILED")

    def test_untrusted_failure_is_not_a_verified_target_failure(self):
        self.audit["cases"][0]["result"] = "FAIL"
        self.assertEqual(self.assess(trusted=False).outcome, "UNVERIFIED")

    def test_human_rejection_denies_otherwise_passing_fixture(self):
        self.audit["review"]["decision"] = "FAIL"
        self.assertEqual(self.assess().outcome, "FAILED")

    def test_unknown_case_remains_unverified(self):
        self.audit["cases"][0]["result"] = "UNKNOWN"
        self.assertEqual(self.assess().outcome, "UNVERIFIED")

    def test_unknown_human_review_remains_unverified(self):
        self.audit["review"]["decision"] = "UNKNOWN"
        self.assertEqual(self.assess().outcome, "UNVERIFIED")

    def test_missing_criterion_is_not_pass(self):
        self.audit["cases"][0]["criterion"] = "HCA-02"
        self.unknown("CRITERIA_OR_LONGITUDINAL_SAMPLE_INCOMPLETE")

    def test_single_session_is_not_longitudinal_proof(self):
        for case in self.audit["cases"]:
            case["session_id"] = "one-session"
        self.unknown("CRITERIA_OR_LONGITUDINAL_SAMPLE_INCOMPLETE")

    def test_same_time_with_renamed_sessions_is_not_a_temporal_sample(self):
        for case in self.audit["cases"]:
            case["observed_utc"] = self.now - 20
        self.unknown("CRITERIA_OR_LONGITUDINAL_SAMPLE_INCOMPLETE")

    def test_correction_promise_without_actual_retest_is_insufficient(self):
        case = next(c for c in self.audit["cases"] if c["criterion"] == "HCA-05")
        case["evidence"] = case["evidence"][:2]
        self.unknown("ACTUAL_CORRECTION_AND_RETEST_REQUIRED")

    def test_separate_human_machine_evidence_is_required(self):
        self.audit["cases"][0]["evidence"][0]["role"] = "machine_response"
        self.unknown("HUMAN_AND_MACHINE_EVIDENCE_REQUIRED")

    def test_fabricated_quote_rejected(self):
        self.audit["cases"][0]["evidence"][0]["quote"] = "fabricated"
        self.unknown("EXCERPT_BYTES_MISMATCH")

    def test_changed_original_transcript_rejected(self):
        (self.root / "transcript.txt").write_bytes(self.data + b"changed")
        self.unknown("ARTIFACT_DIGEST_MISMATCH")

    def test_missing_readback_is_unknown_not_target_failure(self):
        (self.root / "transcript.txt").unlink()
        self.unknown("ARTIFACT_UNAVAILABLE")

    def test_stale_review_rejected(self):
        self.audit["valid_until_utc"] = self.now
        self.unknown("AUDIT_STALE_OR_WINDOW_INVALID")

    def test_future_observation_rejected(self):
        self.audit["window"]["end_utc"] = self.now + 1
        self.unknown("AUDIT_STALE_OR_WINDOW_INVALID")

    def test_validity_cannot_be_unbounded(self):
        self.audit["valid_until_utc"] = self.now + 31 * 86400
        self.unknown("AUDIT_STALE_OR_WINDOW_INVALID")

    def test_changed_system_purpose_actor_version_or_configuration_denies(self):
        for field in self.subject:
            with self.subTest(field=field):
                subject = self.subject | {field: "b" * 64 if field.endswith("sha256") else "changed"}
                self.assertIn("AUDIT_SUBJECT_CHANGED", self.assess(expected_subject=subject).reasons)

    def test_unknown_version_cannot_be_admitted(self):
        self.audit["subject"] = self.subject | {"version": "UNKNOWN"}
        self.unknown("SUBJECT_UNRESOLVED")

    def test_self_review_is_not_accepted(self):
        self.audit["review"]["reviewer_id"] = self.subject["actor_id"]
        self.unknown("HUMAN_REVIEW_INVALID")

    def test_boolean_clock_rejected(self):
        self.audit["window"]["start_utc"] = True
        self.unknown("AUDIT_STALE_OR_WINDOW_INVALID")

    def test_duplicate_json_keys_rejected(self):
        raw = self.raw().replace(b'{"schema":', b'{"audit_id":"shadow","schema":', 1)
        self.assertIn("DUPLICATE_JSON_KEY", self.assess(raw=raw).reasons)

    def test_nonfinite_json_rejected(self):
        self.assertIn("NONFINITE_JSON_VALUE", self.assess(raw=b'{"x":NaN}').reasons)

    def test_oversized_audit_rejected(self):
        self.assertIn("AUDIT_SIZE_INVALID", self.assess(raw=b" " * (MAX_DOCUMENT + 1)).reasons)

    def test_undeclared_fields_rejected(self):
        self.audit["self_certified"] = True
        self.unknown("AUDIT_FIELDS_INVALID")

    def test_path_traversal_rejected(self):
        self.audit["transcripts"][0]["path"] = "../escape.txt"
        self.unknown("ARTIFACT_PATH_INVALID")

    def test_symlink_evidence_rejected(self):
        (self.root / "link.txt").symlink_to(self.root / "transcript.txt")
        self.audit["transcripts"][0]["path"] = "link.txt"
        self.unknown("ARTIFACT_SYMLINK_FORBIDDEN")

    def test_check_failure_remains_unverified(self):
        with patch("pathlib.Path.open", side_effect=OSError("fixture read failure")):
            result = self.assess()
        self.assertEqual(result.outcome, "UNVERIFIED")

    def test_unresolved_findings_deny_admission(self):
        self.audit["open_findings"] = ["finding-1"]
        self.assertEqual(self.assess().outcome, "FAILED")

    def predecessor(self):
        previous = copy.deepcopy(self.audit)
        previous["audit_id"] = "fixture-predecessor"
        previous["open_findings"] = ["fixture-0"]
        previous["cases"][0]["result"] = "FAIL"
        data = json.dumps(previous).encode()
        (self.root / "prior.json").write_bytes(data)
        self.audit["predecessor"] = {"path": "prior.json", "sha256": hashlib.sha256(data).hexdigest()}

    def test_predecessor_findings_cannot_be_silently_dropped(self):
        self.predecessor()
        self.unknown("PREDECESSOR_FINDING_DROPPED")

    def test_correction_preserves_old_failure_and_requires_retest(self):
        self.predecessor()
        self.audit["corrections"] = [{
            "finding_id": "fixture-0", "before": self.excerpt("prior_error", "Human: Pruefe den Einwand."),
            "after": self.excerpt("correction", "Machine: Der Fehler ist korrigiert."),
            "retest": self.excerpt("retest", "Retest: 2 + 2 = 4.")}]
        self.assertEqual(self.assess().outcome, "VERIFIED")
        self.assertEqual(json.loads((self.root / "prior.json").read_text())["cases"][0]["result"], "FAIL")

    def test_failed_prior_case_survives_omission_from_prior_findings_list(self):
        self.predecessor()
        prior_path = self.root / "prior.json"
        previous = json.loads(prior_path.read_text())
        previous["open_findings"] = []
        data = json.dumps(previous).encode()
        prior_path.write_bytes(data)
        self.audit["predecessor"]["sha256"] = hashlib.sha256(data).hexdigest()
        self.unknown("PREDECESSOR_FINDING_DROPPED")

    def test_deep_invalid_json_is_unverified_checker_failure(self):
        result = self.assess(raw=b'{"x":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}')
        self.assertEqual(result.outcome, "UNVERIFIED")

    def test_valid_audit_cannot_override_existing_policy_denial(self):
        bounded, _ = self.bind(self.request(policy_allows_release=False))
        self.assertFalse(bounded.policy_allows_release)
        self.assertFalse(effect_ack_sync(bounded).ordinary_release)

    def test_unverified_audit_denies_an_otherwise_release_ready_request(self):
        request = self.request()
        self.assertTrue(effect_ack_sync(request).ordinary_release)
        bounded, _ = self.bind(request, trusted=False)
        result = effect_ack_sync(bounded)
        self.assertEqual(result.state, EffectState.EFFECT_ACK_CONTINUE)
        self.assertFalse(result.ordinary_release)
        verify_protocol(result.protocol)

    def test_authenticated_violation_blocks_existing_eap(self):
        self.audit["cases"][0]["result"] = "FAIL"
        bounded, _ = self.bind(self.request())
        result = effect_ack_sync(bounded)
        self.assertEqual(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertFalse(result.ordinary_release)
        verify_protocol(result.protocol)

    def test_verified_audit_does_not_bypass_other_eap_gates(self):
        bounded, _ = self.bind(self.request(origin_checked=False))
        self.assertFalse(effect_ack_sync(bounded).ordinary_release)

    def test_verified_fixture_joins_eap_without_extra_wire_state(self):
        bounded, audit = self.bind(self.request())
        result = effect_ack_sync(bounded)
        self.assertTrue(result.ordinary_release)
        self.assertIn("sha256:" + audit.audit_sha256, result.protocol.evidence_refs)
        self.assertEqual(len(EffectState), 5)
        verify_protocol(result.protocol)

    def test_existing_block_and_isolation_are_preserved(self):
        for decision in (ConnectionDecision.BLOCK, ConnectionDecision.ISOLATE):
            with self.subTest(decision=decision):
                bounded, _ = self.bind(self.request(connection_decision=decision))
                self.assertEqual(bounded.connection_decision, decision)
                self.assertFalse(effect_ack_sync(bounded).ordinary_release)

    def test_cli_without_authenticated_review_exits_two(self):
        audit = self.root / "audit.json"
        subject = self.root / "subject.json"
        audit.write_bytes(self.raw())
        subject.write_text(json.dumps(self.subject))
        proc = subprocess.run([sys.executable, "-B", str(ROOT / "tools/ai_handoff.py"),
                               "--cognition-audit", str(audit), "--audit-evidence-root", str(self.root),
                               "--audit-subject", str(subject)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["outcome"], "UNVERIFIED")
        self.assertFalse(result["live_effect_verified"])

    def test_policy_and_entrypoints_anchor_all_seven_criteria(self):
        policy = json.loads((ROOT / "policy/HUMAN_COGNITION_ADMISSIBILITY_V1.json").read_text())
        self.assertEqual({c["id"] for c in policy["criteria"]}, CRITERIA)
        ctx = json.loads((ROOT / "AI_CONTEXT.json").read_text())
        for path in (policy["human_contract"], policy["form"], "policy/HUMAN_COGNITION_ADMISSIBILITY_V1.json"):
            self.assertIn(path, ctx["required_read_order"])
        self.assertIn("HUMAN_COGNITION_ADMISSIBILITY", (ROOT / "AI").read_text())
        self.assertIn("HUMAN_COGNITION_ADMISSIBILITY", (ROOT / "AGENTS.md").read_text())


if __name__ == "__main__":
    unittest.main()
