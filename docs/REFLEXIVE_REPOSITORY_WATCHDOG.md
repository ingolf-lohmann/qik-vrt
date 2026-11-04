# Reflexive repository Gatewatch and pre-deadlock admission

## Open work and useful-progress continuity — Owner correction, 4 November 2026

The existing watchdog must not infer idle from the absence of active workflow
runs. Its native observation now includes `collect-work`, a GET-only inventory
of open GitHub issues and pull requests. Collection is bounded to ten pages plus
one first-page stability read. A short terminal page is required. Duplicate or
foreign entries, an unstable first page, truncation, missing access, a stale
inventory or a different subject cannot establish an empty queue. The existing
twenty-request jobs budget remains unchanged. This inventory covers GitHub work;
it does not claim completeness for private workspace tasks or other stores.

`CONTINUATION_REQUIRED_OPEN_WORK` retains the exact pending item identities when
no productive execution is observed. Missing inventory yields
`PREEMPTIVE_HOLD_WORK_INVENTORY`, with unknown work state. Neither is quiescence,
completion, permission to run issue text, or permission to bypass a blocker.
The existing continuation consumer must triage the preserved obligations and
continue only a safe, callable, already authorized successor. Protected external
dependencies remain explicit holds with their causal next action.

The useful-progress clock is cumulative within the same repository, HEAD, tree
and observation scope. Receipts retain `last_progress_at` and terminal executed
job/step markers. A new executed result advances the clock. Observer heartbeats,
timestamps, run IDs, attempt numbers and an identical retry do not. Frequent
observations therefore cannot renew the progress lease indefinitely. Marker
history survives replacement of a run by an identical retry; stale or foreign
bindings cannot supply progress. The age of the last observation is retained
separately, so failure of the observer remains detectable.

Open work or active execution without a new marker beyond the progress lease
produces the existing no-progress hold and a concrete continuation edge. A
baseline is necessary for that time comparison. A failed check records unknown
live progress. Analysis and collection failures both produce a machine-readable
observation-failure receipt.

The previously implemented `repair-handoff` / `repair-consume` path is now wired
between the existing workflows. The consumer independently reads the producer
run, attempt and jobs, verifies the executed handoff step and exact analysis
bytes, and retains the original input before selecting existing admitted work.
It grants no writer authority. Producer artifacts are bounded and read as data;
repair inputs live outside the checkout and are retained as artifacts.
The watchdog does not subscribe to continuation completion, preventing a
watchdog → continuation → watchdog feedback loop. Actual issue and PR events
and existing workflow events carry observations; no timer is introduced.

This is an executable detection and continuation obligation, not a proof of
universal liveness. Main integration, native execution, available credentials,
original-host admission and productive domain/EFFECT_ACK acceptance retain
their separate evidence obligations.


The adaptive repository monitor is extended by a read-only watchdog that observes its own repository instance at relevant source and workflow transitions. Its purpose is not to wait for a deadlock and then diagnose it. It models writer leases, runner pressure, exact-head execution evidence, and unchanged progress topology early enough to issue a deterministic `HOLD` before a second writer or replacement writer is admitted.

## Operational model

Each repository instance carries the same contract, controller, workflow, and regression test. The Authority remains the serialized source of the portable contract; Mirror and future mesh nodes must retain their own repository identity and integrity projections while satisfying the same structural acceptance.

The watchdog treats repository activity as a resource-allocation graph:

- `REPOSITORY_WRITE_LEASE` has capacity one;
- active repository writers hold or request that lease;
- queued productive workflows request platform runner capacity;
- a writer without a job/step transition beyond its lease is stale;
- unchanged active topology beyond the progress lease is an early stall signal;
- `action_required` and zero-job runs are untrusted execution gaps;
- no active runner is not interpreted as `PIPELINE_EMPTY`.

The first deterministic response is admission control, not destructive recovery: keep one expected-head-bound writer, coalesce only superseded observer runs, preserve an exact-head receipt, and stop before another writer is introduced. The watchdog never cancels a productive writer, mutates a ref, merges a pull request, or performs a release, deployment, Zenodo, DOI, or IETF effect.

## Continuous exact-head Gatewatch

Every state-transition observation materializes an artifact-only
`reflexive-watchdog-receipt.json` and the identically bound
`gatewatch-receipt.json`. Both records contain the literal observed head and
tree, a trusted-workflow matrix, node-liveness observations, and the prior
receipt binding. A receipt from another head or tree is discarded rather than
being used as fresh evidence.

