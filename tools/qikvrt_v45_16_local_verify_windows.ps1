param([string]$Root="")
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "qikvrt_common_windows.ps1")
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = (Split-Path -Parent $scriptDir) }
$rootPath = Normalize-QikvrtPathArg -Path $Root -MustExist
& (Join-Path $scriptDir "qikvrt_v45_16_package_selftest_windows.ps1") -Root $rootPath
$shaFile = Join-Path $rootPath "SHA256SUMS"
if (-not (Test-Path -LiteralPath $shaFile)) { Write-QikBlock "SHA256SUMS missing" }
$bad=0; $missing=0; $ok=0
foreach ($line in Get-Content -LiteralPath $shaFile) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  $m=[regex]::Match($line,'^([0-9a-fA-F]{64})\s+\*?(.+)$')
  if (-not $m.Success) { Write-QikBlock ("malformed SHA256SUMS line: " + $line) }
  $expected=$m.Groups[1].Value.ToLowerInvariant(); $rel=$m.Groups[2].Value.Trim(); $p=Join-Path $rootPath $rel
  if (-not (Test-Path -LiteralPath $p)) { Write-Host ("MISSING " + $rel); $missing++; continue }
  $actual=Get-QikSha256 $p
  if ($actual -ne $expected) { Write-Host ("MISMATCH " + $rel); $bad++ } else { $ok++ }
}
if ($missing -ne 0 -or $bad -ne 0) { Write-QikBlock ("internal SHA256SUMS failed ok="+$ok+" missing="+$missing+" bad="+$bad) }
Write-QikPass ("internal SHA256SUMS ok=" + $ok)
$incoming = Join-Path $rootPath "incoming\QV45_WINZIP_OK.zip"
$incomingSha = Join-Path $rootPath "incoming\QV45_WINZIP_OK.zip.sha256"
if (-not (Test-Path -LiteralPath $incoming)) { Write-QikBlock "incoming QV45 zip missing" }
if (-not (Test-Path -LiteralPath $incomingSha)) { Write-QikBlock "incoming QV45 sidecar missing" }
$actual=Get-QikSha256 $incoming
$side=Get-Content -LiteralPath $incomingSha -Raw
$m=[regex]::Match($side,'[0-9a-fA-F]{64}')
if (-not $m.Success) { Write-QikBlock "incoming sidecar lacks SHA256" }
if ($actual -ne $m.Value.ToLowerInvariant()) { Write-QikBlock "incoming artifact SHA mismatch" }
Write-QikPass ("incoming QV45 artifact verified: " + $actual)
Write-QikPass "QIKVRT V45.16 local verify ok; remote effect pending live GitHub run"
exit 0
