#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression tests for JSONL log validity and exit-state semantics."""
from tests.helpers import repo_path, load_json

def test_windows_cmd_uses_json_safe_forward_slash_log_path():
    """Verify CMD uses LOG_JSON_PATH and no DONE-like nonzero status."""
    cmd = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert "LOG_JSON_PATH" in cmd
    assert "%LOG_FILE:\\=/%" in cmd
    assert "DONE_BY_PYTHON_LAUNCHER" not in cmd
    assert '"status":"FAIL"' in cmd
    assert "continue_path" in cmd

def test_validator_rejects_done_status_for_nonzero_exit_and_accepts_good_log():
    """Verify schema and example valid log semantics."""
    schema = load_json("canonical/JSONL_LOG_EVENT_SCHEMA_V21.json")
    example = load_json("canonical/EXAMPLE_VALID_WINDOWS_JSONL_LOG.json")
    assert "DONE_BY_PYTHON_LAUNCHER" in schema["forbidden_done_status_for_nonzero_exit"]
    events = example["events"]
    assert all(isinstance(event, dict) for event in events)
    run_end = [event for event in events if event.get("event") == "run_end"][0]
    assert run_end["exit_code"] != 0
    assert run_end["status"] == "FAIL"
    assert run_end["continue_path"]

def test_powershell_uses_json_safe_log_path_and_fail_status():
    """Verify PowerShell wrapper uses JSON-safe path and FAIL on missing runtime."""
    ps1 = repo_path("qikvrt.ps1").read_text(encoding="utf-8", errors="ignore")
    assert 'Replace("\\", "/")' in ps1 or 'Replace("\", "/")' in ps1
    assert '"status":"FAIL"' in ps1
    assert "DONE_BY_PYTHON_LAUNCHER" not in ps1
    assert "continue_path" in ps1
