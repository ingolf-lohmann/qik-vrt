#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for runtime/DEPENDENCIES.json volatile classification."""
from tests.helpers import load_json, repo_path

def test_runtime_dependencies_gate_materialized():
    """Verify V35 gate exists."""
    gate = load_json("canonical/RUNTIME_DEPENDENCIES_JSON_VOLATILE_CLASSIFICATION_GATE_V35.json")
    assert gate["gate_id"] == "RUNTIME_DEPENDENCIES_JSON_VOLATILE_OR_IMMUTABLE_CLASSIFICATION_GATE"
    assert "RUNTIME_DEPENDENCIES_JSON_HASH_MISMATCH_AFTER_FIELD_RUN" in gate["error_classes"]
    assert "runtime/DEPENDENCIES.json" in gate["volatile_runtime_paths_must_include"]

def test_runtime_dependencies_json_marked_volatile():
    """Verify runtime/DEPENDENCIES.json is runtime state."""
    data = load_json("runtime/DEPENDENCIES.json")
    assert data["classification"] == "VOLATILE_RUNTIME_DEPENDENCY_STATE"
    assert data["immutable_release_constant"] is False
    assert data["excluded_from_sha256sums"] is True

def test_runtime_dependencies_not_in_sha256sums():
    """Verify volatile dependency state is not hashed immutable."""
    text = repo_path("SHA256SUMS.txt").read_text(encoding="utf-8")
    assert " runtime/DEPENDENCIES.json" not in text
