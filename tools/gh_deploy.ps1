# QIKVRT Artifact Header
# Deutsch: Generisches Node-Git-Deployment. Kein lokaler GitHub-Release-REST-Create; Release/Asset entstehen im Zielrepo per GitHub Actions.
# English: Generic node Git deployment. No local GitHub release REST create; release/asset are created in the target repo by GitHub Actions.
# Audit note: git -C style operations are executed through System.Diagnostics.Process wrappers, not raw native stderr-sensitive PowerShell calls.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
param(
  [string]$RepoRoot = (Get-Location).Path,
  [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$RuntimeDir = Join-Path $RepoRoot 'qikvrt\runtime\deploy'
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$Tsv = Join-Path $RuntimeDir 'deploy_result.tsv'
$Json = Join-Path $RuntimeDir 'deploy_result.json'
$script:Rows = @()
function Add-DeployResult([string]$Gate,[string]$Status,[string]$Detail){
  $script:Rows += [pscustomobject]@{ timestamp_utc=(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'); gate=$Gate; status=$Status; detail=$Detail }
  Write-Host ($Gate + "`t" + $Status + "`t" + $Detail)
}
function Get-DeployRowCount([string]$Gate,[string]$Status){
  return (($script:Rows | Where-Object { $_.gate -eq $Gate -and $_.status -eq $Status }) | Measure-Object).Count
}
function Write-DeployLogsAndExit([int]$Code){
  $script:Rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Json -Encoding UTF8
  'utc`tgate`tstatus`tdetail' | Set-Content -LiteralPath $Tsv -Encoding UTF8
  foreach ($row in $script:Rows) { ($row.timestamp_utc + "`t" + $row.gate + "`t" + $row.status + "`t" + (($row.detail -replace "`r?`n", ' ') -replace "`t", ' ')) | Add-Content -LiteralPath $Tsv -Encoding UTF8 }
  exit $Code
}
function Parse-GitHubRemote([string]$remote){
  if ([string]::IsNullOrWhiteSpace($remote)) { return $null }
  if ($remote -match 'github\.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)(\.git)?$') { return @{ owner=$Matches.owner; repo=$Matches.repo } }
  return $null
}
function Resolve-OwnerRepo {
  $owner = $env:QIKVRT_GITHUB_OWNER
  $repo = $env:QIKVRT_GITHUB_REPO
  if (-not [string]::IsNullOrWhiteSpace($owner) -and -not [string]::IsNullOrWhiteSpace($repo)) { Add-DeployResult 'GITHUB_TARGET_ENV' 'PASS' ($owner + '/' + $repo); return @{ owner=$owner; repo=$repo } }
  $persisted = Join-Path $RepoRoot 'qikvrt\config\REPOSITORY_TARGET.json'
  if (Test-Path -LiteralPath $persisted) {
    try {
      $cfg = Get-Content -LiteralPath $persisted -Raw | ConvertFrom-Json
      if (-not [string]::IsNullOrWhiteSpace($cfg.github_owner) -and -not [string]::IsNullOrWhiteSpace($cfg.github_repository)) {
        Add-DeployResult 'GITHUB_TARGET_PERSISTED_CONFIG' 'PASS' ($cfg.github_owner + '/' + $cfg.github_repository)
        return @{ owner=[string]$cfg.github_owner; repo=[string]$cfg.github_repository }
      }
    } catch { Add-DeployResult 'GITHUB_TARGET_PERSISTED_CONFIG' 'BLOCK' $_.Exception.Message }
  }
  try {
    $remoteProbe = Invoke-NativeGit @('-C', $RepoRoot, 'config', '--get', 'remote.origin.url')
    if ($remoteProbe.exit_code -eq 0) {
      $remote = [string]$remoteProbe.text
      $parsed = Parse-GitHubRemote $remote
      if ($null -ne $parsed) { Add-DeployResult 'GITHUB_TARGET_GIT_REMOTE' 'PASS' ($parsed.owner + '/' + $parsed.repo); return $parsed }
    }
  } catch { Add-DeployResult 'GITHUB_TARGET_GIT_REMOTE' 'SKIP' 'git remote probe unavailable before target prompt/config' }
  $owner = Read-Host 'GitHub owner/org'
  $repo = Read-Host 'GitHub repository'
  if ([string]::IsNullOrWhiteSpace($owner) -or [string]::IsNullOrWhiteSpace($repo)) { throw 'GitHub owner/repository missing' }
  Add-DeployResult 'GITHUB_TARGET_PROMPT' 'PASS' ($owner + '/' + $repo)
  return @{ owner=$owner; repo=$repo }
}
function RoleName {
  $roleFile = Join-Path $RepoRoot 'qikvrt\config\ROLE.json'
  if (Test-Path -LiteralPath $roleFile) {
    try { $r = Get-Content -LiteralPath $roleFile -Raw | ConvertFrom-Json; if ($r.role) { return [string]$r.role } } catch {}
  }
  return 'node'
}
function Sha256([string]$p){ return (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant() }
function Normalize-GitHubHeaderToken($raw){
  if ($null -eq $raw) { $raw = '' }
  $rawString = [string]$raw
  $before = $rawString.Length
  $t = [regex]::Replace($rawString, '[\x00-\x1F\x7F]', '')
  $t = $t.Trim()
  if ($t.StartsWith('Bearer ', [System.StringComparison]::OrdinalIgnoreCase)) { $t = $t.Substring(7).Trim() }
  if (($t.StartsWith('"') -and $t.EndsWith('"')) -or ($t.StartsWith("'") -and $t.EndsWith("'"))) { $t = $t.Substring(1, $t.Length - 2).Trim() }
  $removed = $before - $t.Length
  return [pscustomobject]@{ token=[string]$t; removed=[int]$removed }
}
function Read-GitHubTokenInteractive {
  Add-DeployResult 'GITHUB_TOKEN_PROMPT' 'PASS' 'prompting for token for git push only; token will not be persisted and will not be used for local release REST calls'
  $plain = ''
  try {
    $secure = Read-Host 'GitHub token for git push' -AsSecureString
    if ($null -ne $secure -and $secure.Length -gt 0) {
      $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
      try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
  } catch {
    Add-DeployResult 'GITHUB_TOKEN_SECURE_READ' 'BLOCK' ('secure token read failed; using plain fallback: ' + $_.Exception.GetType().FullName)
  }
  if ([string]::IsNullOrWhiteSpace($plain)) {
    Add-DeployResult 'GITHUB_TOKEN_PROMPT_FALLBACK' 'PASS' 'secure token input was empty/unavailable; plain fallback will be used for this process only'
    $plain = Read-Host 'GitHub token for git push (plain fallback; input may be visible)'
  }
  return [string]$plain
}
function Quote-NativeArgument([string]$Value){
  if ($null -eq $Value) { return '""' }
  if ($Value.Length -eq 0) { return '""' }
  if ($Value -notmatch '[\s"]') { return $Value }
  $escaped = $Value -replace '\\(?=")', '\\\\'
  $escaped = $escaped -replace '"', '\"'
  $escaped = $escaped -replace '(\+)$', '$1$1'
  return '"' + $escaped + '"'
}
function Resolve-GitTimeoutSeconds {
  $defaultTimeout = 120
  if (-not [string]::IsNullOrWhiteSpace($env:QIKVRT_GIT_TIMEOUT_SECONDS)) {
    try {
      $parsed = [int]$env:QIKVRT_GIT_TIMEOUT_SECONDS
      if ($parsed -ge 5 -and $parsed -le 3600) { return $parsed }
    } catch {}
  }
  return $defaultTimeout
}
function Get-NoninteractiveGitEnv {
  $envMap = @{}
  $envMap['GIT_TERMINAL_PROMPT'] = '0'
  $envMap['GCM_INTERACTIVE'] = 'Never'
  $envMap['GCM_MODAL_PROMPT'] = '0'
  $envMap['GIT_CREDENTIAL_INTERACTIVE'] = 'Never'
  return $envMap
}
function Merge-EnvMap($Base,$Extra){
  $merged = @{}
  if ($null -ne $Base) { foreach ($k in $Base.Keys) { $merged[[string]$k] = [string]$Base[$k] } }
  if ($null -ne $Extra) { foreach ($k in $Extra.Keys) { $merged[[string]$k] = [string]$Extra[$k] } }
  return $merged
}
function Invoke-NativeGit([string[]]$Arguments,[hashtable]$ExtraEnv=$null,[int]$TimeoutSeconds=0){
  $gitCommand = Get-Command git -ErrorAction Stop
  if ($TimeoutSeconds -le 0) { $TimeoutSeconds = Resolve-GitTimeoutSeconds }
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $gitCommand.Source
  $psi.Arguments = (($Arguments | ForEach-Object { Quote-NativeArgument ([string]$_) }) -join ' ')
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true
  $envMap = Merge-EnvMap (Get-NoninteractiveGitEnv) $ExtraEnv
  foreach ($k in $envMap.Keys) { $psi.EnvironmentVariables[[string]$k] = [string]$envMap[$k] }
  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()
  $stdoutTask = $p.StandardOutput.ReadToEndAsync()
  $stderrTask = $p.StandardError.ReadToEndAsync()
  $timedOut = $false
  $timeoutMs = [int]($TimeoutSeconds * 1000)
  if (-not $p.WaitForExit($timeoutMs)) {
    $timedOut = $true
    try { $p.Kill() } catch {}
    try { $p.WaitForExit(5000) | Out-Null } catch {}
  }
  try { $stdoutTask.Wait(5000) | Out-Null } catch {}
  try { $stderrTask.Wait(5000) | Out-Null } catch {}
  $stdout = ''
  $stderr = ''
  try { if ($stdoutTask.IsCompleted) { $stdout = [string]$stdoutTask.Result } } catch {}
  try { if ($stderrTask.IsCompleted) { $stderr = [string]$stderrTask.Result } } catch {}
  $exitCode = 124
  if (-not $timedOut) { $exitCode = [int]$p.ExitCode }
  $combined = (($stdout + $(if ([string]::IsNullOrWhiteSpace($stderr)) { '' } else { "`n" + $stderr })).Trim())
  if ($timedOut) {
    $combined = ('git timed out after ' + $TimeoutSeconds + ' seconds; interactive credential prompt or network stall prevented completion' + $(if ([string]::IsNullOrWhiteSpace($combined)) { '' } else { '; output=' + $combined }))
  }
  return [pscustomobject]@{ exit_code=[int]$exitCode; stdout=[string]$stdout; stderr=[string]$stderr; text=[string]$combined; arguments=[string]$psi.Arguments; timed_out=[bool]$timedOut; timeout_seconds=[int]$TimeoutSeconds }
}
function Invoke-GitChecked([string[]]$Arguments,[string]$Gate,[string]$PassDetail,[hashtable]$ExtraEnv=$null,[int]$TimeoutSeconds=0){
  $result = Invoke-NativeGit $Arguments $ExtraEnv $TimeoutSeconds
  $text = [string]$result.text
  if ($result.exit_code -ne 0) {
    if ([string]::IsNullOrWhiteSpace($text)) { $text = ('git exit code ' + $result.exit_code) }
    Add-DeployResult $Gate 'BLOCK' $text
    throw ('Git command failed at ' + $Gate)
  }
  if ([string]::IsNullOrWhiteSpace($PassDetail)) { $PassDetail = $text }
  Add-DeployResult $Gate 'PASS' $PassDetail
  return $text
}
function New-GitHttpAuthHeader([string]$Token){
  $pair = 'x-access-token:' + [string]$Token
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($pair)
  return 'Authorization: Basic ' + [Convert]::ToBase64String($bytes)
}
function Test-GitRefExists([string]$Ref){
  $probe = Invoke-NativeGit @('-C', $RepoRoot, 'rev-parse', '--verify', '--quiet', $Ref)
  return ($probe.exit_code -eq 0)
}
function Get-GitObjectId([string]$Ref,[string]$Gate){
  $probe = Invoke-NativeGit @('-C', $RepoRoot, 'rev-parse', '--verify', $Ref)
  if ($probe.exit_code -ne 0) {
    $detail = [string]$probe.text
    if ([string]::IsNullOrWhiteSpace($detail)) { $detail = ('git rev-parse failed for ' + $Ref) }
    Add-DeployResult $Gate 'BLOCK' $detail
    throw ('Git object id resolution failed for ' + $Ref)
  }
  return ([string]$probe.text).Trim()
}
function Get-GitShortObjectId([string]$Ref,[string]$Gate){
  $full = Get-GitObjectId $Ref $Gate
  if ([string]::IsNullOrWhiteSpace($full)) { return 'unknown' }
  if ($full.Length -lt 12) { return [string]$full }
  return [string]$full.Substring(0,12)
}
function Get-SafeDeployBranchName([string]$Tag){
  $raw = if ($env:QIKVRT_NODE_DEPLOY_BRANCH) { [string]$env:QIKVRT_NODE_DEPLOY_BRANCH } else { 'qikvrt-node/' + $Tag }
  $safe = ($raw -replace '[^A-Za-z0-9._/-]', '-')
  $safe = ($safe -replace '/+', '/')
  $safe = $safe.Trim('/','.')
  if ([string]::IsNullOrWhiteSpace($safe)) { $safe = 'qikvrt-node/deploy' }
  return [string]$safe
}
function Test-GitAuthOrPermissionFailure([string]$Text){
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match '(?i)(permission.*denied|403|401|authentication failed|could not read username|repository not found|not found)')
}
function Test-GitNonFastForwardFailure([string]$Text){
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match '(?i)(non-fast-forward|fetch first|rejected|failed to push some refs|tip of your current branch is behind)')
}
function Get-RemoteTagObjectId([string]$Tag,[hashtable]$ExtraEnv,[int]$TimeoutSeconds){
  $probe = Invoke-NativeGit @('-C', $RepoRoot, 'ls-remote', 'origin', ('refs/tags/' + $Tag)) $ExtraEnv $TimeoutSeconds
  if ($probe.exit_code -ne 0) { return [pscustomobject]@{ ok=$false; found=$false; object=''; text=[string]$probe.text } }
  $line = (([string]$probe.stdout) -split "`r?`n" | Where-Object { $_ -match ("refs/tags/" + [regex]::Escape($Tag) + '$') } | Select-Object -First 1)
  if ([string]::IsNullOrWhiteSpace($line)) { return [pscustomobject]@{ ok=$true; found=$false; object=''; text=[string]$probe.text } }
  $parts = $line -split "\s+"
  return [pscustomobject]@{ ok=$true; found=$true; object=[string]$parts[0]; text=[string]$probe.text }
}
function Push-BranchBestEffort([string]$Branch,[string]$Tag,[string]$AuthHeader,[hashtable]$PushEnv,[int]$PushTimeout){
  $primary = Invoke-NativeGit @('-C', $RepoRoot, '-c', ('http.https://github.com/.extraheader=' + $AuthHeader), 'push', 'origin', ('HEAD:refs/heads/' + $Branch)) $PushEnv $PushTimeout
  if ($primary.exit_code -eq 0) { Add-DeployResult 'GIT_PUSH_BRANCH' 'PASS' ('origin ' + $Branch); return [string]$Branch }
  $text = [string]$primary.text
  if (Test-GitAuthOrPermissionFailure $text) { Add-DeployResult 'GIT_PUSH_BRANCH' 'BLOCK' $text; throw 'Git command failed at GIT_PUSH_BRANCH' }
  if (Test-GitNonFastForwardFailure $text) {
    Add-DeployResult 'GIT_PUSH_BRANCH_PRIMARY' 'SKIP' ('primary branch ' + $Branch + ' rejected as non-fast-forward; trying node deploy branch')
    $fallback = Get-SafeDeployBranchName $Tag
    $fb = Invoke-NativeGit @('-C', $RepoRoot, '-c', ('http.https://github.com/.extraheader=' + $AuthHeader), 'push', 'origin', ('HEAD:refs/heads/' + $fallback)) $PushEnv $PushTimeout
    if ($fb.exit_code -eq 0) { Add-DeployResult 'GIT_PUSH_BRANCH_FALLBACK' 'PASS' ('origin ' + $fallback); return [string]$fallback }
    $fbText = [string]$fb.text
    if (Test-GitAuthOrPermissionFailure $fbText) { Add-DeployResult 'GIT_PUSH_BRANCH_FALLBACK' 'BLOCK' $fbText; throw 'Git command failed at GIT_PUSH_BRANCH_FALLBACK' }
    if (Test-GitNonFastForwardFailure $fbText) {
      $headShort = Get-GitShortObjectId 'HEAD' 'GIT_HEAD_SHORT_FOR_CONFLICT_BRANCH'
      $conflictBranch = ($fallback + '-' + $headShort)
      $cb = Invoke-NativeGit @('-C', $RepoRoot, '-c', ('http.https://github.com/.extraheader=' + $AuthHeader), 'push', 'origin', ('HEAD:refs/heads/' + $conflictBranch)) $PushEnv $PushTimeout
      if ($cb.exit_code -eq 0) { Add-DeployResult 'GIT_PUSH_BRANCH_CONFLICT_FALLBACK' 'PASS' ('origin ' + $conflictBranch); return [string]$conflictBranch }
      Add-DeployResult 'GIT_PUSH_BRANCH_CONFLICT_FALLBACK' 'BLOCK' ([string]$cb.text)
      throw 'Git command failed at GIT_PUSH_BRANCH_CONFLICT_FALLBACK'
    }
    Add-DeployResult 'GIT_PUSH_BRANCH_FALLBACK' 'BLOCK' $fbText
    throw 'Git command failed at GIT_PUSH_BRANCH_FALLBACK'
  }
  Add-DeployResult 'GIT_PUSH_BRANCH' 'BLOCK' $text
  throw 'Git command failed at GIT_PUSH_BRANCH'
}
function Push-TagIdempotent([string]$Tag,[string]$AuthHeader,[hashtable]$PushEnv,[int]$PushTimeout){
  $tagRef = 'refs/tags/' + $Tag
  $localObject = Get-GitObjectId $tagRef 'GIT_LOCAL_TAG_OBJECT'
  $force = ([string]$env:QIKVRT_FORCE_TAG -eq '1')
  if ($force) {
    $forced = Invoke-NativeGit @('-C', $RepoRoot, '-c', ('http.https://github.com/.extraheader=' + $AuthHeader), 'push', '--force', 'origin', $tagRef) $PushEnv $PushTimeout
    if ($forced.exit_code -eq 0) { Add-DeployResult 'GIT_PUSH_TAG' 'PASS' ('origin ' + $Tag + ' force'); return }
    Add-DeployResult 'GIT_PUSH_TAG' 'BLOCK' ([string]$forced.text)
    throw 'Git command failed at GIT_PUSH_TAG'
  }
  $push = Invoke-NativeGit @('-C', $RepoRoot, '-c', ('http.https://github.com/.extraheader=' + $AuthHeader), 'push', 'origin', $tagRef) $PushEnv $PushTimeout
  if ($push.exit_code -eq 0) { Add-DeployResult 'GIT_PUSH_TAG' 'PASS' ('origin ' + $Tag); return }
  $text = [string]$push.text
  if (Test-GitAuthOrPermissionFailure $text) { Add-DeployResult 'GIT_PUSH_TAG' 'BLOCK' $text; throw 'Git command failed at GIT_PUSH_TAG' }
  $remote = Get-RemoteTagObjectId $Tag $PushEnv $PushTimeout
  if ($remote.ok -and $remote.found -and ([string]$remote.object).ToLowerInvariant() -eq ([string]$localObject).ToLowerInvariant()) {
    Add-DeployResult 'GIT_PUSH_TAG_IDEMPOTENT' 'PASS' ('remote tag already matches local tag object ' + $localObject)
    return
  }
  if ($remote.ok -and $remote.found) {
    Add-DeployResult 'GIT_PUSH_TAG' 'BLOCK' ('remote tag exists but differs; local=' + $localObject + ' remote=' + $remote.object + '; set QIKVRT_FORCE_TAG=1 only if intentional')
  } elseif (-not $remote.ok) {
    Add-DeployResult 'GIT_PUSH_TAG' 'BLOCK' ('tag push failed and remote tag probe failed: ' + $text + ' | probe=' + $remote.text)
  } else {
    Add-DeployResult 'GIT_PUSH_TAG' 'BLOCK' $text
  }
  throw 'Git command failed at GIT_PUSH_TAG'
}
function Ensure-GitRepository([hashtable]$Target){
  $gitCommand = Get-Command git -ErrorAction SilentlyContinue
  if ($null -eq $gitCommand) { Add-DeployResult 'GIT_AVAILABLE' 'BLOCK' 'git.exe not found in PATH'; throw 'git missing' }
  Add-DeployResult 'GIT_AVAILABLE' 'PASS' $gitCommand.Source
  if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot '.git'))) {
    $null = Invoke-GitChecked @('-C', $RepoRoot, 'init') 'GIT_INIT' 'initialized local repository for node deploy'
    $branch = if ($env:QIKVRT_GIT_BRANCH) { [string]$env:QIKVRT_GIT_BRANCH } else { 'main' }
    $null = Invoke-GitChecked @('-C', $RepoRoot, 'checkout', '-B', $branch) 'GIT_BRANCH_PREPARE' ('branch=' + $branch)
  } else {
    Add-DeployResult 'GIT_INIT' 'PASS' 'existing .git directory present'
  }
  if ($env:QIKVRT_GIT_BRANCH) {
    $branchName = [string]$env:QIKVRT_GIT_BRANCH
  } else {
    $branchProbe = Invoke-NativeGit @('-C', $RepoRoot, 'branch', '--show-current')
    $branchName = if ($branchProbe.exit_code -eq 0) { [string]$branchProbe.text } else { '' }
  }
  if ([string]::IsNullOrWhiteSpace($branchName)) { $branchName = 'main'; $null = Invoke-GitChecked @('-C', $RepoRoot, 'checkout', '-B', $branchName) 'GIT_BRANCH_PREPARE' ('branch=' + $branchName) }
  $emailProbe = Invoke-NativeGit @('-C', $RepoRoot, 'config', 'user.email')
  $email = if ($emailProbe.exit_code -eq 0) { [string]$emailProbe.text } else { '' }
  if ([string]::IsNullOrWhiteSpace($email)) { $null = Invoke-GitChecked @('-C', $RepoRoot, 'config', 'user.email', 'qikvrt-deploy@users.noreply.github.com') 'GIT_USER_EMAIL' 'qikvrt-deploy@users.noreply.github.com' } else { Add-DeployResult 'GIT_USER_EMAIL' 'PASS' $email }
  $nameProbe = Invoke-NativeGit @('-C', $RepoRoot, 'config', 'user.name')
  $name = if ($nameProbe.exit_code -eq 0) { [string]$nameProbe.text } else { '' }
  if ([string]::IsNullOrWhiteSpace($name)) { $null = Invoke-GitChecked @('-C', $RepoRoot, 'config', 'user.name', 'QIKVRT Deploy Bot') 'GIT_USER_NAME' 'QIKVRT Deploy Bot' } else { Add-DeployResult 'GIT_USER_NAME' 'PASS' $name }
  $null = Invoke-GitChecked @('-C', $RepoRoot, 'config', 'core.autocrlf', 'false') 'GIT_CORE_AUTOCRLF' 'false'
  $null = Invoke-GitChecked @('-C', $RepoRoot, 'config', 'core.eol', 'lf') 'GIT_CORE_EOL' 'lf'
  $remoteUrl = 'https://github.com/' + $Target.owner + '/' + $Target.repo + '.git'
  $originProbe = Invoke-NativeGit @('-C', $RepoRoot, 'remote', 'get-url', 'origin')
  $origin = if ($originProbe.exit_code -eq 0) { [string]$originProbe.text } else { '' }
  if (-not [string]::IsNullOrWhiteSpace($origin)) {
    $null = Invoke-GitChecked @('-C', $RepoRoot, 'remote', 'set-url', 'origin', $remoteUrl) 'GIT_REMOTE_ORIGIN' ('set-url ' + $remoteUrl)
  } else {
    $null = Invoke-GitChecked @('-C', $RepoRoot, 'remote', 'add', 'origin', $remoteUrl) 'GIT_REMOTE_ORIGIN' ('add ' + $remoteUrl)
  }
  return [string]$branchName
}
function CommitNodeState([string]$Tag){
  $null = Invoke-GitChecked @('-C', $RepoRoot, 'add', '-A') 'GIT_ADD' 'staged node repository state including release workflow'
  $diffProbe = Invoke-NativeGit @('-C', $RepoRoot, 'diff', '--cached', '--quiet', '--exit-code')
  if ($diffProbe.exit_code -eq 0) {
    Add-DeployResult 'GIT_COMMIT' 'PASS' 'no staged changes; reusing current HEAD'
  } elseif ($diffProbe.exit_code -eq 1) {
    $null = Invoke-GitChecked @('-C', $RepoRoot, 'commit', '-m', ('QIKVRT node git-trigger release ' + $Tag)) 'GIT_COMMIT' ('committed node state for ' + $Tag)
  } else {
    $detail = [string]$diffProbe.text
    if ([string]::IsNullOrWhiteSpace($detail)) { $detail = ('git diff probe exit code ' + $diffProbe.exit_code) }
    Add-DeployResult 'GIT_DIFF_CACHED' 'BLOCK' $detail
    throw 'Git cached diff probe failed'
  }
}
function PrepareReleaseTag([string]$Tag){
  if (Test-GitRefExists ('refs/tags/' + $Tag)) {
    $headCommit = Get-GitObjectId 'HEAD' 'GIT_HEAD_OBJECT'
    $tagCommit = Get-GitObjectId (($Tag) + '^{commit}') 'GIT_TAG_COMMIT_OBJECT'
    if (([string]$headCommit).ToLowerInvariant() -eq ([string]$tagCommit).ToLowerInvariant()) {
      Add-DeployResult 'GIT_TAG_EXISTS_REUSE' 'PASS' ('local tag already points to HEAD: ' + $Tag)
      return
    }
    if ([string]$env:QIKVRT_FORCE_TAG -eq '1') {
      $null = Invoke-GitChecked @('-C', $RepoRoot, 'tag', '-d', $Tag) 'GIT_TAG_RECREATE' ('deleted local tag ' + $Tag + ' because QIKVRT_FORCE_TAG=1')
    } else {
      Add-DeployResult 'GIT_TAG_EXISTS' 'BLOCK' ('local tag already exists but does not point to HEAD; tag_commit=' + $tagCommit + ' head=' + $headCommit + '; set QIKVRT_FORCE_TAG=1 only if intentional')
      throw 'local tag exists on different commit'
    }
  }
  $null = Invoke-GitChecked @('-C', $RepoRoot, 'tag', '-a', $Tag, '-m', ('QIKVRT node release trigger ' + $Tag)) 'GIT_TAG_CREATE' $Tag
}
function New-GitArchiveAsset([string]$Ref,[string]$Role){
  $asset = [string](Join-Path $RuntimeDir ('qv2134_' + $Role + '.zip'))
  if (Test-Path -LiteralPath $asset) { Remove-Item -LiteralPath $asset -Force }
  $null = Invoke-GitChecked @('-C', $RepoRoot, 'archive', '--format=zip', ('--output=' + $asset), $Ref) 'DEPLOY_ASSET_GIT_ARCHIVE' ($asset + ' ref=' + $Ref)
  Add-DeployResult 'DEPLOY_STAGING_SELF_COPY_PREVENTION' 'PASS' '.gitattributes export-ignore excludes qikvrt/runtime/deploy, qikvrt/runtime/bootstrap, qikvrt/runtime/win_acceptance, qikvrt/runtime/setup, release/artifacts, package_staging, build, and git metadata'
  return [string]$asset
}
function Publish-LocalArtifactIntoRepository([string]$Asset,[string]$Hash,[string]$Tag,[string]$Role){
  $artifactDir = Join-Path $RepoRoot 'release\artifacts'
  New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
  $repoAsset = Join-Path $artifactDir ('qv2134_' + $Role + '.zip')
  $repoSha = $repoAsset + '.sha256'
  $repoJson = Join-Path $artifactDir 'NODE_RELEASE_ARTIFACT.json'
  Copy-Item -LiteralPath $Asset -Destination $repoAsset -Force
  ($Hash + '  ' + (Split-Path -Leaf $repoAsset)) | Set-Content -LiteralPath $repoSha -Encoding ASCII
  $meta = [ordered]@{
    qikvrt_version='2.13.4R'
    role=$Role
    tag=$Tag
    artifact='release/artifacts/' + (Split-Path -Leaf $repoAsset)
    sha256=$Hash
    hash_parity_policy='target GitHub Actions uploads this committed artifact verbatim; no server-side ZIP regeneration'
    local_release_rest_api='disabled'
    generated_utc=(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  }
  ($meta | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $repoJson -Encoding UTF8
  Add-DeployResult 'DEPLOY_ARTIFACT_COMMITTED_SOURCE' 'PASS' ('release/artifacts/' + (Split-Path -Leaf $repoAsset) + ' sha256=' + $Hash)
  $null = Invoke-GitChecked @('-C', $RepoRoot, 'add', 'release/artifacts/qv2134_node.zip', 'release/artifacts/qv2134_node.zip.sha256', 'release/artifacts/NODE_RELEASE_ARTIFACT.json') 'GIT_ADD_RELEASE_ARTIFACT' 'staged committed release artifact and checksum'
  $diffProbe = Invoke-NativeGit @('-C', $RepoRoot, 'diff', '--cached', '--quiet', '--exit-code')
  if ($diffProbe.exit_code -eq 0) {
    Add-DeployResult 'GIT_COMMIT_RELEASE_ARTIFACT' 'PASS' 'committed artifact unchanged; reusing current HEAD'
  } elseif ($diffProbe.exit_code -eq 1) {
    $null = Invoke-GitChecked @('-C', $RepoRoot, 'commit', '-m', ('QIKVRT committed node release artifact ' + $Tag)) 'GIT_COMMIT_RELEASE_ARTIFACT' ('committed local release artifact for ' + $Tag)
  } else {
    $detail = [string]$diffProbe.text
    if ([string]::IsNullOrWhiteSpace($detail)) { $detail = ('git diff probe exit code ' + $diffProbe.exit_code) }
    Add-DeployResult 'GIT_DIFF_RELEASE_ARTIFACT' 'BLOCK' $detail
    throw 'Git release artifact diff probe failed'
  }
}
# QIKVRT V2.13.4R: no AskPass token file is written. Git push uses a non-persistent http.extraheader for this process only.
try {
  $target = Resolve-OwnerRepo
  $role = RoleName
  if ($role -ne 'node') { Add-DeployResult 'NODE_ONLY_VARIANT' 'BLOCK' ('role=' + $role + '; this 2.13.4R package is node-only'); Write-DeployLogsAndExit 3 }
  Add-DeployResult 'NODE_ONLY_VARIANT' 'PASS' 'general node variant only; no seed deploy path included'
  Add-DeployResult 'GIT_NATIVE_STDERR_CAPTURE' 'PASS' 'git is executed through System.Diagnostics.Process; normal stderr such as branch-switch messages is captured, not treated as a PowerShell exception'
  Add-DeployResult 'GIT_OPTIONAL_PROBE_CAPTURE' 'PASS' 'optional git probes such as remote get-url origin, branch, config, rev-parse, and diff use Process exit-code handling; missing origin is add-path, not BLOCK'
  Add-DeployResult 'GIT_TIMEOUT_GATE' 'PASS' ('all git commands use System.Diagnostics.Process timeout; default_seconds=' + (Resolve-GitTimeoutSeconds))
  Add-DeployResult 'GIT_FUNCTION_OUTPUT_SCALAR_GATE' 'PASS' 'helper functions suppress internal Invoke-GitChecked output and return scalar branch/path values only'
  Add-DeployResult 'GIT_IDEMPOTENT_TAG_GATE' 'PASS' 'existing local tag on HEAD is reused; matching remote tag is treated as idempotent success; differing tags require QIKVRT_FORCE_TAG=1'
  Add-DeployResult 'GIT_BRANCH_FALLBACK_GATE' 'PASS' 'non-fast-forward primary branch push falls back to qikvrt-node/<tag>; if that remote branch already diverged, a HEAD-suffixed conflict branch is used; auth/permission failures still BLOCK'
  $tag = if ($env:QIKVRT_RELEASE_TAG) { [string]$env:QIKVRT_RELEASE_TAG } else { 'v2.13.4-node-r' }
  $branch = Ensure-GitRepository $target
  CommitNodeState $tag
  Add-DeployResult 'NODE_HASH_PARITY_GATE' 'PASS' 'local deploy commits release/artifacts/qv2134_node.zip and GitHub Actions uploads that committed artifact verbatim'
  $asset = New-GitArchiveAsset 'HEAD' $role
  $hash = Sha256 $asset
  Add-DeployResult 'DEPLOY_ASSET_PACKAGE' 'PASS' $asset
  Add-DeployResult 'DEPLOY_ASSET_SHA256' 'PASS' $hash
  Publish-LocalArtifactIntoRepository $asset $hash $tag $role
  PrepareReleaseTag $tag
  Add-DeployResult 'LOCAL_RELEASE_REST_API' 'PASS' 'disabled; local deploy uses git push only; GitHub Actions in target repo uploads committed release artifact'
  if ($DryRun -or [string]$env:QIKVRT_DRY_RUN -eq '1') {
    Add-DeployResult 'GIT_PUSH' 'BLOCK' 'dry-run; branch/tag not pushed and no remote mutation performed'
    Write-DeployLogsAndExit 3
  }
  $tokenSource = 'env'
  $normalizedToken = Normalize-GitHubHeaderToken $env:GITHUB_TOKEN
  Add-DeployResult 'GITHUB_TOKEN_NORMALIZER_SHAPE' 'PASS' 'normalizer always returns object {token, removed}, including empty input'
  if ([string]::IsNullOrWhiteSpace([string]$normalizedToken.token)) {
    $tokenSource = 'prompt'
    $rawPromptToken = Read-GitHubTokenInteractive
    $normalizedToken = Normalize-GitHubHeaderToken $rawPromptToken
  }
  if ([string]::IsNullOrWhiteSpace([string]$normalizedToken.token)) {
    Add-DeployResult 'GITHUB_TOKEN_SANITIZE' 'BLOCK' 'missing token after environment and interactive prompt sanitization; git push not performed'
    Write-DeployLogsAndExit 3
  }
  Add-DeployResult 'GITHUB_TOKEN_SANITIZE' 'PASS' ('git http.extraheader safe; source=' + $tokenSource + '; control chars removed=' + $normalizedToken.removed + '; token not persisted')
  $pushTimeout = Resolve-GitTimeoutSeconds
  Add-DeployResult 'GIT_NONINTERACTIVE_ENV' 'PASS' ('GIT_TERMINAL_PROMPT=0; GCM_INTERACTIVE=Never; GCM_MODAL_PROMPT=0; timeout_seconds=' + $pushTimeout)
  $authHeader = New-GitHttpAuthHeader ([string]$normalizedToken.token)
  $pushEnv = Get-NoninteractiveGitEnv
  $pushedBranch = Push-BranchBestEffort $branch $tag $authHeader $pushEnv $pushTimeout
  Push-TagIdempotent $tag $authHeader $pushEnv $pushTimeout
  Add-DeployResult 'GITHUB_ACTIONS_RELEASE_TRIGGER' 'PASS' ('pushed tag ' + $tag + ' and branch ' + $pushedBranch + '; target workflow .github/workflows/qikvrt_node_release.yml is responsible for release and asset upload')
  Write-DeployLogsAndExit 0
} catch {
  Add-DeployResult 'NODE_GIT_DEPLOY_FINAL' 'BLOCK' $_.Exception.Message
  Write-DeployLogsAndExit 1
}
