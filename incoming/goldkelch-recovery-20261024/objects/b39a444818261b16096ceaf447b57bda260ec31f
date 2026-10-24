# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

param(
  [string]$RepoRoot = (Get-Location).Path,
  [switch]$SkipLiveFetch,
  [switch]$SkipBuild,
  [switch]$SkipDependencyBootstrap
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

function FullPath([string]$p) {
  return [System.IO.Path]::GetFullPath($p)
}

$RepoRoot = FullPath $RepoRoot
Set-Location -LiteralPath $RepoRoot

$RuntimeDir = Join-Path $RepoRoot 'qikvrt\runtime\win_acceptance'
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$TsvPath = Join-Path $RuntimeDir 'WIN_ACCEPTANCE_RESULT.tsv'
$JsonPath = Join-Path $RuntimeDir 'WIN_ACCEPTANCE_RESULT.json'
$script:Rows = @()
$script:Failed = $false

function Add-Result([string]$Gate, [string]$Status, [string]$Detail) {
  if ($null -eq $Detail) { $Detail = '' }
  $row = New-Object PSObject -Property @{
    timestamp_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    gate = $Gate
    status = $Status
    detail = $Detail
  }
  $script:Rows += $row
  if ($Status -eq 'FAIL') { $script:Failed = $true }
  Write-Host (($Gate + "`t" + $Status + "`t" + $Detail))
}

function FileExists([string]$Rel) {
  $p = Join-Path $RepoRoot $Rel
  if (Test-Path -LiteralPath $p) { Add-Result ('FILE_' + $Rel) 'PASS' 'present' } else { Add-Result ('FILE_' + $Rel) 'FAIL' 'missing' }
}

function Sha256([string]$Path) {
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Read-ShortLog([string]$Path) {
  try {
    if (-not (Test-Path -LiteralPath $Path)) { return '' }
    $txt = Get-Content -Raw -LiteralPath $Path
    if ($null -eq $txt) { return '' }
    $txt = $txt -replace "`r?`n", ' ' 
    if ($txt.Length -gt 600) { return $txt.Substring(0, 600) }
    return $txt
  } catch { return '' }
}

function Refresh-PathFromRegistry {
  try {
    $machine = [Environment]::GetEnvironmentVariable('Path','Machine')
    $user = [Environment]::GetEnvironmentVariable('Path','User')
    if ($null -eq $machine) { $machine = '' }
    if ($null -eq $user) { $user = '' }
    $env:Path = $machine + ';' + $user + ';' + $env:Path
    Add-Result 'PATH_REFRESH' 'PASS' 'Machine/User PATH reloaded into current PowerShell process'
  } catch {
    Add-Result 'PATH_REFRESH' 'BLOCK' $_.Exception.Message
  }
}

function Add-DirectoryToPath([string]$Dir) {
  if (($null -eq $Dir) -or ($Dir.Trim().Length -eq 0)) { return }
  if (-not (Test-Path -LiteralPath $Dir)) { return }
  $parts = $env:Path -split ';'
  foreach ($part in $parts) {
    if ($part.Trim().ToLowerInvariant() -eq $Dir.Trim().ToLowerInvariant()) { return }
  }
  $env:Path = $Dir + ';' + $env:Path
}

function New-CompilerCandidate([string]$Kind, [string]$Path, [string]$Detail) {
  $o = New-Object PSObject -Property @{
    kind = $Kind
    path = $Path
    detail = $Detail
  }
  return $o
}

function To-ObjectArray([object]$Value) {
  if ($null -eq $Value) { return ,@() }
  $arr = @($Value | Where-Object { $null -ne $_ })
  return ,$arr
}

function Get-ObjectArrayCount([object]$Value) {
  $arr = To-ObjectArray $Value
  return [int]($arr | Measure-Object).Count
}

function Add-CandidateIfFile([object[]]$List, [string]$Kind, [string]$Path, [string]$Detail) {
  if (($null -eq $Path) -or ($Path.Trim().Length -eq 0)) { return $List }
  if (-not (Test-Path -LiteralPath $Path)) { return $List }
  $full = [System.IO.Path]::GetFullPath($Path)
  foreach ($x in $List) {
    if ($x.path.ToLowerInvariant() -eq $full.ToLowerInvariant()) { return $List }
  }
  $dir = Split-Path -Parent $full
  Add-DirectoryToPath $dir
  return @($List + (New-CompilerCandidate $Kind $full $Detail))
}

function Add-CandidatesByPattern([object[]]$List, [string]$Kind, [string]$Pattern, [string]$Detail) {
  try {
    $hits = Get-ChildItem -Path $Pattern -ErrorAction SilentlyContinue
    foreach ($h in $hits) {
      if (-not $h.PSIsContainer) { $List = Add-CandidateIfFile $List $Kind $h.FullName $Detail }
    }
  } catch { }
  return $List
}

function Find-VsDevCmdCandidates([object[]]$List) {
  $roots = @()
  if ($env:ProgramFiles) { $roots += (Join-Path $env:ProgramFiles 'Microsoft Visual Studio') }
  $pf86 = ${env:ProgramFiles(x86)}
  if ($pf86) { $roots += (Join-Path $pf86 'Microsoft Visual Studio') }
  foreach ($root in $roots) {
    try {
      if (Test-Path -LiteralPath $root) {
        $hits = Get-ChildItem -Path (Join-Path $root '*\*\Common7\Tools\VsDevCmd.bat') -ErrorAction SilentlyContinue
        foreach ($h in $hits) {
          $full = [System.IO.Path]::GetFullPath($h.FullName)
          $exists = $false
          foreach ($x in $List) { if ($x.path.ToLowerInvariant() -eq $full.ToLowerInvariant()) { $exists = $true } }
          if (-not $exists) { $List = @($List + (New-CompilerCandidate 'msvc_devcmd' $full 'Visual Studio DevCmd')) }
        }
      }
    } catch { }
  }
  return $List
}

function Find-CompilerCandidates {
  $list = @()

  $cmds = @(
    @{Name='zig.exe'; Kind='zigcc'},
    @{Name='cl.exe'; Kind='msvc_path'},
    @{Name='gcc.exe'; Kind='gcc'},
    @{Name='clang.exe'; Kind='clang'}
  )
  foreach ($c in $cmds) {
    $cmd = Get-Command $c.Name -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
      $list = Add-CandidateIfFile $list $c.Kind $cmd.Path ('PATH ' + $c.Name)
    }
  }

  $pf = $env:ProgramFiles
  $pf86 = ${env:ProgramFiles(x86)}
  $la = $env:LOCALAPPDATA

  if ($pf) {
    $list = Add-CandidateIfFile $list 'clang' (Join-Path $pf 'LLVM\bin\clang.exe') 'known LLVM ProgramFiles path'
    $list = Add-CandidateIfFile $list 'zigcc' (Join-Path $pf 'Zig\zig.exe') 'known Zig ProgramFiles path'
    $list = Add-CandidatesByPattern $list 'gcc' (Join-Path $pf 'WinLibs\*\bin\gcc.exe') 'known WinLibs ProgramFiles pattern'
  }
  if ($pf86) {
    $list = Add-CandidateIfFile $list 'clang' (Join-Path $pf86 'LLVM\bin\clang.exe') 'known LLVM ProgramFiles(x86) path'
    $list = Add-CandidateIfFile $list 'zigcc' (Join-Path $pf86 'Zig\zig.exe') 'known Zig ProgramFiles(x86) path'
    $list = Add-CandidatesByPattern $list 'gcc' (Join-Path $pf86 'WinLibs\*\bin\gcc.exe') 'known WinLibs ProgramFiles(x86) pattern'
  }
  if ($la) {
    $list = Add-CandidateIfFile $list 'clang' (Join-Path $la 'Programs\LLVM\bin\clang.exe') 'known LLVM LocalAppData path'
    $list = Add-CandidateIfFile $list 'clang' (Join-Path $la 'Microsoft\WinGet\Links\clang.exe') 'known WinGet Links clang path'
    $list = Add-CandidateIfFile $list 'gcc' (Join-Path $la 'Microsoft\WinGet\Links\gcc.exe') 'known WinGet Links gcc path'
    $list = Add-CandidateIfFile $list 'zigcc' (Join-Path $la 'Microsoft\WinGet\Links\zig.exe') 'known WinGet Links zig path'
    $list = Add-CandidateIfFile $list 'zigcc' (Join-Path $la 'Programs\Zig\zig.exe') 'known Zig LocalAppData path'
    $list = Add-CandidatesByPattern $list 'gcc' (Join-Path $la 'Programs\WinLibs\*\bin\gcc.exe') 'known WinLibs LocalAppData pattern'
  }

  $list = Add-CandidateIfFile $list 'gcc' 'C:\msys64\ucrt64\bin\gcc.exe' 'known MSYS2 UCRT path'
  $list = Add-CandidateIfFile $list 'gcc' 'C:\msys64\mingw64\bin\gcc.exe' 'known MSYS2 MinGW64 path'
  $list = Add-CandidateIfFile $list 'clang' 'C:\msys64\clang64\bin\clang.exe' 'known MSYS2 Clang64 path'
  $list = Add-CandidateIfFile $list 'gcc' 'C:\Program Files\Git\mingw64\bin\gcc.exe' 'known Git for Windows MinGW path'
  $list = Add-CandidatesByPattern $list 'gcc' 'C:\WinLibs\*\bin\gcc.exe' 'known C:\WinLibs pattern'

  $list = Find-VsDevCmdCandidates $list
  return $list
}

function Report-CompilerCandidates([object]$Candidates, [string]$Gate) {
  $candidateList = To-ObjectArray $Candidates
  if ((Get-ObjectArrayCount $candidateList) -eq 0) {
    Add-Result $Gate 'BLOCK' 'no compiler candidates found'
    return
  }
  $parts = @()
  foreach ($c in $candidateList) { $parts += ($c.kind + ':' + $c.path) }
  Add-Result $Gate 'PASS' ($parts -join ' | ')
}

function Install-ChocoPackage([string]$Name, [string]$Gate) {
  if ($env:QIKVRT_ALLOW_PACKAGE_INSTALL -ne '1') {
    Add-Result $Gate 'BLOCK' ('automatic package installation disabled by default; set QIKVRT_ALLOW_PACKAGE_INSTALL=1 intentionally to install ' + $Name)
    return $false
  }
  $choco = Get-Command 'choco.exe' -ErrorAction SilentlyContinue
  if ($null -eq $choco) {
    Add-Result $Gate 'BLOCK' 'choco.exe not found; install dependencies manually or install Chocolatey outside QIKVRT'
    return $false
  }
  $safe = $Name -replace '[^A-Za-z0-9_\-]', '_'
  $out = Join-Path $RuntimeDir ($safe + '_choco.out.txt')
  $err = Join-Path $RuntimeDir ($safe + '_choco.err.txt')
  try {
    Add-Result $Gate 'PASS' ('explicit opt-in choco install attempt: ' + $Name)
    $p = Start-Process -FilePath $choco.Path -ArgumentList @('install',$Name,'-y','--no-progress') -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    Refresh-PathFromRegistry
    if ($p.ExitCode -eq 0) { Add-Result ($Gate + '_EXIT') 'PASS' 'exit=0'; return $true }
    Add-Result ($Gate + '_EXIT') 'BLOCK' ('exit=' + $p.ExitCode); return $false
  } catch { Add-Result ($Gate + '_ERROR') 'BLOCK' $_.Exception.Message; return $false }
}

function Bootstrap-MsvcBuildTools {
  $ok = Install-ChocoPackage 'visualstudio2022buildtools' 'DEPENDENCY_BOOTSTRAP_CHOCO_VSBT'
  Refresh-PathFromRegistry
  return $ok
}

function Bootstrap-ZigCompiler {
  $ok = Install-ChocoPackage 'zig' 'DEPENDENCY_BOOTSTRAP_CHOCO_ZIG'
  Refresh-PathFromRegistry
  return $ok
}

function Bootstrap-Compiler {
  if ($SkipDependencyBootstrap) {
    Add-Result 'DEPENDENCY_BOOTSTRAP' 'BLOCK' 'skipped by user'
    return
  }
  $existing = Sort-CompilerCandidates (Find-CompilerCandidates)
  if ((Get-ObjectArrayCount $existing) -gt 0) {
    Report-CompilerCandidates $existing 'DEPENDENCY_BOOTSTRAP_EXISTING_COMPILER'
    foreach ($cand in $existing) {
      if ($cand.kind -eq 'zigcc') { Add-Result 'DEPENDENCY_BOOTSTRAP' 'PASS' 'zig compiler candidate already present'; return }
    }
  }
  Add-Result 'DEPENDENCY_BOOTSTRAP_PACKAGE_INSTALL_POLICY' 'PASS' 'existing compiler preferred; package install requires QIKVRT_ALLOW_PACKAGE_INSTALL=1'
  Bootstrap-ZigCompiler | Out-Null
  $afterZig = Sort-CompilerCandidates (Find-CompilerCandidates)
  if ((Get-ObjectArrayCount $afterZig) -gt 0) {
    Report-CompilerCandidates $afterZig 'DEPENDENCY_BOOTSTRAP_AFTER_CHOCO_ZIG'
    foreach ($cand in $afterZig) {
      if ($cand.kind -eq 'zigcc') { Add-Result 'DEPENDENCY_BOOTSTRAP' 'PASS' 'zig compiler candidate found after Chocolatey resolution'; return }
    }
  }
  Add-Result 'DEPENDENCY_BOOTSTRAP' 'BLOCK' 'zig compiler unavailable after existing-compiler resolution and optional package-install path'
}

function Build-WithCompilerCandidate([object]$Candidate) {
  New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot 'build') | Out-Null
  $safeKind = ([string]$Candidate.kind) -replace '[^A-Za-z0-9_\-]', '_'
  $out = Join-Path $RuntimeDir ('build_' + $safeKind + '.out.txt')
  $err = Join-Path $RuntimeDir ('build_' + $safeKind + '.err.txt')
  $exe = Join-Path $RepoRoot 'build\qikvrt_verify.exe'
  if (Test-Path -LiteralPath $exe) { Remove-Item -LiteralPath $exe -Force }
  try {
    if ($Candidate.kind -eq 'msvc_path') {
      $buildArgs = @('/nologo','/TC','/W4','/WX','/Fe:build\qikvrt_verify.exe','src\main.c','src\qikvrt.c','/Iinclude','Ws2_32.lib')
      $p = Start-Process -FilePath $Candidate.path -ArgumentList $buildArgs -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    } elseif ($Candidate.kind -eq 'msvc_devcmd') {
      $bat = Join-Path $RuntimeDir 'build_msvc_devcmd.bat'
      $lines = @(
        '@echo off',
        'call "' + $Candidate.path + '" -arch=x64',
        'cd /d "' + $RepoRoot + '"',
        'cl.exe /nologo /TC /W4 /WX /Fe:build\qikvrt_verify.exe src\main.c src\qikvrt.c /Iinclude Ws2_32.lib'
      )
      $lines | Set-Content -LiteralPath $bat -Encoding ASCII
      $p = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', $bat) -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    } elseif ($Candidate.kind -eq 'zigcc') {
      $buildArgs = @('cc','-target','x86_64-windows-gnu','-std=c89','-pedantic','-Wall','-Wextra','-Werror','-Iinclude','-o','build\qikvrt_verify.exe','src\main.c','src\qikvrt.c','-lws2_32')
      $p = Start-Process -FilePath $Candidate.path -ArgumentList $buildArgs -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    } else {
      $buildArgs = @('-std=c89','-pedantic','-Wall','-Wextra','-Werror','-Iinclude','-o','build\qikvrt_verify.exe','src\main.c','src\qikvrt.c','-lws2_32')
      $p = Start-Process -FilePath $Candidate.path -ArgumentList $buildArgs -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    }
    if (($p.ExitCode -eq 0) -and (Test-Path -LiteralPath $exe)) {
      Add-Result 'C_BUILD' 'PASS' ($Candidate.kind + ' ' + $Candidate.path)
      return $true
    }
    Add-Result 'C_BUILD_ATTEMPT' 'BLOCK' ($Candidate.kind + ' exit=' + $p.ExitCode + ' path=' + $Candidate.path + ' stdout=' + $out + ' stderr=' + $err + ' err_sample=' + (Read-ShortLog $err))
    return $false
  } catch {
    Add-Result 'C_BUILD_ATTEMPT' 'BLOCK' ($Candidate.kind + ' ' + $_.Exception.Message)
    return $false
  }
}


