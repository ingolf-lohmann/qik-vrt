#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for initial launcher acceptance before any effect."""
from tests.helpers import load_json, repo_path

def test_initial_acceptance_gate_exists():
    """Verify initial acceptance gate is materialized."""
    gate = load_json("canonical/INITIAL_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT_GATE_V29.json")
    assert gate["gate_id"] == "INITIAL_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT_GATE"
    assert "command_start" in gate["effectful_events"]
    assert gate["no_acceptance_status"] == "CONTINUE_ACCEPTANCE_REQUIRED"

def test_cmd_blocks_command_start_before_acceptance():
    """Verify qikvrt.cmd checks acceptance before command_start."""
    text = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert "acceptance_required" in text
    assert "CONTINUE_ACCEPTANCE_REQUIRED" in text
    assert "Run qikvrt.cmd accept before executing master-gate" in text
    assert text.index("if not exist") < text.index('echo {"event":"command_start"')

def test_python_launcher_requires_acceptance_before_run_command():
    """Verify qikvrt.py requires acceptance before run_command."""
    text = repo_path("qikvrt.py").read_text(encoding="utf-8")
    assert "qikvrt_initial_acceptance_gate" in text
    assert "require_acceptance" in text
    assert text.index("require_acceptance") < text.index("run_command")

def test_acceptance_validator_tool_exists():
    """Verify validator can detect ordering."""
    text = repo_path("tools/qikvrt_initial_acceptance_gate.py").read_text(encoding="utf-8")
    assert "validate_log_order" in text
    assert "effectful event occurred before persisted acceptance" in text
    assert "persist_acceptance" in text
