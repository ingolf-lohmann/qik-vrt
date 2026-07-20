<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# PYTHON_RUNTIME_BUNDLING_ATTEMPT_VOLATILE_CLASSIFICATION_GATE

## Fehlerklassen

```text
PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24_HASH_MISMATCH_AFTER_FIELD_RUN
RUNTIME_BUNDLING_ATTEMPT_STATE_FILE_HASHED_IMMUTABLE
PYTHON_RUNTIME_BUNDLING_ATTEMPT_IS_ENVIRONMENT_STATE_NOT_RELEASE_CONSTANT
MASTER_GATE_HASHES_RUNTIME_ATTEMPT_STATE_AS_IMMUTABLE
RUNTIME_STATE_CLASSIFICATION_INCOMPLETE
```

## Feldbefund

```text
FAIL hash mismatch runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json
```

## Regel

`runtime/*ATTEMPT*.json` und vergleichbare Runtime-State-Dateien sind volatile Runtime-State-Artefakte, solange ihre Unveränderlichkeit nicht ausdrücklich bewiesen ist.

q.e.d. Ingolf Lohmann
