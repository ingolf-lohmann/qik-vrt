<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# QIK-VRT: Erkundung mit Gedächtnis

## Entdeckung, Abschluss und Rückbestätigung

Idee, Ziel und Auftrag: Ingolf Lohmann. Mathematische Ausarbeitung, Referenzcode
und Prüfungen: OpenAI Codex, künstliche Kognition. Datum: 4. Oktober 2026.

## Ergebnis und genaue Aussage

Die gespeicherte, eindeutig identifizierte Entdeckung eines Durchgangs ist ein
korrekter Existenzzeuge. Auf einem endlichen, statischen, zusammenhängenden,
ungerichteten Graphen entdeckt der einfache Zufallslauf alle Durchgänge mit
Wahrscheinlichkeit eins, unabhängig vom Startknoten. Daraus folgt noch keine
sicher erkennbare Abschlusszeit. Eine Erkundung mit vollständiger lokaler
Nachbarerfassung, Gedächtnis und offener Arbeitsliste terminiert und bestimmt
die exakte Durchgangsmenge der erreichbaren Komponente. Eine Aussage über den
gesamten Raum braucht zusätzlich den Nachweis, dass diese Komponente den ganzen
Prüfbereich umfasst, oder einen Einstieg in jede weitere Komponente.

Die uneingeschränkte Behauptung, räumliche Begrenzung und zufällige Bewegung
allein entschieden stets in garantiert endlicher Zeit zwischen null, genau
einem und mehreren Durchgängen, ist durch die folgenden Gegenbeispiele
widerlegt. Die Ergänzung ist ausdrücklich eine stärkere Spezifikation; sie
wird nicht rückwirkend der ursprünglichen Beschreibung zugeschrieben.

## 1. Definitionen und Voraussetzungen

Sei G=(V,E) ein endlicher, statischer, einfacher, ungerichteter Graph. V enthält
die möglichen Orte; E enthält die tatsächlich verfügbaren Bewegungen. Ein
Start s liegt in V. Eine feste, korrekt beobachtbare Funktion side: V ->
{innen, außen} gibt die Zugehörigkeit an. Ein Durchgang ist eine Kante mit
unterschiedlichen Seiten an ihren Endpunkten:

    B = { {u,v} in E : side(u) != side(v) }.

Die Durchgangsidentität ist die ungeordnete Kante {u,v}. Hin- und Rückweg
zählen einmal. Bei parallel vorhandenen Türen reicht ein Endpunktpaar nicht:
dann muss jede physische Tür eine eigene stabile Identität erhalten. Dieser
Multigraph-Fall liegt außerhalb der hier ausführbar geprüften Spezifikation.

C(s) bezeichnet die vom Start erreichbare Komponente. B_s enthält die
Durchgänge dieser Komponente. Ein lokales Nachbarorakel liefert bei der
Erweiterung eines Ortes vollständig und endlich alle angrenzenden Orte. Seine
Vollständigkeit, korrekte Seitenbeobachtung, stabile Identitäten und unveränderte
Quelle sind Modellvoraussetzungen. Ein Algorithmus kann diese Eigenschaften
nicht allein durch eine Behauptung seines Orakels garantieren.

Ein räumlicher Zaun impliziert weder endliches V noch Zusammenhang. Ein
beschränktes kontinuierliches Gebiet kann unendlich viele Orte enthalten.
Wenn beide Seiten vorkommen und der ganze Graph zusammenhängend ist, gibt es
mindestens eine Schnittkante. Der Fall null Durchgänge kann dann nur auftreten,
wenn eine Seite im Prüfbereich leer ist oder die Seiten getrennte Komponenten
bilden. Eine Erkundung aller Komponenten bleibt auch in diesem Fall möglich,
wenn jede Komponente separat zugänglich ist.

## 2. Satz C01: sichere Existenzzeugen und monotones Gedächtnis

