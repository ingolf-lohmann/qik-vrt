<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidence boundary

## Status

```text
PASS_WITH_EXPLICIT_BOUNDARIES
```

Dieser Status ist kein globales Gütesiegel. Er gilt nur für die nachfolgend
benannten Evidenzobjekte, Prüfverfahren und Anspruchsgrenzen.

## Direkt belegt

### Öffentliche Persistenz

- Das Working Paper ist unter [DOI
  10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773)
  veröffentlicht.
- Der versionierte Software-Snapshot ist unter [DOI
  10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774)
  veröffentlicht.
- Revision `-01` des EFFECT_ACK-Internet-Drafts ist im [IETF
  Datatracker](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/01/)
  als aktiver Internet-Draft mit Intended Status Experimental ausgewiesen und
  im [IETF-Archiv](https://www.ietf.org/archive/id/draft-lohmann-qikvrt-effect-ack-01.html)
  abrufbar.
- Die beiden veröffentlichten Repository-Tags benennen die versionierten
  Quellen in [Goldkelch/qik-vrt](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
  und [ingolf-lohmann/qik-vrt](https://github.com/ingolf-lohmann/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0).

DOI-Auflösung, Datenträgerverfügbarkeit, Git-Referenzen und Hashgleichheit sind
verschiedene Eigenschaften. Die Veröffentlichungsprüfung hat sie getrennt
behandelt. Keine davon allein beweist die wissenschaftliche Wahrheit des
Inhalts.

### Endliche Modellprüfung

Im veröffentlichten Prüfmodell sind exhaustiv geprüft:

- 19 boolesche Modellmerkmale und fünf Verbindungsentscheidungen;
- 2.621.440 Zustandsbelegungen;
- 5.242.880 Kombinationen mit gültiger oder ungültiger
  Verbraucherzulassung;
- Totalität und Erreichbarkeit der fünf modellierten Zustände;
- gewöhnliche Freigabe nur bei `EFFECT_ACK_DONE`;
- Prioritätsorakel, gezielte Prioritätskollisionen und die 17
  Core-Done-Konjunkte;
- kleine Repository-, Faktorisierungs- und Inversionsmodelle in den im
  Working Paper ausgewiesenen endlichen Domänen.

Die maßgeblichen Einzelheiten und reproduzierbaren Dateien gehören zum
[veröffentlichten Working-Paper-Bündel](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0/docs/publications/2026-07-22-effect-ack-universal-effect-control).

### Mathematische Anspruchsgrenze

Für `E:S -> O` und `sigma:S -> T` ist eine Rekonstruktion `h` auf dem Bild von
`E` mit `sigma = h o E` genau dann wohldefiniert, wenn

```text
E(s1) = E(s2)  =>  sigma(s1) = sigma(s2).
```

Dies ist ein Faktorisierungskriterium. Es ist weder die Behauptung, dass die
Bedingung für jede gewünschte Semantik erfüllt ist, noch dass `h` in jedem Fall
effektiv berechenbar oder rechtmäßig zugänglich ist. Exakte historische
Inversion verlangt Injektivität auf der betrachteten Ursprungsmenge.

Die veröffentlichte Formalisierung enthält 37 typisierte Claims, darunter 19
`PROVED`, fünf `PROVED_CONDITIONAL` und drei `OPEN_EMPIRICAL`. Dokumentiert
sind 118 Lean-Deklarationen ohne Fehler oder ungeprüfte Proof-Escapes,
TypeScript Gate 20 mit 18/18, Python Gate 20 mit 18/18, pytest mit 5/5 und drei
von drei zurückgewiesene Überbehauptungen. Diese Zählungen belegen den
angegebenen Formalisierungsstand, nicht die Vollständigkeit der Mathematik
oder Physik.

### Physik-, Universums- und Quantengrenze

- Ein gewählter Grundbereich `U` und sein relatives Komplement sind ein
  mathematisches Modellobjekt. Die Gleichsetzung eines Modelluniversums mit
  dem empirischen Kosmos bleibt offen.
- Dimensionshomogenität und Planck-Kombinationen liefern notwendige
  Konsistenzbedingungen, aber keinen Nachweis ontischer Raumzeitquantisierung
  oder einer neuen Quantengravitation.
- Im definierten autonomen Vorwärtsmodell ist ein No-Backward-Channel-Satz
  formalisiert. Er ist kein Experiment zum Nachweis physischer
  Retrokausalität oder eines steuerbaren Rückwärtskanals.
- Der Quantencomputing-Bezug hat den Status
  `CONCEPTUAL_ONLY / NOT_IMPLEMENTED`. Es gibt im verankerten Stand keine
  Quantenschaltung, kein Quanten-Backend, keine Geräteausführung und keinen
  Quantenbenchmark.

## Konditional

Folgende Aussagen gelten nur, wenn ihre Voraussetzungen außerhalb des
endlichen Kernmodells gesondert nachgewiesen sind:

- vollständige Mediation jedes gewöhnlichen geschützten Wirkungspfads;
- schema-valide, authentisierte, frische und kettenvalide
  Verbraucherzulassung;
- korrekte Neuberechnung der Policy- und Evidenzbindungen;
- treue Ausführung nach der digitalen Freigabe;
- zutreffende Hardware-, Sensor-, Aktor- und Fehlermodelle;
- empirische Validierung des konkreten Einsatzsystems;
- ausreichende Ressourcen, Berechenbarkeit und autorisierter Zugriff.

## Nicht belegt

- eine positive Totalisierungs- oder Vollständigkeitsgarantie für beliebige
  Eingaben, Programme, Semantiken, Ursprünge oder physikalische Systeme;
- ein universeller semantischer oder historischer Decoder;
- Erzeugung verlorener oder nie beobachteter Information;
- garantierte Terminierung oder ein späteres `EFFECT_ACK_DONE`;
- Lösung des Halteproblems oder der allgemeinen Rice-Unentscheidbarkeit;
- vollständige Draft-01-Wire-Konformität der gegenwärtigen Python-Runtime;
- unabhängige Interoperabilität oder unabhängige Replikation;
- Nichtumgehbarkeit, Funktionssicherheit oder Gefahrlosigkeit eines konkreten
  Produktionssystems;
- eine vollständige Rekonstruktion der Informatik, Mathematik, Physik oder des
  bekannten Universums;
- ontische Raumzeitquantisierung, neue Quantengravitation, physische
  Retrokausalität oder kontrollierbare Rückwärtssignalisierung;
- ein implementierter Quantenalgorithmus, Quantencomputer oder
  Quantenhardware-Mapping;
- eine vollständige Ableitung sämtlicher Logik oder die Reduktion
  metaphysischer beziehungsweise spiritueller Wahrheit auf ein formales
  System oder Naturtheorem;
- IETF-Konsens, RFC-Status, Peer Review, Zertifizierung oder externe Adoption;
- Patentanmeldung, Patenterteilung, Priorität, Patentierbarkeit, Freedom to
  Operate, Rechtsbeständigkeit oder Nichtverletzung fremder Rechte.

## Abgeleitete, aber nicht selbständige Evidenz

Diese Statusklärung fasst veröffentlichte Primärartefakte zusammen. Ihre
Zusammenfassung ist keine neue experimentelle Messung und kein Ersatz für die
dort hinterlegten Dateien. Der WhatsApp-Kommentar ist nochmals kürzer und darf
nicht als eigenständiger Beweis verwendet werden.

Nichtöffentliche Kommunikation ist kein Bestandteil dieser Evidenzkette. Das
Bundle enthält weder Audioquellen noch Transkripte und stützt keine Aussage auf
deren Identität, Vollständigkeit oder Interpretation.

## Fortbestehender Continue-Status

```text
CONTINUE_DRAFT01_WIRE_IMPLEMENTATION
```

Dieser Continue-Status ist eine sachliche Grenze und kein verdeckter Pass. Eine
spätere Änderung erfordert neue Implementierung, neue Tests, neue Evidenz und
eine getrennte Freigabe.
