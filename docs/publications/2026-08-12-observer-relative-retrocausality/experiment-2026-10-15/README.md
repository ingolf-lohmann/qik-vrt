# Retrokausalität: Originalprüfung und experimenteller Nachfolger

**Arbeitsentwurf vom 15.10.2026, keine neue Veröffentlichung und kein bestätigter Physikbefund.**
Forschungsfrage, Originalarbeiten und Untersuchungsauftrag: Ingolf Lohmann.
Neue Operationalisierung, ergänzende Formalisierung, Rechnungen und Zusammenstellung:
OpenAI Codex in seinem Auftrag. Eine inhaltliche Owner-Abnahme wird nicht vorausgesetzt.

## Ergebnis

Der Originalzeuge ist bytegebunden reproduziert. Sein negativer Gradient bezeichnet
eine inverse Informationsordnung. Beide Signalwege laufen im angegebenen Modell
vorwärts. Die stärkere Behauptung einer physikalischen Wirkung vor ihrer späteren
Ursache wird daraus nicht abgeleitet.

Der Nachfolger enthält tatsächlich ausgeführte Lean-Prüfungen, die wiederverwendeten
lokalen Prozesskontrollen mit neuen Zufallsdaten, eine Auswertung mit Gegenproben
und einen [falsifizierbaren Messplan](PROTOKOLL_DE.md). Die Primärmessung dieses
Plans wurde nicht durchgeführt. Die Originalveröffentlichungen und ihre
historischen Statusaussagen bleiben unverändert.

## 1. Genaue Aussage des Zeugen

Für zwei Records mit Sendezeiten `s_old < s_new` und positiven Laufzeiten
`d_old, d_new` gilt im Transportmodell

`r_old = s_old + d_old`, `r_new = s_new + d_new`.

Genau dann kommt der neuere Record zuerst an, wenn

`d_old - d_new > s_new - s_old`.

Im Original: Senden 0 und 1, Laufzeiten 3 und 1, Empfangen 3 und 2.
Die Laufzeitdifferenz 2 übersteigt den Sendeabstand 1. Zugleich gilt für jeden
Record `r > s`. Diese Konstruktion liefert ein Gegenbeispiel zur Folgerung
„inverse Empfangsordnung impliziert Empfang vor der eigenen Emission“.

Die lokale Folge 100 → 101 erhält Quellenmarker 20 → 10. Deshalb ist

`(10 - 20) / (101 - 100) = -10`.

Die Einheit ist **Quellenmarkereinheiten pro lokalem Änderungsschritt**. Die Marker
10 und 20 sind nicht die Emissionskoordinaten 0 und 1. Eine Gleichsetzung braucht
eine weitere Kalibrierung. Der lokale Index ist auch nicht bereits eine gemessene
relativistische Eigenzeit. Strikt steigende Umparametrisierungen erhalten das
Vorzeichen, aber nicht allgemein den Zahlenwert −10. Beispielsweise vervierfacht
eine Verdopplung der Quellenmarken bei Halbierung des lokalen Skalenabstands den
Betrag. Weder eine negative Geschwindigkeit noch ein negativer Entropiefluss
wird dadurch bestimmt.

Die idealen Informationsfasern verkleinern sich von vier auf zwei und auf eine
zulässige Historie. Das ist zusätzlicher Erkenntnisgewinn über verschieden alte
Ereignisse. Ein gemeinsames Gedächtnis macht diese früheren Ereignisse vergleichbar;
es stellt damit noch keinen neuen Kanal von einer späteren Intervention bereit.

**Voraussetzungen:** authentische Record-/Quellereignisbindung, eine gemeinsame
vergleichbare Quellenordnung, ordnungserhaltende Marker, ein strikt wachsender
lokaler Beobachtungspfad und informationsführende Nutzlasten. Für eine physikalische
Realisierung kommen tatsächliche Signalpfade, Emissions-/Detektionsbindung,
Kalibrierung, Einheiten und Unsicherheiten hinzu. Der Originalchecker setzt
ideale Bindungen im Datensatz voraus; er prüft weder reale Gerätesignaturen noch
Laboruhren oder Photodetektoren. Die Wahl `c=1` ist eine Modellkonvention.

