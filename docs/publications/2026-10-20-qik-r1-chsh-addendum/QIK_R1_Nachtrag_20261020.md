# QIK R1 und der CHSH Benchmark

## Wissenschaftlicher Nachtrag zu Korrelationsgesetz und Akzeptanzbedingungen

Stand: 20. Oktober 2026. Bezug: wissenschaftlich revidierte QIK-Konzeptfassung vom 23. September 2026 und Forschungs-PR #552 im Authority-Repository `ingolf-lohmann/qik-vrt`.

Verantwortlicher Mensch und Aufgabensteller: Ingolf Lohmann. QIK-Rahmen und ursprüngliche Fragestellung: Ingolf Lohmann. Analyse, Prüfcode und Formulierung dieses Nachtrags: OpenAI Codex als künstlich-kognitiver Beitrag. Dieser Nachtrag ist ein eigener Review-Kandidat. Er ersetzt oder redigiert das Originalmanuskript nicht.

### Zusammenfassung

Der vorhandene Benchmark prüft vollständige Wahrscheinlichkeitstabellen für ein binäres Bell-Szenario und berechnet drei etablierte Referenzen korrekt. Seine 30 Regressionstests wurden auf dem gebundenen Quellstand erneut erfolgreich ausgeführt. Damit sind bestimmte Softwareeigenschaften und Referenzberechnungen belegt. Eine aus QIK bestimmte Wahrscheinlichkeitsregel wird dadurch nicht gewonnen.

R1 fordert neben No-Signalling die Reproduktion der quantenmechanischen Korrelationsmenge. Das ist stärker als die Reproduktion eines einzelnen CHSH-Maximums. Sowohl eine PR-Box als auch ein bereits im Benchmark enthaltener Gegenfall verdeutlichen die Lücke: No-Signalling ist zu schwach; selbst No-Signalling zusammen mit sämtlichen Tsirelson-CHSH-Obergrenzen ist zu schwach. Der Nachtrag präzisiert den benötigten Zustands-, Kompositions- und Messvertrag, trennt endliche Kontrollrechnungen von universellen Modellpflichten und gibt eine maschinenlesbare Abnahmespezifikation an. Eine neue physikalische Ableitung, ein vollständiger R1-Beweis oder ein empirischer Bell-Versuch wird nicht behauptet.

## 1 Quellenstand und Erhalt des Originals

Die Untersuchung bindet unterschiedliche Quellen ausdrücklich an ihre jeweiligen Revisionen. [Q1–Q4]

| Gegenstand | Gebundener Stand | Befund |
| --- | --- | --- |
| Authority Main | `a38455c739f7f475b2a93447de1db4ea87e4200c` | Root-Tree `b733ce6cc611dc59c426df531d9128efc0d000b9` |
| PR #552 | `71540655811c8725bb510be506f9308971d50aae` | Draft, offen, nicht integriert; Root-Tree `70ac08b249870a6f35f093ab228fa4c1d65b4a78` |
| Ursprüngliche Benchmark-Basis | `fbc450c4d2d5045335577aa59be7509cda16adeb` | Historische Basis; kein Ersatz für heutiges Main |
| Wissenschaftliches Original | §§ 4.4–4.5, 5/R1, 7.1–7.2 | Manuskript in aktuellem Main und PR-Quellbindung bytegleich |

Der SHA-256-Wert des Markdown-Manuskripts lautet `6b38b48148a9498c599fa9e0d677be71dd55de77243c950cf4714dc5a5e8747d`, sein Git-Blob `a2dd078527593151abd2e73f23495bfe2a39073c`, seine Größe 27.556 Bytes. Diese Identität bezeichnet das Markdown-Manuskript, nicht die versandte PDF oder ein DOCX.

Von den 22 in PR #552 gebundenen ursprünglichen Paketdateien besitzen 21 auch im geprüften Main weiterhin denselben Blob. Nur die README wurde zwischenzeitlich um einen Archivierungs-Readback ergänzt. Ihr heutiger Blob ist `9ccfa05b63946c8cb6dfc6299c634b34e5453685`; im Benchmark ist noch `981711fc163a55b5af7b6433fe23534dd5cd4bbc` gebunden. Der Archivierungsinhalt wird hier als Repository-Aussage behandelt; die Publikation selbst wurde für diesen mathematischen Auftrag nicht erneut extern abgenommen.

