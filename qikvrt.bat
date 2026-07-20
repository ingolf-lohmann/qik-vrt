REM Copyright 2026 Ingolf Lohmann.
REM Licensed under the Apache License, Version 2.0 (the "License");
REM See LICENSES/Apache-2.0.txt.
REM delegates-to: qikvrt.cmd
REM required-token: DEFAULT_COMMAND=master-gate
@echo off
setlocal
echo QIK-VRT V22 BAT Launcher
echo Default command: master-gate
echo Logfile: %~dp0logs\qikvrt_last_run.jsonl
call "%~dp0qikvrt.cmd" %*
exit /b %ERRORLEVEL%
