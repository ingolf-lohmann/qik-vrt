# Prospektiver, falsifizierbarer Messplan

**Entwurf, 15.10.2026. Nicht extern präregistriert; Primärmessung nicht ausgeführt.**
Hypothese und Auftrag: Ingolf Lohmann. Testplanung: OpenAI Codex in seinem Auftrag.
Dieses Dokument und die exakten Geräte-/Softwarebindungen müssen vor Erhebung
der Primärdaten eingefroren werden. Nach Einsicht in Daten entsteht bei Änderung
ein neuer, getrennt benannter Versuchsplan.

## A. Zwei getrennte Untersuchungsziele

**A1: inverse Ordnung.** Ein Sender emittiert authentisch nummerierte und
nutzlasthaltige Records auf zwei Pfaden. Hardware-Taps messen beide Emissionen
und beide Ankünfte. Messgrößen sind Emissionsabstand, beide Laufzeiten,
Ankunftsabstand, Inversionsrate, Verlust und Doppelzustellung. Das Modell sagt
Überholen genau bei `d_old - d_new > s_new - s_old` voraus. Mit programmierter
zusätzlicher Verzögerung kann die Schwelle in beiden Richtungen überfahren
werden. Gleiche Laufzeiten, Pfadtausch und Zeitkalibrierung sind Kontrollen.
Ein bestätigter A1-Versuch bestätigt diese Transportaussage; er entscheidet A2
nicht. Ein Test mit absichtlich nichtnegativen Warteschlangen implementiert
das Vorwärtsmodell bereits und prüft kein neues Naturgesetz.

**A2: operationaler Rückkanal.** Ein eindeutig spezifizierter physikalischer
Kandidatenkanal soll eine vor der späteren Senderwahl abgeschlossene Beobachtung
`R_i` mit dem erst danach erzeugten, intervenierten Nachrichtenbit `B_i` verbinden.
Der feste Decoder für `R_i` muss vorab veröffentlicht sein. Erfolg bedeutet eine
aus den frühen Daten lesbare unbedingte Nachrichtenabhängigkeit, ohne Kenntnis
späterer Sortierklassen. Derzeit gibt es in den geprüften Quellen keine numerisch
gebundene QIK-VRT-Rückkanalvorhersage oder realisierte Ressource dafür. Die
folgende Effektgröße ist eine Prüfentscheidung, kein aus dem Zeugen abgeleitetes
Naturgesetz.

Ein bloß ontisches, rückabhängiges Modell, das exakt dieselben beobachtbaren
Verteilungen wie ein gewöhnliches Modell liefert, kann A2 nicht unterscheiden.
Dafür wäre zuerst eine abweichende beobachtbare Vorhersage nötig. Auch ein
negatives A2-Ergebnis widerlegt nicht sämtliche ontischen Interpretationen.

## B. Apparatur und gleiche Regeln

R ist ein Empfänger mit physikalisch gebundenem Detektor und festem Decoder;
S besitzt den benannten Kandidatenkanal/Aktor sowie einen separaten frischen
Zufallsgeber. W verwahrt frühere Originale und bezeugt Zeiten unabhängig von
R und S. Ein praktischer Kalibrierungsaufbau kann ein getaktetes ADC-/TTL-Paar
mit unabhängigen Signal-Taps sein. Seine normale Vorwärtsverkabelung ist die
Null-/Gerätekontrolle. Sie wird nicht als Kandidatenressource ausgegeben.

Vor Betrieb festzulegen: Kanalprinzip, Hersteller-/Serienkennungen, Firmware,
Sensor/Aktor und räumliche Positionen, Decoder, Messbandbreite, Analogschwellen,
Trigger, Vorverarbeitung, vollständiges Kalibrierprotokoll und Sicherheitsabstände.
Software-Nodes erhalten dieselbe eingefrorene Runtime, Version, Regelsätze und
Ressourcenbedingungen. Rollen sind getrennte identifizierte Prozesse oder Geräte;
Unabhängigkeit wird zusätzlich anhand Betreiber-, Strom-, Takt-, Speicher-,
Netzwerk- und Administrationsgrenzen untersucht. Gleiche Software begründet
Vergleichbarkeit, nicht automatisch Unabhängigkeit.

