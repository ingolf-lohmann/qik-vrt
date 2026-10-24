# QIKVRT Artifact Header
# Deutsch: AV-sichere Windows-Abhaengigkeitspruefung nach Lizenzakzeptanz und GUID-Persistenz.
# English: AV-safe Windows dependency resolution after license acceptance and GUID persistence.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
param([string]$RepoRoot = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
function FullPath([string]$p){ return [System.IO.Path]::GetFullPath($p) }
$RepoRoot = FullPath $RepoRoot
$RuntimeDir = Join-Path $RepoRoot 'qikvrt\runtime\bootstrap'
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$Tsv = Join-Path $RuntimeDir 'CHOCO_BOOTSTRAP_RESULT.tsv'
$Json = Join-Path $RuntimeDir 'CHOCO_BOOTSTRAP_RESULT.json'
$script:Rows = @()
function Add-BootstrapResult([string]$Gate,[string]$Status,[string]$Detail){
  $script:Rows += [pscustomobject]@{timestamp_utc=(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'); gate=$Gate; status=$Status; detail=$Detail}
  Write-Host ($Gate + "`t" + $Status + "`t" + $Detail)
}
function Persist-Results{
  $script:Rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Json -Encoding UTF8
  'timestamp_utc`tgate`tstatus`tdetail' | Set-Content -LiteralPath $Tsv -Encoding UTF8
  foreach($r in $script:Rows){ ($r.timestamp_utc + "`t" + $r.gate + "`t" + $r.status + "`t" + (([string]$r.detail -replace "`r?`n", ' ') -replace "`t", ' ')) | Add-Content -LiteralPath $Tsv -Encoding UTF8 }
}
function Is-Admin { return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }
function Refresh-Path { $m=[Environment]::GetEnvironmentVariable('Path','Machine'); $u=[Environment]::GetEnvironmentVariable('Path','User'); if($null -eq $m){$m=''}; if($null -eq $u){$u=''}; $env:Path=$m+';'+$u+';'+$env:Path; Add-BootstrapResult 'PATH_REFRESH' 'PASS' 'Machine/User PATH reloaded' }
function Find-CommandPath([string]$name){ $c=Get-Command $name -ErrorAction SilentlyContinue; if($null -ne $c){ return $c.Path }; return $null }
function Find-Choco { $c=Find-CommandPath 'choco.exe'; if($null -ne $c){ return $c }; $p='C:\ProgramData\chocolatey\bin\choco.exe'; if(Test-Path -LiteralPath $p){ return $p }; return $null }
function Find-Zig {
  $z=Find-CommandPath 'zig.exe'; if($null -ne $z){ return $z }
  $candidates=@(
    'C:\ProgramData\chocolatey\bin\zig.exe',
    (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\zig.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Zig\zig.exe')
  )
  foreach($p in $candidates){ if($p -and (Test-Path -LiteralPath $p)){ return $p } }
  if($env:LOCALAPPDATA){
    $pattern = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\zig.zig_*\zig-*\zig.exe'
    $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
    if($null -ne $found){ return $found.FullName }
  }
  return $null
}
try {
  $admin = Is-Admin
  if($admin){ Add-BootstrapResult 'WINDOWS_ADMIN_RIGHTS' 'PASS' 'Administrator rights present' } else { Add-BootstrapResult 'WINDOWS_ADMIN_RIGHTS' 'SKIP' 'not required for AV-safe existing-compiler resolution' }
  $lic = Join-Path $RepoRoot 'qikvrt\config\LICENSE_ACCEPTED.json'
  if(-not (Test-Path -LiteralPath $lic)){ Add-BootstrapResult 'LICENSE_ACCEPTANCE_PERSISTED_BEFORE_DEPENDENCY_RESOLUTION' 'BLOCK' 'LICENSE_ACCEPTED.json missing'; Persist-Results; exit 41 }
  $guid = Join-Path $RepoRoot 'qikvrt\runtime\REPOSITORY_GUID.txt'
  if(-not (Test-Path -LiteralPath $guid)){ Add-BootstrapResult 'REPOSITORY_GUID_PERSISTED_BEFORE_DEPENDENCY_RESOLUTION' 'BLOCK' 'REPOSITORY_GUID.txt missing'; Persist-Results; exit 42 }
  Add-BootstrapResult 'LICENSE_ACCEPTANCE_PERSISTED_BEFORE_DEPENDENCY_RESOLUTION' 'PASS' $lic
  Add-BootstrapResult 'REPOSITORY_GUID_PERSISTED_BEFORE_DEPENDENCY_RESOLUTION' 'PASS' $guid
  $choco = Find-Choco
  if($null -eq $choco){ Add-BootstrapResult 'CHOCO_PRESENT' 'SKIP' 'choco.exe not found; no automatic Chocolatey installer is executed in AV-safe default mode' } else { Add-BootstrapResult 'CHOCO_PRESENT' 'PASS' $choco; Add-BootstrapResult 'CHOCO_AVAILABLE' 'PASS' $choco }
  $zig = Find-Zig
  if($null -ne $zig){ Add-BootstrapResult 'DEPENDENCY_ZIG_EXISTING' 'PASS' ('zig already available: ' + $zig); Add-BootstrapResult 'ZIG_AVAILABLE_AFTER_DEPENDENCY_RESOLUTION' 'PASS' $zig; Persist-Results; exit 0 }
  if($env:QIKVRT_ALLOW_PACKAGE_INSTALL -ne '1'){
    Add-BootstrapResult 'PACKAGE_INSTALL_POLICY' 'BLOCK' 'no zig compiler found and automatic package installation is disabled by default; install Zig manually or set QIKVRT_ALLOW_PACKAGE_INSTALL=1 intentionally'
    Persist-Results
    exit 14
  }
  if(-not $admin){ Add-BootstrapResult 'PACKAGE_INSTALL_ADMIN_RIGHTS' 'BLOCK' 'QIKVRT_ALLOW_PACKAGE_INSTALL=1 requires administrator rights'; Persist-Results; exit 77 }
  if($null -eq $choco){ Add-BootstrapResult 'CHOCO_AVAILABLE_FOR_OPT_IN_INSTALL' 'BLOCK' 'choco.exe unavailable; install Chocolatey manually or install Zig manually'; Persist-Results; exit 12 }
  Add-BootstrapResult 'CHOCO_DEPENDENCY_ZIG' 'PASS' 'opt-in installing zig via existing Chocolatey because QIKVRT_ALLOW_PACKAGE_INSTALL=1'
  $out=Join-Path $RuntimeDir 'choco_zig.out.txt'; $err=Join-Path $RuntimeDir 'choco_zig.err.txt'
  $p=Start-Process -FilePath $choco -ArgumentList @('install','zig','-y','--no-progress') -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
  Refresh-Path
  if($p.ExitCode -ne 0){ Add-BootstrapResult 'CHOCO_DEPENDENCY_ZIG_EXIT' 'BLOCK' ('exit=' + $p.ExitCode); Persist-Results; exit 13 }
  Add-BootstrapResult 'CHOCO_DEPENDENCY_ZIG_EXIT' 'PASS' 'exit=0'
  $zig = Find-Zig
  if($null -eq $zig){ Add-BootstrapResult 'ZIG_AVAILABLE_AFTER_DEPENDENCY_RESOLUTION' 'BLOCK' 'zig.exe unavailable after opt-in Chocolatey resolution'; Persist-Results; exit 14 }
  Add-BootstrapResult 'ZIG_AVAILABLE_AFTER_DEPENDENCY_RESOLUTION' 'PASS' $zig
  Persist-Results
  exit 0
} catch {
  Add-BootstrapResult 'DEPENDENCY_RESOLUTION_ERROR' 'BLOCK' $_.Exception.Message
  Persist-Results
  exit 15
}
