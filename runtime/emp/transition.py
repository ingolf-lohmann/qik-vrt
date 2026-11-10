"""Fail-closed EMP transition core (stdlib-only, no effectful executor).

This module computes a next action; it never mutates a repository.
"""
from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    PROPOSED = "PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    REPAIRING = "REPAIRING"
    BLOCKED = "BLOCKED"
    VERIFIED = "VERIFIED"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class Objective:
    objective_id: str
    authorized: bool
    acceptance_observed: bool = False
    eap_verified: bool = False
    revoked: bool = False
    external_blocker: str = ""
    ci_failed: bool = False
    writer_epoch: int = 0
    event_epoch: int = 0
    previous_event_id: str = ""


@dataclass(frozen=True)
class Decision:
    state: State
    next_action: str
    reason: str


def transition(objective: Objective, event_id: str) -> Decision:
    if not objective.objective_id or not event_id:
        return Decision(State.BLOCKED, "REQUEST_VALID_INPUT", "missing identity")
    if objective.revoked:
        return Decision(State.ABORTED, "NONE", "principal revoked")
    if not objective.authorized:
        return Decision(State.PROPOSED, "REQUEST_AUTHORIZATION", "no authorization")
    if objective.writer_epoch < objective.event_epoch:
        return Decision(State.BLOCKED, "REACQUIRE_FENCED_WRITER", "stale writer")
    if event_id == objective.previous_event_id:
        return Decision(State.BLOCKED, "READBACK_ONLY", "duplicate event")
    if objective.acceptance_observed and objective.eap_verified:
        return Decision(State.VERIFIED, "NONE", "independent effect verification")
    if objective.external_blocker:
        return Decision(State.BLOCKED, "SUBSCRIBE_UNBLOCK_EVENT", objective.external_blocker)
    if objective.ci_failed:
        return Decision(State.REPAIRING, "TEMDD_DIAGNOSE", "CI failure")
    return Decision(State.AUTHORIZED, "DISPATCH_AUTHORIZED_STEP", "eligible work remains")
