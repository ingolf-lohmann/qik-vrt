<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->

# QIK R1: reproduzierbarer CHSH-Minimalbenchmark

Stand: 19. Oktober 2026. Verantwortlicher Mensch und Aufgabensteller: Ingolf
Lohmann. Implementierung, Kontrolltests und dieser neue Begleittext: Codex
(künstlich-kognitiver Beitrag). Das wissenschaftliche Original bleibt unverändert.

## Ergebnis und Erkenntnisstatus

Der Benchmark berechnet drei **etablierte Referenzmodelle** aus vollständigen
bedingten Wahrscheinlichkeitstabellen. Er stellt erstmals in diesem Main-Baum
eine ausführbare CHSH-Prüfschnittstelle für die QIK-Anforderung R1 bereit.
Er enthält **keine eigenständige QIK-Ableitung**, keine Detektormessung und
keinen kernelgeprüften formalen Beweis. Ein Tabellenwert ist eine berechnete
Modellwahrscheinlichkeit, kein empirischer Record.

| Referenz | E00 | E01 | E10 | E11 | S | No-Signalling |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Lokales gemeinsames Bit | 1 | 1 | 1 | 1 | 2 | ja |
| QM: Born-Regel, Bell-Zustand und optimale Messungen | 1/√2 | 1/√2 | 1/√2 | −1/√2 | 2√2 | ja |
| PR-Box | 1 | 1 | 1 | −1 | 4 | ja |

Die tatsächlich ausgegebenen Gleitkommawerte und alle 48 Wahrscheinlichkeiten
stehen in [REFERENCE_RESULTS.json](../evidence/chsh-reference/REFERENCE_RESULTS.json).
Die numerische Absoluttoleranz beträgt 10⁻¹². Es gibt keine Zufallsstichprobe,
keine verdeckte Renormalisierung und keine Auswahl günstiger Versuche.

Der positive No-Signalling-Test der PR-Box und ihr negativer Quantengrenztest
zeigen am konkreten Gegenbeispiel: No-Signalling allein impliziert die
Tsirelson-Grenze nicht. Die bekannte Quantenreferenz verwendet den
Hilbertraumformalismus ausdrücklich als zusätzliche Eingabe.

## Quelle, Anschluss und Erhalt des Originals

Gebundener Ausgangspunkt ist Authority `ingolf-lohmann/qik-vrt`, Main
`fbc450c4d2d5045335577aa59be7509cda16adeb`, Root-Tree
`15eb1a7bdd2c1880405df1026b14756f0fe72714`.

- [Revidiertes Original vom 23. September](publications/2026-09-23-qik-scientific-revision/QIK_Publikationsfassung_revidiert.md):
  Abschnitte 4.1–4.5, 5/R1 und 7.1–7.2.
- [Wissenschaftlicher Revisionsbericht](publications/2026-09-23-qik-scientific-revision/QIK_Wissenschaftlicher_Revisionsbericht.md).
- Quellbindungen und bytegenaue SHA-256-Werte:
  [SOURCE_BINDINGS.json](../evidence/chsh-reference/SOURCE_BINDINGS.json).

Beide Manuskriptdateien sowie das übrige Originalpaket werden weder redigiert
noch ersetzt. Dieser Text und die Berechnungen sind eigenständige Ergänzungen.
Die im Auftrag genannte Versendung vom 17. Oktober wird hier nicht als
unabhängig überprüfter Versandnachweis verwendet; für den mathematischen Test
ist die geprüfte Repository-Fassung die Quelle.

## 1. Operationaler Versuchsvertrag

Zwei Parteien A und B besitzen je zwei auswählbare Messsettings
`x,y ∈ {0,1}` und je ein binäres Ergebnis `a,b ∈ {−1,+1}`. Für jedes
Settingpaar werden **alle vier** Ergebniswahrscheinlichkeiten angegeben:

\[
 p_{xy}(a,b)=P(a,b\mid x,y),\quad p_{xy}(a,b)\geq0,
 \qquad\sum_{a,b}p_{xy}(a,b)=1.
\]

In einer späteren Versuchsserie sollen die Settings unabhängig und gleichverteilt
gewählt werden: `P(x,y)=1/4`; das Referenzprogramm wertet direkt die vier
bedingten Verteilungen aus. Für die lokale Bell-Grenze ist zusätzlich die
Unabhängigkeit der Settingwahl von der verborgenen Variable erforderlich:
`P(λ|x,y)=P(λ)`. Diese Modellannahme folgt nicht aus der Record-Speicherung.