Der Test `test_original_publication_package_is_byte_unchanged` besteht mit den 22 historischen Originaldateien. Ein gezielter Austausch ausschließlich der README gegen den aktuellen Main-Stand lässt genau diesen Hash-Test fehlschlagen. Das ist ein reproduzierter Integrationskonflikt der Quellenbindung, kein mathematischer Fehler der CHSH-Rechnung. Vor einer Integration muss die historische Paketprüfung von der zulässigen Nachfolger-README unterschieden werden; die alten Belege bleiben erhalten. Das Originalmanuskript benötigt dafür keine Textänderung.

Der aktuelle Main-Baum enthält noch keine CHSH-Implementierung. Zum Prüfzeitpunkt waren für PR #552 keine Review-Einreichungen vorhanden. Seine frühere Volltestangabe wird als historischer Laufnachweis behandelt. Dieser Nachtrag beansprucht nur die hier frisch ausgeführten fokussierten Prüfungen, keinen neuen vollständigen Main- oder CI-Lauf.

## 2 Was R1 mathematisch verlangt

Die Originalfassung trennt bereits No-Signalling von einem vollständigen Quantengesetz. § 7.1 benennt Born-Statistik als zu reproduzierenden Vergleichsmaßstab und leitet sie ausdrücklich noch nicht aus QIK her. § 7.2 verlangt eine konkrete mathematische Struktur, die die zulässigen gemeinsamen Statistiken bestimmt. Das Tupel aus Ereignissen, Kausalordnung, Maß, Protokollen, Wahrscheinlichkeiten und Records benennt die Stellen des Modells; es bestimmt die Wahrscheinlichkeiten allein noch nicht. [Q1]

Für das aktuelle Szenario seien x,y ∈ {0,1} und a,b ∈ {−1,+1}. Ein Verhalten ist die vollständige Tabelle p(a,b|x,y), also 16 Zahlen. Die Korrelationen und eine CHSH-Orientierung sind

    E_xy = Σ_ab a b p(a,b|x,y)
    S = E_00 + E_01 + E_10 − E_11.

No-Signalling verlangt die Unabhängigkeit jeder lokalen Marginalverteilung vom entfernten Setting. Die Normierung gilt separat für jedes Settingpaar. Eine Verteilung der Settings ist für diese bedingten Tabellen nicht erforderlich. Für die lokale Hidden-Variable-Grenze ist dagegen die Settingunabhängigkeit der gemeinsamen Quellvariable eine eigene Annahme. Gleiche Settinghäufigkeiten sind kein Ersatz dafür.

Für einen präzisierten Szenariobereich Γ ist das Reproduktionsziel als Gleichheit zweier Mengen zu formulieren:

    C_QIK(Γ) = Q_target(Γ).

Die beiden Richtungen haben verschiedene Beweislasten:

1. **Korrektheit der zulässigen Menge:** Jede durch die QIK-Regeln zugelassene Tabelle gehört zur festgelegten Quantenmenge. Ein Kandidat darf insbesondere keine PR-Boxen oder andere überquantenmechanische Tabellen zulassen.
2. **Vollständigkeit gegenüber dem Ziel:** Jede Quantenverteilung des beanspruchten Bereichs ist durch eine zugelassene QIK-Präparation und QIK-Messung darstellbar. Ein rein lokales Modell erfüllt Obergrenzen, würde die zweite Richtung jedoch verfehlen.

Als Arbeitsziel der CHSH-Teilabnahme wird hier die Menge endlicher bipartiter Tensorprodukt-Realisierungen im Szenario (2,2,2) gewählt. Das ist eine ausdrücklich deklarierte Eingrenzung dieses Nachtrags. Das Original legt weder alle Szenarien noch Dimensions-, Abschluss- oder Tensorprodukt-/Kommutationskonventionen abschließend fest. Für eine allgemeine R1-Abnahme muss ein Kandidat diese Konventionen festlegen. Endliche Dimension, eine abgeschlossene Grenzwertmenge und ein allgemeines Modell mit kommutierenden Operatoren dürfen nicht stillschweigend gleichgesetzt werden.

R1 verlangt Reproduktion. Eine eigenständige Herleitung aus QIK ist eine zusätzliche Begründungs- und Ursprungspflicht des hier gesuchten Korrelationsgesetzes. Offen deklarierte Quantenpostulate könnten ein bedingtes erweitertes Modell definieren. Daraus folgt jedoch nicht, dass die ursprünglichen QIK-Postulate schon die Quantenmechanik implizieren.

