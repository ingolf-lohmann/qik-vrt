# COMMIT execution and evidence contract (PR #749 / Issue #748)

Status: normative repair requirement; **not** proof of implemented automation, CI success, merge or productive effect.

## Failure being repaired
A Principal's explicit `COMMIT` instruction was acknowledged in chat as authorization, but no repository write was attempted. Subsequent read-only inspection was misleadingly reported as continuation. Chat-only conclusions are not durable execution evidence.

## Required invariant
`COMMIT` means: perform the authorized, specified, admissible repository transition, then independently read back its effect. Authorization alone is never execution.

For every COMMIT request:
1. Resolve the authority repository, target branch, exact HEAD and authorized change; check existing implementation before writing.
2. If the change is not sufficiently specified or admission fails, record the precise missing precondition and repair path; do not claim a commit.
3. If admissible, attempt the real write, preserving optimistic HEAD/lease/fencing checks and a single writer.
4. Record returned commit SHA; independently verify branch HEAD, changed content and provenance.
5. Run/check exact-HEAD CI, integrity and review gates; do not infer CI success from dispatch or commit.
6. Advance EMP/EAP only with the authorized execution and independent effect acknowledgment; otherwise `CONTINUATION_REQUIRED` with concrete next action.
7. Preserve evidence in the authority repository (not solely in a chat or UI); each report distinguishes confirmed, open, unknown and merely asserted.

## Acceptance regression
Given a valid COMMIT instruction, the system must not return only a verbal authorization confirmation. It must either produce a verified commit readback or an evidenced, specific non-execution result. A read-only fetch cannot satisfy a write request. Never report `EFFECT_ACK_DONE` without independent EAP evidence.

This document records the requirement only. Wiring into the existing synchronous DevOps loop, executable regression tests, CI and production acceptance remain separate, verifiable work.


## Mandatory architectural enforcement (not a conversational convention)
Every authorized actionable instruction must be durably admitted to the existing authority-repository workflow before it can be acknowledged as accepted for execution. Chat memory, UI state, and assistant prose are never authoritative storage.

The existing single-writer DevOps loop MUST implement a durable state machine:
`RECEIVED -> PERSISTED -> ADMITTED -> EXECUTING -> EFFECT_VERIFIED`, with explicit `BLOCKED` / `REPAIR_REQUIRED` branches and an append-only evidence trail. Transitions must be idempotent under replay, correlated by stable intent ID, fenced against stale writers, and bound to exact HEAD and Principal authorization. A blocked request must remain discoverable and actionable across session loss; no silent dropping, no invented completion, and no parallel scheduler.

A success response MUST be mechanically gated on the persisted EAP receipt. An acknowledgement of intent, a commit SHA, a CI dispatch, or a Sites write alone MUST NOT mark completion. The absence of an admissible write must produce a durable failure/repair record where technically possible; if persistence itself is unavailable, report this explicitly and do not claim acceptance.

## Required executable negative regressions
- Authorized COMMIT with read-only processing: reject success; preserve outstanding intent.
- Session interruption after admission: restart/replay finds the same intent without duplicate effects.
- GitHub 403, zero-job/action_required CI, or unavailable writer: keep repair required, never DONE.
- HEAD drift or stale writer lease: reject stale execution and re-admit against current evidence.
- Commit without independent EAP receipt: remain pending, never DONE.
- Persistence unavailable: no accepted/complete acknowledgement.
- Repeated COMMIT with same intent ID: idempotent result, not duplicate commit.

Acceptance requires production-path wiring, exact-HEAD CI passing these tests, and independent runtime EAP readback. This text alone does not implement the enforcement.

## Non-terminating read-only acceptance observation (continuation contract)

An observer run is a **bounded readback**, not completion of the overarching acceptance assignment. The end of a chat turn is not termination of that assignment. The observer MUST persist or recover the last independently evidenced exact HEAD, run IDs, gate outcomes, and unresolved repair obligations through the existing authority-repository evidence mechanism. It MUST NOT interpret the end of a chat turn, successful isolated regression workflow, or an unchanged HEAD as termination.

For every subsequent readback, compare the latest PR HEAD and main HEAD against the prior evidenced baseline; enumerate the COMMIT gate implementation, regression execution, full exact-HEAD CI, production writer integration, reviews, merge/main promotion, original-host runtime and independent EMP/EAP effect receipt. Classify each criterion as CONFIRMED, OPEN, UNKNOWN or ASSERTED_ONLY. Progress bars MUST represent named, independently verifiable acceptance predicates with a stable denominator, not elapsed time, number of commits, or speculative percentages.

**Termination predicate:** the observation may report COMPLETE only if all required predicates are independently CONFIRMED for the relevant exact integrated HEAD, including successful full CI, admitted writer integration, authorized merge/main integration, and independently read-back productive EAP acknowledgment. Any failed, missing, stale, skipped, or unknown gate keeps `CONTINUATION_REQUIRED` and the outstanding repair path visible. An isolated successful COMMIT regression is progress, never final acceptance.

The observer is read-only and must not itself dispatch CI, merge, deploy, create a parallel controller, or claim a continuous execution capability it does not have. Scheduling and continuation must use an already authorized observation mechanism; its availability and last run must be checked rather than presumed. If the mechanism is unavailable, report the interruption as a monitoring defect, not as successful completion. This clause does not itself install or verify a scheduler.

## No-delta reporting and autonomous repair handoff

A readback with no material change in exact HEAD, CI outcome, review/merge status, writer integration, runtime acceptance or EAP receipt is a **NO_DELTA observation**, not a new user decision point. Preserve the evidence and unresolved repair obligation in the existing continuation mechanism, but do not repeatedly request Principal confirmation or send the same blocker as a fresh alert. This suppression concerns notifications only; it MUST NOT suppress subsequent authorized checks or hide a stalled repair.

On a changed failure, new blocker, demonstrated progress, required Principal-only decision, or independently verified completion, publish the precise delta and its source. Otherwise advance the already-authorized, existing DevOps repair path where admissible; if execution is technically unavailable, retain `CONTINUATION_REQUIRED` with the specific blocked action and do not claim autonomous progress.

The next cycle MUST re-read the latest exact HEAD before comparing results, treat superseded runs as historical, and use the current exact-HEAD test result for acceptance. A failed newly added regression is actionable diagnostic evidence, never a PASS and never permission to bypass the gate. Full autonomy remains a measured acceptance target, not a status inferred from repeated COMMITs or unchanged reports.

This is a reporting and continuation **contract**. It does not by itself prove scheduler operation, production writer wiring, or independently acknowledged effect.
