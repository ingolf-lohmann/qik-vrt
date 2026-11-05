#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Fourteen named obligations attached to the existing EAP consumer.

This is an opt-in external evidence profile, not a new wire contract or an
executor. Predicate meanings and the authenticated evaluator are trusted
deployment inputs. A predicate hash alone does not authenticate its callback.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Mapping

try:
    from . import qikvrt_effect_ack as core
    from . import qikvrt_effect_ack_wire as wire
except ImportError:
    import qikvrt_effect_ack as core
    import qikvrt_effect_ack_wire as wire

SCHEMA = "qikvrt-canonical-clause-audit/v1"
CLAUSE_IDS = tuple(f"c{i}" for i in range(1, 15))
Predicate = Callable[[dict[str, Any], Any], bool]


class ClauseAuditError(wire.WireError):
    """Required clause evidence could not be validated; no release."""


def _hash(value: Any) -> str:
    if not isinstance(value, str) or not wire.SHA.fullmatch(value):
        raise ClauseAuditError("SHA256_IDENTIFIER_REQUIRED")
    return value


def verify_clause_evidence(
    record: dict, *, policy: dict, payload: bytes,
    observed_evidence: Mapping[str, Any],
    validators: Mapping[str, Predicate],
) -> dict:
    """Validate all named obligations for the original EAP consumer.

    The caller supplies a trusted immutable policy and audited predicate
    implementations. They must not be selected from untrusted request JSON.
    This helper returns required evidence, never an effect authorization.
    """
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= 65536:
        raise ClauseAuditError("BOUNDED_EXACT_INPUT_BYTES_REQUIRED")
    if record["input_hash"] != core.sha256_identifier(payload):
        raise ClauseAuditError("INPUT_BYTES_BINDING_MISMATCH")
    profile = policy.get("canonical_storage")
    if (not isinstance(profile, dict)
            or set(profile) != {"schema", "audit_hash", "predicates"}
            or profile["schema"] != SCHEMA
            or not isinstance(profile["predicates"], dict)
            or set(profile["predicates"]) != set(CLAUSE_IDS)):
        raise ClauseAuditError("EXACT_FOURTEEN_PREDICATE_POLICY_REQUIRED")
    for ref in profile["predicates"].values():
        _hash(ref)
    if not isinstance(validators, Mapping):
        raise ClauseAuditError("TRUSTED_CLAUSE_VALIDATOR_UNAVAILABLE")

    required: dict[str, Any] = {}

    def resolve(ref: str) -> Any:
        ref = _hash(ref)
        if ref not in observed_evidence:
            raise ClauseAuditError("REQUIRED_EVIDENCE_UNAVAILABLE")
        value = observed_evidence[ref]
        raw = wire.canonical(value)
        if len(raw) > 65536 or wire.digest(value) != ref:
            raise ClauseAuditError("REQUIRED_EVIDENCE_DIGEST_MISMATCH")
        # Freeze caller-owned data; no callback may change the checked object.
        frozen = json.loads(raw)
        required[ref] = frozen
        return frozen

    audit = resolve(profile["audit_hash"])
    if (not isinstance(audit, dict)
            or set(audit) != {"schema", "input_hash", "past", "future", "clauses"}
            or audit["schema"] != SCHEMA
            or audit["input_hash"] != record["input_hash"]):
        raise ClauseAuditError("AUDIT_SUBJECT_BINDING_REQUIRED")
    for field, status in (("past", "OBSERVED"), ("future", "ANTICIPATED")):
        archive = audit[field]
        if (not isinstance(archive, dict)
                or set(archive) != {"status", "payload", "provenance_hash"}
                or archive["status"] != status):
            raise ClauseAuditError("TYPED_CANONICAL_ARCHIVE_REQUIRED")
        resolve(archive["provenance_hash"])

    clauses = audit["clauses"]
    if not isinstance(clauses, list) or len(clauses) != len(CLAUSE_IDS):
        raise ClauseAuditError("EXACT_FOURTEEN_CLAUSES_REQUIRED")
    indexed = {}
    for clause in clauses:
        if (not isinstance(clause, dict)
                or set(clause) != {"id", "predicate_hash", "evidence_hash"}
                or not isinstance(clause["id"], str)
                or clause["id"] not in CLAUSE_IDS or clause["id"] in indexed):
            raise ClauseAuditError("DUPLICATE_OR_UNKNOWN_CLAUSE")
        indexed[clause["id"]] = clause
    for identifier in CLAUSE_IDS:
        clause = indexed[identifier]
        predicate = profile["predicates"][identifier]
        if clause["predicate_hash"] != predicate:
            raise ClauseAuditError("CLAUSE_PREDICATE_BINDING_MISMATCH")
        evidence = resolve(clause["evidence_hash"])
        validator = validators.get(predicate)
        if not callable(validator):
            raise ClauseAuditError("TRUSTED_CLAUSE_VALIDATOR_UNAVAILABLE")
        try:
            # Each evaluator gets independent copies, including its evidence.
            passed = validator(json.loads(wire.canonical(audit)),
                               json.loads(wire.canonical(evidence)))
        except Exception:
            raise ClauseAuditError("CLAUSE_VALIDATOR_FAILED:" + identifier) from None
        if passed is not True:
            raise ClauseAuditError("CLAUSE_NOT_VERIFIED:" + identifier)

    return required


def verify_canonical_storage(
    chain: list[dict], *, policy: dict, payload: bytes,
    authenticated: bool, latest_hash: str,
    observed_evidence: Mapping[str, Any], validators: Mapping[str, Predicate],
) -> dict:
    """Convenience entry point; authorization stays in the original consumer."""
    records = wire.verify_chain(chain)
    refs = records[-1]["required_evidence_refs"]
    if any(ref not in observed_evidence for ref in refs):
        raise ClauseAuditError("REQUIRED_EVIDENCE_UNAVAILABLE")
    required = {ref: observed_evidence[ref] for ref in refs}
    return wire.verify_release(records, authenticated=authenticated,
        latest_hash=latest_hash, policy=policy, required_evidence=required,
        observed_evidence=dict(observed_evidence), input_payload=payload,
        clause_validators=validators)
