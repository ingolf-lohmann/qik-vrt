param(
  [string]$Repo = ".",
  [string]$TargetBranch = "main",
  [string]$RemoteUrl = "",
  [string]$CommitMessage = "QIKVRT V45.12 evidence-freeze overlay bootstrap before immutable GitHub release",
  [string]$GitUserName = "Ingolf Lohmann",
  [string]$GitUserEmail = "ingolf.lohmann@web.de"
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")
try { Assert-QikvrtCommand "git" | Out-Null } catch { Write-QikvrtBlock $_.Exception.Message; exit 20 }
$repoPath = (Resolve-Path -LiteralPath $Repo).Path
Set-Location $repoPath
$normalized = Normalize-QikvrtGitHubRemote $RemoteUrl
$inside = $false
$probe = Invoke-QikvrtCapture "git" @("rev-parse","--is-inside-work-tree")
if ($probe.ExitCode -eq 0 -and $probe.Stdout.Trim() -eq "true") { $inside = $true }
if (!$inside) { Write-QikvrtContinue "no .git repository found; initializing local Git repository"; & git init; if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "git init failed"; exit 1 } } else { Write-QikvrtPass "existing Git repository detected" }
try { Ensure-QikvrtLocalGitIdentity -GitUserName $GitUserName -GitUserEmail $GitUserEmail } catch { Write-QikvrtBlock $_.Exception.Message; exit 32 }
$remoteProbe = Invoke-QikvrtCapture "git" @("remote","get-url","origin")
if ($remoteProbe.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($remoteProbe.Stdout.Trim())) {
  if ([string]::IsNullOrWhiteSpace($normalized)) { Write-QikvrtBlock "git origin missing; provide GitHub repository URL or OWNER/REPO in the wrapper prompt or set QIKVRT_GITHUB_REMOTE_URL"; exit 30 }
  & git remote add origin $normalized
  if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "git remote add origin failed"; exit 1 }
  Write-QikvrtPass "git origin added: $normalized"
} else { Write-QikvrtPass ("git origin present: " + $remoteProbe.Stdout.Trim()) }
$remoteExists = Test-QikvrtRemoteBranchExists -RemoteName "origin" -Branch $TargetBranch
if ($remoteExists) {
  Write-QikvrtContinue "origin/$TargetBranch exists; using remote branch as canonical base before freeze overlay commit"
  $overlayPath = Join-Path $env:TEMP ("qikvrt_v45_12_overlay_" + [guid]::NewGuid().ToString("N"))
  try {
    Copy-QikvrtWorktreeOverlayToTemp -RepoPath $repoPath -OverlayPath $overlayPath
    & git fetch origin $TargetBranch
    if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "git fetch origin $TargetBranch failed before overlay checkout"; exit 1 }
    Clear-QikvrtWorktreeExceptGit -RepoPath $repoPath
    & git checkout -B $TargetBranch ("origin/" + $TargetBranch)
    if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "git checkout remote base origin/$TargetBranch failed"; exit 1 }
    Restore-QikvrtWorktreeOverlayFromTemp -OverlayPath $overlayPath -RepoPath $repoPath
    Write-QikvrtPass "QIKVRT V45.12 freeze overlay restored on top of origin/$TargetBranch"
  } finally { if (Test-Path -LiteralPath $overlayPath) { Remove-Item -LiteralPath $overlayPath -Recurse -Force } }
} else {
  Write-QikvrtContinue "origin/$TargetBranch not found; creating local target branch for first push"
  & git checkout -B $TargetBranch
  if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "git checkout -B $TargetBranch failed"; exit 1 }
}
try { Ensure-QikvrtLocalGitIdentity -GitUserName $GitUserName -GitUserEmail $GitUserEmail } catch { Write-QikvrtBlock $_.Exception.Message; exit 32 }
& git add -A
if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "git add -A failed during bootstrap"; exit 1 }
$headProbe = Invoke-QikvrtCapture "git" @("rev-parse","--verify","HEAD")
$status = (& git status --porcelain)
if ($headProbe.ExitCode -ne 0) { & git commit -m $CommitMessage; if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "initial git commit failed after repository-local identity bootstrap"; exit 1 }; Write-QikvrtPass "initial local Git commit created" }
elseif ($status) { & git commit -m $CommitMessage; if ($LASTEXITCODE -ne 0) { Write-QikvrtBlock "remote-based freeze overlay commit failed after repository-local identity bootstrap"; exit 1 }; Write-QikvrtPass "remote-based QIKVRT V45.12 freeze overlay commit created" }
else { Write-QikvrtPass "local Git working tree already clean after remote base overlay" }
if ($remoteExists) {
  $remoteRef = "origin/$TargetBranch"
  if (Test-QikvrtRemoteIsAncestorOfHead -RemoteRef $remoteRef) { Write-QikvrtPass "$remoteRef is ancestor of HEAD; push can be fast-forward" }
  else { Write-QikvrtBlock "$remoteRef is not ancestor of HEAD after overlay bootstrap; refusing divergent push"; exit 41 }
}
$currentSha = (& git rev-parse HEAD).Trim()
Write-QikvrtPass "git bootstrap complete at $currentSha"
exit 0
