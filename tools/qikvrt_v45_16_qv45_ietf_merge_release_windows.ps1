param([string]$Root="",[string]$Confirmation="",[string]$OriginInput="",[string]$Tag="v45.16",[string]$Branch="main",[switch]$Interactive)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "qikvrt_common_windows.ps1")
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = (Split-Path -Parent $scriptDir) }
$rootPath = Normalize-QikvrtPathArg -Path $Root -MustExist
Set-Location -LiteralPath $rootPath
& (Join-Path $scriptDir "qikvrt_v45_16_package_selftest_windows.ps1") -Root $rootPath
if ($Interactive -and [string]::IsNullOrEmpty($Confirmation)) {
  Write-Host "QIKVRT V45.16 real GitHub merge/release wrapper - QV45 + IETF evidence + clean-checkout overlay staging"
  Write-Host ""
  Write-Host "WARNING: This wrapper can perform real state-changing GitHub effects:"
  Write-Host "  stage extracted package overlay outside the repository"
  Write-Host "  clean untracked package files before checkout of origin/main"
  Write-Host "  overlay uploaded QV45 content on origin/main"
  Write-Host "  persist V45.13, V45.14, V45.15 and IETF/EFFECT_ACK evidence"
  Write-Host "  git add / commit / push"
  Write-Host "  immutable tag v45.16 creation when absent"
  Write-Host "  gh release create / upload / download-verify"
  Write-Host "  V45.16 refuses force-tag updates and refuses asset clobbering"
  Write-Host ""
  Write-Host "Required exact confirmation: JA, ICH AKZEPTIERE"
  $Confirmation = Read-Host "Type exact confirmation now"
}
if ($Confirmation -ne "JA, ICH AKZEPTIERE") {
  Persist-QikRejectedConfirmation -RootPath $rootPath -Actual $Confirmation -Context "QIKVRT V45.16 exact confirmation fail-fast gate"
  Write-QikBlock "required exact confirmation was not supplied; rejected attempt persisted before origin prompt"
}
if ($Interactive -and [string]::IsNullOrWhiteSpace($OriginInput)) {
  Write-Host ""
  Write-Host "Optional GitHub origin input. Accepted: https://github.com/OWNER/REPO.git or OWNER/REPO"
  Write-Host "Leave blank to use default: Goldkelch/qik-vrt"
  $OriginInput = Read-Host "GitHub origin URL or OWNER/REPO [default Goldkelch/qik-vrt]"
}
New-Item -ItemType Directory -Force -Path (Join-Path $rootPath "state") | Out-Null
$acceptPath = Join-Path $rootPath "state\owner_acceptance_record.v45.16.json"
$accept = [ordered]@{schema="qikvrt_owner_acceptance_v45_16";accepted_by="Ingolf Lohmann";confirmation=$Confirmation;scope="QIKVRT V45.16 merge QV45 artifact plus V45.13/V45.14/V45.15/IETF evidence with clean-checkout overlay staging";utc=(Get-Date).ToUniversalTime().ToString("o");real_github_effects_enabled_after_acceptance=$true;package_selftest_before_effect=$true;clean_checkout_overlay_staging=$true}
$accept | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $acceptPath -Encoding UTF8
Write-QikPass ("owner acceptance persisted: " + $acceptPath)
$env:QIKVRT_ENABLE_REAL_GITHUB_EFFECTS="YES"
Write-QikPass "QIKVRT_ENABLE_REAL_GITHUB_EFFECTS set by wrapper after acceptance"
$incomingZip=Join-Path $rootPath "incoming\QV45_WINZIP_OK.zip"
$incomingSha=Join-Path $rootPath "incoming\QV45_WINZIP_OK.zip.sha256"
if (-not (Test-Path -LiteralPath $incomingZip)) { Write-QikBlock "incoming QV45 ZIP missing" }
if (-not (Test-Path -LiteralPath $incomingSha)) { Write-QikBlock "incoming QV45 sidecar missing" }
$actualSha=Get-QikSha256 $incomingZip
$sideText=Get-Content -LiteralPath $incomingSha -Raw
$m=[regex]::Match($sideText,"[0-9a-fA-F]{64}")
if (-not $m.Success) { Write-QikBlock "incoming sidecar lacks SHA256" }
$expectedSha=$m.Value.ToLowerInvariant()
if ($actualSha -ne $expectedSha) { Write-QikBlock ("incoming artifact SHA mismatch expected=" + $expectedSha + " actual=" + $actualSha) }
Write-QikPass ("incoming artifact hash verified: " + $actualSha)
$tempRoot=Join-Path $env:TEMP ("qikvrt_v45_16_" + [guid]::NewGuid().ToString("N"))
$packageOverlay=Join-Path $tempRoot "package_overlay"
New-Item -ItemType Directory -Force -Path $packageOverlay | Out-Null
Copy-QikDirectoryChildren -Source $rootPath -Destination $packageOverlay
Write-QikPass ("package overlay staged before git clean/checkout: " + $packageOverlay)
$tempZip=Join-Path $tempRoot "QV45_WINZIP_OK.zip"
$tempSha=Join-Path $tempRoot "QV45_WINZIP_OK.zip.sha256"
Copy-Item -LiteralPath $incomingZip -Destination $tempZip -Force
Copy-Item -LiteralPath $incomingSha -Destination $tempSha -Force
Invoke-Qik git @("--version") | Out-Null
Invoke-Qik gh @("--version") | Out-Null
$inside=Invoke-Qik git @("rev-parse","--is-inside-work-tree") -AllowFail
if ($inside.Code -ne 0) { Write-QikCont "no .git repository found; initializing local Git repository"; Invoke-Qik git @("init") | Out-Null } else { Write-QikPass "Git repository available before remote effect attempt" }
Ensure-QikGitIdentity
$originCheck=Invoke-Qik git @("remote","get-url","origin") -AllowFail
if ($originCheck.Code -eq 0 -and -not [string]::IsNullOrWhiteSpace($originCheck.Output)) { $originUrl=($originCheck.Output.Trim() -split "`n")[0].Trim(); Write-QikPass ("git origin already configured: " + $originUrl) }
else { $originUrl=Convert-QikOrigin $OriginInput; Invoke-Qik git @("remote","add","origin",$originUrl) | Out-Null; Write-QikPass ("git origin added: " + $originUrl) }
$fetch=Invoke-Qik git @("fetch","origin",$Branch) -AllowFail
$originMainExists=($fetch.Code -eq 0)
if ($originMainExists) {
  Write-QikCont ("origin/" + $Branch + " exists; cleaning untracked package files before checkout")
  Invoke-Qik git @("reset","--hard") -AllowFail | Out-Null
  Invoke-Qik git @("clean","-fdx") | Out-Null
  Write-QikPass "working tree cleaned before origin/main checkout"
  Invoke-Qik git @("checkout","-B",$Branch,("origin/" + $Branch)) | Out-Null
  Write-QikPass "origin/main checked out as canonical base"
} else {
  Write-QikCont ("origin/" + $Branch + " unavailable; creating local branch")
  Invoke-Qik git @("checkout","-B",$Branch) | Out-Null
}
Ensure-QikGitIdentity
Copy-QikDirectoryChildren -Source $packageOverlay -Destination $rootPath
Write-QikPass "V45.16 package overlay restored after origin/main checkout"
$extractDir=Join-Path $tempRoot "extract"; New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
Expand-Archive -LiteralPath $tempZip -DestinationPath $extractDir -Force
$sourceRoot=Join-Path $extractDir "QV45"
if (-not (Test-Path -LiteralPath $sourceRoot)) { Write-QikBlock "extracted artifact does not contain QV45 root" }
Copy-QikDirectoryChildren -Source $sourceRoot -Destination $rootPath
Write-QikPass "QV45 artifact overlay restored on top of origin/main"
# Restore V45.16 control/evidence files after QV45 overlay so the release state is the next version.
Copy-QikDirectoryChildren -Source $packageOverlay -Destination $rootPath
foreach ($dir in @("dist","audit","evidence\external","evidence\failed_acceptance","evidence\packaging_errors","evidence\git_errors","state")) { New-Item -ItemType Directory -Force -Path (Join-Path $rootPath $dir) | Out-Null }
Copy-Item -LiteralPath $tempZip -Destination (Join-Path $rootPath "dist\QV45_WINZIP_OK.zip") -Force
Copy-Item -LiteralPath $tempSha -Destination (Join-Path $rootPath "dist\QV45_WINZIP_OK.zip.sha256") -Force
# Runtime evidence refresh.
$gitCase=[ordered]@{schema="qikvrt_git_checkout_untracked_overwrite_v45_16_runtime";source_version="V45.15";new_error_class="BLOCK_REMOTE_BASE_CHECKOUT_WITH_UNTRACKED_PACKAGE_OVERLAY_NOT_STAGED";repair="package overlay staged outside repo; git clean -fdx before origin/main checkout; overlay restored after checkout";utc=(Get-Date).ToUniversalTime().ToString("o")}
$gitCase | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $rootPath "evidence\git_errors\V45_15_UNTRACKED_WORKTREE_CHECKOUT_OVERWRITE.json") -Encoding UTF8
$bundlePath=Join-Path $rootPath "evidence\external\V45_16_COMBINED_EVIDENCE_BUNDLE.json"
$bundle=[ordered]@{schema="qikvrt_v45_16_combined_evidence_bundle_runtime";utc=(Get-Date).ToUniversalTime().ToString("o");tag=$Tag;branch=$Branch;origin=$originUrl;qv45_asset_sha256=$actualSha;git_checkout_repair=$gitCase;policy=[ordered]@{no_force_tag_update=$true;no_asset_clobber=$true;clean_checkout_overlay_staging=$true;exact_confirmation_required="JA, ICH AKZEPTIERE"}}
$bundle | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $bundlePath -Encoding UTF8
$bundleSha=Get-QikSha256 $bundlePath
($bundleSha + "  V45_16_COMBINED_EVIDENCE_BUNDLE.json") | Set-Content -LiteralPath (Join-Path $rootPath "evidence\external\V45_16_COMBINED_EVIDENCE_BUNDLE.json.sha256") -Encoding UTF8
Copy-Item -LiteralPath $bundlePath -Destination (Join-Path $rootPath "dist\V45_16_COMBINED_EVIDENCE_BUNDLE.json") -Force
($bundleSha + "  V45_16_COMBINED_EVIDENCE_BUNDLE.json") | Set-Content -LiteralPath (Join-Path $rootPath "dist\V45_16_COMBINED_EVIDENCE_BUNDLE.json.sha256") -Encoding UTF8
Write-QikPass "QV45 + V45.13/V45.14/V45.15 + IETF evidence overlay restored"
Invoke-Qik git @("add","-A") | Out-Null
$status=Invoke-Qik git @("status","--porcelain") -AllowFail
if ([string]::IsNullOrWhiteSpace($status.Output)) { Write-QikPass "no overlay changes to commit before push" }
else { Invoke-Qik git @("commit","-m","QIKVRT V45.16 merge QV45 with IETF evidence and clean-checkout overlay repair") | Out-Null; Write-QikPass "V45.16 overlay commit created" }
if ($originMainExists) { $anc=Invoke-Qik git @("merge-base","--is-ancestor",("origin/"+$Branch),"HEAD") -AllowFail; if ($anc.Code -ne 0) { Write-QikBlock ("origin/"+$Branch+" is not ancestor of HEAD; refusing non-ff push") }; Write-QikPass ("origin/"+$Branch+" is ancestor of HEAD; push can be fast-forward") }
$headSha=(Invoke-Qik git @("rev-parse","HEAD")).Output.Trim()
Invoke-Qik git @("push","-u","origin",$Branch) | Out-Null
Write-QikPass ("main branch pushed at " + $headSha)
$tagCheck=Invoke-Qik git @("ls-remote","--tags","origin",("refs/tags/"+$Tag)) -AllowFail
if ($tagCheck.Code -eq 0 -and -not [string]::IsNullOrWhiteSpace($tagCheck.Output)) { $remoteTagSha=($tagCheck.Output.Trim() -split "\s+")[0]; if ($remoteTagSha -ne $headSha) { Write-QikBlock ("remote tag " + $Tag + " exists at " + $remoteTagSha + " but HEAD is " + $headSha + "; refusing force update") }; Write-QikPass ("remote tag " + $Tag + " already exists at HEAD") }
else { Invoke-Qik git @("tag",$Tag) | Out-Null; Invoke-Qik git @("push","origin",$Tag) | Out-Null; Write-QikPass ("immutable tag created and pushed: " + $Tag) }
function Ensure-QikReleaseAsset { param([string]$TagName,[string]$Path,[string]$ExpectedSha,[string]$TempRoot)
  $name=Split-Path -Leaf $Path; $downloadDir=Join-Path $TempRoot ("download_" + ($name -replace '[^A-Za-z0-9_.-]','_')); New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null; $downloadPath=Join-Path $downloadDir $name
  $dl=Invoke-Qik gh @("release","download",$TagName,"-p",$name,"-D",$downloadDir) -AllowFail
  if ($dl.Code -ne 0 -or -not (Test-Path -LiteralPath $downloadPath)) { Write-QikCont ("asset not present on release; uploading without clobber: " + $name); Invoke-Qik gh @("release","upload",$TagName,$Path) | Out-Null; Remove-Item -LiteralPath $downloadDir -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null; Invoke-Qik gh @("release","download",$TagName,"-p",$name,"-D",$downloadDir) | Out-Null }
  $downloadedSha=Get-QikSha256 $downloadPath; if ($downloadedSha -ne $ExpectedSha) { Write-QikBlock ("release asset hash mismatch for " + $name + " expected=" + $ExpectedSha + " actual=" + $downloadedSha) }; Write-QikPass ("release asset verified: " + $name + " sha256=" + $downloadedSha)
}
$assetZip=Join-Path $rootPath "dist\QV45_WINZIP_OK.zip"; $assetSha=Join-Path $rootPath "dist\QV45_WINZIP_OK.zip.sha256"; $bundleAsset=Join-Path $rootPath "dist\V45_16_COMBINED_EVIDENCE_BUNDLE.json"; $bundleAssetSha=Join-Path $rootPath "dist\V45_16_COMBINED_EVIDENCE_BUNDLE.json.sha256"
$releaseView=Invoke-Qik gh @("release","view",$Tag,"--json","url","-q",".url") -AllowFail
if ($releaseView.Code -eq 0 -and -not [string]::IsNullOrWhiteSpace($releaseView.Output)) { $releaseUrl=$releaseView.Output.Trim(); Write-QikPass ("GitHub release already exists: " + $releaseUrl) }
else { $notes="QIKVRT V45.16 merges QV45_WINZIP_OK plus V45.13 rejected-confirmation, V45.14 packaging-error, V45.15 clean-checkout overlay repair, and IETF EFFECT_ACK evidence. No force-tag update. No asset clobber."; $create=Invoke-Qik gh @("release","create",$Tag,$assetZip,$assetSha,$bundleAsset,$bundleAssetSha,"--title","QIKVRT V45.16 QV45 + IETF Evidence Clean-Checkout Overlay Repair","--notes",$notes) -AllowFail; if ($create.Code -ne 0) { Write-QikBlock "GitHub release create failed" }; $releaseUrl=(Invoke-Qik gh @("release","view",$Tag,"--json","url","-q",".url")).Output.Trim(); Write-QikPass ("GitHub release created: " + $releaseUrl) }
Ensure-QikReleaseAsset -TagName $Tag -Path $assetZip -ExpectedSha $actualSha -TempRoot $tempRoot
Ensure-QikReleaseAsset -TagName $Tag -Path $assetSha -ExpectedSha (Get-QikSha256 $assetSha) -TempRoot $tempRoot
Ensure-QikReleaseAsset -TagName $Tag -Path $bundleAsset -ExpectedSha (Get-QikSha256 $bundleAsset) -TempRoot $tempRoot
Ensure-QikReleaseAsset -TagName $Tag -Path $bundleAssetSha -ExpectedSha (Get-QikSha256 $bundleAssetSha) -TempRoot $tempRoot
$tagRemote=(Invoke-Qik git @("ls-remote","--tags","origin",("refs/tags/"+$Tag))).Output.Trim(); $tagSha=($tagRemote -split "\s+")[0]
if ($tagSha -ne $headSha) { Write-QikBlock ("tag/head mismatch after release tag=" + $tagSha + " head=" + $headSha) }
Write-QikPass "GitHub remote effect evidence gate ok"
Write-QikPass "QIKVRT V45.16 QV45 + IETF evidence + clean-checkout overlay repair merge/release persisted and verified"
exit 0
