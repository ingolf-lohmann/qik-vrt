#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Synthetic shift-left launcher regression harness, self-contained and bounded."""
from __future__ import annotations
import json
import pathlib
import tempfile

DONE_LIKE = {"DONE", "DONE_BY_PYTHON_LAUNCHER", "PASS_DONE"}
FINAL_ADAPTER_EVENTS = {"cmd_wrapper_end", "ps1_wrapper_end", "sh_wrapper_end"}

def write_log(path, events):
    """Write a JSONL log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n", encoding="utf-8")

def validate_file(path):
    """Validate JSONL log without repository imports."""
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(event.get("event") == "run_start" for event in events), "missing run_start"
    assert any(event.get("event") == "command_start" for event in events), "missing command_start"
    run_ends = [event for event in events if event.get("event") == "run_end"]
    assert len(run_ends) == 1, f"expected exactly one run_end, got {len(run_ends)}"
    run_end = run_ends[0]
    for field in ["status", "exit_code", "error_class", "continue_path", "repair_hint", "logfile"]:
        assert field in run_end, f"run_end missing field: {field}"
    if int(run_end["exit_code"]) != 0:
        assert run_end["status"] not in DONE_LIKE and run_end["status"] != "PASS"
        assert run_end["continue_path"]
        assert run_end["repair_hint"]
    if any(event.get("event") in FINAL_ADAPTER_EVENTS for event in events):
        assert events[-1].get("event") == "run_end", "adapter end must be followed by canonical run_end"

def scenario_cmd_failure_with_run_end(tmp):
    """Simulate cmd failure with wrapper end followed by canonical run_end."""
    log = tmp / "cmd_failure.jsonl"
    write_log(log, [
        {"event":"run_start","launcher":"qikvrt.cmd","args":"master-gate","default_command":"master-gate","dependency_contract":"GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_GATE"},
        {"event":"command_start","command":"python qikvrt.py master-gate"},
        {"event":"cmd_wrapper_end","status":"FAIL","exit_code":1,"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_LOG_AND_REPAIR_NEXT_ERROR","repair_hint":"Inspect logs/qikvrt_last_run.jsonl."},
        {"event":"run_end","status":"FAIL","exit_code":1,"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_LOG_AND_REPAIR_NEXT_ERROR","repair_hint":"Inspect logs/qikvrt_last_run.jsonl.","logfile":"logs/qikvrt_last_run.jsonl"},
    ])
    validate_file(log)

def scenario_missing_runtime_continue(tmp):
    """Simulate missing runtime with continue run_end."""
    log = tmp / "missing_runtime.jsonl"
    write_log(log, [
        {"event":"run_start","launcher":"qikvrt.sh","default_command":"master-gate"},
        {"event":"command_start","command":"resolve python runtime"},
        {"event":"sh_wrapper_end","status":"CONTINUE","exit_code":20,"error_class":"PYTHON_RUNTIME_NOT_RESOLVED","continue_path":"INSTALL_OR_BUNDLE_RUNTIME","repair_hint":"Install Python 3 or bundle runtime."},
        {"event":"run_end","status":"CONTINUE","exit_code":20,"error_class":"PYTHON_RUNTIME_NOT_RESOLVED","continue_path":"INSTALL_OR_BUNDLE_RUNTIME","repair_hint":"Install Python 3 or bundle runtime.","logfile":"logs/qikvrt_last_run.jsonl"},
    ])
    validate_file(log)

def scenario_bad_wrapper_without_run_end(tmp):
    """Ensure old bug is rejected."""
    log = tmp / "bad_wrapper_without_run_end.jsonl"
    write_log(log, [
        {"event":"run_start","launcher":"qikvrt.cmd","args":"master-gate"},
        {"event":"command_start","command":"python qikvrt.py master-gate"},
        {"event":"cmd_wrapper_end","status":"FAIL","exit_code":1,"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_LOG_AND_REPAIR_NEXT_ERROR","repair_hint":"Inspect logs/qikvrt_last_run.jsonl."},
    ])
    rejected = False
    try:
        validate_file(log)
    except AssertionError:
        rejected = True
    assert rejected, "old wrapper-without-run_end bug was not rejected"

def main():
    """Run all synthetic regression scenarios."""
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        scenario_cmd_failure_with_run_end(tmp)
        scenario_missing_runtime_continue(tmp)
        scenario_bad_wrapper_without_run_end(tmp)
    print("PASS shift-left launcher regression harness")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
