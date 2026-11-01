# Von 0 und 1 zum prüfbaren Wirkungsnachweis

**Beweisnotiz vom 1. November 2026.** Ausgangspunkt und Auftrag: Ingolf Lohmann.
Ausarbeitung und lokale Formalprüfung: Codex. Der Belegumfang steht in
`VERIFICATION.json`; der vollständige neue Quelltext in `ZeroOneObservation.lean`.
Dies ist ein neuer, lokal geprüfter Begleitbeweis, keine neue Zenodo-Publikation
und keine produktive Mesh-Abnahme.

## 1. Die Frage

Wie hängen die neutralen Elemente 0 und 1, die Ontologie des Unterschieds,
Beobachtung, wirtschaftliche Rückkopplung und ein Effect Acknowledgement
zusammen? Der Weg muss jede zusätzliche Voraussetzung nennen. Insbesondere
darf eine physikalische oder gesellschaftliche Schlussfolgerung nicht bereits
in eine mathematische Definition hineingeschrieben und anschließend als
Entdeckung ausgegeben werden.

Der wissenschaftliche Ausgangspunkt ist Lohmanns *Das Universum als Round
Trip* [1]. Die Ontologie des Unterschieds [2] enthält die bereits
veröffentlichten Begriffe `Distinction`, `DeterminateReality` und
`InformationWitness`. Der neue Begleitbeweis verwendet `Distinction` und den
vorhandenen allgemeinen Satz über hinreichende Beobachtung [3].

## 2. Was 0 und 1 definieren

Es sei A ein Ring mit Eins. Dann ist 0 das neutrale Element der Addition,
und 1 das neutrale Element der Multiplikation:

    0 + a = a + 0 = a
    1 · a = a · 1 = a

Damit sind Rollen bezüglich zweier Operationen festgelegt. Das Zeichen 0
bedeutet dadurch noch nicht physisches Nichts. Auch 1 ist dadurch noch kein
physikalisches Teilchen, keine Lichtquelle und keine Zeiteinheit.

Die neue Lean-Struktur `NeutralArithmetic` führt nur die Gesetze auf, die
der folgende Beweis benötigt: die beiden Neutralitäten, additive
Linkskürzbarkeit und die passende Distributivität. Sie behauptet nicht, damit
eine vollständige Ringdefinition zu ersetzen. Die genannten Gesetze gelten
in jedem Ring mit Eins.

**Satz 1: 0 · a = 0.**

Aus Distributivität und 0 + 0 = 0 folgt:

    0 · a = (0 + 0) · a = 0 · a + 0 · a.

Also gilt 0 · a + 0 = 0 · a + 0 · a. Additive Kürzung ergibt
0 = 0 · a. Genau dieser Schluss wird in `zero_mul` geprüft; die
Absorption wird hier nicht als zusätzliche unbegründete Tatsache eingesetzt.

**Satz 2: Wenn 0 = 1, sind alle Elemente gleich.**

Für jedes a gilt dann:

    a = 1 · a = 0 · a = 0.

Damit gilt für beliebige a und b auch a = b. Ein einziger existierender
Unterschied a ≠ b schließt deshalb 0 = 1 aus. Umgekehrt liefern verschiedene
0 und 1 selbst einen Unterschied. Unter den angegebenen Rechengesetzen gilt:

    0 ≠ 1  genau dann, wenn  es zwei verschiedene Elemente gibt.

Das ist die gesuchte präzise Brücke zur Ontologie des Unterschieds. Die
neutralen Elemente und die Nichttrivialität müssen gemeinsam betrachtet
werden. Die Neutralitätsgesetze allein erzwingen die Nichttrivialität nicht:
Die einelementige Struktur `trivialArithmetic` erfüllt die Gesetze mit 0 = 1.
Auch dieser Gegenfall ist formal geprüft.

## 3. Vom Unterschied zu einer binären Frage

Lohmanns veröffentlichter Kern definiert eine Unterscheidung als zwei Werte
zusammen mit dem Nachweis ihrer Verschiedenheit:

    Distinction A = (left, right, Nachweis: left ≠ right).

