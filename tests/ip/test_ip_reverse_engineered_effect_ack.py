#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for IP reverse engineered / EFFECT_ACK materialization."""
from tests.helpers import load_json, repo_path

def test_ip_reverse_engineered_model_is_materialized():
    """Verify TCP/IP operational principles are mapped to QIK-VRT repository behavior."""
    model = load_json("canonical/IP_REVERSE_ENGINEERED_QIKVRT_MODEL.json")
    assert model["schema"] == "qikvrt_ip_reverse_engineered_model_v24"
    assert "IP Reverse Engineered" in model["claim"]
    assert "precision_boundary" in model
    assert "addressing" in model["tcp_ip_operational_principles"]
    assert "acknowledgement" in model["tcp_ip_operational_principles"]
    assert "responsible_continue_path" in model["tcp_ip_operational_principles"]
    assert model["qed"].endswith("Ingolf Lohmann")

def test_ietf_draft_provenance_is_recorded():
    """Verify IETF draft provenance and EFFECT_ACK protocol anchor."""
    prov = load_json("external/ietf/draft-lohmann-qikvrt-effect-ack-00.PROVENANCE.json")
    summary = load_json("external/ietf/EFFECT_ACK_PROTOCOL_SUMMARY.json")
    assert prov["internet_draft"] == "draft-lohmann-qikvrt-effect-ack-00"
    assert prov["title"] == "The QIK-VRT Effect Acknowledgement Protocol"
    assert prov["intended_status"] == "Experimental"
    assert prov["key_protocol_distinction"] == "TRANSPORT_ACK != EFFECT_ACK"
    assert "EFFECT_ACK_DONE" in summary["states"]
    assert summary["responsibility_protocol_required"] is True

def test_runtime_bundling_attempt_and_no_false_github_claim():
    """Verify Python runtime attempt is recorded and GitHub arrival is not falsely claimed."""
    runtime = load_json("runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json")
    github = load_json("publication/GITHUB_READY_BUT_NOT_PUSHED_V24.json")
    assert runtime["runtime_bundled"] is False
    assert runtime["status"].startswith("CONTINUE_")
    assert runtime["continue_path"]
    assert github["github_ready"] is True
    assert github["github_arrived"] is False
    assert github["release_url"] is None
    assert repo_path(".github/workflows/qikvrt-v24-verify.yml").is_file()
