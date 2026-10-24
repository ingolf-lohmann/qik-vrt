# QIKVRT Artifact Header
# Version: 2.13.4
# Deutsch: Automatische Seed-Registrierung aus persistierter Setup-Konfiguration.
# English: Automatic seed registration from persisted setup configuration.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
param([string]$RepoRoot = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$RuntimeDir = Join-Path $RepoRoot 'qikvrt\runtime\onboarding'
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$Tsv = Join-Path $RuntimeDir 'REGISTER_WITH_SEED_RESULT.tsv'
$Json = Join-Path $RuntimeDir 'REGISTER_WITH_SEED_RESULT.json'
$script:Rows = @()
function Add-RegResult([string]$Gate,[string]$Status,[string]$Detail) { $script:Rows += [pscustomobject]@{timestamp_utc=(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ');gate=$Gate;status=$Status;detail=$Detail}; Write-Host ($Gate + "`t" + $Status + "`t" + $Detail) }
$targetPath = Join-Path $RepoRoot 'qikvrt\config\REPOSITORY_TARGET.json'
$onboardingPath = Join-Path $RepoRoot 'qikvrt\config\ONBOARDING.json'
if (-not (Test-Path -LiteralPath $targetPath)) { Add-RegResult 'REGISTER_CONFIG' 'BLOCK' 'REPOSITORY_TARGET.json missing; run setup first'; exit 3 }
if (-not (Test-Path -LiteralPath $onboardingPath)) { Add-RegResult 'REGISTER_CONFIG' 'BLOCK' 'ONBOARDING.json missing; run setup first'; exit 3 }
$target = Get-Content -LiteralPath $targetPath -Raw | ConvertFrom-Json
$payload = Get-Content -LiteralPath $onboardingPath -Raw | ConvertFrom-Json
Add-RegResult 'REGISTER_CONFIG' 'PASS' ($target.github_repository_full_name + ' -> seed ' + $target.seed_repository_full_name)
if ([string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
  Add-RegResult 'REGISTER_WITH_SEED' 'BLOCK' 'missing GITHUB_TOKEN; registration request persisted locally, no remote mutation performed'
} else {
  $headers = @{ Authorization = 'Bearer ' + $env:GITHUB_TOKEN; Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }
  $uri = 'https://api.github.com/repos/' + $target.seed_owner + '/' + $target.seed_repository + '/dispatches'
  $body = @{ event_type='qikvrt_node_onboarding'; client_payload=$payload } | ConvertTo-Json -Depth 8
  try { Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -ContentType 'application/json' -Body $body | Out-Null; Add-RegResult 'REGISTER_WITH_SEED' 'PASS' ('repository_dispatch to ' + $target.seed_repository_full_name) } catch { Add-RegResult 'REGISTER_WITH_SEED' 'BLOCK' $_.Exception.Message }
}
$script:Rows | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Json -Encoding UTF8
'timestamp_utc`tgate`tstatus`tdetail' | Set-Content -LiteralPath $Tsv -Encoding UTF8
foreach ($row in $script:Rows) { ($row.timestamp_utc + "`t" + $row.gate + "`t" + $row.status + "`t" + (($row.detail -replace "`r?`n", ' ') -replace "`t", ' ')) | Add-Content -LiteralPath $Tsv -Encoding UTF8 }
if (($script:Rows | Where-Object { $_.gate -eq 'REGISTER_WITH_SEED' -and $_.status -eq 'PASS' }).Count -gt 0) { exit 0 }
exit 3
