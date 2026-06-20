#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Run CMD target process and append machine-readable stdout/stderr evidence."""
from __future__ import annotations
import argparse
import json
import pathlib
import subprocess
import sys
import time

def json_safe_path(path):
    """Return slash-normalized path for JSON."""
    return pathlib.Path(path).as_posix()

def append_jsonl(log_file, event):
    """Append event to JSONL log."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

def classify(exit_code, stdout, stderr):
    """Classify target process failure."""
    combined = (stdout or "") + "\n" + (stderr or "")
    if "Traceback" in combined:
        return "TARGET_EXCEPTION"
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        return "TARGET_IMPORT_FAILED"
    if "SyntaxError" in combined:
        return "TARGET_SYNTAX_ERROR"
    if int(exit_code) != 0:
        return "TARGET_PROCESS_NONZERO_EXIT"
    return "NONE"

def main(argv=None):
    """Run target and log result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True)
    parser.add_argument("--stdout-file", required=True)
    parser.add_argument("--stderr-file", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("target", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if args.target and args.target[0] == "--":
        target = args.target[1:]
    else:
        target = args.target
    if not target:
        raise SystemExit("missing target command")

    log_file = pathlib.Path(args.log)
    stdout_file = pathlib.Path(args.stdout_file)
    stderr_file = pathlib.Path(args.stderr_file)
    stdout_file.parent.mkdir(parents=True, exist_ok=True)
    stderr_file.parent.mkdir(parents=True, exist_ok=True)

    process = subprocess.run(target, cwd=args.cwd, text=True, capture_output=True)
    stdout = process.stdout or ""
    stderr = process.stderr or ""
    stdout_file.write_text(stdout, encoding="utf-8", errors="replace")
    stderr_file.write_text(stderr, encoding="utf-8", errors="replace")

    error_class = classify(process.returncode, stdout, stderr)
    append_jsonl(log_file, {
        "event": "target_process_result",
        "status": "PASS" if process.returncode == 0 else "FAIL",
        "command": " ".join(target).replace("\\", "/"),
        "exit_code": int(process.returncode),
        "stdout_file": json_safe_path(stdout_file),
        "stderr_file": json_safe_path(stderr_file),
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
        "error_class": error_class,
        "continue_path": "NONE" if process.returncode == 0 else "REPAIR_UNDERLYING_TARGET_PROCESS_AND_RERUN_MASTER_GATE",
        "repair_hint": "NONE" if process.returncode == 0 else "Inspect stdout_file and stderr_file for the target process root cause.",
    })
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)
    return int(process.returncode)

if __name__ == "__main__":
    raise SystemExit(main())
