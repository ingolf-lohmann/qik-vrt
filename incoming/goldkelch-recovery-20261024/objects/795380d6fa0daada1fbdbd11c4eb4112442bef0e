#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
[ -s "$ROOT/QIKVRT.cmd" ]
[ -s "$ROOT/QIKVRT.sh" ]
[ -s "$ROOT/tools/gh_deploy.ps1" ]
[ -s "$ROOT/tools/gh_deploy.sh" ]
# Usability: exactly one public Windows entrypoint and one public POSIX entrypoint in repository root.
public_cmd_count=$(find "$ROOT" -maxdepth 1 -type f -name '*.cmd' | wc -l | tr -d ' ')
public_sh_count=$(find "$ROOT" -maxdepth 1 -type f -name '*.sh' | wc -l | tr -d ' ')
[ "$public_cmd_count" = "1" ]
[ "$public_sh_count" = "1" ]
grep -q 'GITHUB_TOKEN' "$ROOT/QIKVRT.cmd"
! grep -q 'Read-Host' "$ROOT/QIKVRT.cmd"
# Token input must happen in gh_deploy.ps1, not in cmd.exe/for/f wrapper.
grep -q 'Read-GitHubTokenInteractive' "$ROOT/tools/gh_deploy.ps1"
grep -q 'GITHUB_TOKEN' "$ROOT/QIKVRT.sh"
grep -q 'GitHub token' "$ROOT/QIKVRT.sh"
grep -q 'QIKVRT_GITHUB_OWNER' "$ROOT/tools/gh_deploy.ps1"
grep -q 'QIKVRT_GITHUB_REPO' "$ROOT/tools/gh_deploy.ps1"
grep -q 'git -C' "$ROOT/tools/gh_deploy.ps1"
grep -q 'GITHUB_TOKEN' "$ROOT/tools/gh_deploy.ps1"
grep -q 'QIKVRT_GITHUB_OWNER' "$ROOT/tools/gh_deploy.sh"
grep -q 'QIKVRT_GITHUB_REPO' "$ROOT/tools/gh_deploy.sh"
grep -q 'remote.origin.url' "$ROOT/tools/gh_deploy.sh"
grep -q 'GITHUB_TOKEN' "$ROOT/tools/gh_deploy.sh"
grep -q 'DEPLOY_ASSET_GIT_ARCHIVE' "$ROOT/tools/gh_deploy.ps1"
grep -q 'DEPLOY_STAGING_SELF_COPY_PREVENTION' "$ROOT/tools/gh_deploy.ps1"
grep -q 'qikvrt/runtime/deploy' "$ROOT/tools/gh_deploy.ps1"
grep -q 'package_staging' "$ROOT/tools/gh_deploy.ps1"
if grep -Eq 'Copy-Item .* -Recurse|Copy-Item.*-Recurse' "$ROOT/tools/gh_deploy.ps1"; then
  echo "FAIL recursive Copy-Item present in deploy script" >&2
  exit 1
fi
grep -q 'DEPLOY_STAGING_SELF_COPY_PREVENTION' "$ROOT/tools/gh_deploy.sh"
grep -q 'qikvrt/runtime/deploy' "$ROOT/tools/gh_deploy.sh"
grep -q 'package_staging' "$ROOT/tools/gh_deploy.sh"
if grep -q 'Goldkelch/qik-vrt' "$ROOT/QIKVRT.cmd" "$ROOT/QIKVRT.sh" "$ROOT/tools/gh_deploy.ps1" "$ROOT/tools/gh_deploy.sh"; then
  echo "FAIL hardcoded GitHub target in deploy entrypoint/helper" >&2
  exit 1
fi
grep -q 'GIT_PUSH_TAG' "$ROOT/tools/gh_deploy.ps1"
grep -q 'GITHUB_ACTIONS_RELEASE_TRIGGER' "$ROOT/tools/gh_deploy.ps1"

grep -q 'Normalize-GitHubHeaderToken' "$ROOT/tools/gh_deploy.ps1"
grep -q 'GITHUB_TOKEN_SANITIZE' "$ROOT/tools/gh_deploy.ps1"
grep -Fq '[\x00-\x1F\x7F]' "$ROOT/tools/gh_deploy.ps1"
grep -q 'GITHUB_TOKEN_SANITIZE' "$ROOT/tools/gh_deploy.sh"
grep -Fq "tr -d '\\000-\\037\\177'" "$ROOT/tools/gh_deploy.sh"
echo PASS github deploy gates
