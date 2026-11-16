# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Universal transputer: a logical n-dimensional event bus, not a physical claim.

A single canonical, causally linked event stream supports multiple projections.
No polling, clocks, implicit authorization, or invented effect acknowledgements.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence


class TransputerInvariantError(ValueError):
    pass


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def project(events: Sequence[Mapping[str, object]], view: str) -> list[dict]:
    """Verify the complete causal chain before constructing any view.

    Every dimension is logical metadata. The same verified events are shared
    across chat, terminal, dashboard and repository; projections are read-only.
    """
    if view not in ("chat", "terminal", "dashboard", "repository"):
        raise TransputerInvariantError("unknown projection")
    previous = "0" * 64
    seen: set[str] = set()
    output: list[dict] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise TransputerInvariantError("event must be a mapping")
        required = ("id", "source", "subject", "state", "observed_at",
                    "head", "previous_sha256", "sha256", "evidence")
        if any(k not in event for k in required):
            raise TransputerInvariantError("missing canonical event field")
        if not isinstance(event["id"], str) or not event["id"] or event["id"] in seen:
            raise TransputerInvariantError("missing or duplicate event id")
        if event["previous_sha256"] != previous:
            raise TransputerInvariantError("causal predecessor mismatch")
        body = {k: v for k, v in event.items() if k != "sha256"}
        digest = hashlib.sha256(canonical(body)).hexdigest()
        if event["sha256"] != digest:
            raise TransputerInvariantError("event integrity mismatch")
        if event["state"] == "EFFECT_ACK_DONE" and not (
            isinstance(event["evidence"], Mapping)
            and event["evidence"].get("independent_readback") is True
        ):
            raise TransputerInvariantError("effect acknowledgement lacks independent readback")
        seen.add(event["id"])
        previous = digest
        output.append({"ordinal": index, "id": event["id"],
                       "source": event["source"], "subject": event["subject"],
                       "state": event["state"], "observed_at": event["observed_at"],
                       "head": event["head"], "evidence": event["evidence"],
                       "sha256": digest, "view": view})
    return output


def append(events: Sequence[Mapping[str, object]], event: Mapping[str, object]) -> list[dict]:
    previous = events[-1]["sha256"] if events else "0" * 64
    if "sha256" in event or "previous_sha256" in event:
        raise TransputerInvariantError("caller cannot inject chain fields")
    body = {**event, "previous_sha256": previous}
    complete = {**body, "sha256": hashlib.sha256(canonical(body)).hexdigest()}
    project([*events, complete], "repository")
    return [*map(dict, events), complete]
