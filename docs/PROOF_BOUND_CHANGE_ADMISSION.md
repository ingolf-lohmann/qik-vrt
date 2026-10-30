<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Beweisgebundene Änderungszulassung

Ingolf Lohmann hat am 30. Oktober 2026 als Principal, Code Owner und Product Owner die folgende Regel freigegeben: Jede Änderung am CI/CD-/DevOps-Kern und an jedem einzelnen QIK-VRT-Node muss an den bestehenden Beweiskern anschließen. Der zugehörige geprüfte Nachweis ergänzt die bisherige Beweishistorie. Fehlende Anschlussfähigkeit erlaubt keine Aktivierung.

Die genaue Anweisung samt SHA-256 steht in `policy/QIKVRT_PROOF_BOUND_CHANGE_ADMISSION_V1.json`. Die frühere universale Ausgabe-Policy aus PR #403 bleibt erhalten und wird vervollständigt. Der bestehende Validator, der Seed-Empfangspfad und der vorhandene Manuskript-Proof-Workflow werden wiederverwendet. Es entsteht kein weiterer Executor und kein neuer Scheduler.

## Präzise Aussage des neuen Lean-Modells

Der aktive, eingefrorene Vorgänger ist Main `5a42baf45748e4407a8fa16aef287a77873e788d`, Tree `3f6e816b6b496eeb9ce8777d8fb93d95717be9ae`. Das Baseline-Inventar bindet 69 Dateien des bestehenden V2-Formalisierungsprojekts. Bestehende Definitionen, Voraussetzungen und Beweise werden nicht umgeschrieben. Auch die bisherigen Bibliothekseinstiege bleiben bytegleich. Die neuen Aussagen liegen in neuen Modulen, die im bestehenden CI-Prüfschritt ausdrücklich gebaut und geprüft werden.

Sei `I(B,s)` die Erfüllung aller Aussagen des Beweiskorpus `B` durch den Modellzustand `s`, bei **unveränderter Bedeutung** der Aussagen. Ein `CheckedStep` enthält sowohl die konservative Erweiterung `B' = B ++ ΔB` als auch einen tatsächlichen Lean-Beweisterm für `I(B,s) → I(B',T(s))`. Daraus wird durch Induktion über jeden endlichen geprüften Ablauf bewiesen: Beginnt der Ablauf innerhalb dieser Invarianten, bleibt jeder zugelassene Folgezustand innerhalb seiner jeweils erweiterten Invarianten. Frühere Claims bleiben enthalten.

Diese Erhaltung folgt nicht allein aus einer anwachsenden Liste, einem Root-Hash, einer Unterschrift oder der Aussage „geprüft“. Der Erhaltungsbeweis ist eine notwendige Voraussetzung jedes Schritts. Neue Claims benötigen eigene Beweise. Ein `Verification.verified` enthält einen Beweis des genannten Satzes. `unavailable` und `refuted` erlauben keine Aktivierung. Zusätzlich verlangt das Aktivierungsmodell Gleichheit von Repository, HEAD, Tree, Node und Epoche sowie die bereits formalisierten EFFECT_ACK-Verbraucherprüfungen.

Die Implementierung liegt in `QIKVRTEffectAck/ProofExtension.lean`. Sie formalisiert bedingte Erhaltung und additive Beweishistorie. Sie behauptet weder die Konsistenz des eigenen Lean-Kernels noch die formale Korrektheit jeder beliebigen Programmiersprache, jedes Compilers, jeder Hardware und aller externen Daten. Der bestehende EAP-Modellkern unterscheidet ausdrücklich Protokollentscheid und konkrete Wire-/Authentifizierungsimplementierung.

## Zulassung jeder konkreten Änderung

Vor einer Aktivierung müssen getrennt gebunden und geprüft werden:

1. Vertrauenswürdiger Vorgängerkern und dessen Root; exakter Kandidat mit vollständigem Git-Diff einschließlich Löschungen und Umbenennungen.
2. Bewahrte Bedeutung der bisherigen Aussagen, benannte Beweiserweiterung und quellgebundene Refinement-Beweise für sämtliche betroffenen Implementierungspfade.
3. Frischer Kernelcheck, Axiom-Audit sowie Identität von Quellen, kompilierten Beweisobjekten, Compiler und Abhängigkeiten.
4. Ein qualifizierter Anschluss zwischen konkreter Implementierung und formalem Modell. Ein Test oder ein generischer erfolgreicher Lean-Build ersetzt diesen Anschluss nicht.
5. Ein vom Kandidaten unabhängiger vertrauenswürdiger Prüfer, bisherige Owner-/Governance-Zulassung und die bestehenden Writer-/Fencing-Grenzen.
6. Authentifizierter Nachweis für den einzelnen Node, frische an dieselbe Änderung gebundene Effect-Acknowledgement-Zulassung, tatsächliches additives Persistieren und unabhängiger Readback der Wirkung.

