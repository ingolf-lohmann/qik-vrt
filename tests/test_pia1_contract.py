#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""PIA-1 fail-closed conformance tests; no network, host or runtime effects."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qikvrt_participation import (  # noqa: E402
    ClaimStage,
    Membership,
    classify_exchange_claims,
    evaluate_participation,
)


class ParticipationConformance(unittest.TestCase):
    def test_zero_is_a_valid_participant(self):
        assessment = evaluate_participation({"participates": True, "bit": 0})
        self.assertEqual(assessment.membership, Membership.PARTICIPATING)
        self.assertEqual(assessment.bit, 0)

    def test_one_is_a_valid_participant(self):
        assessment = evaluate_participation({"participates": True, "bit": 1})
        self.assertEqual(assessment.membership, Membership.PARTICIPATING)
        self.assertEqual(assessment.bit, 1)

    def test_false_is_exclusion_not_binary_zero(self):
        assessment = evaluate_participation({"participates": False})
        self.assertEqual(assessment.membership, Membership.EXCLUDED)
        self.assertIsNone(assessment.bit)

    def test_null_missing_and_explicit_unknown_remain_unknown(self):
        for record in ({}, {"participates": None}, {"participates": "UNKNOWN"}):
            with self.subTest(record=record):
                assessment = evaluate_participation(record)
                self.assertEqual(assessment.membership, Membership.UNKNOWN)
                self.assertIsNone(assessment.bit)

    def test_unbound_bit_is_never_admitted(self):
        for record in (
            {"bit": 0},
            {"participates": None, "bit": 1},
            {"participates": "UNKNOWN", "bit": 0},
            {"participates": False, "bit": 0},
            {"participates": True},
        ):
            with self.subTest(record=record):
                self.assertEqual(evaluate_participation(record).membership, Membership.HOLD)

    def test_binary_values_require_exact_integer_type(self):
        for bad in (False, True, "0", "1", 2, -1, 1.0, None, [], {}):
            with self.subTest(bit=bad):
                self.assertEqual(
                    evaluate_participation({"participates": True, "bit": bad}).membership,
                    Membership.HOLD,
                )

    def test_participation_predicate_requires_exact_boolean_type(self):
        for bad in (0, 1, "true", "false", [], {}, 1.0):
            with self.subTest(participates=bad):
                self.assertEqual(
                    evaluate_participation({"participates": bad}).membership,
                    Membership.HOLD,
                )

    def test_invalid_record_does_not_default_to_exclusion(self):
        self.assertEqual(evaluate_participation(None).membership, Membership.HOLD)


class ExchangeClaimBoundary(unittest.TestCase):
    def test_sent_does_not_imply_received(self):
        result = classify_exchange_claims({"sent": True})
        self.assertEqual(result.stage, ClaimStage.SENT_CLAIM_ONLY)

    def test_received_requires_prior_sent_claim(self):
        result = classify_exchange_claims({"sent": False, "received": True})
        self.assertEqual(result.stage, ClaimStage.HOLD)

    def test_received_claim_is_not_effect(self):
        result = classify_exchange_claims({"sent": True, "received": True})
        self.assertEqual(result.stage, ClaimStage.RECEIVED_CLAIM_ONLY)

    def test_effect_claim_is_not_verified_effect_even_with_prior_claims(self):
        result = classify_exchange_claims(
            {"sent": True, "received": True, "effect_ack_done": True}
        )
        self.assertEqual(result.stage, ClaimStage.UNVERIFIED_EFFECT_CLAIM)
        self.assertNotIn("VERIFIED", result.stage.name.replace("UNVERIFIED", ""))

    def test_effect_claim_without_receipt_chain_holds(self):
        for record in (
            {"effect_ack_done": True},
            {"sent": True, "effect_ack_done": True},
            {"sent": False, "received": True, "effect_ack_done": True},
        ):
            with self.subTest(record=record):
                self.assertEqual(classify_exchange_claims(record).stage, ClaimStage.HOLD)

    def test_python_zero_false_aliasing_cannot_elevate_claim(self):
        for record in (
            {"sent": 1, "received": True},
            {"sent": True, "received": 0},
            {"sent": True, "received": True, "effect_ack_done": 1},
        ):
            with self.subTest(record=record):
                self.assertEqual(classify_exchange_claims(record).stage, ClaimStage.HOLD)

    def test_untrusted_payload_replay_does_not_verify_effect(self):
        record = {
            "sent": True,
            "received": True,
            "effect_ack_done": True,
            "payload": {"effect_ack_done": True},
            "replay": True,
            "duplicate": True,
        }
        self.assertEqual(
            classify_exchange_claims(record).stage, ClaimStage.UNVERIFIED_EFFECT_CLAIM
        )

    def test_claim_stage_never_returns_productive_done(self):
        for record in (
            {}, {"sent": True}, {"sent": True, "received": True},
            {"sent": True, "received": True, "effect_ack_done": True},
        ):
            with self.subTest(record=record):
                self.assertNotEqual(
                    classify_exchange_claims(record).stage.value, "EFFECT_ACK_DONE"
                )


if __name__ == "__main__":
    unittest.main()
