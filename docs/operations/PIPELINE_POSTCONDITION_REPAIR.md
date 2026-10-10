<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Pipeline postconditions and early fault detection

## Scope and evidence boundary

This maintenance candidate extends PR #455. Its construction base is exact
HEAD `299ac2bdbc165d4b3833c8434c0b2b83065c7f8b`, TREE
`b42fe71c0216387149972d0a6d3235945c78fd7f`. A prior conversational/reporting
TREE `7305885c...` is not a binding of that commit. The source of truth is the
Git commit object, not a comment, a run title, or a transport receipt.

The 4 October 2026 audit reproduced five pipeline defects. These changes reuse
and modify the existing three workflows. `qikvrt_pipeline_contracts.py` is an
extracted, testable implementation of their phase checks, not a second repair
controller. No repair allowlist, reviewer authority, administration credential,
merge permission, or external publication authorization is expanded.

Implementation and local regression results are candidate-scoped. Production
activation requires reviewed integration. Runtime success, current native CI,
review, main integration and EFFECT_ACK_DONE require their own fresh evidence.

## A. Resume transactions, not just byte changes

The existing PR continuation no longer exits before verification dispatch when
its merge/repair produces no new bytes. It rebinds PR eligibility, current main,
branch HEAD and TREE, and independently observes the native exact-subject run.
Status publication is no longer a prerequisite of dispatch. A missing run gets
at most one POST in the invocation and then another GET. An HTTP 204 or lost
response never counts as execution. A later opportunity reobserves before
resuming. Active runs are not duplicated; terminal failures are not rerun.

`repository_dispatch` event HEAD is main, not the payload PR HEAD. Native runs
are selected by verifier workflow path and a run title containing PR number,
HEAD and base. Job and exact-commit status observations remain distinct. An
unadmitted/zero-job run, missing status, duplicate run, or unbound legacy status
is a causal HOLD, not IDLE. A run title alone is not proof of test success.

Readback is not an atomic distributed transaction with GitHub. The design
bounds attempts and serializes the existing continuation workflow; it does not
claim exactly-once execution against arbitrary external concurrent writers or
unbounded API visibility delays. Missing/uncertain observations fail closed.

## B. Eligibility and fair work selection

The 5 October 2026 continuation correction connects the existing self-heal PR
materializer to this worker. New exact, allowlisted repair drafts carry both
the existing promotion marker and the existing continuation marker. A legacy
exact-bound repair draft with only the promotion marker receives at most one
body-only update per invocation, preserving its observed text. Fresh metadata
drift blocks that update; failed or ambiguous writes require independent PR,
branch, commit and base readback before continuation is considered connected.
The GitHub metadata write is not an atomic compare-and-swap transaction.

The active `OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2` delegation already
covers this bounded internal handoff. Repeated ChatGPT authorization and a
ChatGPT scheduler are not prerequisites. Unchanged connected candidates are
read-only; ready, foreign or incorrectly bound PRs receive no continuation
opt-in. Independent native review, enforced governance, terminal exact-head
gates and separately authorized external effects remain distinct conditions.

Only open, opted-in, same-repository draft PRs targeting main are selectable.
The executor rechecks the same conditions. Selection rotates by native workflow
run number through the sorted eligible inventory. For N stable candidates, N
consecutive executed opportunities serve each once, even if one candidate is
unchanged or blocked. This is a bounded fairness guarantee for a stable
inventory, not a proof of fairness under arbitrary cancellations or churn.

At most one candidate is processed per invocation. The existing single-writer
concurrency group is retained. No blocked gate is bypassed to serve another PR.

## C. Final subject binding

The existing CI fixpoint rechecks remote HEAD after testing even on its no-diff
exit. A separate final evidence step checks the actual local HEAD/TREE, clean
worktree, normal/optimized executed-test receipts and current REST ref/commit
readback. Sources are checked again after readback. A valid test of superseded
A remains a test of A; it cannot establish current completion of B.

