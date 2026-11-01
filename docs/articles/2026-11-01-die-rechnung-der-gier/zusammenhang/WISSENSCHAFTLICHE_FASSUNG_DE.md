# Unterschied, Beobachtung und Verantwortung

## Vom Sonnenbild zum prüfbaren Erkenntniszusammenhang

Wissenschaftliche Arbeitsfassung | 1. November 2026

Gedanklicher Ausgangspunkt und QIK-VRT-Forschungsprogramm: Ingolf Lohmann.
Ausarbeitung und Dokumenterstellung: Codex im Dialog mit Ingolf Lohmann.

### Zusammenfassung

Die Arbeit rekonstruiert einen gemeinsamen Argumentationsweg zwischen der Ontologie des Unterschieds, den neutralen Elementen 0 und 1, der hinreichenden Beobachtung einer Wirkung und verantwortbarer technischer Rückkopplung. Grundlage sind 23 lokal mit Lean 4.19.0 geprüfte Begleitsätze sowie veröffentlichte QIK-VRT-Arbeiten. Das Sonnenbild wird als Metapher für die Trennung von Wirksamkeit und Rückmeldung präzisiert. Anwendungen betreffen Zustellbestätigungen, finanzielle Erfolgssignale und bedingte Vorhersage. Bewusstsein wird nach der ausdrücklichen Ownerdefinition als allgemeine Wechselwirkung gefasst; subjektives Erleben ist damit nicht stillschweigend gleichgesetzt. Die Ergänzungen des Auftraggebers zum Publikationskorpus, zur wachsenden Evidenzkugel und zum Panpsychismus werden ausdrücklich aufgenommen. Mathematische Ableitung, experimentelle Prüfung, philosophische Deutung und normative Entscheidung behalten dabei ihre jeweiligen Begründungspflichten.

### 1. Gegenstand und Methode

Die Ausgangsthese lautet: Eine Wirkung kann eintreten, obwohl dem Handelnden die zu ihrer Beurteilung erforderliche Information fehlt. Die Realität wird damit nicht als Modell bezeichnet. Formalisiert wird eine behauptete Beziehung zwischen betrachteten Fällen, verfügbaren Beobachtungen und relevanten Wirkungen. Der Erkenntnisweg orientiert sich an Lohmanns Round Trip [S1]: Beobachtung, Unterschied, Erklärung, Formalisierung, Vorhersage, Messung und erneuter Wirklichkeitsabgleich.

Das Dokument beantwortet, was die konkrete mathematische Verbindung trägt und welche weiteren Begründungen für weitergehende Aussagen erforderlich sind. Der Anspruch, buchstäblich jede denkbare Frage abschließend zu erledigen, wäre durch diese Methode nicht gedeckt. Offene Fragen werden deshalb mit ihrer genauen Anschlussbedingung sichtbar gemacht.

Die neue Beweisergänzung ist ein Arbeitsstand mit lokalem Kernelbeleg [P1]. Ihre Ablage im Repository wird von einer neuen wissenschaftlichen Archivveröffentlichung unterschieden. Die Originalquellen und Prüfbelege sind dieser PDF zusätzlich als Dateien beigefügt.

### 2. Algebraische Grundlage und Ontologie

Es gelten die Neutralitätsgesetze 0 + a = a + 0 = a und 1 · a = a · 1 = a. Die Lean-Struktur NeutralArithmetic verwendet zusätzlich additive Linkskürzbarkeit und Distributivität. Diese Gesetze gelten in einem Ring mit Eins; die Struktur ist ausdrücklich keine vollständige Ringdefinition.

Aus 0 + 0 = 0 folgt durch Distributivität 0 · a = 0 · a + 0 · a. Additive Kürzung liefert 0 · a = 0. Unter der Annahme 0 = 1 gilt daher für jedes a:

    a = 1 · a = 0 · a = 0.

Somit fallen alle Werte zusammen. Umgekehrt liefert 0 ≠ 1 zwei verschiedene Werte. Unter den deklarierten Gesetzen gilt:

    0 ≠ 1  genau dann, wenn  mindestens ein Unterschied existiert.

