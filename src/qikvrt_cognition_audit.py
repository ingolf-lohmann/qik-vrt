#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evidence binding for a human behavioral audit; no semantic AI judge.

The trusted review digests and expected runtime subject MUST come from an
independently authenticated human/control boundary, never from the audit being
checked. A hash pin authenticates the approved bytes only within that boundary.
This module neither authenticates people nor measures hidden cognitive states.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from src.qikvrt_effect_ack import ConnectionDecision, EffectAckRequest

SCHEMA = "qikvrt-human-cognition-audit/v1"
CRITERIA = frozenset(f"HCA-{i:02d}" for i in range(1, 8))
MAX_DOCUMENT = 1024 * 1024
MAX_ARTIFACT = 2 * 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024
MAX_VALIDITY = 30 * 24 * 60 * 60
SHA = re.compile(r"[0-9a-f]{64}\Z")
SUBJECT_KEYS = {"system_id", "version", "configuration_sha256", "purpose", "actor_id"}


class AuditEvidenceError(ValueError):
    pass


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise AuditEvidenceError(code)


def _keys(value: Any, keys: set[str], code: str) -> None:
    _need(type(value) is dict and set(value) == keys, code)


def _text(value: Any, limit: int = 4096) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _need(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise AuditEvidenceError("NONFINITE_JSON_VALUE")


def _load(raw: bytes) -> dict[str, Any]:
    _need(isinstance(raw, bytes) and 0 < len(raw) <= MAX_DOCUMENT, "AUDIT_SIZE_INVALID")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                       parse_constant=_constant)
    _need(type(value) is dict, "AUDIT_OBJECT_REQUIRED")
    return value


def _subject(value: Any) -> None:
    _keys(value, SUBJECT_KEYS, "SUBJECT_FIELDS_INVALID")
    _need(all(_text(v, 512) and v.casefold() not in {"unknown", "unverified", ""}
              for v in value.values()), "SUBJECT_UNRESOLVED")
    _need(SHA.fullmatch(value["configuration_sha256"]) is not None,
          "CONFIGURATION_DIGEST_INVALID")


def _artifact(ref: Any, root: Path, budget: list[int]) -> tuple[str, bytes]:
    _keys(ref, {"path", "sha256"}, "ARTIFACT_FIELDS_INVALID")
    name, digest = ref["path"], ref["sha256"]
    _need(_text(name, 512) and isinstance(digest, str) and SHA.fullmatch(digest)
          is not None, "ARTIFACT_BINDING_INVALID")
    rel = Path(name)
    _need(not rel.is_absolute() and name == rel.as_posix()
          and not any(p in {".", ".."} for p in name.split("/")),
          "ARTIFACT_PATH_INVALID")
    path = root / rel
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        _need(not cursor.is_symlink(), "ARTIFACT_SYMLINK_FORBIDDEN")
    _need(path.resolve().is_relative_to(root) and path.is_file(),
          "ARTIFACT_UNAVAILABLE")
    _need(0 < path.stat().st_size <= MAX_ARTIFACT, "ARTIFACT_SIZE_INVALID")
    with path.open("rb") as stream:
        raw = stream.read(MAX_ARTIFACT + 1)
    budget[0] += len(raw)
    _need(len(raw) <= MAX_ARTIFACT and budget[0] <= MAX_TOTAL,
          "EVIDENCE_BUDGET_EXCEEDED")
    _need(hashlib.sha256(raw).hexdigest() == digest, "ARTIFACT_DIGEST_MISMATCH")
    raw.decode("utf-8")
    return name, raw


def _excerpt(ref: Any, artifacts: dict[str, bytes]) -> str:
    _keys(ref, {"artifact", "role", "start_byte", "end_byte", "quote"},
          "EXCERPT_FIELDS_INVALID")
    _need(isinstance(ref["artifact"], str) and ref["artifact"] in artifacts,
          "EXCERPT_ARTIFACT_UNBOUND")
    _need(ref["role"] in {"human_statement", "machine_response", "tool_readback",
                          "prior_error", "correction", "retest"},
          "EXCERPT_ROLE_INVALID")
    start, end = ref["start_byte"], ref["end_byte"]
    raw = artifacts[ref["artifact"]]
    _need(type(start) is int and type(end) is int and 0 <= start < end <= len(raw),
          "EXCERPT_RANGE_INVALID")
    _need(_text(ref["quote"], 10000) and raw[start:end] == ref["quote"].encode("utf-8"),
          "EXCERPT_BYTES_MISMATCH")
    return ref["role"]


@dataclass(frozen=True)
class CognitionAuditResult:
    outcome: str
    audit_sha256: str
    reasons: tuple[str, ...]

    @property
    def admissible(self) -> bool:
        return self.outcome == "VERIFIED"


