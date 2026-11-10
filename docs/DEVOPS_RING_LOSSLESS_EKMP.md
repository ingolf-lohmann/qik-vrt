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
