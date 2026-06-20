param([string]$Root="")
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "qikvrt_common_windows.ps1")
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = (Split-Path -Parent $scriptDir) }
$rootPath = Normalize-QikvrtPathArg -Path $Root -MustExist
$targets = @(
  "tools\qikvrt_v45_16_local_verify_windows.ps1",
  "tools\qikvrt_v45_16_qv45_ietf_merge_release_windows.ps1",
  "tools\qikvrt_v45_16_package_selftest_windows.ps1",
  "tools\qikvrt_common_windows.ps1",
  "QIKVRT_V45_16_RUN_LOCAL_VERIFY.cmd",
  "QIKVRT_V45_16_REAL_GITHUB_RELEASE.cmd"
)
foreach ($t in $targets) {
  $p = Join-Path $rootPath $t
  if (-not (Test-Path -LiteralPath $p)) { Write-QikBlock ("wrapper target missing; fully extract ZIP before running: " + $t) }
  Write-QikPass ("wrapper target present: " + $t)
}
Write-QikPass "QIKVRT V45.16 package wrapper target selftest ok"
exit 0
