<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Assistant Delivery Response Consistency

V28 erweitert die Prüfung auf die Antwortschicht.

Das Repository kann korrekt sein und die Auslieferungsantwort trotzdem falsch. Genau dieser Reflexionsfehler wird hier gesperrt.

## Kernregel

```text
Die Antwort selbst ist Teil des Acceptance-Pfades.
```

Wenn bekannte offene Bedingungen verbleiben, darf nicht formuliert werden:

```text
behoben
grün
fertig
done
alle Fehler beseitigt
```

sondern nur:

```text
LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE
```

q.e.d. Ingolf Lohmann