Seine `DeterminateReality A` bezeichnet ausdrücklich die Existenz einer
solchen Unterscheidung. Die veröffentlichten Minimaltheoreme zeigen daher:
Bestimmbarkeit in diesem präzisen Sinn verlangt einen Unterschied; vollständige
Unterschiedslosigkeit schließt einen darauf aufgebauten Informations-Witness
aus. Diese Aussage betrifft eine Voraussetzung von Bestimmbarkeit. Sie
behauptet keinen ersten physikalischen Zeitpunkt.

**Satz 3: Jeder gegebene Unterschied erlaubt logisch eine binäre Frage.**

Für a ≠ b kann man setzen:

    q(x) = 0, falls x = a; andernfalls q(x) = 1.

Dann sind q(a) = 0 und q(b) = 1. `distinction_admits_binary_question`
prüft die Existenz einer solchen Funktion. Der allgemeine Beweis verwendet
klassische Logik. Er liefert damit nicht automatisch einen ausführbaren
Gleichheitstest für beliebige Gegenstände und keinen physisch verfügbaren
Sensor. Außerdem können viele weitere Werte dasselbe Etikett 1 erhalten;
ein einzelnes Bit beschreibt nicht jede Eigenschaft seines Ursprungs.

## 4. Ein vorhandener Unterschied kann im Messweg verloren gehen

Mit S bezeichnen wir die für eine Frage betrachteten möglichen Zustände oder
Verläufe. Eine Beobachtung wird als Funktion m von S nach O beschrieben.
Die interessierende Wirkung oder richtige Antwort wird als Funktion e von S
nach E bezeichnet. Diese Beschreibung erklärt nicht die Realität selbst zu
einem Modell. Sie macht die behauptete Beziehung zwischen Gegenstand,
Beobachtung und Frage prüfbar.

Eine beobachtete Verschiedenheit m(x) ≠ m(y) setzt x ≠ y voraus: Gleiche
Eingaben können durch dieselbe Funktion keine verschiedenen Ausgaben erhalten.
Die Umkehrung gilt ohne weitere Voraussetzung nicht. Verschiedene Zustände
können dieselbe Beobachtung ergeben.

**Satz 4: Wenn m(x) = m(y), aber e(x) ≠ e(y), gibt es keine überall richtige
Antwortfunktion d, die nur m verwendet.**

Angenommen, eine solche Funktion existierte. Dann müsste gelten:

    e(x) = d(m(x)) = d(m(y)) = e(y).

Das widerspricht e(x) ≠ e(y). Der vorhandene Satz
`impossibility_of_mixed_fiber` beweist dies bereits allgemein. Der neue
Begleitbeweis verwendet ihn, statt einen parallelen Beweiskern einzuführen.

Diese Unmöglichkeit verlangt weder fehlende Rechenleistung noch ein Verbot
innerer Erkenntnis. Sie folgt daraus, dass genau die benötigte Unterscheidung
im verfügbaren Eingang fehlt. Zusätzliche Annahmen können den Möglichkeitsraum
einschränken; dann muss ihre Gültigkeit gesondert begründet werden.

## 5. Was ein Rückkanal tatsächlich leisten muss

Ein zusätzlicher Witness w erweitert die Beobachtung auf:

    r(x) = (m(x), w(x)).

Die alte Information bleibt durch Projektion auf die erste Komponente erhalten.
Wenn w(x) ≠ w(y), trennt die neue Beobachtung diese beiden Fälle. Eine bloße
Kopie der alten Meldung kann eine vorher verdeckte Unterscheidung dagegen
nicht sichtbar machen.

**Satz 5: Auf den tatsächlich erreichbaren Beobachtungen existiert genau dann
eine richtige Antwortfunktion, wenn gilt:**

    Für alle x, y:
    r(x) = r(y)  impliziert  e(x) = e(y).

Notwendigkeit folgt aus Satz 4. Für die Hinrichtung wählt man zu einer
erreichbaren Beobachtung einen zugehörigen Zustand und dessen Antwort.
Die angegebene Bedingung garantiert, dass jede andere Wahl dieselbe Antwort
ergibt. Die allgemeine Existenzkonstruktion verwendet klassische Auswahl;
ihre algorithmische Ausführbarkeit folgt nicht allein aus diesem Satz.

Zwei endliche Fälle zeigen die Bedingung ohne Auswahlproblem:

