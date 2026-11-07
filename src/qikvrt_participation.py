#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""PIA-1: pure reference boundaries for participation and exchange claims.

This is a fail-closed, side-effect-free reference contract. It does not perform
authenticated host reads, writer fencing, ledger verification or productive EAP
acknowledgement. No result from this module constitutes EFFECT_ACK_DONE.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Membership(str, Enum):
    PARTICIPATING = "PARTICIPATING"
    EXCLUDED = "EXCLUDED"
    UNKNOWN = "UNKNOWN"
    HOLD = "HOLD"


@dataclass(frozen=True)
class ParticipationAssessment:
    membership: Membership
    bit: int | None
    reason: str


class ClaimStage(str, Enum):
    NO_VERIFIED_EXCHANGE = "NO_VERIFIED_EXCHANGE"
    SENT_CLAIM_ONLY = "SENT_CLAIM_ONLY"
    RECEIVED_CLAIM_ONLY = "RECEIVED_CLAIM_ONLY"
    UNVERIFIED_EFFECT_CLAIM = "UNVERIFIED_EFFECT_CLAIM"
    HOLD = "HOLD"


@dataclass(frozen=True)
class ExchangeClaimAssessment:
    stage: ClaimStage
    reason: str


def evaluate_participation(record: Mapping[str, Any] | None) -> ParticipationAssessment:
    """Classify T and s without conflating unknown, exclusion or bit zero.

    A missing/null/"UNKNOWN" T indicates unknown observation only when no bit
    is attached. Boolean T must be of exact bool type. For T=true, s must be
    of exact integer type with value 0 or 1; Python bool is not a bit here.
    """
    if not isinstance(record, Mapping):
        return ParticipationAssessment(Membership.HOLD, None, "INVALID_RECORD")
    t = record.get("participates")
    if "participates" not in record or t is None or (
        type(t) is str and t == "UNKNOWN"
    ):
        if "bit" in record:
            return ParticipationAssessment(Membership.HOLD, None, "UNBOUND_BIT")
        return ParticipationAssessment(Membership.UNKNOWN, None, "PARTICIPATION_UNKNOWN")
    if type(t) is not bool:
        return ParticipationAssessment(Membership.HOLD, None, "INVALID_PARTICIPATION_TYPE")
    if t is False:
        if "bit" in record:
            return ParticipationAssessment(Membership.HOLD, None, "BIT_ON_EXCLUDED_MEMBER")
        return ParticipationAssessment(Membership.EXCLUDED, None, "EXPLICIT_NONPARTICIPATION")
    if "bit" not in record:
        return ParticipationAssessment(Membership.HOLD, None, "MISSING_MEMBER_BIT")
    bit = record["bit"]
    if type(bit) is not int or bit not in (0, 1):
        return ParticipationAssessment(Membership.HOLD, None, "INVALID_BINARY_STATE")
    return ParticipationAssessment(Membership.PARTICIPATING, bit, "VALID_MEMBER_STATE")


def classify_exchange_claims(record: Mapping[str, Any] | None) -> ExchangeClaimAssessment:
    """Classify untrusted SENT/RECEIVED/EFFECT claims; never approve effect.

    Values must be exact bool or explicitly unknown (missing/null). A claimed
    effect is at most an unverified claim even if all preceding claims are
    present. An admitted host adapter must independently establish a fresh,
    authenticated exact-subject receipt before making a productive EAP decision.
    """
    if not isinstance(record, Mapping):
        return ExchangeClaimAssessment(ClaimStage.HOLD, "INVALID_RECORD")
    for key in ("sent", "received", "effect_ack_done"):
        if key in record and record[key] is not None and type(record[key]) is not bool:
            return ExchangeClaimAssessment(ClaimStage.HOLD, "INVALID_CLAIM_TYPE:" + key)
    sent = record.get("sent") is True
    received = record.get("received") is True
    effect = record.get("effect_ack_done") is True
    if received and not sent:
        return ExchangeClaimAssessment(ClaimStage.HOLD, "RECEIPT_WITHOUT_SEND_CLAIM")
    if effect and not received:
        return ExchangeClaimAssessment(ClaimStage.HOLD, "EFFECT_WITHOUT_RECEIPT_CLAIM")
    if effect:
        return ExchangeClaimAssessment(
            ClaimStage.UNVERIFIED_EFFECT_CLAIM, "INDEPENDENT_EFFECT_READBACK_REQUIRED"
        )
    if received:
        return ExchangeClaimAssessment(
            ClaimStage.RECEIVED_CLAIM_ONLY, "RECEIPT_NOT_AN_EFFECT_PROOF"
        )
    if sent:
        return ExchangeClaimAssessment(
            ClaimStage.SENT_CLAIM_ONLY, "SEND_NOT_A_RECEIPT"
        )
    return ExchangeClaimAssessment(
        ClaimStage.NO_VERIFIED_EXCHANGE, "NO_POSITIVE_EXCHANGE_CLAIMS"
    )
