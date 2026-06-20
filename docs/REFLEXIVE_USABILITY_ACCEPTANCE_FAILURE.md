<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Reflexive Usability Acceptance Failure

V27 repariert die reflexive Fehlerklasse, dass eine Lieferung lokale Gates bestand, aber bekannte offene Bedingungen weiter enthielt.

## Kernregel

```text
Local pass ist nicht automatisch global green.
```

Bekannte offene Bedingungen muessen als Gate-Zustand geführt werden:

```text
CONTINUE
BLOCK
EXTERNAL_EVIDENCE_REQUIRED
DEPENDENCY_RUNTIME_OPEN
```

Erst wenn `KNOWN_OPEN_CONDITIONS = 0` oder der Freigabeumfang maschinenlesbar begrenzt ist, darf eine Abschlussaussage erfolgen.

q.e.d. Ingolf Lohmann
