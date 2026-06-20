#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Structured JSONL logger for QIK-VRT launchers."""
from __future__ import annotations
import datetime as dt
import json
import pathlib
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "qikvrt_last_run.jsonl"

def utc_now():
    """Return UTC timestamp."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def json_safe_path(path):
    """Return JSON-safe path using forward slashes."""
    return pathlib.Path(path).as_posix()

def ensure_log_dir():
    """Create log directory."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR

def write_event(event, **fields):
    """Append one valid JSONL event."""
    ensure_log_dir()
    safe_fields = {key: (json_safe_path(value) if isinstance(value, pathlib.Path) else value) for key, value in fields.items()}
    payload = {"timestamp": utc_now(), "event": event, **safe_fields}
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload

def reset_log(launcher):
    """Reset the single machine-readable log for a new run."""
    ensure_log_dir()
    LOG_FILE.write_text("", encoding="utf-8")
    write_event("run_start", launcher=launcher, platform=sys.platform, logfile=json_safe_path(LOG_FILE))
    return LOG_FILE

def log_command_start(command):
    """Log command start."""
    return write_event("command_start", command=command)

def log_stream(stream_name, command, text):
    """Log stdout or stderr."""
    return write_event(stream_name, command=command, text=text)

def log_check_result(check_name, status, exit_code=0, duration_ms=None, error=None):
    """Log check result."""
    payload = {"check_name": check_name, "status": status, "exit_code": int(exit_code)}
    if duration_ms is not None:
        payload["duration_ms"] = int(duration_ms)
    if error:
        payload["error"] = str(error)
    return write_event("check_result", **payload)

def log_repair_hint(error_class, hint, severity="CONTINUE", continue_path="INSPECT_LOG_AND_REPAIR_NEXT_ERROR"):
    """Log repair hint."""
    return write_event("repair_hint", error_class=error_class, hint=hint, severity=severity, continue_path=continue_path)

def finish(exit_code, status=None, continue_path=None):
    """Write canonical run_end with identical field structure for PASS and non-PASS."""
    code = int(exit_code)
    if status is None:
        status = "PASS" if code == 0 else "FAIL"
    if code != 0 and status in {"DONE", "DONE_BY_PYTHON_LAUNCHER", "PASS"}:
        status = "FAIL"
    if code == 0:
        payload = {
            "exit_code": code,
            "status": status,
            "error_class": "NONE",
            "continue_path": "NONE",
            "repair_hint": "NONE",
            "logfile": json_safe_path(LOG_FILE),
        }
    else:
        payload = {
            "exit_code": code,
            "status": status,
            "continue_path": continue_path or "INSPECT_LOG_AND_REPAIR_NEXT_ERROR",
            "error_class": "NONZERO_EXIT",
            "repair_hint": "Inspect target_process_result and repair the underlying failure.",
            "logfile": json_safe_path(LOG_FILE),
        }
    write_event("run_end", **payload)
    return code

def run_logged(label, callable_obj):
    """Run callable and log exception data."""
    start = time.time()
    log_command_start(label)
    try:
        result = callable_obj()
        log_check_result(label, "PASS", 0, int((time.time() - start) * 1000))
        return result
    except Exception as exc:
        log_check_result(label, "FAIL", 1, int((time.time() - start) * 1000), str(exc))
        log_stream("stderr", label, traceback.format_exc())
        log_repair_hint("UNHANDLED_RUNTIME_EXCEPTION", f"Repair failing command: {label}", "BLOCK")
        raise
