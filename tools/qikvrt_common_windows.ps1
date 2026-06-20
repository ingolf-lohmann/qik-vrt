Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-QikPass([string]$Message) { Write-Host ("PASS " + $Message) }
function Write-QikCont([string]$Message) { Write-Host ("CONTINUE " + $Message) }
function Write-QikBlock([string]$Message, [int]$Code = 1) { Write-Host ("BLOCK " + $Message); exit $Code }

function Normalize-QikvrtPathArg {
  param([Parameter(Mandatory=$true)][string]$Path, [switch]$MustExist)
  if ([string]::IsNullOrWhiteSpace($Path)) { Write-QikBlock "empty path argument" }
  $expanded = [Environment]::ExpandEnvironmentVariables($Path)
  if ($MustExist) {
    try { return (Resolve-Path -LiteralPath $expanded).Path.TrimEnd('\') }
    catch { Write-QikBlock ("path does not exist: " + $expanded) }
  }
  $parent = Split-Path -Parent $expanded
  if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  return [System.IO.Path]::GetFullPath($expanded).TrimEnd('\')
}

function Invoke-Qik {
  param([Parameter(Mandatory=$true)][string]$Exe,[Parameter(Mandatory=$false)][string[]]$Args=@(),[switch]$AllowFail)
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try { $output = & $Exe @Args 2>&1; $code = $LASTEXITCODE }
  catch { $output = @($_.Exception.Message); $code = 127 }
  finally { $ErrorActionPreference = $oldEap }
  if ($null -ne $output) { foreach ($line in $output) { if ($null -ne $line -and "$line".Length -gt 0) { Write-Host $line } } }
  if (-not $AllowFail -and $code -ne 0) { Write-QikBlock ("command failed rc=" + $code + ": " + $Exe + " " + ($Args -join " ")) }
  return [pscustomobject]@{ Code=$code; Output=(($output | ForEach-Object { "$_" }) -join "`n") }
}

function Get-QikSha256([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }

function Convert-QikOrigin([string]$OriginInput) {
  if ([string]::IsNullOrWhiteSpace($OriginInput)) { return "https://github.com/Goldkelch/qik-vrt.git" }
  $x = $OriginInput.Trim()
  if ($x -match '^https://github\.com/.+/.+(\.git)?$') { if ($x.EndsWith(".git")) { return $x } else { return ($x + ".git") } }
  if ($x -match '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { return ("https://github.com/" + $x + ".git") }
  return $x
}

function Ensure-QikGitIdentity {
  Invoke-Qik git @("config","--local","user.name","Ingolf Lohmann") | Out-Null
  Invoke-Qik git @("config","--local","user.email","ingolf.lohmann@web.de") | Out-Null
  Invoke-Qik git @("config","--local","core.autocrlf","false") | Out-Null
  Invoke-Qik git @("config","--local","core.safecrlf","false") | Out-Null
  Write-QikPass "repository-local Git identity/config ready"
}

function Persist-QikRejectedConfirmation {
  param([string]$RootPath,[string]$Actual,[string]$Context,[string]$Version="V45.16")
  New-Item -ItemType Directory -Force -Path (Join-Path $RootPath "audit") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $RootPath "state") | Out-Null
  $knownTypo = $false
  if ($Actual -eq "JA, ICH AKUEPTIERE") { $knownTypo = $true }
  $obj = [ordered]@{
    schema="qikvrt_rejected_confirmation_runtime_v45_16"; utc=(Get-Date).ToUniversalTime().ToString("o");
    expected="JA, ICH AKZEPTIERE"; actual=$Actual; known_typo_akueptiere=$knownTypo;
    accepted=$false; real_github_effect_started=$false; context=$Context; version=$Version;
    repair_note="V45.16 persists rejected attempts but never accepts typo confirmation as authorization."
  }
  $json = $obj | ConvertTo-Json -Depth 8
  $p1 = Join-Path $RootPath "state\rejected_owner_confirmation_runtime.v45.16.json"
  $p2 = Join-Path $RootPath "audit\rejected_owner_confirmation_runtime.v45.16.json"
  $json | Set-Content -LiteralPath $p1 -Encoding UTF8
  $json | Set-Content -LiteralPath $p2 -Encoding UTF8
  Write-QikPass ("rejected confirmation persisted before block: " + $p1)
}

function Copy-QikDirectoryChildren {
  param([string]$Source,[string]$Destination)
  foreach ($child in Get-ChildItem -LiteralPath $Source -Force) {
    if ($child.Name -eq ".git") { continue }
    Copy-Item -LiteralPath $child.FullName -Destination $Destination -Recurse -Force
  }
}