W kann intern als Verwahrer arbeiten oder als externer, über den Universal-
Transputer angeschlossener Metabeobachter. Im externen Modus sind seine
Beobachtungskanäle während des frühen Fensters technisch nur lesend; W darf
keine späteren Bits, Zeitkorrekturen oder Decoder an R zurückliefern. Eine
Freigabebestätigung ist ein eigener kausaler Eingriff und wird als solche
protokolliert. Ein retrospektiver Gesamtblick im Modell ist keine physikalische
Allwissenheit. Interner/externer Beobachter und passive/aktive Aufzeichnung sind
vorab getrennte Versuchsarme; sie werden nicht nach Ergebnis ausgewählt.

## C. Zeitfolge, Synchronisation und unabhängige Zeitstempel

Jeder geplante Slot bekommt vorab eine unveränderliche laufende ID und Nonce.
Die frühe Erfassung endet bei `E_i`; ein von späteren Daten unabhängiger Decoder
liefert `R_i` oder einen expliziten Ausfallmarker. Danach werden die Originalbytes,
Slot-ID, Gerätestand, Kalibrierung und Decoderidentität in einer kanonischen
Darstellung mit mindestens 256 Bit frischem Salt gebunden. W speichert diese
Bytes außerhalb der schreibbaren Domäne von R/S **vor** seiner Bestätigung,
beispielsweise in einem append-only Datenträger mit fsync und unabhängigem
zweitem Verwahrer. Erst die nachgewiesene Verwahrung schaltet den Sender frei.

Der physikalische Entropiegewinn für `B_i` beginnt erst danach. Ein gepufferter
Zufallsstring oder ein vorher gesetzter PRNG-Seed erfüllt das nicht. Ein
Host-CSPRNG ist eine Softwarekontrolle; seine späte API-Ausgabe beweist nicht,
wann die zugrunde liegende physikalische Entropie entstand. Für die Primärstudie
sind Ereignistaps des Zufallsgebers, Bias-/Gedächtnisdiagnose und eine begründete
bedingte Vorhersagbarkeitsgrenze erforderlich. `B_i` steuert anschließend die
vorgegebene physikalische Intervention. Deren tatsächliche Stellung wird durch
einen gesonderten Sensor protokolliert. Auch Nichtzustellungen bleiben Slots.

Eine zentrale Hardware-Zeitmarkierung erfasst frühe Detektion und Senderwahl.
Zusätzlich schreibt ein unabhängig betriebener Zeitzeuge die physikalischen
Taps und Verwahrungsbestätigung mit eigener Uhr. Für die Zuordnung werden
TAI-Nanosekunden mit expliziter UTC-Umrechnung verwendet; lokale monotone Zähler,
Clock-ID und Reboot-Epoche bleiben zusätzlich erhalten. Kalibrierung vor und nach
jedem Lauf bindet Offset, Drift, asymmetrische Kabel-/Netzlaufzeit, Jitter,
Digitizerauflösung und Triggerverzögerung. NTP oder ein Blockchain-/Hashstempel
allein liefert keine hinreichende Ereigniskalibrierung. Digitale Signaturen
authentisieren bei gültigem Schlüsselmanagement eine Aussage, nicht automatisch
ihre physikalische Uhrgenauigkeit.

Jeder Ereignisstempel ist ein Intervall `[t_min, t_max]`. Zur Zulassung müssen
mit dem gesamten Unsicherheitsbudget gelten:

`E_i.max < Lock_i.min < ... < W_ack_i.min`,

und präziser für jede benachbarte Ereignispaarung