No-Signalling wird für beide Richtungen und jedes lokale Ergebnis geprüft:

\[
 \sum_b p_{x0}(a,b)=\sum_b p_{x1}(a,b),\qquad
 \sum_a p_{0y}(a,b)=\sum_a p_{1y}(a,b).
\]

Die Residuen sind jeweils das Maximum der absoluten Marginaldifferenzen.
Ein vollständiger, normierter, aber signalisierender Input besteht diese
Prüfung nicht, selbst wenn sein CHSH-Wert kleiner als 2 ist.

Die Korrelationsfunktion und die orientierte CHSH-Kombination lauten:

\[
 E_{xy}=\sum_{a,b=\pm1}ab\,p_{xy}(a,b),\qquad
 S=E_{00}+E_{01}+E_{10}-E_{11}.
\]

Die Grenzen gelten für `|S|`. Zusätzlich werden alle acht Vorzeichenmuster
`s00 s01 s10 s11 = −1` ausgewertet. Das verhindert, dass eine lokal
umbenannte PR-Box mit orientiertem `S=0` durch den Kontrolltest schlüpft.

## 2. Die drei Referenzen

### 2.1 Lokales klassisches Modell

Die Quelle verteilt ein gemeinsames, faires Bit `λ ∈ {−1,+1}`.
Beide Parteien geben unabhängig vom Setting `a=λ`, `b=λ` aus:

\[
 p_{xy}(a,b)=\tfrac12\,\mathbf1_{a=b}.
\]

Für jedes `(x,y)` gilt also `P(++ )=P(−−)=1/2` und
`P(+−)=P(−+)=0`. Die lokalen Marginalverteilungen sind fair,
alle vier Korrelationen sind 1 und `S=2`.

Als zusätzliche endliche Kontrolle werden sämtliche 16 deterministischen
Antwortbelegungen `(A0,A1,B0,B1)` enumeriert. Jede ergibt `|S|=2` und
erfüllt sämtliche lokalen CHSH-Facetten. Eine nicht gleichgewichtete konvexe
Mischung wird gesondert getestet. Die allgemeine lokale Grenze beruht auf

\[
 A_0(B_0+B_1)+A_1(B_0-B_1)\in\{-2,+2\}
\]

für vorab festgelegte binäre lokale Antworten und auf der Linearität des
Erwartungswerts bei settingunabhängigen Mischungsgewichten. Dies ist die
bekannte lokale Modellklasse; es ist keine zusätzliche QIK-Folgerung.

### 2.2 Quantenmechanisches Referenzmodell

Die zusätzlich gesetzten QM-Strukturen sind
`H = C² ⊗ C²`, der normierte Zustand

\[
 |\Phi^+\rangle=(|00\rangle+|11\rangle)/\sqrt2,
\]

und die Observablen

\[
 A_0=\sigma_z,\quad A_1=\sigma_x,\qquad
 B_0=(\sigma_z+\sigma_x)/\sqrt2,\quad
 B_1=(\sigma_z-\sigma_x)/\sqrt2.
\]

Die Settingwinkel in der XZ-Ebene sind für A `(0, π/2)` und für B
`(π/4, −π/4)`, im Bogenmaß. Die Ergebnisprojektoren sind
`F^x_a=(I+a A_x)/2` und `G^y_b=(I+b B_y)/2`. Der Code berechnet direkt

\[
 p_{xy}(a,b)=\langle\Phi^+|F^x_a\otimes G^y_b|\Phi^+\rangle.
\]

Ein unabhängiger Test vergleicht jedes Ergebnis mit der geschlossenen Formel

\[
 p_{xy}(a,b)=(1+ab\,c_{xy})/4,\quad
 (c_{00},c_{01},c_{10},c_{11})=(1,1,1,-1)/\sqrt2.
\]

| Settingpaar | P(++), P(−−), jeweils | P(+−), P(−+), jeweils |
| --- | ---: | ---: |
| 00, 01, 10 | (1+1/√2)/4 ≈ 0,426776695296637 | (1−1/√2)/4 ≈ 0,073223304703363 |
| 11 | (1−1/√2)/4 ≈ 0,073223304703363 | (1+1/√2)/4 ≈ 0,426776695296637 |

Diese Referenz erreicht `S=2√2`. Eine zweite Winkelwahl wird gegen
`cos(θ_A−θ_B)` geprüft und erreicht das Maximum gerade nicht. Dadurch
wird auch kontrolliert, dass der Code nicht lediglich den Zielwert ausgibt.

### 2.3 No-Signalling-Modell außerhalb der Quantengrenze

