#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Closed revision-03 wire adapter of the original EFFECT_ACK evaluator.

The JSON grammar and bounds follow draft-lohmann-qikvrt-effect-ack-03,
sections 4-9 and Appendix A. Authentication, evidence truth and a trusted
latest-chain anchor are deployment inputs, never consequences of a hash.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
import time
import unicodedata
from typing import Any

try:
    from . import qikvrt_effect_ack as core
except ImportError:
    import qikvrt_effect_ack as core

SPECIFICATION = "https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03"
SHA = re.compile(r"sha256:[0-9a-f]{64}\Z")
MAX_INTEGER = 9007199254740991
SETS = ("reasons", "evidence_refs", "required_evidence_refs", "open_questions", "next_required_checks")
BOOLS = ("transport_ack", "origin_checked", "context_checked", "semantics_reconstructed",
         "effect_anticipated", "risk_classified", "responsibility_assigned", "connection_decided",
         "policy_allows_release", "ordinary_release", "deadline_exceeded")
FIELDS = frozenset((*BOOLS, *SETS, "wire_version", "message_type", "protocol_root_id",
    "protocol_version", "protocol_id", "previous_protocol_id", "previous_protocol_hash",
    "protocol_hash", "input_id", "input_hash", "state", "risk_level", "responsibility_owner",
    "connection_decision", "policy_id", "policy_version", "policy_hash", "evaluation_timeout_ms", "created_utc"))


class WireError(ValueError):
    """No ordinary release is admitted after a wire or deployment failure."""


def normalize(value: Any) -> Any:
    if isinstance(value, str):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise WireError("UNICODE_SCALAR_VALUE_REQUIRED")
        return unicodedata.normalize("NFC", value)
    if value is None or type(value) is bool:
        return value
    if type(value) is int and abs(value) <= MAX_INTEGER:
        return value
    if isinstance(value, list) or isinstance(value, tuple):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        result = {}
        for key, v in value.items():
            if not isinstance(key, str):
                raise WireError("STRING_MEMBER_NAME_REQUIRED")
            key = normalize(key)
            if key in result:
                raise WireError("DUPLICATE_NORMALIZED_MEMBER")
            result[key] = normalize(v)
        return result
    raise WireError("IJSON_EXACT_INTEGER_OR_SUPPORTED_VALUE_REQUIRED")


def parse(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= 65536 or raw.startswith(b"\xef\xbb\xbf"):
        raise WireError("BOUNDED_UTF8_WITHOUT_BOM_REQUIRED")
    def pairs(items):
        result = {}
        for name, value in items:
            name = normalize(name)
            if name in result:
                raise WireError("DUPLICATE_JSON_MEMBER")
            result[name] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(WireError("NON_IJSON_NUMBER")))
        value = normalize(value)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise WireError("INVALID_IJSON") from exc
    if not isinstance(value, dict):
        raise WireError("JSON_OBJECT_REQUIRED")
    return value


