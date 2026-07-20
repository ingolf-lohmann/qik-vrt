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

Die historische Bezeichnung „Akzeptanz“ meint hier ausschließlich die
Autorisierung eines konkreten externen Effekts durch die verantwortliche Person.
Sie ist keine zusätzliche Bedingung der
PolyForm-Noncommercial-1.0.0-, CC-BY-NC-ND-4.0- oder fortbestehenden
historischen Apache-2.0-Lizenz.

Lokale, folgenlose Prüfung, Hilfeausgabe, Konfigurationsvalidierung und
Dry-Run-Auswertung dürfen ohne Effektfreigabe stattfinden. Vor einem
Repository-Schreibvorgang, Push, Release, Download mit Ausführung oder einem
anderen externen Effekt muss die konkrete Freigabe maschinenlesbar gebunden und
persistiert sein.

```text
run_start
local_preflight
effect_authorization_required
run_end(status=CONTINUE_EFFECT_AUTHORIZATION_REQUIRED)
```

q.e.d. Ingolf Lohmann
