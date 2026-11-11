# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure, fail-closed priority queue policy for the existing continuation worker.

No network calls, timers, mutable global state or effect acknowledgement.
The existing controller owns claims, persistence, execution and readback.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

PRIORITIES = ("P0", "P1", "P2", "P3", "P4")
TERMINAL = frozenset({"VERIFIED", "CANCELLED"})
ACTIVE = frozenset({"QUEUED", "HOLD", "CLAIMED", "RUNNING", "VERIFIED", "CANCELLED"})


class QueueInvariantError(ValueError):
    """Invalid queue snapshot: no action may be selected."""


def validate(units: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    by_id: dict[str, Mapping[str, Any]] = {}
    keys: set[str] = set()
    for unit in units:
        ident, key = unit.get("id"), unit.get("dedupe_key")
        if not isinstance(ident, str) or not ident or ident in by_id:
            raise QueueInvariantError("duplicate or missing work-unit identity")
        if not isinstance(key, str) or not key or key in keys:
            raise QueueInvariantError("duplicate or missing dedupe key")
        if unit.get("priority") not in PRIORITIES or unit.get("state") not in ACTIVE:
            raise QueueInvariantError("invalid priority or state")
        if type(unit.get("last_attempt", 0)) is not int or unit.get("last_attempt", 0) < 0:
            raise QueueInvariantError("invalid attempt ordinal")
        if (not isinstance(unit.get("dependencies", []), list)
                or any(not isinstance(dep, str) for dep in unit.get("dependencies", []))
                or len(set(unit.get("dependencies", []))) != len(unit.get("dependencies", []))):
            raise QueueInvariantError("invalid dependencies")
        by_id[ident] = unit
        keys.add(key)
    for ident, unit in by_id.items():
        for dep in unit.get("dependencies", []):
            if dep not in by_id or dep == ident:
                raise QueueInvariantError("missing or self dependency")
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(ident: str) -> None:
        if ident in visiting:
            raise QueueInvariantError("dependency cycle")
        if ident in visited:
            return
        visiting.add(ident)
        for dep in by_id[ident].get("dependencies", []):
            visit(dep)
        visiting.remove(ident)
        visited.add(ident)
    for ident in by_id:
        visit(ident)
    return by_id


def select_next(units: Sequence[Mapping[str, Any]], *, writer_available: bool,
                exact_head: str | None) -> Mapping[str, Any] | None:
    """Choose one admissible unit; return None rather than infer permission.

    An active writer fences *all* new claims. A dependency is satisfied only
    by VERIFIED, never by HOLD, a successful test alone, or a claimed effect.
    """
    by_id = validate(units)
    if not writer_available or not exact_head:
        return None
    candidates = [
        u for u in units
        if u["state"] == "QUEUED"
        and u.get("head") == exact_head
        and all(by_id[d]["state"] == "VERIFIED" for d in u.get("dependencies", []))
    ]
    return min(candidates, key=lambda u: (
        PRIORITIES.index(u["priority"]), u.get("last_attempt", 0), u["id"]
    )) if candidates else None


def consolidate(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Losslessly dedupe identical event IDs; reject divergent replay.

    Return immutable-in-spirit source event records in first-seen order.
    The caller must persist original evidence and its content digest.
    """
    seen: dict[str, dict[str, Any]] = {}
    for event in events:
        ident = event.get("event_id")
        if not isinstance(ident, str) or not ident:
            raise QueueInvariantError("missing event identity")
        copy = dict(event)
        if ident in seen and seen[ident] != copy:
            raise QueueInvariantError("conflicting event replay")
        seen.setdefault(ident, copy)
    return list(seen.values())
