<#
Copyright 2026 Ingolf Lohmann.
Licensed under the Apache License, Version 2.0 (the "License");
See LICENSES/Apache-2.0.txt.
The repository launcher remains the authorization-before-effect authority.
Upstream reconstruction is an explicit runtime/download_python_runtime.ps1 operation.
#>
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DefaultCommand = 'master-gate'
[string[]]$EffectiveArgs = if ($args.Count -eq 0) { @($DefaultCommand) } else { @($args) }
$powerShellExe = (Get-Process -Id $PID).Path
$bootstrap = Join-Path $ScriptDir 'tools/bootstrap-runtime.ps1'

function Invoke-LockedRuntime([switch]$PrintPath) {
    # Windows PowerShell must not turn successful native stderr telemetry into
    # a terminating NativeCommandError. Bind the child exit code and streams.
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $powerShellExe
    $start.Arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
        $bootstrap + '" -Install -AcceptThirdParty -Profile windows-start'
    if ($PrintPath) { $start.Arguments += ' -PrintPath' }
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'Windows runtime bootstrap could not start' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(60000)) {
            $process.Kill()
            [void]$process.WaitForExit(2000)
            throw 'Windows runtime bootstrap exceeded its 60-second bound'
        }
        [Console]::Error.Write($stderr.Result)
        return [pscustomobject]@{ ExitCode = $process.ExitCode; Output = $stdout.Result }
    } finally { $process.Dispose() }
}

if ($EffectiveArgs.Count -eq 1 -and $EffectiveArgs[0] -eq '--runtime-self-test') {
    $result = Invoke-LockedRuntime
    [Console]::Out.Write($result.Output)
    exit $result.ExitCode
}

# Restoration of an already materialized, license-bound cache is local only.
# No launcher argument enables ReconstructUpstream or an unverified fallback.
$result = Invoke-LockedRuntime -PrintPath
if ($result.ExitCode -ne 0) { exit $result.ExitCode }
$pathOutput = @($result.Output.TrimEnd([char[]]"`r`n") -split '[\r\n]+')
if ($pathOutput.Count -ne 1) { throw 'Windows runtime bootstrap returned an ambiguous path' }
$PythonCommand = [string]$pathOutput[0]
& $PythonCommand -I -B (Join-Path $ScriptDir 'qikvrt.py') @EffectiveArgs
exit $LASTEXITCODE
