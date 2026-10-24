# Kausale Distanz im doppelkanonischen QIKVRT-Speicher

## Eine evidenzgebundene Pfadgeometrie zwischen Beobachtung, Antizipation und bestätigter Wirkung

Ingolf Lohmann · Independent Researcher · 24. Oktober 2026 · Anschlussarbeit mit Lean-Nachweis, Version 2.0.0

Anschluss an: QIK-VRT und das Effect-Acknowledgement-Protokoll: Kanonischer Speicher zwischen Vergangenheit und Zukunft. DOI: 10.5281/zenodo.21711193. https://zenodo.org/records/21711193

**Publikationsstatus dieses Kandidaten:** zur Prüfung zurückgegebene Fassung; eine neue Zenodo-Veröffentlichung wird erst durch den öffentlichen Record und bytegleichen Redownload bestätigt. Der Software-Nachweis ist lokal. Eine produktive Mesh-Abnahme und physische Retrokausalität werden nicht behauptet.

## Zusammenfassung

Räumlicher Abstand, zeitlicher Abstand und Abstand innerhalb einer Wirkungsabhängigkeit beantworten unterschiedliche Fragen. Diese Arbeit operationalisiert den dritten Begriff für einen endlichen, versionierten und evidenzgebundenen QIKVRT-Abhängigkeitsgraphen. Ausgangspunkt ist der publizierte doppelkanonische Speicher: Ein gemeinsamer Codec repräsentiert ausgewählte Beobachtungen und antizipierte Wirkungen, während die epistemischen Typen OBSERVED und ANTICIPATED getrennt bleiben. Eine gegenwärtig vorhandene Darstellung eines künftigen Akzeptanzzustands kann dadurch die gegenwärtige Freigabe einer Handlung beeinflussen. Der gerichtete kausale Abstand wird als kürzeste Summe positiver ganzzahliger Abhängigkeitsgewichte definiert. Er ist eine erweiterte Quasimetrik; die ungerichtete Projektion liefert eine Metrik auf jeder schwach zusammenhängenden Komponente. Die mathematischen Eigenschaften werden analytisch hergeleitet. Ein Anschluss an den vorhandenen Lean-4.19.0-Kern ergänzt die Herleitung um 36 neue geprüfte Theoreme mit konstantspezifischem Axiomaudit. Ein kontrollierter Softwareversuch verwendet den unveränderten QIKVRT-Protokollkern sowie den originalen Journal- und Terminal-Leser. Vier Eingangsbedingungen unterscheiden Freigabe und Verweigerung einer tatsächlichen lokalen Dateiänderung. Elf Journalereignisse bleiben nach erneutem Öffnen lesbar. 61 Tests umfassen Negativkontrollen und den Vergleich aller 4096 gerichteten Graphen auf vier Knoten mit einer unabhängigen Floyd-Warshall-Berechnung. Das Ergebnis ist eine begrenzte Messvorschrift für deklarierte Softwareabhängigkeiten, kein Maß sämtlicher Naturkausalität und kein Nachweis physischer Rückwärtswirkung.

## Abstract

This paper operationalizes causal distance within a finite, versioned and evidence-bound QIKVRT dependency graph. It extends the published canonical temporal memory model, whose OBSERVED and ANTICIPATED archives share a codec while retaining distinct epistemic types. A presently available representation of a future acceptance condition can affect present action admission. Directed distance is defined as the minimum total positive integer weight of a directed dependency path. It forms an extended quasi-metric; the undirected projection induces a metric on each weakly connected component. The analytical derivation is additionally connected to the existing Lean 4.19.0 / Std kernel through 36 checked theorems and an exact axiom-dependency audit. A controlled software witness reuses the unchanged QIKVRT Effect Acknowledgement core, event ledger and original terminal reader. Four conditions separate admission from refusal of an actual local file update. Eleven journal events survive reopening. Sixty-one tests include negative controls and all 4096 directed four-vertex graphs compared with an independent Floyd-Warshall oracle. The construction measures declared software dependencies at a fixed resolution. It does not establish a universal physical causal metric, biological cognition, productive Mesh acceptance or backward physical signalling.

Schlüsselwörter: kausale Distanz; doppelkanonischer Speicher; Effect Acknowledgement; Provenienz; gerichtete Graphen; Antizipation; Retrodiktion; QIKVRT.

## 1. Fragestellung und Anschluss an die Vorarbeit

Die Vorarbeit [1] beschreibt Vergangenheit und Zukunft in einer gemeinsamen Repräsentationsform. Das Vergangenheitsarchiv enthält ausgewählte realisierte Records, ihre Herkunft und ihren Erkenntnisstatus. Das Zukunftsarchiv enthält erwartete beziehungsweise geforderte spätere Wirkungen, die Herkunft der zugrunde liegenden Modelle, Akzeptanzbedingungen und Unsicherheit. Gleicher Codec bedeutet vergleichbare Darstellungsregeln; es bedeutet keine Gleichheit von Beobachtung und Erwartung.

Die neue Frage lautet: Wie lässt sich innerhalb eines solchen Arbeitszusammenhangs angeben, wie weit eine Eingangsbedingung von einer später überprüften Wirkung entfernt ist? Die Antwort soll numerisch, reproduzierbar und an eine konkrete Graphfassung gebunden sein. Sie soll zugleich verhindern, dass zeitliche Nähe, ein Integritätshash oder ein erfolgreiches Protokoll allein als vollständiger Kausalbeweis behandelt werden.

