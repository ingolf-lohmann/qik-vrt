<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Runtime DEPENDENCIES.json Volatile Classification

V35 repariert den Feldfehler:

```text
FAIL hash mismatch runtime/DEPENDENCIES.json
```

`runtime/DEPENDENCIES.json` wird als Runtime-Dependency-State klassifiziert und aus `SHA256SUMS.txt` ausgeschlossen.

q.e.d. Ingolf Lohmann
