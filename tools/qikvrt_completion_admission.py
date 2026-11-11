# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed QIK-VRT completion admission predicate.

A positive completion claim requires independent evidence for every gate.
This module cannot replace original-host readback or governance review.
"""
from __future__ import annotations

REQUIRED_GATES = (
    "exact_subject",
    "exact_head",
    "exact_tree",
    "tests_pass",
    "integrity_pass",
    "governance_pass",
    "independent_review_pass",
    "independent_effect_readback_pass",
    "all_required_dod_gates_pass",
)


def completion_admitted(evidence: object) -> bool:
    """Reject absent, unknown, asserted-only, stale or non-boolean evidence."""
    if not isinstance(evidence, dict):
        return False
    return all(evidence.get(gate) is True for gate in REQUIRED_GATES)


def completion_disposition(evidence: object) -> str:
    return "ADMITTED" if completion_admitted(evidence) else "HOLD"