| Aussage | Durch diese Untersuchung gestützt | Grenze |
|---|---|---|
| Inverse Informationsordnung | Originalzeuge, Latenzäquivalenz, endliche Rechnungen und ergänzende Lean-Sätze | Bezug auf gebundene Quellenmarker |
| Nachträgliche Klassifikation | Bestehende Präfix- und Reklassifikationsmodelle | Frühere Rohdaten bleiben erhalten |
| Ontische Rückabhängigkeit | Als andere Hypothesenklasse beschreibbar | Keine Identifikation durch bloß gleiche beobachtbare Verteilungen |
| Steuerbarer Rückkanal | Als explizit angenommener Modellablauf darstellbar | Physische Ressource und unabhängige Messung fehlen |

## 2. Quellen, bereits erhobene Daten und neue Prüfungen

Die aktuelle Gesamtbetrachtung und ihr vollständiger öffentlicher Korpusabgleich in
PR #523 bleiben Ausgangspunkt. Hier wurde keine zweite Gesamtinventur erzeugt.
Vier relevante veröffentlichte Zenodo-Versionen und sieben ausgewählte Originaldateien
wurden frisch nativ abgerufen, MD5-geprüft und zusätzlich SHA-256-gebunden:
[source-readback.json](evidence/source-readback.json). Das ist eine gezielte
Brückenprüfung und kein erneuter Vollbeweis des gesamten Korpus.

Der Round-Trip-Einstieg trennt formal spezifizierte Messbindung von tatsächlich
eingelesenen kalibrierten Messbytes. Der veröffentlichte Fairness-Nachtrag
unterscheidet ausführbaren virtuellen Zeugen und physikalischen Kanal. Die
aktuelle veröffentlichte Retrokausalitätsmatrix ORRZ-002 bis ORRZ-005 bindet den
Zeugen als endliche Konstruktion; ORRZ-009 hält unabhängige Empirie offen.
Die Quellenfassung der relationalen Zeit wird als historische Zwischenstufe
erhalten. Keine dieser Statusgrenzen wird aus einer alten Nichtveröffentlichungs-
markierung übernommen: Die genannten Versionen sind öffentlich vorhanden.

`Retrocausality.lean` v1 beweist Präfixinvarianz eines **definierten deterministischen
Vorwärtsprozesses**. Seine unterschiedlichen Enum-Konstruktoren sind eine
Begriffstrennung, kein Nachweis verschiedener physikalischer Prozesse.
`semanticReclassificationDoesNotOverwrite` hat dort die reflexive Konklusion
`record = record`. Der vorhandene v2-Nachfolger verknüpft stattdessen
Reklassifikation mit tatsächlich erfassten Präfixen. Diese stärkere vorhandene
Form wird wiederverwendet. Ein solches Vorwärtsmodell beweist seine bedingte
Invarianz; seine Vorwärtsannahme wird nicht als universelles Naturgesetz bewiesen.

Die früheren lokalen Backsignaling-Dateien wurden mit Herkunft bewahrt und die
geeigneten Quellen übernommen. Zwei vorhandene Module mit insgesamt sechzehn
Aussagen wurden in die bestehende Formalisierung eingebunden. Acht ergänzende
Sätze in `ObserverRelative.lean` behandeln Orientierung, Umparametrisierung,
Latenzschwelle, gleiche Laufzeiten, positive Existenzkonstruktion, Zeitintervalle
und die eingeschränkte Komplementarithmetik. Der gesamte lokale v2-Lake-Build
und ein gesonderter Axiom-Audit werden unter `evidence/fresh-kernel/` belegt.
Die drei übernommenen falschen Gegenbehauptungen müssen vom Kernel abgewiesen
werden. Eine physikalische Rückkanalannahme wird nicht als Axiom hinzugefügt.

