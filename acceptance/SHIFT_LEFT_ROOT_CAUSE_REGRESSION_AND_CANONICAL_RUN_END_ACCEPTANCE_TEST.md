<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# SHIFT_LEFT_ROOT_CAUSE_REGRESSION_AND_CANONICAL_RUN_END_ACCEPTANCE_TEST

## Fehlerklassen

```text
CANONICAL_RUN_END_EVENT_MISSING
WRAPPER_END_WITHOUT_RUN_END
PYTHON_LAUNCHER_TARGET_FAILED_WITHOUT_CANONICAL_FINALIZATION
SHIFT_LEFT_REGRESSION_GATE_MISSING
MANUAL_FIELD_TEST_REQUIRED_TO_FIND_BASIC_LAUNCHER_ERROR
USABILITY_ITERATION_LOOP_NOT_CLOSED
CI_DEVOPS_SHIT_LEFT_INSTEAD_OF_SHIFT_LEFT
UNBOUNDED_SUBPROCESS_IN_MASTER_GATE
IMPLICIT_PYTHON_PACKAGE_IMPORT_IN_HARNESS
```

Jeder Launcher und Adapter muss immer genau ein kanonisches finales `run_end` schreiben.  
Ein Fehler gilt erst als repariert, wenn sein Rückfall vor Auslieferung automatisch blockiert wird.

q.e.d. Ingolf Lohmann
