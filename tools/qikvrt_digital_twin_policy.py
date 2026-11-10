"""Fail-closed Digital Twin command/effect admission policy.

This module is a reference policy, not an authentication provider or live executor.
No principal identity may be inferred from an unverified text declaration.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    OUTSIDE = "outside"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    ACKNOWLEDGED = "acknowledged"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Evidence:
    command_id: str
    principal_id: str
    authenticated_principal: bool
    scope_authorized: bool
    expected_head: str
    observed_head: str
    expected_tree: str
    observed_tree: str
    governance_admitted: bool
    execution_started: bool
    effect_id: str
    ack_command_id: str
    ack_effect_id: str
    ack_independent: bool
    ack_verified: bool


def phase(e: Evidence) -> Phase:
    """Monotonic interpretation of immutable evidence, without inventing ACKs."""
    authorized = (
        bool(e.command_id)
        and bool(e.principal_id)
        and e.authenticated_principal
        and e.scope_authorized
        and bool(e.expected_head)
        and e.expected_head == e.observed_head
        and bool(e.expected_tree)
        and e.expected_tree == e.observed_tree
        and e.governance_admitted
    )
    if not authorized:
        return Phase.BLOCKED if e.execution_started or e.ack_verified else Phase.OUTSIDE
    if e.ack_verified:
        if (
            e.execution_started
            and bool(e.effect_id)
            and e.ack_independent
            and e.ack_command_id == e.command_id
            and e.ack_effect_id == e.effect_id
        ):
            return Phase.ACKNOWLEDGED
        return Phase.BLOCKED
    if e.execution_started:
        return Phase.EXECUTING
    return Phase.AUTHORIZED


def can_claim_effect(e: Evidence) -> bool:
    return phase(e) is Phase.ACKNOWLEDGED
