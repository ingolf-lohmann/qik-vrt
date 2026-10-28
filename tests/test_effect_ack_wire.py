#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Revision-03 wire/gate controls. No deployment acceptance is inferred."""
import copy
import dataclasses
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import qikvrt_effect_ack as core
import qikvrt_effect_ack_wire as wire

POLICY = {"policy_id": "test-bounded-policy", "policy_version": 1, "required_evidence_rule": "exact evidence"}
EVIDENCE = {wire.digest({"value": "bound evidence"}): {"value": "bound evidence"}}


def request(**changes):
    values = dict(protocol_root_id="test:wire", input_id="one", payload=b"exact input", transport_ack=True,
        origin_checked=True, context_checked=True, semantics_reconstructed=True, effect_anticipated=True,
        risk_classified=True, risk_level=core.RiskLevel.LOW, responsibility_assigned=True,
        responsibility_owner="test-owner", connection_decision=core.ConnectionDecision.RELEASE,
        policy_allows_release=True, evidence_refs=tuple(EVIDENCE), required_evidence_refs=tuple(EVIDENCE))
    values.update(changes)
    return core.EffectAckRequest(**values)


class WireTests(unittest.TestCase):
    def setUp(self):
        self.record = wire.make_record(request(), POLICY)

    def release(self, record=None, **changes):
        values = dict(authenticated=True, latest_hash=self.record["protocol_hash"], policy=POLICY,
            required_evidence=EVIDENCE, observed_evidence=EVIDENCE)
        values.update(changes)
        return wire.verify_release([record or self.record], **values)

    def test_full_closed_wire_record_and_all_five_states(self):
        cases = [({}, "EFFECT_ACK_DONE"), ({"transport_ack": False, "payload": None}, "EFFECT_NACK"),
            ({"origin_checked": False}, "EFFECT_ACK_CONTINUE"),
            ({"connection_decision": "ISOLATE"}, "EFFECT_ACK_ISOLATE"),
            ({"connection_decision": "BLOCK"}, "EFFECT_ACK_BLOCK")]
        for changes, expected in cases:
            with self.subTest(expected=expected):
                r = wire.make_record(request(**changes), POLICY)
                self.assertEqual(set(r), wire.FIELDS)
                self.assertEqual(r["state"], expected)
                self.assertEqual(r["ordinary_release"], expected == "EFFECT_ACK_DONE")
                self.assertEqual(wire.verify_record(r), r)

    def test_fields_match_the_published_revision_03_normative_cddl(self):
        import re
        source = (Path(__file__).resolve().parents[1] / "external/ietf/draft-lohmann-qikvrt-effect-ack-03.txt").read_text()
        block = source.split("effect-ack-record = {", 1)[1].split("}", 1)[0]
        normative = set(re.findall(r"^\s+([a-z_]+):", block, re.MULTILINE))
        self.assertEqual(wire.FIELDS, normative)

    def test_each_done_conjunct_independently_prevents_release(self):
        changes = [{k: False} for k in ("origin_checked", "context_checked", "semantics_reconstructed",
            "effect_anticipated", "risk_classified", "responsibility_assigned", "policy_allows_release")]
        changes += [{"responsibility_owner": ""}, {"risk_level": "UNKNOWN"}, {"connection_decision": "CONTINUE"},
            {"open_questions": ["unresolved"]}, {"next_required_checks": ["check"]}, {"evidence_refs": []}]
        for values in changes:
            with self.subTest(values=values):
                r = wire.make_record(request(**values), POLICY)
                self.assertNotEqual(r["state"], "EFFECT_ACK_DONE")
                with self.assertRaises(wire.WireError):
                    self.release(r, latest_hash=r["protocol_hash"])

    def test_recomputed_forged_done_still_fails_state_rederivation(self):
        for field in ("origin_checked", "context_checked", "effect_anticipated", "policy_allows_release"):
            r = copy.deepcopy(self.record); r[field] = False; r["protocol_hash"] = wire.digest(wire.projection(r))
            with self.subTest(field=field), self.assertRaises(wire.WireError):
                wire.verify_record(r)

    def test_unknown_fields_versions_enums_and_boolean_integers(self):
        for name, value in [("unexpected", 1), ("wire_version", 2), ("wire_version", True),
                ("state", "DONE"), ("connection_decision", "ALLOW"), ("risk_level", "safe"),
                ("policy_version", True), ("protocol_version", 9007199254740992), ("evaluation_timeout_ms", 0)]:
            r = copy.deepcopy(self.record); r[name] = value
            with self.subTest(name=name, value=value), self.assertRaises((wire.WireError, TypeError)):
                wire.verify_record(r)

    def test_parser_rejects_ambiguous_or_non_ijson_inputs(self):
        for value in [b'{"x":1,"x":2}', b'{"e\\u0301":1,"\\u00e9":2}', b'{"x":1.0}', b'{"x":NaN}',
                b'{"x":9007199254740992}', b'{"x":"\\ud800"}', b'\xef\xbb\xbf{}', b'[]']:
            with self.subTest(value=value), self.assertRaises(wire.WireError):
                wire.parse(value)

    def test_nfc_set_order_and_jcs_utf16_member_order(self):
        self.assertEqual(wire.canonical({"\ue000": 1, "\U00010000": 2}), '{"\U00010000":2,"\ue000":1}'.encode())
        r = wire.make_record(request(reasons=["e\u0301", "é", "", "z"]), POLICY)
        self.assertEqual(r["reasons"], sorted(set(r["reasons"])))
        self.assertIn("é", r["reasons"])
        self.assertNotIn("e\u0301", r["reasons"])

    def test_timestamp_is_not_the_hash_or_freshness_anchor(self):
        r = copy.deepcopy(self.record); r["created_utc"] = "2020-01-01T00:00:00Z"
        self.assertEqual(wire.verify_record(r)["protocol_hash"], self.record["protocol_hash"])
        with self.assertRaises(wire.WireError):
            self.release(r, latest_hash="sha256:" + "0" * 64)

    def test_authenticated_policy_evidence_and_latest_anchor_required(self):
        self.assertEqual(self.release(), self.record)
        changes = [{"authenticated": False}, {"latest_hash": "sha256:" + "0" * 64},
            {"policy": {**POLICY, "policy_version": 2}}, {"required_evidence": {}},
            {"observed_evidence": {}}, {"observed_evidence": {next(iter(EVIDENCE)): {"value": "tampered"}}}]
        for values in changes:
            with self.subTest(values=values), self.assertRaises(wire.WireError):
                self.release(**values)

    def test_contiguous_chain_and_stale_done_revocation(self):
        successor = wire.make_record(request(connection_decision="BLOCK"), POLICY, previous_chain=[self.record])
        self.assertEqual(successor["protocol_version"], 2)
        self.assertEqual(successor["previous_protocol_hash"], self.record["protocol_hash"])
        self.assertEqual(wire.verify_chain([self.record, successor])[-1], successor)
        with self.assertRaises(wire.WireError):
            self.release(latest_hash=successor["protocol_hash"])
        bad = copy.deepcopy(successor); bad["previous_protocol_hash"] = "sha256:" + "0" * 64
        bad["protocol_hash"] = wire.digest(wire.projection(bad))
        with self.assertRaises(wire.WireError):
            wire.verify_chain([self.record, bad])

    def test_repeated_identical_evaluation_reuses_original_bytes(self):
        self.assertEqual(wire.make_record(request(), POLICY, previous_chain=[self.record]), self.record)

    def test_corrupt_predecessor_is_an_incident_not_a_trusted_successor(self):
        bad = copy.deepcopy(self.record); bad["protocol_hash"] = "sha256:" + "0" * 64
        incident = wire.make_record(request(), POLICY, previous_chain=[bad])
        self.assertEqual(incident["state"], "EFFECT_ACK_BLOCK")
        self.assertEqual(incident["protocol_version"], 1)
        self.assertIsNone(incident["previous_protocol_hash"])
        self.assertTrue(incident["protocol_root_id"].startswith("qikvrt:incident:"))

    def test_timeout_has_priority_and_explicit_continuation(self):
        ticks = iter(range(0, 100000000, 2000000))
        with mock.patch.object(wire.time, "monotonic_ns", side_effect=lambda: next(ticks)):
            r = wire.make_record(request(transport_ack=False), POLICY, timeout_ms=1)
        # Missing receipt plus timeout selects BLOCK before NACK, retaining
        # the real payload hash rather than inventing one for absent bytes.
        self.assertEqual(r["state"], "EFFECT_ACK_BLOCK")
        self.assertTrue(r["deadline_exceeded"])
        self.assertTrue(r["next_required_checks"])

    def test_unrepresentable_absent_input_timeout_fails_closed(self):
        ticks = iter(range(0, 100000000, 2000000))
        with mock.patch.object(wire.time, "monotonic_ns", side_effect=lambda: next(ticks)):
            with self.assertRaises(wire.WireError):
                wire.make_record(request(transport_ack=False, payload=None), POLICY, timeout_ms=1)


if __name__ == "__main__":
    unittest.main()