## 3 Tatsächliche Testabdeckung

Die folgende Zuordnung bezieht sich auf die ausgeführten Testmethoden. Eine Methode kann mehrere endliche Unterfälle prüfen. Die Zahl 30 ist weder die Zahl aller mathematischen Fälle noch eine Evidenz für universelle Quantoren. Die vollständigen Methodennamen und Resultate stehen in `TEST_COVERAGE.json` und im Original-Testlog. [Q2–Q4]

| Testgruppe | Methoden | Tatsächlich geprüfte Eigenschaft | Aussagegrenze |
| --- | ---: | --- | --- |
| Lokale Referenzen | 3 | Gemeinsames faires Bit; alle 16 deterministischen Antwortbelegungen; eine nichtuniforme konvexe Mischung | Die allgemeine lokale Grenze verwendet zusätzlich das analytische Argument und Settingunabhängigkeit. |
| Born-Referenz | 3 | Alle 16 Wahrscheinlichkeiten der Bell-Referenz; ein nichtoptimales Winkelpaar; vier identische Winkelkonfigurationen | Ein fest gewählter Bell-Zustand und reelle XZ-Messungen; keine allgemeine Zustands-/POVM-Abnahme. |
| PR-Referenz und gemeinsame Konsistenz | 2 | PR-Parität; Normierung, faire Marginalen und No-Signalling der drei Referenzen | No-Signalling enthält keine Quantenmitgliedschaft. |
| Grenzen und Gegenkontrollen | 6 | Positive Grenzkontrollen; QM an lokaler Grenze abgelehnt; PR an Quantengrenze abgelehnt; negative Orientierung; umbenannte PR-Box; Gegenfall E=(1,1,1,1/2) | Alle acht CHSH-Vorzeichenmuster werden ausgewertet. Eine Schranke bleibt eine notwendige Bedingung. |
| Datenschnittstelle und Reproduzierbarkeit | 3 | Tabellen-Roundtrip; CLI für PR; deterministische Ausgabe und eingefrorenes Referenzergebnis | Ein erfolgreicher Prozess-Exit ist keine physikalische Akzeptanz. |
| Erhalt der historischen Quellen | 1 | SHA-256- und Git-Blobvergleich der 22 Originaldateien | Der Test bindet auch die inzwischen geänderte README; heutige Integration braucht eine explizite Nachfolgerbindung. |
| Ungültige Eingaben und Signalling | 12 | Fehlende/zusätzliche Zellen; ungültige Zahlen, Labels und Parameter; falsche Normierung; beide Signalling-Richtungen; CLI-Fehler | Belegt die konkreten Negativfälle und Eingangsprüfungen; keine erschöpfende Parser-Sicherheitsprüfung. |

Die Born-Implementierung berechnet Projektorwahrscheinlichkeiten auf dem Zustand Φ+ mit dem Tensorprodukt. Der Vergleich mit der geschlossenen Kosinusformel ist eine anders formulierte Rechenkontrolle desselben Standardmodells. Er stellt keine unabhängige physikalische Evidenz dar.

Die Ergebnisse lauten S=2 für das lokale gemeinsame Bit, S=2√2 für die gewählte Quantenreferenz und S=4 für die PR-Box. Die numerische Absoluttoleranz beträgt 10⁻¹². Negative Wahrscheinlichkeiten werden auch innerhalb dieser Toleranz abgelehnt; die Toleranz betrifft insbesondere Normierung und berechnete Residuen. Sie macht Gleitkommatests nicht zu exakten Gleichheitsbeweisen.

`candidate_report` meldet Quantenmitgliedschaft ausdrücklich als `NOT_DECIDED_BY_THIS_BENCHMARK`. Das CLI gibt für eine wohlgeformte PR-Tabelle Exitcode 0 und gleichzeitig `within_quantum_CHSH_ceiling=false` aus. Auch eine normierte signalisierende Tabelle kann erfolgreich ausgewertet werden; ihr No-Signalling-Feld fällt negativ aus. Nur der aufrufende Abnahmepfad darf aus den einzelnen Prüffeldern einen zulässigen Softwarestatus bilden. Exitcode 2 kennzeichnet ungültige Eingaben, nicht die allgemeine Ablehnung jedes physikalisch ungeeigneten Modells.

