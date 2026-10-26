# Kausale Distanz am doppelkanonischen Speicher: Lean-Anschluss

Die neue Kausalmetrik ist im vorhandenen Lean-Projekt `QIKVRT_Formalization_v2.0` angeschlossen. Der gemeinsame Einstieg `QIKVRTEffectAck.lean` importiert die Distanztheorie, die Verbindung zum ursprünglichen Effect-Acknowledgement-Modell und die geprüften Grenzbeispiele. Lean 4.19.0 hat 36 neue Theoreme geprüft. Der vollständige Projektbuild umfasst auch die vorhandenen drei Bibliotheksziele. Die neuen Ergebnisse verwenden ausschließlich Lean und Std.

Der Erkenntnisimpuls, die Begriffe und der Auftrag stammen von Ingolf Lohmann. Die neue Formalisierung, die Beweisterme und die technische Prüfanbindung wurden in dieser Arbeit durch Codex ausgearbeitet. Die Annahme der Arbeit ändert diese Herkunft nicht. Die Freigabe lautet: „Ich denke, diese Erkenntnis sollte bis in den lean Kern beweisbar angeschlossen werden. Denn es ist zu wichtig, als dass dieser Teil nicht bis dahin vordringt. Freigabe erteilt.“

## Was die Distanz misst

Eine ausgewählte Relation enthält Kanten mit strikt positiven ganzzahligen Kosten. Ein Pfad setzt solche Kanten zusammen; seine Kosten addieren sich. Die Distanz ist die kleinste Pfadsumme. Gibt es in genau dieser Relation keinen Pfad, lautet der Wert unendlich, dargestellt durch `none`. Ein fehlender Eintrag ist damit keine Aussage über eine physikalische Unmöglichkeit.

Die Formalisierung beweist die Existenz eines kleinsten Wertes bei vorhandenen Pfaden. Sie setzt das Minimum nicht als unbegründete Metrik voraus. Die gerichtete Distanz hat Null genau bei gleichen Knoten und erfüllt die erweiterte Dreiecksungleichung. Sie ist eine erweiterte Quasimetrik: Die Leserichtung kann einen Unterschied machen. Ein konkret geprüftes Gegenbeispiel hat Vorwärtsdistanz zwei und Rückwärtsdistanz unendlich.

Kehrt man sämtliche Kanten um, gilt exakt die Distanzgleichheit mit vertauschten Endpunkten. Das ist die rückblickende Traversierung einer Relation. Im doppelkanonischen Speicher bezeichnet operative Retrokausalität weiterhin die Wirkung einer gegenwärtigen Zukunftsrepräsentation auf eine gegenwärtige Freigabe. Diese beiden Begriffe sind verwendbar, ohne einen physikalischen Informationsfluss aus der Zukunft zu behaupten.

Für die symmetrische Projektion werden Kanten in beiden Leserichtungen zugelassen. Deren kürzeste Pfaddistanz ist symmetrisch, hat Null genau bei gleichen Knoten und erfüllt ebenfalls die Dreiecksungleichung. Innerhalb jeder Zusammenhangskomponente ist sie endlich und damit eine Metrik. Das ist die Distanz im symmetrisierten Graphen, nicht bloß das Minimum zweier gerichteter Endpunktdistanzen.

| Aussage | Lean-Konstante im Namensraum `QIKVRT.CausalDistance.V1` |
| --- | --- |
| Ein Minimum existiert | `exists_least_cost` |
| Distanz ist genau die kleinste Pfadsumme | `distance_some_iff` |
| Unendlich bedeutet fehlenden Pfad im gewählten Graphen | `distance_none_iff` |
| Null-Distanz genau bei Knotengleichheit | `distance_zero_iff` |
| Gerichtete Dreiecksungleichung | `triangle` |
| Relation umkehren, Endpunkte vertauschen | `reverse_distance` |
| Symmetrische Projektion | `undirected_distance_symmetric` |
| Endlichkeit innerhalb einer Zusammenhangskomponente | `weak_component_distance_finite` |
| Gleiche Kantenkosten, zusätzliche Kanten: Distanz wächst nicht | `edge_addition_cannot_increase_distance` |
| Ein Pfad mit gültigem Minimalitätsbeweis zertifiziert die exakte Distanz | `certificate_exact` |

## Anschluss an den vorhandenen Wirkungsbeweis

