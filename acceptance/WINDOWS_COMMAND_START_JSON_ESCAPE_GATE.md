<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# WINDOWS_COMMAND_START_JSON_ESCAPE_GATE

## Fehlerklassen

```text
WINDOWS_COMMAND_PATH_NOT_JSON_ESCAPED_IN_COMMAND_START
CMD_ECHO_WRITES_RAW_WINDOWS_PATH_IN_JSON
COMMAND_START_JSONL_INVALID_ON_WINDOWS_RUNTIME_PATH
ACCEPTANCE_ORDER_PASS_BUT_LOG_MACHINE_READABILITY_FAIL
REGRESSION_TEST_CONTAINS_RAW_UNESCAPED_WINDOWS_STRING
```

Der Feldfehler ist ein JSONDecodeError durch rohe Windows-Backslashes in `command_start.command`.

q.e.d. Ingolf Lohmann
