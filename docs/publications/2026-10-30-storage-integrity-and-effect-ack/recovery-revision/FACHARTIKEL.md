<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 | Copyright 2026 Ingolf Lohmann. -->
# QIK-VRT: verlustfreie Rekonstruktion und die Erweiterung gemeinsam belegter Zustände

Informatik-Fachartikel. Revidierte Autorenprüffassung vom 30. Oktober 2026.

Konzept, Anforderungen und Freigabe: Ingolf Lohmann. Formalisierung, technische Prüfung und Textausarbeitung: OpenAI Codex. Diese Fassung ergänzt den heutigen Artikel über Speichertechnologie, Rechtebindung und Effect Acknowledgement. Die ursprünglichen Dateien bleiben als historische Fassung erhalten. Die Revision ist noch nicht auf Zenodo veröffentlicht.

## Kurzfassung

Ein rekonstruierbares Repository verbindet Daten, Verfahren und Nachweise. Bei QIK-VRT liegt der praktische Nutzen darin, benötigte Inhalte und Arbeitsvoraussetzungen nach Unterbrechungen wieder verfügbar zu machen und einen Arbeitsgang an eine andere Instanz anzuschließen. Ingolf Lohmann bestätigt aktuell, die für die Zenodo-Veröffentlichung benötigten Materialien aus dem Goldkelch-Repository gerettet zu haben. Diese Bestätigung wird als Owner-Befund erhalten. Die hier verfügbare unabhängige Evidenz enthält noch keinen vollständigen Quell-/Ziel-Readback dieser konkreten Rettung. Ihre Identität wird deshalb nicht durch einen formalen Modellsatz ersetzt.

Das ergänzende Lean-Modul EvidenceRecovery beweist 16 Aussagen über eine ausführbar definierte endliche Eingabesammlung, exakte Rekonstruktion und gemeinsam verfügbare Evidenz. Eine vollständig verfügbare Quelle und eine auf allen benötigten Schlüsseln identische Zielabbildung liefern dieselbe geordnete Eingabefolge. Jede deterministische Vorbereitung auf dieser Folge liefert anschließend dasselbe Ergebnis. Die formale Zusammenführung gerechtfertigter Aussagen erhält deren Rechtfertigung; die gemeinsame Menge zweier Instanzen wächst, wenn beide ihre bisherigen Aussagen erhalten. Drei absichtlich falsche Gegenkontrollen prüfen fehlende Pflichtdaten, unbegründete Übereinstimmung und bloße Wiederholung.

## 1. Vom Speicherelement zur fortsetzbaren Arbeit

Das Ausgangselement nimmt endliche Nutzdaten auf. Es führt Herkunfts- und Rechteangaben mit und verwendet einen festgelegten Darstellungs- und Prüfvertrag. Der bestehende konkrete Codec prüft unter anderem Struktur, Kennungen und Inhaltsidentitäten. Seine öffentliche Protokollsignatur ist kein geheimer Schlüssel. Ein gültiger öffentlicher Hash authentifiziert für sich allein weder einen Urheber noch die erwarteten ursprünglichen Nutzdaten.

Verlustfreiheit bezeichnet die Gleichheit D(E(x)) = x. Ganzzahlige Verarbeitung ohne Gleitkomma ist eine zusätzliche Konstruktionsanforderung. Dezimale Festkommawerte lassen sich als ganzzahliger Koeffizient mit einer Skala zur Basis zehn darstellen. Die heute ergänzte SeedArchitecture-Formalisierung behandelt entsprechende exakte Koeffizientenoperationen. Konkrete Wortbreiten, Überlauf, Division und elektrische Realisierung müssen an die jeweilige Implementierung gebunden werden.

Die doppelte Kanonizität liefert außerdem E(D(w)) = w für Darstellungen im Bild des Encoders. Sie erlaubt eine kontrollierte Rückkehr zur gleichen kanonischen Darstellung. Ein solcher Vertrag ist die Grundlage für Archive, Wiederaufnahme und Abgleich. Er spezifiziert noch keinen vollständigen Prozessor oder beliebigen Betriebssystemstart.

