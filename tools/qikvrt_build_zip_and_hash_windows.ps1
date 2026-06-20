param([string]$Root = "",[string]$OutDir = "")
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")
$defaultRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = $defaultRoot }
$rootPath = Normalize-QikvrtPathArg -Path $Root -MustExist
if ([string]::IsNullOrWhiteSpace($OutDir)) { $OutDir = Join-Path $rootPath "dist" }
$outDirPath = Normalize-QikvrtPathArg -Path $OutDir
if (!(Test-Path -LiteralPath $outDirPath)) { New-Item -ItemType Directory -Force -Path $outDirPath | Out-Null }
$outDirPath = Normalize-QikvrtPathArg -Path $outDirPath -MustExist
$name = "QIKVRT_V45_12"
$zipPath = Join-Path $outDirPath ($name + ".zip")
$shaPath = $zipPath + ".sha256"
$manifestPath = $zipPath + ".manifest.json"
if ($zipPath.Length -gt 240) { Write-QikvrtWarn "output ZIP path is long ($($zipPath.Length) chars). Extract nearer to C:\\q on legacy Windows if needed." }
New-QikvrtDirectoryForFile $zipPath
$tmpBase = Join-Path $env:TEMP "qv4512_pack"
if (!(Test-Path -LiteralPath $tmpBase)) { New-Item -ItemType Directory -Force -Path $tmpBase | Out-Null }
$tmp = Join-Path $tmpBase ([guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$stage = Join-Path $tmp $name
New-Item -ItemType Directory -Force -Path $stage | Out-Null
$excludeDirs = @(".git","dist","__pycache__")
Get-ChildItem -LiteralPath $rootPath -Force | Where-Object { $excludeDirs -notcontains $_.Name } | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $stage -Recurse -Force }
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force
$sha = Get-QikvrtSha256 $zipPath
("$sha  " + (Split-Path -Leaf $zipPath)) | Set-Content -LiteralPath $shaPath -Encoding ASCII
$manifest = [ordered]@{
  package = $name
  version = "V45.12"
  sha256 = $sha
  created_utc = (Get-Date).ToUniversalTime().ToString("o")
  local_verify = "QIKVRT_V45_12_RUN_LOCAL_VERIFY.cmd"
  build_wrapper = "QIKVRT_V45_12_BUILD_ZIP_AND_HASH.cmd"
  real_github_release_wrapper = "QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd"
  freeze_policy = "NO_FORCE_TAG_UPDATE_AND_NO_RELEASE_ASSET_CLOBBER"
  release_claim = $false
  remote_release_status = "BLOCK_UNTIL_LIVE_GITHUB_EVIDENCE_FREEZE"
}
Write-QikvrtJson -Path $manifestPath -Object $manifest
Remove-Item -LiteralPath $tmp -Recurse -Force
Write-QikvrtPass "built ZIP: $zipPath"
Write-QikvrtPass "sha256: $sha"
Write-QikvrtPass "manifest: $manifestPath"
exit 0
