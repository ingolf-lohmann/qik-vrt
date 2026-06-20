<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Volatile Runtime State Persisted in Delivery ZIP

V40 repariert den wiederholten Feldfehler: `runtime/DEPENDENCIES.json` war registriert, aber im entpackten Paket nicht vorhanden.

V40 erzwingt:

```text
runtime/DEPENDENCIES.json
runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json
runtime/RUNTIME_DEPENDENCY_MANIFEST.json
```

als vorhandene, volatile, nicht immutable-gehashte Runtime-State-Dateien — und prüft zusätzlich das finale ZIP selbst.

q.e.d. Ingolf Lohmann