The Gatewatch classifies each declared trusted workflow as `SUCCESS`,
`FAILED`, `MISSING`, `ACTIVE`, `UNTRUSTED`, `NOT_OBSERVED`, or
`NOT_APPLICABLE`. A terminal execution failure is a deterministic `HOLD`; a
required pull-request gate that is missing or lacks executed job evidence is
also a `HOLD`. The contract distinguishes a pull request against `main` from
a stacked pull request: only the former requires the evidence-materialization
workflow, because that workflow is configured to trigger only for `main`-base
pull requests. A stacked successor therefore still requires exact-head CI but
never treats an impossible materializer run as proof. Main observations
distinguish an optional scheduled gate from a missing pull-request gate, so a
missing main-only run is never silently invented as a successful verification.

For repository nodes that carry the onboarding records, the same observation
parses all three exact-tree inputs:

- `SEED_ACCEPTANCE_STATUS.json` must bind the currently reobserved Authority
  `main` head;
- `NODE_REGISTRATION_RENEWAL.json` must not be overdue;
- `NODE_HEALTH.json` must not be expired.

An Authority instance without all three node-local records is explicitly
`NOT_APPLICABLE`; a partial record set, malformed record, stale seed
acceptance, overdue renewal, or expired health becomes a read-only `HOLD`.
Records approaching expiry remain visible as `EXPIRING` without a fabricated
renewal. The observer also detects a missed continuous observation only when a
previous receipt is bound to the same head and tree and exceeds the declared
fifteen-minute freshness bound. A burst of cancelled, zero-job observer runs is
coalesced only when a later exact-head receipt remains within that bound;
otherwise it is a deterministic observation-cadence `HOLD`, not a claim of
pipeline quiescence.

The workflow remains transition-driven, exact-head-bound, and read-only. It fetches
the current Authority head only for comparison, materializes Action artifacts
only, and never writes a repository liveness record, dispatches a productive
workflow, or treats its own terminality as gate success.

## Reflexivity

### Job-readback request budget

The existing controller's `collect-runs` command reads pages of 100 entries with
at most ten original `gh api` GETs, retaining page bytes and stderr under
`run-pages/`. It merges them into `current-runs.json` before requesting any jobs.
Every page must report the same
integer `total_count`; the combined inventory must match that count, contain no
truncation or duplicate IDs, and bind every run to the expected head. Invalid
names, statuses or timestamps also stop admission. This count check fails closed
if the provider's own pagination/search limit prevents a complete inventory.

`job-readback-budget --required-jobs-only` derives the exact job dependencies of
the analyzer: the latest run of **each workflow name**, plus **every active run**,
including an older active run with a newer completed successor. It never samples
the first 20 runs. At most 20 per-run jobs GETs are admitted for this union; older
completed runs remain in the full metadata inventory. Their normalized receipt
entries explicitly have `jobs_observed=false` and `jobs=null`, rather than
claiming an observed zero-job execution. Latest gate decisions and all writer,
queue, liveness and stale-progress checks remain in force. The legacy budget CLI
without this explicit option retains its all-run policy and historical format.

An incomplete inventory or a union needing more than 20 job requests produces
`HOLD` before any jobs GET. The failure receipt records `JOBS_BUDGET_PREFLIGHT`;
pipeline progress remains unknown. A denied run or job GET stops the step;
there is no automatic retry. Failure to download the prior receipt artifact also
stops at `BASELINE_READBACK`, before any current run or job request. An HTTP 403
on that earlier path cannot be ignored as an optional missing baseline.

`collect-jobs` shares a hard budget of 20 actual jobs GETs across selected runs
and their continuation pages, each with `per_page=100`. Budget exhaustion stops
analysis; a 21st request is never issued. Page counts, identities and statuses
are checked during collection. `JOBS_COMPLETENESS_PREFLIGHT` also requires the
merged integer `total_count`
to equal the returned job count and rejects malformed/duplicate jobs, mismatched
run/head/attempt identities and active jobs on a terminal run. Analysis rederives
the plan, verifies its inventory SHA-256, and requires exactly the selected job
files. A missing file cannot become an empty successful observation. The original
artifact, causal reproduction and bounded regression evidence for issue #682 are
in `evidence/receipts/20261104-watchdog-run-inventory/`.

Unknown job statuses count as untrusted evidence even in the gate evaluator;
one successful job cannot hide another malformed or active job. The collector
and numeric latest-run ordering from overlapping PR #683 are retained, together
with its original evidence archive. The source histories converge in PR #684;
native tests for predecessor heads do not accept the combined successor.

This is a bound on this step's job-page reads,
not a provider-wide quota controller or proof of live event delivery.

### Failure of the observer itself

An API/readback failure before analysis is an observation error. It must leave
a `qikvrt_reflexive_observation_failure_receipt_v1` in both receipt paths,
bound to the actual checkout head/tree, expected head, run, attempt, failing
stage and nonzero exit code. The receipt records `OBSERVATION_FAILED` and
`HOLD`; live state and pipeline progress remain unknown. The failed workflow
remains failed even when artifact upload succeeds. This distinct receipt is
never substituted for a successful observation or a trusted gate.