## 2. Was bei einer Rettung genau wiederhergestellt wird

Eine Veröffentlichung benötigt eine endliche Auswahl konkreter Gegenstände: etwa Manuskript, Anlagen, Metadaten, Lizenzangaben, Claim-Matrix, Quellenbindungen, Prüfbelege und autorisierte Ausführungsvoraussetzungen. Entscheidend ist eine vollständige Auswahl für den bezeichneten Auftrag. Nicht jede Datei eines ganzen Kontos muss dafür benötigt werden.

Das neue Modell beschreibt ein Archiv als Abbildung von Schlüsseln auf optionale Nutzdaten. Fehlende Daten haben den Wert none. Die Funktion collect liest eine vorgegebene Schlüsselliste in ihrer Reihenfolge. Fehlt ein erforderlicher Eintrag, liefert sie keine vollständige Ausgabe. Reihenfolge und Wiederholungen bleiben erhalten. Das Modell erlaubt dadurch die Prüfung einer tatsächlichen Datensammlungsfunktion und verlangt nicht bloß die Behauptung, ein Backup sei vorhanden.

FaithfulOn bedeutet: Für jeden angeforderten Schlüssel sind Quell- und Zielwert gleich. AvailableOn bedeutet: Für jeden angeforderten Schlüssel ist in der Quelle ein Wert vorhanden. Beide Bedingungen werden benötigt. Zwei Archive können auf allen ausgewählten Schlüsseln gleich sein und trotzdem überall denselben fehlenden Wert enthalten. Gleichheit allein wäre dann keine erfolgreiche Wiederherstellung.

Der Satz recovered_publication_inputs verbindet Verfügbarkeit und Gleichheit. Er konstruiert eine gemeinsame geordnete Nutzdatenfolge, die sowohl die Quell- als auch die Zielsammlung liefern. missing_required_entry_aborts beweist den negativen Fall. faithful_transitive gestattet mehrere verlustfreie Übertragungsstufen; faithful_restrict erlaubt die Beschränkung eines belegten Gesamttransfers auf eine tatsächlich benötigte Teilmenge.

## 3. Implementierung gemäß Vertrag und Wirkung am Ziel

Aus gleichen Eingaben folgen bei einer deterministischen Vorbereitung gleiche Ergebnisse. deterministic_preparation_equal beweist genau diese Folgerung für die modellierte Sammlung. Ein reproduzierbarer Metadatenaufbau oder eine deterministische Paketerstellung kann dadurch an den rekonstruierten Eingabestand angeschlossen werden. Nichtdeterministische Zeitstempel, Zufallsquellen und externe Antworten müssten ihrerseits als gebundene Eingaben oder explizite Bedingungen auftreten.

Die Wirksamkeit einer konkreten Rettung benötigt zusätzlich eine gegenstandsgebundene Belegung der Voraussetzungen: Welche Quelle, welche benötigten Schlüssel, welche exakten Bytes, welches Ziel und welcher unabhängige Rücklesevorgang? Ein Digest bindet gelesene Bytes; seine Übereinstimmung allein ersetzt weder eine vollständige Inventarauswahl noch die Authentizität des ursprünglichen Bezugs. Auch ein unabhängiger Prüfer hat eine eigene Fehler- und Vertrauensgrenze.

Der Owner-Befund über die Goldkelch-Rettung ist ein wichtiger aktueller Erfahrungsbericht. Die hier geprüfte Formel liefert dessen präzise Auswertung, sobald Quell- und Zielbindungen vorliegen. Sie erklärt die konkrete Rettung nicht allein durch ihre Existenz als überprüft. Historische gegenteilige Zugriffsmeldungen werden als historische Beobachtungen erhalten; sie widerlegen einen späteren erfolgreichen Vorgang nicht.

