#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Executable integration controls; fixture predicates are not production proofs."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import qikvrt_effect_ack as core
import qikvrt_effect_ack_wire as wire
import qikvrt_canonical_clause_audit as audit


class CanonicalClauseAuditTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"one exact proposed effect"
        self.input_hash = core.sha256_identifier(self.payload)
        self.evidence = {}
        self.validators = {}
        self.predicates = {}
        provenance = {"fixture": "explicit synthetic archive provenance"}
        provenance_hash = wire.digest(provenance)
        self.evidence[provenance_hash] = provenance
        self.artifact = {"schema": audit.SCHEMA, "input_hash": self.input_hash,
            "past": {"status": "OBSERVED", "payload": {"value": 10}, "provenance_hash": provenance_hash},
            "future": {"status": "ANTICIPATED", "payload": {"limit": 30}, "provenance_hash": provenance_hash},
            "clauses": []}
        for identifier in audit.CLAUSE_IDS:
            predicate_hash = wire.digest({"fixture_predicate": identifier})
            self.predicates[identifier] = predicate_hash
            n = int(identifier[1:])
            evidence = {"clause": identifier, "sum": 10 + n}
            ref = wire.digest(evidence)
            self.evidence[ref] = evidence
            self.artifact["clauses"].append({"id": identifier,
                "predicate_hash": predicate_hash, "evidence_hash": ref})
            def validate(storage, evidence, identifier=identifier, n=n):
                return (evidence["clause"] == identifier
                    and storage["past"]["payload"]["value"] + n == evidence["sum"]
                    and evidence["sum"] <= storage["future"]["payload"]["limit"])
            self.validators[predicate_hash] = validate
        self.bind()

    def bind(self, **changes):
        ref = wire.digest(self.artifact)
        self.evidence[ref] = copy.deepcopy(self.artifact)
        self.policy = {"policy_id": "synthetic-canonical-audit", "policy_version": 1,
            "canonical_storage": {"schema": audit.SCHEMA, "audit_hash": ref,
                "predicates": self.predicates.copy()}}
        required = {ref, self.artifact["past"]["provenance_hash"], self.artifact["future"]["provenance_hash"]}
        required.update(c["evidence_hash"] for c in self.artifact["clauses"])
        values = dict(protocol_root_id="test:canonical", input_id="one", payload=self.payload,
            transport_ack=True, origin_checked=True, context_checked=True,
            semantics_reconstructed=True, effect_anticipated=True, risk_classified=True,
            risk_level=core.RiskLevel.LOW, responsibility_assigned=True,
            responsibility_owner="test-fixture-only", connection_decision=core.ConnectionDecision.RELEASE,
            policy_allows_release=True, evidence_refs=tuple(required), required_evidence_refs=tuple(required))
        values.update(changes)
        self.record = wire.make_record(core.EffectAckRequest(**values), self.policy)

    def verify(self, **changes):
        values = dict(policy=self.policy, payload=self.payload, authenticated=True,
            latest_hash=self.record["protocol_hash"], observed_evidence=self.evidence,
            validators=self.validators)
        values.update(changes)
        return audit.verify_canonical_storage([self.record], **values)

    def test_complete_audit_reuses_original_consumer_and_wire(self):
        self.assertEqual(self.verify(), self.record)
        self.assertEqual(set(self.record), wire.FIELDS)

    def test_original_consumer_cannot_bypass_policy_selected_audit(self):
        required = {ref: self.evidence[ref] for ref in self.record["required_evidence_refs"]}
        arguments = dict(authenticated=True, latest_hash=self.record["protocol_hash"],
            policy=self.policy, required_evidence=required, observed_evidence=self.evidence)
        with self.assertRaises(wire.WireError):
            wire.verify_release([self.record], **arguments)
        self.assertEqual(wire.verify_release([self.record], **arguments,
            input_payload=self.payload, clause_validators=self.validators), self.record)

    def test_each_validator_runs_exactly_once(self):
        called = []
        validators = {}
        for ref, old in self.validators.items():
            def once(storage, evidence, ref=ref, old=old):
                called.append(ref)
                return old(storage, evidence)
            validators[ref] = once
        self.verify(validators=validators)
        self.assertEqual(called, [self.predicates[x] for x in audit.CLAUSE_IDS])

    def test_duplicate_ids_do_not_replace_missing_clauses(self):
        self.artifact["clauses"] = [copy.deepcopy(self.artifact["clauses"][0])] * 14
        self.bind()
        with self.assertRaisesRegex(audit.ClauseAuditError, "DUPLICATE"):
            self.verify()

    def test_missing_extra_and_unknown_clauses_are_rejected(self):
        original = copy.deepcopy(self.artifact)
        for mode in ("missing", "extra", "unknown"):
            with self.subTest(mode=mode):
                self.artifact = copy.deepcopy(original)
                if mode == "missing": self.artifact["clauses"].pop()
                if mode == "extra": self.artifact["clauses"].append(self.artifact["clauses"][0])
                if mode == "unknown": self.artifact["clauses"][0]["id"] = "c15"
                self.bind()
                with self.assertRaises(audit.ClauseAuditError): self.verify()

    def test_arbitrary_64_characters_are_not_a_commitment(self):
        self.artifact["clauses"][0]["evidence_hash"] = "z" * 64
        # The original core rejects the malformed required digest even before
        # a release record can reach the added evidence-profile validator.
        with self.assertRaisesRegex(ValueError, "canonical sha256 references"):
            self.bind()
            self.verify()

    def test_valid_hex_digest_without_matching_bytes_is_rejected(self):
        ref = self.artifact["clauses"][0]["evidence_hash"]
        self.evidence[ref] = {"clause": "c1", "sum": 999}
        with self.assertRaisesRegex(audit.ClauseAuditError, "DIGEST_MISMATCH"): self.verify()

    def test_each_of_fourteen_failed_predicates_prevents_release(self):
        for identifier in audit.CLAUSE_IDS:
            with self.subTest(identifier=identifier):
                validators = self.validators.copy()
                validators[self.predicates[identifier]] = lambda *_: False
                with self.assertRaisesRegex(audit.ClauseAuditError, "CLAUSE_NOT_VERIFIED:" + identifier):
                    self.verify(validators=validators)

    def test_boolean_ack_does_not_replace_predicate_evidence(self):
        self.artifact["clauses"][0]["acknowledged"] = True
        self.bind()
        with self.assertRaises(audit.ClauseAuditError): self.verify()

    def test_missing_exception_and_non_boolean_validator_fail_closed(self):
        def broken(*_): raise RuntimeError("fixture checker failure")
        for value in (None, broken, lambda *_: 1):
            with self.subTest(value=value):
                validators = self.validators.copy()
                validators[self.predicates["c1"]] = value
                with self.assertRaises(audit.ClauseAuditError): self.verify(validators=validators)

    def test_changed_past_or_future_requires_new_valid_evidence(self):
        original = copy.deepcopy(self.artifact)
        for field, key, value in (("past", "value", 11), ("future", "limit", 1)):
            with self.subTest(field=field):
                self.artifact = copy.deepcopy(original)
                self.artifact[field]["payload"][key] = value
                self.bind()
                with self.assertRaisesRegex(audit.ClauseAuditError, "CLAUSE_NOT_VERIFIED"):
                    self.verify()

    def test_epistemic_archive_types_are_distinct(self):
        self.artifact["future"]["status"] = "OBSERVED"
        self.bind()
        with self.assertRaisesRegex(audit.ClauseAuditError, "TYPED_CANONICAL_ARCHIVE"):
            self.verify()

    def test_input_bytes_and_audit_subject_are_bound(self):
        with self.assertRaisesRegex(audit.ClauseAuditError, "INPUT_BYTES_BINDING"):
            self.verify(payload=b"different proposed effect")
        self.artifact["input_hash"] = core.sha256_identifier(b"another subject")
        self.bind()
        with self.assertRaisesRegex(audit.ClauseAuditError, "AUDIT_SUBJECT_BINDING"):
            self.verify()

    def test_policy_predicates_are_complete_and_exact(self):
        self.artifact["clauses"][0]["predicate_hash"] = self.predicates["c2"]
        self.bind()
        with self.assertRaisesRegex(audit.ClauseAuditError, "PREDICATE_BINDING"):
            self.verify()
        self.predicates.pop("c14")
        self.bind()
        with self.assertRaisesRegex(audit.ClauseAuditError, "FOURTEEN_PREDICATE_POLICY"):
            self.verify()

    def test_missing_provenance_or_clause_evidence_prevents_release(self):
        for ref in (self.artifact["past"]["provenance_hash"], self.artifact["clauses"][0]["evidence_hash"]):
            evidence = dict(self.evidence); evidence.pop(ref)
            with self.subTest(ref=ref), self.assertRaises(audit.ClauseAuditError):
                self.verify(observed_evidence=evidence)

    def test_original_authentication_freshness_and_done_checks_remain_required(self):
        for changes in ({"authenticated": False}, {"latest_hash": "sha256:" + "0" * 64}):
            with self.subTest(changes=changes), self.assertRaises(wire.WireError): self.verify(**changes)
        for changes in ({"origin_checked": False}, {"policy_allows_release": False},
                        {"connection_decision": core.ConnectionDecision.BLOCK}):
            self.bind(**changes)
            with self.subTest(changes=changes), self.assertRaises(wire.WireError): self.verify()

    def test_callbacks_cannot_mutate_checked_archive_or_evidence(self):
        original = copy.deepcopy(self.evidence)
        old = self.validators[self.predicates["c1"]]
        def mutating(storage, evidence):
            passed = old(storage, evidence)
            storage["past"]["payload"]["value"] = 999
            evidence["sum"] = 999
            return passed
        self.validators[self.predicates["c1"]] = mutating
        self.verify()
        self.assertEqual(self.evidence, original)


if __name__ == "__main__":
    unittest.main()