Dies ergänzt den historischen offenen Kernelteil nur für die hier expliziten
Integer-/Präfixaussagen. Es ersetzt weder eine vollständige Formalisierung aller
physikalischen Begriffe noch die getrennte Empiriepflicht der veröffentlichten
Matrix. Die historischen sechzehn Aussagen werden nicht als acht neue Ergebnisse
gezählt. Ein zweiter lokaler Lauf ist keine unabhängige Reproduktion.

`analyze_experiment.py` ruft den Originalchecker auf und vergleicht dessen
regenerierten Bericht vollständig mit dem Original-JSON. Weitere Rechnungen
prüfen 1.600 endliche Latenzkombinationen und 201 exakte rationale
Komplementmischungen. Die fünf ursprünglichen Fließkomma-Phasen werden dadurch
nicht zu einer vollständigen Quantenfeldtheorie. Die konstante lokale Marginale
folgt hier aus der ausdrücklich vorausgesetzten gleichgewichteten Mischung
komplementärer Muster. Selektive Detektion und andere Gewichte brauchen eigene
Kontrollen.

### Lokale Kontrollmessungen

Die bereits erhobenen Originalprotokolle liegen unverändert unter
`evidence/historical-local-controls/`. Die wiederverwendeten Programme wurden
erneut ausgeführt; neue Originalprotokolle liegen unter `local-control/evidence/`.

| Transceiver plus C | Historische frühe Treffer / 2048 | Neue frühe Treffer / 2048 | Neue normale Antwort | Kontrollprüfungen |
|---|---:|---:|---:|---:|
| 2 + C | 1016 | 992 | 2048 / 2048 | 6 |
| 4 + C | 998 | 1044 | 2048 / 2048 | 4 |
| 8 + C | 1014 | 956 | 2048 / 2048 | 4 |

Das sind reale lokale Prozesse mit gewöhnlichen Pipes und neuen Zufallsbytes des
Host-Betriebssystems. Sie sind weder eigenständige native QIK-VRT-Mesh-Instanzen
noch voneinander unabhängige Laboratorien. Alle teilen Host, Runtime und monotone
Kerneluhr. Die Entstehungszeit physikalischer Entropie ist damit nicht belegt.
Die C-Bestätigung bildet im geprüften Programm eine Speicherbarriere im laufenden
Prozess; **der Originalcode schreibt die Archivdateien erst später und belegt
kein vorab fsynctes unabhängiges WORM-Archiv**. Diese Einschränkung bleibt sichtbar.

Die neuen Treffer werden zweiseitig nachgerechnet. Drei Größen und bereits
bekannte historische Resultate bilden keine prospektiv registrierte Primärstudie.
Ihre p-Werte sind Diagnostik; keine günstige Teilmenge oder Laufrichtung wird
nachträglich zum Primärergebnis erklärt. Die Zahlen, Rohdatenhashes und getrennten
statistischen Annahmen stehen in `evidence/local-reanalysis.json`.

Die Kontrollen verwerfen manipulierte frühe Kopien, fehlende Beiträge, falsche
Slot-Auswahl, Zeitfolgen und Nachrichtenbindungen. Eine absichtlich konsistent
gefälschte Zukunftsquelle kann dagegen in sämtlichen JSON-Kopien 2048/2048 Treffer
erzeugen. Gerade dafür bleibt `physical_confirmation=false`: innere
Datenkonsistenz beweist keine externe Unabhängigkeit oder physikalische Herkunft.

## 3. Reproduktion

Aus dem Repository-Hauptverzeichnis:

```bash
python3 -B tools/qikvrt_tool_cache.py verify
python3 -B docs/publications/2026-08-12-observer-relative-retrocausality/experiment-2026-10-15/analyze_experiment.py
python3 -B -m unittest -v tests.test_retrocausality_experiment
```