Die PR-Box setzt

\[
 p_{xy}(a,b)=\begin{cases}
 1/2,&ab=(-1)^{xy},\\0,&\text{sonst}.
 \end{cases}
\]

Äquivalent gilt für `α=(1−a)/2`, `β=(1−b)/2`:
`α XOR β = x y`. Für 00, 01 und 10 sind die gleichen Ergebnisse
jeweils mit Wahrscheinlichkeit 1/2 erlaubt; für 11 die ungleichen.
Alle lokalen Marginalwahrscheinlichkeiten bleiben 1/2. Damit bestehen
Normalisierung und No-Signalling exakt; `S=4` verletzt die Quantengrenze.
Die Settinglabels dieser abstrakten Box behaupten keine physisch
realisierbaren Pauli-Messgeräte.

## 3. Reproduktion und Kandidatenschnittstelle

Es wird der bereits deklarierte Repository-Python verwendet, ohne neue
Pakete, Downloads oder Zufallszahlengeneratoren. Aus dem Repository-Wurzelordner:

```sh
python3 -B -m src.qikvrt_chsh_benchmark
make chsh-reference-test
```

Die erste Anweisung gibt das deterministische JSON-Ergebnis auf stdout aus.
Die zweite läuft zusätzlich im bestehenden `make test`-Pfad. Vollständige
Repositoryprüfungen und deren etwaige unabhängige Bestandsfehler sind im
Work-Unit-Nachweis getrennt von den CHSH-Kontrollen dokumentiert.

Ein künftiger QIK-Formalismus liefert eine JSON-Liste mit genau 16 Einträgen
der Form `{"x":0,"y":0,"a":-1,"b":-1,"p":0.5}`. Je eine Zelle für
jedes `(x,y,a,b)` ist erforderlich; auch Nullwahrscheinlichkeiten sind explizit.
Aufruf:

```sh
python3 -B -m src.qikvrt_chsh_benchmark --candidate candidate.json
```

Die Ausgabe nennt `S`, sämtliche Korrelationen, den maximalen Betrag aller
CHSH-Facetten und beide No-Signalling-Residuen. Ungültige Tabellen führen zu
Exitcode 2. Gültige Tabellen werden auch bei physikalisch verletzten Grenzen
mit ihren tatsächlichen booleschen Prüfergebnissen ausgegeben: Exitcode 0
bedeutet erfolgreiche Auswertung, keine Modellannahme oder R1-Akzeptanz.

Die Schnittstelle akzeptiert **keine** Detektorzählwerte als Ersatz für
Wahrscheinlichkeiten. Eine empirische Ergänzung müsste Anzahl und Auswahl
aller Versuche, Unabhängigkeit der Settings, Missing-/No-click-Regeln,
Detektionseffizienz, Unsicherheiten, zeitliche Zuordnung und erlaubte
Kommunikationswege zusätzlich binden. Exakte No-Signalling-Gleichheit wird
nicht aus einer endlichen Stichprobe verlangt; dafür wäre ein gesonderter
statistischer Test samt vorher festgelegtem Niveau erforderlich.

## 4. Zuordnung zum vorhandenen QIK-Träger

| Bestandteil des Originals | Konkrete Belegung im CHSH-Vertrag | Zusätzliche Annahme / Grenze |
| --- | --- | --- |
| `E`, Ereignismarker, §4.1/D2 | Pro Versuch Präparation eS, lokale Setting-/Ergebnisereignisse eA und eB, späterer Vergleich eC | Programmereignisse sind keine gemessenen physikalischen Ereignisse. |
| `≺`, strikte Kausalordnung | eS ≺ eA ≺ eC und eS ≺ eB ≺ eC; eA und eB unvergleichbar | Unvergleichbarkeit beweist laut Original keine metrische Raumartigkeit; sie verbietet nicht von selbst jede statistische Korrelation. |
| `μ`, Maß-/Zählstruktur, §4.2/D3 | In einem späteren Experiment z. B. Zählmaß über gültige Versuche und ihre Recordmengen | Dieses Zählmaß erzeugt weder Born-Regel noch Tensorprodukt. |
| `𝓜`, lokale Protokolle, §4.4/D5 | M_A(x), M_B(y), Präparation, spätere Vergleichsregel | Zulässigkeit inkompatibler Settings und Zusammensetzung müssen spezifiziert werden. |
| `P(r|M)` | Vollständige bedingte Tabelle `P(a,b|x,y)`; Settings sind Konditionen | Im Benchmark aus dem jeweiligen Referenzmodell gesetzt bzw. im QM-Fall mit Born berechnet. |
| `Π`, endlicher Record | Lokaler Record r_A=(Versuchs-ID,x,a), r_B=(Versuchs-ID,y,b), Vergleichsrecord mit beiden Verweisen | Recordbildung und statistisches Korrelationsgesetz sind verschiedene Abbildungen. |
| Information, §4.3/D4 | Unterscheidbare Ergebnisverteilungen und ihre Marginalen | Es wird kein zusätzliches Informationsmaß als Quantengesetz eingeführt. |

