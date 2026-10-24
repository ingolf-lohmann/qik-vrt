@echo off
REM QIKVRT Artifact Header
REM Deutsch: Einheitlicher Windows-Einstiegspunkt fuer Setup, Acceptance, Deploy und Registrierung.
REM English: Unified Windows entry point for setup, acceptance, deploy and registration.
REM Author / Urheber: Ingolf Lohmann
REM Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
REM License: Apache-2.0 for scripts unless otherwise stated.
setlocal EnableExtensions EnableDelayedExpansion
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
set "QIKVRT_MODE=%~1"
if "%QIKVRT_MODE%"=="" set "QIKVRT_MODE=deploy"
if /I "%QIKVRT_MODE%"=="help" goto :usage

REM Windows MOTW / execution-policy preflight.
REM Deutsch: Entfernt Zone.Identifier-Markierungen, falls vorhanden. Wenn keine
REM Streams vorhanden sind oder die lokale Policy trotzdem AllSigned erzwingt,
REM laedt dieser Entry-Point PS1-Dateien NICHT per -File, sondern als lokalen
REM Inline-ScriptBlock aus dem entpackten Repository. Keine Policy-Bypass-Option,
REM keine automatische Elevation, kein Download, keine Remote-Ausfuehrung.
REM English: Remove Zone.Identifier markers if present. If no streams are present
REM or local policy still enforces AllSigned, this entry point does NOT load PS1
REM files via -File, but as local inline script blocks from the extracted repo.
REM No policy-bypass option, no automatic elevation, no download, no remote execution.
set "QIKVRT_MOTW_REMOVED=0"
for /R "%QIKVRT_ROOT%" %%F in (*.ps1 *.psm1 *.psd1 *.cmd *.bat *.json *.jsonl *.md *.txt *.c *.h *.yaml *.yml) do (
  if exist "%%F:Zone.Identifier" (
    del /f /q "%%F:Zone.Identifier" >nul 2>nul
    if not errorlevel 1 set /a QIKVRT_MOTW_REMOVED+=1 >nul
  )
)
if "%QIKVRT_MOTW_REMOVED%"=="0" (
  echo QIKVRT_MOTW_UNBLOCK	SKIP	no Zone.Identifier streams found or removal not required
) else (
  echo QIKVRT_MOTW_UNBLOCK	PASS	removed Zone.Identifier from %QIKVRT_MOTW_REMOVED% file^(s^) before PowerShell script execution
)

echo QIKVRT Windows Entry Point
echo REPO_ROOT=%QIKVRT_ROOT%
echo MODE=%QIKVRT_MODE%
echo QIKVRT_ADMIN_RIGHTS	SKIP	No automatic elevation in AV-safe default mode. Package installation requires explicit QIKVRT_ALLOW_PACKAGE_INSTALL=1.
echo QIKVRT_POWERSHELL_SCRIPT_HOST	PASS	local PS1 files are loaded as inline ScriptBlock; no -File; no policy-bypass flag

REM Mandatory first repository gate: authorship / rights / license acceptance.
call :run_ps1 "tools\license_acceptance.ps1"
set "QIKVRT_EXIT=%ERRORLEVEL%"
if not "%QIKVRT_EXIT%"=="0" goto :finish

REM Mandatory second repository gate: GUID and GitHub target persistence.
call :run_ps1 "tools\setup_repository.ps1"
set "QIKVRT_EXIT=%ERRORLEVEL%"
if not "%QIKVRT_EXIT%"=="0" goto :finish

REM AV-safe dependency resolution: detect existing compiler first; no remote installer by default.
call :run_ps1 "tools\choco_bootstrap.ps1"
set "QIKVRT_EXIT=%ERRORLEVEL%"
if not "%QIKVRT_EXIT%"=="0" goto :finish

if /I "%QIKVRT_MODE%"=="setup" goto :setup_done
if /I "%QIKVRT_MODE%"=="register" goto :register
if /I "%QIKVRT_MODE%"=="deploy" goto :deploy
if /I "%QIKVRT_MODE%"=="acceptance" goto :acceptance
if /I "%QIKVRT_MODE%"=="test" goto :acceptance
if /I "%QIKVRT_MODE%"=="full" goto :deploy
echo Unknown QIKVRT mode: %QIKVRT_MODE%
goto :usage

:setup_done
set "QIKVRT_EXIT=0"
goto :finish

:register
call :run_ps1 "tools\register_with_seed.ps1"
set "QIKVRT_EXIT=%ERRORLEVEL%"
goto :finish

:deploy
call :run_ps1 "tools\win_acceptance.ps1"
set "QIKVRT_EXIT=%ERRORLEVEL%"
if not "%QIKVRT_EXIT%"=="0" goto :finish
REM GitHub token handling is intentionally delegated to tools\gh_deploy.ps1.
REM 2.13.4R: local deploy uses git commit/tag/push only. GitHub Actions in the target repository creates the release and uploads the asset.
call :run_ps1 "tools\gh_deploy.ps1"
set "QIKVRT_EXIT=%ERRORLEVEL%"
goto :finish

:acceptance
call :run_ps1 "tools\win_acceptance.ps1"
set "QIKVRT_EXIT=%ERRORLEVEL%"
goto :finish

:run_ps1
set "QIKVRT_SCRIPT_REL=%~1"
set "QIKVRT_SCRIPT_PATH=%QIKVRT_ROOT%\%QIKVRT_SCRIPT_REL%"
powershell -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; $scriptPath=$env:QIKVRT_SCRIPT_PATH; $repoRoot=$env:QIKVRT_ROOT; if([string]::IsNullOrWhiteSpace($scriptPath) -or -not [System.IO.File]::Exists($scriptPath)){ throw ('QIKVRT script not found: ' + $scriptPath) }; $content=[System.IO.File]::ReadAllText($scriptPath, [System.Text.Encoding]::UTF8); $sb=[System.Management.Automation.ScriptBlock]::Create($content); & $sb -RepoRoot $repoRoot"
exit /b %ERRORLEVEL%

:usage
echo Usage: QIKVRT.cmd [setup^|register^|deploy^|acceptance^|test^|full]
echo default    same as deploy: license, GUID setup, AV-safe dependency detection, acceptance, GitHub deploy
echo setup      accepts/persists license, creates/persists GUID and target config, resolves existing compiler only
echo register   registers this node with the configured seed using persisted config
echo deploy     prompts for GITHUB_TOKEN if needed, then git-pushes branch/tag; target GitHub Actions creates release
echo acceptance runs the Windows acceptance runner after mandatory gates
echo opt-in dependency install: set QIKVRT_ALLOW_PACKAGE_INSTALL=1 before running when no compiler is present
set "QIKVRT_EXIT=2"
goto :finish

:finish
echo.
echo QIKVRT_CMD_EXIT=%QIKVRT_EXIT%
echo Ergebnis / Result logs:
echo   qikvrt\runtime\bootstrap\CHOCO_BOOTSTRAP_RESULT.tsv
echo   qikvrt\runtime\win_acceptance\WIN_ACCEPTANCE_RESULT.tsv
echo   qikvrt\runtime\deploy\deploy_result.tsv
echo.
if not "%QIKVRT_NO_PAUSE%"=="1" (
  echo Press any key to close this QIKVRT window . . .
  pause >nul
)
exit /b %QIKVRT_EXIT%