Sei K_t die Menge aller bis zum Zeitpunkt t tatsächlich beobachteten und
identitätsgeprüften Durchgänge. Dann gilt K_t subset B und K_t subset K_(t+1).
Insbesondere: |K_t| >= 1 beweist mindestens einen Durchgang; |K_t| >= 2
beweist mehr als einen.

Beweis. Anfangs ist K_0 leer und damit Teilmenge von B. Ein Update fügt nur
eine beobachtete Kante mit ungleichen Seiten hinzu; diese gehört definitionsgemäß
zu B. Die Vereinigungsoperation entfernt keinen früheren Fund. Induktion über
die Updates beweist beide Invarianten. Mengensemantik und kanonische Identität
verhindern doppeltes Zählen des Rückwegs. Die beiden Folgerungen ergeben sich
aus der Inklusion. q.e.d.

Aus K_t leer folgt nur, dass bisher kein Durchgang gefunden wurde. Aus einem
einzigen Fund folgt zunächst nur eine untere Schranke.

## 3. Satz C02: Entdeckung durch einfachen Zufallslauf

Zusätzlich sei G zusammenhängend. An jedem Schritt wird gleichverteilt einer
der Nachbarn gewählt. Dann ist mit Wahrscheinlichkeit eins jede Kante und
damit jeder Durchgang nach endlich vielen Schritten traversiert. Der Satz gilt
für jeden Start. Im Ein-Knoten-Fall ist die Kantenmenge leer.

Beweis für n=|V| >= 2. Sei D der maximale Grad. Für jede feste Kante e={a,b}
und jeden aktuellen Ort gibt es einen einfachen Weg nach a mit höchstens n-1
Schritten; danach wird e traversiert. Diese konkrete Folge von höchstens n
Schritten hat bedingt auf den aktuellen Zustand eine Wahrscheinlichkeit von
mindestens p=D^(-n)>0. Also ist die Wahrscheinlichkeit, e in einem Block von
n Schritten zu verfehlen, höchstens 1-p. Wiederholte bedingte Anwendung ergibt:

    P(e nach k*n Schritten noch nicht traversiert) <= (1-p)^k.

Der Grenzwert ist null. Weil E endlich ist, ergibt die Vereinigungsabschätzung:

    P(mindestens eine Kante nach k*n Schritten fehlt) <= |E|*(1-p)^k -> 0.

Damit hat die vollständige Kantenüberdeckung Wahrscheinlichkeit eins. Es gibt
eine endliche erwartete Überdeckungszeit; beispielsweise ist die Summe der
Erwartungszeiten sukzessiver Kantenentdeckungen durch |E|*n/p beschränkt. Dieser
grobe Bound ist kein deterministischer Zeitschrankenbeweis. q.e.d.

Die bloße Aussage 'per Zufall' garantiert diese Voraussetzung nicht. Eine
Auswahlregel mit Nullwahrscheinlichkeit für eine nötige Bewegung kann einen
Durchgang dauerhaft auslassen. Auch veränderliche Wahrscheinlichkeiten brauchen
eine zusätzliche Fairness- oder Fortschrittsbedingung.

## 4. Gegenbeispiele C03: keine allgemeine sichere Abschlussregel

Betrachte den Weg 0--1--2. Die Orte 0 und 1 liegen außen, 2 innen. Der einzige
Durchgang ist {1,2}. Starte bei 0. Bei jedem Besuch von 1 kann der Zufallslauf
zurück nach 0 gehen. Die Folge (0,1,0) wiederholt sich k-mal mit der positiven
Wahrscheinlichkeit 2^(-k). Für jedes endliche Budget kann die Entdeckung daher
noch ausstehen. Eine feste Zeitüberschreitung beweist nicht null Durchgänge.

Unter einer Beobachtung, die nur die bisher traversierten Orte und Kanten
kennt und offene Nachbarn nicht vollständig erfasst, ist diese Beobachtungsfolge
auch mit einem Graphen vereinbar, der nur aus 0--1 besteht und keinen Durchgang
hat. Eine nach dieser Folge ausgegebene sichere Null-Aussage wäre in einem der
beiden Modelle falsch. Für genau einen gilt dasselbe durch einen noch nicht
besuchten zweiten Durchgang. Sobald das lokale Orakel sämtliche Nachbarn
liefert und ihre Bearbeitung nachweisbar abschließt, ist diese Ununterscheidbarkeit
aufgehoben. Das ist die im nächsten Satz eingeführte Ergänzung.