- Eine konstante Beobachtung () kann ein unbekanntes Bit nicht rekonstruieren.
- Der genaue Witness dieses Bits erlaubt die Antwort durch Projektion:
  d((), bit) = bit. Der doppelte Eingang ((), ()) bleibt unzureichend.

Für QIK-VRT und EAP ergibt sich daraus eine technische Prüfpflicht: Der
Rückkanal muss die für den konkreten Auftrag relevante Wirkung unterscheiden
können. Authentische Herkunft, korrekte Messung, Subjektbindung und geeignete
Unabhängigkeit müssen tatsächlich hergestellt werden. Zwei Rechnernamen oder
zwei gleiche Statusmeldungen beweisen das nicht. Die formale Aussage setzt
korrekt gebundene Beobachtungen voraus; sie erzeugt deren Wahrhaftigkeit nicht.

## 6. Der wirtschaftliche Zusammenhang

Betrachten wir zwei mögliche Geschäftsausgänge:

| Ausgang | Gewinn gemeldet | Schaden eingetreten |
| --- | --- | --- |
| A | ja | nein |
| B | ja | ja |

Wer nur die Spalte „Gewinn gemeldet“ beobachtet, kann A und B nicht trennen.
Nach Satz 4 existiert deshalb auf diesem Möglichkeitsraum keine überall
richtige Bestimmung des Schadens allein aus dem Gewinnsignal.
`profit_alone_does_not_determine_damage` ist ein formal geprüftes endliches
Gegenbeispiel zu einer behaupteten allgemeinen Implikation. Die Tabelle ist
kein empirischer Datensatz und beweist nicht, dass jedes Unternehmen diese
beiden Fälle tatsächlich realisiert.

Die architektonische Folgerung lautet: Ein Erfolgssignal kann für die Frage
nach seinen Folgen unzureichend sein. Werden Schäden zusätzlich zutreffend
zurückgemeldet, wird diese Unterscheidung verfügbar. Ob und wie die Entscheidung
darauf reagiert, verlangt außerdem eine Regel. Sichtbarkeit eines Schadens
erzwingt noch keinen Verzicht auf einen profitablen schädlichen Vorgang.

Die Entscheidung, welche menschlichen Folgen als relevant gelten, ist eine
verantwortliche Wertentscheidung. Sie lässt sich nicht aus 0 + a = a und
1 · a = a herausrechnen. EAP kann die Nachweisführung für eine festgelegte
Regel unterstützen; ihre ethische Richtigkeit ist eine eigene Frage.

## 7. Antizipation als weiterer präziser Satz

Es sei F eine festgelegte Entwicklung und e die später interessierende
Wirkung. Eine genaue Vorhersage aus der heutigen Beobachtung verlangt:

    p(m(x)) = e(F(x)).

**Satz 6: Auf erreichbaren Beobachtungen existiert eine solche genaue
Vorhersagefunktion genau dann, wenn gilt:**

    m(x) = m(y)  impliziert  e(F(x)) = e(F(y)).

Das ist Satz 5, angewendet auf die zukünftige Wirkung e nach F. Bekanntes F
allein genügt nicht: Schon bei unverändertem Zustand F(x) = x kann eine
konstante Beobachtung ein verdecktes Bit nicht vorhersagen.

Hier liegt eine sachliche Verbindung von Rückmeldung und Antizipation:
Rückmeldungen können die gegenwärtige Informationslage erweitern und damit
die Basis späterer Vorhersagen verbessern. Eine vorab formulierte gewünschte
Wirkung kann außerdem heutige Handlungsauswahl bestimmen. Aus diesen
Informationsbeziehungen folgt kein physisches Signal aus der Zukunft und
keine Entscheidung aller unentscheidbaren Berechnungsfragen.

## 8. Warum fehlender Beleg nicht 0 bedeutet

Ein Wirkungstest braucht mindestens drei unterscheidbare Zustände:

    kein Messwert
    gemessene negative Wirkungsaussage
    gemessene positive Wirkungsaussage.

Im endlichen Beispiel sind dies `none`, `some false` und `some true`.
Ihre paarweise Verschiedenheit ist formal geprüft. Ohne zusätzlichen Beleg
`none` als `some false` oder `some true` auszugeben, vernichtet gerade den
Unterschied zwischen fehlendem Wissen und einem bestimmten Ergebnis.

