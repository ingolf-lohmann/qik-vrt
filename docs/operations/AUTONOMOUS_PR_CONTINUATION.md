<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Autonomous PR continuation

## Mesh-wide target and current implementation boundary

The owner's target applies to every Mesh repository, not only Goldkelch:
process inputs using persisted cognition and ethics without external artificial
cognition or repeated owner intervention; return to zero open issues and pull
requests after actually delivering the requested effects. Returning to rest
does not reset history or erase unresolved work. Stable workflow rules must
process supported work units without rewriting themselves for each input.

This is a target, not an assertion that the current implementation meets it.
The first role-local repair on `ingolf-lohmann/qik-vrt`, based on
`25c4df4caf063d0545621f9958941c3cd0dfd5fa`, removes proposal-to-effect promotion
and replaces the cross-repository auto-finish effect runner with a read-only,
fully paginated local queue observer. Empty-at-observation is not completion;
pagination is not an atomic snapshot. Historical DONE bundles are not current
authorization. Tests, reviews, rules and effect receipts must be freshly bound
to the executing repository, exact base, head, tree and work unit.

Still required: validated allowlisted deterministic issue handlers beyond the
initial fail-closed compiler; event-bound resumption instead of unchanged
backlog retries; exact-subject native review and effect verification; and actual
resolution of the remaining local issues and PRs. The proposal workflow no
longer calls an external model, but unsupported work units remain `BLOCK`. This
repair must not be advertised as autonomous backlog completion. No predecessor or other
repository's validation is imported as proof for this candidate.

The code-owner gate must emit its own `QIKVRT required code-owner review`
context, not overwrite `QIKVRT requested review execution`. Native code-owner
approval remains independently required; correcting the status label cannot
manufacture it. Platform protection and activation on trusted main are separate
effects from local candidate tests.

## Purpose

The repository may independently continue deterministic, repository-internal
repairs on an explicitly opted-in same-repository draft pull request. The
continuation is bounded by the active owner delegation and never substitutes
an external scientific review or a separately authorized publication effect.

## Opt-in

A draft pull request is eligible only when its body contains the exact marker:

```text
<!-- qikvrt-autonomous-self-heal:enabled -->
```

The scheduled worker processes at most one eligible pull request per run. The
head repository must equal the executing repository, the head must still equal
the immediately reobserved SHA, and history rewriting is forbidden.

## Deterministic sequence

```text
REOBSERVE_MAIN_AND_PR_HEAD
→ MERGE_CURRENT_MAIN_HISTORY_PRESERVING
→ RUN_ALLOWLISTED_SELF_HEAL_HANDLERS
→ VERIFY_PUBLICATION_OVERVIEW
→ VERIFY_REPOSITORY_NATIVE_INTEGRITY
→ RUN_CONTROLLER_TESTS
→ RUN_FULL_REPOSITORY_SUITE
→ PUSH_FAST_FORWARD_SUCCESSOR
→ REPOSITORY_DISPATCH_EXACT_HEAD_REVERIFICATION
→ PERSIST_COMMIT_STATUS_AND_PR_COMMENT
```

The first added repair class is `PUBLICATION_OVERVIEW_DRIFT`. It detects a
local `docs/publications/*/README.md` that is absent from either
`docs/publications/index.json` or `docs/publications/index.html`, adds only the
missing index entries, and then lets repository-native integrity regeneration
bind the changed bytes.

## Trigger semantics

A push performed with the workflow-provided `GITHUB_TOKEN` does not recursively
start ordinary push or pull-request workflows. The worker therefore emits the
explicit repository-dispatch event
`qikvrt_autonomous_exact_head_verify`. The receiving workflow checks out the
exact candidate SHA, runs the full repository suite, re-executes the QCE finite
formal package when present, and writes a distinct status to the candidate
commit.

This mechanism does not impersonate pre-existing workflow contexts and does
not alter branch protection.

## External boundaries

The following gates cannot be manufactured by repository automation:

- an identified independent Human Physics Review when the candidate requires
  one;
- a natural-person decision authorizing a concrete Zenodo payload;
- credentials and authorization for a cross-repository Mirror mutation.

The worker stops before these gates. A future cross-repository continuation may
use a separately configured GitHub App installation credential with access to
both repositories, but no such credential value is stored in the repository
and no Mirror or Zenodo effect is authorized by this contract.

## Prohibited effects

- force push or history rewrite;
- direct mutation of `main` by the proposal worker;
- unconditional automatic merge;
- branch-protection change;
- release or tag creation;
- deployment;
- Zenodo or IETF mutation;
- repository-wide `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` claims.
