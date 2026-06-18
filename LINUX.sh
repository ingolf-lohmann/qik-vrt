#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Ingolf Lohmann.
# Author/Rights holder: Ingolf Lohmann.

# QALL_SCRIPT_TERMINATION_GUARD_BEGIN
_qall_script_name="$(basename "$0")"
mkdir -p LOGS
_qall_write_term() {
  _qall_rc="$1"
  if [ "$_qall_rc" -eq 0 ]; then
    echo "SCRIPT_TERMINATION=PASS"
    echo "SCRIPT_EXIT_CODE=0"
    printf '{"id":"QIKVRT_SCRIPT_TERMINATION_RECORD","script":"%s","status":"PASS","exit_code":0,"errors":[],"license_notice":{"spdx_license_identifier":"Apache-2.0","copyright":"Copyright (c) 2026 Ingolf Lohmann.","author_rights_holder":"Ingolf Lohmann","future_outputs_require_header_or_manifest_coverage":true,"streams_and_information_objects_require_manifest_coverage":true}}\n' "$_qall_script_name" > "LOGS/$_qall_script_name.termination.json"
  else
    echo "SCRIPT_TERMINATION=ERROR"
    echo "SCRIPT_EXIT_CODE=$_qall_rc"
    printf '{"id":"QIKVRT_SCRIPT_TERMINATION_RECORD","script":"%s","status":"ERROR","exit_code":%s,"errors":[{"operation":"shell","type":"ShellError","message":"shell command failed"}],"license_notice":{"spdx_license_identifier":"Apache-2.0","copyright":"Copyright (c) 2026 Ingolf Lohmann.","author_rights_holder":"Ingolf Lohmann","future_outputs_require_header_or_manifest_coverage":true,"streams_and_information_objects_require_manifest_coverage":true}}\n' "$_qall_script_name" "$_qall_rc" > "LOGS/$_qall_script_name.termination.json"
  fi
}
trap '_qall_rc=$?; _qall_write_term "$_qall_rc"; exit "$_qall_rc"' EXIT
# QALL_SCRIPT_TERMINATION_GUARD_END

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$ROOT/LOGS"
echo "[QALL] Linux-Start / Linux start" > "$ROOT/LOGS/LAST_RUN.txt"
exec /bin/sh "$ROOT/_payload/_internal/RUN.sh" "$ROOT"