def assess_cognition_audit(
    raw: bytes, *, evidence_root: Path, expected_subject: dict[str, str], now: int,
    trusted_review_sha256: Iterable[str] = (),
) -> CognitionAuditResult:
    """Check an exact human-approved dossier; unavailable checking is UNVERIFIED.

    VERIFIED means scoped documentary admission based on the pinned human
    judgment. It is not semantic truth, legal certification, permanent behavior
    change, or an observed downstream effect. No trusted review is the default.
    """
    digest = hashlib.sha256(raw).hexdigest() if isinstance(raw, bytes) else ""
    try:
        audit = _load(raw)
        _keys(audit, {"schema", "audit_id", "subject", "window", "valid_until_utc",
                      "review", "transcripts", "cases", "predecessor",
                      "corrections", "open_findings"}, "AUDIT_FIELDS_INVALID")
        _need(audit["schema"] == SCHEMA and _text(audit["audit_id"], 128),
              "AUDIT_IDENTITY_INVALID")
        _subject(audit["subject"])
        _subject(expected_subject)
        _need(audit["subject"] == expected_subject, "AUDIT_SUBJECT_CHANGED")
        _need(type(now) is int and now >= 0, "CHECK_CLOCK_INVALID")
        window = audit["window"]
        _keys(window, {"start_utc", "end_utc"}, "WINDOW_FIELDS_INVALID")
        start, end, until = window["start_utc"], window["end_utc"], audit["valid_until_utc"]
        _need(all(type(t) is int for t in (start, end, until))
              and 0 <= start <= end <= now < until <= end + MAX_VALIDITY,
              "AUDIT_STALE_OR_WINDOW_INVALID")
        review = audit["review"]
        _keys(review, {"reviewer_id", "kind", "reviewed_utc", "decision", "rationale"},
              "REVIEW_FIELDS_INVALID")
        _need(_text(review["reviewer_id"], 256) and review["kind"] == "human"
              and review["reviewer_id"] != expected_subject["actor_id"]
              and type(review["reviewed_utc"]) is int
              and end <= review["reviewed_utc"] <= now
              and review["decision"] in {"PASS", "FAIL", "UNKNOWN"}
              and _text(review["rationale"]), "HUMAN_REVIEW_INVALID")
        refs = audit["transcripts"]
        _need(type(refs) is list and 1 <= len(refs) <= 32, "TRANSCRIPTS_REQUIRED")
        root, budget = Path(evidence_root).resolve(), [0]
        artifacts: dict[str, bytes] = {}
        for ref in refs:
            name, data = _artifact(ref, root, budget)
            _need(name not in artifacts, "DUPLICATE_ARTIFACT")
            artifacts[name] = data
        cases = audit["cases"]
        _need(type(cases) is list and 7 <= len(cases) <= 128, "AUDIT_CASES_INCOMPLETE")
        ids, criteria, sessions, statuses, observations = set(), set(), set(), set(), set()
        for case in cases:
            _keys(case, {"case_id", "criterion", "session_id", "observed_utc",
                         "result", "rationale", "evidence"}, "CASE_FIELDS_INVALID")
            _need(_text(case["case_id"], 128) and case["case_id"] not in ids,
                  "CASE_ID_INVALID_OR_DUPLICATED")
            ids.add(case["case_id"])
            _need(case["criterion"] in CRITERIA and _text(case["session_id"], 128)
                  and type(case["observed_utc"]) is int
                  and start <= case["observed_utc"] <= end
                  and case["result"] in {"PASS", "FAIL", "UNKNOWN"}
                  and _text(case["rationale"]), "CASE_BINDING_INVALID")
            evidence = case["evidence"]
            _need(type(evidence) is list and 2 <= len(evidence) <= 16,
                  "CASE_EVIDENCE_REQUIRED")
            roles = {_excerpt(item, artifacts) for item in evidence}
            _need({"human_statement", "machine_response"} <= roles,
                  "HUMAN_AND_MACHINE_EVIDENCE_REQUIRED")
            if case["criterion"] == "HCA-05" and case["result"] == "PASS":
                _need({"prior_error", "correction", "retest"} <= roles,
                      "ACTUAL_CORRECTION_AND_RETEST_REQUIRED")
            criteria.add(case["criterion"])
            sessions.add(case["session_id"])
            statuses.add(case["result"])
            observations.add(case["observed_utc"])
        _need(criteria == CRITERIA and len(sessions) >= 2 and len(observations) >= 2,
              "CRITERIA_OR_LONGITUDINAL_SAMPLE_INCOMPLETE")
        findings = audit["open_findings"]
        _need(type(findings) is list and len(findings) <= 128
              and all(_text(f, 128) for f in findings) and len(set(findings)) == len(findings),
              "FINDINGS_INVALID")
        predecessor, corrections = audit["predecessor"], audit["corrections"]
        _need(type(corrections) is list and len(corrections) <= 128,
              "CORRECTIONS_INVALID")
        if predecessor is not None:
            _, previous = _artifact(predecessor, root, budget)
            prior = _load(previous)
            _need(prior.get("schema") == SCHEMA and _text(prior.get("audit_id"), 128)
                  and prior["audit_id"] != audit["audit_id"],
                  "PREDECESSOR_IDENTITY_INVALID")
            _subject(prior.get("subject"))
            _need(all(prior["subject"][key] == expected_subject[key]
                      for key in ("system_id", "purpose", "actor_id")),
                  "PREDECESSOR_SUBJECT_CHANGED")
            _need(type(prior.get("open_findings")) is list
                  and len(prior["open_findings"]) <= 128
                  and all(_text(f, 128) for f in prior["open_findings"]),
                  "PREDECESSOR_FINDINGS_INVALID")
            _need(type(prior.get("cases")) is list and len(prior["cases"]) <= 128
                  and all(type(c) is dict and _text(c.get("case_id"), 128)
                          and c.get("result") in {"PASS", "FAIL", "UNKNOWN"}
                          for c in prior["cases"]), "PREDECESSOR_CASES_INVALID")
            obligations = set(prior["open_findings"]) | {
                c["case_id"] for c in prior["cases"] if c["result"] == "FAIL"}
            if type(prior.get("review")) is dict and prior["review"].get("decision") == "FAIL":
                obligations.add("review:" + prior["audit_id"])
            corrected = set()
            for correction in corrections:
                _keys(correction, {"finding_id", "before", "after", "retest"},
                      "CORRECTION_FIELDS_INVALID")
                finding = correction["finding_id"]
                _need(_text(finding, 128) and finding not in corrected
                      and finding in obligations, "CORRECTION_FINDING_INVALID")
                corrected.add(finding)
                for field, role in (("before", "prior_error"), ("after", "correction"),
                                    ("retest", "retest")):
                    _need(_excerpt(correction[field], artifacts) == role,
                          "CORRECTION_EVIDENCE_ROLE_INVALID")
            _need(obligations <= corrected | set(findings),
                  "PREDECESSOR_FINDING_DROPPED")
        else:
            _need(not corrections, "CORRECTION_PREDECESSOR_REQUIRED")
        pins = tuple(trusted_review_sha256)
        _need(len(pins) <= 128 and all(isinstance(p, str) and SHA.fullmatch(p) for p in pins),
              "REVIEW_TRUST_BINDING_INVALID")
        _need(digest in pins, "INDEPENDENT_HUMAN_REVIEW_NOT_AUTHENTICATED")
        if findings or "FAIL" in statuses or review["decision"] == "FAIL":
            return CognitionAuditResult("FAILED", digest, ("HUMAN_REVIEWED_BEHAVIOR_VIOLATION",))
        if "UNKNOWN" in statuses or review["decision"] != "PASS":
            return CognitionAuditResult("UNVERIFIED", digest, ("HUMAN_REVIEW_INCOMPLETE",))
        return CognitionAuditResult("VERIFIED", digest, ("SCOPED_HUMAN_AUDIT_VERIFIED",))
    except (AuditEvidenceError, OSError, ValueError, TypeError, KeyError,
            UnicodeError, OverflowError, RecursionError) as error:
        reason = str(error) if isinstance(error, AuditEvidenceError) else "AUDIT_CHECK_UNAVAILABLE_OR_INVALID"
        return CognitionAuditResult("UNVERIFIED", digest, (reason,))


def bind_cognition_audit(request: EffectAckRequest, raw: bytes, **checks: Any
                        ) -> tuple[EffectAckRequest, CognitionAuditResult]:
    """Conjoin human audit with existing policy; never grant other EAP gates.

    An authenticated violation blocks the scoped action. An absent/unreliable
    review denies release and leaves the original five-state engine to CONTINUE.
    Existing BLOCK/ISOLATE decisions are retained. No wire fields are added.
    """
    audit = assess_cognition_audit(raw, **checks)
    decision = request.connection_decision
    if audit.outcome == "FAILED" and decision not in {
            ConnectionDecision.BLOCK, ConnectionDecision.ISOLATE}:
        decision = ConnectionDecision.BLOCK
    refs = request.evidence_refs
    if audit.audit_sha256:
        refs = tuple(dict.fromkeys((*refs, "sha256:" + audit.audit_sha256)))
    bounded = replace(request,
                      policy_allows_release=request.policy_allows_release and audit.admissible,
                      connection_decision=decision, evidence_refs=refs,
                      reasons=(*request.reasons, *audit.reasons))
    return bounded, audit