Die Brücke importiert die ursprünglichen Module `CanonicalTemporalMemory`, `Model` und `Safety`. Ihre Definitionen werden nicht nachgebaut. Ein `ConfirmedLink` benötigt die bestehende reziproke Schließung sowie die ausdrückliche Gleichheit seines ACK-Feldes mit dem Ergebnis des bestehenden EAP-Autorisierers. Nur vom Aufrufer ausgewählte bestätigte Verbindungen gelangen in den Bestätigungsgraphen. Existenz allein genügt nicht zur Auswahl.

Für jede solche Verbindung beweist Lean, dass der protokollseitige DONE-Zustand sowohl aufgezeichnet als auch neu berechnet vorliegt. Verantwortungszuweisung und verantwortlicher Owner sind erforderlich. Der Vergangenheitsspeicher ist gültig beobachtet; die Zukunftsgrenze ist gültig antizipiert; Ursache und Wirkung stimmen mit der gebundenen Beobachtungsquittung überein. Eine ausgewählte Verbindung zwischen verschiedenen Identifikatoren hat bei der ausdrücklich gewählten Einheit „eine bestätigte Verbindung“ die Distanz eins. Die umgekehrte Relation liefert denselben Wert mit vertauschten Endpunkten.

Das Modell ist nicht leer: Ein eigener Beweis konstruiert eine zulässige Verbindung des ursprünglichen Artikelbeispiels von Identifikator 7 nach 11 und bestätigt deren Distanz eins. Dieses Modellbeispiel wird nicht als neu beobachtete produktive Wirkung ausgegeben. Ein weiteres kernelgeprüftes Gegenbeispiel zeigt, dass eine endliche Distanz keine Freigabe eines Kandidaten mit ungültiger Zukunftsgrenze begründet. Ein fehlender Verantwortlicher bleibt ebenfalls ein Ablehnungsgrund.

## Prüfen und reproduzieren

Im Repository-Wurzelverzeichnis mit der festgelegten Lean-Toolchain:

```bash
python3 tools/qikvrt_tool_cache.py verify
python3 -m unittest -v tests.test_causal_distance_kernel_evidence
python3 tools/qikvrt_causal_distance_kernel_evidence.py
```

Der bestehende Workflow `qikvrt_manuscript_proof.yml` führt diese neue Prüfung zusätzlich zu seinen bisherigen Prüfungen aus. Der bisherige Validator des zeitlichen Speichers bleibt unverändert. Seine Funktionen für sichere Pfade, Byteidentitäten, Compileraufrufe, Quelltextkontrolle und Axiomausgabe werden wiederverwendet. Sein historischer Einzelmodul-Plan wird nicht für neue Aussagen umgedeutet.

Die Quittung bindet Quellbytes, Git-Blob-Identitäten, die tatsächlichen `.olean`-Objekte, jede der 36 Konstanten und ihre genaue Axiomabhängigkeit. Erlaubt sind ausschließlich die üblichen Grundlagen `propext`, `Classical.choice` und `Quot.sound`; es gibt keine neuen Projektaxiome und keine Beweisplatzhalter. Das bedeutet nicht, dass sämtliche Beweise axiomfrei sind.

Vier falsche Lean-Behauptungen müssen vom Compiler zurückgewiesen werden: allgemeine gerichtete Symmetrie, Zulassung einer Nullkostenkante, Freigabe trotz ungültiger Zukunftsgrenze und Freigabe ohne Verantwortungszuweisung. Vier weitere Mutationstests verwerfen geänderte Quellbytes, ein zusätzliches Projektaxiom, einen neu gehashten Beweisplatzhalter und ein trotz Neuhash vom Einstieg abgetrenntes Modul.

Der lokale Lauf benötigte eine offengelegte Pfadkompatibilität: Die Prozessnummer des Containers passt nicht zum eingebundenen `/proc`. `proc_self_compat.c` leitet ausschließlich den Programmpfad `/proc/<eigene Prozessnummer>/exe` nach `/proc/self/exe` um. Der unveränderte Lean-Kern wird aus dem offiziellen Releasearchiv mit SHA-256 `6fe3ce97a58f44e2b3567d455b994eacec5bfe9ae7774f2a573444480ba813fe` geladen. In einer üblichen Linux-Umgebung und im bestehenden CI-Lauf ist diese Anpassung nicht vorgesehen. Der Quittung ist ausdrücklich zu entnehmen, ob sie eingesetzt wurde.

