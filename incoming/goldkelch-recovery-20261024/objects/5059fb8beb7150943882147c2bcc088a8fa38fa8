# QIKVRT Artifact Header
# Version: 2.13.4
# Deutsch: Generisches Repository-Setup mit GUID-Persistenz und GitHub-Zielkonfiguration.
# English: Generic repository setup with GUID persistence and GitHub target configuration.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
param(
  [string]$RepoRoot = (Get-Location).Path,
  [switch]$NonInteractive
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$DefaultOwner = 'Goldkelch'
$DefaultRepo = 'qik-vrt-node'
$DefaultSeedOwner = 'Goldkelch'
$DefaultSeedRepo = 'qik-vrt'
$Role = 'node'
$RuntimeDir = Join-Path $RepoRoot 'qikvrt\runtime\setup'
$OnboardingDir = Join-Path $RepoRoot 'qikvrt\runtime\onboarding'
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
New-Item -ItemType Directory -Force -Path $OnboardingDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot 'qikvrt\config') | Out-Null
$script:Rows = @()
function Add-SetupResult([string]$Gate,[string]$Status,[string]$Detail) {
  $script:Rows += [pscustomobject]@{ timestamp_utc=(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'); gate=$Gate; status=$Status; detail=$Detail }
  Write-Host ($Gate + "`t" + $Status + "`t" + $Detail)
}
function Ask-WithDefault([string]$Prompt,[string]$Default,[string]$EnvName) {
  $envValue = [Environment]::GetEnvironmentVariable($EnvName)
  if (-not [string]::IsNullOrWhiteSpace($envValue)) { return $envValue }
  if ($NonInteractive -or $env:QIKVRT_SETUP_NONINTERACTIVE -eq '1') { return $Default }
  $answer = Read-Host ($Prompt + ' [' + $Default + ']')
  if ([string]::IsNullOrWhiteSpace($answer)) { return $Default }
  return $answer
}
function Ensure-Guid {
  $guidPath = Join-Path $RepoRoot 'qikvrt\runtime\REPOSITORY_GUID.txt'
  $legacyNodeGuidPath = Join-Path $RepoRoot 'qikvrt\runtime\node\REPOSITORY_GUID.txt'
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $legacyNodeGuidPath) | Out-Null
  if (Test-Path -LiteralPath $guidPath) {
    $guid = (Get-Content -LiteralPath $guidPath -Raw).Trim()
    Add-SetupResult 'REPOSITORY_GUID' 'PASS' ('existing ' + $guid)
  } else {
    $guid = [guid]::NewGuid().ToString()
    Set-Content -LiteralPath $guidPath -Value $guid -Encoding ASCII
    Add-SetupResult 'REPOSITORY_GUID' 'PASS' ('generated ' + $guid)
  }
  Set-Content -LiteralPath $legacyNodeGuidPath -Value $guid -Encoding ASCII
  return $guid
}
Add-SetupResult 'QIKVRT_REPOSITORY_SETUP' 'PASS' 'started'
$guid = Ensure-Guid
$owner = Ask-WithDefault 'GitHub target owner/org' $DefaultOwner 'QIKVRT_GITHUB_OWNER'
$repo = Ask-WithDefault 'GitHub target repository' $DefaultRepo 'QIKVRT_GITHUB_REPO'
$seedOwner = Ask-WithDefault 'GitHub seed owner/org' $DefaultSeedOwner 'QIKVRT_SEED_OWNER'
$seedRepo = Ask-WithDefault 'GitHub seed repository' $DefaultSeedRepo 'QIKVRT_SEED_REPO'
$target = [ordered]@{
  version = '2.13.4'
  role = $Role
  repository_guid = $guid
  github_owner = $owner
  github_repository = $repo
  github_repository_full_name = ($owner + '/' + $repo)
  seed_owner = $seedOwner
  seed_repository = $seedRepo
  seed_repository_full_name = ($seedOwner + '/' + $seedRepo)
  seed_url = ('https://github.com/' + $seedOwner + '/' + $seedRepo)
  raw_seed_manifest_url = ('https://raw.githubusercontent.com/' + $seedOwner + '/' + $seedRepo + '/main/MANIFEST.json')
  no_prompt_after_setup = $true
  node_identifies_to_seed_with_guid = $true
  remote_mutation_requires_token = $true
  author = 'Ingolf Lohmann'
  rights_holder = 'Ingolf Lohmann or a legal entity designated by him'
}
$targetPath = Join-Path $RepoRoot 'qikvrt\config\REPOSITORY_TARGET.json'
$target | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $targetPath -Encoding UTF8
Add-SetupResult 'REPOSITORY_TARGET_CONFIG' 'PASS' ($owner + '/' + $repo + ' seed=' + $seedOwner + '/' + $seedRepo)
$onboarding = [ordered]@{
  version = '2.13.4'
  event = 'QIKVRT_NODE_ONBOARDING_REQUEST'
  role = $Role
  repository_guid = $guid
  source_repository = ($owner + '/' + $repo)
  seed_repository = ($seedOwner + '/' + $seedRepo)
  seed_url = ('https://github.com/' + $seedOwner + '/' + $seedRepo)
  automatic_after_setup = $true
  no_further_human_machine_interaction_after_setup = $true
  authorized_manifest_graph_only = $true
  no_global_scanning = $true
  no_self_propagation = $true
  no_remote_mutation_without_authorization = $true
}
$onboardingPath = Join-Path $RepoRoot 'qikvrt\config\ONBOARDING.json'
$onboarding | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $onboardingPath -Encoding UTF8
$reqPath = Join-Path $OnboardingDir 'SEED_REGISTRATION_REQUEST.json'
$onboarding | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reqPath -Encoding UTF8
Add-SetupResult 'SEED_REGISTRATION_REQUEST' 'PASS' $reqPath
$JsonPath = Join-Path $RuntimeDir 'SETUP_RESULT.json'
$TsvPath = Join-Path $RuntimeDir 'SETUP_RESULT.tsv'
$script:Rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
'timestamp_utc`tgate`tstatus`tdetail' | Set-Content -LiteralPath $TsvPath -Encoding UTF8
foreach ($row in $script:Rows) { ($row.timestamp_utc + "`t" + $row.gate + "`t" + $row.status + "`t" + (($row.detail -replace "`r?`n", ' ') -replace "`t", ' ')) | Add-Content -LiteralPath $TsvPath -Encoding UTF8 }
Add-SetupResult 'SETUP_RESULT_TSV' 'PASS' $TsvPath
Add-SetupResult 'SETUP_RESULT_JSON' 'PASS' $JsonPath
exit 0
