# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Canonical, lossless continuation journal: serialization is not effect admission."""
from __future__ import annotations
import hashlib
import json
from typing import Any

SCHEMA = "qikvrt_continuation_journal_v1"


class JournalError(ValueError):
    pass


def encode(state: dict[str, Any]) -> bytes:
    if not isinstance(state, dict) or state.get("schema") != SCHEMA:
        raise JournalError("unsupported journal schema")
    if not isinstance(state.get("events"), list) or not isinstance(state.get("units"), list):
        raise JournalError("missing journal collections")
    try:
        data = json.dumps(state, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise JournalError("unserializable journal") from exc
    if json.loads(data) != state:
        raise JournalError("non-roundtrippable journal value")
    return data


def decode(data: bytes) -> dict[str, Any]:
    if not isinstance(data, bytes) or len(data) > 8 * 1024 * 1024:
        raise JournalError("invalid journal size or type")
    try:
        def unique_pairs(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise JournalError("duplicate JSON key")
                value[key] = item
            return value
        state = json.loads(data.decode("utf-8"), object_pairs_hook=unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(JournalError("nonfinite number")))
        if encode(state) != data:
            raise JournalError("noncanonical journal bytes")
        from tools.qikvrt_recursive_priority_queue import validate, consolidate
        validate(state["units"])
        if consolidate(state["events"]) != state["events"]:
            raise JournalError("duplicate journal event")
        return state
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise JournalError("journal readback rejected") from exc


def receipt(data: bytes) -> dict[str, str]:
    state = decode(data)
    return {"schema": SCHEMA, "sha256": hashlib.sha256(data).hexdigest(),
            "event_count": str(len(state["events"])),
            "unit_count": str(len(state["units"]))}


def verify_receipt(data: bytes, expected_sha256: str) -> dict[str, Any]:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise JournalError("invalid receipt digest")
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise JournalError("journal digest mismatch")
    return decode(data)
