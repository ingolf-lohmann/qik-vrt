#!/usr/bin/env bash
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_COMMAND="master-gate"
if [ "$#" -eq 0 ]; then
  set -- "$DEFAULT_COMMAND"
fi
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/qikvrt_last_run.jsonl"
mkdir -p "$LOG_DIR"
: > "$LOG_FILE"
echo '{"event":"run_start","launcher":"qikvrt.sh","default_command":"master-gate","dependency_contract":"GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_GATE"}' >> "$LOG_FILE"
echo "QIK-VRT V23 Unix/macOS Shell Launcher"
echo "Command: $*"
echo "Logfile: $LOG_FILE"
PY_EXE=""
if [ -x "$SCRIPT_DIR/runtime/python/linux/python3" ]; then PY_EXE="$SCRIPT_DIR/runtime/python/linux/python3"; fi
if [ -z "$PY_EXE" ] && [ -x "$SCRIPT_DIR/runtime/python/macos/python3" ]; then PY_EXE="$SCRIPT_DIR/runtime/python/macos/python3"; fi
if [ -z "$PY_EXE" ] && [ -x "$SCRIPT_DIR/python/bin/python3" ]; then PY_EXE="$SCRIPT_DIR/python/bin/python3"; fi
if [ -z "$PY_EXE" ] && command -v python3 >/dev/null 2>&1; then PY_EXE="python3"; fi
if [ -z "$PY_EXE" ] && command -v python >/dev/null 2>&1; then PY_EXE="python"; fi
if [ -z "$PY_EXE" ]; then
  "$SCRIPT_DIR/runtime/download_python_runtime.sh"
  EXITCODE=$?
  echo '{"event":"sh_wrapper_end","status":"CONTINUE","exit_code":20,"error_class":"PYTHON_RUNTIME_NOT_RESOLVED","continue_path":"INSTALL_OR_BUNDLE_RUNTIME","repair_hint":"Install Python 3 or place a runtime at runtime/python/linux/python3 or runtime/python/macos/python3."}' >> "$LOG_FILE"
  echo '{"event":"run_end","status":"CONTINUE","exit_code":20,"error_class":"PYTHON_RUNTIME_NOT_RESOLVED","continue_path":"INSTALL_OR_BUNDLE_RUNTIME","repair_hint":"Install Python 3 or bundle runtime.","logfile":"logs/qikvrt_last_run.jsonl"}' >> "$LOG_FILE"
else
  "$PY_EXE" "$SCRIPT_DIR/qikvrt.py" "$@"
  EXITCODE=$?
  if [ "$EXITCODE" -eq 0 ]; then
    echo '{"event":"sh_wrapper_end","status":"PASS","exit_code":0}' >> "$LOG_FILE"
    echo '{"event":"run_end","status":"PASS","exit_code":0,"error_class":"NONE","continue_path":"NONE","repair_hint":"NONE","logfile":"logs/qikvrt_last_run.jsonl"}' >> "$LOG_FILE"
  else
    echo '{"event":"sh_wrapper_end","status":"FAIL","exit_code":'"$EXITCODE"',"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_LOG_AND_REPAIR_NEXT_ERROR","repair_hint":"Inspect logs/qikvrt_last_run.jsonl."}' >> "$LOG_FILE"
    echo '{"event":"run_end","status":"FAIL","exit_code":'"$EXITCODE"',"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_LOG_AND_REPAIR_NEXT_ERROR","repair_hint":"Inspect logs/qikvrt_last_run.jsonl.","logfile":"logs/qikvrt_last_run.jsonl"}' >> "$LOG_FILE"
  fi
fi
echo "QIK-VRT finished."
echo "Exit-Code: $EXITCODE"
echo "Logfile: $LOG_FILE"
exit "$EXITCODE"
