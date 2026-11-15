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