`E_i.max < Lock_i.min`, `Lock_i.max < W_ack_i.min`,
`W_ack_i.max < EntropyStart_i.min`,
`EntropyStart_i.max < ChoiceComplete_i.min`.

Für den behaupteten Kanal in die eigene kausale Vergangenheit muss die frühe
Auslese zusätzlich invariant in der zeitartigen Vergangenheit der Senderwahl
liegen. Unter den deklarierten räumlichen Schranken verlangt das
`c * (EntropyStart_i.min - E_i.max) > L_max` mit Unsicherheitsreserve.
Eine mögliche langsame Kontrollgeometrie ist Abstand höchstens 10 m,
E→Entropiestart mindestens 100 ms und gesamtes Zeitbudget unter 1 ms. Dies sind
prospektive Designgrenzen, keine gemessenen Gerätewerte. Ein Kandidatenkanal
mit kürzerer Wirkungszeit benötigt einen neu begründeten Plan. Raumartige
delayed-choice-Anordnungen gehören zu einem gesonderten Test: Dort gibt es keine
beobachterunabhängige Reihenfolge „später“, und eine Lorentz-Koordinatenzuweisung
ist noch kein Signal in die eigene Vergangenheit.

Die Prüfdaten enthalten `early_end`, `locked`, `custody_ack`, `entropy_start` und
`choice_complete`, jeweils `lo_ns`, `hi_ns`, `clock_id`. Die Beispielstruktur
`SIMULATED_EXAMPLE.json` enthält ausdrücklich künstliche Zeiten. Der Offline-
Prüfer erkennt Intervallüberlappungen; er zertifiziert keine Kalibrierung und
implementiert noch keine physische Kanal- oder räumliche Abnahme.

## D. Hypothesen und vorab festgelegte Statistik

Primärgröße ist `X_i = 1[R_i = B_i]` in allen **N = 200.000 geplanten Slots**
einer vorab benannten A2-Kanalkonfiguration. Keine Verschiebung von Slotpaaren,
kein nachträglich trainierter Decoder, keine günstige Phase und keine Auswahl
passender Läufe. Es gibt genau einen zweiseitigen Primärtest. Die Gegenrichtung
wird damit von Anfang an berücksichtigt.

Die operationale Nullhypothese lautet: gegeben die bereits gesicherten frühen
Daten und die gesamte verfügbare Vergangenheit liegt die bedingte
Trefferwahrscheinlichkeit zwischen `1/2 - epsilon` und `1/2 + epsilon`, mit
einer **extern begründeten** Schranke `epsilon <= 0,001`. Bei idealen fairen,
frischen späteren Bits ist epsilon null, selbst wenn die frühen Bits beliebig
verzerrt sind oder Gedächtnis besitzen. Eine bloß marginal faire, aber aus der
Vergangenheit vorhersagbare Folge genügt dieser Annahme nicht.

Für Trefferzahl K und vollständige Daten gilt die konservative zweiseitige
Hoeffding-Schranke für beschränkte Martingaldifferenzen:

`p_bound = min(1, 2 exp(-2 N max(0, |K/N - 1/2| - epsilon)^2))`.

Vorab gilt `alpha = 0,001`. Bei N = 200.000 und epsilon = 0,001 wird die
Nullhypothese für `K >= 101.072` oder `K <= 98.928` verworfen. Die separat
berechnete ideale Binomialzahl wird als numerische Diagnostik ausgewiesen;
sie ersetzt die begründete Zufallsvoraussetzung nicht.

Für die ausdrücklich spezifizierte unabhängige Alternative mit stationärer
Trefferwahrscheinlichkeit 0,51 beträgt die numerische Power etwa 0,999984;
die zusätzliche konservative untere Schranke beträgt etwa 0,999818. Diese
Rechnung benutzt ein Alternativmodell, keine erhobene Effektmessung. Der
1-Prozentpunkt-Effekt wird nicht als QIK-VRT-Naturvorhersage dargestellt.

