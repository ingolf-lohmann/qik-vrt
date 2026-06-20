#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for CMD wrapper interpreter probe and 9009 capture."""
from tests.helpers import load_json, repo_path

def test_interpreter_probe_gate_materialized():
    gate=load_json("canonical/CMD_WRAPPER_INTERPRETER_PROBE_AND_9009_CAPTURE_GATE_V39.json")
    assert gate["gate_id"]=="CMD_WRAPPER_INTERPRETER_PROBE_AND_9009_CAPTURE_GATE"
    assert "CMD_WRAPPER_EXIT_9009_WITHOUT_TARGET_PROCESS_RESULT" in gate["error_classes"]
    assert "COMMAND_START_LOGGED_BEFORE_INTERPRETER_PROBE" in gate["error_classes"]

def test_cmd_probes_before_command_start():
    text=repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert ":TRY_PY" in text
    assert '"event":"interpreter_probe"' in text
    assert text.find('"event":"interpreter_probe"') < text.find('"event":"command_start"')
    assert "PYTHON_RUNTIME_NOT_FOUND_OR_NOT_EXECUTABLE" in text

def test_cmd_synthesizes_target_process_result_for_9009():
    text=repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert 'if "%EXITCODE%"=="9009"' in text
    assert "CMD_WRAPPER_EXIT_9009_WITHOUT_TARGET_PROCESS_RESULT" in text
    assert '"event":"target_process_result"' in text