## 4 Zwei unterschiedliche Ausschlusslücken

### 4.1 No-Signalling reicht nicht

Die PR-Box hat faire lokale Marginalen und E=(1,1,1,−1). Sie erreicht S=4. Damit liefert sie einen etablierten, im Benchmark ausgeführten Gegenvergleich zur Folgerung aus No-Signalling auf die Quantenmenge. Sie ist keine physische Realisierung und kein QIK-Kandidat. [B1–B3]

### 4.2 Auch alle Tsirelson-CHSH-Obergrenzen reichen nicht

Die faire Tabelle p(a,b|x,y)=(1+ab E_xy)/4 mit E=(1,1,1,1/2) ist normiert und no-signalling-kompatibel. Ihr maximaler CHSH-Betrag ist 2,5 und damit kleiner als 2√2. Trotzdem ist sie nicht quantenmechanisch realisierbar. Im Operatorargument erzwingen die ersten drei perfekten Korrelationen die Gleichheit der entsprechenden Zustandsvektoren; damit muss auch die vierte Korrelation 1 sein. [Q2]

Der vorhandene Test überprüft, dass diese Tabelle die CHSH-Obergrenze besteht und keinen Quantenmitgliedschaftsstempel erhält. Er implementiert nicht den Ausschlussbeweis. Als zusätzliche numerische Diagnose im Prüfmaterial wird deshalb das etablierte Korrelatorkriterium im binären Zwei-Setting-Szenario ausgewertet: [B4]

    max_(s00 s01 s10 s11 = −1) |Σ_xy s_xy asin(E_xy)| ≤ π.

Für den Gegenfall ergibt die linke Seite 4π/3; der Überschuss beträgt π/3. Für die PR-Box ergibt sie 2π. Die Bedingung charakterisiert die vierdimensionale Quanten-Korrelatorprojektion. Bei exakt verschwindenden lokalen Mittelwerten bestimmt E bereits die ganze Tabelle; für vorgeschriebene nichtverschwindende lokale Mittelwerte genügt dieses Korrelatorkriterium allein nicht zur Abnahme der vollständigen Tabelle. Der beigefügte Code meldet deshalb nur eine numerische Korrelatordiagnose.

An den Grenzen von asin ist die Fehlerfortpflanzung besonders empfindlich. Die Diagnose clippt einen durch Normierungstoleranz geringfügig außerhalb [−1,1] liegenden Korrelator nicht auf den Rand. Sie meldet die Rundungsfrage offen. Exakte oder zertifizierte Aussagen benötigen algebraische Belege bzw. kontrollierte Fehlerintervalle.

## 5 Vertrag eines zukünftigen QIK-Korrelationsgesetzes

Ein zukünftiger Kandidat muss seine zulässigen Modelle bestimmen und daraus die Tabellen erzeugen. Eine gespeicherte Tabelle reicht nur als Eingabe für den bestehenden Auswerter. Die folgenden Regeln dürfen abstrakt operational formuliert werden; ein Hilbertraum ist keine unangekündigte Voraussetzung dieser Spezifikation.

### 5.1 Zustände und Präparationen

Anzugeben sind die Zustandsräume Ω_A, Ω_B und Ω_AB, ihre Typen, die Zulässigkeitsprädikate und eine deterministische Kodierung der Präparation. Klassische Randomisierung ist als konvexe Mischung mit positiv normierten Gewichten zu beschreiben; Wahrscheinlichkeiten müssen unter solcher operationaler Mischung affin sein. Nichtklassische gemeinsame Zustände dürfen nicht vorab auf Produkte oder auf lokale Hidden-Variable-Mischungen beschränkt werden, wenn Bell-verletzende Quantenstatistik zum Ziel gehört.

Die gemeinsame Präparation ist von der später gewählten lokalen Settingkombination zu unterscheiden. Dieselbe eingefrorene Präparation muss alle vier Zeilen eines Versuchsvertrags tragen. Eine pro Settingpaar passend ausgesuchte Quellverteilung wäre eine andere Modellklasse. Ein Manifest kann die Gleichheit von Präparations-Hashes prüfen; die behauptete kausale bzw. probabilistische Settingunabhängigkeit benötigt zusätzlich eine Modellbegründung.

