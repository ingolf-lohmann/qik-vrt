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
