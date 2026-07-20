@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem Copyright 2026 Ingolf Lohmann.
rem SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
rem The Python launcher is the single authority for authorization-before-effect.

set "SCRIPT_DIR=%~dp0"
set "PY_EXE="
set "PY_ARGS="

if exist "%SCRIPT_DIR%runtime\python\windows\python.exe" (
  "%SCRIPT_DIR%runtime\python\windows\python.exe" -c "import sys; raise SystemExit(0)" >nul 2>nul
  if not errorlevel 1 set "PY_EXE=%SCRIPT_DIR%runtime\python\windows\python.exe"
)
if not defined PY_EXE if exist "%SCRIPT_DIR%python\python.exe" (
  "%SCRIPT_DIR%python\python.exe" -c "import sys; raise SystemExit(0)" >nul 2>nul
  if not errorlevel 1 set "PY_EXE=%SCRIPT_DIR%python\python.exe"
)
if not defined PY_EXE (
  py -3 -c "import sys; raise SystemExit(0)" >nul 2>nul
  if not errorlevel 1 (
    set "PY_EXE=py"
    set "PY_ARGS=-3"
  )
)
if not defined PY_EXE (
  python -c "import sys; raise SystemExit(0)" >nul 2>nul
  if not errorlevel 1 set "PY_EXE=python"
)

if not defined PY_EXE (
  echo BLOCK: Python 3 was not found. Install Python 3 or provide runtime\python\windows\python.exe. 1>&2
  exit /b 20
)

if "%~1"=="" (
  "%PY_EXE%" %PY_ARGS% "%SCRIPT_DIR%qikvrt.py" master-gate
) else (
  "%PY_EXE%" %PY_ARGS% "%SCRIPT_DIR%qikvrt.py" %*
)
exit /b %ERRORLEVEL%