### 5.2 Komposition und lokale Struktur

Eine Regel muss den gemeinsamen Zustandsraum, Produktpräparationen, die Einbettung lokaler Effekte und die Marginalbildung festlegen. Für unabhängige Präparationen wird die Produktwahrscheinlichkeit verlangt. Die gesamte Menge gemeinsamer Zustände darf trotzdem verschränkt sein. Discard-/Einheitseffekte u_A und u_B legen lokale Marginalen fest. Für einen Mehrsystemanspruch sind auch Assoziativität bzw. eine präzise Äquivalenz der Klammerungen und die Konsistenz weiterer Kompositionen erforderlich.

Weder eine Kausalordnung zwischen Ereignissen noch ein Zählmaß μ wählt von sich aus eine bestimmte Komposition, ein komplexes Amplitudenkalkül oder die Born-Regel aus. Tensorprodukte und sektorübergreifende Kommutation sind deshalb als importiert zu kennzeichnen, wenn sie gesetzt statt hergeleitet werden.

### 5.3 Messungen und Wahrscheinlichkeiten

Jedes lokale Setting ist durch eine zulässige Messung mit Effekten e^A_(a|x), e^B_(b|y) und eindeutigen Ergebnislabels zu kodieren. Effekte sind auf allen zugelassenen Zuständen positiv; die Summe der Effekte jeder vollständigen Messung ist der Einheitseffekt. Lokale inkompatible Settings benötigen keine gemeinsame klassische Vorabbelegung. Für getrennte Parteien ist hingegen eine kompatible lokale Einbettung zu definieren.

Die gemeinsame Wahrscheinlichkeitsregel muss explizit sein, beispielsweise operational als

    p(a,b|x,y; ω_AB) = (e^A_(a|x) ⊗ e^B_(b|y))(ω_AB).

Das Tensorzeichen steht hier für die eigens zu definierende Produkt-Effekt-Einbettung, nicht schon für ein bewiesenes Hilbertraum-Tensorprodukt. Unter positiv normierten Zuständen, normalisierten lokalen Messungen und einer konsistenten Marginalstruktur folgt No-Signalling durch Summation über den entfernten Effekt. Dass diese Voraussetzungen bei QIK gelten, bleibt Teil seiner Modellpflicht.

Für die ausdrücklich importierte Quantenrealisierung lauten die zusätzlichen Regeln ρ≥0, Tr ρ=1, F_(a|x)≥0, Σ_a F_(a|x)=I und entsprechend für G sowie p=Tr[ρ(F⊗G)]. Diese Regeln sind ein hinreichender Vergleichsrahmen. Eine Herleitung aus QIK benötigt die Abbildungen und Sätze, die ihn mit dem QIK-Kern verbinden, oder eine nachgewiesen gleichwertige andere Struktur.

Für den einmaligen CHSH-Vergleich reichen Effekte und Wahrscheinlichkeiten aus. Ein Anspruch auf sequenzielle Messprotokolle verlangt darüber hinaus Instrumente, Zustandsänderungen und deren Kompositionsregeln. Diese zusätzliche Dynamik wird hier nicht aus einem bestandenen Einzelschritttest gefolgert.

### 5.4 Anschluss an Ereignisse und Records

Der Kandidat muss erläutern, wie Präparation, lokale Settings, Resultate und spätere Vergleichsrecords mit E, ≺, μ, den Protokollen und Π verbunden sind. Unvergleichbarkeit in ≺ ist ohne weitere Rekonstruktion kein Nachweis physischer Raumartigkeit. Ein Ledger-Eintrag beweist die Speicherung seiner Bytes; er liefert keine quantenmechanische Zustandsregel und keine empirische Bell-Verletzung.

Alle 16 Modellwahrscheinlichkeiten sind mit den exakten Feldern `x,y,a,b,p` an `box_from_records` zu übergeben. Die Nullzellen bleiben explizit. Eine externe Kandidatenhülle bindet außerdem Gesetzesquellcode, Parameter, Präparation, Komposition, lokale Messungen, Annahmen und Rechentrace. Die bestehende Liste selbst wird nicht um Zusatzfelder erweitert, weil der Parser deren exakte Schlüsselmenge prüft.

## 6 Maschinenprüfbare Akzeptanzbedingungen

