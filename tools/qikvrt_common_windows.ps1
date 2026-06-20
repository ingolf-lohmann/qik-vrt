$ErrorActionPreference = "Stop"
function Write-QikvrtPass([string]$Message) { Write-Host ("PASS " + $Message) }
function Write-QikvrtBlock([string]$Message) { Write-Host ("BLOCK " + $Message) }
function Write-QikvrtContinue([string]$Message) { Write-Host ("CONTINUE " + $Message) }
function Write-QikvrtWarn([string]$Message) { Write-Host ("WARN " + $Message) }

function Trim-QikvrtTrailingSeparator([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { return $Path }
  $p = $Path
  while ($p.Length -gt 3 -and ($p.EndsWith("\") -or $p.EndsWith("/"))) { $p = $p.Substring(0, $p.Length - 1) }
  return $p
}
function Normalize-QikvrtPathArg {
  param([Parameter(Mandatory=$true)][string]$Path,[switch]$MustExist)
  if ([string]::IsNullOrWhiteSpace($Path)) { throw "path argument is empty" }
  $p = $Path.Trim()
  while ($p.Length -ge 2 -and (($p.StartsWith('"') -and $p.EndsWith('"')) -or ($p.StartsWith("'") -and $p.EndsWith("'")))) { $p = $p.Substring(1, $p.Length - 2).Trim() }
  if ([string]::IsNullOrWhiteSpace($p)) { throw "path argument is empty after quote trim" }
  if ($p -match '[\x00-\x1F]') { throw "path contains control character: $p" }
  try {
    if (Test-Path -LiteralPath $p) { return (Trim-QikvrtTrailingSeparator ((Resolve-Path -LiteralPath $p).Path)) }
    if ($MustExist) { throw "path does not exist: $p" }
    return (Trim-QikvrtTrailingSeparator ([System.IO.Path]::GetFullPath($p)))
  } catch {
    if ($MustExist) { throw }
    try { return (Trim-QikvrtTrailingSeparator ([System.IO.Path]::GetFullPath($p))) } catch { throw "invalid path argument: $p" }
  }
}
function New-QikvrtDirectoryForFile([string]$Path) { $dir = Split-Path -Parent $Path; if (![string]::IsNullOrWhiteSpace($dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null } }
function Write-QikvrtJson([string]$Path, $Object) { New-QikvrtDirectoryForFile $Path; ($Object | ConvertTo-Json -Depth 30) | Set-Content -LiteralPath $Path -Encoding UTF8 }
function Read-QikvrtJson([string]$Path) { if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }; return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json) }
function Assert-QikvrtCommand([string]$Name) { $cmd = Get-Command $Name -ErrorAction SilentlyContinue; if ($null -eq $cmd) { throw "required command missing: $Name" }; return $cmd.Source }
function Get-QikvrtSha256([string]$Path) { if (!(Test-Path -LiteralPath $Path)) { throw "file missing for sha256: $Path" }; return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function ConvertTo-QikvrtCommandLineArgument([AllowNull()][object]$Argument) {
  if ($null -eq $Argument) { return '""' }
  $arg = [string]$Argument
  if ($arg.Length -eq 0) { return '""' }
  if ($arg -notmatch '[\s"]') { return $arg }
  $result = '"'; $backslashes = 0
  for ($i = 0; $i -lt $arg.Length; $i++) {
    $ch = $arg[$i]
    if ($ch -eq '\') { $backslashes++ }
    elseif ($ch -eq '"') { if ($backslashes -gt 0) { $result += ('\' * ($backslashes * 2)) }; $result += '\"'; $backslashes = 0 }
    else { if ($backslashes -gt 0) { $result += ('\' * $backslashes) }; $backslashes = 0; $result += $ch }
  }
  if ($backslashes -gt 0) { $result += ('\' * ($backslashes * 2)) }
  $result += '"'; return $result
}
function Join-QikvrtCommandLineArguments([AllowNull()][object[]]$Arguments) { if ($null -eq $Arguments) { return '' }; $parts=@(); foreach ($a in $Arguments) { $parts += (ConvertTo-QikvrtCommandLineArgument $a) }; return ($parts -join ' ') }
function Invoke-QikvrtCapture([string]$FilePath, [AllowNull()][object[]]$Arguments) {
  if ([string]::IsNullOrWhiteSpace($FilePath)) { throw "process FilePath is empty" }
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $FilePath
  $psi.Arguments = Join-QikvrtCommandLineArguments $Arguments
  $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
  $p = [System.Diagnostics.Process]::Start($psi); if ($null -eq $p) { throw "failed to start process: $FilePath" }
  $stdout = $p.StandardOutput.ReadToEnd(); $stderr = $p.StandardError.ReadToEnd(); $p.WaitForExit()
  return [pscustomobject]@{ ExitCode=$p.ExitCode; Stdout=$stdout; Stderr=$stderr; FilePath=$FilePath; Arguments=$psi.Arguments }
}
function Copy-QikvrtWorktreeOverlayToTemp { param([Parameter(Mandatory=$true)][string]$RepoPath,[Parameter(Mandatory=$true)][string]$OverlayPath)
  New-Item -ItemType Directory -Force -Path $OverlayPath | Out-Null
  Get-ChildItem -LiteralPath $RepoPath -Force | Where-Object { $_.Name -ne ".git" } | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $OverlayPath -Recurse -Force }
}
function Clear-QikvrtWorktreeExceptGit { param([Parameter(Mandatory=$true)][string]$RepoPath)
  Get-ChildItem -LiteralPath $RepoPath -Force | Where-Object { $_.Name -ne ".git" } | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
}
function Restore-QikvrtWorktreeOverlayFromTemp { param([Parameter(Mandatory=$true)][string]$OverlayPath,[Parameter(Mandatory=$true)][string]$RepoPath)
  Get-ChildItem -LiteralPath $OverlayPath -Force | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $RepoPath -Recurse -Force }
}
function Test-QikvrtRemoteBranchExists { param([string]$RemoteName="origin",[string]$Branch="main")
  $probe = Invoke-QikvrtCapture "git" @("ls-remote","--heads",$RemoteName,$Branch)
  return ($probe.ExitCode -eq 0 -and ![string]::IsNullOrWhiteSpace($probe.Stdout.Trim()))
}
function Test-QikvrtRemoteIsAncestorOfHead { param([string]$RemoteRef)
  $probe = Invoke-QikvrtCapture "git" @("merge-base","--is-ancestor",$RemoteRef,"HEAD")
  return ($probe.ExitCode -eq 0)
}
function Get-QikvrtGitConfigValue([string]$Key) { $probe=Invoke-QikvrtCapture "git" @("config","--local","--get",$Key); if ($probe.ExitCode -eq 0) { return $probe.Stdout.Trim() }; return "" }
function Set-QikvrtGitConfigIfMissing { param([Parameter(Mandatory=$true)][string]$Key,[Parameter(Mandatory=$true)][string]$Value)
  $current = Get-QikvrtGitConfigValue $Key
  if ([string]::IsNullOrWhiteSpace($current)) { & git config --local $Key $Value; if ($LASTEXITCODE -ne 0) { throw "git config --local $Key failed" }; Write-QikvrtPass "local git config set: $Key" } else { Write-QikvrtPass "local git config present: $Key" }
}
function Ensure-QikvrtLocalGitIdentity { param([string]$GitUserName="Ingolf Lohmann",[string]$GitUserEmail="ingolf.lohmann@web.de")
  if ([string]::IsNullOrWhiteSpace($GitUserName)) { $GitUserName = "Ingolf Lohmann" }
  if ([string]::IsNullOrWhiteSpace($GitUserEmail)) { $GitUserEmail = "ingolf.lohmann@web.de" }
  Set-QikvrtGitConfigIfMissing -Key "user.name" -Value $GitUserName
  Set-QikvrtGitConfigIfMissing -Key "user.email" -Value $GitUserEmail
  Set-QikvrtGitConfigIfMissing -Key "core.autocrlf" -Value "false"
  Set-QikvrtGitConfigIfMissing -Key "core.safecrlf" -Value "false"
  Write-QikvrtPass "repository-local Git identity/config ready before commit"
}
function Normalize-QikvrtGitHubRemote([string]$RemoteUrlOrSlug) {
  if ([string]::IsNullOrWhiteSpace($RemoteUrlOrSlug)) { return "" }
  $v = $RemoteUrlOrSlug.Trim()
  if ($v -match '^https://github\.com/[^/]+/[^/]+(\.git)?$') { if ($v.EndsWith('.git')) { return $v } else { return ($v + '.git') } }
  if ($v -match '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { return ('https://github.com/' + $v + '.git') }
  if ($v -match '^git@github\.com:[^/]+/[^/]+\.git$') { return $v }
  return $v
}
function Get-QikvrtRemoteRefSha { param([Parameter(Mandatory=$true)][string]$Ref)
  $probe = Invoke-QikvrtCapture "git" @("ls-remote","origin",$Ref)
  if ($probe.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($probe.Stdout.Trim())) { return "" }
  return (($probe.Stdout.Trim() -split "\s+")[0]).ToLowerInvariant()
}
function Test-QikvrtReleaseAssetExists { param([Parameter(Mandatory=$true)][string]$Tag,[Parameter(Mandatory=$true)][string]$AssetName)
  $raw = (& gh release view $Tag --json assets)
  if ($LASTEXITCODE -ne 0) { return $false }
  $obj = $raw | ConvertFrom-Json
  foreach ($a in $obj.assets) { if ($a.name -eq $AssetName) { return $true } }
  return $false
}