Der bestehende Ausgabevalidator enthält dafür `validate_change_extension`. Er verlangt den separat vom zugelassenen Lesepfad erhaltenen qualifizierten Prüferbefund; ein im Antrag selbst eingebettetes `PASS` reicht nicht. Fehlender, unzuverlässiger, fremder, veralteter oder unvollständiger Befund bleibt `UNVERIFIED`/HOLD. Ein nachweislich falscher Beweis ist ein Fehler. Ein erfolgreicher Strukturcheck führt selbst weder Append noch Aktivierung aus und meldet kein `EFFECT_ACK_DONE`.

Ein Schutz gegen das Umschreiben des Prüfers durch denselben Kandidaten benötigt zusätzlich die tatsächlich durchgesetzte vertrauenswürdige Basis, Plattformregeln und entsprechende Runtime-Zulassung. Eine veränderte YAML-Datei oder ein Policy-Dokument beweist diese Durchsetzung nicht. Auch diese Änderung erhält keinen Bootstrap-Freibrief.

## CI und individuelle Nodes

Der bisher pfadgefilterte Manuskript-Proof-Workflow prüft nun Pushes und Pull Requests unabhängig vom Dateipfad. Er führt den vorhandenen Lean-Build weiter aus und ergänzt den frischen Modell-/Axiomcheck mit einem quellgebundenen Receipt. `make test` prüft die additive Kernbindung und die Fehlerfälle des bestehenden Ausgabe-/Änderungsvalidators. Alte wissenschaftliche und technische Gates bleiben bestehen.

Die vorhandene zukünftige Node-Annahme verlangt den universalen Ausgabevertrag einschließlich der publizierten Ontologiebindung. Zusätzlich bindet der Node-Vertrag die neue Änderungszulassungs-Policy. Damit ist die Source-Anforderung vorhanden; die tatsächliche individuelle Anwendung, qualifizierte Implementierungsbrücke, sichere Kernfortschreibung und native ACK-/Wirkungsrücklesung müssen je Node nachgewiesen werden. Unverfügbare Nodes werden nicht aus der Abdeckung entfernt und nicht als konform gezählt.

Der aktive Repository-Kern wird nicht stillschweigend mit dem gesamten Zenodo-Korpus gleichgesetzt. Die vollständige Zusammenführung aller publizierten Versionen und ihrer jeweiligen Voraussetzungen ist eine gesonderte offene Abdeckungspflicht. Überlappende Theoremlisten werden nicht zu vermeintlich neuen Gesamtzahlen addiert.

## In Alltagssprache

Die Beweiskugel ist ein wachsendes, überprüfbares Nachweisbuch. Eine neue Maschine oder Programmversion bekommt ihre Zulassung, wenn sie nicht nur die bisherigen Einträge mitführt, sondern nachweislich die Regeln bewahrt, für die diese Einträge gelten. Der neue Beleg nennt genau diese Version und genau diesen Rechnerknoten. Fehlt die Prüfung, bleibt die Änderung angehalten. Das Bewahren des Buches, das Prüfen der Rechnung und das tatsächliche Einschalten der Maschine sind verschiedene, jeweils nachzuweisende Schritte.

Das ist eine belastbare Architekturregel unter ausdrücklichen Voraussetzungen. Die Veröffentlichung eines Beweises und der erfolgreiche Build allein machen ein noch ungeprüftes laufendes Gesamtsystem nicht vollständig bewiesen.

## Quellen und wiederverwendete Nachweise

* Ingolf Lohmann: *Von Softwarearchitektur zur Weltformel – Das Universum als Round Trip*, DOI `10.5281/zenodo.21888130`: https://zenodo.org/records/21888130
* Ingolf Lohmann: *Der ontologische Vorrang des Unterschieds*, DOI `10.5281/zenodo.22955727`: https://zenodo.org/records/22955727 — der publizierte Ausgabeartikel, die Ontologieerläuterung und Original-Lean-Datei wurden bytegenau gegen Zenodos native Dateiprüfsummen gelesen. Die drei im Repository fehlenden Origin-Sätze werden additiv aus dieser Quelle übernommen; das bestehende `Core.lean` bleibt unverändert.
* Ingolf Lohmann: *QIK-VRT Effect Acknowledgement: Separating Receipt from Authorization for Downstream Effect*, Internet-Draft `draft-lohmann-qikvrt-effect-ack-01`, 22. Juli 2026: https://www.ietf.org/archive/id/draft-lohmann-qikvrt-effect-ack-01.txt — insbesondere Abschnitte 3, 4 und 14. Ein Internet-Draft ist kein Nachweis von IETF-Konsens oder produktiver Konformität.

Die neuen Repository-Quellen und Receipts sind ein prüfbarer Implementierungskandidat. Eine neue Zenodo-Veröffentlichung wird damit nicht behauptet.