Die Beiträge dieser Anschlussarbeit sind deshalb begrenzt: eine explizite Distanzdefinition, die analytische Herleitung ihrer Eigenschaften, eine lesende Referenzimplementierung und ein kontrollierter lokaler Ausführungsnachweis. Die Pfadkonstruktion selbst steht in der Tradition gewichteter kürzester Wege [3]. Der zusätzliche QIKVRT-Beitrag liegt in der Bindung an typisierte Records, Versionen, Gegenstände und überprüfbare Evidenz. Eine neue fundamentale Naturmetrik wird nicht abgeleitet.

Als übergreifender Erkenntnisweg bleibt der in [2] formulierte Round Trip maßgeblich: Beobachtungen motivieren eine Architektur; deren Aussagen werden formalisiert oder getestet; die Ergebnisse werden innerhalb ihrer Voraussetzungen mit Beobachtungen abgeglichen. Eine thematische Anschlussbeziehung ersetzt keine Beweisabhängigkeit.

## 2. Drei unterschiedliche Abstandsaussagen

Räumlicher Abstand setzt eine räumliche Messvorschrift und gegebenenfalls ein Bezugssystem voraus. Zeitlicher Abstand setzt eine Uhr beziehungsweise eine ausgewiesene Zeitkoordinate voraus. Ein Abhängigkeitsabstand setzt dagegen einen Gegenstandsbereich, eine Relation und eine Gewichtung voraus. Zwei Ereignisse können zeitlich nahe sein, obwohl kein Einflussweg zwischen ihnen bekannt ist. Eine unmittelbare Softwareabhängigkeit kann eine lange Wartezeit enthalten. Sehr viele Verarbeitungsschritte können in kurzer physischer Zeit stattfinden.

Lamports Ereignisordnung [4] macht die Bedeutung dieser Unterscheidung für verteilte Systeme deutlich. Eine Uhrordnung liefert nicht ohne weitere Voraussetzungen dieselbe Information wie eine nachgewiesene Nachrichten- oder Prozessabhängigkeit. Auch eine vorhandene Einflussmöglichkeit und eine tatsächliche Ursache eines bestimmten Ergebnisses bleiben verschiedene Aussagen. Die systematische Behandlung von Kausalinterventionen in [6] begründet, weshalb zeitliche Reihenfolge und statistische Beziehung allein nicht genügen.

Für diese Arbeit bezeichnet eine kausale Kante daher eine im deklarierten Softwaremodell begründete unmittelbare Wirkungs- oder Datenabhängigkeit. Die Begründung kann aus kontrollierter Programmlogik, Intervention und beobachtetem Readback entstehen. Welche Evidenz ausreicht, muss zum jeweiligen Gegenstand angegeben werden. W3C PROV-DM [5] liefert ein anschlussfähiges Vokabular für Herkunft und Ableitung, aber keine automatische Garantie, dass ein Provenienzgraph vollständig oder wahr ist.

## 3. Zeitbezug, Retrodiktion und operationale Protokoll-Retrokausalität

Für einen Entscheidungszeitpunkt t werden die Archive als M_t = (H_t^-, H_t^+) geschrieben. H_t^- enthält typisierte Beobachtungen bis zum ausgewiesenen Erkenntnisstand. H_t^+ enthält heute repräsentierte Erwartungen, Ziele oder Akzeptanzbedingungen für spätere Zustände. Die Indizierung einer Erwartung mit einer späteren Zeit macht den Record selbst nicht zu einem Ereignis aus dieser späteren Zeit.

Dieser Unterschied präzisiert eine Besonderheit der Vorarbeit. Dort bezeichnet operationale Protokoll-Retrokausalität ausdrücklich die kontrafaktische Relevanz einer gegenwärtig verfügbaren, zukunftsindexierten Wirkungsbedingung für die gegenwärtige Freigabe. Diese autorenseitige Benennung wird hier beibehalten, einschließlich ihrer engen Definition [1, Abschnitte zum doppelten Speicher und zur Protokoll-Retrokausalität].

Davon sind zwei andere Bedeutungen zu unterscheiden. Retrodiktion rekonstruiert mögliche frühere Ursachen aus gegenwärtiger Evidenz. Physische Retrokausalität würde eine Abhängigkeit früherer physischer Zustände von späteren Bedingungen betreffen. In den von Wharton und Argaman diskutierten Modellen [7] sind entsprechende Future-Input-Abhängigkeiten Bestandteil der Modellarchitektur. Eine solche Modellstruktur ist weder durch einen rückwärts gelesenen Softwaregraphen noch durch die Berücksichtigung eines heutigen Plans experimentell nachgewiesen.

Die Vorarbeit liefert damit eine wichtige terminologische Disziplin: Die eigene operationale Benennung darf verwendet werden, solange ihre Definition sichtbar bleibt und nicht stillschweigend in die stärkere physikalische Behauptung übergeht. Der neue lokale Versuch prüft die operationale Abhängigkeit. Er verändert keine historischen Archivbytes und behauptet kein Signal aus einer bereits aktualen Zukunft.

## 4. Formales Messobjekt und Evidenzgrenze

Das Messobjekt ist ein endlicher gerichteter Graph G = (V, E, w). V ist eine endliche Menge verschiedener Record- oder Ereignisidentitäten. E enthält die ausgewählten gerichteten Abhängigkeiten. w ordnet jeder Kante eine positive ganze Zahl zu. Standardmäßig wird eine primitive Abhängigkeit mit einer Einheit gewichtet.