Ein künftiges empirisches Recordformat benötigt mindestens Versuchs-ID,
Präparations-/Protokollversion, Partei, lokales Setting und Ergebnis,
Ereignisverweise, Auswahlstatus sowie nachvollziehbare Provenienz. Remote
Settings werden erst im gemeinsamen kausalen Zukunftsbereich zusammengeführt.
Die Modellwahrscheinlichkeitsliste des aktuellen Programms enthält dagegen
alle möglichen Ergebniszellen und ist ausdrücklich **keine** Liste realisierter
Versuche. Deren ausgedachte Ausführung wird nicht behauptet.

Die vorhandenen nativen Komponenten `src/qikvrt_temdd_event_ledger.py` und
`src/qikvrt_effect_ack_http_terminal.py` bleiben für Software-Arbeitsnachweise
zuständig. Ein dortiger Hash-Readback beweist die Speicherung eines
Berechnungsergebnisses, keine Bell-Verletzung der Natur und keine QIK-Ableitung.
Die Reihenfolge von Software-Records ersetzt nicht die physikalische
Kausalordnung oder eine gesicherte räumliche Trennung.

## 5. Was für eine QIK-Ableitung zusätzlich fehlt

Das Tupel `(E,≺,μ,𝓜,P,Π)` benennt Strukturen, spezifiziert jedoch noch
keine solche Einschränkung von `P`, dass PR-Boxen ausgeschlossen wären.
Der aktuelle Gegenvergleich macht diese Unterbestimmtheit ausführbar.
Für eine hinreichende **bedingte Einbettung** in den bekannten Quantenfall
könnte man ergänzen:

1. Einen Zustandsraum mit positiven, normierten Zuständen `ρ` und eine
   begründete Kompositionsregel für unabhängige Subsysteme.
2. Lokale Messungen als positive Effekte/Instrumente, Normalisierung und
   Kompatibilität getrennter Regionen; im Projektorfall selbstadjungierte
   Observablen mit `A_x²=B_y²=I`.
3. Die Born-Wahrscheinlichkeitsregel `Tr[ρ(F^x_a⊗G^y_b)]` oder eine
   explizit bewiesene empirisch gleichwertige Regel; einschließlich ihres
   Anschlusses an lokale Protokolle und die Recordabbildung `Π`.
4. Ein QIK-internes Prinzip bzw. eine Dynamik, aus dem diese Einschränkungen
   folgen. Ein gesetztes Tensorprodukt oder eine gesetzte Born-Regel ist
   eine zusätzliche Modellannahme und noch keine Herleitung aus QIK.

Unter genau diesen zusätzlich importierten Hilbertraum-/Operatorannahmen ist
die bekannte Tsirelson-Abschätzung nachvollziehbar. Für

\[
 \mathcal B=A_0\otimes(B_0+B_1)+A_1\otimes(B_0-B_1)
\]

gilt

\[
 \mathcal B^2=4I-[A_0,A_1]\otimes[B_0,B_1],\qquad
 \|[A_0,A_1]\|,\|[B_0,B_1]\|\le2.
\]

Somit `‖B‖² ≤ 8` und `|Tr(ρ B)| ≤ 2√2`. Die hier verwendete
Quantenreferenz erreicht die Schranke. Das ist ein mathematisches Argument
**innerhalb des etablierten Quantenformalismus**; der Benchmark erbringt
keinen separaten kernelgeprüften Beweis dieses Satzes und keinen Beweis
der fehlenden QIK-zu-Operator-Abbildung.

Auch die erfolgreiche Prüfung aller CHSH-Schranken ist noch keine
Charakterisierung der gesamten quantenmechanischen Korrelationsmenge.
Schon im hiesigen Szenario liefert die faire No-Signalling-Tabelle
`E=(1,1,1,1/2)` ein Gegenbeispiel: maximaler CHSH-Betrag `2,5 < 2√2`,
aber keine quantenmechanische Realisierung. Bei drei perfekten
Korrelationen erzwingen die gleichgesetzten Zustandsvektoren
`A0|ψ⟩=B0|ψ⟩=B1|ψ⟩=A1|ψ⟩` auch die vierte perfekte Korrelation
`E11=1` (mit lokalen Operatoren auf dem gemeinsamen/purifizierten Zustand).
Dieser Input erhält deshalb lediglich `within_quantum_CHSH_ceiling=true`;
das Programm bescheinigt ihm ausdrücklich keine Quantenmitgliedschaft.