function Get-CompilerPreferenceRank([object]$Candidate) {
  if ($Candidate.kind -eq 'zigcc') { return 0 }
  if ($Candidate.kind -eq 'msvc_path') { return 1 }
  if ($Candidate.kind -eq 'msvc_devcmd') { return 2 }
  if ($Candidate.kind -eq 'gcc') { return 3 }
  if ($Candidate.kind -eq 'clang') { return 9 }
  return 20
}
function Sort-CompilerCandidates([object]$Candidates) {
  $arr = To-ObjectArray $Candidates
  return ,($arr | Sort-Object @{ Expression = { Get-CompilerPreferenceRank $_ } }, @{ Expression = { [string]$_.path } })
}

function Try-Build-AllCandidates {
  $candidates = Sort-CompilerCandidates (Find-CompilerCandidates)
  Report-CompilerCandidates $candidates 'C_COMPILER_CANDIDATES'
  if ((Get-ObjectArrayCount $candidates) -eq 0) { return $false }
  foreach ($cand in $candidates) {
    $ok = Build-WithCompilerCandidate $cand
    if ($ok) { return $true }
  }
  return $false
}

function Run-Exe([string[]]$Arguments, [string]$Gate) {
  $exe = Join-Path $RepoRoot 'build\qikvrt_verify.exe'
  if (-not (Test-Path -LiteralPath $exe)) {
    Add-Result $Gate 'BLOCK' 'build\qikvrt_verify.exe missing'
    return
  }
  $safe = $Gate -replace '[^A-Za-z0-9_\-]', '_'
  $outFile = Join-Path $RuntimeDir ($safe + '.out.txt')
  $errFile = Join-Path $RuntimeDir ($safe + '.err.txt')
  try {
    $p = Start-Process -FilePath $exe -ArgumentList $Arguments -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile
    $txt = ''
    if (Test-Path -LiteralPath $outFile) { $txt = (Get-Content -Raw -LiteralPath $outFile).Trim() }
    if ($p.ExitCode -eq 0) { Add-Result $Gate 'PASS' $txt } else { Add-Result $Gate 'FAIL' ('exit=' + $p.ExitCode + ' ' + $txt) }
  } catch {
    Add-Result $Gate 'FAIL' $_.Exception.Message
  }
}

