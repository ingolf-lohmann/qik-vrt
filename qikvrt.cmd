@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "DEFAULT_COMMAND=master-gate"
set "ARGS=%*"
if "%ARGS%"=="" set "ARGS=%DEFAULT_COMMAND%"
set "LOG_DIR=%SCRIPT_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\qikvrt_last_run.jsonl"
set "STDOUT_FILE=%LOG_DIR%\target_stdout.txt"
set "STDERR_FILE=%LOG_DIR%\target_stderr.txt"
set "STATE_DIR=%SCRIPT_DIR%\state"
set "ACCEPTANCE_FILE=%STATE_DIR%\launcher_acceptance_record.json"
set "LOG_JSON_PATH=%LOG_FILE:\=/%"
set "ACCEPTANCE_JSON_PATH=%ACCEPTANCE_FILE:\=/%"
set "STDOUT_JSON_PATH=%STDOUT_FILE:\=/%"
set "STDERR_JSON_PATH=%STDERR_FILE:\=/%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%STATE_DIR%" mkdir "%STATE_DIR%"
> "%LOG_FILE%" echo {"event":"run_start","launcher":"qikvrt.cmd","logfile":"%LOG_JSON_PATH%","default_command":"%DEFAULT_COMMAND%","args":"%ARGS%"}

if /I "%ARGS%"=="accept" goto INTERACTIVE_ACCEPT
if /I "%ARGS%"=="--accept" goto INTERACTIVE_ACCEPT
if not exist "%ACCEPTANCE_FILE%" goto INTERACTIVE_ACCEPT
echo {"event":"acceptance_verified","status":"ACCEPTED","persisted":true,"acceptance_record":"%ACCEPTANCE_JSON_PATH%"}>> "%LOG_FILE%"
goto AFTER_ACCEPTANCE

:INTERACTIVE_ACCEPT
echo.
echo QIK-VRT LICENSE / AUTHORSHIP / EFFECT ACCEPTANCE
echo Urheber/Rechteinhaber: Ingolf Lohmann
echo Source Code: Apache-2.0
echo Non-source/docs/canon/audit/metadata: CC BY-NC-ND 4.0
echo Python Runtime Third-Party Area: Python Software Foundation License Version 2
echo.
echo Wirkung: Nach Akzeptanz darf dieses Skript master-gate, resolver, GitHub automation oder andere angeforderte Aktionen starten.
echo Ohne Akzeptanz wird keine Wirkung gestartet.
echo.
set /p USER_ACCEPT="Bitte JA eingeben, um Lizenz, Urheberschaft und Wirkung zu akzeptieren: "
if /I not "%USER_ACCEPT%"=="JA" if /I not "%USER_ACCEPT%"=="YES" (
  echo {"event":"acceptance_declined","status":"BLOCK","persisted":false,"error_class":"LICENSE_AUTHORSHIP_ACCEPTANCE_DECLINED_IMPORT_BLOCKED","continue_path":"USER_ACCEPTANCE_REQUIRED","repair_hint":"Run qikvrt.cmd again and type JA to accept before effect."}>> "%LOG_FILE%"
  echo {"event":"run_end","status":"BLOCK","exit_code":31,"error_class":"LICENSE_AUTHORSHIP_ACCEPTANCE_DECLINED_IMPORT_BLOCKED","continue_path":"USER_ACCEPTANCE_REQUIRED","repair_hint":"Acceptance required before any effect.","logfile":"%LOG_JSON_PATH%"}>> "%LOG_FILE%"
  exit /b 31
)
> "%ACCEPTANCE_FILE%" echo {"accepted":true,"accepted_by":"Ingolf Lohmann","accepted_text":"%USER_ACCEPT%","accepted_scope":"QIK-VRT V45 launcher execution before effect","source_code_license":"Apache-2.0","non_source_license":"CC-BY-NC-ND-4.0","python_runtime_third_party_license":"Python Software Foundation License Version 2","effect_acceptance":true}
echo {"event":"acceptance_persisted","status":"ACCEPTED","persisted":true,"acceptance_record":"%ACCEPTANCE_JSON_PATH%","accepted_text":"%USER_ACCEPT%"}>> "%LOG_FILE%"
if /I "%ARGS%"=="accept" (
  echo {"event":"run_end","status":"PASS","exit_code":0,"error_class":"NONE","continue_path":"NONE","repair_hint":"NONE","logfile":"%LOG_JSON_PATH%"}>> "%LOG_FILE%"
  exit /b 0
)
if /I "%ARGS%"=="--accept" (
  echo {"event":"run_end","status":"PASS","exit_code":0,"error_class":"NONE","continue_path":"NONE","repair_hint":"NONE","logfile":"%LOG_JSON_PATH%"}>> "%LOG_FILE%"
  exit /b 0
)

:AFTER_ACCEPTANCE
set "PY_EXE="
set "PY_EXE_JSON="
call :TRY_PY "%SCRIPT_DIR%\runtime\python\windows\python.exe"
if defined PY_EXE goto PY_READY
call :TRY_PY "%SCRIPT_DIR%\python\python.exe"
if defined PY_EXE goto PY_READY
call :TRY_PY "py"
if defined PY_EXE goto PY_READY
call :TRY_PY "python"
if defined PY_EXE goto PY_READY
call :TRY_PY "python3"
if defined PY_EXE goto PY_READY

