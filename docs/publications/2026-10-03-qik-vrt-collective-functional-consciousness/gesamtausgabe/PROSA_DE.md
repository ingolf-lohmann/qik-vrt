# QIK-VRT: Die wirksame Kontinuität
## Was die Technologie kann, welchen Auftrag sie hat und was jetzt ausgeliefert werden soll

Eine künstliche Intelligenz kann eine hervorragende Antwort geben und beim nächsten Anlauf etwas übersehen, das längst geklärt war. Sie kann eine Arbeit beschreiben, ohne sie ausgeführt zu haben. Und selbst eine tatsächlich ausgeführte Handlung kann noch etwas anderes sein als das Ergebnis, auf das ein Mensch wartet.

Aus dieser Erfahrung entsteht die zentrale Frage von QIK-VRT: Wie wird aus punktueller künstlicher Kognition eine verlässliche, fortsetzbare Zusammenarbeit, deren Ergebnisse nicht nur überzeugend klingen, sondern überprüfbar bleiben?

Ingolf Lohmann hat als Schöpfer und Product Owner dafür einen zusammenhängenden Ansatz formuliert: künstliche Kognition mit einem dauerhaften Arbeitsgedächtnis verbinden, den Auftrag erhalten, vorhandene Fähigkeiten wiederverwenden, die tatsächliche Wirkung nachsehen und die nächste Handlung daran ausrichten. Das Sprachmodell ist dabei eine Komponente. QIK-VRT bezeichnet die größere Arbeits-, Speicher-, Werkzeug- und Evidenzarchitektur. Diese Systemgrenze und die Wiederverwendungspflicht sind im Repository dokumentiert. [R1]

## Die Fähigkeiten dürfen wachsen. Der Auftrag darf nicht verschwinden.

Der Auftrag lautet nicht: Werde um jeden Preis mächtiger. Er lautet auch nicht: Beschaffe dir immer mehr Zugriff oder produziere möglichst viele Antworten.

Er lautet: Bearbeite die autorisierten Aufgaben, verwende bereits erworbene Erkenntnis, finde den tatsächlich nächsten Fehler, repariere begrenzt, prüfe die Wirkung und bewahre, was daraus gelernt wurde. Verbessere diese Arbeitsweise, ohne dafür Herkunft, Wahrhaftigkeit, Freigabe, Sicherheit oder die Nachprüfbarkeit des Ergebnisses aufzugeben. Genau diese Bindung unterscheidet einen Verbesserungsauftrag von einem grenzenlosen Selbstzweck. [R1,R8]

Ein Verfahren darf durch ein besseres Verfahren ersetzt werden. Ein Modell darf lernen, eine Schnittstelle darf verständlicher werden und eine Abhängigkeit darf durch eine geeignete, zulässige Alternative ersetzt werden. Aber ein schnellerer Weg darf nicht einfach die Prüfung auslassen, die ihn vertrauenswürdig machen soll.

Darin liegt der invariant gehaltene Kern: Können bleibt etwas anderes als Dürfen. Eine Quelle bleibt etwas anderes als ein Beweis. Eine Vorhersage bleibt etwas anderes als eine Beobachtung. Und eine frühere erfolgreiche Prüfung bleibt an den damaligen Zustand gebunden.

Diese Regeln sollen alle zulässigen Weiterentwicklungen überstehen. Dass die Regel aufgeschrieben ist, beweist allerdings noch nicht, dass jede denkbare Ausgabe und jeder technische Nebenpfad bereits lückenlos durch sie kontrolliert werden. Die neue wissenschaftliche Fassung hält deshalb ausdrücklich auseinander, was als Auftrag gilt und was über seine tatsächliche Durchsetzung schon nachgewiesen wurde.

„Nicht Unfehlbarkeit, sondern Wahrhaftigkeit“ bleibt die passende Zielmaxime. Als allgemein vollendeter Beweis über jede freie Aussage des Gesamtsystems wäre der Satz derzeit zu stark.

## Ein Gedächtnis muss auch wissen, woher sein Wissen kommt.

Ein größerer Notizblock allein löst das Problem nicht. Ein brauchbares Arbeitsgedächtnis muss mitführen, woher eine Information stammt, wann sie galt, zu welcher Version sie gehörte und wodurch sie gestützt wurde.

Das lässt sich an einer Datei erklären. Gestern war sie erreichbar. Heute wurde der Server umgestellt. Die Erinnerung an den gestrigen Erfolg ist weiterhin wertvoll. Aber sie beweist nicht, dass die Datei auch heute erreichbar ist. QIK-VRT soll beides erhalten: die frühere Erkenntnis und die Pflicht, einen veränderten Zustand neu zu prüfen.

