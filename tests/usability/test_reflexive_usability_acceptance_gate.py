#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for reflexive usability acceptance and known open conditions."""
from tests.helpers import load_json, repo_path

def test_known_open_conditions_block_false_green_claims():
    """Known open conditions must make overall_green false."""
    known = load_json("canonical/KNOWN_OPEN_CONDITIONS_REGISTER_V27.json")
    verdict = load_json("publication/DELIVERY_VERDICT_V27.json")
    assert known["known_open_condition_count"] > 0
    assert known["green_claim_allowed"] is False
    assert verdict["overall_green"] is False
    assert verdict["allowed_user_facing_summary"] == "LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE"

def test_open_conditions_include_github_runtime_and_windows_field_confirmation():
    """Verify all known open external conditions are explicit."""
    known = load_json("canonical/KNOWN_OPEN_CONDITIONS_REGISTER_V27.json")
    ids = {item["id"] for item in known["conditions"]}
    assert "REAL_WINDOWS_FIELD_CONFIRMATION_V26_PLUS" in ids
    assert "REAL_GITHUB_RELEASE_AUTH_REMOTE_REQUIRED" in ids
    assert "PYTHON_RUNTIME_BINARY_BUNDLING_NOT_EMBEDDED" in ids

def test_reflexive_usability_gate_materialized():
    """Verify gate and checker exist."""
    gate = load_json("canonical/REFLEXIVE_USABILITY_ACCEPTANCE_GATE_V27.json")
    assert gate["gate_id"] == "REFLEXIVE_USABILITY_ACCEPTANCE_AND_KNOWN_OPEN_CONDITIONS_GATE"
    assert "FALSE_COMPLETE_REPAIR_CLAIM_WITH_KNOWN_OPEN_CONDITIONS" in gate["error_classes"]
    checker = repo_path("tools/qikvrt_claim_consistency_gate.py").read_text(encoding="utf-8")
    assert "overall_green=false" in checker
    assert "known open conditions" in checker