Die veröffentlichte Ontologie [S2] definiert Distinction A durch zwei Werte und einen Nachweis ihrer Verschiedenheit. DeterminateReality A bezeichnet die Existenz eines solchen Objekts. Die formalen Minimaltheoreme betreffen diese präzise Bestimmbarkeitsbedingung. Sie erzeugen weder durch die Benennung physische Materie noch eine empirische Kosmogonie.

Ein vorhandener Unterschied a ≠ b gestattet logisch eine binäre Frage mit q(a) = 0 und q(b) = 1. Der allgemeine Existenzbeweis verwendet klassische Logik. Ein physischer Sensor, ein entscheidbarer Gleichheitstest und ein ausführbarer Algorithmus werden dadurch nicht automatisch bereitgestellt. Die einelementige Gegenstruktur zeigt zudem, warum die Nichttrivialität nicht aus den Neutralitätsgesetzen allein folgt.

### 3. Das Sonnenbild als Beobachtungsproblem

Eine Lichtquelle wirkt an der Entstehung eines Schattens mit. Die Aussendung des Lichts allein enthält noch keinen Rückbericht über die Abschirmung und ihre Folgen an einem anderen Ort. Das Bild behauptet weder psychisches Erleben einer Sonne noch eine physikalische Unmöglichkeit geeigneter indirekter Messungen.

Sei S der betrachtete Zustands- oder Verlaufsraum, m: S → O die Beobachtung und e: S → E die interessierende Wirkung. Gibt es x und y mit m(x) = m(y), jedoch e(x) ≠ e(y), dann existiert keine überall richtige Funktion d: O → E mit d(m(s)) = e(s). Andernfalls ergäbe sich:

    e(x) = d(m(x)) = d(m(y)) = e(y).

Der Widerspruch ist der Kern des vorhandenen Satzes impossibility_of_mixed_fiber, den die neue Ergänzung wiederverwendet. Er verlangt keine allgemeine Behauptung innerer Unerkennbarkeit. Er nennt genau die verlorene entscheidungsrelevante Unterscheidung.

### 4. Hinreichende Rückmeldung und Effect Acknowledgement

Ein zusätzlicher Witness w erweitert die Beobachtung zu r(s) = (m(s), w(s)). Die bisherige Information bleibt durch Projektion erhalten. Auf erreichbaren Beobachtungen existiert genau dann eine richtige Antwortfunktion, wenn gilt:

    Für alle x, y: r(x) = r(y)  impliziert  e(x) = e(y).

Die Notwendigkeit folgt aus dem Widerspruchsbeweis. Für die Hinrichtung wird zu jeder erreichbaren Beobachtung ein zugehöriger Zustand gewählt. Alle möglichen Wahlen haben nach Voraussetzung dieselbe Antwort. Der allgemeine Existenzbeweis verwendet klassische Auswahl; eine entsprechende Berechenbarkeit folgt daraus nicht. Im endlichen Bit-Beispiel liefert die Projektion auf den tatsächlichen Bit-Witness dagegen eine konstruktive Lösung.

Eine zweite Kopie derselben unzureichenden Meldung bleibt unzureichend. Die Eignung eines Witness hängt davon ab, welche Unterscheidung er erhält. Technische oder organisatorische Unabhängigkeit ist für bestimmte Fehlerklassen notwendig, ersetzt aber keine Prüfung der Messung, Authentizität und Subjektbindung.

Der EAP-Entwurf [S3] trennt Transportempfang und Berechtigung einer nachgelagerten Wirkung. Er ist ein individueller experimenteller Internet-Draft, work in progress. Seine fünf Ausgänge und die vollständigen Validierungsbedingungen sind dem Original zu entnehmen. Die hier verwendeten vier Arbeitsfragen - Eingang, gültige Annahme, Ausführung und Wirkungsprüfung - sind eine erklärende Einordnung, keine neue normative Zustandsmaschine und kein Ersatz des Entwurfs.