Die beiden Komponenten 0--1 und 2--3 mit Start 0 und side(2)=innen, allen
anderen Orten außen, liefern ein anderes Gegenbeispiel: B_s ist leer, global
existiert aber {2,3}. Bewegung in C(0) kann diese fremde Komponente nie erkunden.

Auch ein Besuch aller Orte genügt für reine Traversierung nicht: Im Dreieck
mit side(1)=innen und side(0)=side(2)=außen besucht der Weg 0->2->1 alle Orte,
traversiert jedoch die zweite Schnittkante {0,1} nicht. Benötigt wird der
Nachweis sämtlicher relevanter Kanten oder vollständiger Nachbarschaften.

## 5. Satz C04: terminierende vollständige Erkundung

Algorithmus: Starte mit der Arbeitsliste [s] und der Entdeckungsmenge {s}.
Entnimm einen Ort, erfasse seine ganze Nachbarschaft, registriere jede
Schnittkante und füge jeden noch nicht entdeckten Nachbarn einmal der
Arbeitsliste hinzu. Markiere den Ort als vollständig bearbeitet. Wiederhole,
bis die Liste leer ist. Jede Erweiterung verwendet denselben Quellensnapshot.

Terminierung. Jeder Ort wird wegen der Entdeckungsmenge höchstens einmal
eingereiht. Es gibt höchstens |C(s)| Entnahmen; jede bearbeitet eine endliche
Nachbarschaft. Als Rangfunktion dient |C(s)| minus die Zahl vollständig
bearbeiteter Orte. Solange die Liste nicht leer ist, sinkt diese natürliche
Zahl strikt bei jeder Entnahme. Der Algorithmus terminiert.

Vollständigkeit. Bei leerer Arbeitsliste ist jeder entdeckte Ort bearbeitet
und jeder seiner Nachbarn entdeckt. Die Entdeckungsmenge enthält s und ist
unter Nachbarschaft abgeschlossen. Induktion über die Länge jedes Weges von s
zeigt deshalb C(s) subset entdeckt. Umgekehrt werden nur Nachbarn bereits
erreichbarer Orte eingefügt; also entdeckt subset C(s). Die Mengen sind gleich.
Alle Nachbarschaften in C(s) wurden bearbeitet. Damit ist jede dortige Kante
inspiziert und jede Schnittkante genau einmal identitätsbezogen registriert.
Das Ergebnis ist exakt B_s. q.e.d.

Ein reales mobiles Gerät kann die logische Arbeitsliste durch einen
DFS-Rückweg auf einem gespeicherten Baum abarbeiten. Das erfordert tatsächlich
begehbare Rückwege und verlässliche Ortsidentität. Der Referenzcode modelliert
Orakelabfragen; eine physische Navigation oder deren Energiebedarf wurde hier
nicht verifiziert.

## 6. Satz C05: sicheres Abschlusszertifikat und globale Reichweite

Ein Zertifikat bindet Start, Quellensnapshot, bearbeitete Orte, deren vollständige
Nachbarschaften, inspizierte Kanten, Durchgangsidentitäten und Klassifikation.
Ein separater Prüfer vergleicht die Nachbarschaften mit der autoritativen Quelle,
prüft die erreichbare Menge und berechnet die Schnittmenge unabhängig neu.
Unter korrekter Quellenbindung bestätigt ein akzeptiertes Zertifikat exakt
B_s. Der Code verwendet dafür eine andere Erreichbarkeitsberechnung als der
Erkunder: booleschen transitiven Abschluss statt Arbeitsliste.

