<#
Copyright 2026 Ingolf Lohmann.
Licensed under the Apache License, Version 2.0 (the "License");
See LICENSES/Apache-2.0.txt.
Downloads official Python Windows embeddable runtime after accepted license/provenance consent.
#>
$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $RepoRoot "logs"
$LogFile = Join-Path $LogDir "qikvrt_last_run.jsonl"
$RuntimeDir = Join-Path $RepoRoot "runtime\python\windows"
$ZipFile = Join-Path $RuntimeDir "python-3.12.10-embed-amd64.zip"
$Url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"

if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
if (!(Test-Path $RuntimeDir)) { New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null }

Add-Content -Path $LogFile -Value '{"event":"runtime_download_start","component":"python-embed-amd64","url":"https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip","license_area":"third_party_python_runtime"}'

try {
  Invoke-WebRequest -Uri $Url -OutFile $ZipFile -UseBasicParsing
  $Hash = (Get-FileHash -Algorithm SHA256 -Path $ZipFile).Hash.ToLower()
  Expand-Archive -Path $ZipFile -DestinationPath $RuntimeDir -Force
  if (Test-Path (Join-Path $RuntimeDir "python.exe")) {
    Add-Content -Path $LogFile -Value ('{"event":"runtime_download_end","status":"PASS","sha256":"' + $Hash + '","target_path":"runtime/python/windows/python.exe"}')
    exit 0
  } else {
    Add-Content -Path $LogFile -Value '{"event":"runtime_download_end","status":"FAIL","error_class":"PYTHON_EXE_NOT_FOUND_AFTER_EXTRACT","continue_path":"INSPECT_RUNTIME_DOWNLOAD"}'
    exit 20
  }
} catch {
  $Message = ($_.Exception.Message).Replace("\", "/").Replace('"', "'")
  Add-Content -Path $LogFile -Value ('{"event":"runtime_download_end","status":"FAIL","error_class":"PYTHON_RUNTIME_DOWNLOAD_FAILED","continue_path":"CHECK_NETWORK_OR_MANUAL_RUNTIME_INSTALL","repair_hint":"' + $Message + '"}')
  exit 20
}

# field normalization simulation v42

# field normalization simulation v43
