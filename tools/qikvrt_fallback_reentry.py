# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure, fail-closed fallback re-entry decision; never a writer or timer."""
from __future__ import annotations

from typing import Any, Mapping


def decide_reentry(state: Mapping[str, Any]) -> dict[str, Any]:
    """Require independently evidenced admission before resuming the existing consumer.

    No claim of a productive effect, GitHub mutation, or lease acquisition is made.
    """
    required = ("continuation_required", "active_writer", "lease_valid",
                "fencing_verified", "checkpoint_verified", "exact_head_verified",
                "consumer_authorized")
    missing = [name for name in required if type(state.get(name)) is not bool]
    if missing:
        return {"decision": "HOLD", "reason": "UNKNOWN_INPUT",
                "missing": missing, "effect_ack_done": False}
    if not state["continuation_required"]:
        return {"decision": "NO_CONTINUATION", "effect_ack_done": False}
    if state["active_writer"]:
        return {"decision": "OBSERVE_EXISTING_WRITER", "effect_ack_done": False}
    if not all(state[k] for k in ("lease_valid", "fencing_verified",
                                   "checkpoint_verified", "exact_head_verified",
                                   "consumer_authorized")):
        return {"decision": "RECOVERY_REQUIRED", "reason": "ADMISSION_INCOMPLETE",
                "effect_ack_done": False}
    return {"decision": "REENTER_EXISTING_CONSUMER", "effect_ack_done": False}
