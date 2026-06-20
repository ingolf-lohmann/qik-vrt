param(
  [string]$Repo = ".",
  [string]$TargetBranch = "main",
  [string]$SourceBranch = "",
  [string]$Tag = "v45.11",
  [string]$Title = "QIKVRT V45.11",
  [string]$AcceptanceJson = ".\state\owner_acceptance_record.json",
  [string]$EvidenceJson = ".\audit\github_remote_effect_evidence.v45.11.json",
  [string]$Asset = "",
  [string]$CommitMessage = "QIKVRT V45.11 Git bootstrap origin-safe full repository",
  [string]$RemoteUrl = "",
  [switch]$InitializeGitIfMissing,
  [switch]$RealRemoteEffects,
  [string]$GitUserName = "Ingolf Lohmann",
  [string]$GitUserEmail = "ingolf.lohmann@web.de"
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")

function FailEvidence([string]$Reason, [int]$Code = 1) {
  $ev = [ordered]@{
    evidence_version = "QIKVRT_GITHUB_REMOTE_EFFECT_EVIDENCE_V45_11"
    status = "BLOCK"
    release_claim = $false
    real_remote_effects = $false
    reason = $Reason
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    remediation = "Run QIKVRT_V45_11_REAL_GITHUB_RELEASE.cmd. The wrapper bootstraps local Git identity, uses origin/main as the canonical base when it exists, creates a non-divergent overlay commit, then requires gh authentication, push rights and release evidence. No PASS is possible without real remote evidence."
  }
  Write-QikvrtJson -Path $EvidenceJson -Object $ev
  Write-QikvrtBlock $Reason
  exit $Code
}

if (!$RealRemoteEffects) { FailEvidence "RealRemoteEffects switch missing" }
if ($env:QIKVRT_ENABLE_REAL_GITHUB_EFFECTS -ne "YES") { FailEvidence "QIKVRT_ENABLE_REAL_GITHUB_EFFECTS is not YES; run QIKVRT_V45_11_REAL_GITHUB_RELEASE.cmd so interactive acceptance is persisted before the variable is set" }
try { Assert-QikvrtCommand "git" | Out-Null } catch { FailEvidence $_.Exception.Message 20 }
try { Assert-QikvrtCommand "gh" | Out-Null } catch { FailEvidence $_.Exception.Message 20 }

$repoPath = (Resolve-Path -LiteralPath $Repo).Path
Set-Location $repoPath

try { $acc = Read-QikvrtJson $AcceptanceJson } catch { FailEvidence $_.Exception.Message }
if ($acc.status -ne "ACCEPTED" -or $acc.persisted -ne $true) { FailEvidence "owner acceptance missing or not persisted" }

# .git bootstrap: ZIP extractions are not Git repositories. This must be handled cleanly.
$insideProbe = Invoke-QikvrtCapture "git" @("rev-parse", "--is-inside-work-tree")
if ($insideProbe.ExitCode -ne 0 -or $insideProbe.Stdout.Trim() -ne "true") {
  if (!$InitializeGitIfMissing) { FailEvidence "not a git repository and InitializeGitIfMissing was not set" 31 }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "qikvrt_git_bootstrap_windows.ps1") -Repo $repoPath -TargetBranch $TargetBranch -RemoteUrl $RemoteUrl -CommitMessage "QIKVRT V45.11 remote-based overlay bootstrap before real GitHub release" -GitUserName $GitUserName -GitUserEmail $GitUserEmail
  if ($LASTEXITCODE -ne 0) { FailEvidence "git bootstrap failed; see previous BLOCK message" $LASTEXITCODE }
} else {
  Write-QikvrtPass "Git repository available before remote effect attempt"
}

# V45.11: ensure repository-local identity after .git exists and before later commit paths.
try { Ensure-QikvrtLocalGitIdentity -GitUserName $GitUserName -GitUserEmail $GitUserEmail } catch { FailEvidence $_.Exception.Message 32 }

# gh authentication must be checked before mutating remote state.
$authProbe = Invoke-QikvrtCapture "gh" @("auth", "status")
if ($authProbe.ExitCode -ne 0) { FailEvidence "GitHub CLI is not authenticated; run: gh auth login" 21 }

