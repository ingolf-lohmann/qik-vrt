#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test -f "$ROOT/QIKVRT.cmd"
test -f "$ROOT/tools/choco_bootstrap.ps1"
grep -q 'QIKVRT_ADMIN_RIGHTS' "$ROOT/QIKVRT.cmd"
grep -q 'license_acceptance.ps1' "$ROOT/QIKVRT.cmd"
grep -q 'setup_repository.ps1' "$ROOT/QIKVRT.cmd"
grep -q 'choco_bootstrap.ps1' "$ROOT/QIKVRT.cmd"
grep -q 'AV-safe' "$ROOT/tools/choco_bootstrap.ps1"
grep -q 'choco.exe' "$ROOT/tools/choco_bootstrap.ps1"
grep -q 'QIKVRT_ALLOW_PACKAGE_INSTALL' "$ROOT/tools/choco_bootstrap.ps1"
grep -q "install','zig" "$ROOT/tools/choco_bootstrap.ps1"
grep -q 'LICENSE_ACCEPTED.json' "$ROOT/tools/choco_bootstrap.ps1"
grep -q 'REPOSITORY_GUID.txt' "$ROOT/tools/choco_bootstrap.ps1"
if grep -q 'DownloadString' "$ROOT/tools/choco_bootstrap.ps1"; then
  echo "FAIL remote installer DownloadString remains in choco_bootstrap" >&2
  exit 1
fi
if grep -q 'Invoke-Expression' "$ROOT/tools/choco_bootstrap.ps1"; then
  echo "FAIL Invoke-Expression remains in choco_bootstrap" >&2
  exit 1
fi
if grep -q 'ExecutionPolicy Bypass' "$ROOT/QIKVRT.cmd"; then
  echo "FAIL ExecutionPolicy Bypass remains in QIKVRT.cmd" >&2
  exit 1
fi
if grep -q 'Verb RunAs' "$ROOT/QIKVRT.cmd"; then
  echo "FAIL automatic elevation remains in QIKVRT.cmd" >&2
  exit 1
fi

if grep -qi -- 'powershell .* -File ' "$ROOT/QIKVRT.cmd"; then
  echo "FAIL direct PowerShell -File invocation remains in QIKVRT.cmd" >&2
  exit 1
fi
if ! grep -q 'QIKVRT_POWERSHELL_SCRIPT_HOST' "$ROOT/QIKVRT.cmd"; then
  echo "FAIL inline PowerShell script host audit marker missing" >&2
  exit 1
fi
if ! grep -q 'ScriptBlock' "$ROOT/QIKVRT.cmd"; then
  echo "FAIL inline ScriptBlock host missing" >&2
  exit 1
fi

if grep -q 'winget install' "$ROOT/tools/win_acceptance.ps1"; then
  echo "FAIL winget install remains in win_acceptance" >&2
  exit 1
fi
echo PASS av-safe windows dependency bootstrap gates


for ps1 in tools/setup_repository.ps1 tools/choco_bootstrap.ps1 tools/gh_deploy.ps1 tools/register_with_seed.ps1; do
  if grep -q '^\$Rows = @()' "$ROOT/$ps1"; then
    echo "FAIL unscoped Rows initializer remains in $ps1; inline ScriptBlock host requires \$script:Rows" >&2
    exit 1
  fi
  if ! grep -q '\$script:Rows = @()' "$ROOT/$ps1"; then
    echo "FAIL script-scoped Rows initializer missing in $ps1" >&2
    exit 1
  fi
done

