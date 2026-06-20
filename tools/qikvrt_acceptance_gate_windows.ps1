param(
  [string]$AcceptedBy = "Ingolf Lohmann",
  [string]$Scope = "QIKVRT V45.12 evidence-freeze GitHub merge commit push release",
  [string]$OutFile = ".\state\owner_acceptance_record.json",
  [string]$Confirmation = ""
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")
Write-Host "QIKVRT V45.12 Product Owner acceptance gate"
Write-Host "Scope: $Scope"
Write-Host "Required exact confirmation: JA, ICH AKZEPTIERE"
if ([string]::IsNullOrWhiteSpace($Confirmation)) { $Confirmation = Read-Host "Enter exact confirmation" }
if ($Confirmation -ne "JA, ICH AKZEPTIERE") { Write-QikvrtBlock "acceptance declined or not exact"; exit 1 }
$record = [ordered]@{
  version = "V45.12"
  status = "ACCEPTED"
  persisted = $true
  accepted_by = $AcceptedBy
  timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
  scope = $Scope
  required_confirmation = "JA, ICH AKZEPTIERE"
  requirement = "No GitHub state-changing effect before persisted Product Owner acceptance. V45.12 additionally forbids force-tag updates and release-asset clobbering."
  effect_boundary = "git fetch/checkout, overlay commit, push branch, create immutable tag when absent, create release when absent, upload asset only when absent, download-verify asset, freeze evidence publication"
}
Write-QikvrtJson -Path $OutFile -Object $record
Write-QikvrtPass "owner acceptance persisted: $OutFile"
exit 0
