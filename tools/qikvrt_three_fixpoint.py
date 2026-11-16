"""Executable three-fixpoint reference semantics; no production admission."""
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class Transition:
    command_id: str
    principal_authorized: bool
    expected_head: str
    observed_head: str
    gates_passed: bool
    effect_id: str
    ack_command_id: str
    ack_effect_id: str
    ack_independent: bool
    ack_verified: bool


def admitted(t: Transition) -> bool:
    return (
        bool(t.command_id)
        and t.principal_authorized
        and bool(t.expected_head)
        and t.expected_head == t.observed_head
        and t.gates_passed
    )


def acknowledged(t: Transition) -> bool:
    return (
        admitted(t)
        and bool(t.effect_id)
        and t.ack_command_id == t.command_id
        and t.ack_effect_id == t.effect_id
        and t.ack_independent
        and t.ack_verified
    )


def inside(t: Transition) -> bool:
    """Only an independently acknowledged authorized operation is inside."""
    return acknowledged(t)
