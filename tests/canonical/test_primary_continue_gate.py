#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: canonical repository must not dead-block."""
from tests.helpers import load_json, repo_path

REQUIRED = [
    "blocking_gate", "error_class", "human_readable_reason", "machine_readable_reason",
    "continue_path", "repair_hint", "next_responsible_action", "required_consent",
    "license_or_rights_context", "provenance_requirement", "retry_or_rebuild_path",
    "logfile", "evidence_file", "exit_code"
]

def test_primary_continue_gate_is_rank_one():
    """Verify primary canonical continue gate is rank 1 and active."""
    gate = load_json("canonical/CANONICAL_PRIMARY_ACCEPTANCE_GATE.json")
    assert gate["rank"] == 1
    assert gate["gate_id"] == "CANONICAL_CONTINUE_PATH_PRIMARY_ACCEPTANCE_GATE"
    assert gate["status"] == "ACTIVE_PRIMARY_GATE"
    assert "dead_block" in gate["must_not"]

def test_responsible_block_event_has_continue_path():
    """Verify block example includes required continue fields."""
    event = load_json("canonical/EXAMPLE_RESPONSIBLE_BLOCK_EVENT.json")
    assert repo_path("canonical/EXAMPLE_RESPONSIBLE_BLOCK_EVENT.json").is_file()
    for key in REQUIRED:
        assert key in event
        assert event[key] not in ("", None)
    assert event["continue_path"] != "NONE"
    assert event["exit_code"] in (1, 20, 9009)
