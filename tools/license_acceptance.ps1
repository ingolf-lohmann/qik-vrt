# QIKVRT Artifact Header
# Deutsch: Verpflichtende Laufzeit-Akzeptanz von Urheber-, Rechte- und Lizenzbedingungen vor jeder weiteren Aktivität.
# English: Mandatory runtime acceptance of authorship, rights and license terms before any further activity.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
param([string]$RepoRoot = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
function FullPath([string]$p){ return [System.IO.Path]::GetFullPath($p) }
$RepoRoot = FullPath $RepoRoot
$configDir = Join-Path $RepoRoot 'qikvrt\config'
$ledgerDir = Join-Path $RepoRoot 'qikvrt\ledger'
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
New-Item -ItemType Directory -Force -Path $ledgerDir | Out-Null
$acceptedFile = Join-Path $configDir 'LICENSE_ACCEPTED.json'
$ledgerFile = Join-Path $ledgerDir 'LICENSE_RUNTIME_ACCEPTANCE.jsonl'
function Persist-Acceptance([string]$Source){
  $obj = [ordered]@{
    version = '2.13.4'
    accepted = $true
    accepted_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    source = $Source
    author = 'Ingolf Lohmann'
    rights_holder = 'Ingolf Lohmann or a legal entity designated by him'
    software_license = 'Apache-2.0'
    non_software_license = 'CC BY-NC-ND 4.0 unless otherwise stated'
    gate = 'QIKVRT_LICENSE_AUTHORSHIP_RIGHTS_ACCEPTANCE_BEFORE_ACTIVITY'
  }
  ($obj | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $acceptedFile -Encoding UTF8
  ($obj | ConvertTo-Json -Compress -Depth 5) | Add-Content -LiteralPath $ledgerFile -Encoding UTF8
  Write-Host ("LICENSE_RUNTIME_ACCEPTANCE`tPASS`taccepted and persisted before further QIKVRT activity")
}
if (Test-Path -LiteralPath $acceptedFile) {
  try {
    $cfg = Get-Content -LiteralPath $acceptedFile -Raw | ConvertFrom-Json
    if ($cfg.accepted -eq $true) {
      Write-Host ("LICENSE_RUNTIME_ACCEPTANCE`tPASS`tprevious acceptance persisted")
      exit 0
    }
  } catch { }
}
if ($env:QIKVRT_ACCEPT_LICENSE -eq '1') { Persist-Acceptance 'environment:QIKVRT_ACCEPT_LICENSE'; exit 0 }
Write-Host ''
Write-Host 'QIKVRT LICENSE / AUTHORSHIP / RIGHTS ACCEPTANCE'
Write-Host 'DE: Vor jeder weiteren QIKVRT-Aktivitaet muessen Urheber-, Rechte- und Lizenzbedingungen akzeptiert werden.'
Write-Host 'EN: Before any further QIKVRT activity, authorship, rights and license terms must be accepted.'
Write-Host 'Urheber / Author: Ingolf Lohmann'
Write-Host 'Rechteinhaber / Rights holder: Ingolf Lohmann or a legal entity designated by him'
Write-Host 'Software license: Apache-2.0'
Write-Host 'Non-software/docs license: CC BY-NC-ND 4.0 unless otherwise stated'
Write-Host ''
$answer = Read-Host 'Akzeptieren? Type JA or YES to continue'
$normalized = ($answer | ForEach-Object { $_.Trim().ToUpperInvariant() })
if (($normalized -eq 'JA') -or ($normalized -eq 'J') -or ($normalized -eq 'YES') -or ($normalized -eq 'Y') -or ($normalized -eq 'ACCEPT') -or ($normalized -eq 'I ACCEPT')) {
  Persist-Acceptance 'interactive'
  exit 0
}
Write-Host ("LICENSE_RUNTIME_ACCEPTANCE`tBLOCK`tnot accepted; no further QIKVRT activity allowed")
exit 41