The existing integrity writer is not expanded or reclassified as independent
review. GitHub's originating event SHA and the actual tested successor SHA are
recorded separately. Fresh execution evidence is required for each successor.

## D. Technical verification and reporting are different results

The verifier computes its technical result from explicit raw step outcomes.
Optional QCE skips are accepted only when the package is absent. Successful
steps also require final local/remote subject binding before success status
publication. Invalid envelopes do not authorize a status write.

Status publication and comment delivery have separate postconditions and
causal fields. A denied/lost comment cannot turn successful technical tests
into a failed code-test status. A required delivery failure still blocks the
workflow's overall completion. The former blanket `if: failure()` overwrite
path is removed. A source HEAD/base drift remains a separate HOLD.

QCE diagnostic JSON and axiom output now go to runner-temporary paths rather
than being created inside the package inventory under verification. Whether
that change closes every QCE defect requires a real exact-head QCE run; it is
not inferred from this maintenance change.

## E. Export final evidence, not a historical predecessor bundle

The preliminary diagnostic/history export has a distinct artifact name. The
final artifact is created after tests and final HEAD/TREE readback, contains
only run-local output, and retains `FINAL_EVIDENCE.json`, both executed-test
inventories and available raw make logs. Its manifest hashes the exported
files. The final elementary workflow-disposition check remains separate;
artifact publication is not effect acknowledgement.

Missing, stale, skipped, duplicate, forged-coverage or source-drifted execution
receipts cannot establish final success. Historical PASS records are not
imported as current execution. The unchanged general make gates remain in
force; no test count is inferred merely from command/source presence.

## F. Issue autofinish requires observed postconditions

An empty check rollup, or a rollup containing no successful check, no longer
authorizes either the authority merge or the mirror merge. Authority and mirror
rollups are evaluated independently. Neutral or skipped checks may coexist with
a success, but they cannot establish readiness by themselves.

After both merges and tag readbacks, the issue close operation now precedes the
effect acknowledgement. The workflow reads the issue state back and emits
`EFFECT_ACK_DONE` only after observing `CLOSED`. A transport acknowledgement of
the close request is not substituted for that state observation.

## Earlier detection is an executable gate

`state/autonomy/PIPELINE_CONTRACT_TESTS_V1.json` maps each audit requirement to
specific test IDs and the required runner. `make test` runs
`pipeline-contract-test` before compile/integrity gates. The same declared suite
runs in normal and optimized Python. The runner records planned IDs, actually
started/completed IDs, outcomes, requirement coverage, Python mode, source
hashes, run/attempt, HEAD/TREE and whether the subject was a clean committed
snapshot. Skips/expected failures do not satisfy required coverage.

The tests include real temporary Git repositories and bare remotes, controlled
GitHub API failures, lost responses, late competing writes, reporting faults,
and an end-to-end invocation of the real evidence runner in both modes. API
faults are deterministic doubles, not claims of live platform capability.

A local dirty candidate may pass its tests, but its receipt says
`committed_subject=false`. The final CI gate rejects such a receipt as proof of
an exact committed subject. Results are not transferred from a predecessor.

Run the required gate with `make pipeline-contract-test`; inspect the normal
and optimized JSON files under `QIKVRT_CONTRACT_EVIDENCE_DIR` (default:
`.qikvrt/runtime/pipeline-contracts/tests`). This gate is not repository-wide
zero-bug proof. New materially different failure classes still require their
own requirement/test/runner/evidence connection.

`PREDECESSOR_EVIDENCE_TRANSFER=false`; `TRANSPORT_ACK != EFFECT_ACK`;
`EFFECT_ACK_DONE=false`.


## Shared writer postcondition audit, 5 October 2026

The production stranded-branch case is draft PR #459, HEAD
`9c431098c4680f295a90bafe49ba747a74d288e6`. This successor starts from PR #455
HEAD `ca2678839c4170871d2624e21df614b295f55477`, TREE
`d411ea95cdb8b66d2f35f7b589ebbbb17c233766`, with Main
`86d7062f25f174039da0a5df8a856127553036f1`. These are source bindings,
not current-success claims for a later commit.

`AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json.same_repository_writer_postconditions`
inventories twelve existing internal writer carriers. The source/native audit
is retained in
`state/work_units/QIKVRT_SHARED_WRITER_POSTCONDITIONS_20261005_V1.json`:
185 registered workflows were read; 77 have source on observed Main.
Registration without a current source is classified historically and is not
silently restored or dispatched. Other write carriers retain their exact bytes
and their separate liveness, cross-repository, release or publication contracts.

The active Global Completion writer also has an older Authority-reference
classification. Its original classification and digest entries stay unchanged.
The new work unit binds exactly that operational workflow's forward successor;
the preservation regression still resolves and verifies its historical Git blob,
and additionally compares the unchanged triggers, concurrency, generation steps
and entire verification job. Negative controls reject a different path, changed
digest, liveness claim or scheduler/verifier change even with a replacement
successor digest. The old receipt does not become current execution evidence.

The existing `qikvrt_pipeline_contracts.py` now shares source/base observation,
bounded non-force push readback, draft-PR materialization and exact verifier
handoff. Every generic writer preserves its existing generation, staging and
checks. The self-heal materializer retains its original allowlist, identity and
create-only branch write; it delegates the PR/verifier phases to that same
helper. CI retains its tested fixpoint and its final exact-subject receipt.
The continuation retains its selector, maximum one candidate and scheduler.
The former repository-evidence rerun/sleep path is replaced by the existing
exact-head verifier handoff. No scheduler or executor is added.

A changed Main materializer is isolated on a base/tree-bound review branch.
An unchanged review branch still reconciles its missing PR/verifier. Lost,
denied, malformed or misleading write responses are not effect evidence;
independent remote observations decide whether the next phase may execute.
Read denial is not branch absence. A closed, ready, foreign, duplicate,
metadata-drifted or competing subject produces HOLD without being reopened,
made draft, overwritten, approved or merged. The CI and continuation push
entrypoints also recheck draft admission before a branch write.

Versioned corpus candidates keep their original staging base. Their existing
verifier receives an exact base-ref/head/tree binding; it is read-only apart
from separately typed status/comment delivery. Staging candidates receive no
Main-continuation or promotion marker. Main continuation selection and all
review, governance, owner-content-return and external-effect gates retain their
original scope. The generic helper grants no promotion marker.

Per invocation, each effect phase has at most one branch push, PR POST,
body-only PATCH and verifier dispatch. An already observed exact native verifier
suppresses redispatch, and its terminal failure is preserved. Readback and
metadata PATCH remain non-atomic; no global exactly-once guarantee is claimed
against arbitrary competing external writers or unbounded API visibility delays.

Native execution exposed one activation gap: Main `86d7062f...` still carries
the legacy verifier without a subject-bound run title. Its HTTP-204 dispatches
create runs that the new exact postcondition cannot identify safely. Before any
dispatch, the helper now reads the carrier from exact trusted Main, verifies its
Git blob and checks the binding protocol (including base-ref support for staging).
A legacy, absent, denied, corrupt or drifted carrier produces a causal HOLD
without another dispatch. Existing branch/PR materialization remains separately
observable. The exact legacy Main bytes are an executable negative regression;
after independently reviewed Main activation the same PR resumes without being
recreated, using freshly observed candidate HEAD/TREE and current base identities
after the existing re-entry. Old subjects and results do not transfer. No
candidate writes itself onto Main to satisfy this precondition.

The required normal and optimized runner includes stateful response fault
regressions, real temporary Git/bare-remotes, Main isolation, byte-NOOP PR
recovery, admission races, staging preservation and production shell parsing.
Review candidate construction, exact local/native technical tests and reviewed
Main activation remain separate evidence states. `EFFECT_ACK_DONE=false`.
