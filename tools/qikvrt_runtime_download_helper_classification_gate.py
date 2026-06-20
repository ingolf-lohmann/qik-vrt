#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate runtime download helper classification."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "canonical" / "RUNTIME_DOWNLOAD_HELPER_SCRIPT_CLASSIFICATION_GATE_V42.json"
SHA = ROOT / "SHA256SUMS.txt"

def validate_runtime_download_helpers():
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    sha_text = SHA.read_text(encoding="utf-8") if SHA.is_file() else ""
    assert "runtime/download_python_runtime.ps1" in gate["runtime_helper_files"], "download helper not registered"
    for rel in gate["runtime_helper_files"]:
        path = ROOT / rel
        assert path.is_file(), "runtime helper missing: " + rel
        policy = ROOT / (rel + ".policy.json")
        if not policy.is_file() and rel == "runtime/download_python_runtime.ps1":
            policy = ROOT / "runtime/download_python_runtime.policy.json"
        assert policy.is_file(), "runtime helper policy missing: " + rel
        data = json.loads(policy.read_text(encoding="utf-8"))
        assert data["classification"] == "VOLATILE_FIELD_NORMALIZED_RUNTIME_HELPER"
        assert data["excluded_from_sha256sums"] is True
        assert data["immutable_release_constant"] is False
        assert (" " + rel) not in sha_text, rel + " present in SHA256SUMS"
    return True

def main(argv=None):
    validate_runtime_download_helpers()
    print("PASS runtime download helper script classification gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
