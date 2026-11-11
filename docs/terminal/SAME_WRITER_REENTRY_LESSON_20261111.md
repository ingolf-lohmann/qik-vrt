# QIK-VRT TEMDD lesson: follow the admitted same writer, not an alternate controller

Status: normative repair guidance; not proof of successful CI, deployment, or EAP.
Authority: ingolf-lohmann/qik-vrt. Owner direction: 2026-11-11.

## Failure signature
When CI/integrity fails (e.g. PR #721 at 32c81da6ba33c534524fa626b065100ee18600ea: stale runtime/toolchains/CACHE_COVERAGE.json and manifest SHA mismatch), repeatedly reporting RED or seeking a new browser login does not repair the existing writer. Treat that detour as a controller-direction error.

## Correct same-writer continuation
1. Read the repository surface and identify the admitted, exclusive writer, its exact HEAD, successor, fencing/lease, and persistent queue entry. A context or workflow-status change is not evidence of writer completion.
2. Follow the existing writer and its successor to a terminal result. Distinguish action_required (execution admission), failure (executed RED), and pending/running (unfinished). Do not add a parallel controller, timer, new site, or browser-authentication dependency.
3. On executed RED, inspect the first causal log failure and reproduce TEMDD RED on the same exact source. For cache integrity, run the existing tool-cache render/verify before the repository manifest/SHA generators; do not hand-edit generated integrity files.
4. Use the smallest reversible fix in the existing PR/authorized writer; test positive, negative, crash/restart, and same-writer re-entry. Preserve exclusive writer fencing and dependency ordering. Record the error signature as a regression.
5. Accept the successor only after independent exact-HEAD/TREE, CI, artifact/SHA, review/governance, and EAP readbacks appropriate to the claimed effect. Failed/unverified attempts remain journaled and do not advance the accepted fixpoint.
6. If an admission or host gate is blocked, persist its cause and prerequisites, then service the next independent runnable queue entry fairly. Do not spin on the same blocked item.

## Acceptance tests for this lesson
- A failed CI plus an admitted existing writer does not trigger a new browser login, controller, or redundant retry.
- A same-writer successor is followed across status/context changes until terminal, with exact-HEAD readback.
- Stale cache coverage cannot be marked GREEN by editing a manifest or SHA without deterministic render/verify and tests.
- An action_required workflow remains an admission block, not a passing or failing test.
- No merge, host deployment, release, or EFFECT_ACK_DONE claim without independent evidence.

This document is an actionable failure-prevention rule, not a claim that the PR #721 repair has been executed.
