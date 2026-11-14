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

def completion_receipt_admitted(receipt: object, *, head: str, tree: str) -> bool:
    """Bind a completion receipt to an exact Git object pair, not just booleans.

    A mutable 'passed' flag or a successful CI on another commit is insufficient.
    """
    import re
    if not isinstance(receipt, dict) or type(head) is not str or type(tree) is not str:
        return False
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        return False
    if receipt.get("schema") != "qikvrt-completion-admission/v1":
        return False
    if receipt.get("repository") != "ingolf-lohmann/qik-vrt":
        return False
    if receipt.get("head") != head or receipt.get("tree") != tree:
        return False
    if receipt.get("effect_ack_done") is not True:
        return False
    return completion_admitted(receipt.get("evidence"))
