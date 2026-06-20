#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for CMD wrapper target stdout/stderr capture."""
from tests.helpers import load_json, repo_path

def test_cmd_wrapper_capture_gate_materialized():
    """Verify V33 capture gate exists."""
    gate = load_json("canonical/CMD_WRAPPER_TARGET_PROCESS_STDOUT_STDERR_CAPTURE_GATE_V33.json")
    assert gate["gate_id"] == "CMD_WRAPPER_TARGET_PROCESS_STDOUT_STDERR_CAPTURE_GATE"
    assert "CMD_WRAPPER_TARGET_FAILURE_WITHOUT_STDOUT_STDERR_EVIDENCE" in gate["error_classes"]
    assert "target_process_result" in gate["rule"]

def test_cmd_uses_target_runner_and_evidence_files():
    """Verify qikvrt.cmd captures target stdout/stderr."""
    text = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert "qikvrt_cmd_target_runner.py" in text
    assert "--stdout-file" in text
    assert "--stderr-file" in text
    assert "target_stdout.txt" in text
    assert "target_stderr.txt" in text

def test_runner_emits_target_process_result():
    """Verify target runner emits required evidence fields."""
    text = repo_path("tools/qikvrt_cmd_target_runner.py").read_text(encoding="utf-8")
    assert '"event": "target_process_result"' in text
    assert "stdout_tail" in text
    assert "stderr_tail" in text
    assert "stdout_file" in text
    assert "stderr_file" in text
