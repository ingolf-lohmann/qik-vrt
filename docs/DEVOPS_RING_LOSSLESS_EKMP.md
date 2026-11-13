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

## Stall repair bound to 13 November 2026

Observed Main is `014bbb095a20680c4851e62575ee932d7a45b206`, tree
`d867b5b5df4f76be4daa0c575e0d5bde9e03aeaf`. Watchdog run `43215795672`
stopped at JOBS_BUDGET_PREFLIGHT: 2,500 reported exact-head runs versus 1,000
returned. GitHub caps a filtered run search at 1,000 results. Increasing page
numbers alone cannot restore completeness. The existing collector now partitions
larger inventories into disjoint UTC creation intervals, verifies every identity
and partition count, rechecks the root page, and holds on drift, duplicates,
unpartitionable single-second overflow or its total 64-request budget. The
existing 20-request job budget remains unchanged.

Wakeup run `43382241445` returned success after finding seven queued watchdogs.
Fresh repository readback places those queued watchdogs in September/October,
on older heads. A queued record is not current useful progress. The existing
wakeup now requires a fresh exact-head record within the original queue/progress
lease. Stale, foreign-head, future or unreadable activity yields HOLD and no
dispatch. It neither cancels the original run nor grants another writer. Its
clock and a green wakeup remain observation only, never autonomous completion.

The ring planner preserves `action_required` and `startup_failure` as explicit
admission-repair tasks. They cannot turn into an empty IDLE queue. Status
deduplication suppresses redundant notifications, not diagnosis of an unresolved
failure. An unknown cause requires its original log/checkpoint; after a verified
repair, immediately reassess the original work and continue admitted successors.

Continuation run `43215795637` has a separate unresolved immutable-tree write
for PR #459. Its original checkpoint and ambiguous-effect readback duty remain
open; this repair must not repeat that POST, reset its intent or mint a writer.
PR #743/#747 workflow approval, complete successor CI, canonical integrity
regeneration, protected host/SSO admission, TLS and independent EAP acceptance
remain separate gates. Source saving and fixture tests establish neither Main
integration nor unattended execution. The Principal's authorization persists;
do not request it again or replace a missing operation with another scheduler.