$start = (Get-Date).ToUniversalTime().ToString("o")
$originProbe = Invoke-QikvrtCapture "git" @("remote", "get-url", "origin")
if ($originProbe.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($originProbe.Stdout.Trim())) {
  if (![string]::IsNullOrWhiteSpace($RemoteUrl)) {
    $normalized = Normalize-QikvrtGitHubRemote $RemoteUrl
    & git remote add origin $normalized
    if ($LASTEXITCODE -ne 0) { FailEvidence "git remote add origin failed" }
    $origin = $normalized
  } else {
    FailEvidence "git origin missing; cannot push or release without GitHub remote URL/OWNER/REPO" 30
  }
} else {
  $origin = $originProbe.Stdout.Trim()
}
if ([string]::IsNullOrWhiteSpace($origin)) { FailEvidence "git origin resolved to empty string" 30 }

# V45.11 divergence repair: never pull --ff-only after creating an unrelated local root commit.
# qikvrt_git_bootstrap_windows.ps1 has already used origin/<branch> as the canonical base when it exists.
# Here we only verify the ancestry relation required for a safe fast-forward push.
$remoteHeadProbe = Invoke-QikvrtCapture "git" @("ls-remote", "--heads", "origin", $TargetBranch)
if ($remoteHeadProbe.ExitCode -eq 0 -and ![string]::IsNullOrWhiteSpace($remoteHeadProbe.Stdout.Trim())) {
  & git fetch origin $TargetBranch
  if ($LASTEXITCODE -ne 0) { FailEvidence "git fetch origin target branch failed" }
  $ancestorProbe = Invoke-QikvrtCapture "git" @("merge-base", "--is-ancestor", ("origin/" + $TargetBranch), "HEAD")
  if ($ancestorProbe.ExitCode -ne 0) {
    FailEvidence "origin/$TargetBranch is not ancestor of HEAD; refusing divergent push. V45.11 requires remote-based overlay bootstrap, not pull --ff-only over unrelated histories." 41
  }
  Write-QikvrtPass "origin/$TargetBranch is ancestor of HEAD; no divergent pull required"
} else {
  Write-QikvrtContinue "remote branch not found; first push will create origin/$TargetBranch"
}

if (![string]::IsNullOrWhiteSpace($SourceBranch)) {
  & git merge --no-ff $SourceBranch -m "Merge $SourceBranch into $TargetBranch for $Tag"
  if ($LASTEXITCODE -ne 0) { FailEvidence "git merge failed" }
}

# Build asset before commit so the release asset and its sidecar/manifest can be included if desired.
if (![string]::IsNullOrWhiteSpace($Asset) -and !(Test-Path -LiteralPath $Asset)) {
  Write-QikvrtContinue "asset missing before release; building repository ZIP first: $Asset"
  $assetOutDir = Split-Path -Parent $Asset
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "qikvrt_build_zip_and_hash_windows.ps1") -Root $repoPath -OutDir $assetOutDir
  if ($LASTEXITCODE -ne 0) { FailEvidence "asset build before release failed" }
}
if (![string]::IsNullOrWhiteSpace($Asset) -and !(Test-Path -LiteralPath $Asset)) { FailEvidence "asset missing after build: $Asset" }

& git add -A
if ($LASTEXITCODE -ne 0) { FailEvidence "git add failed" }
$status = (& git status --porcelain)
$headProbe = Invoke-QikvrtCapture "git" @("rev-parse", "--verify", "HEAD")
if ($headProbe.ExitCode -ne 0) {
  & git commit -m $CommitMessage
  if ($LASTEXITCODE -ne 0) { FailEvidence "git initial commit failed after repository-local identity bootstrap" }
} elseif ($status) {
  & git commit -m $CommitMessage
  if ($LASTEXITCODE -ne 0) { FailEvidence "git commit failed after repository-local identity bootstrap" }
} else {
  Write-QikvrtPass "no local changes to commit before push"
}
$localSha = (& git rev-parse HEAD).Trim()
if ([string]::IsNullOrWhiteSpace($localSha)) { FailEvidence "local commit SHA missing" }

