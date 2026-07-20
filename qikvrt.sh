#!/usr/bin/env bash
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# The Python launcher is the single authority for authorization-before-effect.
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PY_EXE=""

for candidate in \
  "$SCRIPT_DIR/runtime/python/linux/python3" \
  "$SCRIPT_DIR/runtime/python/macos/python3" \
  "$SCRIPT_DIR/python/bin/python3"
do
  if [ -x "$candidate" ] && "$candidate" -c 'import sys; raise SystemExit(0)' >/dev/null 2>&1; then
    PY_EXE="$candidate"
    break
  fi
done

if [ -z "$PY_EXE" ] && command -v python3 >/dev/null 2>&1; then
  PY_EXE="$(command -v python3)"
fi
if [ -z "$PY_EXE" ] && command -v python >/dev/null 2>&1; then
  PY_EXE="$(command -v python)"
fi
if [ -z "$PY_EXE" ]; then
  echo "BLOCK: Python 3 was not found; no runtime was downloaded automatically." >&2
  exit 20
fi

if [ "$#" -eq 0 ]; then
  set -- master-gate
fi
exec "$PY_EXE" "$SCRIPT_DIR/qikvrt.py" "$@"