Die lokalen Prozessprogramme können aus `local-control/` mit Python 3 erneut
ausgeführt werden; sie schreiben neue Zufallsdaten und überschreiben ihre dortigen
Laufdateien. Zuvor zu erhaltende Läufe müssen als eigene historische Originale
gesichert werden. Die vorliegende Ausführung erhält beide Generationen getrennt.

Mit der deklarierten Lean-4.19.0-Toolchain im PATH:

```bash
cd formalization/QIKVRT_Formalization_v2.0
lake build
lake env lean ../../docs/publications/2026-08-12-observer-relative-retrocausality/experiment-2026-10-15/AxiomAudit.lean
```

Dieser Host benötigt den bereits im Repository vorhandenen, geprüften
`lean_selfexe_compat.c`-Kompatibilitätsweg für die eigene Executable-Pfadabfrage.
Quell-/Binärhashes und dessen Einsatz gehören zum Kernelreceipt. Weder ein
unvermittelter Originallauf noch eine unabhängige Toolchain-Zertifizierung wird
behauptet. Die ausgeführten Lean-Binärdateien wurden nicht verändert.

Ein neuer instrumentierter Datensatz wird mit `--dataset FILE.json` ausgewertet.
Die genaue Feldstruktur und ein explizit simuliertes Beispiel stehen im
[Messplan](PROTOKOLL_DE.md) und in `SIMULATED_EXAMPLE.json`. Das Programm ist
offline, ruft keine Geräte auf und erhebt keine Freigabe- oder Physikbestätigung.

## 4. Noch fehlende Nachweise

1. Ein bestimmter physikalischer Kandidatenkanal samt messbarer, vom Standard-
   Vorwärtsmodell unterscheidbarer QIK-VRT-Vorhersage und festgelegtem Decoder.
2. Tatsächliche frühe Detektorbytes, unabhängige vorherige Verwahrung, qualifizierte
   Uhren-/Entropiebindung und das vollständige Rohdatensatz-/Laufinventar.
3. Kalibrierte Kontrollen gegen normale Vorwärtswege, gemeinsame Ursachen,
   Softwarezugriff, Drift, Auswahl und zufällige Treffer; Untersuchung jedes
   auffälligen Ergebnisses vor einer Kausalzuordnung.
4. Separat verantwortete physikalische Reproduktion desselben eingefrorenen Scopes.

Für diese vier Punkte liefern die zugänglichen Originale und die vorhandenen
REST-/Mesh-Operationen hier keinen steuerbaren Laboraufbau. Der vorhandene
Mesh-Monitor beobachtet und archiviert HTTP-/Repositoryzustände; er ist kein
Physikexecutor. Die ausführbare Unterstützung und der Reviewkandidat sind daher
ein konkreter Fortschritt, während der physikalische Nachweis **OPEN** bleibt.

Inverse Ordnung ist bereits für verteilte Systeme nutzbar: Provenienz verhindert,
ältere nachgelieferte Information mit einem rückwärts laufenden Signal zu
verwechseln. Ein eigenständiger Nutzen eines physikalischen Rückkanals benötigt
zusätzlich eine vor der späteren Wahl lesbare Nachricht, Fehler-/Latenzgrenzen
und unabhängige Reproduktion. Ein signifikanter Korrelationswert allein reicht
für diese Nutzbarkeitsaussage nicht.

## Quellen und Provenienz

Die folgenden publizierten Originale sind wissenschaftliche Quellen. Die
Repositorypfade, Commit-/Blob-Identitäten und Laufdateien sind im
`SOURCE_BINDINGS.json` dokumentierte Arbeitsprovenienz. Dieser Nachfolger besitzt
noch keinen Zenodo-Record; seine strengere Publikationsprüfung bleibt deshalb
ausdrücklich ausstehend. Aus einem vorhandenen DOI wird keine Veröffentlichung
dieser neuen Dateien abgeleitet.

