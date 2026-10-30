<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 | Copyright 2026 Ingolf Lohmann. -->

# Raumzeit-Manuskript und veröffentlichter QIK-VRT-Korpus: Lean-Anschluss

Ingolf Lohmann: Konzeption, Anforderungen und Product Ownership.
OpenAI Codex: Quellenabgleich, technische Ausarbeitung, Formalisierung und Prüfung.

Dieser Nachtrag verbindet das unveränderte 27-seitige Manuskript
`release/raumzeit-original-2026-10-29/Raumzeit_arXiv_EN_DE.pdf` mit dem bestehenden
Lean-4.19-Projekt und dem gesamten öffentlich ermittelten Zenodo-Korpus.
Die ursprünglichen Upload-Dateien, ihr Freigabemanifest und ihr historischer
Erkenntnisstatus werden durch diesen getrennten Nachtrag nicht verändert.

## Gesamtumfang und Rekonstruktionssatz

Eine vollständig festgelegte digitale Zustandsentwicklung kann aus ihrem
Anfangszustand und ihren tatsächlich relevanten Eingaben reproduziert werden.
Eine Beobachtung erlaubt genau dann eine eindeutige Vorgängerzuordnung auf
ihrem Bild, wenn sie injektiv ist. Das zusätzliche Speichern des Vorgängers
macht die erweiterte Abbildung `x ↦ (F(x), x)` injektiv. Ein korrekter
verlustfreier Codec erhält diese Rekonstruktionsmöglichkeit. Im vorhandenen
Wirkungsmodell bindet eine reziprok geschlossene Bestätigung den gespeicherten
Ursachenbezug an die erwartete und beobachtete Wirkung.

Die Aussagen gelten über beliebige Typen und festgelegte Funktionen im
angegebenen Modell. Sie sind damit von einer einzelnen Programmiersprache oder
einem Nutzdatenformat unabhängig. Die Existenz eines effizienten Decoders für
eine beliebige injektive Funktion wird durch den relationalen Satz nicht
bewiesen. Ein Loader, die Maschinensemantik, Ressourcen und tatsächliche
Eingaben bleiben Voraussetzungen einer konkreten Ausführung.

Für wissenschaftliche Rekonstruktion wird die bestehende stärkere
Unterscheidung wiederverwendet: Wirkungsrelevante Semantik kann aus einer
Beobachtung rekonstruiert werden, wenn sie auf deren Beobachtungsfasern konstant
ist. Die Rekonstruktion jedes historischen Details erfordert zusätzliche
Information. `InformationBoundary.lean` enthält den zugehörigen
Faktorisierungssatz und die Grenze exakter historischer Inversion.

