@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Copyright 2026 Ingolf Lohmann.
rem SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
rem Both Windows frontends consume the same locked offline bootstrap.
set "SCRIPT_DIR=%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%SCRIPT_DIR%qikvrt.ps1" %*
exit /b %ERRORLEVEL%
