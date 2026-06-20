#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Root-cause logging helpers for QIK-VRT target process failures."""
from __future__ import annotations
import json, pathlib, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "logs" / "qikvrt_last_run.jsonl"
EVIDENCE_FILE = ROOT / "evidence" / "target_process_failure_root_cause.json"
def json_safe_path(path):
    """Return JSON-safe path."""
    return pathlib.Path(path).as_posix()
def append_event(event):
    """Append one event to JSONL log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload
def classify_failure(exit_code, stdout, stderr):
    """Classify target failure."""
    combined = (stdout or "") + "\n" + (stderr or "")
    if "hash mismatch" in combined:
        return "STATIC_HASH_MANIFEST_CONTAINS_VOLATILE_RUNTIME_ARTIFACT"
    if "AssertionError" in combined:
        return "TARGET_ASSERTION_FAILED"
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        return "TARGET_IMPORT_FAILED"
    if "Traceback" in combined:
        return "TARGET_EXCEPTION"
    if int(exit_code) != 0:
        return "TARGET_PROCESS_NONZERO_EXIT"
    return "NONE"
def record_target_process_result(command, target_script, working_directory, exit_code, stdout, stderr):
    """Record target process result with root-cause evidence."""
    error_class = classify_failure(exit_code, stdout, stderr)
    status = "PASS" if int(exit_code) == 0 else "FAIL"
    check_result = {
        "event":"target_process_result",
        "status":status,
        "command":command,
        "target_script":target_script,
        "working_directory":json_safe_path(working_directory),
        "exit_code":int(exit_code),
        "stdout":stdout or "",
        "stderr":stderr or "",
        "stdout_tail":(stdout or "")[-4000:],
        "stderr_tail":(stderr or "")[-4000:],
        "check_result":status,
        "error_class":error_class,
        "repair_hint":"Inspect target_process_result stdout/stderr and repair the underlying target script or gate.",
        "continue_path":"REPAIR_UNDERLYING_TARGET_PROCESS_AND_RERUN_MASTER_GATE",
        "evidence_file":json_safe_path(EVIDENCE_FILE)
    }
    append_event(check_result)
    EVIDENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_FILE.write_text(json.dumps(check_result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return check_result
