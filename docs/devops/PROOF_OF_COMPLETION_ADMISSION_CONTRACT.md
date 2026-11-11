# QIK-VRT DevOps: proof-of-completion admission contract

Status: **normative candidate, not yet admitted on main**. Principal authorization: 2026-11-11. Authority: `ingolf-lohmann/qik-vrt`.

## Fundamental invariant

Analysis, diagnosis, plan, workspace task, commit, PR, CI start, or self-reported completion **MUST NOT** transition a task to DONE.

The only permitted terminal transition is an independently verified admission receipt bound to the exact subject and current HEAD/TREE. A task with any unsatisfied criterion remains OPEN or HOLD, with the smallest authorized, reversible, causally justified next step explicitly recorded.

```
OBSERVED -> DIAGNOSED -> REPAIRED -> TESTED_EXACT_HEAD
  -> INDEPENDENT_READBACK -> ADMITTED
```

A failed transition MUST retain its original causal error, produce a machine-readable fail-closed receipt, and MUST NOT silently convert HOLD into NOOP or DONE. On CI/CD failure TEMDD is mandatory: failing evidence (RED), root cause, minimal reversible correction, regression (GREEN), exact-HEAD integrity and independent readback.

## Acceptance predicate

`admitted := exact_subject && exact_head && exact_tree && tests_pass && integrity_pass && governance_pass && independent_review_pass && independent_effect_readback_pass && all_required_dod_gates_pass`

Unknown, missing, stale, ambiguous, or only asserted inputs evaluate to **false**. No provider action, deployment, effect acknowledgement, or reviewer approval may be inferred from a workspace entry, a tool response lacking proof, or this document.

## Non-bypassable responsibilities

- The owner sets authorization and scope; execution is restricted to the authorized reversible repository paths until separately admitted.
- A writer must bind every claimed effect to its independently reobserved receipt; the observer must distinguish observed, unknown, open, and asserted states.
- Every incomplete task remains routable to the next concrete step; if a step is blocked, preserve the failure and continue independent read-only diagnostics where feasible.
- A new commit invalidates earlier exact-HEAD CI/review evidence unless explicitly proven reusable under the repository's governance contract.
- This contract itself requires implementation binding, executable negative tests, code-owner review, and exact-HEAD CI before it can be considered enforced across the network.

## Current tracked obligations

- PR #743: continuation bootstrap rate-limit failure receipt, manifest regeneration and negative tests; HOLD until CI and review pass.
- PR #742: isolated positive-real conformal volume law Mathlib formalization; distinguish arithmetic lemma, continuum mathematical proof, stochastic Poisson convergence, and physical validation. Do not conflate these proof levels.