Jede Messung bindet mindestens fünf Angaben: den exakten Gegenstand, die Graphfassung, die Ereignisauflösung, die Gewichtung und die Evidenzklasse. Der Gegenstand kann durch Repository-, Commit-, Tree- und Laufidentitäten spezifiziert werden. Die Auflösung legt beispielsweise fest, ob ein Knoten einen Maschinenbefehl, einen Protokollschritt oder eine fachliche Entscheidung bezeichnet. Die Ebenen dürfen nicht ohne Kalibrierung verglichen werden.

Ein Belegrecord einer Kante enthält Anfang, Ende, Gewicht, Gegenstandsreferenz, Auflösung und Scope. Die Implementierung überprüft die Zuordnung zu seinen exakten Bytes. Ein Hash bestätigt hierbei die Inhaltsbindung unter den Hashannahmen, nicht die semantische Wahrheit der behaupteten Abhängigkeit. Die tatsächliche kausale Interpretation bleibt eine zusätzliche Prüfpflicht.

Aus Journalnummern oder Zeitstempeln werden keine Kanten automatisch erzeugt. Ebenso begründet ein gemeinsamer Vorgänger keinen gerichteten Einflussweg zwischen zwei Nachfolgern. Das ist besonders relevant bei Verzweigungen: Aus A nach B und A nach C folgt keine Kante B nach C.

Für die zeitliche Interpretation werden verschiedene Graphen nicht unmarkiert zusammengezogen. Ein Graph tatsächlich ausgeführter Ereignisse, ein Planungsgraph und ein hypothetisches Wirkmodell besitzen verschiedene Evidenzklassen. Im lokalen Beispiel sind auch die Zukunftsbedingungsrecords gegenwärtig erzeugte und gelesene Darstellungen. Ihr gewünschter Zielzustand ist kein bereits beobachteter zukünftiger Knoten.

## 5. Definition der gerichteten Distanz

Für verschiedene Knoten a und b sei P_G(a,b) die Menge aller gerichteten Pfade von a nach b. Die Länge eines Pfads ist die Summe seiner Kantengewichte. Definiert wird:

    d_G(a,b) = min { sum(w(e), e in p) : p in P_G(a,b) }.

Für a = b gilt d_G(a,a) = 0. Ist P_G(a,b) leer, wird d_G(a,b) = unendlich gesetzt. Die Software stellt diesen Fall als distance: null gemeinsam mit NO_PATH_IN_BOUND_GRAPH dar, weil JSON keine geeignete standardisierte unendliche Zahl enthält.

Die Bedeutung der Unendlichkeit ist strikt auf G beschränkt. Sie besagt, dass im ausgewiesenen Graphen kein gerichteter Pfad vorhanden ist. Sie beweist weder, dass eine tatsächliche Abhängigkeit ausgeschlossen ist, noch, dass die Beobachtung vollständig war. Ein unbekannter Knoten wird gesondert als Eingabefehler zurückgewiesen.

Bei Einheitsgewicht zählt d_G die minimale Anzahl primitiver Abhängigkeitsschritte. Mit anderen positiven ganzzahligen Gewichten kann eine ausgewiesene Kostenkonvention verwendet werden. Unsicherheit, Dauer oder Wirkungsstärke werden nicht stillschweigend zu Gewichtungen umgedeutet. Hierfür wären zusätzliche Kalibrierungen und eigene Geltungsbereiche nötig.

Die Definition misst einen kürzesten Pfad, nicht die Länge jeder tatsächlichen Ausführung. Sie ist außerdem abhängig von der Kantenkonvention. Würde man zusätzlich zu A nach B und B nach C eine transitive Abkürzung A nach C mit Gewicht eins eintragen, änderte sich der Abstand. Für vergleichbare Messungen müssen deshalb dieselben primitiven Relationen und Auflösungen verwendet werden. Diese Abhängigkeit ist ein Bestandteil der Messvorschrift.

## 6. Analytische Eigenschaften und symmetrische Metrik

Die folgenden Aussagen sind analytische Folgerungen aus dem angegebenen Modell. Abschnitt 9.3 verbindet die positive ganzzahlige Distanz und das ursprüngliche Protokoll zusätzlich mit 36 kernelgeprüften Lean-Theoremen. Die formale Graphdefinition erlaubt beliebige Knotentypen; die konkrete Softwareauswertung bleibt auf ihre ausgewählten endlichen Graphen bezogen.

**Existenz eines Minimums.** Ist b von a erreichbar, kann aus jedem Weg mit wiederholten Knoten ein Zyklus entfernt werden. Weil jede Kante positives Gewicht hat, wird der Weg dadurch kürzer. Ein kürzester Weg kann deshalb unter den einfachen Pfaden gesucht werden. In einem endlichen Graphen existieren nur endlich viele einfache Pfade. Eine nichtleere endliche Menge ihrer Längen besitzt ein Minimum.

**Nichtnegativität und Trennung.** Jede Pfadlänge ist nichtnegativ. Der leere Pfad von a nach a hat Länge null. Jeder nichtleere Pfad hat mindestens das positive Gewicht einer Kante. Folglich gilt d_G(a,b) = 0 genau dann, wenn a = b.