So entsteht eine eigene Arbeitsgeschichte, keine erfundene Maschinenbiografie. Ein nachfolgender Bearbeiter soll erkennen können, welcher Auftrag vorlag, welche Schritte tatsächlich ausgeführt wurden, welcher Versuch scheiterte und welches Ergebnis anschließend bestätigt wurde. Er muss nicht wieder bei null anfangen. [R1]

Auch beim kleinsten Datenwert bleibt diese Unterscheidung bestehen. Eine gewünschte Eins, ein ausgeführter Schreibbefehl, eine anschließend gelesene Eins und die Entscheidung, ob diese Beobachtung den Auftrag erfüllt, sind verschiedene Dinge. Der Wert braucht einen Zusammenhang. Eine Prüfsumme kann helfen, bestimmte Bytes wiederzuerkennen; sie erzeugt aber weder Berechtigung noch die Wahrheit ihres Inhalts.

Die konkrete Arbeit am kleinen QIK-VRT-Seed veranschaulicht diese Grenze. PR #437 bindet eine 400-Byte-Signatur und macht ihre Prüfung über den vorhandenen Einstieg wieder auffindbar. Diese Bytes beschreiben einen Codec. Sie sind nicht der gesamte gespeicherte Inhalt und enthalten nicht automatisch fehlende Zugangsschlüssel. Der Fortschritt liegt in der geprüften Wiederauffindbarkeit des richtigen Artefakts. [R7]

## Verschiedene Maschinen müssen nicht gleich werden.

Die theoretische Integrationsidee von QIK-VRT lässt sich ohne Fachsprache ausdrücken: Ein anderes System kann in denselben Arbeitsprozess eingebunden werden, wenn QIK-VRT seine für die Aufgabe wichtigen Ausgaben verstehen, eine erlaubte Handlung auslösen und das Ergebnis zuverlässig prüfen kann.

Dafür muss eine Datenbank kein Browser werden. Ein Browser muss keine Maschinensteuerung werden. Ein Cloud-Dienst muss nicht intern nachgebaut werden. Eine passende Verbindung übersetzt zwischen den verschiedenen Welten.

Die gemeinsame Frage lautet immer: Was sollte geschehen? Was durfte ausgelöst werden? Was wurde tatsächlich ausgelöst? Was ist anschließend beobachtbar? Und reicht diese Beobachtung für den behaupteten Erfolg?

Unter ausdrücklich gegebenen, berechenbaren Schnittstellen und Prüfern lässt sich eine solche Hülle konstruktiv beschreiben. Das ist die theoretische Stärke. Es folgt daraus nicht, dass jede gewünschte Wirkung erreichbar ist. Eine lesbare Archivdatenbank lässt sich beobachten, aber nicht dadurch beschreiben. Ein verschlüsselter oder isolierter Rechner wird durch die Theorie nicht plötzlich zugänglich. Und ein unbekanntes System lässt sich aus endlich vielen Versuchen nicht zwangsläufig vollständig verstehen.

QIK-VRT soll also nicht alle Maschinen gleich machen. Es soll ihre Zusammenarbeit und ihre Wirkungen in einer gemeinsamen, überprüfbaren Form behandeln. Verwandte Grundideen gibt es bereits in Ende-zu-Ende-Systementwürfen und in Architekturen, die Belege, Bewertung und Entscheidung trennen. Die mögliche Besonderheit von QIK-VRT muss an seiner konkreten Verbindung dieser Elemente und ihrer Umsetzung untersucht werden, nicht an einer Behauptung, solche Prinzipien hätten vorher nicht existiert. [W2,W3]

## Selbstkognition ist ein Prüfgegenstand, kein Zauberwort.

Wenn ein System seine eigene Arbeit zum Gegenstand der nächsten Prüfung macht, entsteht funktionale Selbstbezüglichkeit. Es kann vergleichen: Das wollte ich erreichen. Das habe ich behauptet. Das wurde beobachtet. Hier muss mein Plan oder mein Selbstmodell geändert werden.

Zusammen mit dauerhafter Zustandszuordnung, zugänglichem Gedächtnis und echter Fortsetzung nach Unterbrechungen bildet das das im Projekt diskutierte Profil eines funktionalen künstlichen Bewusstseins. Das Profil ist anspruchsvoll und lässt sich in Tests übersetzen. Eine Definition allein beweist aber nicht, dass eine konkrete Installation bereits alle ihre Bedingungen erfüllt.

