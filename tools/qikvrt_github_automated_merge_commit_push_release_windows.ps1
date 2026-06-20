param(
  [string]$Repo = ".",
  [string]$TargetBranch = "main",
  [string]$SourceBranch = "",
  [string]$Tag = "v45.12",
  [string]$Title = "QIKVRT V45.12",
  [string]$AcceptanceJson = ".\state\owner_acceptance_record.json",
  [string]$EvidenceJson = ".\audit\github_remote_effect_evidence.v45.12.json",
  [string]$Asset = "",
  [string]$CommitMessage = "QIKVRT V45.12 evidence-freeze no-force-tag real GitHub release repository",
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
    evidence_version = "QIKVRT_GITHUB_REMOTE_EFFECT_EVIDENCE_V45_12"
    status = "BLOCK"
    release_claim = $false
    real_remote_effects = $false
    no_force_tag_update = $true
    tag_force_updated = $false
    asset_clobbered = $false
    reason = $Reason
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    remediation = "Run QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd. V45.12 refuses force-tag updates and release asset clobbering; use a new tag if the old tag/release points elsewhere."
  }
  Write-QikvrtJson -Path $EvidenceJson -Object $ev
  Write-QikvrtBlock $Reason
  exit $Code
}
if (!$RealRemoteEffects) { FailEvidence "RealRemoteEffects switch missing" }
if ($env:QIKVRT_ENABLE_REAL_GITHUB_EFFECTS -ne "YES") { FailEvidence "QIKVRT_ENABLE_REAL_GITHUB_EFFECTS is not YES; run QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd so interactive acceptance is persisted before the variable is set" }
try { Assert-QikvrtCommand "git" | Out-Null } catch { FailEvidence $_.Exception.Message 20 }
try { Assert-QikvrtCommand "gh" | Out-Null } catch { FailEvidence $_.Exception.Message 20 }
$repoPath = (Resolve-Path -LiteralPath $Repo).Path
Set-Location $repoPath
try { $acc = Read-QikvrtJson $AcceptanceJson } catch { FailEvidence $_.Exception.Message }
if ($acc.status -ne "ACCEPTED" -or $acc.persisted -ne $true) { FailEvidence "owner acceptance missing or not persisted" }
$insideProbe = Invoke-QikvrtCapture "git" @("rev-parse","--is-inside-work-tree")
if ($insideProbe.ExitCode -ne 0 -or $insideProbe.Stdout.Trim() -ne "true") {
  if (!$InitializeGitIfMissing) { FailEvidence "not a git repository and InitializeGitIfMissing was not set" 31 }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "qikvrt_git_bootstrap_windows.ps1") -Repo $repoPath -TargetBranch $TargetBranch -RemoteUrl $RemoteUrl -CommitMessage "QIKVRT V45.12 evidence-freeze overlay bootstrap before immutable GitHub release" -GitUserName $GitUserName -GitUserEmail $GitUserEmail
  if ($LASTEXITCODE -ne 0) { FailEvidence "git bootstrap failed; see previous BLOCK message" $LASTEXITCODE }
} else { Write-QikvrtPass "Git repository available before remote effect attempt" }
try { Ensure-QikvrtLocalGitIdentity -GitUserName $GitUserName -GitUserEmail $GitUserEmail } catch { FailEvidence $_.Exception.Message 32 }
$authProbe = Invoke-QikvrtCapture "gh" @("auth","status")
if ($authProbe.ExitCode -ne 0) { FailEvidence "GitHub CLI is not authenticated; run: gh auth login" 21 }
$start = (Get-Date).ToUniversalTime().ToString("o")
$originProbe = Invoke-QikvrtCapture "git" @("remote","get-url","origin")
if ($originProbe.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($originProbe.Stdout.Trim())) {
  if (![string]::IsNullOrWhiteSpace($RemoteUrl)) {
    $normalized = Normalize-QikvrtGitHubRemote $RemoteUrl
    & git remote add origin $normalized
    if ($LASTEXITCODE -ne 0) { FailEvidence "git remote add origin failed" }
    $origin = $normalized
  } else { FailEvidence "git origin missing; cannot push or release without GitHub remote URL/OWNER/REPO" 30 }
} else { $origin = $originProbe.Stdout.Trim() }
if ([string]::IsNullOrWhiteSpace($origin)) { FailEvidence "git origin resolved to empty string" 30 }
$remoteHeadProbe = Invoke-QikvrtCapture "git" @("ls-remote","--heads","origin",$TargetBranch)
if ($remoteHeadProbe.ExitCode -eq 0 -and ![string]::IsNullOrWhiteSpace($remoteHeadProbe.Stdout.Trim())) {
  & git fetch origin $TargetBranch
  if ($LASTEXITCODE -ne 0) { FailEvidence "git fetch origin target branch failed" }
  $ancestorProbe = Invoke-QikvrtCapture "git" @("merge-base","--is-ancestor",("origin/"+$TargetBranch),"HEAD")
  if ($ancestorProbe.ExitCode -ne 0) { FailEvidence "origin/$TargetBranch is not ancestor of HEAD; refusing divergent push" 41 }
  Write-QikvrtPass "origin/$TargetBranch is ancestor of HEAD; no divergent pull required"
} else { Write-QikvrtContinue "remote branch not found; first push will create origin/$TargetBranch" }
if (![string]::IsNullOrWhiteSpace($SourceBranch)) { & git merge --no-ff $SourceBranch -m "Merge $SourceBranch into $TargetBranch for $Tag"; if ($LASTEXITCODE -ne 0) { FailEvidence "git merge failed" } }
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
$headProbe = Invoke-QikvrtCapture "git" @("rev-parse","--verify","HEAD")
if ($headProbe.ExitCode -ne 0) { & git commit -m $CommitMessage; if ($LASTEXITCODE -ne 0) { FailEvidence "git initial commit failed after repository-local identity bootstrap" } }
elseif ($status) { & git commit -m $CommitMessage; if ($LASTEXITCODE -ne 0) { FailEvidence "git commit failed after repository-local identity bootstrap" } }
else { Write-QikvrtPass "no local changes to commit before push" }
$localSha = (& git rev-parse HEAD).Trim().ToLowerInvariant()
if ([string]::IsNullOrWhiteSpace($localSha)) { FailEvidence "local commit SHA missing" }
& git push -u origin $TargetBranch
if ($LASTEXITCODE -ne 0) { FailEvidence "git push failed; check origin URL, credentials and repository permissions" }
$remoteSha = Get-QikvrtRemoteRefSha -Ref ("refs/heads/"+$TargetBranch)
if ([string]::IsNullOrWhiteSpace($remoteSha)) { FailEvidence "remote branch ref not found after push" }
$pushedOk = ($localSha -eq $remoteSha.ToLowerInvariant())
if (!$pushedOk) { FailEvidence "remote SHA does not match local SHA after push" }
# V45.12 evidence freeze: immutable tag rule. Existing tag may only pass if it already points at localSha.
$existingRemoteTagSha = Get-QikvrtRemoteRefSha -Ref ("refs/tags/"+$Tag)
$tagPreexisting = ![string]::IsNullOrWhiteSpace($existingRemoteTagSha)
$tagCreated = $false
if ($tagPreexisting) {
  if ($existingRemoteTagSha.ToLowerInvariant() -ne $localSha) { FailEvidence "remote tag $Tag already exists at $existingRemoteTagSha; V45.12 forbids force-tag update to $localSha. Use a new tag." 52 }
  Write-QikvrtPass "remote tag $Tag already exists and already points to local HEAD; no tag move performed"
} else {
  $localTagProbe = Invoke-QikvrtCapture "git" @("rev-parse","-q","--verify",("refs/tags/"+$Tag))
  if ($localTagProbe.ExitCode -eq 0 -and ![string]::IsNullOrWhiteSpace($localTagProbe.Stdout.Trim())) {
    $localTagSha = $localTagProbe.Stdout.Trim().ToLowerInvariant()
    if ($localTagSha -ne $localSha) { FailEvidence "local tag $Tag already exists at $localTagSha; V45.12 refuses moving it to $localSha" 53 }
  } else {
    & git tag $Tag $localSha
    if ($LASTEXITCODE -ne 0) { FailEvidence "git tag creation failed" }
  }
  & git push origin ("refs/tags/"+$Tag)
  if ($LASTEXITCODE -ne 0) { FailEvidence "git push tag failed; V45.12 refuses tag-moving push semantics" }
  $tagCreated = $true
}
$remoteTagSha = Get-QikvrtRemoteRefSha -Ref ("refs/tags/"+$Tag)
if ([string]::IsNullOrWhiteSpace($remoteTagSha)) { FailEvidence "remote tag ref missing after immutable tag step" }
if ($remoteTagSha.ToLowerInvariant() -ne $localSha) { FailEvidence "remote tag $Tag does not point to local commit after immutable tag step" }
$releaseViewProbe = Invoke-QikvrtCapture "gh" @("release","view",$Tag)
$releaseCreated = $false
if ($releaseViewProbe.ExitCode -ne 0) {
  & gh release create $Tag --target $localSha --title $Title --notes "QIKVRT V45.12 evidence-freeze release: no force-tag update, no release asset clobber, Product Owner acceptance persisted before real GitHub effect."
  if ($LASTEXITCODE -ne 0) { FailEvidence "gh release create failed" }
  $releaseCreated = $true
} else { Write-QikvrtPass "GitHub release already exists; V45.12 will verify asset and refuse clobbering" }
$uploadedAssets = @()
$assetUploaded = $false
$assetAlreadyExisted = $false
if (![string]::IsNullOrWhiteSpace($Asset)) {
  $assetName = Split-Path -Leaf $Asset
  $localAssetSha = Get-QikvrtSha256 $Asset
  $assetAlreadyExisted = Test-QikvrtReleaseAssetExists -Tag $Tag -AssetName $assetName
  if (!$assetAlreadyExisted) {
    & gh release upload $Tag $Asset
    if ($LASTEXITCODE -ne 0) { FailEvidence "gh release upload failed; V45.12 refuses release asset overwrite semantics" }
    $assetUploaded = $true
  } else { Write-QikvrtPass "release asset already exists; V45.12 will download-verify and will not clobber" }
  $downloadDir = Join-Path $env:TEMP ("qikvrt_asset_download_" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
  & gh release download $Tag --dir $downloadDir --pattern $assetName
  if ($LASTEXITCODE -ne 0) { FailEvidence "gh release download for hash verification failed" }
  $downloaded = Join-Path $downloadDir $assetName
  if (!(Test-Path -LiteralPath $downloaded)) { FailEvidence "downloaded release asset missing" }
  $downloadedSha = Get-QikvrtSha256 $downloaded
  Remove-Item -LiteralPath $downloadDir -Recurse -Force
  if ($localAssetSha -ne $downloadedSha) { FailEvidence "existing/downloaded release asset hash differs from local asset; V45.12 refuses clobber" 54 }
  $uploadedAssets += [ordered]@{ name=$assetName; local_path=$Asset; local_sha256=$localAssetSha; downloaded_sha256=$downloadedSha; sha256_match=($localAssetSha -eq $downloadedSha); uploaded_this_run=$assetUploaded; already_existed_before_upload=$assetAlreadyExisted }
}
if ($uploadedAssets.Count -lt 1) { FailEvidence "no release asset uploaded or verified" }
$releaseJsonRaw = (& gh release view $Tag --json id,url,tagName,targetCommitish,createdAt,publishedAt)
if ($LASTEXITCODE -ne 0) { FailEvidence "gh release view json failed" }
$release = $releaseJsonRaw | ConvertFrom-Json
$actor = ""
try { $actor = (& gh api user --jq .login).Trim() } catch { $actor = "unknown" }
$ev = [ordered]@{
  evidence_version = "QIKVRT_GITHUB_REMOTE_EFFECT_EVIDENCE_V45_12"
  status = "PASS"
  release_claim = $true
  real_remote_effects = $true
  freeze_policy = "NO_FORCE_TAG_UPDATE_AND_NO_RELEASE_ASSET_CLOBBER"
  no_force_tag_update = $true
  tag_force_updated = $false
  asset_clobbered = $false
  repository_url = $origin
  target_branch = $TargetBranch
  source_branch = $SourceBranch
  local_commit_sha = $localSha
  remote_commit_sha = $remoteSha
  remote_tag_sha = $remoteTagSha
  pushed_ref_verified = $pushedOk
  tag_ref_verified = ($remoteTagSha.ToLowerInvariant() -eq $localSha)
  release_tag = $Tag
  tag_preexisting_before_run = $tagPreexisting
  tag_created_this_run = $tagCreated
  release_created_this_run = $releaseCreated
  release_id = $release.id
  release_url = $release.url
  release_target_commitish = $release.targetCommitish
  release_created_at = $release.createdAt
  release_published_at = $release.publishedAt
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
Write-QikvrtPass "real GitHub merge/commit/push/release evidence freeze persisted and verified"
exit 0