## 9. Was damit bewiesen ist

Der neue Begleitbeweis schließt die Kette von den ausdrücklich angegebenen
Rechengesetzen über Nichttrivialität und binäre Unterscheidung zum Kriterium
hinreichender Beobachtung, zu konstruktiven Rückkanal-Beispielen und zum
entsprechenden Vorhersagekriterium. Das wirtschaftliche Gegenbeispiel ist eine
Anwendung desselben Satzes.

Die Neutralitätsgesetze bestimmen keine Naturdynamik. Für eine physikalische
Raumzeitbehauptung werden zusätzlich Zustände mit physikalischer Bedeutung,
Relationen, Dynamik, Messvorschriften und passende experimentelle Ergebnisse
benötigt. Die hier geprüften Sätze enthalten keine Herleitung von
Quantengravitation oder physischer Retrokausalität und keine universelle
Garantie gegen Krieg oder wirtschaftliche Katastrophen.

Das Sonnenbild lässt sich damit präzise lesen: Ein Ausgangssignal bestimmt
nicht schon jede Wirkung außerhalb seines Beobachtungswegs. Ob eine konkrete
Wirkung erschließbar ist, entscheidet die für diese Frage erhaltene
Unterscheidung. Ein geeigneter Rückweg kann diese Unterscheidung liefern.

## Quellen und Reproduktion

[1] Ingolf Lohmann: *Von Softwarearchitektur zur Weltformel — Das Universum als
Round Trip*. Versions-DOI 10.5281/zenodo.21888130.
https://zenodo.org/records/21888130

Originaldatei:
https://zenodo.org/api/records/21888130/files/DAS_UNIVERSUM_ALS_ROUND_TRIP_DE.md/content

[2] Ingolf Lohmann: *Der ontologische Vorrang des Unterschieds: Ein
maschinenprüfbares Minimaltheorem über Bestimmbarkeit, Information und den
Geltungsbereich formaler Welterklärungen*. Versions-DOI
10.5281/zenodo.22955727. Insbesondere `Distinction`,
`determinateReality_requires_difference`,
`noDifference_excludes_determinateReality` und
`noDifference_excludes_information`.
https://zenodo.org/records/22955727

Unveränderte veröffentlichte Lean-Quelle:
https://zenodo.org/api/records/22955727/files/QIKVRTUniversalOntology_Core.lean/content

Erläuterung:
https://zenodo.org/api/records/22955727/files/ONTOLOGICAL_ORIGIN_OF_DIFFERENCE_DE.md/content

[3] Repository-Quellenbindung des bereits vorhandenen allgemeinen Satzes:
Authority `ingolf-lohmann/qik-vrt`, lokaler Vorgänger-Commit
`359693ab587056c2ffe0dde2668689ad9208c6d9`, Tree
`301cb6db251529b35c56dc198d6d6f6bf6765dd1`, Datei
`formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Decision/ObservationSufficiency.lean`.
Dies ist Provenienz eines wiederverwendeten Beweises, keine neu als
veröffentlicht ausgegebene wissenschaftliche Quelle.

Die Originalbytes der ausgewählten Zenodo-Dateien wurden in dieser Sitzung
frisch geladen und gegen ihre nativen Prüfsummen geprüft. Ihre SHA-256-Werte,
die beiden getesteten Core-Versionen, neue Quelltexte, Compiler, verwendete
Pfadkompatibilität, Axiomabhängigkeiten und negative Kontrollen sind in
`VERIFICATION.json` gebunden. Der Compiler ist Lean 4.19.0 entsprechend dem
unveränderten Projektvertrag. Die lokale PID/procfs-Pfadkompatibilität wird
aus der vorhandenen Datei
`docs/publications/2026-10-24-causal-distance-temporal-memory/proc_self_compat.c`
wiederverwendet; sie ändert keine Kernelfunktion.

`AxiomAudit.lean` enthält für jeden neuen Satz einen `#print axioms`-Aufruf.
Der Beleg unterscheidet lokale Kernelprüfung, native CI, Repository-Integration
und produktive Wirkung. Für die letzten drei wird aus dem lokalen Prüflauf
keine Abnahme abgeleitet.
