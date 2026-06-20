#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for volatile runtime state materialization."""
from tests.helpers import load_json, repo_path

def test_materialization_gate_exists():
    """Verify V38 gate exists."""
    gate=load_json("canonical/VOLATILE_RUNTIME_STATE_MATERIALIZATION_GATE_V38.json")
    assert gate["gate_id"]=="VOLATILE_RUNTIME_STATE_MATERIALIZATION_GATE"
    assert "VOLATILE_RUNTIME_FILE_REGISTERED_BUT_NOT_MATERIALIZED" in gate["error_classes"]
    assert "runtime/DEPENDENCIES.json" in gate["runtime_volatile_files"]

def test_registered_volatile_runtime_files_exist():
    """Verify every registered volatile runtime file exists."""
    gate=load_json("canonical/VOLATILE_RUNTIME_STATE_MATERIALIZATION_GATE_V38.json")
    for rel in gate["runtime_volatile_files"]:
        path=repo_path(rel)
        assert path.is_file()
        data=load_json(rel)
        assert data["classification"]=="VOLATILE_RUNTIME_STATE"
        assert data["excluded_from_sha256sums"] is True

def test_registered_volatile_runtime_files_not_in_sha256sums():
    """Verify volatile runtime files are not immutable-hashed."""
    gate=load_json("canonical/VOLATILE_RUNTIME_STATE_MATERIALIZATION_GATE_V38.json")
    sha=repo_path("SHA256SUMS.txt").read_text(encoding="utf-8")
    for rel in gate["runtime_volatile_files"]:
        assert (" "+rel) not in sha
