# Was die QIK-VRT-Arbeit derzeit wirklich beweist

## Von einer umfassenden Idee zu einem reproduzierbar prüfbaren Forschungsprogramm

Die 62-seitige Arbeit *Mandelbrot, Anschlussordnung, Physik und
Retrokausalität* entwickelt einen weitgespannten Zusammenhang zwischen
Mengenlehre, rekursiven Prozessen, Quantisierbarkeit, physikalischen
Dimensionen, Kausalität und einer „Ontologie des Unterschieds“. Seit dem
22. Juli 2026 liegt dazu zusätzlich eine maschinenprüfbare Formalisierung vor.

Damit hat sich der Erkenntnisstatus der Arbeit wesentlich verändert: Ihre
zentralen Aussagen stehen nicht mehr nur als Formeln, Bilder und sprachliche
Argumente im Raum. Sie wurden in einzelne Behauptungen zerlegt, nach ihrem
jeweiligen Status klassifiziert und — soweit mathematisch möglich — in Lean 4
formalisiert.

Das ist ein bedeutender Schritt zur wissenschaftlichen Anschlussfähigkeit. Es
ist jedoch ebenso wichtig, genau zu benennen, was damit bewiesen wurde und was
weiterhin eine physikalische Hypothese, eine Interpretation oder eine
normative Schlussfolgerung bleibt.

Die beiden Fassungen sind dauerhaft erreichbar:

- [62-seitige wissenschaftliche Ausgangsfassung](https://doi.org/10.5281/zenodo.21482023)
- [Maschinenprüfbare Formalisierung](https://doi.org/10.5281/zenodo.21488116)

## Zwei verschiedene Arten von Prüfung

Ein mathematischer Beweis und eine physikalische Bestätigung sind nicht
dasselbe.

Ein formaler Beweis zeigt, dass eine Aussage aus ausdrücklich angegebenen
Definitionen und Voraussetzungen logisch folgt. Ein Beweisassistent wie Lean
kontrolliert dabei jeden einzelnen Schluss. Er prüft jedoch nicht automatisch,
ob die verwendeten Begriffe tatsächlich die Natur beschreiben.

Eine physikalische Theorie benötigt zusätzlich eine konkrete Zuordnung zu
messbaren Größen, dimensionsrichtige Gleichungen, ein Messprotokoll,
quantitative Vorhersagen, Unsicherheitsangaben, Falsifikationsbedingungen und
eine unabhängige experimentelle Reproduktion.

Die neue Formalisierung hält diese Ebenen bewusst auseinander. Gerade diese
Trennung ist eine ihrer wichtigsten wissenschaftlichen Leistungen.

## Was die Matrix aus 37 Aussagen zeigt

Die Arbeit wurde in 37 zentrale Aussagen zerlegt. Jede besitzt einen eigenen
Status, einen Geltungsbereich, Voraussetzungen, Belege, Seitenverweise und
gegebenenfalls Falsifikationsbedingungen.

| Status | Anzahl | Bedeutung |
|---|---:|---|
| `PROVED` | 19 | innerhalb der angegebenen formalen Definitionen bewiesen |
| `PROVED_CONDITIONAL` | 5 | unter ausdrücklich genannten Zusatzannahmen bewiesen |
| `OPEN_EMPIRICAL` | 3 | physikalisch prüfbare, gegenwärtig offene Hypothese |
| `INTERPRETIVE` | 3 | philosophische oder physikalische Interpretation |
| `FALSE_IN_GENERAL` | 2 | in dieser allgemeinen Form unzulässiger Schluss |
| übrige Statusklassen | 5 | Definition, Hintergrund, Modellwiderlegung, unbelegt oder normativ |

Die Zahl bewiesener Aussagen allein misst nicht ihre Tragweite. Ein einfacher
Mengensatz und ein umfangreicher Struktursatz können beide als `PROVED`
erscheinen. Entscheidend sind deshalb stets Satzinhalt und Geltungsbereich.

## Mandelbrot-Menge und Komplement

Ein mathematisch gesichertes Ergebnis betrifft die Komplementstruktur. Wird
ein Grundbereich \(U\) festgelegt und darin eine Klasse \(M_U\) betrachtet,
dann ist ihr relatives Komplement

\[
K_U = U \setminus M_U.
\]

Daraus folgen

\[
M_U \cup K_U = U
\qquad\text{und}\qquad
M_U \cap K_U = \varnothing.
\]

Die beiden Klassen bilden also eine vollständige und disjunkte Partition des
gewählten Grundbereichs. Dieser Satz ist unabhängig davon, wie viele
Dimensionen der Trägerraum besitzt oder welche physikalische Interpretation
man ihm gibt.

Für die Mandelbrot-Menge bedeutet das: Sobald der betrachtete Ausschnitt der
komplexen Ebene als Grundbereich festgelegt ist, bilden Mandelbrot-Menge und
ihr relatives Komplement gemeinsam diesen Grundbereich vollständig ab.

Bewiesen ist damit eine Mengenstruktur. Nicht bewiesen ist, dass die
Mandelbrot-Menge oder ihr Komplement physisch mit der Raumzeit identisch sind.
Eine solche Identifikation benötigte eine zusätzliche
Korrespondenzabbildung, die Observablen, Einheiten, Invarianten und messbare
Vorhersagen verbindet.

## Quantisierbar bedeutet nicht notwendig quantisiert

Ein zweites zentrales Ergebnis betrifft den Unterschied zwischen
Quantisierbarkeit und ontischer Quantisierung.

Die Formalisierung konstruiert einen Raum unendlicher Bitfolgen. Für jede
gewünschte endliche Genauigkeit lässt sich eine solche Folge durch ein
endliches Präfix darstellen. Der Raum ist auf jeder endlichen
Präzisionsstufe quantisierbar. Gleichzeitig kann kein endliches Präfix die
gesamte unendliche Folge bestimmen: Hinter ihm bleiben unendlich viele
mögliche Fortsetzungen.

Damit liegt ein maschinengeprüftes Gegenmodell gegen den Schluss vor:

\[
\text{beliebig fein quantisierbar}
\quad\Longrightarrow\quad
\text{ontisch diskret}.
\]

Dieser Schluss ist im Allgemeinen falsch. Die Möglichkeit, etwas durch
endliche Messwerte, Raster oder Codes darzustellen, beweist nicht, dass das
dargestellte Objekt selbst aus kleinsten unteilbaren Einheiten besteht.

Für die Raumzeit folgt daraus weder, dass sie kontinuierlich ist, noch, dass
sie diskret ist. Bewiesen ist, dass ihre Quantisierbarkeit allein keine
ontische Quantisierung erzwingt. Auch die Planck-Länge ist zunächst eine aus
\(G\), \(c\) und \(\hbar\) gebildete natürliche Skala; ihre
Dimensionsrichtigkeit beweist kein kleinstes Raumzeitpixel.

## Physikalische Einheiten als Kontrollschicht

Maschinengeprüft ist unter anderem:

- Beide Seiten der Einstein-Gleichung besitzen die Dimension \(L^{-2}\).
- \(\hbar G/c^3\) besitzt die Dimension einer Fläche.
- \(\hbar G/c^5\) besitzt die Dimension einer Zeit zum Quadrat.
- \(\hbar c/G\) besitzt die Dimension einer Masse zum Quadrat.
- Der normierte geometrische Faktor der Bekenstein-Hawking-Entropie ist
  dimensionslos.

Eine Gleichung, deren Einheiten nicht zusammenpassen, kann kein gültiges
Naturgesetz sein. Der Umkehrschluss gilt nicht: Dimensionsrichtigkeit allein
beweist keine physikalische Wahrheit. Dimensionsanalyse ist ein notwendiger
Zulässigkeitsfilter, kein empirischer Wahrheitsbeweis.

## Was bei der Retrokausalität geklärt wurde

„Retrokausalität“ kann sehr unterschiedliche Sachverhalte meinen. Die
Formalisierung trennt insbesondere:

1. **Retrodiktion:** Spätere Daten verbessern eine Aussage über Früheres.
2. **Semantische Rückbestimmung:** Spätere Erkenntnisse verändern die
   Klassifikation früherer Spuren.
3. **Ontische Retrokausalität:** Ein späteres physisches Ereignis steht in
   einer wirklichen Abhängigkeitsrelation zu einem früheren Zustand.
4. **Rückwärtssignalisierung:** Eine spätere frei wählbare Intervention
   verändert eine früher lokal auslesbare Statistik.

Diese Kategorien sind nicht austauschbar. Wenn ein später gefundenes
Beweisstück einen älteren Datensatz neu interpretieren lässt, verändert sich
dessen Bedeutung. Das frühere physische Ereignis wird dadurch nicht notwendig
überschrieben.

Für die definierte autonome Vorwärtsrekursion wurde ein
No-Backward-Channel-Theorem bewiesen: Stimmen zwei Eingabeverläufe bis zu einem
Zeitpunkt überein und unterscheiden sie sich erst danach, ist der bis dahin
erzeugte Zustand identisch. Innerhalb dieses Modells gibt es daher keinen
operativen Rückwärtskanal.

Das ist kein universeller Beweis gegen jede denkbare retrokausale Physik. Wer
eine ontische Rückwirkung behauptet, muss eine zusätzliche Rückabhängigkeit
ausdrücklich modellieren und daraus eine unterscheidbare Vorhersage ableiten.
Auch Delayed-Choice- oder Quantum-Eraser-Experimente ergeben nach heutigem
Standardverständnis ohne späteren Vergleichskanal keine früher auslesbare
Nachricht. Eine experimentell bestätigte ontische Retrokausalität bleibt
offen; frei kontrollierbare Rückwärtssignalisierung wäre eine noch stärkere
und bislang unbelegte Behauptung.

## Was die Maschine tatsächlich geprüft hat

Die Lean-Formalisierung umfasst 118 Deklarationen und wurde ohne
projektinterne Beweislücken kompiliert: kein `sorry`, kein `admit`, keine als
Ersatzbeweis neu eingeführte `axiom`-Deklaration und null registrierte
„proof escapes“.

Zusätzlich liefen mehrere getrennte Prüfwege:

- Lean-Kernelprüfung: bestanden;
- TypeScript/Zod-Prüfung der Aussagenmatrix: bestanden;
- unabhängige Python-Prüfung derselben Statuslogik: bestanden;
- Gate 20: 18 von 18 Kontrollen bestanden;
- pytest: 5 von 5 Tests bestanden;
- negative Übertreibungstests: 3 von 3 problematischen Behauptungen
  zurückgewiesen.

Die negativen Tests sind ein Qualitätsmerkmal. Ein System, das jede
formulierte Behauptung bestätigt, wäre keine Prüfung, sondern ein
Bestätigungsapparat. Hier werden insbesondere unbelegte Gleichsetzungen von
Quantisierbarkeit und ontischer Diskretheit, von semantischer Rückbestimmung
und physischer Retrokausalität sowie von Ontologie und Naturtheorem blockiert.

## Der erkenntnistheoretische Status

Die Gesamtarbeit hat damit den Status eines **formal rekonstruierten
theoretischen Forschungsprogramms** erreicht. Sie enthält einen
maschinenbewiesenen mathematischen Kern, bedingte Modellsätze, eine
nachvollziehbare Dimensionsprüfung, eine klare Taxonomie zeitlicher
Rückbezüge, offene Korrespondenzhypothesen, philosophische Interpretationen
und offen gekennzeichnete normative Folgerungen.

Sie ist dadurch mehr als eine spekulative Ideensammlung: Begriffe,
Voraussetzungen und Grenzen können öffentlich geprüft, reproduziert und
kritisiert werden. Sie ist gegenwärtig jedoch keine experimentell bestätigte
neue Theorie der Raumzeit oder Quantengravitation. Dazu fehlen eine konkrete
physikalische Korrespondenzabbildung, neue quantitative Vorhersagen und deren
unabhängige experimentelle Bestätigung.

Die wissenschaftlich stärkste, gegenwärtig tragfähige Zusammenfassung lautet:

> Der formal entscheidbare Kern ist reproduzierbar bewiesen; die Übergänge
> von diesem Kern zur physischen Welt sind ausdrücklich als offene
> Hypothesen, Interpretationen oder normative Schlüsse gekennzeichnet.

Gerade diese Grenze macht die Arbeit anschlussfähig. Sie zeigt nicht nur,
welche Gedanken verfolgt werden, sondern auch, an welcher Stelle der
mathematische Beweis endet und die empirische Forschungsaufgabe beginnt. Das
ist der Unterschied zwischen einer weitreichenden Behauptung und einem
prüfbaren wissenschaftlichen Programm.
