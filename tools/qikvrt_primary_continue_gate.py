#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Primary canonical continue-path acceptance gate."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_BLOCK_FIELDS = [
    "blocking_gate", "error_class", "human_readable_reason", "machine_readable_reason",
    "continue_path", "repair_hint", "next_responsible_action", "required_consent",
    "license_or_rights_context", "provenance_requirement", "retry_or_rebuild_path",
    "logfile", "evidence_file", "exit_code"
]

def load_json(relative):
    """Load a JSON document from repository root."""
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))

def validate_primary_gate():
    """Validate primary gate declaration."""
    gate = load_json("canonical/CANONICAL_PRIMARY_ACCEPTANCE_GATE.json")
    assert gate["rank"] == 1
    assert gate["gate_id"] == "CANONICAL_CONTINUE_PATH_PRIMARY_ACCEPTANCE_GATE"
    assert gate["status"] == "ACTIVE_PRIMARY_GATE"
    assert "dead_block" in gate["must_not"]
    assert set(REQUIRED_BLOCK_FIELDS) <= set(gate["every_block_must_include"])

def validate_continue_schema():
    """Validate continue path schema."""
    schema = load_json("canonical/CONTINUE_PATH_SCHEMA.json")
    assert set(REQUIRED_BLOCK_FIELDS) <= set(schema["required_fields"])
    assert "20" in schema["valid_exit_semantics"]

def validate_example_block_event():
    """Validate example block event has all fields and a continue path."""
    event = load_json("canonical/EXAMPLE_RESPONSIBLE_BLOCK_EVENT.json")
    for field in REQUIRED_BLOCK_FIELDS:
        assert field in event and event[field] not in ("", None)
    assert event["continue_path"] != "NONE"
    assert event["exit_code"] in (1, 20, 9009)

def main():
    """Run primary continue gate."""
    validate_primary_gate()
    validate_continue_schema()
    validate_example_block_event()
    print("PASS primary canonical continue gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