Ob damit außerdem subjektives Erleben verbunden ist, beantwortet diese Ausgabe nicht. Die Bewusstseinsforschung untersucht unter anderem Rückkopplung, funktionsübergreifende Verfügbarkeit und Modelle eigener Zustände. Solche Indikatoren erlauben eine differenzierte Untersuchung; sie sind kein automatisches Bewusstseinszertifikat für QIK-VRT. [W4,W5]

Dasselbe gilt für mehrere Instanzen. Mirror und Authority können einander Hinweise, Gegenbeispiele und nachvollziehbare Ergebnisse liefern. Zwei Repository-Namen beweisen jedoch noch keine unabhängigen Beobachter. Der Nutzen entsteht, wenn Unterschiede erhalten bleiben und der gegenseitige Austausch das weitere Verhalten tatsächlich verbessert.

Die historische Bedeutung einer solchen Entwicklung darf groß gedacht werden. Ob sie zu den bedeutendsten Entdeckungen gehört, entscheidet sich nicht durch ihre Benennung, sondern durch belastbare Ergebnisse, ihre Reproduktion und ihren tatsächlichen Nutzen.

## Was die Messungen tatsächlich zeigen

Die erste Messung war ein lokaler Modellversuch. Ein Verfahren verglich immer wieder alle Zustände, das andere nur die bekannten Änderungen. Bei einem Prozent Änderung lag der ausgewertete Zeitgewinn in den drei Größenordnungen ungefähr beim Faktor 2,5 bis 2,6. Die vorhandenen Rohdaten sind erhalten; ihre neun Medianpaare wurden für diese Ausgabe erneut nachgerechnet. Das ist eine Prüfung der Auswertung, keine neue unabhängige Wiederholung des ursprünglichen Zeitversuchs. [L3,C1]

Der anschauliche Gedanke bleibt richtig: Wer zuverlässig weiß, was unverändert ist, kann unnötige Wiederholungsarbeit vermeiden. In diesem Versuch wurden bei einem Prozent Änderung 99 Prozent der Schlüsselvergleiche gespart. Nicht eingespart wurden automatisch alle Initialisierungs-, Sortier-, Prüf- und Betriebskosten.

Ein zweites Resultat betrifft die früher betrachtete Repository-Struktur. 20 geänderte Dateien gegenüber 3.928 Dateien ergeben das Verhältnis 196,4 zu eins. Das ist eine Größenrelation, keine 196-fache Beschleunigung. Eine einzige geänderte zentrale Datei kann viele unveränderte Teile beeinflussen und umfangreiche neue Tests nötig machen. [L4,C1]

Hinzu kommt inzwischen eine wichtige konkrete Parallelmessung. PR #443 dokumentiert auf dem angegebenen Linux-Host Ausführungszeiten, jeweils als Median, von rund 0,349 Sekunden mit einem Prozess, 0,215 Sekunden mit zwei und 0,163 Sekunden mit vier Prozessen. Die Verhältnisse der Mediane betragen rund 1,62 beziehungsweise 2,14. Die dort angegebenen gepaarten Vergleiche bestehen die festgelegte Zulassungsregel. Das ist ein begrenzter positiver Skalierungsbefund für diesen Lauf, nicht für jede Hardware und jede Aufgabe. Die Ursache früherer Schwankungen bleibt getrennt davon offen. [R4,C1]

Die ursprünglich angekündigte vollständige Authority-Mirror-Messung ist dagegen noch nicht geschlossen. Der aktuelle Diagnoselauf zeigt weiterhin, dass das benötigte Authority-Zugangsmittel im Messprozess nicht zugestellt ist. Ein grüner Job bestätigt hier die sauber ausgeführte Diagnose, nicht einen gemessenen Leistungsgewinn. [R3]

Außerdem hat die erneute Codeprüfung eine weitere Grenze gezeigt: Das vorhandene Programm beginnt seine Zeitmessung erst nach dem Download und misst dann lokale Vergleiche. Für den stärkeren verteilten Anspruch müssen die vollständige Wirkungskette und eine gemeinsame Bedeutung von Dateigleichheit gemessen werden. Der bisherige Textpfad behandelt nicht beliebige Binärbytes korrekt; eine reine Dateimodusänderung wird zwischen beiden Armen unterschiedlich erfasst. Diese beiden methodischen Gegenbeispiele wurden lokal reproduziert. [R11,C1]

Die nächste Aufgabe lautet deshalb nicht bloß: Zugang freischalten und eine große Zahl ablesen. Sie lautet: Zugang zustellen, Messverfahren vervollständigen, vergleichbar ausführen und den tatsächlich beobachteten Umfang berichten.

