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

## Exact-HEAD gate evidence: PR #721, 2026-11-11

Subject: `ccfea5781ce3572fbb1fec2b01fab1ac6ae84a2e` (PR #721, Draft). This is an observation, not an accepted fixpoint.

| Gate | Native evidence | Result | Required transition |
| --- | --- | --- | --- |
| CI | https://github.com/ingolf-lohmann/qik-vrt/actions/runs/42937554554 | FAILURE: `test_native_api_retry_requires_later_exact_native_rest_success`, `SPECIFICATION_HISTORICAL_SOURCE_REPAIR_SCOPE_REQUIRED`; same-writer fixpoint step failed | TEMDD RED reproduction and minimal contract/fixture repair, then complete GREEN on new exact HEAD |
| Collective governance | https://github.com/ingolf-lohmann/qik-vrt/actions/runs/42937553597 | FAILURE: `BLOCK repository manifest differs from deterministic regeneration` | Cache render/verify, manifest generator/verify, full tests; rerun exact-head collective review |
| PR reviews | https://github.com/ingolf-lohmann/qik-vrt/pull/721 | No submitted independent PR reviews (readback `reviews=[]`); review observer and executor SUCCESS are not approvals | Independent authorized reviewer submits an actual review of the accepted exact HEAD |
| EAP HTTP terminal | https://github.com/ingolf-lohmann/qik-vrt/actions/runs/42937553714 | FAILURE | Native/host admission and independent effect readback, no inferred ACK |
| Watchdog | https://github.com/ingolf-lohmann/qik-vrt/actions/runs/42937553754 | SUCCESS | Preserve same-writer fencing and follow successor; does not waive gates |

### Deduplicated causal queue (ordered by dependency, not status repetition)

- P0 INTEGRITY-721: repository manifest drift; dependent on deterministic cache coverage regeneration; acceptance: generated outputs verify and complete tests pass on the exact successor. Blocked until admitted writer can execute; never hand-edit generated hashes.
- P1 CI-SPEC-721: native API retry fixture/contract failure; reproduce failing test and distinguish invalid fixture from valid fail-closed policy; acceptance: negative security cases still reject and the full suite passes.
- P1 REVIEW-721: independent review absent; dependent on a stable tested exact HEAD; acceptance: submitted review by an eligible independent reviewer, not merely successful observer/executor.
- P1 GOVERNANCE-721: collective review blocked by manifest; dependent on integrity GREEN; acceptance: collective-review workflow SUCCESS on accepted exact HEAD.
- P2 EAP-721: terminal HTTP FAILED; dependent on admitted native/host runtime and release gates; acceptance: independently verified EFFECT_ACK, never inferred from workflow dispatch.

After every admitted mutation or gate change, independently re-read the PR HEAD, tree, workflows, reviews, and next queue dependency. Do not merge a Draft PR or claim DoD while any required gate is RED, unknown, or unverified.
