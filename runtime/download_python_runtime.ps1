<#
Copyright 2026 Ingolf Lohmann.
Licensed under the Apache License, Version 2.0 (the "License");
See LICENSES/Apache-2.0.txt.
Explicit reconstruction adapter for the existing runtime/cache authority.
#>
[CmdletBinding()]
param(
    [switch]$AcceptThirdParty,
    [switch]$ReconstructUpstream,
    [string]$ArchiveFile = '',
    [string]$CacheDir = ''
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$hostExe = (Get-Process -Id $PID).Path
$parameters = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
    '-File', (Join-Path $repo 'tools/bootstrap-runtime.ps1'), '-Profile', 'windows-start')
if ($AcceptThirdParty) { $parameters += @('-Install', '-AcceptThirdParty') }
else { $parameters += '-CheckOnly' }
if ($ReconstructUpstream) { $parameters += '-ReconstructUpstream' }
if ($ArchiveFile) { $parameters += @('-ArchiveFile', $ArchiveFile) }
if ($CacheDir) { $parameters += @('-CacheDir', $CacheDir) }
& $hostExe @parameters
exit $LASTEXITCODE