**Gerichtete Dreiecksungleichung.** Sind die Distanzen von a nach b und von b nach c endlich, ergibt die Verkettung zweier kürzester Pfade einen zulässigen Weg von a nach c. Das Minimum von a nach c ist höchstens dessen Länge. Damit gilt d_G(a,c) <= d_G(a,b) + d_G(b,c). Ist eine der rechten Distanzen unendlich, gilt dieselbe Ungleichung im erweiterten nichtnegativen Zahlbereich.

**Fehlende Symmetrie.** Aus einem Pfad von a nach b folgt allgemein kein Pfad von b nach a. d_G ist daher im Allgemeinen eine erweiterte Quasimetrik. Der Begriff Metrik darf für diese gerichtete Größe nicht ohne Erläuterung verwendet werden.

Für eine symmetrische Größe wird die ungerichtete Projektion U(G) gebildet. Jede belegte Kante kann dort mit demselben Gewicht in beiden Suchrichtungen durchlaufen werden. Bestehen entgegengesetzte Kanten mit verschiedenen Gewichten, werden sie als entsprechende alternative Wege behandelt. m_G(a,b) ist die kürzeste gewichtete Pfadlänge in U(G).

Der Beweis von Nichtnegativität, Identität und Dreiecksungleichung gilt auch für m_G. Zusätzlich kann jeder ungerichtete Pfad bei gleicher Länge umgekehrt werden; deshalb ist m_G symmetrisch. Innerhalb jeder schwach zusammenhängenden Komponente ist m_G eine endliche Metrik. Zwischen Komponenten erhält man eine erweiterte Metrik mit unendlichen Abständen.

Die Symmetrisierung erkauft ihre Metrikeigenschaft mit einem Bedeutungswechsel: Sie beschreibt strukturelle Verbundenheit, nicht gerichtete Einflussmöglichkeit. Bei einer gemeinsamen Ursache A können B und C im Projektionsgraphen Abstand zwei haben, obwohl weder B von C noch C von B gerichtet erreichbar ist. Ein retrospektiver Abruf der Ursache a einer Wirkung b fragt dagegen die ursprüngliche Distanz d_G(a,b) ab; er erzeugt keine neue Wirkungskante in Gegenrichtung.

## 7. Ausführbarer lokaler Nachweis

Der Versuch verwendet die originalen Module qikvrt_effect_ack.py, qikvrt_temdd_event_ledger.py und qikvrt_effect_ack_http_terminal.py des gebundenen Quellstands. Ihre Bytes werden gegen gelieferte Git-Blob-Identitäten geprüft. Das mitgelieferte Begleitpaket [E1] enthält die Originalquellen, die neue lesende Distanzkomponente, den Ausführungsharness, einen getrennten Verifikator und Rohbelege. Es ist Bestandteil des neuen Publikationskandidaten; sein Archivierungsstatus wird separat dokumentiert.

Die Anfangsbeobachtung ist ein bewusst einfacher Testzustand: Ein isolierter lokaler Zähler hat den Wert zwei. Das Vergangenheitsarchiv repräsentiert diesen Zustand mit dem Typ OBSERVED. Die spezifizierte Aktion erhöht den Wert um eins; ihre deterministische Modellprognose lautet daher drei. Das Zukunftsarchiv enthält eine geforderte Zielzahl und den Typ ANTICIPATED.

Im ersten Fall entspricht die geforderte Zielzahl drei der Prognose, und die Verantwortung ist zugeordnet. Der originale Protokollkern gibt die Aktion frei. Der Harness schreibt tatsächlich die lokale Datei mit dem Wert drei. Ein separater Python-Prozess liest die Datei und berechnet ihren Hash.

Im zweiten Fall wird nur der exogene Zielwert auf vier geändert. Die daraus abgeleiteten Prüfprädikate ändern sich; eine Erhöhung um eins erfüllt die Bedingung nicht. Die Aktion wird nicht freigegeben und die Datei bleibt bei zwei. Der dritte Fall ersetzt den Zukunftsarchivtyp ANTICIPATED durch OBSERVED und prüft die Verwechslung einer Erwartung mit einer Beobachtung. Auch dann bleibt die Datei unverändert. Im vierten Fall fehlt die Zuordnung der Verantwortung; die passende Zielzahl allein genügt nicht zur Freigabe.

| Fall | Erwartungs-/Zulassungsbedingung | Lokale Freigabe | Tatsächlicher Dateiwert |
|---|---|---|---:|
| admitted | Ziel 3, ANTICIPATED, Verantwortung vorhanden | ja | 3 |
| changed_future | Ziel 4 bei derselben Aktion | nein | 2 |
| wrong_future_type | OBSERVED anstelle von ANTICIPATED | nein | 2 |
| missing_authorization | Ziel 3, Verantwortung fehlt | nein | 2 |

Die Bytes und der Digest des ursprünglichen Vergangenheitsarchivs bleiben in allen vier Fällen gleich. Dies ist ein konkreter Nichtüberschreibungsnachweis für den Testgegenstand. Er ist kein Beweis, dass beliebige Speicherimplementierungen oder beliebige Fremdsysteme dieselbe Eigenschaft besitzen.

Der originale Ledger schreibt elf Ereignisse in ein frisches lokales Testjournal. Der originale Terminal-Leser überprüft jedes Ereignis über eine eigene schreibgeschützte Datenbankverbindung. Nach dem Schließen des Writers werden die Ereignisse erneut gelesen und bytegleich verglichen. Aus dem beobachteten Resultat drei entsteht anschließend ein neuer beobachteter Record und die nächste Erwartung vier. Gezeigt wird ein begrenzter Feedbackschritt. Ein dauerhaft autonom laufender produktiver Executor wird dadurch nicht etabliert.

