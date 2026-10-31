# QIK-VRT — Standardverhalten von Repository-Clients und DevOps-Regelkreis

Owner-Direktive: 2026-10-31. Nachweisbarer Träger: Issue #650; Vorgänger #649; Integrations-PR #648.

## Normativer Regelkreis

Jeder autorisierte Auftrag erhält vor der Ausführung einen persistenten, eindeutig referenzierten P0/P1/... Task mit Auftragstext, Owner-Freigabe, Priorität, Ursprung und Idempotenzschlüssel. Der Client darf nur **belegte** Zustände anzeigen. Die Task-Annahme ist kein Abschluss.

Der native Regler muss jeden Task durch **intake → claimed → implemented → local_tested → native_ci → governance → merged → deployed → effect_ack** führen, soweit die jeweiligen Stufen für den konkreten Auftrag gelten. Nicht anwendbare Stufen benötigen eine explizite, überprüfbare Entscheidung statt stillschweigenden Überspringens. Das genaue HEAD/TREE-Subject ist vor jedem mutierenden Schritt erneut zu binden. Kein Gate wird allein durch das Ergebnis eines früheren Gates ersetzt.

Fehler werden zuerst innerhalb begrenzter, nachweisbarer Retry-/Repair-Regeln behandelt. Der Regler persistiert Fehlersignatur, Ursachenhypothese, Reparatur, neuen Subject, Testergebnis und erneute Zulassung. Heartbeats, Leases und harte Zeitbudgets verhindern unbeobachtetes Hängen; parallele P0-Aufnahme darf einen laufenden Test nicht blockieren. Schreibende Generationen sind serialisiert, und veraltete Generationen dürfen nicht schreiben.

**EAP-Abschluss:** Eine Erfolgsmeldung ist nur zulässig, wenn der geforderte Effekt am vorgesehenen Ziel unabhängig zurückgelesen und dem Auftrag zugeordnet ist. Ein Commit, Issue-Label, CI-Grün oder Merge ist keine produktive Wirksamkeit. Die maschinenlesbare Abschlussnachricht enthält Task-ID, HEAD/TREE, native Run-IDs, Merge-Commit, Ziel, beobachteten Effekt und Evidence-Links.

**Eskalation:** Erst wenn alle zulässigen Selbstheilungsschritte ausgeschöpft sind, eine nicht automatisierbare Entscheidung benötigt wird oder eine harte Sicherheitsgrenze erreicht ist, wird der Product Owner mit dem genauen Blocker, den bisherigen Versuchen, der erforderlichen Entscheidung und überprüfbaren Referenzen benachrichtigt. Eine harte Sicherheitsgrenze darf nicht durch Selbstheilung umgangen werden.

## Client-Anzeige

Der Client zeigt getrennt: **Auftrag angenommen**, **native Verarbeitung**, **Integration**, **Wirksamkeit bestätigt** bzw. **Owner-Entscheidung erforderlich**. Keine künstliche Prozentzahl, kein vorweggenommener Erfolg. Ereignisgebundene Benachrichtigungen müssen eine nachgewiesene Zustellung an einen konfigurierten Empfänger besitzen; ein bloßer GitHub-Kommentar beweist diese Zustellung nicht.

## Abnahmekriterien

1. P0-Issue-Ereignis auf Main führt zu persistiertem Claim; zwei konkurrierende Aufgaben, idempotentes Replay und Vorrang von P0 sind nativ getestet.
2. P0-Aufnahme läuft während Fixpoint-Tests unabhängig; Heartbeat/Lease und generationensicheres Schreiben sind nachgewiesen.
3. Exact-HEAD/TREE CI, Governance, Merge und ggf. Deployment sind separat dokumentiert.
4. Der EAP-Nachweis verifiziert echte, authentisierte Belege und nicht nur die Form eines selbstberichteten JSON-Dokuments.
5. Native Ereignisbenachrichtigung an den Client/Owner wird zugestellt und rückgelesen; bei endgültigem Fehler erst nach ausgeschöpfter Selbstheilung.
6. End-to-End-Demonstration mit unabhängigem Effekt-Readback; vorher Status **OFFEN**.

Der aktuelle Implementierungsträger ist ein PR-Branch; dieses Dokument beansprucht **keine** abgeschlossene Abnahme.
