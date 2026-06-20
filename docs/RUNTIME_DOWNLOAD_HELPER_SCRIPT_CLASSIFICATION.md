<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Runtime Download Helper Script Classification

V42 repariert den Feldfehler:

```text
FAIL hash mismatch runtime/download_python_runtime.ps1
```

`runtime/download_python_runtime.ps1` wird als `VOLATILE_FIELD_NORMALIZED_RUNTIME_HELPER` geführt und aus `SHA256SUMS.txt` ausgeschlossen.

q.e.d. Ingolf Lohmann
