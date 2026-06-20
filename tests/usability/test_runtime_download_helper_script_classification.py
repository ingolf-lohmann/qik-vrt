#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for runtime download helper script classification."""
from tests.helpers import load_json, repo_path

def test_runtime_download_helper_gate_materialized():
    gate = load_json("canonical/RUNTIME_DOWNLOAD_HELPER_SCRIPT_CLASSIFICATION_GATE_V42.json")
    assert gate["gate_id"] == "RUNTIME_DOWNLOAD_HELPER_SCRIPT_CLASSIFICATION_GATE"
    assert "RUNTIME_DOWNLOAD_POWERSHELL_SCRIPT_HASH_MISMATCH_AFTER_FIELD_RUN" in gate["error_classes"]
    assert "runtime/download_python_runtime.ps1" in gate["runtime_helper_files"]

def test_runtime_download_helper_policy():
    policy = load_json("runtime/download_python_runtime.policy.json")
    assert policy["path"] == "runtime/download_python_runtime.ps1"
    assert policy["classification"] == "VOLATILE_FIELD_NORMALIZED_RUNTIME_HELPER"
    assert policy["excluded_from_sha256sums"] is True

def test_runtime_download_helper_not_in_sha256sums():
    sha = repo_path("SHA256SUMS.txt").read_text(encoding="utf-8")
    assert " runtime/download_python_runtime.ps1" not in sha
