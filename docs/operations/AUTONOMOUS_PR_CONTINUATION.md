<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Autonomous PR continuation

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

## Independent promotion: executable software evidence

`tools/qikvrt_expected_head_promotion.py` reuses the native independent Code
Owner gate. A candidate author cannot supply its own independent approval.
The decision binds repository, pull request, exact head and tree, current base,
native enforcement rules, current-head review, workflow event, run/attempt,
and executed jobs/steps. A green name, predecessor run, synthetic bot status,
zero-job registration, or `action_required` cannot establish promotion.

The trusted-main workflow repeats the complete technical and semantic
observation before an effect (`D0=2 REOBSERVE`), retains the existing distinct
writer and expected-head REST merge precondition, and reads back the actual
merge response, PR and Main commit with their parent bindings. The second
observation must still satisfy independent review, gate execution and competing
writer predicates. A review revoked on the same head does not remain valid.

`PROMOTION_EFFECT_BOUND_REVALIDATION_PENDING` establishes only the observed
merge effect. It requires fresh validation of the promoted Main. A changed
merged tree is recorded explicitly; neither candidate tests nor a successful
merge become its validation. Observations and readback are retained as bounded
workflow artifacts. This does not manufacture `EFFECT_ACK_DONE`.

Run the software boundary experiment with:

```sh
python3 -B -m unittest -v tests.test_qikvrt_expected_head_promotion
```

The production decision core is exercised over all 1,024 combinations of ten
declared perturbations, with a valid positive control. Further controls cover
foreign repository/PR/head, run attempts, duplicate or skipped jobs, execution
steps, stale/revoked/self reviews, malformed observations and substituted
effect readback. The actual workflow observer is executed against simulated
API responses, and all embedded shell blocks are syntax checked.

These are bounded executable tests, not a proof-kernel theorem about every
possible workflow or platform principal. Raw API observations are trusted
input predicates to this decision core; the tests do not authenticate a natural
person or supply a missing live credential. Software changes and an independent
release decision remain distinct effects. A platform HTTP 403 by itself does
not prove a self-writing cause. Current Authority/Mirror access, native rules,
reviews, execution admission and fresh successor validation require their own
live evidence. Existing scientific and documentary artifacts retain their
declared evidence classes.
