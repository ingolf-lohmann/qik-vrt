param(
  [Parameter(Mandatory=$true)][string]$EvidenceJson
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")

function Fail([string]$m) { Write-QikvrtBlock $m; exit 1 }

try { $ev = Read-QikvrtJson $EvidenceJson } catch { Fail $_.Exception.Message }

if ($ev.evidence_version -ne "QIKVRT_GITHUB_REMOTE_EFFECT_EVIDENCE_V45_11") { Fail "wrong evidence_version" }
if ($ev.status -ne "PASS") { Fail "status is not PASS" }
if ($ev.release_claim -ne $true) { Fail "release_claim is not true" }
if ($ev.real_remote_effects -ne $true) { Fail "real_remote_effects is not true" }
if ([string]::IsNullOrWhiteSpace($ev.repository_url)) { Fail "repository_url missing" }
if ([string]::IsNullOrWhiteSpace($ev.target_branch)) { Fail "target_branch missing" }
if ($ev.local_commit_sha -notmatch '^[0-9a-fA-F]{40,64}$') { Fail "local_commit_sha invalid" }
if ($ev.remote_commit_sha -notmatch '^[0-9a-fA-F]{40,64}$') { Fail "remote_commit_sha invalid" }
if ($ev.local_commit_sha.ToString().ToLowerInvariant() -ne $ev.remote_commit_sha.ToString().ToLowerInvariant()) { Fail "remote_commit_sha does not match local_commit_sha" }
if ($ev.pushed_ref_verified -ne $true) { Fail "pushed_ref_verified is not true" }
if ([string]::IsNullOrWhiteSpace($ev.release_tag)) { Fail "release_tag missing" }
if ([string]::IsNullOrWhiteSpace([string]$ev.release_id)) { Fail "release_id missing" }
if ($ev.release_url -notmatch '^https://github\.com/.+/.+/releases/tag/.+') { Fail "release_url invalid" }
if ([string]::IsNullOrWhiteSpace($ev.release_target_commitish)) { Fail "release_target_commitish missing" }
if ($null -eq $ev.acceptance) { Fail "acceptance missing" }
if ($ev.acceptance.status -ne "ACCEPTED") { Fail "acceptance status not ACCEPTED" }
if ($ev.acceptance.persisted -ne $true) { Fail "acceptance persisted not true" }
if ($null -eq $ev.uploaded_assets -or $ev.uploaded_assets.Count -lt 1) { Fail "uploaded_assets missing" }
foreach ($asset in $ev.uploaded_assets) {
  if ([string]::IsNullOrWhiteSpace($asset.name)) { Fail "asset name missing" }
  if ($asset.local_sha256 -notmatch '^[0-9a-fA-F]{64}$') { Fail "asset local_sha256 invalid" }
  if ($asset.downloaded_sha256 -notmatch '^[0-9a-fA-F]{64}$') { Fail "asset downloaded_sha256 invalid" }
  if ($asset.sha256_match -ne $true) { Fail "asset sha256_match not true" }
  if ($asset.local_sha256.ToString().ToLowerInvariant() -ne $asset.downloaded_sha256.ToString().ToLowerInvariant()) { Fail "asset downloaded hash differs" }
}
if ($ev.synthetic_example -eq $true) { Fail "synthetic example cannot be used as real evidence" }

Write-QikvrtPass "GitHub remote effect evidence gate ok"
exit 0
