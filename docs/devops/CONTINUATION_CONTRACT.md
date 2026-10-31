# QIK-VRT: verbindlicher Fortsetzungsvertrag (PR #655)

Dieser Vertrag ist der stabile Arbeitskontext über ChatGPT-Eingabe-/Ausgabe-Zyklen hinweg. Das Repository ist Authority; Chat-Antworten sind keine Authority. Der Vertrag ist eine Spezifikation, **kein Nachweis seiner vollständigen Implementierung**.

## Ziel und unveränderliche Definition of Done

1. Ein eigenständiger HTML5/React-Client und der ChatGPT-Client verwenden denselben versionierten Terminal-Vertrag; die Darstellung darf keine fremden oder veralteten PR-IDs als aktuellen Zustand ausgeben.
2. Authentifizierte Aufträge passieren den originalen, zugelassenen Universalterminal-/Transputer-Adapter; bei fehlender Zulassung gilt fail-closed.
3. Auftrag -> persistiertes Ereignis -> Repository-native Ausführung -> PR -> exakte native CI -> Governance -> Main -> Host-/Domain-Readback -> EFFECT_ACK sind getrennt belegte Kausalstufen.
4. Die exakte Zieldomäne raumzeitterminal.de liefert die spezifizierte Oberfläche und einen überprüfbaren produktiven Effekt. Ohne Domain-, Host- und Effekt-Readback keine Abnahme.
5. CI-Artefakte, Logabrufdefekte, Integritätsregeneration, Lean-Kernel-Nachweise und Veröffentlichung werden mit exaktem HEAD/TREE und eigenständigen Belegen geführt.
6. Alle schreibenden Fortsetzungen sind repository-native, ereignisgetrieben und ohne externe/interne Timer. Stündliche ChatGPT-Aufgaben sind ausschließlich lesend.

## Deterministische Fortsetzung jedes Chat-Zyklus

1. **READ**: Authority Main, PR #655, exakten HEAD/TREE, Workflow-Runs und Jobs sowie native Terminal-Admission rücklesen. Veraltete gespeicherte SHAs nie als aktuell ausgeben.
2. **DIFF**: Ist-Zustand gegen die sechs DoD-Gates und zuletzt persistierte Belege vergleichen; zuerst den frühesten kausalen Blocker bestimmen.
3. **ACT**: Einen nachgewiesenen, sicher ausführbaren Repository-Fix ausführen; keine Secrets auslesen, keine unzugelassene Produktionswirkung behaupten.
4. **VERIFY**: Den neuen Commit und dessen exakte CI prüfen. Bot-Commits mit `action_required` nicht als Testnachweis werten. Log-404 von Testfehler trennen.
5. **PERSIST**: Diagnose, Änderungsreferenz, Prüfergebnis und nächsten kausalen Schritt im Repository nachführen; unverifizierte Gates explizit offen lassen.
6. **REPORT**: Im Chat nur nachweisbare Änderungen und den laufenden Stand anzeigen. Zwischenbericht ≠ Abschluss; niemals `DONE` ohne sämtliche Gates.

## Zustandsmodell

`UNVERIFIED -> OBSERVED -> RUNNING -> PASSED | FAILED | BLOCKED`.

Ein Gate ist nur `PASSED`, wenn sein eigener unveränderlicher Nachweis vorliegt. Die Gesamtzustandsfunktion ist `DONE` genau dann, wenn **alle** sechs DoD-Gates durch Readbacks erfüllt sind; andernfalls `IN_PROGRESS` oder `BLOCKED`. Keine Schlussfolgerung von CI-Erfolg auf produktiven Effekt.

## Aktuelle bekannte Risiken (nicht als Live-Status verwenden)

- PR #655 ist Draft; ein vollständig zugelassener Original-Terminal-Adapter und produktiver Effekt sind nicht belegt.
- Die Integritätsregeneration erzeugt Bot-Commits, deren Folge-Workflows `action_required` erhalten können. Erneutes Triggern ist eine Zwischenmaßnahme, keine endgültige Lösung.
- Die vorhandene HTML-Datei ist bislang Vanilla-JavaScript, nicht die geforderte eigenständige React-Implementierung.
- Die Bridge liefert derzeit `503 ORIGINAL_TERMINAL_TRANSPUTER_ADAPTER_NOT_ADMITTED` für Mutationen. Das ist korrektes Fail-Closed-Verhalten, aber keine fertige Auftragseinreichung.

**Autoritative Aktualität:** Live-Zustand immer aus GitHub-/Native-Readbacks, niemals aus dieser Momentaufnahme ableiten.