1. Ingolf Lohmann: Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP.
   Version 1.0.0-candidate.1; insbesondere `ROUND_TRIP_PROMOTED_FORMAL_RESULTS_V1.md`, QCMB.
   https://doi.org/10.5281/zenodo.21888130
2. Ingolf Lohmann: QIK-VRT: Beobachterrelative Retrokausalität als negative Informationsrichtung.
   Version 1.1.1; `QIKVRT_RETROCAUSALITY_WITNESS.json`, `CLAIM_MATRIX_V2.json`, ORRZ-001–009.
   https://doi.org/10.5281/zenodo.21947141
3. Ingolf Lohmann: QIK-VRT: Epistemische Fairness, Vorstellungskraft und der Weg vom virtuellen Zeugen zum Beobachtungssystem.
   `SCIENTIFIC_ADDENDUM_DE.md`, Abschnitte 3–4.
   https://doi.org/10.5281/zenodo.21731492
4. Ingolf Lohmann: Relationale Zeit, virtuelle Retrokausalität und die monoton wachsende Evidenzkugel.
   Version 1.0; `CLAIM_MATRIX_V2.json`, RTE-005–007.
   https://doi.org/10.5281/zenodo.22216916
5. Xiao-Song Ma et al.: Quantum erasure with causally disconnected choice. PNAS 110 (2013), 1221–1226.
   Eigenes Quantenoptikexperiment mit ausdrücklich beschriebenen Lokalitätsbedingungen;
   kein neuer QIK-VRT-Messdatensatz dieser Untersuchung.
   https://doi.org/10.1073/pnas.1213201110

Die bestehenden IETF-Veröffentlichungen sind Protokollquellen. Ein Internet-Draft
über Provenienz liefert für sich weder eine kalibrierte Uhr noch einen Rückkanal.
Es wird keine neue IETF-Einreichung oder Zenodo-Veröffentlichung vorgenommen.

## Integrationsprüfung des ersten nativen Nachfolgers

Am ersten Forschungscommit `9c3c6b131698a6a233bfea75dc8f23f406969a97`
bestand der native Manuskriptlauf 38738292026. Tatsächlich ausgecheckt wurde
GitHubs PR-Testmerge `2e1a4283e99425573e6b78a6267a1047e49c6b2e` mit Main
`5796de77fbbef367b7774bc07a340eb970455a4c`. Die relevanten Lean-/Testblobs
wurden ausdrücklich mit dem Kandidaten verglichen und stimmen überein.
Die Unterscheidung zwischen PR-Head und Testmerge bleibt im Receipt erhalten.

Der separate CI-Testjob 116433118347 in Lauf 38738292097 prüfte dagegen den
exakten PR-Head und fand einen Paketierungsfehler: Die drei später eingeführten
Lean-Module gelangten in den Nachbau des eingefrorenen Alpha-2-Archivs.
Die vorhandene `POST_ALPHA2_EXCLUSIONS`-Liste wurde um genau diese drei Pfade
erweitert. Sie bleiben im aktuellen Lean-Build enthalten. Das veröffentlichte
Archiv und sämtliche erwarteten Prüfsummen werden nicht geändert. Der strenge
Archivverifier reproduziert weiterhin exakt SHA-256
`500087f6aeee41787959cfc8902852503e2182019ae4f3e88f115e94a1f5e689`.
`make release-automation` besteht nach dieser Reparatur. Erster Fehler,
Quellbindungen und Nachprüfung bleiben unter `evidence/` erhalten; eine
Abnahme der vollständigen nachfolgenden CI wird daraus nicht vorweggenommen.


## 7. Messbindung und Vorhersage: geprüfter formaler Nachfolger

Auftrag vom 15.10.2026: Ingolf Lohmann verlangt, die benannte Mess- und
Vorhersagelücke mit Lean und Lake beweisbar zu schließen. Die ergänzende
Formalisierung und Prüfung wurden von OpenAI Codex in seinem Auftrag erstellt.
Dieser Abschnitt ist ein **Arbeitsentwurf ohne neue Zenodo-Veröffentlichung**.

