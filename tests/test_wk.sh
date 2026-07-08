#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
grep -q "QIKVRT_NO_PAUSE" "$ROOT/QIKVRT.cmd" || true
# Unified Windows entrypoint must be visible and call the acceptance runner through the single public script.
grep -q "win_acceptance.ps1" "$ROOT/QIKVRT.cmd"
grep -q "acceptance" "$ROOT/QIKVRT.cmd"
echo PASS windows keep-open launcher gates