Add-Result 'WINDOWS_ACCEPTANCE_RUNNER' 'PASS' 'PowerShell 5.1 compatible runner started'
Add-Result 'REPO_ROOT' 'PASS' $RepoRoot
Add-Result 'PS_VERSION' 'PASS' ($PSVersionTable.PSVersion.ToString())

FileExists 'README.md'
FileExists 'LICENSE.md'
FileExists 'Makefile'
FileExists 'SHA256SUMS.txt'
FileExists 'QIKVRT.cmd'
FileExists 'QIKVRT.sh'
FileExists 'tools\license_acceptance.ps1'
FileExists 'tools\choco_bootstrap.ps1'
FileExists 'tools\win_acceptance.ps1'
FileExists 'src\main.c'
FileExists 'src\qikvrt.c'
FileExists 'include\qikvrt.h'
FileExists 'qikvrt\manifests\LE.json'
FileExists 'qikvrt\evidence\GH_WEB_REF.json'

try {
  $licenseAccepted = Join-Path $RepoRoot 'qikvrt\config\LICENSE_ACCEPTED.json'
  if (Test-Path -LiteralPath $licenseAccepted) {
    $lic = Get-Content -LiteralPath $licenseAccepted -Raw | ConvertFrom-Json
    if ($lic.accepted -eq $true) { Add-Result 'LICENSE_RUNTIME_ACCEPTANCE' 'PASS' 'accepted before Windows acceptance activity' } else { Add-Result 'LICENSE_RUNTIME_ACCEPTANCE' 'FAIL' 'LICENSE_ACCEPTED.json present but not accepted' }
  } else {
    Add-Result 'LICENSE_RUNTIME_ACCEPTANCE' 'FAIL' 'qikvrt/config/LICENSE_ACCEPTED.json missing; QIKVRT.cmd must gate before acceptance'
  }
} catch { Add-Result 'LICENSE_RUNTIME_ACCEPTANCE' 'FAIL' $_.Exception.Message }