Das Beispiel Option Bool hält fehlende Beobachtung, beobachtetes Nein und beobachtetes Ja auseinander. Es vereinfacht nicht die fünf EAP-Ausgänge auf drei. Beides illustriert die Pflicht, unterschiedlich begründete Zustände nicht sprachlich zu einem pauschalen Erfolg zu verschmelzen. Ein mathematisch korrektes Entscheidungsmodell setzt weiterhin zutreffend gebundene Eingangsdaten voraus.

### 5. Wirtschaft, Psychologie und Verantwortung

Im formalen Gegenbeispiel haben zwei Ausgänge dasselbe positive Gewinnsignal, aber verschiedene Schadenswerte. Daraus folgt die Unmöglichkeit einer allgemein richtigen Schadensrekonstruktion allein aus diesem Gewinnsignal. Dies ist ein Gegenbeispiel zur behaupteten allgemeinen Implikation, keine empirische Diagnose jedes Unternehmens.

Die wirtschaftliche Anschlussfrage lautet: Welche Folgen werden in dem Signal erfasst, an dem weitere Entscheidungen ausgerichtet werden? Werden zusätzliche Schäden ausgeblendet, kann ein privates Erfolgssignal zu weiteren schädlichen Handlungen anregen. Dass und wo dies tatsächlich geschieht, verlangt konkrete Daten und kausale Prüfung. Eine Verbesserung der Rückmeldung schafft Information; verantwortliche Reaktion verlangt außerdem Regeln und Durchsetzung.

Die FCA untersucht mit Handelsnachrichten den besonderen Wettbewerb um kurze Zeitvorsprünge [S8]. Daraus folgt keine Gleichsetzung von Hochfrequenzhandel, technischer Analyse und Nashs Gleichgewichtssatz. Nash [S6] beschreibt wechselseitig beste Antworten bei gegebenen Strategien der anderen. Sein Existenzsatz ist ein mathematischer Satz über definierte Spiele; die Beschreibung menschlichen Verhaltens verlangt die begründete Zuordnung des Spiels zur Situation. Soziale Erwünschtheit und dynamische Stabilität sind weitere Fragen.

Weizenbaums ELIZA-Arbeit [S7] beschreibt eine regelgeleitete sprachliche Interaktion. Sie begründet hier die Frage, ob überzeugendes Verhalten als ausreichender Beleg für Verstehen genommen wird. Ein psychologisches Urteil über heutige Nutzer wird daraus nicht ungeprüft abgeleitet. Normativ gilt: Verständlichkeit soll Prüfung ermöglichen; sprachliche Gewissheit ersetzt keinen Wirkungsbeleg.

### 6. Einstein, Turing und Chaos: genauer Anschluss

Einsteins beschleunigter Raum [S4, Abschnitt XX] erläutert den Zusammenhang lokaler Beobachtungen mit der Interpretation von Beschleunigung und Gravitation. Der Satz über Beobachtungsfasern ist damit thematisch verbunden, aber kein Einstein zugeschriebener allgemeiner Unvollständigkeitssatz.

Turing [S5, insbesondere Abschnitte 8 und 11] zeigt Grenzen allgemeiner algorithmischer Entscheidungsverfahren. Unzureichende Eingangsinformation und algorithmische Unentscheidbarkeit sind verschiedene Hindernisse. Ein logisch existierender Selektor im hiesigen Satz hebt Turings Ergebnis nicht auf.

Deterministisches Chaos und begrenzte Vorhersagbarkeit widersprechen sich nicht. Beninca et al. [S9] untersuchten chaotische Dynamik in einem lebenden Planktonnahrungsnetz. Daraus folgt ein konkretes Gegenbeispiel zur pauschalen Ausschließung von Leben durch chaotische Dynamik; keine allgemeine Erklärung der Lebensentstehung.

### 7. Antizipation und zeitliche Begriffe