echo {"event":"runtime_unusable","status":"CONTINUE","exit_code":20,"error_class":"PYTHON_RUNTIME_NOT_FOUND_OR_NOT_EXECUTABLE","continue_path":"RESOLVE_OR_BUNDLE_EXECUTABLE_PYTHON_RUNTIME","repair_hint":"Install Python or provide runtime/python/windows/python.exe.","stdout_file":"%STDOUT_JSON_PATH%","stderr_file":"%STDERR_JSON_PATH%"}>> "%LOG_FILE%"
echo {"event":"target_process_result","status":"FAIL","command":"PYTHON_INTERPRETER_PROBE","exit_code":20,"stdout_file":"%STDOUT_JSON_PATH%","stderr_file":"%STDERR_JSON_PATH%","stdout_tail":"","stderr_tail":"No usable Python interpreter found after acceptance.","error_class":"PYTHON_RUNTIME_NOT_FOUND_OR_NOT_EXECUTABLE","continue_path":"RESOLVE_OR_BUNDLE_EXECUTABLE_PYTHON_RUNTIME","repair_hint":"Install Python or provide runtime/python/windows/python.exe."}>> "%LOG_FILE%"
echo {"event":"run_end","status":"CONTINUE","exit_code":20,"error_class":"PYTHON_RUNTIME_NOT_FOUND_OR_NOT_EXECUTABLE","continue_path":"RESOLVE_OR_BUNDLE_EXECUTABLE_PYTHON_RUNTIME","repair_hint":"Install Python or provide runtime/python/windows/python.exe.","logfile":"%LOG_JSON_PATH%"}>> "%LOG_FILE%"
exit /b 20

:PY_READY
echo {"event":"interpreter_probe","status":"PASS","python":"%PY_EXE_JSON%"}>> "%LOG_FILE%"
set "COMMAND_JSON=%PY_EXE_JSON% qikvrt.py %ARGS%"
echo {"event":"command_start","command":"%COMMAND_JSON%"}>> "%LOG_FILE%"
"%PY_EXE%" "%SCRIPT_DIR%\tools\qikvrt_cmd_target_runner.py" --log "%LOG_FILE%" --stdout-file "%STDOUT_FILE%" --stderr-file "%STDERR_FILE%" --cwd "%SCRIPT_DIR%" -- "%PY_EXE%" "%SCRIPT_DIR%\qikvrt.py" %ARGS%
set "EXITCODE=%ERRORLEVEL%"
if "%EXITCODE%"=="9009" (
  echo {"event":"target_process_result","status":"FAIL","command":"%COMMAND_JSON%","exit_code":9009,"stdout_file":"%STDOUT_JSON_PATH%","stderr_file":"%STDERR_JSON_PATH%","stdout_tail":"","stderr_tail":"Interpreter or target runner command failed with 9009.","error_class":"CMD_WRAPPER_EXIT_9009_WITHOUT_TARGET_PROCESS_RESULT","continue_path":"REPAIR_INTERPRETER_OR_TARGET_RUNNER_INVOCATION","repair_hint":"Verify selected Python executable and qikvrt_cmd_target_runner.py path."}>> "%LOG_FILE%"
)
if "%EXITCODE%"=="0" (
  echo {"event":"cmd_wrapper_end","status":"PASS","exit_code":0}>> "%LOG_FILE%"
  echo {"event":"run_end","status":"PASS","exit_code":0,"error_class":"NONE","continue_path":"NONE","repair_hint":"NONE","logfile":"%LOG_JSON_PATH%"}>> "%LOG_FILE%"
) else (
  echo {"event":"cmd_wrapper_end","status":"FAIL","exit_code":%EXITCODE%,"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_TARGET_PROCESS_RESULT","repair_hint":"Inspect target_process_result, target_stdout.txt and target_stderr.txt."}>> "%LOG_FILE%"
  echo {"event":"run_end","status":"FAIL","exit_code":%EXITCODE%,"error_class":"PYTHON_LAUNCHER_TARGET_FAILED","continue_path":"INSPECT_TARGET_PROCESS_RESULT","repair_hint":"Inspect target_process_result, target_stdout.txt and target_stderr.txt.","logfile":"%LOG_JSON_PATH%"}>> "%LOG_FILE%"
)
exit /b %EXITCODE%

:TRY_PY
set "CAND=%~1"
if not exist "%CAND%" (
  if /I not "%CAND%"=="py" if /I not "%CAND%"=="python" if /I not "%CAND%"=="python3" goto :EOF
)
"%CAND%" -c "import sys; raise SystemExit(0)" >nul 2>nul
set "PROBE_CODE=%ERRORLEVEL%"
set "CAND_JSON=%CAND:\=/%"
echo {"event":"interpreter_probe_candidate","candidate":"%CAND_JSON%","exit_code":%PROBE_CODE%}>> "%LOG_FILE%"
if "%PROBE_CODE%"=="0" (
  set "PY_EXE=%CAND%"
  set "PY_EXE_JSON=%CAND_JSON%"
)
goto :EOF