Die normative Prüfspezifikation dieses Nachtrags ist `ACCEPTANCE_CONTRACT.json`. Sie trennt **ausführbare endliche Kontrollen** von **noch einzulösenden, maschinenprüfbar zu belegenden universellen Beweispflichten**. Ein Hash oder ein vorhandenes PDF beweist nur Artefaktidentität. Für einen universellen Satz ist ein zum Satz passender überprüfter Beweisterm bzw. ein ausdrücklich festgelegtes anderes Zertifikatsverfahren erforderlich. Dafür existiert in diesem Nachtrag noch kein universeller QIK-Beweisprüfer.

| ID | Akzeptanzbedingung | Maschine bzw. Nachweis | Gegenwärtiger Status |
| --- | --- | --- | --- |
| AC00 | Originalmanuskript unverändert; aktuelle Quellen an Commit, Blob und SHA-256 gebunden | Byte-/Blobvergleich; veränderte README separat behandeln | PASS für die geprüften Quellen |
| AC01 | Kandidatengesetz, Domäne, Parameter und Annahmen vor dem Vergleich eingefroren | Manifest und reproduzierbare Ausführung; kein Rückgriff auf Zieltabellen im Gesetz | OPEN |
| AC02 | Zustandsmengen und Präparationen explizit; Normierung, Positivität, affine Mischung | Typ-/Wertekontrollen plus universeller Satz für den zugelassenen Zustandsraum | OPEN |
| AC03 | Komposition, lokale Effekte und Marginalen festgelegt | Produkt-, Marginal- und gegebenenfalls Mehrsystemkontrollen plus Strukturbeweis | OPEN |
| AC04 | Messregeln und Ergebniswahrscheinlichkeiten explizit aus dem Kandidaten berechnet | Aufruftrace vom Kandidateninput bis zu allen 16 Zellen | OPEN |
| AC05 | Tabelle vollständig, endlich, positiv und zeilenweise normiert | Bestehendes `box_from_records`; keine Umnormierung oder Postselektion | PASS für Referenzen; Kandidat OPEN |
| AC06 | Beide No-Signalling-Richtungen | Bestehende Residuen ≤10⁻¹² für Testfälle; universeller Kandidatensatz separat | PASS für Referenzen; Kandidat OPEN |
| AC07 | Alle acht CHSH-Orientierungen innerhalb der Quantengrenze | Bestehende Facettenprüfung; PR-Kontrolle negativ | PASS als Referenzkontrolle; Kandidat OPEN |
| AC08 | Quantengrenze und weitere Quantenstatistik erreichbar | Vollständige Born-Tabellen für optimale und nichtoptimale Settings; nicht jede Präparation muss maximal verletzen | PASS für importierte Referenz; Kandidat OPEN |
| AC09 | Quantenmitgliedschaft stärker als CHSH geprüft | Im passenden eingeschränkten Bereich Korrelatorkriterium; sonst vollständige Realisierungszertifikate/geeignete Ausschlussverfahren | OPEN für Kandidaten |
| AC10 | Alle zugelassenen Kandidatenverteilungen sind quantenmechanisch | Universeller, annahmengebundener Soundness-Satz | OPEN |
| AC11 | Alle Zielverteilungen sind durch Kandidaten erreichbar | Universeller Vollständigkeitssatz oder explizit eingeschränkter Familienbeweis | OPEN |
| AC12 | Ursprung jedes mathematischen Schritts offengelegt | Register: etabliert, importiert, neu angenommen, QIK-intern bewiesen, offen | OPEN für Kandidat; Referenzimporte ausgewiesen |
| AC13 | Rechenresultate, mathematischer Beweis und empirische Evidenz getrennt | Maschinenlesbare Evidenzklassen und getrennte Statusfelder | PASS für dieses Prüfmaterial |
| AC14 | Allgemeiner R1-Geltungsbereich ausdrücklich festgelegt | Szenarien, Dimensionen, Abschluss, Kompositionskonvention und Quantoren im Satz identisch | OPEN |

Ein Kandidat erhält erst nach AC01–AC04 und bestandenen fallbezogenen AC05–AC09 den Status einer **numerisch geprüften CHSH-Kandidatenfamilie**. Dieser Status enthält keine universelle R1-Abnahme. Ein mathematischer Reproduktionssatz im ausdrücklich erklärten Bereich braucht zusätzlich AC10 und AC11 sowie die Annahmenbindung AC12. Ein Anspruch auf eigenständige QIK-Herleitung verlangt die entsprechende Ableitung; importierte Quantenpostulate bleiben als solche sichtbar. Allgemeines R1 verlangt darüber hinaus AC14 und Beweise im gesamten beanspruchten Bereich.

