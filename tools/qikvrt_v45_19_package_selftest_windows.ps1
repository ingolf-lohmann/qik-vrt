param([string]$Root)
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = Split-Path -Parent $PSScriptRoot }
. (Join-Path $PSScriptRoot 'qikvrt_common_windows.ps1')
$required = @(
 'tools\qikvrt_v45_19_local_verify_windows.ps1',
 'tools\qikvrt_v45_19_document_persistence_release_windows.ps1',
 'tools\qikvrt_v45_19_package_selftest_windows.ps1',
 'tools\qikvrt_common_windows.ps1',
 'QIKVRT_V45_19_RUN_LOCAL_VERIFY.cmd',
 'QIKVRT_V45_19_REAL_GITHUB_RELEASE.cmd'
)
foreach ($r in $required) { Require-File (Join-Path $Root $r) }
$common = Get-Content -LiteralPath (Join-Path $Root 'tools\qikvrt_common_windows.ps1') -Raw
if ($common -match 'function\s+Run-Git\s*\(\s*\[string\[\]\]\$args\s*\)') { QFail 'legacy Run-Git $args collision pattern still present' }
if ($common -notmatch 'ValueFromRemainingArguments') { QFail 'ValueFromRemainingArguments guard missing' }
if ($common -notmatch 'empty argument vector') { QFail 'zero-argument git/gh guard missing' }

if ($common -notmatch 'Test-QikvrtGitRemoteExists') { QFail 'safe origin remote existence guard missing' }
if ($common -match 'git remote get-url origin \*>') { QFail 'unsafe native stderr origin probe still present' }
QPass 'QIKVRT V45.19 package wrapper, Git invocation and safe origin probe selftest ok'
exit 0
