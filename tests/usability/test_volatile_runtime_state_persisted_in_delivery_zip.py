#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for volatile runtime state persisted in delivery ZIP."""
from tests.helpers import load_json, repo_path

def test_delivery_zip_gate_materialized():
    """Verify V40 gate exists."""
    gate = load_json("canonical/VOLATILE_RUNTIME_STATE_PERSISTED_IN_DELIVERY_ZIP_GATE_V40.json")
    assert gate["gate_id"] == "VOLATILE_RUNTIME_STATE_PERSISTED_IN_DELIVERY_ZIP_GATE"
    assert "VOLATILE_RUNTIME_STATE_MATERIALIZATION_NOT_PERSISTED_IN_DELIVERY_ZIP" in gate["error_classes"]
    assert "runtime/DEPENDENCIES.json" in gate["required_runtime_state_files"]

def test_required_runtime_state_files_exist_before_zip():
    """Verify required volatile runtime files exist."""
    gate = load_json("canonical/VOLATILE_RUNTIME_STATE_PERSISTED_IN_DELIVERY_ZIP_GATE_V40.json")
    for rel in gate["required_runtime_state_files"]:
        path = repo_path(rel)
        assert path.is_file()
        data = load_json(rel)
        assert data["classification"] == "VOLATILE_RUNTIME_STATE"
        assert data["excluded_from_sha256sums"] is True
        assert data["must_exist_in_delivery_zip"] is True

def test_required_runtime_state_files_not_in_sha256sums():
    """Verify required volatile runtime files are excluded from immutable SHA256SUMS."""
    gate = load_json("canonical/VOLATILE_RUNTIME_STATE_PERSISTED_IN_DELIVERY_ZIP_GATE_V40.json")
    sha = repo_path("SHA256SUMS.txt").read_text(encoding="utf-8")
    for rel in gate["required_runtime_state_files"]:
        assert (" " + rel) not in sha
