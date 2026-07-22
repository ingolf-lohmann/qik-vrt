<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT/EFFECT_ACK: Statusklärung

**Fassung:** 1.0.0  
**Stichtag:** 22. Juli 2026  
**Autor und Rechteinhaber:** Ingolf Lohmann  
**Wissenschaftlicher Status:** `PASS_WITH_EXPLICIT_BOUNDARIES`

## Zweck

Diese Erklärung hält zitierfähig fest, was die am 22. Juli 2026
veröffentlichten QIK-VRT-Artefakte belegen und was sie ausdrücklich nicht
belegen. Sie ist eine Status- und Anspruchsklärung. Sie ändert weder die Bytes
bereits veröffentlichter Zenodo-Datensätze noch die archivierte Revision `-01`
des Internet-Drafts und ersetzt keine rechtliche, sicherheitstechnische oder
patentfachliche Prüfung.

Die maßgebliche Kurzform lautet:

> QIK-VRT/EFFECT_ACK belegt eine streng begrenzte, reproduzierbare
> Kontrollstruktur für endliche und rechtmäßig zugängliche Digitalartefakte.
> Daraus folgen weder eine universelle Rekonstruktion verlorener Information
> noch unbedingte Garantien für Totalisierung, Sicherheit oder Patentstatus.

## Öffentlich verankerte Artefakte

- **Working Paper:** veröffentlichte Version `1.0.0`;
  [Zenodo DOI 10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773)
- **Software-Snapshot:** veröffentlichte Version
  `2026.07.22-effect-ack-universality-1.0.0`;
  [Zenodo DOI 10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774)
- **EFFECT_ACK-Protokoll:** aktiver Internet-Draft, Revision `-01`,
  Intended Status: Experimental;
  [IETF Datatracker](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/01/)