def canonical(value: Any) -> bytes:
    """NFC/I-JSON + JCS; UTF-16 member ordering, scalar ordering for sets.

    Floating point is excluded by this protocol. Fixed wire member names are
    ASCII; the general serializer also handles supplementary-plane keys.
    """
    def encode(v):
        if isinstance(v, dict):
            keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
            return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + encode(v[k]) for k in keys) + "}"
        if isinstance(v, list):
            return "[" + ",".join(encode(x) for x in v) + "]"
        return json.dumps(v, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return encode(normalize(value)).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def projection(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in ("protocol_hash", "created_utc")}


def selected_state(record: dict) -> str:
    """Reuse the original evaluator's state predicate after wire validation."""
    if record["deadline_exceeded"] or "PREVIOUS_PROTOCOL_INTEGRITY_FAILURE" in record["reasons"]:
        return core.EffectState.EFFECT_ACK_BLOCK.value
    request = core.EffectAckRequest(
        protocol_root_id=record["protocol_root_id"], input_id=record["input_id"], payload=None,
        **{k: record[k] for k in ("transport_ack", "origin_checked", "context_checked",
            "semantics_reconstructed", "effect_anticipated", "risk_classified", "risk_level",
            "responsibility_assigned", "responsibility_owner", "connection_decision", "policy_allows_release",
            "evidence_refs", "required_evidence_refs", "open_questions", "next_required_checks")})
    integrity_reasons = {"PAYLOAD_EXCEEDS_SYNCHRONOUS_LIMIT", "DECLARED_INPUT_HASH_MALFORMED", "INPUT_HASH_MISMATCH"}
    state, _, _ = core.EffectAckEngine()._decide(request, {
        "effect_checkable": record["transport_ack"] and bool(SHA.fullmatch(record["input_hash"])),
        "input_hash": record["input_hash"], "payload_too_large": bool(integrity_reasons.intersection(record["reasons"])),
        "malformed_declared_hash": False, "hash_mismatch": False})
    return state.value


def verify_record(value: dict, previous: dict | None = None) -> dict:
    record = normalize(value)
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise WireError("CLOSED_VERSION_1_FIELDS_REQUIRED")
    if type(record["wire_version"]) is not int or record["wire_version"] != 1 or record["message_type"] != "effect-ack-record":
        raise WireError("UNSUPPORTED_WIRE_VERSION_OR_MESSAGE")
    if any(type(record[k]) is not bool for k in BOOLS):
        raise WireError("BOOLEAN_REQUIRED")
    for name, limit, minimum in (("protocol_root_id", 256, 1), ("protocol_id", 512, 1),
            ("input_id", 256, 1), ("policy_id", 256, 1), ("responsibility_owner", 256, 0)):
        if not isinstance(record[name], str) or not minimum <= len(record[name]) <= limit:
            raise WireError("BOUNDED_IDENTIFIER_REQUIRED:" + name)
    for name, maximum in (("protocol_version", MAX_INTEGER), ("policy_version", MAX_INTEGER), ("evaluation_timeout_ms", 2147483647)):
        if type(record[name]) is not int or not 1 <= record[name] <= maximum:
            raise WireError("POSITIVE_BOUNDED_INTEGER_REQUIRED:" + name)
    if record["protocol_id"] != f'{record["protocol_root_id"]}:v{record["protocol_version"]}':
        raise WireError("PROTOCOL_ID_MISMATCH")
    for name in ("protocol_hash", "policy_hash"):
        if not isinstance(record[name], str) or not SHA.fullmatch(record[name]):
            raise WireError("SHA256_IDENTIFIER_REQUIRED:" + name)
    if any(not isinstance(record[k], str) for k in ("state", "risk_level", "connection_decision")) or record["state"] not in {s.value for s in core.EffectState} or record["risk_level"] not in {s.value for s in core.RiskLevel} or record["connection_decision"] not in {s.value for s in core.ConnectionDecision}:
        raise WireError("UNKNOWN_VERSION_1_ENUM")
    if record["input_hash"] != "UNAVAILABLE" and (not isinstance(record["input_hash"], str) or not SHA.fullmatch(record["input_hash"])):
        raise WireError("INPUT_HASH_REQUIRED")
    if record["input_hash"] == "UNAVAILABLE" and record["state"] != "EFFECT_NACK":
        raise WireError("UNAVAILABLE_ONLY_FOR_NACK")
    for name in SETS:
        items = record[name]
        if not isinstance(items, list) or len(items) > 128 or any(not isinstance(x, str) or len(x) > 1024 for x in items):
            raise WireError("BOUNDED_TEXT_SET_REQUIRED")
        record[name] = sorted(set(x for x in items if x))
        if name in ("evidence_refs", "required_evidence_refs") and any(not SHA.fullmatch(x) for x in record[name]):
            raise WireError("EVIDENCE_DIGEST_REQUIRED")
    try:
        stamp = record["created_utc"]
        if not isinstance(stamp, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", stamp):
            raise ValueError()
        datetime.fromisoformat(stamp[:-1] + "+00:00")
    except (ValueError, TypeError) as exc:
        raise WireError("UTC_TIMESTAMP_REQUIRED") from exc
    if record["connection_decided"] != (record["connection_decision"] != "UNDECIDED"):
        raise WireError("CONNECTION_DECISION_MISMATCH")
    if record["deadline_exceeded"] and not record["next_required_checks"]:
        raise WireError("TIMEOUT_CONTINUATION_REQUIRED")
    if record["state"] != selected_state(record) or record["ordinary_release"] != (record["state"] == "EFFECT_ACK_DONE"):
        raise WireError("STATE_REDERIVATION_MISMATCH")
    if record["protocol_hash"] != digest(projection(record)):
        raise WireError("PROTOCOL_HASH_MISMATCH")
    if record["protocol_version"] == 1:
        if previous is not None or record["previous_protocol_id"] is not None or record["previous_protocol_hash"] is not None:
            raise WireError("FIRST_RECORD_PREDECESSOR_FORBIDDEN")
    else:
        if previous is None:
            raise WireError("IMMEDIATE_PREDECESSOR_REQUIRED")
        # Caller validates predecessors in order; never recursively trust an unbounded chain.
        if (record["protocol_version"] != previous["protocol_version"] + 1
                or record["previous_protocol_id"] != previous["protocol_id"]
                or record["previous_protocol_hash"] != previous["protocol_hash"]
                or any(record[k] != previous[k] for k in ("protocol_root_id", "input_id", "input_hash"))):
            raise WireError("CHAIN_BINDING_MISMATCH")
    return record


def verify_chain(records: list[dict]) -> list[dict]:
    if not isinstance(records, list) or not 1 <= len(records) <= 128:
        raise WireError("BOUNDED_NONEMPTY_CHAIN_REQUIRED")
    result = []
    for record in records:
        result.append(verify_record(record, result[-1] if result else None))
    return result


def make_record(request: core.EffectAckRequest, policy: dict, *, previous_chain: list[dict] | None = None, timeout_ms: int = 1000) -> dict:
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 2147483647:
        raise WireError("POSITIVE_TIMEOUT_REQUIRED")
    started = time.monotonic_ns()
    old = None
    incident = None
    if previous_chain:
        try:
            old = verify_chain(previous_chain)[-1]
            input_hash = core.sha256_identifier(request.payload) if request.payload is not None else "UNAVAILABLE"
            if old["protocol_root_id"] != request.protocol_root_id or old["input_id"] != request.input_id or old["input_hash"] != input_hash:
                raise WireError("PREDECESSOR_INPUT_BINDING_MISMATCH")
        except (WireError, KeyError, TypeError, ValueError):
            last = previous_chain[-1] if isinstance(previous_chain[-1], dict) else {}
            incident = digest({"root": str(request.protocol_root_id)[:256], "predecessor_hash": str(last.get("protocol_hash", ""))[:71]})
            old = None
    remaining = max(0, timeout_ms - (time.monotonic_ns() - started) // 1000000)
    result = core.EffectAckEngine().evaluate(request, timeout_ms=remaining)
    record = result.protocol.to_dict()
    del record["schema"]
    record.update(wire_version=1, message_type="effect-ack-record", policy_id=policy["policy_id"],
        policy_version=policy["policy_version"], policy_hash=digest(policy), evaluation_timeout_ms=timeout_ms,
        deadline_exceeded="SYNCHRONOUS_DEADLINE_EXCEEDED" in record["reasons"])
    if incident:
        record.update(protocol_root_id="qikvrt:incident:" + incident[7:], state="EFFECT_ACK_BLOCK", ordinary_release=False)
        record["reasons"] = sorted(set(record["reasons"] + ["PREVIOUS_PROTOCOL_INTEGRITY_FAILURE"]))
        record["next_required_checks"] = ["REBUILD_OR_RECOVER_VERIFIED_PROTOCOL_CHAIN"]
        record["evidence_refs"] = sorted(set(record["evidence_refs"] + [incident]))
    if old:
        changed = set(FIELDS) - {"protocol_version", "protocol_id", "previous_protocol_id", "previous_protocol_hash", "protocol_hash", "created_utc"}
        if all(record[k] == old[k] for k in changed) and time.monotonic_ns() - started < timeout_ms * 1000000:
            return old
        record.update(protocol_version=old["protocol_version"] + 1, previous_protocol_id=old["protocol_id"], previous_protocol_hash=old["protocol_hash"])
    record["protocol_id"] = f'{record["protocol_root_id"]}:v{record["protocol_version"]}'
    if time.monotonic_ns() - started >= timeout_ms * 1000000:
        record.update(state="EFFECT_ACK_BLOCK", ordinary_release=False, deadline_exceeded=True)
        record["reasons"] = sorted(set(record["reasons"] + ["SYNCHRONOUS_DEADLINE_EXCEEDED"]))
        record["next_required_checks"] = sorted(set(record["next_required_checks"] + ["RETRY_AFTER_BOUNDED_EVALUATOR_RECOVERY"]))
    record["protocol_hash"] = digest(projection(record))
    return verify_record(record, old)


def verify_release(chain: list[dict], *, authenticated: bool, latest_hash: str, policy: dict,
                   required_evidence: dict[str, Any], observed_evidence: dict[str, Any]) -> dict:
    record = verify_chain(chain)[-1]
    if authenticated is not True:
        raise WireError("AUTHENTICATED_AUTHORIZED_EVALUATOR_REQUIRED")
    if latest_hash != record["protocol_hash"]:
        raise WireError("STALE_OR_UNANCHORED_RECORD")
    if (record["policy_id"] != policy.get("policy_id") or record["policy_version"] != policy.get("policy_version")
            or record["policy_hash"] != digest(policy)):
        raise WireError("TRUSTED_POLICY_BINDING_MISMATCH")
    if record["required_evidence_refs"] != sorted(required_evidence):
        raise WireError("POLICY_REQUIRED_EVIDENCE_MISMATCH")
    for ref, expected in required_evidence.items():
        if ref not in record["evidence_refs"] or ref not in observed_evidence or digest(observed_evidence[ref]) != ref or canonical(observed_evidence[ref]) != canonical(expected):
            raise WireError("REQUIRED_EVIDENCE_VALIDATION_FAILED")
    if record["state"] != "EFFECT_ACK_DONE" or record["ordinary_release"] is not True:
        raise WireError("ORDINARY_RELEASE_NOT_AUTHORIZED")
    return record