Für eine globale Aussage muss zusätzlich C(s)=V gelten. Andernfalls lautet
der Geltungsbereich ausdrücklich 'erreichbare Komponente'. Ein unabhängiger
Eintrittspunkt je Komponente, ein vollständiges externes Grenzkataster oder ein
anderer nachweislich erschöpfender Prüfweg kann die globale Abdeckung ergänzen.
Ein sich selbst als vollständig bezeichnendes Datenpaket ersetzt diese Bindung
nicht. q.e.d. unter den angegebenen Quellenannahmen.

Diese Informationsgrenze nutzt das bereits vorhandene Minimal Recovery Theorem
und `QIKVRTFormalization/Decision/ObservationSufficiency.lean`: Eine sichere
Entscheidung darf Beobachtungen, die verschiedene korrekte Antworten zulassen,
nicht gleichsetzen. Das neue Paket ergänzt den konkreten Irrgarten-Abschluss;
es ersetzt den vorhandenen allgemeinen Entscheidungssatz nicht.

## 7. Satz C06: was der kleine Ringschluss belegt

Im vorliegenden Dialog hat Ingolf Lohmann das Irrgartenprinzip beschrieben;
Codex hat es interpretiert und auf QIK-VRT bezogen; Ingolf Lohmann hat diese
Übertragung mit 'Richtig' bestätigt. Das ist ein dokumentierter, vom Nutzer
bestätigter Verständigungszyklus. Der genaue akustische Schlusszusatz bleibt
unsicher; die Aufzeichnung wurde nicht als vollständig wörtlich verifiziert.

Die Implikation 'eine Zusammenfassung wird akzeptiert, also ist jeder Lauf des
beschriebenen Algorithmus korrekt' ist ungültig. Gegenmodell: Dieselbe richtige
Zusammenfassung wird beim Graphen aus Abschnitt 4 akzeptiert, während der
Zufallslauf den Durchgang beliebig lange verfehlt. Sprachliches Verstehen und
algorithmische Abschlussgarantie sind verschiedene Aussagen. Die Bestätigung
belegt die geäußerte Annahme der Interpretation; sie ist keine unabhängige
Leistungs- oder Korrektheitsmessung des gesamten QIK-VRT-Produkts.

## 8. Ausführbare Prüfungen und ihre Grenze

Die Referenz `labyrinth.py` und der Prüflauf `check_labyrinth.py` untersuchen
alle 1.099 beschrifteten einfachen ungerichteten Graphen mit 1 bis 5 Knoten,
jede boolesche Innen/Außen-Zuordnung und jeden Start. Ergebnis: 168.146
Graph/Partition/Start-Fälle ohne Abweichung; davon 119.018 zusammenhängende
und 49.128 komponentenbegrenzte Fälle. Zusätzlich bestehen 19 Negativ- und
Grenzprüfungen, einschließlich gefälschter Zertifikate, fehlender Kanten,
doppelter Identitäten, asymmetrischer Eingaben und falscher globaler Aussagen.

Reproduktion: `python3 -B check_labyrinth.py --output TEST_RECEIPT.json`.
Die getestete Laufzeit ist CPython 3.12.14. Diese endliche exhaustive Prüfung
ergänzt den mathematischen Induktionsbeweis; sie ersetzt ihn nicht für beliebig
große Graphen.

`LabyrinthClosure.lean` formuliert zehn abstrakte Modelllemmas: Umkehridentität,
sicheres und monotones Gedächtnis, zwei Existenzzeugen, Erreichbarkeitsabschluss,
globale Abdeckung unter Zusammenhang, kein unendlicher strikter Rangabstieg,
Null- und Eindeutigkeitsschluss unter Vollständigkeit sowie ein Gegenmodell
zum Null-Schluss aus einem leeren Teilgedächtnis. Die lokale Lean-Ausführung
ist beim Start blockiert: Der Compiler benötigt `/proc/<pid>/exe`; dieser
Zugriff wird in der Ausführungsumgebung verweigert. Daraus wird keine
Kernelbestätigung abgeleitet. Die vorhandene Repository-Kernel-Pipeline ist
um die Prüfung dieses exakten Pakets ergänzt; ihre frische Quittung ist bis
zum erfolgreichen Rücklesen offen. Der Zufallslaufsatz bleibt eine schriftliche
mathematische Ableitung. Auch eine erfolgreiche Prüfung dieser zehn Lemmas
wäre noch kein Refinementbeweis des Python-Codes oder der produktiven Laufzeit.