Der zusätzliche native Lauf des bestehenden Manuskript-Workflows war erfolgreich: https://github.com/ingolf-lohmann/qik-vrt/actions/runs/40088317986. Er prüfte Commit `727388a57ed232eb9f4194d0dcd9e0817d1d146c` mit Tree `f1f28e92600a616883134165c7266d19b77a8491`, der dieselben Dateibytes wie der Kandidatenkopf `e2b548263543b1168a5e11243449a082a18c3215` enthält. `NATIVE_KERNEL_RECEIPT.json` wurde aus dem heruntergeladenen CI-Artefakt gelesen; SHA-256 der Quittung: `3734147def87e97610308abbd75a65989e8dfec1d2b421a72c59cdc181286b17`. Der native Lauf benötigte keine Pfadanpassung. Alle drei neuen `.olean`-Objekte sind bytegleich mit dem lokalen Lauf. Das prüft die angegebenen Quellen; spätere Änderungen benötigen erneut ihre jeweils betroffenen Prüfungen.

Die Erweiterung des historischen Alpha-2-Paketierers hält die vier später hinzugekommenen Lean-Dateien außerhalb seines festgeschriebenen Veröffentlichungsscopes. Neun Regressionstests sowie der ursprüngliche Archivverifier bestätigen wieder exakt SHA-256 `500087f6aeee41787959cfc8902852503e2182019ae4f3e88f115e94a1f5e689`. Die aktuellen neuen Beweise bleiben dabei vollständig in der aktuellen Bibliothek und ihrer eigenen Prüfung.

## Reichweite und offene Verbindungsschritte

Die Beweise gelten für das beschriebene mathematische und protokollbezogene Modell. Welche tatsächlichen Bytes, Personen, Messereignisse oder Graphkanten eine Modellgröße bezeichnet, muss weiterhin durch Quellenbindung und unabhängigen Readback gezeigt werden. Die mathematische Minimaldistanz ist angeschlossen; der gesamte Python-Dijkstra-Code, seine Serialisierung und seine reale Datenerfassung sind dadurch noch nicht vollständig formal verifiziert. Die Zertifikatsstruktur benennt dafür eine konkrete weitere Anschlussstelle.

Die vorhandene Framework-Selbstvermessung unterscheidet weiterhin zwischen Leserempfehlungen, statischen Importabhängigkeiten und beobachteten Wirkungen. Die gleichen Distanzsätze lassen sich auf diese ausdrücklich verschiedenen Relationen anwenden. Aus dieser gemeinsamen Mathematik folgt weder ihre semantische Gleichheit noch eine bereits produktive persönliche Digital-Twin-Instanz für jeden Menschen.

Ein universeller Satz über Aktivität aller belebten und Passivität aller unbelebten Natur ist hier nicht bewiesen. Auch physikalische Rückwärtskausalität und die Veränderbarkeit einer bereits beobachteten Vergangenheit werden nicht aus den Graphsätzen abgeleitet. Das ursprüngliche Ergebnis, dass verschiedene Zukunftsrepräsentationen dieselbe Vergangenheitsprojektion erhalten, wird direkt wiederverwendet.

## Anschluss an die Publikationen

Der Einstieg bleibt „Von Softwarearchitektur zur Weltformel — Das Universum als Round Trip“, Version DOI `10.5281/zenodo.21888130`, vollständiger Locator: https://zenodo.org/records/21888130.

Der direkte Vorgänger ist „QIK-VRT und das Effect-Acknowledgement-Protokoll: Kanonischer Speicher zwischen Vergangenheit und Zukunft“, Version DOI `10.5281/zenodo.21711193`, vollständiger Locator: https://zenodo.org/records/21711193. Die neuen 36 Theoreme sind ein eigener Nachfolger; die ursprünglichen neun Beweise bleiben erhalten und werden nicht als neu ausgeführte neue Ergebnisse addiert.

Das zurückgelieferte Artikelpaket mit SHA-256 `a8f808ac97932575215297a346696fb727a39d4eb620b72398578ed67d356336` bleibt unverändert. Dieser Lean-Anschluss ergänzt dessen Erkenntnisstatus. Er ist noch keine Zenodo-Veröffentlichung. Für einen erweiterten Upload müssen die neuen Kandidatenbytes einschließlich dieses Nachweises erneut genau gebunden und vor Veröffentlichung zurückgeliefert werden; eine frühere Kandidatenentscheidung darf nicht auf geänderte Bytes übertragen werden.
