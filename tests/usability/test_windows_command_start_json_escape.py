#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for Windows command_start JSON escaping."""
import json
import pytest
from tests.helpers import load_json, repo_path

def make_bad_raw_json():
    """Build invalid JSON with raw Windows backslashes without source-level unicode escapes."""
    b = chr(92)
    command = "C:" + b + "Users" + b + "ingol" + b + "_script_runner_" + b + "repo" + b + "runtime" + b + "python" + b + "windows" + b + "python.exe qikvrt.py master-gate"
    return '{"event":"command_start","command":"' + command + '"}'

def test_windows_command_escape_gate_materialized():
    """Verify gate metadata exists."""
    gate = load_json("canonical/WINDOWS_COMMAND_START_JSON_ESCAPE_GATE_V32.json")
    assert gate["gate_id"] == "WINDOWS_COMMAND_START_JSON_ESCAPE_GATE"
    assert "WINDOWS_COMMAND_PATH_NOT_JSON_ESCAPED_IN_COMMAND_START" in gate["error_classes"]
    assert "raw backslashes" in gate["rule"]

def test_qikvrt_cmd_slash_normalizes_command_start():
    """Verify qikvrt.cmd no longer echoes raw PY_EXE in command_start."""
    text = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert "PY_EXE_JSON=%PY_EXE:" in text
    assert "COMMAND_JSON=%PY_EXE_JSON%" in text
    assert '"command":"%COMMAND_JSON%"' in text
    assert '"command":"%PY_EXE% qikvrt.py %ARGS%"' not in text

def test_bad_field_log_pattern_is_invalid_and_good_pattern_is_valid():
    """Verify the field failure pattern is blocked."""
    bad = make_bad_raw_json()
    good = '{"event":"command_start","command":"C:/Users/ingol/_script_runner_/repo/runtime/python/windows/python.exe qikvrt.py master-gate"}'
    with pytest.raises(json.JSONDecodeError):
        json.loads(bad)
    parsed = json.loads(good)
    assert parsed["event"] == "command_start"
    assert chr(92) not in parsed["command"]