## 9. Übertragung auf QIK-VRT

Die informatische Übertragung führt eine Menge identitätsgebundener Funde,
eine Menge bearbeiteter Gegenstände und eine Menge noch offener Arbeit.
Abschluss entsteht aus abgeschlossener Abdeckung des deklarierten Prüfbereichs
und frischem Ergebnis-Readback. Für neue Inhalte bleibt frühere Evidenz
historisch; sie beweist nicht den neuen Zustand. Ein Schreiben, eine
Transportbestätigung, eine Annahmeentscheidung und eine beobachtete Wirkung
erhalten getrennte Belege.

Das ist eine spezifizierte Übertragung der bewiesenen Modellinvarianten. Ein
Konformitätsbeweis der gesamten Laufzeit benötigt die Abbildung konkreter
QIK-VRT-Zustände und Operationen auf dieses Modell sowie entsprechende
Implementierungs-, Sicherheits- und Außenwirkungsnachweise. Diese Abbildung
ist hier eine erklärte Folgerungsanforderung, keine behauptete globale Abnahme.

## 10. Quellen, Provenienz und Prüfvermerk

Primärquellen zu den Standardverfahren:
1. MIT, 6.856 Lecture Notes: Markov Chains, Abschnitt Random walks on
   undirected graphs und General graph cover time.
   https://courses.csail.mit.edu/6.856/21/Notes/n25-markov-chains.html
2. Carnegie Mellon University, Graphs - Traversal Algorithms.
   https://www.cs.cmu.edu/~clo/www/CMU/DataStructures/Lessons/lesson5_2.htm

Die vorstehenden Beweise sind eigens für diese Aufgabe ausgearbeitet. Die
Quellen verankern Zufallslauf, Zusammenhang und systematische Grapherkundung;
sie sind weder ein Neuheitsnachweis noch eine Prüfung des gesamten QIK-VRT.

Repository-Basis der persönlichen Arbeitskopie: ingolf-lohmann/qik-vrt,
HEAD 93be182a277f29fcb1ffb5d4ace0483f6c29dc58,
TREE 25e36016536b45701abdc699c586394f53c69aa6. Authority Goldkelch/qik-vrt
ist über den vorhandenen GitHub-Connector derzeit nicht auflösbar (404).
Der öffentliche Universal Terminal liefert gesondert HEAD
f2fa5a5e11dafe6d9579301c2a479e0eaa02d16c und TREE
956c16b291c05243437b1f018321936e4438949a. Diese Subjekte werden nicht
gleichgesetzt. Sein Capability-Readback begrenzt die Terminal-Eingabe auf
`external_effects: NONE`.

Die Idee und der Auftrag sind menschliche Beiträge. Die mathematische
Ausarbeitung, der Referenzcode, die Tests und diese Redaktion sind künstlich
kognitive Beiträge. Die Zustimmung zu der früheren Zusammenfassung ist ein
menschlicher Beitrag; eine Annahme dieser neuen Beweisbytes wird nicht daraus
abgeleitet. Rohaufnahme und Rohtranskript werden nicht öffentlich hochgeladen.

Prüfvermerk: Modellbeweise ausgearbeitet; Gegenbeispiele ausgewiesen;
exhaustive endliche Prüfungen erfolgreich; unabhängige externe Begutachtung
und produktweiter Konformitätsbeweis bleiben separat offen. Eine öffentliche
Zenodo-Produktion bleibt an exakte Kandidatenrücklieferung, erforderliche
Kernelquittungen und die kandidatengebundene Owner-Entscheidung gebunden.
