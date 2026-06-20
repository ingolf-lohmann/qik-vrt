<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Runtime Attempt State Volatile Classification

V37 repariert den Feldfehler aus V36:

```text
FAIL hash mismatch runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json
```

Nicht nur diese eine Datei, sondern alle passenden Runtime-Attempt-/State-/Dependency-Dateien werden als volatile Runtime-State klassifiziert und aus dem immutable Hashmanifest ausgeschlossen.

q.e.d. Ingolf Lohmann