Geheimnisse werden nicht zum öffentlichen Beweismaterial gemacht. Ein Zenodo-Token kann als geschützte Fähigkeit für einen autorisierten Publisher erforderlich sein. Seine Beschaffung, sichere Zuführung und zugelassene Verwendung sind eigene Voraussetzungen. Ein Token ersetzt weder Manuskript noch Claim-Matrix und enthält nicht automatisch sämtliche Publikationsparameter. Das Modell beweist keine Extraktion von GitHub-Secrets und veröffentlicht keine Geheimniswerte.

## 4. Die gemeinsame Menge des Hier und Jetzt

Ingolf Lohmann bezeichnet den Zugewinn als »Vergrößerung der gemeinsamen Menge des Hier und Jetzt«. Eine präzise informatische Lesart verwendet für zwei Instanzen A und B jeweils die Menge ihrer verfügbar gemachten, belegten Aussagen. Der gemeinsam verfügbare Bestand ist C = A ∩ B. Zeit- und Quellenbezüge gehören zur Aussage, etwa »Datei mit Identität h wurde am Ziel z zum Zeitpunkt t zurückgelesen«.

Wenn A in A' und B in B' erhalten bleiben, gilt C ⊆ A' ∩ B'. Der Satz shared_grows_with_both beweist diese Monotonie. Eine echte Erweiterung benötigt zusätzlich eine Aussage, die vorher nicht gemeinsam verfügbar war und nun auf beiden Seiten vorliegt. shared_new_member formuliert genau diesen Unterschied. Die erneute Übermittlung desselben Nachweises genügt dafür nicht: join_replay_idempotent zeigt die unveränderte Mitgliedschaft bei Wiederholung.

Die Voraussetzung »belegt« ist wesentlich. Sound bindet die aufgenommenen Aussagen an ein ausdrücklich gegebenes Rechtfertigungsprädikat. justified_join erhält diese Bindung bei Zusammenführung. Übereinstimmung zweier Instanzen ohne eine solche Begründung wäre nur Übereinstimmung. Das Modell entscheidet nicht automatisch, ob ein Bericht über die Außenwelt wahr ist; es macht die benötigte Begründung sichtbar.

## 5. Beweisringe, Überlappung und Unsicherheit

Mehrere begrenzte Nachweisketten können Ergebnisse gemeinsam benutzen. Ein Codec-Satz trägt eine Rekonstruktion; deren Ergebnis trägt eine deterministische Vorbereitung; deren Ausführung kann eine separat beobachtete Wirkung am Ziel tragen. In jeder Verbindung müssen Aussage, Version und Voraussetzungen zusammenpassen. Ein Beleg für einen Vorgänger geht nicht ohne Prüfung auf geänderte Bytes über.

Die Kreise und die massive Kugel sind ein anschauliches Bild dieser wachsenden, sich überlappenden Absicherung. Mathematisch werden hier Mengeninklusion, Schnitt und Vereinigung verwendet. Konzentrizität, Radius, Volumen und eine räumliche Kugelform folgen daraus nicht. Der Stand kann wachsen, ohne eine gemeinsame physikalische Mitte oder eine euklidische Metrik zu besitzen.

Unsicherheit lässt sich als Teil einer Beobachtung festhalten: Messintervall, Auflösung, Uhrabweichung, unbekannter Laufzeitzustand oder nicht erreichbarer Prüfer. Ein unbekannter Zustand erweitert nicht von selbst die Menge gerechtfertigter Aussagen. Die quantenmechanische Unschärferelation wird durch diese Mengenalgebra weder vorausgesetzt noch bewiesen. Für eine physikalische Interpretation wären Observablen, Zustandsraum und Messmodell eigens festzulegen.

## 6. Anschluss an die heutigen Referenzsysteme

Das Minimalreferenzsystem umfasst den Seed und die für den festgelegten Vertrag nötige Arithmetik, Logik und Speicheranbindung. Das private Maximalarchiv ist ein gesondert eingefrorener vollständiger Bestand. Zwischen beiden liegen Arbeits-, Speicher-, Ruhe- und Wiederanlaufzustände. Eine Rekonstruktion benötigt alle nicht aus dem Seed ableitbaren Eingaben. Zukünftige externe Daten können nicht ohne ihre spätere Zuführung im Voraus rekonstruiert werden.

