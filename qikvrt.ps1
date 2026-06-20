<#
Copyright 2026 Ingolf Lohmann.
Licensed under the Apache License, Version 2.0 (the "License");
See LICENSES/Apache-2.0.txt.
required-token: DEFAULT_COMMAND=master-gate
required-token: download_python_runtime.ps1
#>
$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DefaultCommand = "master-gate"
if ($args.Count -eq 0) { $EffectiveArgs = @($DefaultCommand) } else { $EffectiveArgs = $args }
$LogDir = Join-Path $ScriptDir "logs"
$LogFile = Join-Path $LogDir "qikvrt_last_run.jsonl"
$LogJsonPath = $LogFile.Replace("\", "/")
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
Set-Content -Path $LogFile -Value ("{""event"":""run_start"",""launcher"":""qikvrt.ps1"",""logfile"":""" + $LogJsonPath + """,""default_command"":""master-gate"",""dependency_contract"":""GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_GATE""}") -Encoding UTF8
Write-Host "QIK-VRT V22 PowerShell Launcher"
Write-Host "Command: $($EffectiveArgs -join ' ')"
Write-Host "Logfile: $LogFile"

$Candidate1 = Join-Path $ScriptDir "runtime\python\windows\python.exe"
$Candidate2 = Join-Path $ScriptDir "python\python.exe"
$PythonCommand = $null
if (Test-Path $Candidate1) { $PythonCommand = $Candidate1 }
elseif (Test-Path $Candidate2) { $PythonCommand = $Candidate2 }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $PythonCommand = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $PythonCommand = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $PythonCommand = "python3" }

if ($null -eq $PythonCommand) {
  Add-Content -Path $LogFile -Value '{"event":"runtime_missing","status":"CONTINUE","continue_path":"DOWNLOAD_ACCEPTED_PYTHON_RUNTIME","dependency_contract":"GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_GATE","license_area":"third_party_python_runtime"}'
  & powershell -ExecutionPolicy Bypass -NoProfile -File (Join-Path $ScriptDir "runtime\download_python_runtime.ps1")
  if (Test-Path $Candidate1) { $PythonCommand = $Candidate1 }
}

if ($null -eq $PythonCommand) {
  $ExitCode = 20
  Add-Content -Path $LogFile -Value '{"event":"run_end","status":"CONTINUE","exit_code":20,"error_class":"PYTHON_RUNTIME_DOWNLOAD_NOT_COMPLETED","continue_path":"CHECK_NETWORK_OR_MANUAL_RUNTIME_INSTALL"}'
} else {
  if ($PythonCommand -eq "py") { & py -3 (Join-Path $ScriptDir "qikvrt.py") @EffectiveArgs } else { & $PythonCommand (Join-Path $ScriptDir "qikvrt.py") @EffectiveArgs }
  $ExitCode = $LASTEXITCODE
  if ($ExitCode -ne 0) {
    Add-Content -Path $LogFile -Value ('{"event":"ps1_wrapper_end","status":"FAIL","exit_code":' + $ExitCode + ',"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_LOG_AND_REPAIR_NEXT_ERROR","repair_hint":"Inspect logs/qikvrt_last_run.jsonl."}')
    Add-Content -Path $LogFile -Value ('{"event":"run_end","status":"FAIL","exit_code":' + $ExitCode + ',"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_LOG_AND_REPAIR_NEXT_ERROR","repair_hint":"Inspect logs/qikvrt_last_run.jsonl.","logfile":"' + $LogJsonPath + '"}')
  } else {
    Add-Content -Path $LogFile -Value ('{"event":"ps1_wrapper_end","status":"PASS","exit_code":0}')
    Add-Content -Path $LogFile -Value ('{"event":"run_end","status":"PASS","exit_code":0,"error_class":"NONE","continue_path":"NONE","repair_hint":"NONE","logfile":"' + $LogJsonPath + '"}')
  }
}
Write-Host ""
Write-Host "QIK-VRT finished."
Write-Host "Exit-Code: $ExitCode"
Write-Host "Logfile: $LogFile"
Read-Host "Press Enter to close this window"
exit $ExitCode
