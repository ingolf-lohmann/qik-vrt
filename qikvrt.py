#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""QIK-VRT launcher with authorization-before-effect enforcement."""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_runtime_logger as qlog
from tools import qikvrt_initial_acceptance_gate as initial_acceptance
from tools.qikvrt_subprocess import run_bounded

DEFAULT_COMMAND = "master-gate"
COMMANDS = {
    "master-gate": ["tools/qikvrt_master_acceptance_gate.py"],
    "cicd-publish": ["tools/qikvrt_cicd_publish.py"],
}

def build_parser():
    """Build parser."""
    parser = argparse.ArgumentParser(description="QIK-VRT launcher. Scoped local authorization is required before any effect.")
    parser.add_argument("command", nargs="?", default=DEFAULT_COMMAND, choices=sorted(COMMANDS))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser

def normalize_extra_args(raw_args):
    """Normalize pass-through args."""
    return raw_args[1:] if raw_args and raw_args[0] == "--" else raw_args

def run_command(command, extra):
    """Run accepted command."""
    target = ROOT.joinpath(*COMMANDS[command])
    if not target.is_file() or target.is_symlink():
        qlog.log_check_result(command, "BLOCK", 1, error=f"target missing: {target}")
        qlog.log_repair_hint(
            "PYTHON_LAUNCHER_TARGET_MISSING",
            f"Restore the declared command target: {target.relative_to(ROOT)}",
            "BLOCK",
            "RESTORE_COMMAND_TARGET_AND_RERUN",
        )
        return 1
    cmd = [sys.executable, str(target)] + list(extra)
    qlog.log_command_start([qlog.json_safe_path(part) for part in cmd])
    try:
        process = run_bounded(
            cmd,
            cwd=ROOT,
            env={**os.environ, "QIKVRT_LAUNCHED_BY_QIKVRT": "1"},
            timeout=900,
            max_output_bytes=2 * 1024 * 1024,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        qlog.log_check_result(command, "BLOCK", 1, error=str(exc))
        qlog.log_repair_hint(
            "PYTHON_LAUNCHER_TARGET_START_FAILED",
            "Inspect the launcher exception and repair the target runtime.",
            "BLOCK",
            "REPAIR_TARGET_RUNTIME_AND_RERUN",
        )
        return 1
    if process.timed_out or process.output_limit_exceeded:
        reason = "target timed out" if process.timed_out else "target output limit exceeded"
        qlog.log_check_result(command, "BLOCK", 1, error=reason)
        qlog.log_repair_hint(
            "PYTHON_LAUNCHER_TARGET_BOUNDED_EXECUTION_FAILED",
            reason,
            "BLOCK",
            "REPAIR_TARGET_RUNTIME_AND_RERUN",
        )
        return 1
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
    if argv in (["--accept"], ["accept"]):
        try:
            initial_acceptance.persist_acceptance()
        except (OSError, UnicodeError, ValueError) as exc:
            message = f"launcher effect authorization could not be persisted: {exc}"
            print("BLOCK " + message, file=sys.stderr)
            qlog.log_check_result("persist-launcher-acceptance", "BLOCK", 1, error=message)
            qlog.log_repair_hint(
                "LAUNCHER_ACCEPTANCE_PERSIST_FAILED",
                "Repair the reported repository context or filesystem error, then accept again.",
                "BLOCK",
                "REPAIR_ACCEPTANCE_CONTEXT_AND_RERUN",
            )
            return qlog.finish(
                1,
                error_class="LAUNCHER_ACCEPTANCE_PERSIST_FAILED",
                continue_path="REPAIR_ACCEPTANCE_CONTEXT_AND_RERUN",
                repair_hint=message,
            )
        return qlog.finish(0)
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = int(exc.code or 0)
        return qlog.finish(
            code,
            status="PASS" if code == 0 else "BLOCK",
            error_class="NONE" if code == 0 else "INVALID_LAUNCHER_ARGUMENTS",
            continue_path="NONE" if code == 0 else "CORRECT_ARGUMENTS_AND_RERUN",
            repair_hint="NONE" if code == 0 else "Run 'python qikvrt.py --help'.",
        )
    if not initial_acceptance.require_acceptance(args.command):
        print(
            "CONTINUE: explicit bound effect authorization is required. "
            "Run 'python qikvrt.py --accept' and then rerun the command.",
            file=sys.stderr,
        )
        return qlog.finish(
            20,
            status="CONTINUE",
            error_class="CONTINUE_ACCEPTANCE_REQUIRED",
            continue_path="PERSIST_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT",
            repair_hint="Run 'python qikvrt.py --accept' before an effectful command.",
        )
    qlog.write_event(
        "usage",
        command=args.command,
        default_command=DEFAULT_COMMAND,
        extra_args=normalize_extra_args(args.args),
        log_file=qlog.json_safe_path(qlog.LOG_FILE),
    )
    exit_code = run_command(args.command, normalize_extra_args(args.args))
    return qlog.finish(exit_code)

if __name__ == "__main__":
    raise SystemExit(main())
