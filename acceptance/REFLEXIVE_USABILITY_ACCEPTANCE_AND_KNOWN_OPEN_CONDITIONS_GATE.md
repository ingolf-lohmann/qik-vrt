<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# REFLEXIVE_USABILITY_ACCEPTANCE_AND_KNOWN_OPEN_CONDITIONS_GATE

## Fehlerklassen

```text
REFLEXIVE_USABILITY_ACCEPTANCE_FAILURE
FALSE_COMPLETE_REPAIR_CLAIM_WITH_KNOWN_OPEN_CONDITIONS
KNOWN_REMAINING_FIELD_CONFIRMATION_NOT_GATED
ARTIFACT_DELIVERY_WITH_UNRESOLVED_EXTERNAL_RELEASE_CONDITIONS
RUNTIME_BUNDLING_OPEN_BUT_ALL_REMAINING_ERRORS_CLAIMED_FIXED
LOCAL_GREEN_CLAIM_WITH_EXTERNAL_BLOCKERS_OPEN
```

## Regel

Ein Zustand darf nur dann grün genannt werden, wenn alle bekannten Restbedingungen bestanden sind.

Wenn bekannte Restbedingungen verbleiben, muss das Artefakt maschinenlesbar sagen:

```text
LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE
```

Nicht erlaubt:

```text
ALL_REMAINING_ERRORS_FIXED_UNQUALIFIED
FULLY_GREEN
GITHUB_RELEASE_DONE
SELF_CONTAINED_RUNTIME_DONE
```

q.e.d. Ingolf Lohmann
