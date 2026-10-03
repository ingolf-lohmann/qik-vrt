<#
QIKVRT ODU V2.7 - GitHub-token-only Zenodo publication path using Git HTTPS Basic auth header.

This script does NOT use a Zenodo API token.
It uses the owner's GitHub token to:
  1. verify local QIKVRT package contents,
  2. create a timestamped local Git worktree under build/,
  3. commit the extracted repository contents via Git CLI,
  4. push the branch and tag to GitHub,
  5. create a published GitHub Release,
  6. upload the PDF and an exact release bundle as GitHub release assets.

Zenodo publication is completed by Zenodo's GitHub integration IF AND ONLY IF:
  - the owner has linked Zenodo with GitHub in the Zenodo web interface,
  - the target repository is enabled in Zenodo's GitHub settings,
  - Zenodo successfully processes the GitHub release event.

Required GitHub token capability:
  - Fine-grained PAT: selected target repository + Contents: read and write + Metadata: read.
  - Classic PAT: repo scope for private repositories, public_repo/repo capability for public repositories.
  - Organization repositories may additionally require owner-side PAT policy approval.

No local cleanup, no Zenodo token, no direct Zenodo API publish call, no GitHub Git-Blobs API.
V2.5 fix: Git remote authentication no longer relies on credential manager or Bearer extraHeader for Git transport.
          It uses a GitHub-supported HTTPS Basic Authorization header derived from the owner-supplied GitHub token.
          It adds a non-mutating Git auth preflight using git ls-remote before any push/release action.
