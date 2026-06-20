#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate CMD wrapper target stdout/stderr capture."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = ["command", "exit_code", "stdout_file", "stderr_file", "stdout_tail", "stderr_tail", "error_class", "repair_hint", "continue_path"]

def validate_cmd_script():
    """Validate qikvrt.cmd uses target runner."""
    text = (ROOT / "qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert "qikvrt_cmd_target_runner.py" in text, "CMD wrapper does not use target runner"
    assert "--stdout-file" in text and "--stderr-file" in text, "stdout/stderr files not passed"
    assert "INSPECT_TARGET_PROCESS_RESULT" in text, "wrapper does not point to target_process_result"

def validate_runner_script():
    """Validate target runner emits target_process_result."""
    text = (ROOT / "tools" / "qikvrt_cmd_target_runner.py").read_text(encoding="utf-8", errors="ignore")
    assert '"event": "target_process_result"' in text, "runner lacks target_process_result"
    for field in REQUIRED_FIELDS:
        assert field in text, "runner missing field: " + field

def validate_log(path):
    """Validate log has target_process_result after command_start and before wrapper end."""
    events = [json.loads(line) for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    indexes = {name: [i for i, e in enumerate(events) if e.get("event") == name] for name in ["command_start", "target_process_result", "cmd_wrapper_end", "run_end"]}
    if indexes["command_start"]:
        assert indexes["target_process_result"], "target_process_result missing after command_start"
        assert indexes["command_start"][0] < indexes["target_process_result"][0], "target_process_result before command_start"
        if indexes["cmd_wrapper_end"]:
            assert indexes["target_process_result"][0] < indexes["cmd_wrapper_end"][0], "target_process_result after cmd_wrapper_end"
        target = events[indexes["target_process_result"][0]]
        for field in REQUIRED_FIELDS:
            assert field in target, "target_process_result missing field: " + field
    return True

def main(argv=None):
    """Run gate."""
    argv = argv or []
    validate_cmd_script()
    validate_runner_script()
    if argv:
        validate_log(pathlib.Path(argv[0]))
    print("PASS CMD wrapper target stdout/stderr capture gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