## 8. Distanzwerte und Testumfang

Der erklärende Programmgraf enthält sechs Identitäten: Vergangenheitsrecord, gegenwärtiger Zukunftsbedingungsrecord, Gate, Dateiänderung, Readback und Feedbackrecord. Die ersten beiden Records gehen als getrennte Eingänge in das Gate ein. Es folgen Gate nach Dateiänderung, Dateiänderung nach Readback und Readback nach Feedbackrecord. Alle fünf Kanten haben Gewicht eins.

Damit beträgt der gerichtete Abstand vom Vergangenheitsrecord zum Readback drei. Vom Zukunftsbedingungsrecord zum Gate beträgt er eins. Vom Vergangenheitsrecord zum Feedbackrecord beträgt er vier. In Gegenrichtung vom Readback zum Vergangenheitsrecord existiert kein gerichteter Pfad, während die symmetrische Projektion den Abstand drei liefert. Elf gespeicherte Journalereignisse bedeuten folglich nicht elf kausale Abstandseinheiten; Journalumfang und Abhängigkeitsauflösung sind unterschiedliche Größen.

Die 61 dokumentierten Tests bestehen aus 16 neuen Metrik- und Witness-Tests, 41 originalen EAP-Tests und vier ausgewählten originalen Writer-Kontinuitätstests. Der exhaustive Graphentest durchläuft sämtliche 2^12 = 4096 gerichteten Graphen ohne Selbstkanten auf vier benannten Knoten. Für jeden Graphen werden die gerichteten und symmetrischen Abstände mit einer unabhängig implementierten Floyd-Warshall-Berechnung verglichen. Zusätzlich werden alle 64 Knotentripel auf die jeweiligen Dreiecksungleichungen geprüft. Gewichtete Beispiele und Negativtests ergänzen diese endliche Untersuchung.

Ein getrennter Verifikator prüft gespeicherte Protokolle, die tatsächlichen Dateiinhalte, die archivierten Eingangsbytes, die ursprünglichen Journalereignisse und die wiederholten Terminal-Readbacks. Seine Negativkontrollen verändern gezielt Dateistand, Erwartungstyp, DONE-Protokoll, Journalquittung, Distanzwert oder Abschlussbehauptung. Die veränderten Belege werden zurückgewiesen. Eine erfolgreiche Produzentenausgabe allein genügt damit nicht zum Bestehen der Auswertung.

Die Graphkanten beschreiben bekannte Abhängigkeiten des kontrollierten Programms. Nicht jede Kante wurde durch ein eigenes isoliertes Interventionsexperiment identifiziert. Der Graph ist deshalb ein begründetes Programmmodell mit ausgewiesenen Interventionen und kein automatisches Verfahren zur Entdeckung sämtlicher Ursachen. Der ursprüngliche lokale Zeuge beansprucht für sich weder einen vollständigen Repository-Test noch eine Lean-Ausführung oder eine externe Laborreproduktion. Der später hinzugekommene Lean- und Integrationsnachweis ist davon getrennt in Abschnitt 9.3 gebunden.

## 9. Bedeutung für künstlich kognitive Systeme

Die technische Aufgabenstellung lautet, erhaltene Erfahrung, aktuelle Eingänge, mögliche Handlungen, erwartete Folgen und tatsächlich beobachtete Ergebnisse verbindlich miteinander zu koppeln. Der doppelkanonische Speicher hält unterschiedliche epistemische Rollen auseinander. Effect Acknowledgement prüft eine Freigabebedingung. Der Journal- und Readbackpfad macht einen begrenzten Ausführungsschritt nachprüfbar. Die Distanzfunktion ergänzt diese Architektur um eine numerische Auswertung ihrer ausdrücklich modellierten Abhängigkeiten.

Keine dieser Komponenten allein ist ein vollständiger Kognitionsnachweis. Ein Protokoll generiert nicht von selbst zutreffende Ziele, Modelle oder Bedeutungen. Ebenso unterscheidet die pauschale Gegenüberstellung aktiv und passiv biologische Lebendigkeit nicht zuverlässig. Technische Systeme können selbsttätig regeln, ohne biologisch lebendig zu sein. Die vorliegende Arbeit behandelt funktionale Handlungs- und Nachweisfähigkeit, nicht eine Definition des Lebens oder des Bewusstseins.

Für experimentelle Anwendungen eröffnet die Architektur eine überprüfbare Dokumentationsmöglichkeit: Hypothesen, erwartete Ergebnisse, Entscheidungskriterien und Eingangsbytes können vor einer Handlung gebunden und später mit dem Readback verglichen werden. Eine behauptete Vorhersageleistung braucht jedoch zusätzlich ein vorab festgelegtes Auswertungsverfahren, unabhängige Daten, geeignete Vergleichsmodelle und eine Kontrolle nachträglicher Auswahl. Ein vorab veröffentlichter Hash allein garantiert weder Unbekanntheit der Eingabe noch kausale Unabhängigkeit.

Auch Quantenexperimente gewinnen durch eine bessere Provenienz kein automatisch anderes physikalisches Ergebnis. Eine Behauptung physischer Retrokausalität müsste unterscheidende Vorhersagen und geeignete Kontrollen gegenüber gewöhnlicher Konditionierung, Planung und globaler Modellierung angeben [7]. Die neue Distanzdefinition liefert hierfür ein mögliches Instrument zur Beschreibung eines Versuchsaufbaus, keine Abkürzung um dessen empirische Nachweispflichten.