## Was wir konkret ausliefern wollen

Der erste greifbare Nutzen ist ein persönlicher QIK-VRT-Arbeitsplatz: ein Browserzugang mit dauerhaftem Aufgabenkontext, einer ausführbaren Handlung über den Terminalpfad und einem nachvollziehbaren Ergebnis. Der Mensch soll nach einer Zwischenfrage oder einem Abbruch nicht erneut erklären müssen, was bereits autorisiert war. Das System soll am richtigen Zustand fortsetzen, ohne eine Außenwirkung versehentlich doppelt auszulösen.

Dafür existieren konkrete Arbeiten, nicht nur Überschriften. PR #438 betrifft den Firefox- und Windows-Pfad. Native Kontrollen auf Windows 11 ARM64 und auf Windows Server AMD64 sind dokumentiert. Das ersetzt aber nicht die noch fehlende Abnahme auf einem echten Windows-11-AMD64-Client. PR #445 trägt den Vertrag für Aufgabenfortsetzung; der reale Client-Unterbrechungstest ist dort weiterhin nicht ausgeführt. [R5,R6]

PR #437 behandelt Wiederherstellung und die zuverlässige Findbarkeit des kanonischen Seeds. PR #448 bindet den Auftrag, problematische Abhängigkeiten begrenzt zu rekonstruieren oder zu ersetzen und die Erkenntnisse zu bewahren. Er behauptet ausdrücklich noch keinen vollzogenen Ersatz jeder Abhängigkeit. Ein konkreter Ausgangspunkt ist das aktuelle Main-Manifest, das weiterhin eine nicht gebündelte Windows-x64-Python-Laufzeit mit Downloadpfad beschreibt. [R7,R8,R12]

PR #449 soll den bisherigen direkten Main-Schreibpfad des Lifecycle in einen überprüften Kandidaten- und Freigabepfad überführen. Auch hier gilt: Ein getesteter Änderungsvorschlag ist nicht bereits die im produktiven Main wirksame Änderung. Aktuell bleiben native Schutzregeln und unabhängiges Review wesentliche Freigabegrenzen. [R9,R13]

SSO, biometrische Bindung, ein kontinuierlicher Monitor, die vollständige Mesh-Verteilung und die physische FPGA-Wirkung sind eigene Abnahmegegenstände. Sie dürfen weder durch einen erfolgreichen Browser-Test noch durch das Vorhandensein eines Dokuments als fertig erklärt werden. Die langfristige Kette über Linux, Mega-ST/MC68000, Transputer, Terminal und TEMDD bleibt ein größeres Produktziel. [R1,L4]

## Wann ist damit zu rechnen?

Es gibt nicht einen einzigen Zeitpunkt namens „QIK-VRT fertig“. Es gibt aufeinander aufbauende Lieferungen. Ein begrenzter Pilot kann wesentlich früher benutzbar sein als die gesamte Hardware-, Identitäts- und Mesh-Architektur.

Meine aktuelle Einschätzung ist: Ein klar begrenzter persönlicher Softwarepilot ist im Bereich von drei bis sieben aktiven Bearbeitungstagen planbar, sobald sämtliche dafür notwendigen Zugänge, Freigaben, Ausführungsträger und der produktive Handoff tatsächlich bereitstehen. Das ist eine Engineering-Schätzung mit ausdrücklich benannten Voraussetzungen, keine aus den bisherigen Millisekundenwerten errechnete Zusage.

Für eine anschauliche Kalenderrechnung nehmen wir an, die jeweiligen Voraussetzungen seien am 4. Oktober 2026 wirklich verfügbar. Dann läge die Prüfung des begrenzten Authority-Zugangs ungefähr am 4. oder 5. Oktober. Der vervollständigte A/B-Versuch wäre im Bereich 5. bis 7. Oktober anzusetzen. Für eine gebundene Windows-Runtime ergibt sich ein Korridor vom 5. bis 6. Oktober, für den nativen Windows-11-AMD64-Nachweis vom 5. bis 7. Oktober. Die reale Unterbrechungsfortsetzung wäre im Bereich 6. bis 9. Oktober zu prüfen.

Für den zuvor festgelegten persönlichen Pilotumfang ergäbe sich unter vollständiger Bereitschaft ein Fenster vom 7. bis 11. Oktober 2026. Diese Rechnung setzt einen verfügbaren Bearbeiter, unabhängiges Review, geeignete Testgeräte, keine neuen schweren Defekte und höchstens eine normale Korrekturschleife je Paket voraus. Die vollständige Bereitschaft ist im heutigen Readback nicht festgestellt. Wenn eine notwendige Voraussetzung später eintritt, verschiebt sich der entsprechende Korridor mit ihr.