Ein konkretes endliches Quanten-Realisierungszertifikat soll Dimensionen, eine Dichtematrix, sämtliche lokalen Effekte und die Zuordnung zur gelieferten Tabelle enthalten. Ein Prüfer kontrolliert Hermitizität, positive Semidefinitheit, Spur/Einheitssummen und jede berechnete Wahrscheinlichkeit. Numerische Eigenwerte oberhalb −ε liefern ohne kontrollierte Fehlerrechnung nur einen approximativen Befund. Ein solches Zertifikat zeigt die Zugehörigkeit einer Tabelle zur gewählten Quantenklasse; es zeigt weder die Vollständigkeit des QIK-Modells noch, dass sein Zustandsraum keine weiteren unzulässigen Tabellen enthält.

Auch ein bestandener endlicher NPA-Hierarchietest ist im Allgemeinen nur eine notwendige Außenapproximation. Das allgemeine Konvergenzziel ist ein Modell mit kommutierenden Messungen; es ist kein stillschweigender Beweis für das hier gewählte endliche Tensorproduktziel. Ein einzelner SDP-Lauf und eine Solver-Toleranz schließen diese Lücke nicht. [B5]

## 7 Ergebnis und konkrete Fortsetzung

Die prüfbare Leistung von PR #552 ist eine korrekt begrenzte Referenzrechnung und eine brauchbare Eingangs-/Auswertungsschnittstelle. Die bestehende Dokumentation verschweigt die fehlende QIK-Ableitung nicht. Der zusätzliche Nutzen dieses Nachtrags besteht in der expliziten Trennung von Mengen-Korrektheit und Vollständigkeit, den Regeln für einen Kandidateninput, der methodengenauen Testabdeckung und den getrennten numerischen und universellen Akzeptanzbedingungen.

Der nächste mathematische Liefergegenstand ist ein eingefrorenes QIK-Modell mit explizitem Zustandsraum, Komposition, lokalen Messungen und einer ausführbaren Wahrscheinlichkeitsregel. Danach werden dessen vollständige Tabellen mit den bestehenden Referenzen verglichen. Die Tabellen werden aus dem Gesetz berechnet; sie werden weder aus dem Referenzbericht kopiert noch nachträglich auf die Tsirelson-Grenze beschnitten. Unbekannte oder nicht belegte Modellpflichten bleiben OPEN.

Vor einer Repository-Integration ist außerdem die überholte README-Bindung des historischen Pakettests aufzulösen, ohne die ursprünglichen Quellen oder ihre historische Identität zu überschreiben. Dieser Nachtrag ändert weder das Originalmanuskript noch die produktiven wissenschaftlichen, Review- oder Veröffentlichungsgates. Eine Archivierung oder Repository-Integration wäre getrennt vom physikalischen Modellnachweis zu bewerten.

## Prüfmaterial und Reproduktion

Das Prüfmaterial enthält die unveränderten benötigten Referenzquellen, die Zuordnung aller 30 Testmethoden, deren frischen Laufbeleg, die gezielte README-Konfliktkontrolle und acht neue Tests der eng begrenzten Korrelatordiagnose und Statusgrenzen. Diese acht Tests bestehen ebenfalls. Sie sind neue Softwarekontrollen und werden nicht den ursprünglichen 30 Methoden zugerechnet.

Die Datei `README_PRUEFPAKET.txt` beschreibt die Offline-Aufrufe. `audit_reference_scope.py` verwendet den vorhandenen Benchmark über einen expliziten Quellpfad und prüft zunächst dessen Quellhashes. Eine optionale Kandidatentabelle erhält weiterhin weder einen Gesetzesnachweis noch eine R1-Freigabe. Die universellen Beweispflichten der Spezifikation sind nicht durch einen hier vorhandenen vollständigen QIK-Beweisprüfer implementiert.

## Quellen