## 9.1. Erste Selbstvermessung des Frameworks

Die Distanzkomponente wird zusätzlich auf zwei ausdrücklich verschiedene Ausschnitte des Frameworks angewendet [E2]. Im Publikationskatalog mit Prüfstand 11. Oktober 2026 werden die 32 Datensatzfamilien als Knoten und die vorhandenen sieben kuratierten Leserouten als Quelle gerichteter Empfehlungsbeziehungen verwendet. Nach Zusammenfassung identischer Knotenpaare enthält dieser Graph 19 Kanten. 50 der 992 geordneten Paare verschiedener Knoten sind gerichtet erreichbar; der größte endliche gerichtete Abstand beträgt fünf Empfehlungsschritte. Der Graph besitzt 13 schwach zusammenhängende Komponenten, darunter elf isolierte Knoten. Das bezeichnet den Umfang dieses historischen Empfehlungsnetzes, keine Aussage über fehlende Naturkausalität oder die Qualität der isolierten Veröffentlichungen.

Der zweite Ausschnitt verwendet sämtliche zehn Python-Quelldateien im src-Verzeichnis des gebundenen Repository-Quellstands. Eine statische AST-Auswertung findet 15 verschiedene interne Importabhängigkeiten. 21 der 90 geordneten Paare verschiedener Module sind innerhalb dieser Auswahl gerichtet erreichbar; der größte endliche Abstand beträgt drei Importstufen. Drei gefundene QIKVRT-Importstellen verweisen auf Module außerhalb der ausgewählten zehn Dateien. Daraus folgt zunächst eine Auswahlgrenze; ein außerhalb der Auswahl liegender Import wird nicht pauschal als global fehlende Datei behandelt. Statische Importe sind außerdem mögliche Codeabhängigkeiten, kein Nachweis, dass eine bestimmte Wirkung im laufenden Mesh eingetreten ist.

Für beide Ausschnitte werden dieselbe Distanzimplementierung, positive Einheitsgewichte und getrennte Evidenzklassen verwendet. Die Messwerte dürfen deshalb nicht zu einer einzigen universellen Kausalzahl addiert werden. Gerade die Trennung macht die Selbstanwendung wissenschaftlich brauchbar: Sie zeigt, welche Art Anschluss tatsächlich vermessen wurde und welche zusätzliche Laufzeitevidenz für eine stärkere Behauptung fehlt.

## 9.2. Interessenabhängige Leserouten und persönlicher Digital Twin

Eine ausführbare, rein lesende Erweiterung erzeugt aus dem vorhandenen Katalog sieben Leserouten: Grundidee, mathematische Beweisfrage, Physik und Kosmogenese, Zeit und Retrokausalität, natürliche Kognition und Verantwortung, künstliche Kognition sowie Implementierung und Auslieferung. Der Round-Trip-Einstieg wird, wo nötig, als gesonderter redaktioneller Präfix vorangestellt. Die deklarierte Leserreihenfolge bleibt erhalten; ein kürzester Weg im überlagerten Empfehlungsgraphen wird nicht ungeprüft als didaktisch optimale Reihenfolge ausgegeben.

Das Lesemodell ist an ein ausdrücklich angegebenes Personenprofil gebunden. Für Ingolf Lohmann werden Interessen und gewünschte Darstellungsart gespeichert; dieselbe Profilstruktur lässt sich ohne Codeänderung für eine andere deklarierte Person verwenden. Ein menschlicher und ein künstlich kognitiver Konsument erhalten dieselben Quellenidentitäten und dieselben Erkenntnisgrenzen. Sechs zusätzliche Tests prüfen Reihenfolge, Personenbindung, unterschiedliche Profilhashes, unbekannte Interessen, verbotene Aktionsrechte und Unveränderlichkeit des Kataloginputs.

Dies realisiert eine wiederverwendbare, lesende Wissensansicht als begrenzten Baustein eines persönlichen Digital Twin. Es ist noch kein produktiv abgenommener vollständiger persönlicher Zwilling. Dafür sind unter anderem autorisierte persönliche Datenquellen, bestätigte Identität, Zugriffstrennung, Widerruf, Erhalt offener Verpflichtungen sowie tatsächliche Terminal-/Transputer-Fortsetzung separat zu integrieren und zu prüfen. Die vorliegende Profilfunktion behauptet weder eine Authentisierung der deklarierten Person noch Handlungsvollmacht. Universelle Anschlussfähigkeit bleibt ein Architektur- und Interoperabilitätsziel, dessen einzelne Schnittstellen jeweils Evidenz benötigen.

## 9.3. Anschluss bis zum vorhandenen Lean-Kern

Der neue Nachweis wird durch den bestehenden Bibliothekseinstieg QIKVRTEffectAck eingebunden. Drei neue Module behandeln die Distanzkonstruktion, ihre Verbindung zum unveränderten doppelkanonischen Speicher und EAP-Autorisierer sowie konkrete Grenzbeispiele. Der Quellstand ist zusammen mit dem reproduzierbaren Paket QIKVRT_Lean_Anschluss_20261024.zip und der unveränderten nativen Prüfquittung NATIVE_KERNEL_RECEIPT.json Bestandteil dieser Einreichung. Die 36 neuen Theoreme sind eigenständige Nachfolger; die neun ursprünglichen Speicherbeweise werden nicht als weitere neue Ergebnisse mitgezählt.

