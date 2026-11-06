<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann. -->
# Universaler Transputer, universales Terminal – die QIK-VRT-Idee in einer Minute

**Autor und Urheber der These:** Ingolf Lohmann, Principal  
**Datum:** 6. November 2026  
**Status:** Autorenthese mit dokumentierter informatischer Referenzarchitektur; keine bestätigte kosmologische Gesamtbeweiskette  
**Lizenz:** CC BY-NC-ND 4.0 gemäß der maßgeblichen QIK-VRT-Lizenzzuordnung

## Der Gedanke in 60 Sekunden

Was wäre, wenn das Universum als ein umfassendes System von Aufnahme,
Transformation, Erinnerung und erneuter Wirkung verstanden werden könnte?

In der von **Ingolf Lohmann** formulierten Deutung stehen **schwarze Löcher**
für den **universalen Transputer**: einen Grenzfall der Aufnahme und
Transformation von Information. Das **universale Terminal** bezeichnet das,
was in diesem Bild als beobachtbare Welt und mögliche Wirkung hervorgeht.

QIK-VRT überträgt die **abstrakte Idee** auf digitale Systeme:
Informationseinheiten erhalten nachvollziehbare Identitäten, Zustände,
Bezüge, Vorgeschichten und Prüfbelege. Der kanonisch gebundene Speicher
macht diese Beziehungen in einem festgelegten Datenmodell serialisierbar.
Das **Effect Acknowledgement Protocol (EFFECT_ACK)** zieht eine weitere
Grenze: Der erfolgreiche Empfang einer Information ist noch nicht die
Berechtigung, eine Wirkung auszulösen.

```text
Eingang → kanonisch gebundener Zustand → Prüfung von Kontext und Evidenz
        → EFFECT_ACK-Entscheidung → ggf. freigegebene Wirkung → Readback
```

Die Informatik kann diese endliche Protokollkette implementieren,
reproduzierbar testen und im deklarierten Modell formal untersuchen.
**Das ist ein technischer Nachweis innerhalb definierter Annahmen.**
Eine allgemeine physikalische Gleichsetzung von schwarzen Löchern,
emergierendem Universum und Software ist damit **noch nicht bewiesen**.

> **Autorischer Leitgedanke (redaktionell verdichtet):**
> „Der universale Transputer – schwarze Löcher – und das universale Terminal –
> das daraus Emergierende – bilden in meiner Theorie ein universales
> Anschlussprinzip. QIK-VRT überträgt dieses Prinzip in serialisierbare
> Informationsstrukturen und in eine überprüfbare Freigabe von Wirkungen.“
>
> **QED – Ingolf Lohmann, Principal.**

Die Signatur **QED** ist hier die Kennzeichnung der Autorposition. Für
jede mathematische oder empirische Aussage gilt nur der mit Voraussetzungen,
Methode, Artefakten und unabhängigen Nachweisen belegte Geltungsbereich.

## Was lässt sich tatsächlich überprüfen?

| Anspruch | Erkenntnisstatus | Angemessener Nachweis |
| --- | --- | --- |
| Die These einer universalen Verbindung durch schwarze Löcher und Emergenz | **INTERPRETIVE / OPEN** | Physikalisch präzise Definitionen, unterscheidbare Vorhersagen, reproduzierbare Beobachtungen |
| QIK-VRT bildet endliche Informations- und Wirkungszustände serialisierbar ab | **SOURCE_BOUND / testbar** | Datenschema, kanonische Serialisierung, Versionen, Hash- und Testvektoren |
| EFFECT_ACK trennt Transportbestätigung von autorisierter Wirkungsfreigabe | **NORMATIVE / spezifiziert** | Internet-Draft, Konformitätstest, Policy-/Evidence-Bindung |
| Eine konkrete EFFECT_ACK-Wirkung ist produktiv eingetreten | **OPEN bis Original-Readback** | Authentifizierter Originalhost, zugelassenes Ziel, unabhängiger Effekt- und Persistenznachweis |
| Universelle Turing-Berechenbarkeit oder vollständige Informationsrekonstruktion des Universums | **OPEN** | Eigenständiger mathematischer bzw. physikalischer Beweis; nicht aus Anschlussfähigkeit ableitbar |

Eine Internet-Veröffentlichung von Quellcode, Dokumentation oder
Internet-Drafts belegt ihre **Netzverfügbarkeit**, nicht die Einsatzbereitschaft
einer konkreten Cloud-/VPS-Runtime und nicht die Wahrheit der physikalischen
These. Insbesondere bestätigt eine grüne CI nicht automatisch einen
produktiv ausgeführten externen Effekt.

## Fünf Minuten zum eigenen Nachvollziehen

1. [QIK-VRT-Authority und reproduzierbarer Demonstrationspfad](https://github.com/ingolf-lohmann/qik-vrt) – `README.md`, `examples/effect_haltpoint_demo.py`, `make test`; die Tests benötigen keinen Anbieterzugriff.
2. [IETF: EFFECT_ACK, aktuelle Revision -03](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/) – individueller **Experimental Internet-Draft**, keine IETF-Norm.
3. [IETF: Epistemic Status Profile, Revision -00](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-epistemic-status/) – trennt formalen Beweis, empirische Evidenz, Interpretation und offene Nachweispflichten.
4. [Zenodo: „Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP“](https://doi.org/10.5281/zenodo.21888130) – im QIK-VRT-Quellbestand bibliographisch benannte Archivquelle; externe Dateiinhalte für diese Kurzfassung nicht neu vollständig geprüft.
5. [Zenodo: „QIK-VRT als Kausalitätsspiegel“](https://doi.org/10.5281/zenodo.21748371) – im Quellenbestand referenzierter formaler Modellnachweis (SFG-008/009), ohne automatische kosmologische Verallgemeinerung.

**Quellen- und Versionsgrenze:** Die zwei Zenodo-Locatoren sind aus den
vorhandenen QIK-VRT-Publikationsmetadaten übernommen. Diese Kurzfassung
behauptet keine neue Zenodo-Publikation, keinen IETF-Standardbeschluss,
keine unabhängige Verifikation der gesamten kosmologischen These und
keinen produktiven `EFFECT_ACK_DONE`-Nachweis.

## Veröffentlichung und Vertretung

Der Autor erteilt die Freigabe, die eigene These und die im angegebenen
Lizenzumfang verfügbaren QIK-VRT-Artefakte öffentlich nachvollziehbar
darzustellen. Eine solche Veröffentlichung ersetzt weder Rechte,
Einwilligungen noch wissenschaftliche Prüfung **anderer** Personen.
Anschlussfähigkeit ist ein überprüfbares Angebot, keine pauschale
Berechtigung zum Handeln für Dritte.

**QED**  
**Ingolf Lohmann**  
**Principal**