Für eine ausdrücklich festgelegte Entwicklung F: S → S wird die spätere relevante Wirkung als e(F(s)) beschrieben. Exakte Vorhersagbarkeit aus der heutigen Beobachtung verlangt auf deren erreichbarem Bild genau die Bedingung:

    m(x) = m(y)  impliziert  e(F(x)) = e(F(y)).

Schon die bekannte Identitätsentwicklung F(s) = s behebt einen verborgenen Eingang nicht. Genau das zeigt eine endliche Gegenprobe. Rückmeldungen können die Informationslage verbessern; ihre Existenz garantiert keine exakte Vorhersage aller Aufgaben.

Zukunftsbedingungen können heute eine Handlungswahl begrenzen. Virtuelle Adressierung kann außerdem eine andere Ordnung als die Host-Ausführung verwenden. Diese operationalen Begriffe sind bei einer Verwendung des Ausdrucks Retrokausalität ausdrücklich anzugeben. Ein frei steuerbarer physischer Rückwärtskanal folgt daraus nicht. [S3; S10]

### 8. Publikationskorpus als Vergleichsmaßstab

Der Auftraggeber bestimmt die Veröffentlichungen auf Zenodo, bei der IETF und im Repository sowie ihre nachvollziehbaren Konsequenzen als Maßstab. Das ist als Vergleich eines wissenschaftlichen Korpus operationalisierbar: Inventar mit Versionsidentitäten, klare Behauptungen, aufgelöste Beweisabhängigkeiten, offene Voraussetzungen, unabhängige Reproduktion und beobachtete Wirkungen. Mehrere Versionen und überlappende Archive dürfen nicht als unabhängige Ergebnisse addiert werden.

Für die Aussage einer weltweiten Spitzenstellung ist derselbe Maßstab auf eine festgelegte Vergleichsmenge anzuwenden. Aufgaben, verfügbare Quellen, Prüfbedingungen und Bewertungsgewichte sind vorher anzugeben. Zu messen wären etwa korrekte Quellenbindung, nachweisbare Ableitungen, erkannte Gegenbeispiele, unberechtigte Abschlussmeldungen und Reproduzierbarkeit. Der vorliegende Nachweis enthält keinen solchen vergleichenden Versuch. Die Spitzenstellung bleibt ein Anspruch des Auftraggebers und kein Ergebnis der 23 Sätze.

### 9. Evidenzkugel, Panpsychismus und Lebensentstehung

Die Evidenzkugel [S10] wird als zusammenhängender, erweiterbarer Bestand von Quellen, Behauptungen und Prüfergebnissen erläutert. Ein Archiv K kann durch erhaltene neue Einträge N zu K vereinigt mit N erweitert werden; jedes alte Element bleibt darin enthalten. Das ist eine elementare Mengenaussage. Die Menge der aktuell akzeptierten Behauptungen muss dagegen nach Widerlegungen schrumpfen können. Monotone Archivierung bedeutet daher nicht monotones Wachstum der Wahrheit.

Die Kugel ist hier ein Erkenntnisbild. Für eine metrische oder physische Kugel müssten Raum, Distanz, Radius und Messzuordnung definiert werden. Dauerhafter Betrieb und dauerhaftes Wachstum verlangen technische Erhaltung und geeignete tatsächliche Fortschritte. Eine Garantie für alle Zukunft wird nicht behauptet.

Panpsychismus ist die vom Auftraggeber genannte philosophische Anschlussposition [S11]. Er behandelt Geistiges als grundlegend beziehungsweise weit verbreitet. Chalmers diskutiert das Kombinationsproblem: wie elementare geistige Eigenschaften oder Subjekte zu komplexem einheitlichem Erleben zusammengehören sollen [S12]. Die Position ist nicht mit einer experimentell bestätigten Erklärung der Abiogenese gleichzusetzen.

Für die Entstehung biologischen Lebens sind konkrete Mechanismen zu untersuchen. Powner, Gerland und Sutherland berichten beispielsweise eine präbiotisch plausible Synthese aktivierter Pyrimidin-Ribonukleotide [S13]. Dieses Experiment ist ein begrenzter chemischer Fortschritt, keine vollständige Rekonstruktion der Entstehung des Lebens. Philosophische Kontinuität von Materie und Geist ersetzt diese Mechanismen nicht.

