#!/usr/bin/env sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Ingolf Lohmann.
set -eu
cd "$(dirname "$0")/.."
[ -f START_HIER_QIKVRT_UPLOAD.cmd ] || { echo "missing cmd"; exit 1; }
[ -f tools/qikvrt_upload_wsh.js ] || { echo "missing js"; exit 1; }
find . -name '*.ps1' | grep . && { echo "ps1 present"; exit 1; } || true
grep -R "powershell" START_HIER_QIKVRT_UPLOAD.cmd tools/qikvrt_upload_wsh.js && { echo "powershell marker present"; exit 1; } || true
grep -R "git clone\|git commit\|git push" START_HIER_QIKVRT_UPLOAD.cmd tools/qikvrt_upload_wsh.js && { echo "git operation marker present"; exit 1; } || true
python3 - <<'PY'
from pathlib import Path
for p in [Path('START_HIER_QIKVRT_UPLOAD.cmd')]:
    data=p.read_bytes()
    assert all(b<128 for b in data), p
print('ASCII_CMD_SURFACE PASS')
PY
if command -v node >/dev/null 2>&1; then node --check tools/qikvrt_upload_wsh.js >/dev/null; fi
sha256sum -c SHA256SUMS.txt >/dev/null
echo QIKVRT_4AO_CONTRACT_PASS
