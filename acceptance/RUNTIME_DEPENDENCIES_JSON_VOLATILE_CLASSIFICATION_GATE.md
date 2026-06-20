<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# RUNTIME_DEPENDENCIES_JSON_VOLATILE_OR_IMMUTABLE_CLASSIFICATION_GATE

## Fehlerklassen

```text
RUNTIME_DEPENDENCIES_JSON_HASH_MISMATCH_AFTER_FIELD_RUN
RUNTIME_DEPENDENCIES_MANIFEST_MUTABLE_BUT_HASHED_IMMUTABLE
DEPENDENCY_STATE_FILE_INCLUDED_IN_IMMUTABLE_SHA256SUMS
MASTER_GATE_HASHES_RUNTIME_DEPENDENCY_STATE_AS_RELEASE_CONSTANT
DEPENDENCIES_JSON_MUST_BE_POLICY_OR_VOLATILE_SEPARATED
```

## Feldbefund

`target_stderr(1).txt` zeigt:

```text
FAIL hash mismatch runtime/DEPENDENCIES.json
```

## Regel

`runtime/DEPENDENCIES.json` darf nicht zugleich Laufzeit-/Umgebungszustand und immutable Release-Konstante sein.

q.e.d. Ingolf Lohmann