Recovery requires restoring the failed authorized read path, freshly reading
the exact subject, and continuing the existing work unit. A prior receipt,
owner authorization, repeating observer, or missing active runner does not
establish recovery or productive delivery. No new controller, credential,
permission expansion or automatic productive-writer cancellation is involved.

The watchdog observes the workflows that create and verify repository state,
while its own executions are classified as observers rather than productive
writers. Main's 26 October delivery repair uses completion notifications and
`cancel-in-progress: false` so a new lifecycle notification does not cancel
the active observation. The later Owner correction of 31 October removes the five-minute schedule.
Readback of unfinished runs and unchanged heads occurs on actual state
transitions; freshness budgets remain checks, not activation timers. The analyzer still evaluates
every returned run and the explicitly selected complete job inputs; no liveness, missing-evidence or stale-progress
criterion is removed. This source configuration change does not establish a
completed public-host observation or global deadlock freedom.

## Database comparison boundary

Conventional relational database systems already provide transaction deadlock handling techniques such as prevention, detection, ordering, and timeout policies. The QIK-VRT improvement claimed here is narrower and architectural: deadlock-risk admission is bound to versioned repository heads, workflow/job evidence, provenance receipts, Authority-to-node serialization, and external-effect boundaries across independently instantiated repositories. It is not a claim that every relational database lacks deadlock management, nor a benchmark proving universal performance superiority.

## Nonclaims

A successful watchdog run is observation evidence, not gate success. The mechanism does not prove global deadlock freedom, repository completion, Authority–Mirror equality, empirical confirmation, scientific consensus, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Canonical roles and independent native readback

The existing `policy/CANONICAL_UPSTREAM_REMOTE_V1.json` is the sole normative
repository-role source. The executor/liveness contract is a checked projection.
The shared resolver reused from the authority-repair work rejects missing,
malformed, overlapping or contradictory Authority/Mirror assignments. A Mirror
receipt cannot establish Authority continuity even when its commit matches.
Historical receipts retain their original bytes and repository identity.

The native wrapper uses the mandatory job token and bounded GitHub REST GETs.
It binds Authority Main to its exact commit and tree, validates the canonical
role policy, governance policy and CODEOWNERS bytes by Git blob identity, then
reobserves Main. HTTP 200 without the expected active Main roles remains
`AUTHORITY_ROLE_BINDING_NOT_ACTIVE`. HTTP 403/404 has no Mirror, anonymous,
browser or alternate-token fallback. The latest completed observation supplies
the prior denial receipt, including failed observations. An unchanged causal
binding suppresses a repeated denied request. Unrelated commits, lifecycle
progress and timestamps do not admit a retry. Changes to the role policy,
Authority binding or reviewed token/transport carrier require one new bounded
observation; external permission repair must be independently evidenced before
clearing a denial receipt.

A successful role readback still sets `native_activation_verified=false`:
executed native candidate gates, trusted-Main adoption, native enforcement and
independent current-head Code Owner approval remain separately required. No
predecessor test or availability observation substitutes for those effects.


No observation proves that the observer will receive another event. A quiet
system with a lost event needs an independent observation before an observer
failure can be detected; no timer-free global liveness guarantee is claimed.

## Bounded acceptance and the native build stall

The executable invariant is that OPEN or UNKNOWN work never permits silent
idle. A finite acceptance matrix covers 1, 2 and 169 open items with no run,
queued work, running work and terminal success, failure, cancellation, timeout
and action-required states (24 combinations). Existing negative traces cover
unchanged heartbeats, repeated identical failures, stale/wrong-source evidence,
missing readback and analyzer failure. These checks do not prove unconditional
liveness of an external service or permanent runtime availability.

The original exact-head S1 jobs additionally exposed an actual dependency stall:
job 126915921892 received package HTTP 503; job 126914575535 emitted only two
InRelease fetches before its 35-minute cancellation. The successor retains the
original frozen carrier, platform, signature verification, eight package
versions and no-upgrade policy. FROZEN_BUILD_APT_V1.json locks every selected
package's origin, path, size and SHA-256. The official Debian transport supplies
only that set; new index entries cannot silently change a dependency. APT still
verifies Debian signatures and package hashes against its original keyring.
The guard rejects plan drift before download, verifies actual archive bytes
before a no-download install, and checks installed versions afterward.

Index fetch, binary fetch and install have absolute limits of 180, 180 and
120 seconds, each with a 10-second termination grace; individual network waits
are limited to 30 seconds and retries are zero. A failure stops the builder;
it never manufactures a successful smoke test. The existing native CI must
still execute the new source, reproduce both OCI builds and verify the actual
terminal/restart before integration. Productive Originalhost, exact domain,
peer adoption and EFFECT_ACK remain separate, independently observed effects.
