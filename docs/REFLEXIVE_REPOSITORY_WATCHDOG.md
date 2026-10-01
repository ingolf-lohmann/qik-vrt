# Reflexive repository Gatewatch and pre-deadlock admission

The adaptive repository monitor is extended by a read-only watchdog that observes its own repository instance every five minutes and at relevant workflow transitions. Its purpose is not to wait for a deadlock and then diagnose it. It models writer leases, runner pressure, exact-head execution evidence, and unchanged progress topology early enough to issue a deterministic `HOLD` before a second writer or replacement writer is admitted.

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

Every scheduled or event-driven observation materializes an artifact-only
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

The workflow remains five-minute, exact-head-bound, and read-only. It fetches
the current Authority head only for comparison, materializes Action artifacts
only, and never writes a repository liveness record, dispatches a productive
workflow, or treats its own terminality as gate success.

## Reflexivity

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

The watchdog observes the workflows that create and verify repository state, while its own executions are classified as observers rather than productive writers. Observer executions use a coalescing concurrency group so newer observations replace obsolete observations without consuming the repository write lease. A scheduled observation prevents unchanged heads from becoming permanently invisible merely because no new event occurs.

## Database comparison boundary

Conventional relational database systems already provide transaction deadlock handling techniques such as prevention, detection, ordering, and timeout policies. The QIK-VRT improvement claimed here is narrower and architectural: deadlock-risk admission is bound to versioned repository heads, workflow/job evidence, provenance receipts, Authority-to-node serialization, and external-effect boundaries across independently instantiated repositories. It is not a claim that every relational database lacks deadlock management, nor a benchmark proving universal performance superiority.

## Nonclaims

A successful watchdog run is observation evidence, not gate success. The mechanism does not prove global deadlock freedom, repository completion, Authority–Mirror equality, empirical confirmation, scientific consensus, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Authority read capability HOLD

The shared read-only observer classifies a failed Authority Main GET with a
native HTTP 401/403/404/429/500/502/503/504 response as `AUTHORITY_UNAVAILABLE`.
The cause remains `UNESTABLISHED`: this is no evidence of destroyed Authority.
The successful observer workflow materializes a capability HOLD, not a successful
Authority gate. Subject HEAD/TREE, paginated run/job/step evidence, prior receipt
comparison and exact endpoint/status/exit-code/response-digest bindings remain in
the artifact receipt. No takeover, writer admission or EFFECT_ACK is permitted;
`effect_ack_done=false`. Recovery requires restored read capability and a fresh
exact-subject observation. Other API failures, malformed successful ref responses,
changed Authority identity, subject HEAD drift and tracked mutations remain hard
workflow failures. Historical failure receipts remain historical evidence.
# Automatic error-analysis handoff

The watchdog's `repair-handoff` command carries the original UTF-8 analysis,
SHA-256, repository/HEAD/TREE and producer run/attempt into its existing artifact.
The existing draft-PR continuation workflow receives the watchdog completion,
fetches the authenticated producer run, attempt jobs and single bound artifact,
checks the archive digest and extracts only `repair-handoff.json` as data.
Trusted Main's existing self-heal controller executes `repair-consume`. It checks
the current subject, producer path, executed handoff step and exact analysis
bytes, creates the work-unit inbox record and verifies its byte readback. The
consumer receipt and inbox are preserved as GitHub artifacts for 90 days. This
is artifact durability, not perpetual storage or Authority/Mirror equality.

Unknown cause or unsupported repair remains `ADMITTED_ANALYSIS_HOLD`, with the
original analysis available to the existing diagnosis/repair path. The input
never grants writer permission; it is neither executable text nor self-approval.
Identical local inbox replay is readback-only; conflict cannot overwrite the
record. No external writer effect is admitted by this consumer, including on a
repeated runner delivery. General cross-run exactly-once repair requires the
existing independently admitted effect ledger and is not inferred from inbox
deduplication. Stale or foreign subjects, wrong attempts, missing jobs, skipped
handoff steps and altered analysis block before inbox admission.

To keep the event graph finite, continuation completion no longer immediately
triggers its own producer. The watchdog continues observing continuation runs
on its existing schedule and other relevant events. A consumer feedback report
is a bounded NOOP. No second executor or ChatGPT automation is introduced.

## Cause and prevention scope

The prior source had two disconnected edges: the watchdog stopped at artifact
upload, and the continuation subscribed only to CI/evidence completion. Neither
had an executable error-analysis admission/readback contract. This directly
explains why that inspected path could report a failure but could not deliver
its analysis to a repair consumer. It does not establish every historical reason
why the missing integration was introduced. No maintainer motive is inferred.

The regression roundtrip invokes the actual producer and consumer CLIs and
verifies preserved analysis bytes, admission HOLD, replay and readback. The
self-heal contract now requires the handoff edge; absent/weakened bindings block.
These controls address recurrence of this bounded integration gap. The tests
use authenticated-observation fixtures; they do not establish productive Main
activation, independent approval, repair of the reported error, or global DONE.
Productive activation still requires independent native Main admission, then a
real found-error delivery and fresh consumer artifact readback on the admitted
subject. A native governance blocker does not turn persistence into repair.
