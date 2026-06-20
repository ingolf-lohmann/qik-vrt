#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for assistant delivery response consistency."""
from tests.helpers import load_json, repo_path

def test_delivery_verdict_blocks_overall_green():
    """Verify delivery verdict is not overall green when open conditions remain."""
    verdict = load_json("publication/DELIVERY_VERDICT_V28.json")
    assert verdict["overall_green"] is False
    assert verdict["known_open_condition_count"] == 3
    assert verdict["response_layer_status"] == "LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE"

def test_response_gate_forbids_unqualified_fixed_claims():
    """Verify forbidden phrases and required limited status are materialized."""
    gate = load_json("canonical/ASSISTANT_DELIVERY_RESPONSE_CONSISTENCY_GATE_V28.json")
    assert "ASSISTANT_DELIVERY_TEXT_CONTRADICTS_OWN_KNOWN_OPEN_CONDITIONS_GATE" in gate["error_classes"]
    assert "der Fehler wurde behoben" in gate["forbidden_unqualified_phrases_when_open"]
    assert gate["required_status_when_open"] == "LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE"

def test_candidate_safe_delivery_response_is_limited():
    """Verify candidate response contains limited status and explicit open state."""
    text = repo_path("publication/CANDIDATE_SAFE_DELIVERY_RESPONSE_V28.txt").read_text(encoding="utf-8")
    assert "V28_LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE" in text
    assert "overall_green=false" in text
    assert "known_open_condition_count=3" in text
    assert "known open conditions remain" in text
