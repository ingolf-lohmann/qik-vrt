#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for runtime attempt/state volatile classification."""
from tests.helpers import load_json, repo_path

def test_runtime_attempt_gate_materialized():
    """Verify V37 gate exists."""
    gate = load_json("canonical/RUNTIME_ATTEMPT_STATE_VOLATILE_CLASSIFICATION_GATE_V37.json")
    assert gate["gate_id"] == "PYTHON_RUNTIME_BUNDLING_ATTEMPT_VOLATILE_CLASSIFICATION_GATE"
    assert "PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24_HASH_MISMATCH_AFTER_FIELD_RUN" in gate["error_classes"]
    assert "runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json" in gate["runtime_volatile_files"]

def test_runtime_attempt_state_files_marked_volatile():
    """Verify runtime attempt/state files are volatile."""
    gate = load_json("canonical/RUNTIME_ATTEMPT_STATE_VOLATILE_CLASSIFICATION_GATE_V37.json")
    for rel in gate["runtime_volatile_files"]:
        data = load_json(rel)
        assert data["classification"] == "VOLATILE_RUNTIME_STATE"
        assert data["immutable_release_constant"] is False
        assert data["excluded_from_sha256sums"] is True

def test_runtime_attempt_state_not_in_sha256sums():
    """Verify runtime attempt/state files are not in immutable SHA256SUMS."""
    gate = load_json("canonical/RUNTIME_ATTEMPT_STATE_VOLATILE_CLASSIFICATION_GATE_V37.json")
    sha = repo_path("SHA256SUMS.txt").read_text(encoding="utf-8")
    for rel in gate["runtime_volatile_files"]:
        assert (" " + rel) not in sha