Ein Lückenrecord bleibt im Nenner. Wenn m Ergebnisse fehlen und k bekannte
Treffer vorliegen, wird der gesamte mögliche Bereich `[k, k+m]` ausgewertet.
Ein Signalalarm ist nur erlaubt, wenn jeder mögliche Wert dieses Bereichs
außerhalb der Nullzone liegt. Ein fehlender Record oder unerklärte Zeitlücke
verhindert darüber hinaus die physische Abnahme. Fehler dürfen nicht durch
Löschen von Slots repariert werden. Es gibt kein vorzeitiges Stoppen nach
p-Wert; vorgegebene technische Abbrüche und alle gestarteten Läufe werden
mit Gründen archiviert.

Zusätzlich wird eine konservative 99%-Schranke für den absoluten Trefferüberschuss
ausgewiesen. Eine Obergrenze unter 0,01 würde unter den ausgewiesenen Annahmen
die spezifizierte Mindestleistungsbehauptung dieses Apparats ausschließen.
Nichtsignifikanz allein beweist keine Abwesenheit. Zeitdrift und instationäre
Kanäle begrenzen die Übertragung einer solchen Schranke auf spätere Nutzung.

Weitere Kanäle, Distanzen, Beobachtermodi, Frequenzen, Lag-Scans und Decoder
bilden eine vorab definierte Testfamilie mit Alpha-Aufteilung oder eine
explorative Nachanalyse ohne bestätigenden Primärstatus. Replikationsdaten
bleiben unangetasteter Holdout. Die kleinen lokalen 2/4/8-Prozessläufe sind
bereits beobachtete Instrumentkontrollen und werden nicht rückwirkend mit
dieser Registrierung versehen.

## E. Kontrollen und konkurrierende Erklärungen

| Kontrollarm / Manipulation | Erkennungsziel | Entscheidung |
|---|---|---|
| Positiver zusätzlicher Pfaddelay, gleiche Delays, Pfadtausch | Gewöhnliches Überholen und Laufzeitunterschiede | A1-Schwelle samt Unsicherheit prüfen; kein A2-Schluss |
| Normaler Vorwärtskanal nach Wahl | Decoder, Aktor und Detektor funktionieren | Gute späte Antwort bestätigt Gerätefunktion, nicht frühe Wirkung |
| Kandidatenkanal blockiert / elektrisch und optisch getrennt | Leckage und Hintergrund | Frühe Marginale und Fehlerquote vergleichen |
| Scheinintervention mit gleicher Wärme/EM-Last | Gemeinsame Störgrößen | Unterschiede durch Versorgung, Takt, Temperatur oder Funk untersuchen |
| Unabhängiger frischer RNG, separater Seed-/Puffer-Audit | Gemeinsame Ursache und Vorwissen | Bedingte Unvorhersagbarkeit begründen; marginale Fairness reicht nicht |
| Verblindete feste Slot-Zuordnung; alle Detektorereignisse und Ausfälle | Postselektion, Coincidence-Lücken | Kein Löschen oder nur nachträgliches Zusammenführen günstiger Ereignisse |
| Vorab erlaubte Zeitverschiebungen und permutierte Nachrichtencodes | Autokorrelation und viele getestete Lags | Explorativ oder separat multiplicity-korrigiert, keine Decoderwahl am Holdout |
| Falscher Offset, Reboot, vertauschte Nonce, Replay, veränderte Frühdatei | Zeit-/Identitäts-/Archivfehler | Gesamten betroffenen Scope halten; keine Slotselektion |
| Konsistent eingespeiste gemeinsame Zukunftsdatei | Grenze reiner JSON-Prüfung | Darf statistisch auffallen, bleibt synthetisch und nie Physikbeweis |

