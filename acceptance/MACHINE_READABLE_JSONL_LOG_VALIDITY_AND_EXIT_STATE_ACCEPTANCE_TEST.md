<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# MACHINE_READABLE_JSONL_LOG_VALIDITY_AND_EXIT_STATE_ACCEPTANCE_TEST

## Error classes

```text
JSONL_LOG_INVALID_ON_WINDOWS_PATHS
WINDOWS_PATH_BACKSLASHES_NOT_JSON_ESCAPED
RUN_END_STATUS_MISLEADING_FOR_NONZERO_EXIT
NONZERO_EXIT_WITHOUT_STDOUT_STDERR_CAPTURE
NONZERO_EXIT_WITHOUT_REPAIR_HINT
LOG_EXISTS_BUT_NOT_MACHINE_READABLE
```

## Rule

`logs/qikvrt_last_run.jsonl` must be valid JSON Lines. Windows paths must not be written as raw unescaped JSON strings. Non-zero exit codes must not be reported as DONE.

q.e.d. Ingolf Lohmann
