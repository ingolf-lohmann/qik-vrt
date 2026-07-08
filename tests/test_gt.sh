#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
grep -q "Read-GitHubTokenInteractive" "$ROOT/tools/gh_deploy.ps1"
grep -q "Normalize-GitHubHeaderToken" "$ROOT/tools/gh_deploy.ps1"
! grep -q "for /f .*GitHub token" "$ROOT/QIKVRT.cmd"
grep -q "GITHUB_TOKEN_SANITIZE" "$ROOT/tools/gh_deploy.ps1"
grep -qi "token not persisted" "$ROOT/docs/GT.md"
echo "PASS GitHub token runtime prompt repair test"