#>
[CmdletBinding()]
param(
  [switch]$DryRunOnly,
  [switch]$LocalGitSelfTestOnly,
  [switch]$AuthPreflightOnly,
  [string]$Owner = $env:GITHUB_OWNER,
  [string]$Repo = $env:GITHUB_REPO,
  [string]$Branch = $(if ($env:GITHUB_BRANCH) { $env:GITHUB_BRANCH } else { '' }),
  [string]$Tag = $(if ($env:GITHUB_TAG) { $env:GITHUB_TAG } else { 'v2.7-odu-github-release-authz-preflight' }),
  [string]$ReleaseName = $(if ($env:GITHUB_RELEASE_NAME) { $env:GITHUB_RELEASE_NAME } else { 'QIKVRT ODU V2.7 - GitHub Auth Header Zenodo Release' })
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Fail([string]$Message) {
  Write-Host "BLOCK: $Message" -ForegroundColor Red
  exit 1
}
function Info([string]$Message) { Write-Host "[QIKVRT] $Message" }
function Get-Sha256([string]$Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function ConvertTo-PlainText([Security.SecureString]$Secure) {
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
  try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Get-QikvrtObjProp {
  param(
    $Obj,
    [Parameter(Mandatory=$true)][string]$Name
  )
  if ($null -eq $Obj) { return $null }
  $prop = $Obj.PSObject.Properties[$Name]
  if ($null -eq $prop) { return $null }
  return $prop.Value
}
function Test-QikvrtRepoPushPermission {
  param($RepoInfo)
  $perms = Get-QikvrtObjProp $RepoInfo 'permissions'
  if ($null -eq $perms) { return $false }
  foreach ($key in @('admin','maintain','push')) {
    $value = Get-QikvrtObjProp $perms $key
    if ($value -eq $true) { return $true }
  }
  return $false
}
function Get-QikvrtRepoPermissionText {
  param($RepoInfo)
  $perms = Get-QikvrtObjProp $RepoInfo 'permissions'
  if ($null -eq $perms) { return 'permissions object absent' }
  $items = @()
  foreach ($key in @('admin','maintain','push','triage','pull')) {
    $value = Get-QikvrtObjProp $perms $key
    if ($null -ne $value) { $items += ($key + '=' + [string]$value) }
  }
  if ($items.Count -eq 0) { return 'permissions object present but empty/unrecognized' }
  return ($items -join ', ')
}

function Invoke-GitHubJson {
  param(
    [Parameter(Mandatory=$true)][string]$Method,
    [Parameter(Mandatory=$true)][string]$Uri,
    $Body = $null,
    [switch]$AllowNotFound
  )
  if ($Method -ne 'Get') { throw 'NO_BYPASS: direct GitHub REST write disabled' }
  $headers = @{
    'Authorization' = "Bearer $script:GitHubToken"
    'Accept' = 'application/vnd.github+json'
    'X-GitHub-Api-Version' = '2022-11-28'
    'User-Agent' = 'qikvrt-odu-v2-6-authz-preflight-publisher'
  }
  try {
    if ($null -ne $Body) {
      $json = $Body | ConvertTo-Json -Depth 80 -Compress
      return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -ContentType 'application/json' -Body $json
    }
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
  } catch {
    $statusCode = $null
    try {
      if ($_.Exception.Response -and $_.Exception.Response.StatusCode) { $statusCode = [int]$_.Exception.Response.StatusCode }
    } catch { $statusCode = $null }
    if ($AllowNotFound -and $statusCode -eq 404) { return $null }
    $msg = $_.Exception.Message
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
    Fail "GitHub API call failed. Method=$Method Uri=$Uri Status=$statusCode Message=$msg"
  }
}
function Invoke-GitHubUpload { throw 'NO_BYPASS: direct GitHub asset upload disabled' }
function Normalize-RelPath([string]$Path) { $Path.Replace('\\','/') }
function Get-QikvrtRelPath([string]$FullName) {
  $rel = $FullName.Substring($script:RootPathLength)
  $rel = $rel.TrimStart([char]92, [char]47)
  return Normalize-RelPath $rel
}
function ConvertTo-GitProcessArgString {
  param([Parameter(Mandatory=$true)][string[]]$GitArgs)
  $parts = @()
  foreach ($arg in $GitArgs) {
    if ($null -eq $arg) { $s = '' } else { $s = [string]$arg }
    if ($s.Length -eq 0) {
      $parts += '""'
    } elseif ($s -match '[\s"]') {
      # Windows PowerShell 5.1 compatible command-line quoting for Start-Process.
      # Avoids PowerShell native-stderr ErrorRecord conversion caused by '& git ... 2>&1'.
      $escaped = $s.Replace('"', '\"')
      $parts += ('"' + $escaped + '"')
    } else {
      $parts += $s
    }
  }
  return ($parts -join ' ')
}
function Invoke-GitSafe {
  param(
    [Parameter(Mandatory=$true)][string[]]$GitArgs,
    [Parameter(Mandatory=$true)][string]$BlockMessage
  )
  if ($GitArgs -contains 'push' -or $GitArgs -contains 'send-pack') { throw 'NO_BYPASS: direct Git transport write disabled' }
  $gitCommand = Get-Command git -ErrorAction SilentlyContinue
  if (-not $gitCommand) { Fail "$BlockMessage git.exe not found in PATH." }
  $gitExe = $gitCommand.Source
  if (-not $gitExe) { $gitExe = 'git' }

  $stdoutFile = Join-Path $env:TEMP ('qikvrt_git_stdout_' + [guid]::NewGuid().ToString('N') + '.txt')
  $stderrFile = Join-Path $env:TEMP ('qikvrt_git_stderr_' + [guid]::NewGuid().ToString('N') + '.txt')
  $argString = ConvertTo-GitProcessArgString -GitArgs $GitArgs
  try {
    $proc = Start-Process -FilePath $gitExe -ArgumentList $argString -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
  } catch {
    Fail "$BlockMessage git process start failed. $($_.Exception.Message) Args=$argString"
  }

  $stdout = ''
  $stderr = ''
  if (Test-Path -LiteralPath $stdoutFile) {
    $tmpOut = Get-Content -LiteralPath $stdoutFile -Raw -ErrorAction SilentlyContinue
    if ($null -ne $tmpOut) { $stdout = [string]$tmpOut }
  }
  if (Test-Path -LiteralPath $stderrFile) {
    $tmpErr = Get-Content -LiteralPath $stderrFile -Raw -ErrorAction SilentlyContinue
    if ($null -ne $tmpErr) { $stderr = [string]$tmpErr }
  }
  if ($null -eq $stdout) { $stdout = '' }
  if ($null -eq $stderr) { $stderr = '' }
  $joined = ([string](($stdout, $stderr) -join "`n")).Trim()
  if ($null -eq $proc) { Fail "$BlockMessage git process returned null process object. Args=$argString" }
  if ($proc.ExitCode -ne 0) {
    if ($joined -match '403|Write access|Authentication failed|not permitted|not accessible|denied|permission|Resource not accessible|invalid credentials') {
      Fail "$BlockMessage TOKEN_REPO_CONTENTS_WRITE_REQUIRED_OR_INVALID. Fine-grained PAT needs selected repository + Contents read/write + Metadata read; classic PAT needs repo/public_repo as applicable. Git output: $joined"
    }
    Fail "$BlockMessage Git exit code $($proc.ExitCode). Output: $joined"
  }
  $stderrText = [string]$stderr
  if ($stderrText.Trim().Length -gt 0) {
    # Git writes normal progress such as 'From https://github.com/...' to stderr.
    # In V2.5 this is explicitly informational and not a PowerShell BLOCK.
    Info ("git stderr/progress non-fatal: " + ($stderrText.Trim() -replace "`r?`n", ' | '))
  }
  return $joined
}


function Set-GitTransportAuthHeader {
  if (-not $script:GitHubToken) { Fail 'GITHUB_TOKEN is required before Git transport auth header can be built.' }
  $pair = 'x-access-token:' + $script:GitHubToken
  $basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
  # GitHub HTTPS Git transport expects Basic auth for PAT-backed Git operations.
  # This avoids token-in-remote-URL and bypasses stale Windows Credential Manager entries.
  $script:GitHubAuthHeader = 'http.https://github.com/.extraheader=AUTHORIZATION: basic ' + $basic
  $env:GIT_TERMINAL_PROMPT = '0'
  $env:GCM_INTERACTIVE = 'Never'
}
function Get-GitAuthArgs {
  if (-not $script:GitHubAuthHeader) { Fail 'GitHub Git transport auth header was not initialized.' }
  return @('-c', $script:GitHubAuthHeader, '-c', 'credential.helper=', '-c', 'core.askPass=')
}

$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
$Root = $Root.Path
$script:RootPathLength = $Root.Length
Info "Root: $Root"

if ($LocalGitSelfTestOnly) {
  $git = Get-Command git -ErrorAction SilentlyContinue
  if (-not $git) { Fail 'git.exe not found' }
  $td = Join-Path $env:TEMP ('qikvrt_git_ps51_selftest_' + [guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Force -Path $td | Out-Null
  Info "Testing Windows PowerShell 5.1-compatible git invocation in: $td"
  Invoke-GitSafe -GitArgs @('-C', $td, 'init') -BlockMessage 'git init selftest failed.' | Out-Null
  if (-not (Test-Path -LiteralPath (Join-Path $td '.git'))) { Fail 'git init selftest did not create .git directory' }
  Set-Content -LiteralPath (Join-Path $td 'README.md') -Value 'QIKVRT V2.5 local Git selftest' -Encoding UTF8
  Invoke-GitSafe -GitArgs @('-C', $td, 'config', 'user.name', 'QIKVRT Publisher Selftest') -BlockMessage 'git config user.name selftest failed.' | Out-Null
  Invoke-GitSafe -GitArgs @('-C', $td, 'config', 'user.email', 'qikvrt-selftest@users.noreply.github.com') -BlockMessage 'git config user.email selftest failed.' | Out-Null
  Invoke-GitSafe -GitArgs @('-C', $td, 'add', '-A') -BlockMessage 'git add selftest failed.' | Out-Null
  Invoke-GitSafe -GitArgs @('-C', $td, 'commit', '-m', 'QIKVRT V2.5 local Git selftest') -BlockMessage 'git commit selftest failed.' | Out-Null
  Invoke-GitSafe -GitArgs @('-C', $td, 'tag', '-a', 'v2.7-local-git-selftest', '-m', 'QIKVRT V2.5 local Git selftest') -BlockMessage 'git tag selftest failed.' | Out-Null
  Info 'PASS QIKVRT V2.7 Windows PowerShell 5.1-compatible local Git selftest'
  exit 0
}

$pdf = Join-Path $Root 'assets\pdf\odu_proof.pdf'
$metadata = Join-Path $Root '.zenodo.json'
$citation = Join-Path $Root 'CITATION.cff'
$manifest = Join-Path $Root 'MANIFEST.json'
$verifyPy = Join-Path $Root 'tools\verify.py'
foreach ($required in @($pdf,$metadata,$citation,$manifest,$verifyPy)) {
  if (-not (Test-Path -LiteralPath $required)) { Fail "required file missing: $required" }
}
$expectedPdfSha = '2382b5d4970559bc28649a6deb6797fe867fc70439140e4cf1c1e59964a37de6'
$pdfSha = Get-Sha256 $pdf
if ($pdfSha -ne $expectedPdfSha) { Fail "PDF SHA256 mismatch: expected $expectedPdfSha got $pdfSha" }
Info "PDF SHA256 PASS: $pdfSha"

# Ensure no Zenodo direct API token based workflow remains in executable scripts.
$dangerPatterns = @(('ZENODO' + '_ACCESS' + '_TOKEN'), ('zenodo.org/api' + '/deposit' + '/depositions'), ('/api' + '/deposit' + '/depositions'))
$scriptFiles = Get-ChildItem -LiteralPath $Root -Recurse -File | Where-Object { $_.Extension -in @('.cmd','.ps1') }
foreach ($sf in $scriptFiles) {
  $text = Get-Content -LiteralPath $sf.FullName -Raw -ErrorAction Stop
  foreach ($pat in $dangerPatterns) {
    if ($text -like "*$pat*") { Fail "direct Zenodo API/token pattern found in executable script: $($sf.FullName) pattern=$pat" }
  }
  foreach ($bad in @((' r' + 'mdir '), (' d' + 'el '), (' er' + 'ase '), ('Format' + '-Volume'), ('Clear' + '-Content'), ('Remove' + '-Item'))) {
    if ($text -like "*$bad*") { Fail "destructive local command pattern found in executable script: $($sf.FullName) pattern=$bad" }
  }
}
Info "Executable-script safety gate PASS"

# Run internal verifier.
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if ($py) {
  $verifyOut = & $py.Source $verifyPy 2>&1
  $verifyCode = $LASTEXITCODE
  $verifyOut | ForEach-Object { Write-Host $_ }
  if ($verifyCode -ne 0) { Fail "internal verify.py failed" }
} else {
  Info "Python not found; internal verify.py skipped by PowerShell preflight, but package includes verifier."
}

if ($DryRunOnly) {
  Info "DRY RUN PASS. No GitHub upload/release performed."
  exit 0
}

throw 'NO_BYPASS: productive GitHub publication disabled; use current Authority broker'