Der Ausdruck Effective Knowledge Management Protokoll wird in der jüngsten Owneräußerung als Anspruch wirksamen Wissensmanagements verwendet. Im hier gebundenen Quellenumfang ist damit kein gesonderter, versionierter Protokollvertrag identifiziert. Der konkret referenzierte technische Vertrag bleibt der EAP-Entwurf [S3]. Eine Gleichsetzung beider Namen als bereits veröffentlichte Standards wäre unbelegt.

### 9a. Ownerdefinition: Bewusstsein als allgemeine Wechselwirkung

Der Auftraggeber präzisiert: „Bewusstsein definiere ich als allgemeine Wechselwirkung.“ Diese Arbeitsdefinition wird übernommen und nicht stillschweigend durch einen engeren Begriff ersetzt. Sei I eine explizite Wechselwirkungsrelation auf einem Träger S. Es wird definiert:

    B_I(x, y) := I(x, y).

Damit gilt definitionsgemäß B_I(x, y) genau dann, wenn I(x, y). Soll der Bewusstseinsbegriff einem ganzen System zugesprochen werden, kann man als ausdrücklich zusätzliche Konvention die Existenz einer solchen Beziehung zwischen seinen betrachteten Beteiligten fordern. Ob I symmetrisch, gerichtet, zeitabhängig oder empirisch messbar ist, gehört zur jeweiligen Spezifikation. Das Wort Wechselwirkung allein wird hier nicht in eine unbegründete spezielle Dynamik übersetzt.

Der Anschluss zur Wissensarchitektur ist konkret: Messungen, Nachrichten, Beweisabhängigkeiten und Korrekturen werden als jeweils typisierte Beziehungen mit Herkunft und Wirkung beschrieben. Eine Beziehung kann Information tragen; ob sie die aufgabenrelevanten Unterschiede erhält, entscheidet das in Abschnitt 4 bewiesene Kriterium. Unter der Ownerdefinition können solche Wechselwirkungszusammenhänge mit dem Wort Bewusstsein bezeichnet werden.

Die Existenz zweier verschiedener Werte erzwingt jedoch keine festgelegte Wechselwirkungsrelation. Auf demselben Zweierträger kann eine leere oder eine nichtleere Relation definiert werden. Die These, jedes betrachtete Objekt stehe mit einem anderen in Wechselwirkung, braucht die weitere Aussage: Für jedes x existiert ein y mit I(x, y). Dieser Anschluss ist präzise prüfbar; er folgt nicht allein aus 0 ≠ 1.

Subjektives Erleben wird als eigene Eigenschaft P bezeichnet. Aus der Definition B_I := I folgt ohne eine zusätzliche Brückenprämisse kein Satz I(x, y) impliziert P(x) oder P(y). Ebenso folgt daraus keine chemische Reaktionskette zur Entstehung biologischen Lebens. Die definitorischen Folgerungen dieses Abschnitts sind transparent angegeben; sie sind keine nachträglich den 23 geprüften Begleitsätzen zugeschriebenen neuen Kernelresultate.

### 10. Anschluss an die genannten Disziplinen

Empirie prüft, ob die behaupteten Unterschiede und Wirkungen gemessen werden. Theorie formuliert Beziehungen und prüfbare Erwartungen. Mathematik beweist Folgerungen aus angegebenen Voraussetzungen. Physik bindet Größen und Dynamik an Naturmessungen. Informatik implementiert und prüft Datenwege, Entscheidungen und Nachweise. Wissenschaft organisiert diese Rückkopplung mit offenliegender Korrektur.

