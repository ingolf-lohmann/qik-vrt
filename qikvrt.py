#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""QIK-VRT V34 launcher: repository-root bootstrap before local tools imports."""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_runtime_logger as qlog
from tools import qikvrt_initial_acceptance_gate as initial_acceptance

DEFAULT_COMMAND = "master-gate"
COMMANDS = {
    "master-gate": ["tools/qikvrt_master_acceptance_gate.py"],
    "cicd-publish": ["tools/qikvrt_cicd_publish.py"],
}

def build_parser():
    """Build parser."""
    parser = argparse.ArgumentParser(description="QIKVRT V34 launcher. Acceptance is required before any effect.")
    parser.add_argument("command", nargs="?", default=DEFAULT_COMMAND, choices=sorted(COMMANDS))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser

def normalize_extra_args(raw_args):
    """Normalize pass-through args."""
    return raw_args[1:] if raw_args and raw_args[0] == "--" else raw_args

def run_command(command, extra):
    """Run accepted command."""
    target = ROOT.joinpath(*COMMANDS[command])
    cmd = [sys.executable, str(target)] + list(extra)
    command_text = " ".join(cmd).replace("\\", "/")
    qlog.log_command_start(command_text)
    process = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    stdout, stderr = process.stdout or "", process.stderr or ""
    if stdout:
        qlog.log_stream("stdout", command, stdout)
        print(stdout, end="")
    if stderr:
        qlog.log_stream("stderr", command, stderr)
        print(stderr, end="", file=sys.stderr)
    status = "PASS" if process.returncode == 0 else "FAIL"
    qlog.log_check_result(command, status, process.returncode)
    if process.returncode != 0:
        qlog.log_repair_hint(
            "PYTHON_LAUNCHER_TARGET_FAILED",
            "Inspect stdout/stderr stream entries and repair underlying gate.",
            "BLOCK",
            "REPAIR_UNDERLYING_TARGET_PROCESS_AND_RERUN_MASTER_GATE",
        )
    return process.returncode

def main(argv=None):
    """Run launcher."""
    argv = list(sys.argv[1:] if argv is None else argv)
    qlog.reset_log("qikvrt.py")
    qlog.write_event("run_start", launcher="qikvrt.py", default_command=DEFAULT_COMMAND)
    if "--accept" in argv or "accept" in argv:
        initial_acceptance.persist_acceptance()
        return qlog.finish(0)
    parser = build_parser()
    args = parser.parse_args(argv)
    qlog.write_event(
        "usage",
        command=args.command,
        default_command=DEFAULT_COMMAND,
        extra_args=normalize_extra_args(args.args),
        log_file=qlog.json_safe_path(qlog.LOG_FILE),
    )
    if not initial_acceptance.require_acceptance():
        return 30
    exit_code = run_command(args.command, normalize_extra_args(args.args))
    return qlog.finish(exit_code)

if __name__ == "__main__":
    raise SystemExit(main())
