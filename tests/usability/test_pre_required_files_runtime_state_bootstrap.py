#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for pre-required-files runtime state bootstrap."""
from tests.helpers import load_json, repo_path

def test_pre_required_files_bootstrap_gate_materialized():
    gate = load_json("canonical/PRE_REQUIRED_FILES_RUNTIME_STATE_BOOTSTRAP_GATE_V41.json")
    assert gate["gate_id"] == "PRE_REQUIRED_FILES_RUNTIME_STATE_BOOTSTRAP_GATE"
    assert "REQUIRED_FILES_CHECK_RUNS_BEFORE_RUNTIME_STATE_MATERIALIZATION" in gate["error_classes"]
    assert "runtime/DEPENDENCIES.json" in gate["required_runtime_state_files"]

def test_master_gate_runs_bootstrap_before_required_files():
    text = repo_path("tools/qikvrt_master_acceptance_gate.py").read_text(encoding="utf-8")
    assert "pre_required_files_bootstrap, check_required_files" in text
    assert "spec_from_file_location" in text

def test_required_runtime_state_files_exist():
    gate = load_json("canonical/PRE_REQUIRED_FILES_RUNTIME_STATE_BOOTSTRAP_GATE_V41.json")
    for rel in gate["required_runtime_state_files"]:
        path = repo_path(rel)
        assert path.is_file()
        data = load_json(rel)
        assert data["classification"] == "VOLATILE_RUNTIME_STATE"
        assert data["excluded_from_sha256sums"] is True
