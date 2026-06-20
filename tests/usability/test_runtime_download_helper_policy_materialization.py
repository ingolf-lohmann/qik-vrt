#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for runtime download helper policy materialization."""
from tests.helpers import load_json, repo_path
def test_policy_materialization_gate_exists():
    gate=load_json("canonical/RUNTIME_DOWNLOAD_HELPER_POLICY_MATERIALIZATION_GATE_V43.json")
    assert gate["gate_id"]=="RUNTIME_DOWNLOAD_HELPER_POLICY_MATERIALIZATION_GATE"
    assert "RUNTIME_DOWNLOAD_HELPER_POLICY_REGISTERED_BUT_NOT_MATERIALIZED" in gate["error_classes"]
    assert "runtime/download_python_runtime.policy.json" in gate["runtime_helper_policy_files"]
def test_policy_file_exists_and_matches_helper():
    policy=load_json("runtime/download_python_runtime.policy.json")
    assert repo_path("runtime/download_python_runtime.ps1").is_file()
    assert repo_path("runtime/download_python_runtime.policy.json").is_file()
    assert policy["path"]=="runtime/download_python_runtime.ps1"
    assert policy["classification"]=="VOLATILE_FIELD_NORMALIZED_RUNTIME_HELPER"
    assert policy["excluded_from_sha256sums"] is True
def test_policy_not_in_sha256sums():
    sha=repo_path("SHA256SUMS.txt").read_text(encoding="utf-8")
    assert " runtime/download_python_runtime.ps1" not in sha
    assert " runtime/download_python_runtime.policy.json" not in sha
