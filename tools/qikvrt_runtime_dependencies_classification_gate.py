#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate runtime/DEPENDENCIES.json volatile classification."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DEP = ROOT / "runtime" / "DEPENDENCIES.json"
SHA = ROOT / "SHA256SUMS.txt"
POLICY = ROOT / "policy" / "RUNTIME_DEPENDENCIES_STATE_POLICY_V35.json"

def validate_runtime_dependencies_classification():
    """Validate runtime/DEPENDENCIES.json is volatile and excluded from SHA256SUMS."""
    assert RUNTIME_DEP.is_file(), "runtime/DEPENDENCIES.json missing"
    data = json.loads(RUNTIME_DEP.read_text(encoding="utf-8"))
    assert data.get("classification") == "VOLATILE_RUNTIME_DEPENDENCY_STATE", "runtime/DEPENDENCIES.json not volatile state"
    assert data.get("immutable_release_constant") is False, "runtime/DEPENDENCIES.json still immutable"
    assert data.get("excluded_from_sha256sums") is True, "runtime/DEPENDENCIES.json not marked excluded"
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["runtime_dependencies_json"]["excluded_from_immutable_sha256sums"] is True
    if SHA.is_file():
        for line in SHA.read_text(encoding="utf-8").splitlines():
            assert not line.strip().endswith(" runtime/DEPENDENCIES.json"), "runtime/DEPENDENCIES.json is still in SHA256SUMS.txt"

def main(argv=None):
    """Run gate."""
    validate_runtime_dependencies_classification()
    print("PASS runtime/DEPENDENCIES.json volatile classification gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
