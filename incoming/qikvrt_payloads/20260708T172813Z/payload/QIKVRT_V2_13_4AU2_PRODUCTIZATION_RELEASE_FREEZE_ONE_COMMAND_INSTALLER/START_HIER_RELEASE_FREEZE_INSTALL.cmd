@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo QIKVRT V2.13.4AU2 Productization Release Freeze Installer
echo ============================================================
echo ASCII-only Windows CMD surface.
echo One command. Two repository-specific hidden token prompts.
echo No PowerShell. No .ps1. No Git in the Windows installer. No embedded token.
echo.
if not exist "tools\qikvrt_4au2_release_freeze_installer.js" (
  echo BLOCK missing tools\qikvrt_4au2_release_freeze_installer.js
  echo QIKVRT_CMD_EXIT=2
  exit /b 2
)
where cscript.exe >nul 2>nul
if errorlevel 1 (
  echo BLOCK cscript.exe not found or disabled
  echo QIKVRT_CMD_EXIT=3
  exit /b 3
)
cscript.exe //Nologo //E:JScript "tools\qikvrt_4au2_release_freeze_installer.js"
set "ec=%errorlevel%"
echo QIKVRT_CMD_EXIT=%ec%
exit /b %ec%
