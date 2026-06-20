<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# CMD Wrapper Target stdout/stderr Capture

V33 repariert den nächsten Feldfehler: Der Batch-Wrapper darf Zielprozessfehler nicht mehr als bloßen Sammelfehler verlieren.

## Regel

```text
Kein non-zero target exit ohne stdout/stderr evidence.
```

q.e.d. Ingolf Lohmann