Die Distanz wird im Beweis aus Pfaden und strikt positiven natürlichen Kantengewichten konstruiert. Die Existenz einer kleinsten Pfadsumme bei vorhandenen Pfaden wird bewiesen. Der Wert none bezeichnet ausschließlich Unerreichbarkeit in der ausgewählten Relation. Lean prüft Null-Distanz genau bei Knotengleichheit, die gerichtete erweiterte Dreiecksungleichung, die exakte Gleichheit beim Umkehren der Relation und Vertauschen der Endpunkte sowie die Symmetrie der ungerichteten Projektion. Innerhalb einer Zusammenhangskomponente ist die Projektionsdistanz endlich. Zusätzliche Kanten gleicher Kosten können den Abstand nicht vergrößern. Ein Pfad mit einem gültigen Minimalitätsbeweis kann eine konkrete Distanz zertifizieren.

Die Protokollbrücke übernimmt die ursprünglichen Definitionen. Eine ausgewählte bestätigte Verbindung benötigt die vorhandene reziproke Schließung und die ausdrückliche Bindung ihres ACK-Feldes an das Ergebnis des ursprünglichen EAP-Autorisierers. Damit bleiben ein aufgezeichneter und neu berechneter DONE-Zustand, Verantwortungszuweisung und verantwortlicher Owner erforderlich. Vergangenheit und antizipierte Zukunftsgrenze müssen gültig sein; Ursachen- und Wirkungsidentifikatoren müssen zur beobachteten, gebundenen Quittung passen. Zwischen verschiedenen Identifikatoren hat eine ausgewählte Bestätigungsverbindung bei der deklarierten Einheit einer Verbindung den Abstand eins.

Ein kernelgeprüftes Modellbeispiel mit den Identifikatoren 7 und 11 zeigt, dass diese Brücke bewohnbar ist. Es ist ein Beispiel des formalen Modells, kein neuer produktiver Laufzeitbeleg. Weitere bewiesene Grenzfälle zeigen eine gerichtete Distanz zwei bei unendlicher Rückwärtsdistanz, die Ablehnung einer beobachteten anstelle einer antizipierten Zukunftsgrenze und das Fortbestehen der Verantwortungsanforderung. Eine endliche Graphdistanz allein bestätigt keine Wirkungsfreigabe.

Der bestehende native Manuskript-Workflow hat alle 36 Theoreme, die exakten Axiomabhängigkeiten und vier absichtlich falsche Lean-Kontrollen geprüft. Vier Mutationstests verwerfen geänderte Quellbytes, ein zusätzliches Projektaxiom, einen neu gehashten Beweisplatzhalter und ein vom Einstieg abgetrenntes Modul. Der bestehende Proof-Escape-Audit prüfte 58 Lean-Dateien. Neue Projektaxiome und Beweisplatzhalter fehlen. Die üblichen Lean-Grundlagen propext, Classical.choice und Quot.sound werden in der konstantspezifischen Quittung offengelegt. Ein lokaler und ein nativer Lauf erzeugten bytegleiche kompilierte Objekte der drei neuen Module. Der native Lauf benötigte keine lokale Pfadkompatibilität. Auch ein frischer Aufbau des Pakets in einem leeren Verzeichnis bestand.

Die separate Integrationsprüfung erreichte den nativen getesteten Fixpunkt für Commit b1863b75e29cb455b88740ade4441312af9caa8f mit Tree 184adc9c40b27cce1be4995d2eae895d3fbbd2ee. Die anschließende Integration auf Main wurde bei Commit a1a2204f429bcab7a184afaf51a57b7de03d4ee7 mit demselben Tree zurückgelesen. Diese Identitäten bezeichnen den abgegrenzten Quell- und Integrationsnachweis, keine produktive Mesh-Abnahme. Die vollständigen nativen Belegidentitäten sind als Provenienz innerhalb des Begleitmaterials erhalten.

Die Formalisierung beweist Folgen des deklarierten Graph- und Protokollmodells. Die tatsächliche Zuordnung zu Bytes, Identitäten, Messereignissen und physikalischen Vorgängen bleibt eigens zu verifizieren. Der gesamte Python-Dijkstra-Code und seine Serialisierung werden dadurch nicht als vollständig formal verifiziert ausgegeben. Auch ein allgemeiner Satz über alle belebten oder unbelebten Systeme, physikalische Rückwärtswirkung und eine vollständige produktive persönliche Digital-Twin-Instanz folgt nicht aus den Graphsätzen.

## 10. Ergebnis und nächste überprüfbare Schritte

Die kausale Distanz ist innerhalb des spezifizierten Softwaremodells als gewichteter Abhängigkeitsabstand messbar gemacht. Ihre gerichtete und ihre symmetrische Variante werden mathematisch auseinandergehalten. Der kontrollierte lokale Lauf zeigt die Verbindung von typisiertem Vergangenheitsarchiv, gegenwärtig repräsentierter Zukunftsbedingung, protokollgebundener Freigabe, tatsächlicher Dateiänderung und erneutem Readback. Damit ergänzt die Arbeit die publizierte Speicherarchitektur um eine konkrete Messvorschrift und einen reproduzierbaren technischen Testgegenstand.