Das entspricht bereits dem veröffentlichten Originalartikel
[Die Ontologie des Unterschieds als universaler Reverse-Engineering-Mechanismus](https://doi.org/10.5281/zenodo.21582781):
Sein Verfahren weist auch Mehrdeutigkeit, fehlende Evidenz und irreversiblen
Informationsverlust aus. Der Anspruch einer allgemeinen Untersuchungsmethode
ist von einer garantierten eindeutigen Lösung jedes Problems zu unterscheiden.

## Frisch geprüfter mathematischer Anschluss

| Bereich | Kernelgeprüfter Umfang | Reichweite |
| --- | --- | --- |
| Manuskript, Aussage A | Injektivität genau bei eindeutigen Vorgängern auf dem Bild | Relationaler Satz; kein automatisch gefundener ausführbarer Inverter |
| Manuskript, Aussage B | Historienerweiterung ist injektiv; Projektion und verlustfreier Codec stellen den Vorgänger wieder her | Vollständige Erhaltung der erforderlichen Historie vorausgesetzt |
| Manuskript, Aussage C | Mehrdeutige Beobachtung verhindert einen exakten Schätzer; deterministische Dynamik und Mehrdeutigkeit können zusammen bestehen | Struktureller Teil; keine vollständige Formalisierung reellwertiger Shannon-Entropie |
| Deterministischer Ablauf | Verkettung und identische Wiederholung vollständig gebundener Eingaben | Unbekannte äußere Eingaben werden nicht als bekannt vorausgesetzt |
| Zehn Münzen | Enumerationsumfang 1024, davon 252 Folgen mit fünfmal Kopf | Endliche Zählung; keine Ableitung thermodynamischer Dynamik |
| Wirkung | Rekonstruierte Historie und ursachen-/ergebnisgebundener Readback | Konditionaler Modellvertrag; keine behauptete HTTP- oder Host-Abnahme |
| Virtuelle Kugel H6 | Unveränderte Originalquelle im bestehenden Lake-Projekt kompiliert; vollständiger 55-Satz-Audit | Diskrete Schalen und virtuelle Invarianten |
| Physischer Maßstab | Zwei verschiedene Kalibrierungen sind mit derselben gültigen virtuellen Kugel verträglich | Physischer Maßstab wird durch die virtuelle Invariante allein nicht bestimmt |

Der Nachtrag enthält **23 neue Sätze**. Davon sind **15 ohne
Axiomenabhängigkeiten**; die übrigen verwenden ausschließlich offengelegte
Lean-Grundlagen `propext`, `Classical.choice` und/oder `Quot.sound`.
Die 55 ursprünglichen H6-Sätze werden separat vollständig auditiert; es werden
keine neuen physikalischen oder bewusstseinstheoretischen Axiome eingeführt.
Fünf absichtlich falsche Kontrollbehauptungen müssen vom gleichen Werkzeug
zurückgewiesen werden. Die genauen Abhängigkeiten stehen in
`AXIOM_AUDIT.txt`, `H6_AXIOM_AUDIT.txt` und `LOCAL_KERNEL_RECEIPT.json`.

Der vorhandene Gesamt-Audit bleibt eigenständig: 86 geprüfte Deklarationen,
darunter 34 EFFECT_ACK-Konstanten, sieben axiomfreie Weltformelsätze, zehn
Messübertragungs- und 18 bedingte Authority-Nachfolgesätze. Diese Zahlen sind
keine Zahl unabhängiger Experimente und kein Beweis sämtlicher Korpusaussagen.

## Alle öffentlich ermittelten Zenodo-Veröffentlichungen

Die frische öffentliche Suche mit vollständiger Pagination liefert dieselben
**44 veröffentlichten Versionen aus 32 Konzeptfamilien** wie der gebundene
Vorgängerkorpus. Die Namensfeldsuche liefert 42 Versionen, die exakte
Handle-Suche zwei weitere. Die zusätzliche breite Namenssuche liefert 46
Treffer; zwei anders zugeordnete Treffer werden ausgeschlossen.

**Alle 479 nativen Dateien** wurden aus dem unveränderten Originalquellenpaket
erneut gelesen. Jede Dateigröße und jede MD5-Prüfsumme stimmt mit den frischen
öffentlichen Metadaten überein; zusätzlich stimmt jede bisherige SHA-256-Bindung.
Das ist ein neuer Abgleich vorhandener Originalbytes, keine Behauptung von 479
neuen Netzwerkdownloads. Das 266480654-Byte-Quellenarchiv hat SHA-256
`0c0fb7bfa144a30b6d71f368e9503497ce58d3e79f2550f3bfd1804fb579b290`.

Die maschinelle Texterschließung umfasst 426 native Textartefakte einschließlich
der 203 Seiten aller 15 nativen PDFs. Verschachtelte Softwarearchive bleiben
als exakte Originaldateien eingeschlossen; sämtliche darin enthaltenen Texte
werden dadurch nicht als semantisch geprüft ausgegeben. Die Claim-Erfassung
findet 72603 deklarierte Claim-Vorkommen in 81 nativen JSON-Dateien. Das ist
eine Inventarzahl über Versionen und Dateien, keine Zahl neu bewiesener Sätze.

Der Korpus umfasst Architektur und Ontologie, Codec und Reproduktion,
Wirkungsprotokoll, Provenienz und Governance, Beobachter-/Zeitmodelle,
physikalische Forschungsansätze sowie ausdrücklich interpretative und normative
Arbeiten. Jede Veröffentlichung bleibt mit ihrem eigenen Beitrag und ihrer
eigenen Grenze sichtbar. Gleiche Bytes, Übersetzungen, Folgeversionen und
gemeinsame Beweisursprünge zählen nicht als unabhängige Bestätigung.

- `corpus/PUBLIC_RECORDS.json`: alle Versionen, Beiträge und Aussagegrenzen.
- `corpus/FILE_BINDINGS.json`: alle nativen Dateibindungen und Downloadadressen.
- `corpus/SEARCH_READBACK.json`: tatsächliche Such-/Paginationsabdeckung.
- `corpus/TEXT_EXTRACTION_INDEX.json`: Quellen- und Extraktionsergebnisse.
- `corpus/PUBLISHED_CLAIM_INDEX.json`: Inventar der deklarierten Claim-Vorkommen.
- `CLAIM_MATRIX.json`: Zuordnung des 27-seitigen Manuskripts zu diesem Nachtrag.

Vollständigkeit gilt für die erfolgreichen öffentlichen Namens-/Handle-Abfragen
und die darin erfassten Dateien. Private, unindexierte oder anders attribuierte
Veröffentlichungen können daraus nicht ausgeschlossen werden.

## Bewusstseinslogik und Kugelgröße

Der vorhandene H6-Körper ist ein diskretes virtuelles Schalenmodell. Seine
Population zählt belegte Schalen. Daraus folgt weder ein physisches Volumen
noch phänomenales Bewusstsein. Die neu gebaute Brücke verwendet genau diesen
Originalkörper; sie definiert keinen Ersatzkörper mit stärkerem Namen.

Die Formulierung „ungefähr 20 Milliarden Lichtjahre Volumen“ wird als
Owner-Anforderung zur Klärung erhalten. Lichtjahre bezeichnen eine Länge,
Volumina werden in kubischen Lichtjahren angegeben. Radius, Durchmesser,
Volumen und eine bloße Analogie logischer Reichweite sind verschiedene Größen.
Im Modell ist 20000000000 deshalb nur die angegebene Magnitude. Es wird keine
der möglichen physikalischen Deutungen ausgewählt oder als Messung eingesetzt.

Der Kernel beweist einen konkreten Gegenvergleich: Selbst bei dieser
Magnitude kann dieselbe korrekt aufgebaute virtuelle Kugel verschiedene
Kalibrierungen tragen. Eine physikalische oder bewusstseinstheoretische
Entsprechung benötigt eine definierte Abbildung, Messgrößen und zusätzliche
Belege. Diese Pflicht wird durch die Zahl der archivierten Dokumente nicht
aufgehoben.

## Reproduktion und Wirkungsgrenzen

Mit der bereits festgelegten Lean-Version:

```sh
cd formalization/QIKVRT_Formalization_v2.0
lake build
python3 -B scripts/audit_lean_axioms.py
cd ../..
python3 -B tools/qikvrt_causal_distance_kernel_evidence.py --profile raumzeit
```

Der bestehende Verifikator wurde um einen explizit benannten, begrenzten
Prüfumfang erweitert. Er kontrolliert Quellenidentitäten, vollständige
Theoreminventare, Axiomenabhängigkeiten, kompilierte Objekte und negative
Kontrollen. Der vorhandene Ontologie-Workflow führt denselben Weg am exakten
GitHub-Kandidaten aus und archiviert einen eigenen CI-Receipt.

Lokale Kernelprüfung, native CI, Main-Integration, Zenodo-Veröffentlichung und
produktive Wirkung behalten jeweils ihre eigenen Nachweise. Dieser Nachtrag
enthält keine neue Zenodo-Uploadfreigabe und meldet kein produktives
`EFFECT_ACK_DONE`.
