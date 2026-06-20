<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Root-Cause Logging and Volatile Runtime Separation

V26 beseitigt den Restfehler `PYTHON_LAUNCHER_TARGET_FAILED` als blinden Sammelfehler.

Zusätzlich wird der gefundene Root-Cause beseitigt:

```text
logs/qikvrt_last_run.jsonl wurde als statische SHA256SUMS-Datei behandelt,
obwohl der Launcher diese Datei beim Lauf verändert.
```

Das ist falsch. Runtime-Logs sind volatile Evidence, keine unveränderlichen Paketdateien.

q.e.d. Ingolf Lohmann