SeedArchitecture beschreibt die endliche Architekturkomposition mit expliziten Codec-, Invarianten- und Simulationsbedingungen. EvidenceRecovery ergänzt den Abgleich der benötigten Eingaben. StorageIntegrity beschreibt die begrenzten Integritäts- und Rechteeigenschaften des Speichermodells. Die drei Module behalten ihre eigenen Satzlisten; ihre Zahlen werden hier nicht zu einer angeblich unabhängigen Gesamtzahl addiert.

Für die reale Inbetriebnahme hat der Owner raumzeitterminal.de in der bereits spezifizierten Form als Abnahmekriterium festgelegt. Dazu gehört die vorhandene Kette aus Host-Identität, gebundenem Paket, zugelassener Ausführung und unabhängigem HTTPS-/Terminal-Readback. Der Nachweis dieser Funktionen wäre eine konkrete Wirksamkeitsbestätigung im erklärten Betriebsumfang. Er wäre kein pauschaler Beweis physikalischen Superdeterminismus oder einer unbegrenzten Anpassungsfähigkeit aller zukünftigen Systeme.

## 7. Reproduktion und Nachweisstand

Im bestehenden Lean-4.19.0-Projekt werden EvidenceRecovery und EvidenceRecoveryAxiomAudit ausdrücklich gebaut. Alle 16 neuen Sätze wurden lokal vom Kernel geprüft. Elf sind axiomfrei; fünf verwenden ausschließlich die Standardabhängigkeiten propext und Quot.sound. Drei negative Beispiele müssen wegen ihrer falschen Behauptung zurückgewiesen werden. Ein fehlender Import ist kein bestandener Negativtest. Der CI-Anschluss prüft dieselbe Satzliste und deren tatsächliche Axiomabhängigkeiten.

Der lokale Modellnachweis wird mit Quelle, Objektdatei, Toolchain, Befehlen und Diagnoseausgaben gebunden. Ein lokaler Kernelbeleg ist noch kein nativer CI-Lauf für die neue Revision. Repository-Integration, die konkrete Goldkelch-Rettung, veröffentlichte Zenodo-Dateien und die Produktdomain behalten getrennte Nachweise.

## Quellen und Versionsbindung

[1] Ingolf Lohmann: Von Softwarearchitektur zur Weltformel - Das Universum als Round Trip. Versions-DOI 10.5281/zenodo.21888130. https://zenodo.org/records/21888130. Einstieg in die vorhandene Modell-, Beweis- und Messarchitektur; keine automatische Begründung der neuen Rettungsinstanz.

[2] Ingolf Lohmann: QIK-VRT, quellengebundene Lean-4-Formalisierung, Alpha 3. Versions-DOI 10.5281/zenodo.21529081. https://zenodo.org/records/21529081. Quellengebundene Formalumgebungen mit ausdrücklich bedingten Aussagen.

[3] Ingolf Lohmann: Charta maschinenprüfbarer Wissenschaft. DOI 10.5281/zenodo.21515074. https://zenodo.org/records/21515074. Formale, empirische und dokumentarische Evidenzklassen bleiben getrennt.

Arbeitsnachweise dieser Revision, noch nicht als neue wissenschaftliche Zenodo-Quelle archiviert: formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck/EvidenceRecovery.lean; docs/proofs/evidence-recovery-2026-10-30/CLAIM_MATRIX.json und LOCAL_KERNEL_RECEIPT.json. Vorgänger: https://github.com/ingolf-lohmann/qik-vrt/commit/4b18b2c93fe628e4a5fcb3cf1f03dbba29e36df8. Dies sind Provenienzangaben eines Entwurfs, kein neuer DOI und keine Publikationsabschlussbehauptung.
