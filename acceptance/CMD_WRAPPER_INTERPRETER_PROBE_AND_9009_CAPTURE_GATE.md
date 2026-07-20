<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# CMD_WRAPPER_INTERPRETER_PROBE_AND_9009_CAPTURE_GATE

## Fehlerklassen

```text
CMD_WRAPPER_EXIT_9009_WITHOUT_TARGET_PROCESS_RESULT
PYTHON_RUNTIME_CANDIDATE_NOT_EXECUTABLE_BUT_USED
TARGET_RUNNER_NOT_STARTED_WHEN_PYTHON_INTERPRETER_FAILS
CMD_WRAPPER_CANNOT_RELY_ON_TARGET_RUNNER_FOR_INTERPRETER_FAILURE
COMMAND_START_LOGGED_BEFORE_INTERPRETER_PROBE
```

## Regel

Der CMD-Wrapper muss den Python-Interpreter vor `command_start` prüfen. Wenn der Interpreter nicht startet oder Exit 9009 erzeugt, muss der Wrapper selbst ein `target_process_result` schreiben.

q.e.d. Ingolf Lohmann