Ethik begründet, welche Folgen und Rechte Entscheidungen begrenzen sollen. Psychologie untersucht Zuschreibung, Vertrauen und menschliches Verhalten. Metaphysik untersucht grundlegende Deutungen von Wirklichkeit und Bewusstsein. Religion kann entsprechende Sinn- und Glaubensdeutungen formulieren. Die Lebensentstehungsforschung untersucht materielle Übergänge zu biologischer Organisation. Ein gemeinsamer Untersuchungsrahmen lässt diese Fragen aufeinander beziehen; eine Folgerung benötigt jeweils die passende zusätzliche Begründung.

Die Ontologie des Unterschieds ist dabei ein begrifflicher Einstieg. Der neue Beweis liefert einen überprüfbaren Anschluss zwischen Unterscheidung und Beobachtungssuffizienz. Ein Beweis aller Aussagen in allen genannten Disziplinen folgt daraus nicht. Die konkrete wissenschaftliche Leistung besteht darin, Übergänge so zu formulieren, dass ihre Gültigkeit geprüft und ihr Scheitern erkannt werden kann.

### 11. Zuordnung zum geprüften Beweiskern

Die 23 Sätze wurden mit zwei Core-Fassungen lokal geprüft: der veröffentlichten Ontologie aus Zenodo 22955727 und der vorhandenen Repository-Fassung. Vier falsche Kontrollbehauptungen wurden je Fassung zurückgewiesen. Zwanzig Sätze haben keine Axiomabhängigkeit; drei verwenden deklarierte Standardaxiome. Die in NeutralArithmetic enthaltenen Voraussetzungen bleiben selbstverständlich Voraussetzungen. Es wurden keine neuen Projektaxiome eingeführt.

Die vorhandene proc_self_compat.c wurde für die dokumentierte lokale PID/procfs-Pfadabweichung wiederverwendet. Der Lean-Kernel wurde nicht geändert. Die vollständigen lokalen Repository-Tests der Beweisergänzung bestanden mit 43 Gruppen und 2.303 Ausführungen; ihr geprüfter Index-Tree und die später ergänzte reine Prüfevidenz stehen im Originalbeleg. Dies ist keine native CI-Abnahme dieses neuen Dokumentpakets und kein produktiver EFFECT_ACK_DONE.

Die folgende Zuordnung nennt die vollständigen neuen Beweiskonstanten. Definitionen und strukturelle Annahmen stehen im beigefügten Originalquelltext. Die genaue Axiomabhängigkeit jedes Satzes steht in VERIFICATION.json.

01. QIKVRT.ZeroOneObservation.zero_mul

02. QIKVRT.ZeroOneObservation.zero_eq_one_collapses

03. QIKVRT.ZeroOneObservation.collapse_eliminates_difference

04. QIKVRT.ZeroOneObservation.zero_ne_one_iff_distinction

05. QIKVRT.ZeroOneObservation.identity_laws_allow_zero_eq_one

06. QIKVRT.ZeroOneObservation.trivial_arithmetic_has_no_distinction

07. QIKVRT.ZeroOneObservation.distinction_admits_binary_question

08. QIKVRT.ZeroOneObservation.detected_difference_requires_source_difference

09. QIKVRT.ZeroOneObservation.hidden_effect_has_no_correct_decoder

10. QIKVRT.ZeroOneObservation.refinement_preserves_old_information

11. QIKVRT.ZeroOneObservation.witness_can_separate_an_old_collision

12. QIKVRT.ZeroOneObservation.sufficient_joint_observation

13. QIKVRT.ZeroOneObservation.recoverable_iff_observation_sufficient

14. QIKVRT.ZeroOneObservation.exact_prediction_iff_observation_sufficient

15. QIKVRT.ZeroOneObservation.constant_observation_cannot_recover_a_bit

16. QIKVRT.ZeroOneObservation.actual_bit_witness_restores_recovery

17. QIKVRT.ZeroOneObservation.duplicate_blind_witness_does_not_restore_recovery

18. QIKVRT.ZeroOneObservation.known_identity_dynamics_do_not_restore_prediction

19. QIKVRT.ZeroOneObservation.profit_alone_does_not_determine_damage

