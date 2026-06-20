<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# INITIAL_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT_GATE

## Fehlerklassen

```text
BATCH_START_WITHOUT_INITIAL_ACCEPTANCE_GATE
LAUNCHER_CONTINUES_BEFORE_ACCEPTANCE_PERSISTED
INITIAL_ACCEPTANCE_NOT_PERSISTED_BEFORE_EFFECT
POST_START_ACTIVITY_WITHOUT_PRODUCT_OWNER_ACCEPTANCE
REFLEXIVE_ACCEPTANCE_GATE_BYPASSED_BY_LAUNCHER
ACCEPTANCE_REQUIRED_BEFORE_ANY_EFFECT_NOT_ENFORCED
```

Nach Batch-/Launcher-Start darf kein weiterer Wirkpfad laufen, bevor die Akzeptanz maschinenlesbar vorhanden und persistiert ist.

Ohne Akzeptanz darf nur passieren:

```text
run_start
acceptance_required
run_end(status=CONTINUE_ACCEPTANCE_REQUIRED)
```

q.e.d. Ingolf Lohmann