Q1. Ingolf Lohmann, wissenschaftlich revidierte QIK-Konzeptfassung, 23. September 2026, §§ 4.4–4.5, 5/R1, 7.1–7.2. [Gebundenes Manuskript](https://github.com/ingolf-lohmann/qik-vrt/blob/a38455c739f7f475b2a93447de1db4ea87e4200c/docs/publications/2026-09-23-qik-scientific-revision/QIK_Publikationsfassung_revidiert.md).

Q2. Begleitdokument des CHSH-Minimalbenchmarks, insbesondere §§ 3–6. [Gebundene Fassung](https://github.com/ingolf-lohmann/qik-vrt/blob/71540655811c8725bb510be506f9308971d50aae/docs/QIK_R1_CHSH_MINIMALBENCHMARK.md).

Q3. Benchmark-Implementierung und Regressionstests. [Implementierung](https://github.com/ingolf-lohmann/qik-vrt/blob/71540655811c8725bb510be506f9308971d50aae/src/qikvrt_chsh_benchmark.py), [Tests](https://github.com/ingolf-lohmann/qik-vrt/blob/71540655811c8725bb510be506f9308971d50aae/tests/test_qikvrt_chsh_benchmark.py).

Q4. [PR #552](https://github.com/ingolf-lohmann/qik-vrt/pull/552), SOURCE_BINDINGS.json und REFERENCE_RESULTS.json auf dem genannten Kandidaten. Aktuelle Main-Metadaten und die gezielte README-Integrationskontrolle sind im Prüfmaterial separat festgehalten.

B1. J. F. Clauser, M. A. Horne, A. Shimony, R. A. Holt: Proposed Experiment to Test Local Hidden-Variable Theories. Physical Review Letters 23, 880–884 (1969). DOI [10.1103/PhysRevLett.23.880](https://doi.org/10.1103/PhysRevLett.23.880).

B2. B. S. Cirel'son: Quantum generalizations of Bell's inequality. Letters in Mathematical Physics 4, 93–100 (1980). DOI [10.1007/BF00417500](https://doi.org/10.1007/BF00417500). Die bedingte Operatorabschätzung ist auch in Q2 ausgeführt.

B3. S. Popescu, D. Rohrlich: Quantum nonlocality as an axiom. Foundations of Physics 24, 379–385 (1994). DOI [10.1007/BF02058098](https://doi.org/10.1007/BF02058098). Ergänzender Primärtext: [Nonlocality as an axiom for quantum theory](https://arxiv.org/abs/quant-ph/9508009) (1995).

B4. Ll. Masanes: Necessary and sufficient condition for quantum-generated correlations (2003), insbesondere Gleichung (5) und der erklärte Korrelatorbereich. [arXiv:quant-ph/0309137](https://arxiv.org/abs/quant-ph/0309137).

B5. M. Navascués, S. Pironio, A. Acín: A convergent hierarchy of semidefinite programs characterizing the set of quantum correlations. New Journal of Physics 10, 073013 (2008). [arXiv:0803.4290](https://arxiv.org/abs/0803.4290), DOI [10.1088/1367-2630/10/7/073013](https://doi.org/10.1088/1367-2630/10/7/073013).

## Technischer Integrationsnachtrag vom 20. Oktober 2026

Die vorstehenden 30-Test-Befunde bleiben dem ursprünglichen Quellstand zugeordnet. Der nachfolgende Integrationskandidat bewahrt sämtliche aktuellen Main-Dateien und die PR552-Historie. Der Erhaltungstest verwendet für die historische README ausschließlich deren bereits vorhandene bytegleiche Archivkopie. Die aktuelle Status-README wird gesondert an ihren eigenen Hash gebunden; Umleitungen eines Manuskripts oder auf beliebige andere Dateien werden durch eine neue Negativkontrolle abgelehnt. Beide Manuskripte und die alte SOURCE_BINDINGS.json bleiben unverändert. Zwei zusätzliche Methoden prüfen diese technische Reparatur. Die acht Korrelator-/Statuskontrollen laufen zusätzlich im bestehenden Makefile-Ziel.

Die neuen Quellen- und Prüfbefunde stehen in `evidence/chsh-reference/INTEGRATION_BINDINGS_20261020.json` und `INTEGRATION_VALIDATION_20261020.json`. Der technische Integrationsnachtrag ändert weder das physikalische Modell noch die offenen universellen Modellpflichten. Eine Main-Integration oder neue physikalische Bestätigung wird aus dem Kandidaten nicht abgeleitet.
