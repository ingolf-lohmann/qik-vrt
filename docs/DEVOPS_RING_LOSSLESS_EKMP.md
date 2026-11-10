# QIK-VRT DevOps ring — lossless EKMP continuation contract

Status: candidate, not admitted to main. Authority: ingolf-lohmann/qik-vrt.

## Principle
The ring is a succession of bounded executions, not a never-ending GitHub Actions job.
A clock wakes the trusted-main observer. The observer collects open work and exact
HEAD/TREE, workflows, jobs, and receipts. The existing bounded continuation consumer
may act only on independently admitted work. Failure of one dependency MUST NOT
erase unrelated runnable work. An empty queue yields an IDLE observation and the
next clock wakeup, never an invented optimization commit.

## Lossless projection
Each original event retains repository, source HEAD/TREE (when observed), workflow
run ID and attempt, job and step identity, timestamp, original URL, raw evidence
artifact identifier and SHA-256 when available. A consolidated view is a derived
index, never a replacement for the originals. Distinct events MUST NOT be
coalesced merely because their descriptions, state or timestamps match. Missing
identities remain UNKNOWN. No source is silently dropped to meet an API budget;
the readback must instead report INCOMPLETE/HOLD.

The effective-knowledge projection distinguishes:
REQUESTED, STARTED, RUNNING, FAILED, HOLD, IDLE, PASSED, VERIFIED.
PASSED describes a specific executed test, not production admission. VERIFIED
requires independent readback of the claimed target effect. No derived
projection can set EFFECT_ACK_DONE, release admission, reviewer approval or
original-host readiness.

## Continuation and scaling
Work is keyed by immutable source identity plus causal dependency, not by
display name. A lease allows at most one authorized repository writer.
Independent read-only observations may scale without writer privilege.
A failed work item produces a bounded TEMDD diagnostic handoff with original
failure evidence; it does not globally freeze other independently admitted work.
Retries require a changed input, transient-recovery evidence or an explicit
bounded backoff; repeated identical attempts do not renew useful-progress time.

## Acceptance
1. Scheduled wakeup observed on main, followed by independently identified
   trusted-main watchdog run and its original artifact receipt.
2. Open-work and no-work scenarios preserve all input identities; IDLE still
   has an observation receipt and a subsequent wakeup.
3. A failed job produces a causal TEMDD handoff, while unrelated eligible work
   can progress. Restart and replay do not duplicate effects.
4. Integrity manifest/SHA, exact-successor CI and independent governance review
   pass before main admission.
5. Original-host, native EAP and global DoD remain separately fail-closed.

This document records a contract, not proof of operational liveness.


## Synchroner Readback-Kreis nach jedem Auftrag (Owner-Vorgabe 2026-11-10)

Nach jedem an die Authority übergebenen Arbeitsauftrag kehrt der ausführende
Controller **lesend** in den DevOps-Kreis zurück. Er liest den aktuellen
Authority-HEAD/TREE, die **gesamte** beobachtbare Aktivität (auch fremde,
nicht auftragsbezogene PRs, Workflows, Reviews und Änderungen), sowie
zugehörige Log- und Artefaktreferenzen. Alle Beobachtungen erhalten
Zeitstempel, Quellenbindung und eine verkettete Ereignisidentität. Der
Auftrag wird erst dann einem beobachteten Ergebnis zugeordnet, wenn
Auftrags-ID und Exact-HEAD/Run-/Artefaktreferenzen nachweisbar übereinstimmen.

Bei nicht sichtbarem Auftrag ist das Ergebnis `PENDING_READBACK`, niemals
`DONE`. Fremde Aktivitäten bleiben als Kontext und mögliche kausale
Abhängigkeiten im Journal. Ein weiterer synchroner Lesedurchlauf darf
nur bei vorhandenem Ausführungsbudget stattfinden; bei Erschöpfung
wird `OPEN` mit dem letzten belegten Cursor persistiert, statt eine
Endlosschleife oder Erfolg zu behaupten. Die Fortsetzung übernimmt der
bereits zugelassene DevOps-Kreis. Die Readback-Schleife ist read-only;
Writer-Fencing, Admission, Governance und EAP bleiben unabhängig.


## Allgemeiner IaC-Korrekturvertrag (Owner-Freigabe 2026-11-10)

Diese Regel gilt für **jeden** zukünftigen Fehler, Bugfix, jede Änderung und
jede neue Repository-Funktion, nicht nur für Issue #718:

1. **Kausalität statt Symptombehandlung:** Den fehlschlagenden Originalschritt,
   seinen Exact-HEAD/TREE, die ursprünglichen Logs und die verletzte
   Invariante ermitteln. Bei CI/CD-Fehlern TEMDD anwenden.
2. **Authority und bestehender Ausführungspfad:** Die Korrektur ausschließlich
   im Authority-Repository `ingolf-lohmann/qik-vrt` am tatsächlich
   ausführenden IaC-/Quellcode-Pfad vornehmen. Vorhandene Writer, Gatekeeper,
   Validatoren und Fortsetzungsmechanismen wiederverwenden. Keine
   zusätzlichen parallelen Steuerungen oder Timer als Ersatz für die Ursache.
3. **Deterministische Rekonstruktion:** Der nächste zugelassene Lauf muss
   aus den versionierten Quellen, festgelegten Eingaben und vorhandenen
   Generatoren selbst die korrekten Artefakte erzeugen können. Abgeleitete
   Manifest-/SHA-Dateien niemals manuell als angeblichen Beweis umschreiben.
4. **Ein Writer, kausale Fortsetzung:** Bei jeder Mutation den aktuellen
   Remote-HEAD/TREE und die Writer-Zulassung prüfen; konkurrierende Writes
   fail-closed ablehnen. Nach dem kleinsten zulässigen Eingriff sofort die
   vollständigen Tests, die kanonische Integritätsprüfung und den
   unabhängigen Exact-Successor-Readback ausführen. Kein Erfolgstransfer von
   einem alten HEAD.
5. **Negativtests und Abnahme:** Die ursprüngliche Fehlerklasse durch einen
   Regressionstest sowie negative/boundary cases abdecken. Governance,
   unabhängige Reviews, Originalhost und EFFECT_ACK_DONE bleiben getrennte
   Gates. Fehlende Evidenz bleibt UNKNOWN/BLOCK, niemals PASS.
6. **Synchronous continuation:** Nach jeder Beobachtung den nächsten
   unmittelbar ausführbaren kausalen Schritt auslösen, unabhängig blockierte
   Arbeit weiterführen und nur an einer realen externen Ausführungsgrenze
   stoppen. Ein Statusbericht oder Arbeitsauftrag allein ist keine
   Implementierung und kein Abschluss.

**Akzeptanzprädikat:** Eine Änderung ist erst wirksam abgeschlossen, wenn
der neu erzeugte Exact-HEAD die spezifizierte Invariante durch native Tests
besteht, die daraus hervorgegangenen Artefakte reproduzierbar sind und die
beanspruchte Wirkung unabhängig zurückgelesen wurde. Ein erfolgreicher
Teiltest ist keine Freigabe der sieben produktiven DoD-Gates.

Diese Regel ist ein verbindlicher Repository-Vertrag; ihre Existenz allein
beweist weder die Implementierung in allen Workflows noch eine produktive
Wirkung.