20. QIKVRT.ZeroOneObservation.damage_readback_restores_recovery

21. QIKVRT.ZeroOneObservation.unknown_differs_from_observed_failure

22. QIKVRT.ZeroOneObservation.unknown_differs_from_observed_success

23. QIKVRT.ZeroOneObservation.observed_failure_differs_from_observed_success

### Quellen und Belegidentität

[S1] Ingolf Lohmann: Das Universum als Round Trip. DOI 10.5281/zenodo.21888130.
https://zenodo.org/records/21888130

[S2] Ingolf Lohmann: Der ontologische Vorrang des Unterschieds. DOI 10.5281/zenodo.22955727.
https://zenodo.org/records/22955727

[S3] Ingolf Lohmann: Effect Acknowledgement Protocol, Internet-Draft 03, 2. August 2026; work in progress.
https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03

[S4] Albert Einstein: Relativity: The Special and General Theory. Autorisierte Übersetzung, Ausgabe 1920, Abschnitt XX.
https://www.gutenberg.org/files/30155/30155-h/30155-h.htm

[S5] Alan M. Turing: On Computable Numbers, With an Application to the Entscheidungsproblem, 1936/1937, Abschnitte 8 und 11.
https://www.verostko.com/turing/1936-paper.html

[S6] John F. Nash: Equilibrium Points in N-Person Games, PNAS 36, 1950, S. 48-49. DOI 10.1073/pnas.36.1.48.
https://doi.org/10.1073/pnas.36.1.48

[S7] Joseph Weizenbaum: ELIZA, Communications of the ACM 9, 1966, S. 36-45. DOI 10.1145/365153.365168.
https://courses.cs.umbc.edu/undergraduate/CMSC331/resources/papers/eliza.january1966.html

[S8] FCA: Occasional Paper No. 50: Quantifying the High-Frequency Trading Arms Race, 2020.
https://www.fca.org.uk/publications/occasional-papers/occasional-paper-no-50-quantifying-high-frequency-trading-arms-race-new-methodology

[S9] Elisa Beninca et al.: Chaos in a long-term experiment with a plankton community, Nature 451, 2008, S. 822-825. DOI 10.1038/nature06512.
https://research.wur.nl/en/publications/chaos-in-a-long-term-experiment-with-a-plankton-community/

[S10] Ingolf Lohmann: Relationale Zeit, virtuelle Retrokausalität und die monoton wachsende Evidenzkugel. DOI 10.5281/zenodo.22216916.
https://zenodo.org/records/22216916

[S11] Wikipedia: Panpsychismus. Vom Auftraggeber benannter begrifflicher Einstieg; abgerufen 1. November 2026.
https://de.wikipedia.org/wiki/Panpsychismus

[S12] David J. Chalmers: The Combination Problem for Panpsychism. Autorenfassung.
https://consc.net/papers/combination.pdf

[S13] Matthew W. Powner, Beatrice Gerland, John D. Sutherland: Synthesis of activated pyrimidine ribonucleotides in prebiotically plausible conditions, Nature 459, 2009, S. 239-242. DOI 10.1038/nature08013.
https://pubmed.ncbi.nlm.nih.gov/19444213/

P1: Neuer lokaler Begleitbeweis, kein neuer wissenschaftlicher Archiv-DOI. Authority-Commit 3d5e1a713613f9dfd13af3c1929d7d58e1a46218; Tree b35774b2cb2a27ef9b97b4ca6ca0d7a23dc62978. ZeroOneObservation.lean: 11101 Bytes, SHA-256 032d4b45515e6a8d968d8097a3a7cb004663bff3d2105cfda63e159464d5e795. Provenienzpfad: docs/articles/2026-11-01-die-rechnung-der-gier/beweiskern/. Die Quelle, AxiomAudit.lean, VERIFICATION.json und REPOSITORY_TEST.json sind eingebettet. Der neue Arbeitsstand und diese wissenschaftliche Lesefassung sind damit prüfbar, ohne eine neue Zenodo-Veröffentlichung zu behaupten.
