param([string]$Root = "")
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")
Write-Host "QIKVRT V45.12 Windows local verify - evidence-freeze; no direct Python dependency; no force-tag/no clobber release path"
$defaultRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = $defaultRoot }
$rootPath = Normalize-QikvrtPathArg -Path $Root -MustExist
Set-Location $rootPath
$required = @("VERSION","README.md","SHA256SUMS","QIKVRT_V45_12_RUN_LOCAL_VERIFY.cmd","QIKVRT_V45_12_BUILD_ZIP_AND_HASH.cmd","QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd","tools/qikvrt_common_windows.ps1","tools/qikvrt_local_verify_windows.ps1","tools/qikvrt_github_remote_effect_evidence_gate_windows.ps1","tools/qikvrt_github_automated_merge_commit_push_release_windows.ps1","tools/qikvrt_master_gate_windows.ps1","tools/qikvrt_build_zip_and_hash_windows.ps1","docs/EVIDENCE_FREEZE_REQUIREMENT.md","docs/ERROR_CLASSES.md")
foreach ($rel in $required) { if (!(Test-Path -LiteralPath (Join-Path $rootPath $rel))) { Write-QikvrtBlock "required file missing: $rel"; exit 1 } }
Write-QikvrtPass "required files present"
$cmdFiles = @("QIKVRT_V45_12_RUN_LOCAL_VERIFY.cmd","QIKVRT_V45_12_BUILD_ZIP_AND_HASH.cmd","QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd","QIKVRT_V45_12_RUN_PYTHON_VERIFY_OPTIONAL.cmd")
foreach ($cmdRel in $cmdFiles) { $txt = Get-Content -LiteralPath (Join-Path $rootPath $cmdRel) -Raw -Encoding UTF8; if ($txt -match '"%~dp0"') { Write-QikvrtBlock "$cmdRel still passes quoted %~dp0 directly"; exit 1 }; if ($txt -notmatch 'QIKVRT_ROOT:~-1') { Write-QikvrtBlock "$cmdRel does not normalize trailing backslash"; exit 1 } }
Write-QikvrtPass "Windows CMD wrappers normalize %~dp0 trailing backslash before PowerShell handoff"
$realWrapper = Get-Content -LiteralPath (Join-Path $rootPath "QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd") -Raw -Encoding UTF8
if ($realWrapper -notmatch 'set /p QIKVRT_CONFIRM=') { Write-QikvrtBlock "real GitHub wrapper does not request interactive confirmation"; exit 1 }
if ($realWrapper -notmatch 'qikvrt_acceptance_gate_windows\.ps1') { Write-QikvrtBlock "real GitHub wrapper does not persist owner acceptance before effect attempt"; exit 1 }
if ($realWrapper -notmatch 'set "QIKVRT_ENABLE_REAL_GITHUB_EFFECTS=YES"') { Write-QikvrtBlock "real GitHub wrapper does not set real-effects env var after acceptance"; exit 1 }
Write-QikvrtPass "real GitHub wrapper persists acceptance and self-enables real-effects variable only afterward"
$wrapper = Get-Content -LiteralPath (Join-Path $rootPath "QIKVRT_V45_12_RUN_LOCAL_VERIFY.cmd") -Raw -Encoding UTF8
if ($wrapper -match '(?im)^\s*python(\.exe)?\s+') { Write-QikvrtBlock "local verify wrapper calls python directly"; exit 1 }
Write-QikvrtPass "Windows 9009-safe local wrapper does not call python directly"
$releaseScript = Get-Content -LiteralPath (Join-Path $rootPath "tools/qikvrt_github_automated_merge_commit_push_release_windows.ps1") -Raw -Encoding UTF8
if ($releaseScript -match 'git tag -f|tag -f|push.*--force|release upload.*--clobber') { Write-QikvrtBlock "V45.12 freeze release script still contains force tag/push or asset clobber"; exit 1 }
foreach ($needle in @('no_force_tag_update','tag_force_updated = $false','asset_clobbered = $false','remote_tag_sha','Test-QikvrtReleaseAssetExists')) { if ($releaseScript -notmatch [regex]::Escape($needle)) { Write-QikvrtBlock "V45.12 freeze release script missing: $needle"; exit 1 } }
Write-QikvrtPass "V45.12 release script forbids force-tag updates and asset clobbering"
$gate = Get-Content -LiteralPath (Join-Path $rootPath "tools/qikvrt_github_remote_effect_evidence_gate_windows.ps1") -Raw -Encoding UTF8
foreach ($needle in @('QIKVRT_GITHUB_REMOTE_EFFECT_EVIDENCE_V45_12','no_force_tag_update','tag_force_updated','asset_clobbered','remote_tag_sha')) { if ($gate -notmatch [regex]::Escape($needle)) { Write-QikvrtBlock "evidence freeze gate missing: $needle"; exit 1 } }
Write-QikvrtPass "evidence freeze gate checks tag immutability and asset non-clobbering"
$build = Get-Content -LiteralPath (Join-Path $rootPath "tools/qikvrt_build_zip_and_hash_windows.ps1") -Raw -Encoding UTF8
if ($build -match '\$rootPath\s*=\s*\(Resolve-Path\s+\$Root\)') { Write-QikvrtBlock "build script still uses unsafe Resolve-Path `$Root form"; exit 1 }
if ($build -notmatch 'Normalize-QikvrtPathArg -Path \$OutDir') { Write-QikvrtBlock "build script does not normalize OutDir safely"; exit 1 }
if ($build -notmatch 'New-QikvrtDirectoryForFile \$zipPath') { Write-QikvrtBlock "build script does not create ZIP parent directory before Compress-Archive"; exit 1 }
if ($build -notmatch '\$name = "QIKVRT_V45_12"') { Write-QikvrtBlock "build script does not use short output package name QIKVRT_V45_12"; exit 1 }
Write-QikvrtPass "build script creates OutDir/ZIP parent and uses short output package name"
$sumFile = Join-Path $rootPath "SHA256SUMS"
$lines = Get-Content -LiteralPath $sumFile -Encoding UTF8 | Where-Object { $_.Trim().Length -gt 0 }
$checked = 0
foreach ($line in $lines) { if ($line -notmatch '^([0-9a-fA-F]{64})\s+\*(.+)$') { Write-QikvrtBlock "bad SHA256SUMS line: $line"; exit 1 }; $expected=$Matches[1].ToLowerInvariant(); $rel=$Matches[2]; $path=Join-Path $rootPath $rel; if (!(Test-Path -LiteralPath $path)) { Write-QikvrtBlock "SHA256SUMS listed file missing: $rel"; exit 1 }; $actual=Get-QikvrtSha256 $path; if ($actual -ne $expected) { Write-QikvrtBlock "hash mismatch: $rel expected=$expected actual=$actual"; exit 1 }; $checked++ }
Write-QikvrtPass "internal hashes ok checked=$checked"
$missingEvidence = Join-Path $rootPath "examples/missing_remote_evidence.block.json"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $rootPath "tools/qikvrt_github_remote_effect_evidence_gate_windows.ps1") -EvidenceJson $missingEvidence *> $null
if ($LASTEXITCODE -eq 0) { Write-QikvrtBlock "missing remote evidence passed unexpectedly"; exit 1 }
Write-QikvrtPass "missing remote evidence blocks release claim as required"
Write-Host "REMOTE_RELEASE_STATUS = BLOCK_UNTIL_LIVE_GITHUB_EVIDENCE_FREEZE"
Write-Host "LOCAL_VERIFY_STATUS = PASS"
exit 0
