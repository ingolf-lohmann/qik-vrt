<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Canonical Continue Primary Gate

Dieses Dokument manifestiert den wichtigsten Acceptance-Test eines kanonischen Repositories.

## Grundsatz

Ein kanonisches Repository darf nicht sterben; es muss den naechsten verantwortbaren Anschluss anbieten.

## Warum dies der Primaer-Gate ist

Alle anderen Gates koennen blockieren: Lizenz, Runtime, Hash, Plattform, Dokumentation, Tests, Usability, Provenienz.

Aber kein Gate darf zur Sackgasse werden.

Darum steht der Continue-Gate logisch ueber allen anderen Gates:

```text
CANONICAL_CONTINUE_PATH_PRIMARY_ACCEPTANCE_GATE
```

## Gueltige Blockierung

Eine Blockierung ist nur gueltig, wenn sie mindestens enthaelt:

```text
Fehlerklasse
Grund
Logfile
Evidence
Repair-Hint
Consent-Pfad
Lizenz-/Rechtekontext
Provenienzanforderung
naechste Handlung
Retry-/Rebuild-Pfad
Exit-Code
```

## Ungueltige Blockierung

```text
Fehler gefunden.
Ende.
```

ist fuer ein kanonisches Repository unzulaessig.

## QIK-VRT-Formel

```text
BLOCK ist kein Ende.
BLOCK ist ein Haltepunkt mit Anschlussbedingung.
```

q.e.d.  
Ingolf Lohmann
