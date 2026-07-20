@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo.
echo QIKVRT V2.13.4AO Generic Payload GitHub Upload Kit
echo =====================================================
echo.
echo ASCII-only Windows CMD surface.
echo No .ps1 execution. No PowerShell -File. No Git. No embedded token.
echo Uses cscript/JScript + GitHub Contents API.
echo No remote mutation without explicit consent.
echo.

if not exist "tools\qikvrt_upload_wsh.js" (
  echo QIKVRT_BOOTSTRAP BLOCK missing tools\qikvrt_upload_wsh.js
  echo QIKVRT_CMD_EXIT=2
  exit /b 2
)

where cscript.exe >nul 2>nul
if errorlevel 1 (
  echo QIKVRT_BOOTSTRAP BLOCK cscript.exe not found or disabled
  echo QIKVRT_CMD_EXIT=3
  exit /b 3
)

cscript.exe //Nologo //E:JScript "tools\qikvrt_upload_wsh.js"
set "ec=%ERRORLEVEL%"
echo QIKVRT_CMD_EXIT=%ec%
exit /b %ec%
