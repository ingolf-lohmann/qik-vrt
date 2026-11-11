# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""REST handoff contract: accepted request retains a durable observation cursor.

Transport delivery, application acceptance and eventual effect evidence are distinct.
An accepted request is not resubmitted merely because its worker is still pending.
"""
from __future__ import annotations

import re

SHA = re.compile(r"[0-9a-f]{40}\Z")
STATES = frozenset({"ACCEPTED", "QUEUED", "RUNNING", "HOLD", "FAILED", "COMPLETED"})
TERMINAL = frozenset({"HOLD", "FAILED", "COMPLETED"})


def accepted_handoff(*, request_id: str, head: str, tree: str,
                     observation_url: str, journal_cursor: str) -> dict:
    """Return a stable application receipt, not a fabricated effect ACK."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id required")
    if not isinstance(head, str) or not SHA.fullmatch(head):
        raise ValueError("exact head required")
    if not isinstance(tree, str) or not SHA.fullmatch(tree):
        raise ValueError("exact tree required")
    if not isinstance(observation_url, str) or not observation_url.startswith(
        "https://api.github.com/repos/ingolf-lohmann/qik-vrt/"
    ) or "?" in observation_url or "#" in observation_url:
        raise ValueError("authority observation URL required")
    if not isinstance(journal_cursor, str) or not journal_cursor.strip():
        raise ValueError("nonempty journal cursor required")
    return {
        "schema": "qikvrt-rest-handoff/v1",
        "repository": "ingolf-lohmann/qik-vrt",
        "request_id": request_id,
        "head": head,
        "tree": tree,
        "state": "ACCEPTED",
        "observation_url": observation_url,
        "journal_cursor": journal_cursor,
        "effect_ack_done": False,
    }


def next_observation(receipt: object, event: object) -> dict:
    """Advance a single correlated event; preserve connection on no feedback.

    Event sequence is strictly monotone. Unknown/empty readbacks retain the
    last receipt and cursor. This function never asserts completion by itself.
    """
    if not isinstance(receipt, dict) or receipt.get("schema") != "qikvrt-rest-handoff/v1":
        raise ValueError("unrecognized receipt")
    if event is None:
        return dict(receipt)
    if not isinstance(event, dict):
        raise ValueError("invalid event")
    if any(event.get(k) != receipt.get(k) for k in ("request_id", "head", "tree")):
        raise ValueError("cross-request or cross-head event")
    if event.get("state") not in STATES:
        raise ValueError("unknown state")
    if receipt["state"] in TERMINAL:
        raise ValueError("terminal receipt cannot be overwritten")
    old = receipt.get("sequence", 0)
    seq = event.get("sequence")
    if type(seq) is not int or seq <= old:
        raise ValueError("replayed or unordered event")
    cursor = event.get("journal_cursor")
    if not isinstance(cursor, str) or not cursor.strip():
        raise ValueError("missing continuation cursor")
    if event["state"] == "COMPLETED":
        # A worker's terminal status alone is not independently verified.
        if event.get("independent_effect_ack") is not True:
            raise ValueError("completion requires independent effect ACK")
    result = dict(receipt)
    result.update(state=event["state"], sequence=seq, journal_cursor=cursor,
                  effect_ack_done=event["state"] == "COMPLETED")
    return result