try {
  $items = Get-ChildItem -LiteralPath $RepoRoot -Recurse -Force | Where-Object { -not $_.PSIsContainer }
  $maxRel = 0
  foreach ($i in $items) {
    $rel = $i.FullName.Substring($RepoRoot.Length).TrimStart('\','/')
    if ($rel.Length -gt $maxRel) { $maxRel = $rel.Length }
  }
  if ($maxRel -le 120) { Add-Result 'MAX_RELATIVE_PATH_LENGTH' 'PASS' ('max=' + $maxRel) } else { Add-Result 'MAX_RELATIVE_PATH_LENGTH' 'FAIL' ('max=' + $maxRel) }
} catch { Add-Result 'MAX_RELATIVE_PATH_LENGTH' 'FAIL' $_.Exception.Message }

try {
  $sumFile = Join-Path $RepoRoot 'SHA256SUMS.txt'
  $lines = Get-Content -LiteralPath $sumFile | Where-Object { $_.Trim().Length -gt 0 }
  $ok = 0; $bad = 0; $missing = 0
  foreach ($line in $lines) {
    if ($line -notmatch '^([0-9a-fA-F]{64})\s+(.+)$') { $bad = $bad + 1; continue }
    $expected = $Matches[1].ToLowerInvariant()
    $rel = $Matches[2].Trim().Replace('/','\')
    $path = Join-Path $RepoRoot $rel
    if (-not (Test-Path -LiteralPath $path)) { $missing = $missing + 1; continue }
    $actual = Sha256 $path
    if ($actual -eq $expected) { $ok = $ok + 1 } else { $bad = $bad + 1 }
  }
  if (($bad -eq 0) -and ($missing -eq 0)) { Add-Result 'SHA256SUMS' 'PASS' ('ok=' + $ok) } else { Add-Result 'SHA256SUMS' 'FAIL' ('ok=' + $ok + ' bad=' + $bad + ' missing=' + $missing) }
} catch { Add-Result 'SHA256SUMS' 'FAIL' $_.Exception.Message }

try {
  $jsonOk = 0; $jsonBad = 0
  $jsonFiles = Get-ChildItem -LiteralPath $RepoRoot -Recurse | Where-Object { (-not $_.PSIsContainer) -and ($_.Name -like '*.json') }
  foreach ($jf in $jsonFiles) {
    try { Get-Content -Raw -LiteralPath $jf.FullName | ConvertFrom-Json | Out-Null; $jsonOk = $jsonOk + 1 } catch { $jsonBad = $jsonBad + 1 }
  }
  if ($jsonBad -eq 0) { Add-Result 'JSON_PARSE_ALL' 'PASS' ('ok=' + $jsonOk) } else { Add-Result 'JSON_PARSE_ALL' 'FAIL' ('ok=' + $jsonOk + ' bad=' + $jsonBad) }
} catch { Add-Result 'JSON_PARSE_ALL' 'FAIL' $_.Exception.Message }

try {
  $jsonlOk = 0; $jsonlBad = 0
  $jsonlFiles = Get-ChildItem -LiteralPath $RepoRoot -Recurse | Where-Object { (-not $_.PSIsContainer) -and ($_.Name -like '*.jsonl') }
  foreach ($jlf in $jsonlFiles) {
    $content = Get-Content -LiteralPath $jlf.FullName
    foreach ($line in $content) {
      if ($line.Trim().Length -eq 0) { continue }
      try { $line | ConvertFrom-Json | Out-Null; $jsonlOk = $jsonlOk + 1 } catch { $jsonlBad = $jsonlBad + 1 }
    }
  }
  if ($jsonlBad -eq 0) { Add-Result 'JSONL_PARSE_ALL' 'PASS' ('ok=' + $jsonlOk) } else { Add-Result 'JSONL_PARSE_ALL' 'FAIL' ('ok=' + $jsonlOk + ' bad=' + $jsonlBad) }
} catch { Add-Result 'JSONL_PARSE_ALL' 'FAIL' $_.Exception.Message }

$ManifestPath = Join-Path $RuntimeDir 'GH_MANIFEST.json'
$RestPath = Join-Path $RuntimeDir 'GH_REST_TCPIP_MANIFEST.json'
if ($SkipLiveFetch) {
  Add-Result 'LIVE_GITHUB_FETCH' 'BLOCK' 'skipped by user'
} else {
  $targets = @(
    @{ Gate = 'LIVE_FETCH_MANIFEST'; Url = 'https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/MANIFEST.json'; Path = $ManifestPath },
    @{ Gate = 'LIVE_FETCH_REST_TCPIP_MANIFEST'; Url = 'https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/QIKVRT_SELF_CONTAINED_GITHUB_REPOSITORY_WITH_REST_TCPIP_API_V1_MANIFEST.json'; Path = $RestPath }
  )
  foreach ($target in $targets) {
    try {
      $url = [string]$target['Url']
      $path = [string]$target['Path']
      $gate = [string]$target['Gate']
      $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60
      [System.IO.File]::WriteAllText($path, $resp.Content, [System.Text.Encoding]::UTF8)
      $resp.Content | ConvertFrom-Json | Out-Null
      $bytes = (Get-Item -LiteralPath $path).Length
      $hash = Sha256 $path
      Add-Result $gate 'PASS' ('http=200 bytes=' + $bytes + ' sha256=' + $hash + ' url=' + $url)
    } catch {
      Add-Result ([string]$target['Gate']) 'FAIL' $_.Exception.Message
    }
  }
}

if ($SkipBuild) {
  Add-Result 'C_BUILD' 'BLOCK' 'skipped by user'
} else {
  Bootstrap-Compiler
  $built = Try-Build-AllCandidates
  if (-not $built) {
    Add-Result 'C_BUILD_PRIMARY_CANDIDATES' 'BLOCK' 'no existing/LLVM/choco compiler candidate produced build\qikvrt_verify.exe'
    Bootstrap-ZigCompiler | Out-Null
    $built = Try-Build-AllCandidates
  }
  if (-not $built) {
    $msvcCandidatesBefore = To-ObjectArray (Find-CompilerCandidates)
    $hasMsvc = $false
    foreach ($cand in $msvcCandidatesBefore) { if (($cand.kind -eq 'msvc_path') -or ($cand.kind -eq 'msvc_devcmd')) { $hasMsvc = $true } }
    if (-not $hasMsvc) {
      Bootstrap-MsvcBuildTools | Out-Null
      $built = Try-Build-AllCandidates
    }
  }
  if (-not $built) {
    Add-Result 'C_BUILD' 'BLOCK' 'no compiler candidate could build the C verifier after dependency bootstrap attempts'
  }
}


if (Test-Path -LiteralPath (Join-Path $RepoRoot 'build\qikvrt_verify.exe')) {
  Run-Exe @('--verify-repo','.') 'VERIFY_REPO'
  Run-Exe @('--validate-root-layout','.') 'VALIDATE_ROOT_LAYOUT'
  if (Test-Path -LiteralPath $ManifestPath) { Run-Exe @('--validate-github-seed-manifest',$ManifestPath) 'VALIDATE_LIVE_GITHUB_SEED_MANIFEST' }
  Run-Exe @('--validate-live-evidence','qikvrt\evidence\GH_WEB_REF.json') 'VALIDATE_STATIC_LIVE_EVIDENCE'
  $selftests = @('--selftest-multicast','--selftest-ontology','--selftest-governance','--selftest-active','--selftest-watchdog','--selftest-bootstrap','--selftest-tcpip-autonomy','--selftest-damage-containment','--selftest-autonomous-discovery','--selftest-github-seed-discovery','--selftest-real-github-seed-integration','--selftest-zip-layout','--selftest-windows-shell-zip','--selftest-short-path','--selftest-live-evidence','--selftest-claim-matrix','--selftest-node-onboarding','--selftest-rest-api','--selftest-unified-node-core','--selftest-node-onboarding-testbed','--selftest-license-visibility','--selftest-full-test-env','--selftest-seed-node-delivery','--selftest-bilingual-docs','--selftest-github-deploy','--selftest-repository-setup')
  foreach ($st in $selftests) {
    $gate = ('C_' + $st.Replace('--','').Replace('-','_')).ToUpperInvariant()
    Run-Exe @($st) $gate
  }
} else {
  Add-Result 'C_SELFTESTS' 'BLOCK' 'not executed because build\qikvrt_verify.exe is missing'
}

try {
  $script:Rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
  'timestamp_utc`tgate`tstatus`tdetail' | Set-Content -LiteralPath $TsvPath -Encoding UTF8
  foreach ($row in $script:Rows) {
    $detail = [string]$row.detail
    $detail = $detail -replace "`r?`n", ' '
    $detail = $detail -replace "`t", ' '
    ($row.timestamp_utc + "`t" + $row.gate + "`t" + $row.status + "`t" + $detail) | Add-Content -LiteralPath $TsvPath -Encoding UTF8
  }
  Add-Result 'RESULT_TSV' 'PASS' $TsvPath
  Add-Result 'RESULT_JSON' 'PASS' $JsonPath
} catch {
  Add-Result 'RESULT_PERSISTENCE' 'FAIL' $_.Exception.Message
}


function Has-GatePass([string]$Gate) {
  foreach ($row in $script:Rows) {
    if (($row.gate -eq $Gate) -and ($row.status -eq 'PASS')) { return $true }
  }
  return $false
}

function Require-GatePass([string]$Gate) {
  if (Has-GatePass $Gate) { return $true }
  Add-Result ('FINAL_REQUIRED_' + $Gate) 'FAIL' 'required final gate did not reach PASS'
  return $false
}

$finalOk = $true
$requiredFinalGates = @(
  'WINDOWS_ACCEPTANCE_RUNNER',
  'REPO_ROOT',
  'PS_VERSION',
  'FILE_README.md',
  'FILE_LICENSE.md',
  'FILE_Makefile',
  'FILE_SHA256SUMS.txt',
  'FILE_QIKVRT.cmd',
  'FILE_QIKVRT.sh',
  'FILE_tools\license_acceptance.ps1',
  'FILE_tools\choco_bootstrap.ps1',
  'FILE_tools\win_acceptance.ps1',
  'FILE_src\main.c',
  'FILE_src\qikvrt.c',
  'FILE_include\qikvrt.h',
  'FILE_qikvrt\manifests\LE.json',
  'FILE_qikvrt\evidence\GH_WEB_REF.json',
  'LICENSE_RUNTIME_ACCEPTANCE',
  'MAX_RELATIVE_PATH_LENGTH',
  'SHA256SUMS',
  'JSON_PARSE_ALL',
  'JSONL_PARSE_ALL',
  'LIVE_FETCH_MANIFEST',
  'LIVE_FETCH_REST_TCPIP_MANIFEST',
  'DEPENDENCY_BOOTSTRAP',
  'C_COMPILER_CANDIDATES',
  'C_BUILD',
  'VERIFY_REPO',
  'VALIDATE_ROOT_LAYOUT',
  'VALIDATE_LIVE_GITHUB_SEED_MANIFEST',
  'VALIDATE_STATIC_LIVE_EVIDENCE',
  'C_SELFTEST_MULTICAST',
  'C_SELFTEST_ONTOLOGY',
  'C_SELFTEST_GOVERNANCE',
  'C_SELFTEST_ACTIVE',
  'C_SELFTEST_WATCHDOG',
  'C_SELFTEST_BOOTSTRAP',
  'C_SELFTEST_TCPIP_AUTONOMY',
  'C_SELFTEST_DAMAGE_CONTAINMENT',
  'C_SELFTEST_AUTONOMOUS_DISCOVERY',
  'C_SELFTEST_GITHUB_SEED_DISCOVERY',
  'C_SELFTEST_REAL_GITHUB_SEED_INTEGRATION',
  'C_SELFTEST_ZIP_LAYOUT',
  'C_SELFTEST_WINDOWS_SHELL_ZIP',
  'C_SELFTEST_SHORT_PATH',
  'C_SELFTEST_LIVE_EVIDENCE',
  'C_SELFTEST_CLAIM_MATRIX',
  'C_SELFTEST_NODE_ONBOARDING',
  'C_SELFTEST_REST_API',
  'C_SELFTEST_UNIFIED_NODE_CORE',
  'C_SELFTEST_NODE_ONBOARDING_TESTBED',
  'C_SELFTEST_LICENSE_VISIBILITY',
  'C_SELFTEST_FULL_TEST_ENV',
  'C_SELFTEST_SEED_NODE_DELIVERY',
  'C_SELFTEST_BILINGUAL_DOCS',
  'C_SELFTEST_GITHUB_DEPLOY',
  'C_SELFTEST_REPOSITORY_SETUP',
  'RESULT_TSV',
  'RESULT_JSON'
)
foreach ($gate in $requiredFinalGates) {
  if (-not (Require-GatePass $gate)) { $finalOk = $false }
}

if ($finalOk) {
  Add-Result 'WINDOWS_ACCEPTANCE_FINAL_EVALUATION' 'PASS' 'all required final gates reached PASS; recovered compiler attempts remain audit-only'
} else {
  Add-Result 'WINDOWS_ACCEPTANCE_FINAL_EVALUATION' 'FAIL' 'at least one required final gate did not reach PASS'
}

try {
  $script:Rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
  'timestamp_utc`tgate`tstatus`tdetail' | Set-Content -LiteralPath $TsvPath -Encoding UTF8
  foreach ($row in $script:Rows) {
    $detail = [string]$row.detail
    $detail = $detail -replace "`r?`n", ' '
    $detail = $detail -replace "`t", ' '
    ($row.timestamp_utc + "`t" + $row.gate + "`t" + $row.status + "`t" + $detail) | Add-Content -LiteralPath $TsvPath -Encoding UTF8
  }
} catch { }

if (-not $finalOk) {
  Write-Host 'WINDOWS_ACCEPTANCE_RESULT=BLOCK_OR_FAIL'
  exit 1
}
Write-Host 'WINDOWS_ACCEPTANCE_RESULT=PASS'
exit 0