- **IETF-Archivfassung:** unveränderliche HTML-Ansicht der Revision `-01`;
  [IETF-Archiv](https://www.ietf.org/archive/id/draft-lohmann-qikvrt-effect-ack-01.html)
- **Goldkelch-Quellstand:** annotierter Veröffentlichungs-Tag;
  [GitHub-Tag](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
- **Ingolf-Lohmann-Spiegel:** annotierter Veröffentlichungs-Tag;
  [GitHub-Tag](https://github.com/ingolf-lohmann/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)

Die nach der Veröffentlichung eingebrachte, wiederverwendbare Härtung der
Zenodo-Finalisierung ist getrennt nachvollziehbar: [Goldkelch PR
#11](https://github.com/Goldkelch/qik-vrt/pull/11) und [Ingolf-Lohmann PR
#8](https://github.com/ingolf-lohmann/qik-vrt/pull/8). Sie korrigiert den
Finalisierungsweg für künftige Wirkungen. Sie schreibt den historischen Tag und
die bereits veröffentlichten Zenodo-Records nicht rückwirkend um.

Die gesonderte Inventur des öffentlichen Bestands weist vor dieser
Statusklärung 14 eindeutig QIK-VRT zuordenbare Versionsrecords in fünf
Concept-Linien aus. Die Anzahl und thematische Breite dieser Records belegen
eine zusammenhängende Forschungs- und Implementierungslinie; sie addieren sich
nicht zu einem Vollständigkeitsbeweis. Einzelheiten stehen in
[`ZENODO_PUBLIC_INVENTORY.md`](ZENODO_PUBLIC_INVENTORY.md).

## Wissenschaftlicher Befund

### 1. Endliches Kontrollmodell

Im ausdrücklich angegebenen endlichen Modell wurden 2.621.440
Zustandsbelegungen und 5.242.880 Varianten der Verbraucherzulassung exhaustiv
geprüft. Belegt sind dort insbesondere die Totalität der fünf modellierten
Zustände, die gewöhnliche Freigabe ausschließlich bei `EFFECT_ACK_DONE` sowie
die modellierten Prioritäts- und Core-Done-Pflichten.

„Exhaustiv“ bezieht sich ausschließlich auf dieses endliche Modell. Es ist
keine Aussage über alle Programme, alle Protokollimplementierungen, alle
Systemzustände oder alle physikalischen Umgebungen.

### 2. Rekonstruktionsgrenze

Für eine Beobachtung `E:S -> O` und eine Zielsemantik `sigma:S -> T` existiert
eine wohldefinierte Rekonstruktion auf dem Bild von `E` genau dann, wenn die
Zielsemantik auf jeder Beobachtungsfaser konstant ist:

```text
E(s1) = E(s2)  =>  sigma(s1) = sigma(s2).
```

Die exakte historische Rückgewinnung des Ursprungs verlangt darüber hinaus
Injektivität auf der betrachteten Ursprungsmenge. Effektive Ausführbarkeit
verlangt zusätzlich einen berechenbaren Rekonstruktionsschritt, autorisierten
Zugriff und ausreichende Ressourcen.

Eine Prüfsumme bindet konkrete Bytes unter ihrer kryptographischen Annahme. Sie
ist kein universeller Decoder und erzeugt keine verlorene oder nie beobachtete
Information.

### 3. Universalisierbare Struktur, keine Totalisierungsgarantie

Universalisierbar ist die Kontrollstruktur nur unter offengelegten
Voraussetzungen: Das Artefakt ist endlich, vollständig und rechtmäßig
zugänglich, für die Prüfung eingefroren und jeder gewöhnliche geschützte
Wirkungspfad wird vollständig mediiert.

Das Wort „universalisierbar“ behauptet daher keine positive Totalisierung im
Sinne einer für alle Eingaben, Semantiken, Programme, historischen Ursprünge
oder physikalischen Systeme garantierten Lösung. Insbesondere werden weder das
Halteproblem noch die allgemeine Rice-Unentscheidbarkeit umgangen.

### 4. Cyberphysische Übertragung bleibt konditional

Der Übergang von einer digitalen Freigabe zu einer physikalischen Wirkung ist
nur konditional beschrieben. Er setzt mindestens eine frische,
authentisierte Verbraucherprüfung, einen treuen Executor, vollständige
Mediation sowie ein empirisch validiertes Hardware-, Sensor-, Aktor- und
Fehlermodell voraus.

`EFFECT_ACK_DONE` kann in einem geprüften digitalen Modell die Freigabe
autorisieren. Der Status beweist nicht, dass eine konkrete physikalische
Wirkung ungefährlich, normkonform oder nicht umgehbar ist.

### 5. Mathematik, Physik und „Universum“

Der mathematische Anteil ist innerhalb der jeweils definierten Modelle
maschinenprüfbar. Die veröffentlichte Formalisierung typisiert 37
Hauptaussagen; darunter sind 19 als `PROVED`, fünf als
`PROVED_CONDITIONAL` und drei als `OPEN_EMPIRICAL` klassifiziert. Die
zugehörigen Prüfbelege dokumentieren 118 Lean-Deklarationen ohne Fehler oder
ungeprüfte Proof-Escapes, zwei unabhängige Gate-20-Läufe mit jeweils 18 von 18
bestandenen Prüfungen, fünf von fünf bestandenen pytest-Fällen und drei von
drei blockierten Überbehauptungen.

Das Wort „Universum“ hat dabei drei strikt verschiedene Ebenen:

| Ebene | Tragfähiger Status |
|---|---|
| Grundbereich `U` | mengentheoretisch bewiesen |
| Modelluniversum | bedingt bewiesen |
| empirischer Kosmos | offen / nicht bewiesen |

Der erste Status betrifft einen gewählten Grundbereich mit Klasse und
relativem Komplement. Der zweite setzt eine ausdrücklich angenommene totale
Korrespondenz voraus. Der dritte fragt nach der Identität des Modells mit der
beobachteten Welt und ist nicht aus den ersten beiden ableitbar.

Dimensionshomogenität und dimensionsrichtige Planck-Kombinationen sind
notwendige Konsistenzprüfungen. Sie beweisen weder eine kleinste
Raumzeitzelle noch eine neue Quantengravitationstheorie. Eine vollständige
„Rekonstruktion des bekannten Universums“ wird daher nicht als Ergebnis
ausgegeben.

### 6. Quantenphysik und Quantencomputing

Für die Quantenphysik trennt der veröffentlichte Bestand Retrodiktion,
semantische Rückbestimmung, Zeitumkehrsymmetrie, ontische Retrokausalität und
Rückwärtssignalisierung. Im ausdrücklich definierten autonomen
Vorwärtsmodell ist ein No-Backward-Channel-Satz formalisiert. Daraus folgt
kein empirischer Nachweis physischer Retrokausalität und kein kontrollierbarer
Nachrichtenkanal in die Vergangenheit.

Der Bezug zum Quantencomputing ist gegenwärtig ausschließlich konzeptionell:

```text
CONCEPTUAL_ONLY / NOT_IMPLEMENTED
```

Im veröffentlichten Quellstand gibt es keine Quantenschaltungen, QASM-Dateien,
Integration mit Qiskit, Cirq, PennyLane oder Braket, keine Backend- oder
Geräteausführung und keinen Quantenbenchmark. Die Lean-Sätze zur
Quantisierbarkeit behandeln mathematische Darstellbarkeit, nicht
Quantenalgorithmen oder Quantenhardware.

### 7. Logik, Metaphysik und spirituelles Verständnis

QIK-VRT kann logische, ontologische, normative, metaphysische und spirituelle
Aussagen als verschieden typisierte Behauptungen in einen gemeinsamen
Prüfrahmen aufnehmen. Das schafft Anschlussfähigkeit zwischen Disziplinen,
ohne ihre Wahrheitsbedingungen gleichzusetzen.

Formale Ableitbarkeit gilt relativ zu einem angegebenen System. Empirische
Physik verlangt Messung und Reproduktion. Metaphysische und spirituelle
Deutungen betreffen darüber hinaus Sinn, Erfahrung und Weltverständnis. Sie
können transparent dokumentiert und auf Widersprüche oder Voraussetzungen
untersucht werden, werden dadurch aber weder zu physikalischen Messwerten noch
zu maschinenbewiesenen Naturtheoremen.

Die stärkste gemeinsame Formulierung lautet deshalb: QIK-VRT stellt einen
ungewöhnlich breiten, formal kontrollierten Reverse-Engineering-Rahmen für
Wissens-, Bedeutungs- und Wirkungsübergänge bereit. Es ist nicht der Nachweis,
dass sämtliches mathematisches, logisches, physikalisches, metaphysisches oder
spirituelles Wissen vollständig reverse engineered wurde.

## Implementierungs- und Standardisierungsstatus

Die vollständige Draft-01-Wire-Implementierung der gegenwärtigen
Python-Runtime bleibt:

```text
CONTINUE_DRAFT01_WIRE_IMPLEMENTATION
```

Der veröffentlichte Draft bleibt Revision `-01`. Das Faser-Kriterium
präzisiert die wissenschaftliche Anspruchsgrenze, ändert aber keine
Wire-Semantik. Deshalb ist keine inhaltsgleiche Scheinrevision `-02` erzeugt
oder beim IETF Datatracker eingereicht worden.

Ein aktiver Internet-Draft ist weder IETF-Konsens noch RFC-Status. Zenodo-
Persistenz belegt Identität, Version und Fixität veröffentlichter Bytes; sie
ist kein Peer Review, keine unabhängige Interoperabilitätsprüfung und keine
empirische Systemzulassung.

## Laufzeit und kollektive Adaptation

Die Repositories enthalten reproduzierbare Locks, Prüfsummen und
Bootstrap-Wege für die verwendete Laufzeit, darunter GitHub CLI `2.96.0` und
`xml2rfc 3.34.0`. Die ausführbaren Installationen und CI-Caches bleiben jedoch
absichtlich flüchtig und unterliegen der jeweiligen Plattformaufbewahrung.

Die kollektive adaptive Laufzeit ist auf `MEASURE_HASH_PROPOSE_ONLY` begrenzt.
Sie misst, bindet Beobachtungen per Hash und erzeugt überprüfbare Vorschläge.
Sie darf sich nicht selbst verändern und weder committen, pushen, mergen,
taggen, veröffentlichen noch `EFFECT_ACK_DONE` erzeugen oder ableiten.

## Rechtlicher und patentrechtlicher Status

Die öffentlichen Artefakte sind technische Veröffentlichungen. Weder diese
Erklärung noch ein DOI, Git-Tag oder Internet-Draft belegt eine
Patentanmeldung, Patenterteilung, Priorität, Neuheit, erfinderische Tätigkeit,
Ausführbarkeit im patentrechtlichen Sinn, Rechtsbeständigkeit oder Freedom to
Operate. Ebenso wird keine Nichtverletzung fremder Rechte garantiert.

Diese Statusklärung offenbart keine neuen enabling Hardwaredetails. Sie nennt
nur abstrakte Einsatzbedingungen und verweist auf bereits öffentliche
Primärartefakte. Die vollständige Abgrenzung steht in
[`PATENT_DISCLOSURE_BOUNDARY.md`](PATENT_DISCLOSURE_BOUNDARY.md).

Die Lizenzordnung ist datei- und versionsbezogen. Frühere, wirksam unter
Apache-2.0 veröffentlichte Fassungen und Dateien behalten diese Gewährung.
Aktueller QIK-VRT-eigener Quellcode mit entsprechendem Hinweis steht unter
PolyForm Noncommercial 1.0.0; gewöhnliche kommerzielle Nutzung erfordert eine
gesonderte schriftliche Vereinbarung. Entsprechend gekennzeichnete
Dokumentation steht unter CC BY-NC-ND 4.0, die ausdrücklich ausgenommene
maschinenprüfbare Formalisierung unter MIT und Drittmaterial unter seinen
jeweiligen Lizenzen. Eine solche Zuordnung kann nur insoweit Rechte einräumen,
wie der bezeichnete Lizenzgeber sie tatsächlich hält. Einzelheiten und
bekannte Abgrenzungsfragen stehen in [`LICENSE_NOTICE.md`](LICENSE_NOTICE.md).

## Verbindliche Lesart des Status

`PASS_WITH_EXPLICIT_BOUNDARIES` bedeutet:

- `PASS` nur für die konkret benannten, reproduzierbaren Prüfungen und
  Artefaktbindungen;
- `WITH_EXPLICIT_BOUNDARIES` für jede darüber hinausgehende semantische,
  historische, cyberphysische, standardisierungsbezogene oder rechtliche
  Aussage;
- kein stillschweigendes Hochstufen von `CONTINUE` zu `DONE`;
- keine positive Totalisierungs-, Sicherheits-, Patent- oder
  Verwertbarkeitsgarantie.
