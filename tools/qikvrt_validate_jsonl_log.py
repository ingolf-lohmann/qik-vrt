#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate QIK-VRT JSONL log machine readability and canonical finalization."""
from __future__ import annotations
import json
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "logs" / "qikvrt_last_run.jsonl"
DONE_LIKE = {"DONE", "DONE_BY_PYTHON_LAUNCHER", "PASS_DONE"}
FINAL_ADAPTER_EVENTS = {"cmd_wrapper_end", "ps1_wrapper_end", "sh_wrapper_end"}
def parse_jsonl(path):
    """Parse all JSONL lines."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def validate_events(events):
    """Validate required events and canonical finalization."""
    assert events, "log has no events"
    assert any(event.get("event") == "run_start" for event in events), "missing run_start"
    assert any(event.get("event") == "command_start" for event in events), "missing command_start"
    run_ends = [event for event in events if event.get("event") == "run_end"]
    assert len(run_ends) == 1, f"expected exactly one run_end, got {len(run_ends)}"
    run_end = run_ends[0]
    for field in ["status", "exit_code", "error_class", "continue_path", "repair_hint", "logfile"]:
        assert field in run_end, f"run_end missing field: {field}"
    code = int(run_end.get("exit_code", 0))
    status = run_end.get("status", "")
    if code == 0:
        assert status == "PASS", "zero exit should be PASS"
        assert run_end["error_class"] == "NONE"
        assert run_end["continue_path"] == "NONE"
        assert run_end["repair_hint"] == "NONE"
    else:
        assert status not in DONE_LIKE and status != "PASS", f"nonzero exit has misleading status: {status}"
        assert run_end.get("continue_path") not in ("", None), "nonzero exit lacks continue_path"
        assert run_end.get("repair_hint") not in ("", None), "nonzero exit lacks repair_hint"
    if any(event.get("event") in FINAL_ADAPTER_EVENTS for event in events):
        assert events[-1].get("event") == "run_end", "adapter end must be followed by canonical run_end as final event"
def validate_file(path):
    """Validate JSONL file."""
    events = parse_jsonl(path)
    validate_events(events)
    return events
def main(argv=None):
    """Run validator."""
    path = pathlib.Path(argv[0]) if argv else DEFAULT_LOG
    validate_file(path)
    print(f"PASS valid canonical JSONL log: {path}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
