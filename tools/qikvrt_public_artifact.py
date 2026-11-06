#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed metadata admission. No publishing, network, or EAP effects."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

HEX = re.compile(r"[0-9a-f]{64}\Z")
GIT_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\\Z")
IDENT = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,127}\Z")
LICENSES = {"PolyForm-Noncommercial-1.0.0", "CC-BY-NC-ND-4.0", "Apache-2.0", "MIT"}
NOTICE = "Required Notice: Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder."
GATES = ("rights_review", "third_party_review", "security_review", "build_review", "publication_approval")
REQUIRED = ("id", "source_commit", "artifact_sha256", "license", "distribution_url", "required_notice") + GATES

def evaluate(item):
    if not isinstance(item, dict):
        return {"status": "BLOCKED", "reason": "NOT_OBJECT"}
    if any(k not in item for k in REQUIRED):
        return {"status": "BLOCKED", "reason": "MISSING_REQUIRED_FIELD"}
    if not isinstance(item["id"], str) or not IDENT.fullmatch(item["id"]):
        return {"status": "BLOCKED", "reason": "INVALID_ID"}
    if not isinstance(item["source_commit"], str) or not GIT_OBJECT_ID.fullmatch(item["source_commit"]):
        return {"status": "BLOCKED", "reason": "INVALID_GIT_OBJECT_ID"}
    if not isinstance(item["artifact_sha256"], str) or not HEX.fullmatch(item["artifact_sha256"]):
        return {"status": "BLOCKED", "reason": "INVALID_DIGEST"}
    if not isinstance(item["license"], str) or item["license"] not in LICENSES:
        return {"status": "BLOCKED", "reason": "UNREVIEWED_LICENSE"}
    if item["required_notice"] != NOTICE:
        return {"status": "BLOCKED", "reason": "NOTICE_INVALID"}
    url = item["distribution_url"]
    try:
        parsed = urlsplit(url) if isinstance(url, str) else None
        valid_url = (parsed is not None and parsed.scheme == "https" and
                     bool(parsed.hostname) and parsed.username is None and
                     parsed.password is None and parsed.port in (None, 443) and
                     bool(parsed.path and parsed.path != "/") and
                     not parsed.fragment and not any(ch.isspace() for ch in url))
    except ValueError:
        valid_url = False
    if not valid_url:
        return {"status": "BLOCKED", "reason": "URL_INVALID"}
    for gate in GATES:
        if item[gate] != "PASS":
            return {"status": "BLOCKED", "reason": gate.upper() + "_NOT_PASS"}
    if item.get("runtime_effect_status") == "EFFECT_ACK_DONE":
        return {"status": "BLOCKED", "reason": "PUBLICATION_NOT_RUNTIME_ACK"}
    return {"status": "METADATA_ELIGIBLE", "reason": "EXTERNAL_VERIFICATION_REQUIRED"}

def validate_catalog(catalog):
    if not isinstance(catalog, dict) or catalog.get("schema") != "qikvrt.public-artifacts-index.v1":
        return {"status": "BLOCKED", "reason": "INVALID_SCHEMA"}
    records = catalog.get("artifacts")
    if not isinstance(records, list):
        return {"status": "BLOCKED", "reason": "INVALID_ARTIFACTS"}
    if not records:
        return {"status": "CANDIDATE_EMPTY", "artifacts_checked": 0, "results": []}
    ids, results = set(), []
    for item in records:
        outcome = evaluate(item)
        if isinstance(item, dict):
            ident = item.get("id")
            if isinstance(ident, str):
                if ident in ids:
                    outcome = {"status": "BLOCKED", "reason": "DUPLICATE_ID"}
                ids.add(ident)
        results.append(outcome)
    return {"status": "METADATA_ELIGIBLE" if all(x["status"] == "METADATA_ELIGIBLE" for x in results) else "BLOCKED", "artifacts_checked": len(records), "results": results}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": type(error).__name__}))
        return 2
    result = validate_catalog(value) if isinstance(value, dict) and "artifacts" in value else evaluate(value)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"METADATA_ELIGIBLE", "CANDIDATE_EMPTY"} else 1

if __name__ == "__main__":
    raise SystemExit(main())
