<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# ASSISTANT_DELIVERY_RESPONSE_CONSISTENCY_GATE

## Fehlerklassen

```text
ASSISTANT_DELIVERY_TEXT_CONTRADICTS_OWN_KNOWN_OPEN_CONDITIONS_GATE
UNQUALIFIED_FIXED_CLAIM_WITH_OPEN_CONDITIONS
DELIVERY_RESPONSE_NOT_MACHINE_CHECKED_AGAINST_VERDICT
FINAL_ANSWER_BYPASSED_REPOSITORY_CLAIM_GATE
RESPONSE_LAYER_NOT_PART_OF_ACCEPTANCE_SCOPE
```

## Regel

Wenn `overall_green=false` oder `known_open_condition_count>0`, darf die Auslieferungsantwort keine unqualifizierte Abschlussbehauptung enthalten.

Verboten bei offenen Bedingungen:

```text
der Fehler wurde behoben
alle restlichen Fehler beseitigt
vollständig grün
fertig
done
```

Erlaubt ist nur:

```text
LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE
```

q.e.d. Ingolf Lohmann
