<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# VOLATILE_RUNTIME_STATE_PERSISTED_IN_DELIVERY_ZIP_GATE

## Fehlerklassen

```text
VOLATILE_RUNTIME_STATE_MATERIALIZATION_NOT_PERSISTED_IN_DELIVERY_ZIP
MATERIALIZATION_GATE_ASSERTS_BEFORE_CREATING_REQUIRED_STUBS
DELIVERY_ZIP_MISSING_REGISTERED_VOLATILE_RUNTIME_STATE
VOLATILE_RUNTIME_STATE_FILE_NOT_VERIFIED_INSIDE_FINAL_ZIP
FIELD_PACKAGE_LOST_RUNTIME_DEPENDENCIES_JSON
```

## Feldbefund

```text
AssertionError: volatile runtime file missing: runtime/DEPENDENCIES.json
```

## Regel

Pflicht-Volatile-Runtime-State-Dateien müssen vor der Assertion idempotent materialisiert und zusätzlich im finalen ZIP nachgewiesen werden.

q.e.d. Ingolf Lohmann