Die neue Distanzformalisierung ist inzwischen kernelgeprüft und die Erweiterung nach vollständigem Repository-Test auf Main integriert. Offen bleiben eine produktive native Mesh-Ausführung, eine stärkere unabhängige Identifikation einzelner Kanten, eine externe unabhängige Laborreproduktion und experimentelle Vergleiche verschiedener Auflösungen. Weitergehende Aussagen über Naturkausalität, lebende Systeme und Bewusstsein erfordern jeweils eigene Definitionen und Evidenz. Die Stärke des Ergebnisses liegt in seiner überprüfbaren Begrenzung: Eine deklarierte Relation erhält eine explizite Zahl, eine explizite Einheit und einen nachvollziehbaren Nachweisweg.

## Quellen und Begleitmaterial

[1] Ingolf Lohmann: QIK-VRT und das Effect-Acknowledgement-Protokoll: Kanonischer Speicher zwischen Vergangenheit und Zukunft. Working Paper, Version 1.0.0, 2026. DOI: 10.5281/zenodo.21711193. https://doi.org/10.5281/zenodo.21711193 · https://zenodo.org/records/21711193

[2] Ingolf Lohmann: Von Softwarearchitektur zur Weltformel - Das Universum als Round Trip. Version 1.0.0-candidate.1, 2026. DOI: 10.5281/zenodo.21888130. https://doi.org/10.5281/zenodo.21888130 · https://zenodo.org/records/21888130

[3] E. W. Dijkstra: A note on two problems in connexion with graphs. Numerische Mathematik 1, 269-271, 1959. DOI: 10.1007/BF01386390. https://doi.org/10.1007/BF01386390 · https://www.cs.yale.edu/homes/lans/readings/routing/dijkstra-routing-1959.pdf

[4] Leslie Lamport: Time, Clocks, and the Ordering of Events in a Distributed System. Communications of the ACM 21(7), 558-565, 1978. DOI: 10.1145/359545.359563. https://doi.org/10.1145/359545.359563 · https://lamport.azurewebsites.net/pubs/time-clocks.pdf

[5] W3C: PROV-DM: The PROV Data Model. W3C Recommendation, 30 April 2013. https://www.w3.org/TR/2013/REC-prov-dm-20130430/

[6] Judea Pearl: Causal inference in statistics: An overview. Statistics Surveys 3, 96-146, 2009. DOI: 10.1214/09-SS057. https://doi.org/10.1214/09-SS057 · https://ftp.cs.ucla.edu/pub/stat_ser/r350.pdf

[7] K. B. Wharton und N. Argaman: Colloquium: Bell's theorem and locally mediated reformulations of quantum mechanics. Reviews of Modern Physics 92, 021002, 2020. DOI: 10.1103/RevModPhys.92.021002. https://doi.org/10.1103/RevModPhys.92.021002 · https://arxiv.org/abs/1906.04313

[E1] QIKVRT_Causal_Distance_20261024.zip. Eingefrorenes lokales Begleitpaket dieses Kandidaten, 262030 Bytes, SHA-256 d070ae7e9c15feeadedddf55b3bf77072a3b74289dad60bb3adce4aee7089f91. Das Paket enthält SOURCE_BINDING.json, MANIFEST_SHA256.json, Quelltext, Testlogs, vier Versuchsbedingungen und die elf Journalreadbacks. Die dauerhafte Repository-Ablage ist separat nachgewiesen; eine neue öffentliche Zenodo-Archivierung dieses Pakets ist vor dem Publikationsreadback noch offen.

[E2] QIKVRT_Framework_Selbstvermessung_20261024.zip. Reproduzierbare lesende Framework-Auswertung mit Quellenbindung, Katalogsnapshot, zwei getrennten Graphklassen, Personenprofilen, sieben Leserouten und sechs zusätzlichen Tests. 201027 Bytes, SHA-256 01d874f116d68119c3278345bc09fb72fcd1917e88dd27e51b726ef950b3e542. Dieser historische Katalogstand und diese statische Quellauswahl sind keine vollständige aktuelle Vermessung des produktiven Mesh.

[K1] Formale Anlagen dieses Beitrags: QIKVRT_Lean_Anschluss_20261024.zip, NATIVE_KERNEL_RECEIPT.json, PUBLICATION_KERNEL_RECEIPT.json und KERNEL_PROOF_PLAN.json. Sie binden die 36 neuen Theoreme an Quellen, Axiomprüfung und native Beweisobjekte.

## Transparenz, Rechte und Zitation

Architekturgedanke, Begriffsarbeit und wissenschaftliche Verantwortung: Ingolf Lohmann. Textausarbeitung, Programmierung, Formalisierung und technische Prüfungen wurden mit Codex im autorisierten Auftrag ausgearbeitet. Die Nutzung eines KI-Systems ersetzt weder fachliche Begutachtung noch unabhängige Reproduktion. Die analytische Herleitung und die 36 neuen kernelgeprüften Theoreme sind getrennt dokumentierte Nachweisformen. Die historischen neun Theoremkonstanten der Vorarbeit werden nur in ihrem archivierten Scope referenziert und nicht zu einer neuen Theoremzahl addiert.

Der neue Beitrag ist als eigenständige Anschlussarbeit vorgesehen, mit der Zenodo-Beziehung isSupplementTo zu 10.5281/zenodo.21711193. Die historische Vorarbeit bleibt unverändert. Dokumentation: CC BY-NC-ND 4.0; Implementierungsdateien behalten ihre jeweils angegebenen Lizenzen.

