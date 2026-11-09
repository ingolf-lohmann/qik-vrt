#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed source-bound dependency carrier selector; never a production admission."""
from __future__ import annotations
import json
from pathlib import Path
import re

SCHEMA = "qikvrt-runtime-delivery-successor/v1"
RECORD = Path("runtime/self-host/DELIVERY_SUCCESSOR_20261107.json")
SCOPE = "DEPENDENCY_IMAGE_ONLY; RESEAL_CURRENT_SOURCE; NO_PREDECESSOR_PASS_TRANSFER"
CLAIMS = {"predecessor_pass_transferred": False, "host_admitted": False,
          "product_delivery_verified": False, "independent_review_verified": False,
          "effect_ack_done": False}
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")

def select_candidate(root: Path) -> dict:
    root = Path(root)
    definition = json.loads((root / "runtime/self-host/PACKAGE.json").read_bytes())
    record = json.loads((root / RECORD).read_bytes())
    if not isinstance(record, dict) or set(record) != {
            "schema", "historical_predecessor", "candidate", "evidence", "claims"}:
        raise ValueError("RUNTIME_SUCCESSOR_SCHEMA_MISMATCH")
    claims = record["claims"]
    if (record["schema"] != SCHEMA or not isinstance(claims, dict)
            or set(claims) != set(CLAIMS)
            or any(claims[key] is not False for key in CLAIMS)):
        raise ValueError("RUNTIME_SUCCESSOR_UNADMITTED_CLAIMS")
    old = definition["runtime_delivery_baseline"]
    if record["historical_predecessor"] != old:
        raise ValueError("RUNTIME_SUCCESSOR_HISTORICAL_BASELINE_CHANGED")
    new = record["candidate"]
    if not isinstance(new, dict) or set(new) != {
            "artifact_bytes", "artifact_id", "artifact_sha256", "delivery_sha256",
            "repository", "run_id", "attempt", "source_head", "source_tree", "reuse_scope"}:
        raise ValueError("RUNTIME_SUCCESSOR_CANDIDATE_SCHEMA_MISMATCH")
    evidence = record["evidence"]
    if not isinstance(evidence, dict) or set(evidence) != {
            "source_run_url", "observation", "distinction"}:
        raise ValueError("RUNTIME_SUCCESSOR_PROVENANCE_MISSING")
    expected_url = ("https://github.com/" + old["repository"]
                    + "/actions/runs/" + str(new["run_id"])
                    + "/attempts/" + str(new["attempt"]))
    if (evidence["source_run_url"] != expected_url
            or not isinstance(evidence["observation"], str)
            or not evidence["observation"].endswith("Z")
            or not isinstance(evidence["distinction"], str)
            or not evidence["distinction"]):
        raise ValueError("RUNTIME_SUCCESSOR_PROVENANCE_MISMATCH")
    for name in ("artifact_bytes", "artifact_id", "run_id", "attempt"):
        if type(new[name]) is not int or new[name] <= 0:
            raise ValueError("RUNTIME_SUCCESSOR_INVALID_INTEGER")
    if (not HEX64.fullmatch(new["artifact_sha256"])
            or not HEX64.fullmatch(new["delivery_sha256"])
            or not HEX40.fullmatch(new["source_head"])
            or not HEX40.fullmatch(new["source_tree"])):
        raise ValueError("RUNTIME_SUCCESSOR_INVALID_SHA")
    if (new["repository"] != old["repository"]
            or new["source_head"] != old["source_head"]
            or new["source_tree"] != old["source_tree"]
            or new["run_id"] != old["run_id"]
            or new["attempt"] < 2
            or new["reuse_scope"] != SCOPE
            or new["artifact_id"] == old["artifact_id"]
            or new["artifact_sha256"] == old["artifact_sha256"]
            or new["delivery_sha256"] == old["delivery_sha256"]):
        raise ValueError("RUNTIME_SUCCESSOR_EQUIVALENCE_UNPROVEN")
    # The caller must independently check ZIP bytes, DELIVERY.json and every file.
    return dict(new)
