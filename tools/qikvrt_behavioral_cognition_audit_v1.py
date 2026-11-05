#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded, local structure/integrity check for QIK-VRT behavioral audit records.

This is deliberately NOT an independent truth checker, deployment gate,
identity attestor, policy admission, or EAP commit executor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "QIKVRT_BEHAVIORAL_COGNITION_AUDIT_V1.json"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
HEAD = re.compile(r"[0-9a-f]{40}\Z")
MAX_AUDIT_BYTES = 2_000_000
MAX_CAPTURE_BYTES = 2_000_000
MAX_OBSERVATIONS = 100


def load_json_no_duplicates(payload: bytes) -> object:
    def reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result

    return json.loads(payload.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs)


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def bounded_bytes(path: Path, limit: int) -> bytes:
    require(path.is_file(), "file missing: " + str(path))
    require(path.stat().st_size <= limit, "file size limit exceeded")
    return path.read_bytes()


def field(obj: dict, name: str) -> str:
    value = obj.get(name)
    require(isinstance(value, str) and 0 < len(value) <= 512, "invalid field " + name)
    return value


def check_capture(root: Path, relative: str, expected: str) -> str:
    require(len(relative) <= 256 and not Path(relative).is_absolute(), "absolute/long capture path")
    require(not any(part in (".", "..") for part in Path(relative).parts), "unsafe capture path")
    resolved = (root / relative).resolve(strict=True)
    require(resolved.is_relative_to(root), "capture path escapes evidence root")
    contents = bounded_bytes(resolved, MAX_CAPTURE_BYTES)
    require(DIGEST.fullmatch(expected) is not None, "invalid capture digest")
    require(sha256(contents) == expected, "capture digest mismatch")
    return sha256(contents)


def validate(audit: object, evidence_root: Path, policy: object, policy_digest: str) -> dict:
    require(isinstance(audit, dict), "audit must be object")
    require(isinstance(policy, dict), "policy must be object")
    require(audit.get("schema") == "qikvrt_behavioral_cognition_audit_v1", "audit schema mismatch")
    require(audit.get("policy_sha256") == policy_digest, "exact policy digest mismatch")

    subject = audit.get("subject")
    require(isinstance(subject, dict), "subject missing")
    for name in ("agent_id", "model_id", "runtime_id", "environment"):
        field(subject, name)
    head = field(subject, "source_head")
    require(HEAD.fullmatch(head) is not None, "source_head must be exact 40-character lowercase SHA")
    criterion_ids = [c["id"] for c in policy["criteria"]]
    require(len(criterion_ids) == len(set(criterion_ids)) == 7, "invalid policy criterion inventory")
    observations = audit.get("observations")
    require(isinstance(observations, list) and 0 < len(observations) <= MAX_OBSERVATIONS, "observations count invalid")
    sessions = set()
    keys = set()
    counts = {"PASS": 0, "FAIL": 0, "UNVERIFIED": 0}
    for observation in observations:
        require(isinstance(observation, dict), "observation must be object")
        session_id = field(observation, "session_id")
        turn_id = field(observation, "turn_id")
        require((session_id, turn_id) not in keys, "duplicate session/turn")
        keys.add((session_id, turn_id))
        sessions.add(session_id)
        check_capture(evidence_root, field(observation, "capture_path"),
                      field(observation, "capture_sha256"))
        checks = observation.get("checks")
        require(isinstance(checks, list) and len(checks) == len(criterion_ids), "incomplete criterion inventory")
        observed_ids = []
        for check in checks:
            require(isinstance(check, dict), "check must be object")
            criterion_id = field(check, "id")
            observed_ids.append(criterion_id)
            result = field(check, "result")
            require(result in counts, "unknown criterion result")
            reviewer_id = field(check, "reviewer_id")
            require(reviewer_id != subject["agent_id"], "self-review cannot be represented as independent")
            rationale = field(check, "rationale")
            require(len(rationale) >= 15, "rationale is too short")
            field(check, "evidence_anchor")
            counts[result] += 1
        require(set(observed_ids) == set(criterion_ids)
                and len(set(observed_ids)) == len(criterion_ids), "missing/duplicate criterion")

    minimum_sessions = policy["testing"]["minimum_distinct_sessions"]
    if counts["FAIL"]:
        decision = "BLOCK"
    elif len(sessions) < minimum_sessions or counts["UNVERIFIED"]:
        decision = "HOLD"
    else:
        decision = "READY_FOR_INDEPENDENT_REVIEW"

    return {
        "schema": "qikvrt_behavioral_audit_structural_result_v1",
        "decision": decision,
        "structural_integrity": "VERIFIED",
        "behavioral_truth": "NOT_VERIFIED",
        "reviewer_independence": "NOT_AUTHENTICATED",
        "runtime_admission": "UNVERIFIED",
        "EFFECT_ACK_DONE": False,
        "observations": len(observations),
        "distinct_sessions": len(sessions),
        "criteria_count": len(criterion_ids),
        "results": counts,
        "policy_sha256": policy_digest,
        "subject": subject,
        "warning": "A local hash/shape check does not verify the truth of an observation or an independent reviewer."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_json", type=Path)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        policy_bytes = bounded_bytes(POLICY, MAX_AUDIT_BYTES)
        policy = load_json_no_duplicates(policy_bytes)
        audit = load_json_no_duplicates(bounded_bytes(args.audit_json, MAX_AUDIT_BYTES))
        evidence_root = args.evidence_root.resolve(strict=True)
        require(evidence_root.is_dir(), "evidence root must be directory")
        result = validate(audit, evidence_root, policy, sha256(policy_bytes))
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
        return 0 if result["decision"] == "READY_FOR_INDEPENDENT_REVIEW" else 2
    except (OSError, ValueError, KeyError, UnicodeError, TypeError) as exc:
        print(json.dumps({"schema": "qikvrt_behavioral_audit_structural_result_v1",
                          "decision": "BLOCK", "reason": str(exc),
                          "EFFECT_ACK_DONE": False}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
