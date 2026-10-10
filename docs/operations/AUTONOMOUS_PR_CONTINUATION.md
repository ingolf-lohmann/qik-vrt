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

### Highest-priority gap and cause repair

Ingolf Lohmann authorized the following general CI rule on 2026-10-02:
"Lücken sind höchstprior zu schließen und die Ursache für das Entstehen jeglicher
Lücke ebenso!" Both obligations are `OWNER_HIGHEST` in the existing contract's
`gap_and_cause_priority`. Contract loading rejects omission, weaker priorities,
integer substitutes for booleans, or a claim that symptom resolution closes the
cause. The existing `ci-continuation` receipt carries the complete bound rule;
the existing error-analysis consumer carries separate open gap/cause flags.

The existing repair handler used to report `REPAIRED` after a zero-exit repair
command, even when the original operation still failed. The controlled real
subprocess counterexample reproduces this on source HEAD
`2a4d587ea799d57ae569a011551a61123850fb1b`. The source-bound cause is the absent
post-repair probe and unconditional success return. Historical development
motives are unestablished.

The handler now repeats the identical original probe before returning any
verified symptom result. A failed recheck blocks the candidate. A successful
recheck returns `SYMPTOM_VERIFIED_CAUSE_OPEN`, with command, exit-code and output
digest observations; it leaves `cause_closed=false` and `repair_complete=false`.
These observations prove only the scoped operation. They do not prove why the
original drift arose. Establish and repair that cause, automatically catch its
regression, and freshly read back the exact-subject effect before closing the
repair. The existing V25 Shift-Left policy supplies the regression obligation.
A subsequent NOOP cannot discharge a previously open cause.

The authorization covers diagnosis and repair. Existing allowlists, trusted-Main
pipeline invariance and independent native effect admission still govern writer
execution. The upgraded producer/consumer is a review candidate until Main
admission and an actual native run establish productive activation.

Ingolf Lohmann's command **Never stop CI** is bound to this repository in
`state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json.continuous_integration`.
The existing CI executes `tools/qikvrt_autonomous_self_heal.py ci-continuation`
after its terminal test disposition, including on failure. The controller reads
that command, checks its invariants and the actual committed contract/controller
bytes, and emits `CI_CONTINUATION.json` bound to the current HEAD/TREE and native
run/attempt. The existing audit upload retains this receipt after either result.
It does not turn a failed test into success or authorize a writer.

The existing PR worker also accepts completed CI and repository-evidence events,
without a success-only filter. An event selects only an opted-in same-repository
draft whose current head equals that completed run's head. Stale and unrelated
events are strict NOOPs. The existing scheduled fallback remains available.
Finite jobs and fail-closed writer gates remain; success, failure and scoped
release acceptance never discharge the overall integration obligation.

The CI consumer can be tested on the exact PR candidate. Activation of the
upgraded default-branch `workflow_run` worker requires independent native review
and Main admission. Its trusted-Main pipeline binding remains mandatory; opting
in a candidate does not allow it to execute an unreviewed pipeline upgrade.

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


## NOOP is not the system Definition of Done

The 2026-10-01 successor fixes a real early halt: an unchanged, opted-in
candidate used to exit before reaching the dedicated exact-head verifier.
The existing workflow now continues to verification even when its repository
mutation is NOOP. Ordinary green CI or evidence materialization does not replace
this verifier. An existing dedicated status consumes that submission slot:
pending, failure and success each require readback of the existing execution;
none causes blind redispatch or establishes product acceptance.

Before a verifier dispatch, the workflow reobserves current Main and the actual
candidate head. A failed/ambiguous dispatch after its pending status requires
reconciliation of that existing attempt, not another trigger. One repository-
dispatch is emitted when no dedicated status exists. Its subsequent execution,
artifact readback and native review remain distinct obligations.

## Invariant pipeline during feedback

The existing self-heal controller now exposes `pipeline-bind` and
`pipeline-verify`. They bind sorted path/mode/checkout-byte records for workflows,
tools, tests, runtime locks, policies, authorization/autonomy, all source code and
fixed entrypoints. A separately reobserved trusted Main SHA supplies the
reference. The workflow copies that trusted observer before checking out the
candidate and invokes it before candidate-controlled commands and after repair.
Reference bytes use Git's actual checkout conversion, including declared CRLF
PowerShell files; `.gitattributes` itself is protected. Runner Git configuration
and non-versioned attributes are part of the separately trusted environment.
Changing executable source or attributes still fails rather than silently
normalizing arbitrary candidate bytes. The first hosted candidate's failed
raw-blob comparison is preserved as predecessor evidence, never transferred.
New protected paths, deletions, byte changes, executable-mode changes and
symlinks fail closed. Generated integrity/projection outputs and ordinary data
are outside this control-plane inventory. The controller also verifies
invariance across each bounded local repair pass.

An intentional pipeline upgrade requires independent native review and Main
activation; a candidate cannot make its own new pipeline the trusted baseline.
This protects the declared source inventory. It is not a complete mediation
proof for arbitrary programs, a provider capability revocation, a physical
clock witness or a guarantee for every future environment.

Tests execute the actual workflow shell in a private Git/HTTP-command fixture,
observe exactly one dispatch on a clean NOOP, and observe zero duplicate
submissions when a dedicated status already exists or the combined status
inventory is incomplete. A separate source-invariance
experiment runs both data directions, absent/partial/full selection and up to
16 feedback generations. Altered Makefile bytes, executable modes, added test
paths, missing protected files and tampered bindings are negative controls.

The existing exact-head verifier additionally runs a read-only PR contract job
on pipeline candidates. That job has only contents-read permission and executes
the complete repository suite. It neither activates the new Main workflow nor
performs a repository-dispatch, native review, merge or productive Mesh effect.
The actual-shell, checkout and invariance regression tests are mandatory through
the existing `make test` entrypoint's `autonomous-continuation-test` prerequisite.
The dedicated contract job uses that same entrypoint rather than running those
tests twice or maintaining a parallel suite.
The scheduled continuation still executes the current Main version until its
independent integration succeeds. Its owner-requested opt-in is therefore held
pending activation of the invariant observer; placing a marker on a candidate
cannot repair an older trusted-Main workflow.

The 400-byte standpoint stays byte-identical. A seed carried in text or graphics
is data; it neither authenticates a receiving operator nor authorizes that
receiver's execution, registration or hierarchy. Admitted descendants preserve
the Goldkelch lineage under the existing explicit registration/capability
contract. Owner requirements for broader future propagation are attributed
requirements rather than an observed effect on unrelated systems.

## Repository ownership of execution and external dependencies

The general owner correction is bound in the existing self-healing contract's
`execution_routing` and the `/AI` entrypoint. Repository-native CI/CD and admitted
Mesh executors own repository tasks and durable continuation. External clients
may transport authorized requests, prepare reviewable changes, read back
effects and deliver personal read-only reports. An external ChatGPT schedule
or webhook is not the repository executor.

The native `ci-continuation` command rejects a weakened execution route or CQF
dependency policy. Its receipt binds the executed controller/verifier closure,
both policy digests and exact native run/attempt/HEAD/TREE. It does not infer
that every production dependency is already mirrored.

The all-external-dependency mirroring rule is implemented in the existing full
node recovery policy and verifier; see `docs/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION.md`.
Three reachable external execution tasks were paused without deleting their
prompts or schedules; an observer's incorrect external-executor reference was
corrected. The exact-bound work unit preserves the audit digests and visibility
limits. Those configuration effects do not prove productive replacement of
the Authority scopes or Main activation. Existing independent native review,
authority, rights and effect boundaries remain required.
