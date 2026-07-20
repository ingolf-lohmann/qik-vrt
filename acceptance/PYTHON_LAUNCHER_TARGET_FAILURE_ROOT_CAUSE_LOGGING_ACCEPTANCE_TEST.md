<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# PYTHON_LAUNCHER_TARGET_FAILURE_ROOT_CAUSE_LOGGING_ACCEPTANCE_TEST

## Fehlerklassen

```text
PYTHON_LAUNCHER_TARGET_FAILED_WITHOUT_STDOUT_STDERR
TARGET_PROCESS_FAILURE_WITHOUT_ROOT_CAUSE_EVIDENCE
MASTER_GATE_FAILURE_NOT_DIAGNOSED
REMAINING_ERROR_NOT_SHIFT_LEFT_BLOCKED
COLLECTOR_ERROR_CLASS_WITHOUT_UNDERLYING_CAUSE
VOLATILE_LOG_INCLUDED_IN_IMMUTABLE_HASH_MANIFEST
MASTER_GATE_FAILS_AFTER_OWN_LOG_MUTATION
PASS_RUN_END_MISSING_CANONICAL_FIELDS
```

Ein Sammelfehler ist keine Ursachenanalyse.  
PASS und FAIL müssen dieselbe kanonische `run_end`-Feldstruktur besitzen.  
Runtime-Logs sind volatile Evidence und dürfen nicht in `SHA256SUMS` eingefroren werden.

q.e.d. Ingolf Lohmann
