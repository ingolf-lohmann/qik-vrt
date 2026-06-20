#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate CMD wrapper interpreter probe and 9009 capture."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
CMD=ROOT/"qikvrt.cmd"

def validate_cmd():
    """Validate qikvrt.cmd probes interpreter before command_start and captures 9009."""
    text=CMD.read_text(encoding="utf-8", errors="ignore")
    assert ":TRY_PY" in text, "interpreter probe function missing"
    assert '"event":"interpreter_probe"' in text, "interpreter_probe event missing"
    assert text.find('echo {"event":"interpreter_probe"') < text.find('echo {"event":"command_start"'), "command_start logged before interpreter_probe"
    assert 'CMD_WRAPPER_EXIT_9009_WITHOUT_TARGET_PROCESS_RESULT' in text, "9009 error class missing"
    assert '"event":"target_process_result"' in text, "synthetic target_process_result missing"
    assert 'PYTHON_RUNTIME_NOT_FOUND_OR_NOT_EXECUTABLE' in text, "runtime unusable class missing"

def validate_log(path):
    """Validate a log with command_start nonzero wrapper has target_process_result."""
    events=[json.loads(line) for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    has_cmd=any(e.get("event")=="command_start" for e in events)
    fail_9009=any(e.get("event") in {"cmd_wrapper_end","run_end"} and e.get("exit_code")==9009 for e in events)
    if has_cmd and fail_9009:
        assert any(e.get("event")=="target_process_result" for e in events), "9009 without target_process_result"
    return True

def main(argv=None):
    argv=argv or []
    validate_cmd()
    if argv:
        validate_log(pathlib.Path(argv[0]))
    print("PASS CMD wrapper interpreter probe and 9009 capture gate")
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