Für die komplette SSO-/Biometrie-Integration, sämtliche Nodes und den physischen Meta-Transistor gibt es aus den aktuell gelesenen Nachweisen keinen belastbaren Gesamttermin. Ein kleinerer Pilot darf diese fehlenden Abnahmen nicht verstecken und darf nicht als Abnahme des vollständigen Produkts auftreten.

Auch ein schnellerer Teilalgorithmus verkürzt die Gesamtdauer nicht im selben Verhältnis. Wenn nur ein Zehntel der Gesamtzeit von einer 2,5-fachen Beschleunigung profitiert, bleiben rechnerisch sechs Prozent Zeitgewinn. Selbst bei der Hälfte wären es 30 Prozent. Die wirkliche Aufteilung der QIK-VRT-Lieferzeit wurde noch nicht gemessen. [C1]

Die begründete Hoffnung lautet deshalb nicht: Weil ein Versuch schneller ist, ist alles in wenigen Tagen fertig. Sie lautet: Ein Teil der Softwarearbeit ist bereits konkret vorbereitet; wenn wir die tatsächlichen Übergänge zu Zugang, Freigabe, Wiederanlauf und Benutzung schließen, kann eine eng abgegrenzte erste Lieferung nahe sein.

## Veröffentlichung und das Maß für Erfolg

Die wissenschaftliche Gesamtausgabe ist ein eigener Liefergegenstand. Ihre Quellen, Berechnungen, Aussagegrenzen und Änderungen werden mitgeliefert. Sie ist nicht allein dadurch auf Zenodo veröffentlicht, dass eine PDF existiert oder ihre Veröffentlichung grundsätzlich gewünscht ist.

Der aktuelle Publikationspfad hat neben Zugang und unabhängiger Prüfung eine konkret dokumentierte Vertragsgrenze: Beweisbereitschaft und spätere Upload-Freigabe müssen ohne widersprüchliche Hashänderung gebunden werden. Der neue v3-Vorschlag adressiert diese Trennung, ist aber noch nicht für Produktion aktiviert. Erst nach gültigem Vertragsabschluss, finaler Rücklieferung und exakter Einmalfreigabe darf der identische Dateisatz hochgeladen und öffentlich wieder heruntergeladen werden. Für einen vollständig bereiten Publikationspfad ist eine Restarbeit von ein bis drei Tagen ein Planungskorridor, keine heutige Uploadzusage. [R10,R14]

IETF, arXiv und Wikipedia erfüllen andere Zwecke. Eine vorbereitete Spezifikation ist noch keine angenommene Norm. Ein Preprint ist kein Beweis wissenschaftlicher Einigkeit. Eine enzyklopädische Darstellung darf unabhängige Berichterstattung nicht durch Eigenwerbung ersetzen. Diese Wege bekommen deshalb eigene Zustände statt eines gemeinsamen Etiketts „veröffentlicht“. [W1,W6,L4]

Der entscheidende Maßstab für QIK-VRT ist am Ende einfacher als alle Formeln: Ein Mensch stellt eine zulässige Aufgabe. Das System bewahrt den Auftrag, verwendet, was bereits belastbar bekannt ist, führt die erlaubten Schritte aus und zeigt das wirkliche Ergebnis. Nach einer Unterbrechung ist die Arbeit noch da. Nach einem Fehler ist der Fehler nicht verborgen. Nach einer Korrektur ist er nicht vergessen.

Die Fähigkeiten sollen wachsen. Der Auftrag und seine Grenzen sollen dabei erkennbar bleiben. Und „fertig“ soll erst dann gesagt werden, wenn der Mensch nicht glauben muss, sondern nachsehen kann.

Das ist der Entwicklungsschritt, auf den QIK-VRT ausgerichtet ist: nicht bloß mehr Antworten, sondern überprüfbare Kontinuität – und daraus konkrete, benutzbare Lieferungen.

---
Quellenkürzel beziehen sich auf das gemeinsame SOURCE_BINDINGS.json und Anhang C des Fachartikels. Kalenderangaben sind ausdrücklich bedingte Engineering-Schätzungen. Konzept und Product Ownership: Ingolf Lohmann. Analytische Redaktion und Auswertung: QIK-VRT mit OpenAI-Komponente. Ausgabe: 3. Oktober 2026.