Klassische Records allein erzwingen umgekehrt keine lokalen Hidden Variables:
Eine gemeinsame, settingunabhängige Verteilung für sämtliche hypothetischen
inkompatiblen Messresultate wäre eine zusätzliche lokale Modellannahme und
könnte Bell-verletzende Quantenstatistik gerade nicht tragen.

## 6. Kontrollen und nächste Forschungsaufgabe

Die automatisierten Kontrollen umfassen die analytischen drei Referenzen,
alle 16 lokalen deterministischen Strategien, eine lokale Mischung,
unabhängig geprüfte Born-Wahrscheinlichkeiten auch bei anderen Winkeln,
beide No-Signalling-Richtungen, umbenannte/negative CHSH-Werte und die
Dateischnittstelle. Negative Kontrollen verwerfen die Quantenreferenz an
der lokalen Grenze und die PR-Box an der Quantengrenze. Zusätzlich scheitern
fehlende/duplizierte Zellen, fehlende explizite Nullen, ungültige Zahlen,
falsche Normalisierung, ungültige Ergebnislabels und Signalling.

**Die nächste konkrete Forschungsaufgabe ist ein QIK-Korrelationsgesetz**:
eine explizite, unabhängig von diesen Zieltabellen definierte Abbildung
von QIK-Präparation und zulässigen lokalen Protokollen nach
`P(a,b|x,y)`. Ihr Axiomen-/Annahmenregister muss zeigen, wodurch die
PR-Box und das Beispiel `E=(1,1,1,1/2)` ausgeschlossen werden, während
die vollständigen Born-Verteilungen für die optimalen **und** weitere
Settingwinkel reproduziert werden. Die hier vorliegende Schnittstelle
kann deren Tabellen unmittelbar auswerten.

Abnahme dieses nächsten Schritts: Quelle und Parameter des Gesetzes vor
dem Vergleich einfrieren; Zustands-/Kompositions-/Messregeln explizit
angeben; No-Signalling nachweisen; die CHSH-Obergrenze für alle zugelassenen
Zustände und Settings ableiten und ihre Erreichbarkeit belegen; zusätzliche
Quantenbedingungen über CHSH hinaus prüfen. Ein bloßer Cutoff `|S|≤2√2`
oder eine Übernahme der drei Referenztabellen würde die gesuchte
QIK-Ableitung nicht liefern. Der volle R1-Nachweis bleibt offen.

## Fachquellen und Aussageklassen

- **Etablierte Fachgrundlage (B):** J. F. Clauser et al., *Proposed Experiment
  to Test Local Hidden-Variable Theories*, Physical Review Letters 23,
  880–884 (1969), DOI [10.1103/PhysRevLett.23.880](https://doi.org/10.1103/PhysRevLett.23.880).
- **Etablierte Fachgrundlage (B):** B. S. Cirel'son, *Quantum generalizations
  of Bell's inequality*, Letters in Mathematical Physics 4, 93–100 (1980),
  DOI [10.1007/BF00417500](https://doi.org/10.1007/BF00417500).
- **Etablierte Fachgrundlage (B):** S. Popescu und D. Rohrlich, *Quantum
  nonlocality as an axiom*, Foundations of Physics 24, 379–385 (1994),
  DOI [10.1007/BF02058098](https://doi.org/10.1007/BF02058098).
  Ergänzender Primärtext der Autoren:
  [Nonlocality as an axiom for quantum theory (1995)](https://arxiv.org/abs/quant-ph/9508009).
- **Definitionen/Annahmen (D):** Settingvertrag, Datenformat, Zustandswahl,
  Messoperatoren und Gleitkommatoleranz dieses Benchmarks.
- **Berechnung/Test:** Ausgeführtes Programm, JSON-Ergebnis und Regressionen.
- **Interpretation (I):** Zuordnung zu QIK-Ereignissen, Protokollen und Records.
- **Offene Modellpflicht (R1):** QIK-interne Korrelationsregel und ihre
  Herleitung; volle Quantenmitgliedschaft, empirische Prüfung und allgemeine
  Reproduktion der Quantenstatistik sind durch diesen Kontrollvergleich
  nicht erledigt.
