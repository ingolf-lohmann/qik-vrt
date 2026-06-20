#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for Product Owner final artifact delivery override."""
from tests.helpers import load_json, repo_path

def test_product_owner_override_allows_delivery():
    """Verify Product Owner override allows final artifact delivery."""
    gate = load_json("canonical/PRODUCT_OWNER_FINAL_ARTIFACT_DELIVERY_OVERRIDE_GATE_V31.json")
    verdict = load_json("publication/FINAL_ARTIFACT_DELIVERY_VERDICT_V31.json")
    assert gate["product_owner_override"] is True
    assert gate["artifact_delivery_allowed"] is True
    assert verdict["delivery_status"] == "FINAL_ARTIFACT_DELIVERY_AUTHORIZED_BY_PRODUCT_OWNER_OVERRIDE"
    assert verdict["artifact_delivery_allowed"] is True

def test_owner_override_does_not_create_false_external_claims():
    """Verify external evidence claims remain false."""
    gate = load_json("canonical/PRODUCT_OWNER_FINAL_ARTIFACT_DELIVERY_OVERRIDE_GATE_V31.json")
    verdict = load_json("publication/FINAL_ARTIFACT_DELIVERY_VERDICT_V31.json")
    assert gate["external_evidence_claims"] is False
    assert gate["no_false_external_claims"] is True
    assert verdict["external_evidence_claims"] is False
    assert "REAL_GITHUB_RELEASE_AUTH_REMOTE_REQUIRED" in verdict["external_conditions_not_claimed_as_completed"]

def test_override_tool_exists():
    """Verify override gate tool exists."""
    text = repo_path("tools/qikvrt_product_owner_delivery_override_gate.py").read_text(encoding="utf-8")
    assert "product_owner_override" in text
    assert "artifact_delivery_allowed" in text
    assert "external_evidence_claims" in text
