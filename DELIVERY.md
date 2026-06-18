<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# DELIVERY

## Delivery-UX-Regel

Unnötige technische Details werden unter `_internal/` verdeckt.

Die Startdateien liegen sichtbar im Root.

Die Log- und Ergebnisdateien liegen sichtbar in `LOGS/`, also direkt neben den Startdateien.

## Sichtbare Ebene

```text
START.bat
RUN.ps1
RUN.sh
LINUX.sh
START.command
README.md
LOGS/
```

## Interne Ebene

```text
_internal/
```

## Payload

```text
_payload/REPO.zip
_payload/BASE.zip
```

## MinRoot-Ergänzung

Die sichtbare Root-Ebene enthält keine README und keine Hilfsskripte mehr, sondern nur drei Plattformskripte.

## Payload/Internal-Korrektur

`_internal/` liegt nun unter `_payload/_internal/`. Root enthält `README.md` und `QALL.ini`.
