<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# VOLATILE_RUNTIME_STATE_MATERIALIZATION_GATE

## Fehlerklassen

```text
VOLATILE_RUNTIME_FILE_REGISTERED_BUT_NOT_MATERIALIZED
RUNTIME_DEPENDENCIES_JSON_DECLARED_VOLATILE_BUT_MISSING
RUNTIME_STATE_REGISTRY_CONTAINS_NONEXISTENT_FILE
VOLATILE_FILE_POLICY_WITHOUT_PAYLOAD_MATERIALIZATION
WINDOWS_SHORT_PACKAGE_DROPPED_REQUIRED_RUNTIME_STATE_FILE
```

## Feldbefund

```text
AssertionError: volatile runtime file missing: runtime/DEPENDENCIES.json
```

## Regel

Jede als vorhanden registrierte volatile Runtime-State-Datei muss im Paket tatsächlich materialisiert sein.

q.e.d. Ingolf Lohmann
