param(
  [switch]$RequireGithubRelease,
  [string]$EvidenceJson = ""
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")

if ($RequireGithubRelease) {
  if ([string]::IsNullOrWhiteSpace($EvidenceJson)) {
    Write-QikvrtBlock "RequireGithubRelease set but EvidenceJson missing"
    exit 1
  }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "qikvrt_github_remote_effect_evidence_gate_windows.ps1") -EvidenceJson $EvidenceJson
  if ($LASTEXITCODE -ne 0) { exit 1 }
  Write-QikvrtPass "master gate with real GitHub release evidence ok"
  exit 0
}

Write-QikvrtPass "master local structure gate ok"
Write-Host "REMOTE_RELEASE_STATUS = BLOCK_UNTIL_LIVE_GITHUB_EVIDENCE"
exit 0