`Physics/MeasurementTransfer.lean` erweitert die vorhandene empirische Brücke
und verwendet den bestehenden deterministischen Vorwärtsprozess. Zehn neue
Sätze sind im vollständigen Lake-Build geprüft. Die formale Brücke lautet:

1. Anfangszustand und Eingaben sind eindeutig gebunden.
2. Zugelassene Zustände bleiben unter erlaubten Eingaben im deklarierten Bereich.
3. Ein einzelner Modellschritt stimmt unter der Referenzabbildung mit dem
   zugeordneten Referenzschritt überein.
4. Daraus folgt per Induktion die Übereinstimmung für jede zugelassene Schrittlänge.
5. Bei gültiger Messbindung und begrenztem Modellfehler bleibt der Fehler der
   übertragenen Prognose innerhalb der Summe beider Fehlergrenzen.

Der Schluss ist stärker als eine bloße Registermarkierung: Er leitet eine
Aussage über beliebig viele zugelassene Schritte aus einer lokalen
Übergangseigenschaft her. Die lokalen Korrespondenz- und Kalibrierungsvoraussetzungen
bleiben dabei offen sichtbar. Ein Referenzzustand ist hier ein mathematisch
beschriebener Zustand; seine Benennung zertifiziert kein physikalisches Gerät.

Zusätzlich sind konstruktiv bewiesen: Strikt gleiche Ordnungsinformation bestimmt
keinen eindeutigen metrischen Uhrenmaßstab; gleiche Koordinatendauer bestimmt
keine eindeutige Eigenzeit; ein beliebig langer endlicher Kalibrierungspräfix
bestimmt seinen nächsten Messwert nicht ohne weitere Annahme. Die exakten
Eigenzeitbeispiele sind gerade, zeitartige Trägheitssegmente einer flachen
Raumzeit mit einer räumlichen Dimension, `c=1` und ganzzahligen gemeinsamen
Auflösungseinheiten. Beschleunigte oder gekrümmte Weltlinien werden dadurch
nicht mitformalisiert.

Nachweis: [Kernelbeleg](evidence/measurement-binding/receipt.json),
[Quellen- und Axiomprüfung](AxiomAudit.lean), drei erwartete negative
Compilerkontrollen unter `evidence/measurement-binding/negative-controls/`.
Der aktuelle globale Axiom-Audit umfasst 68 Konstanten, darunter die zehn
neuen; im auf diesen Versuch begrenzten Audit bleiben 24 wiederverwendete
Sätze zusätzlich getrennt erkennbar. 40 Projektregressionen und die Prüfung
auf Beweisplatzhalter bestehen. Die Ergänzung des bestehenden Audit-Parsers
behandelt tatsächlich beobachtete mehrzeilige Axiomlisten vollständig.
Das veröffentlichte Alpha-2-Originalarchiv bleibt byte-identisch.

**Formal geschlossen:** die bedingte Übertragung und ihre Fehlergrenze sowie
präzise Gegenbeispiele gegen das Weglassen von Kalibrierung und Bereichsbindung.
**Empirische Restpflicht:** Für eine konkrete Naturvorhersage müssen Geräte,
Ereignisse, Weltlinien, physikalische Uhrenkalibrierung und der behauptete
Gültigkeitsbereich tatsächlich gebunden und die Beobachtungen unabhängig
bestätigt sein. Diese Daten werden durch den Kernel nicht erzeugt.
Die historische veröffentlichte Matrix ORRZ-009 wird nicht nachträglich geändert.

Veröffentlichte Ausgangsquellen: Ingolf Lohmann,
*QIK-VRT: Beobachterrelative Retrokausalität als negative Informationsrichtung*,
https://doi.org/10.5281/zenodo.21947141 ;
*Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP*,
https://doi.org/10.5281/zenodo.21888130 .