Ein Schlüsselunterschied zum Sortieren von Quantum-Eraser-Daten ist die
unbedingte frühe Verteilung. Für bedingte Klassen gilt stets die Zerlegung
`P(R|B) = sum_z P(R|B,z) P(z|B)`. Gegenphasige Teilmuster können sich in
dieser Summe aufheben. Die bloße Änderung von `P(R|B,z)` zeigt keinen nutzbaren
Rückkanal. Der Primärdecoder darf B oder z nicht kennen. Bei Photonen müssen
alle frühen Einzelereignisse, Nullergebnisse, Dunkelzählungen und Effizienzen
gespeichert werden; Coincidence-Postselektion ist kein Ersatz dafür.

Ein später aus frühem R berechnetes B verletzt die Zufallsvoraussetzung und
erzeugt gewöhnliche Vorwärtskorrelation. Getrennte Verantwortlichkeit,
physische Isolation und originale Entropietaps adressieren diese Alternative.
Ein endlicher Test kann nicht alle denkbaren gemeinsamen Ursachen logisch
ausschließen. Ein reproduzierbarer Alarm eröffnet deshalb zunächst eine
gezielte Diagnose, keine unmittelbare ontische Kausalitätsbehauptung.

## F. Reproduzierbarkeit, Nutzen und Freigabegrenze

Vorab öffentlich zu binden sind Geräte-/Decoder-/Runtime-Digests, Kanalmodell,
Null-/Alternativhypothese, N, epsilon, Alpha, Testfamilie, Kalibrierungen,
vollständiges Verlust-/Abbruchverfahren und Auswertungscode. Originalbytes
erhalten unabhängige Signatur-/Hash-/Zeitbelege; Ableitungen bewahren die
Rohdaten. Ein unabhängiges Team erhält denselben eingefrorenen Plan und erstellt
eigene Rohdaten ohne gemeinsamen Daten-, Entropie- oder Administrationspfad.
Anderer Botname, zweite Repositorykopie und Wiederholung auf demselben Host
reichen dafür nicht.

Für Nutzbarkeit folgt nach einem unabhängig bestätigten Signalbefund eine
gesonderte Codierungsstudie: die Nachricht wird aus frühen Daten auf bislang
unbenutzten Slots dekodiert, mit vorab vereinbarter Bitfehlerrate, Nachrichtengröße,
Zeitvorsprung, Paketverlust und Kapazitätsabschätzung. Fehlerkorrektur und Auswahl
dürfen keine späteren Decoderinformationen verstecken. Eine p-Zahl allein
etabliert keine Kapazität und keinen praktisch bedienbaren Kanal.

**Aktueller erster externer Blocker:** Es fehlt ein benannter, steuerbarer
physikalischer Kandidatenkanal mit diskriminierender Vorhersage und qualifiziertem
Messaufbau. Wiederaufnahmebedingung: diese Geräte-/Kanal-/Kalibrier-/Zufalls- und
Verwahrungsbindungen sind tatsächlich verfügbar. Kleinster nächster Schritt ist
ihre Referenzbindung und eine blinde Kalibrier-/Leckageprobe vor jeder Primärserie.
Die vorhandenen REST-Operationen stellen diese Hardware nicht bereit. Ein
erfundenes positives Messergebnis oder eine erneute Softwarezählung schließt
diese Lücke nicht.

## Quellen

Die folgenden veröffentlichten Originale liefern die Definitionen und
Nachweisgrenzen; sie dokumentieren keine ausgeführte Primärserie dieses Plans.

- Ingolf Lohmann: Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP.
  https://doi.org/10.5281/zenodo.21888130
- Ingolf Lohmann: QIK-VRT: Beobachterrelative Retrokausalität als negative Informationsrichtung.
  https://doi.org/10.5281/zenodo.21947141
- Ingolf Lohmann: QIK-VRT: Epistemische Fairness, Vorstellungskraft und der Weg vom virtuellen Zeugen zum Beobachtungssystem.
  https://doi.org/10.5281/zenodo.21731492
- Ingolf Lohmann: Relationale Zeit, virtuelle Retrokausalität und die monoton wachsende Evidenzkugel.
  https://doi.org/10.5281/zenodo.22216916
