#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate Windows command_start JSON escaping."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def bad_raw_windows_json_sample():
    """Create invalid JSON with raw Windows backslashes without raw source escape hazards."""
    command = "C:" + chr(92) + "Users" + chr(92) + "ingol" + chr(92) + "_script_runner_" + chr(92) + "repo" + chr(92) + "runtime" + chr(92) + "python" + chr(92) + "windows" + chr(92) + "python.exe qikvrt.py master-gate"
    return '{"event":"command_start","command":"' + command + '"}'

def good_json_sample():
    """Create valid JSON with slash-normalized path."""
    return '{"event":"command_start","command":"C:/Users/ingol/_script_runner_/repo/runtime/python/windows/python.exe qikvrt.py master-gate"}'

def validate_cmd_script():
    """Validate qikvrt.cmd slash-normalizes command_start."""
    text = (ROOT / "qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    assert "PY_EXE_JSON=%PY_EXE:" in text and "COMMAND_JSON=%PY_EXE_JSON%" in text, "qikvrt.cmd does not slash-normalize PY_EXE into COMMAND_JSON"
    assert '"command":"%COMMAND_JSON%"' in text, "qikvrt.cmd does not log command_start with COMMAND_JSON"
    assert '"command":"%PY_EXE% qikvrt.py %ARGS%"' not in text, "raw Windows path command_start still present"

def validate_samples():
    """Validate representative good/bad samples."""
    json.loads(good_json_sample())
    failed = False
    try:
        json.loads(bad_raw_windows_json_sample())
    except json.JSONDecodeError:
        failed = True
    assert failed, "bad raw Windows backslash sample unexpectedly parsed"

def validate_log(path):
    """Validate an uploaded or generated log."""
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event") == "command_start":
            command = event.get("command", "")
            assert chr(92) not in command, f"raw backslash in command_start at line {line_number}"
    return True

def main(argv=None):
    """Run gate."""
    argv = argv or []
    validate_cmd_script()
    validate_samples()
    if argv:
        validate_log(pathlib.Path(argv[0]))
    print("PASS Windows command_start JSON escape gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
