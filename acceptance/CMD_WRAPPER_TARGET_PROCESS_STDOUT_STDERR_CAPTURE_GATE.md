<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# CMD_WRAPPER_TARGET_PROCESS_STDOUT_STDERR_CAPTURE_GATE

## Fehlerklassen

```text
CMD_WRAPPER_TARGET_FAILURE_WITHOUT_STDOUT_STDERR_EVIDENCE
PYTHON_TARGET_EXIT_1_WITHOUT_CAPTURED_STDOUT
PYTHON_TARGET_EXIT_1_WITHOUT_CAPTURED_STDERR
CMD_WRAPPER_LOSES_TARGET_PROCESS_ROOT_CAUSE
TARGET_PROCESS_RESULT_EVENT_MISSING_AFTER_COMMAND_START
```

## Feldbefund

V32-Feldtest:

```text
JSONL_PARSEABLE = PASS
ACCEPTANCE_BEFORE_EFFECT = PASS
COMMAND_START_JSON_ESCAPED = PASS
RUN_END = FAIL, exit_code=1, PYTHON_LAUNCHER_TARGET_FAILED
```

Es fehlte:

```text
target_process_result
stdout_tail
stderr_tail
stdout_file
stderr_file
```

q.e.d. Ingolf Lohmann
