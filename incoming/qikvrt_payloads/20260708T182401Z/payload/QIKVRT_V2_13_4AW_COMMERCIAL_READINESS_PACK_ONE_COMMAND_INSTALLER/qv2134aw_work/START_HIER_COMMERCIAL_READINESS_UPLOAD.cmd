@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo QIKVRT V2.13.4AW Commercial Readiness Pack Upload Installer
echo ==============================================================
echo ASCII-only Windows CMD surface.
echo One command. Two repository-specific hidden token prompts.
echo No PowerShell. No .ps1. No Git in the Windows installer. No embedded token.
echo.
if not exist "tools\qikvrt_4aw_uploader.js" (
  echo BLOCK missing tools\qikvrt_4aw_uploader.js
  echo QIKVRT_CMD_EXIT=2
  exit /b 2
)
where cscript.exe >nul 2>nul
if errorlevel 1 (
  echo BLOCK cscript.exe not found or disabled
  echo QIKVRT_CMD_EXIT=3
  exit /b 3
)
cscript.exe //Nologo //E:JScript "tools\qikvrt_4aw_uploader.js"
set ec=%ERRORLEVEL%
echo QIKVRT_CMD_EXIT=%ec%
exit /b %ec%