& git push -u origin $TargetBranch
if ($LASTEXITCODE -ne 0) { FailEvidence "git push failed; check origin URL, credentials and repository permissions" }
$remoteLineProbe = Invoke-QikvrtCapture "git" @("ls-remote", "origin", ("refs/heads/" + $TargetBranch))
if ($remoteLineProbe.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($remoteLineProbe.Stdout.Trim())) { FailEvidence "remote branch ref not found after push" }
$remoteSha = ($remoteLineProbe.Stdout.Trim() -split "\s+")[0]
$pushedOk = ($localSha.ToLowerInvariant() -eq $remoteSha.ToLowerInvariant())
if (!$pushedOk) { FailEvidence "remote SHA does not match local SHA after push" }

& git tag -f $Tag $localSha
if ($LASTEXITCODE -ne 0) { FailEvidence "git tag failed" }
& git push origin ("refs/tags/" + $Tag) --force
if ($LASTEXITCODE -ne 0) { FailEvidence "git push tag failed" }

$releaseViewProbe = Invoke-QikvrtCapture "gh" @("release", "view", $Tag)
if ($releaseViewProbe.ExitCode -ne 0) {
  & gh release create $Tag --target $localSha --title $Title --notes "QIKVRT V45.11 real GitHub release generated after interactive persisted Product Owner acceptance and Git bootstrap/origin-safe remote evidence repair."
  if ($LASTEXITCODE -ne 0) { FailEvidence "gh release create failed" }
} else {
  Write-QikvrtPass "GitHub release already exists; uploading/verifying asset against existing release"
}

$uploadedAssets = @()
if (![string]::IsNullOrWhiteSpace($Asset)) {
  $assetName = Split-Path -Leaf $Asset
  $localAssetSha = Get-QikvrtSha256 $Asset
  & gh release upload $Tag $Asset --clobber
  if ($LASTEXITCODE -ne 0) { FailEvidence "gh release upload failed" }
  $downloadDir = Join-Path $env:TEMP ("qikvrt_asset_download_" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
  & gh release download $Tag --dir $downloadDir --pattern $assetName --clobber
  if ($LASTEXITCODE -ne 0) { FailEvidence "gh release download for hash verification failed" }
  $downloaded = Join-Path $downloadDir $assetName
  if (!(Test-Path -LiteralPath $downloaded)) { FailEvidence "downloaded release asset missing" }
  $downloadedSha = Get-QikvrtSha256 $downloaded
  Remove-Item -LiteralPath $downloadDir -Recurse -Force
  $uploadedAssets += [ordered]@{
    name = $assetName
    local_path = $Asset
    local_sha256 = $localAssetSha
    downloaded_sha256 = $downloadedSha
    sha256_match = ($localAssetSha -eq $downloadedSha)
  }
}
if ($uploadedAssets.Count -lt 1) { FailEvidence "no release asset uploaded and verified" }

$releaseJsonRaw = (& gh release view $Tag --json id,url,tagName,targetCommitish)
if ($LASTEXITCODE -ne 0) { FailEvidence "gh release view json failed" }
$release = $releaseJsonRaw | ConvertFrom-Json
$actor = ""
try { $actor = (& gh api user --jq .login).Trim() } catch { $actor = "unknown" }

$ev = [ordered]@{
  evidence_version = "QIKVRT_GITHUB_REMOTE_EFFECT_EVIDENCE_V45_11"
  status = "PASS"
  release_claim = $true
  real_remote_effects = $true
  repository_url = $origin
  target_branch = $TargetBranch
  source_branch = $SourceBranch
  local_commit_sha = $localSha
  remote_commit_sha = $remoteSha
  pushed_ref_verified = $pushedOk
  release_tag = $Tag
  release_id = $release.id
  release_url = $release.url
  release_target_commitish = $release.targetCommitish
  acceptance = $acc
  uploaded_assets = $uploadedAssets
  actor = $actor
  timestamp_start_utc = $start
  timestamp_end_utc = (Get-Date).ToUniversalTime().ToString("o")
  generated_by = "tools/qikvrt_github_automated_merge_commit_push_release_windows.ps1"
}
Write-QikvrtJson -Path $EvidenceJson -Object $ev

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "qikvrt_github_remote_effect_evidence_gate_windows.ps1") -EvidenceJson $EvidenceJson
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-QikvrtPass "real GitHub merge/commit/push/release evidence persisted and verified"
exit 0
