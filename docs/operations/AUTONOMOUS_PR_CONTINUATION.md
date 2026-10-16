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

### Owner-requested signing and GitHub completion feedback — 2026-10-17

The existing `QIKVRT workflow executor` now has a separately bounded signing
continuation for the Owner's explicit persistent-execution request. Its ordinary
watchdog allowlist remains effect-free. The additional capability is fixed to
the official AMO unlisted endpoint and the exact deterministic six-component
Standard XPI digest in `WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json`.

The existing executor receives GitHub `workflow_run: completed` events for
`QIKVRT CI` and its existing watchdog. A read-only receiver independently GETs
the original run, jobs and steps and stores `GITHUB_RUN_FEEDBACK.json`. This
includes actual `cancelled`, `timed_out` or `failure` conclusions. GitHub may
omit the underlying cancellation reason; that remains
`NOT_EXPOSED_BY_GITHUB`. Original signing preflight and receipt boundary codes
are retained when available. A single bounded original-log read per failed job
may add failed repository test identifiers, `MAKE_TEST_EXIT` codes or the known
GitHub execution-limit/concurrency reason codes. Arbitrary exception text,
raw logs and credential values are not forwarded. A log unavailable under the
existing Actions read permission remains explicitly unavailable. An elapsed
interval is never abortion evidence.

This is asynchronous provider push feedback, not a blocking synchronous call.
The receiver checks out its own Main event SHA, never triggering-run source or
executable artifacts. It has no dependency on the caller and no workflow-global
concurrency lock. Original signing-job artifacts can be reconciled even when
another job keeps the full CI workflow in progress. A run still active without
a provider completion event remains pending; no application timer declares it
dead. Existing unrelated reminder schedules do not drive this signing path.

For an initial upload the existing executor requires current native Main
protection, independent code-owner review enforcement and required checks;
the request and six-component package must match exactly. Only the existing
AMO secret names' presence booleans and a non-secret opaque binding revision
are visible to the coordinator. Values reach only the existing signing step.
Direct Owner invocation of that step retains its exact PR523 admission.
Delegated `github-actions[bot]` invocation additionally verifies the original
Main-run intent artifact, its digest and the actual started dispatch step.
It never waits for its caller's later receipt or overall return.

Before dispatch an immutable intent is uploaded and admission is read again.
The native workflow token invokes the existing CI with
`return_run_details: true`; the immediate returned run ID is journaled. There
is no run-ID polling loop. A missing HTTP acknowledgement is ambiguous and
must be recovered from an original CI preflight backlink; it cannot authorize
a replacement upload. Provider-confirmed cancellation or pending AMO signing
permits one independent GET-only readback, using a separate concurrency group
so it cannot queue behind a stuck writer. A GET 404 in that mode cannot PUT,
even when the original journal is missing. Pending or aborted recovery does
not dispatch another unchanged recovery loop. A new provider observation or
explicitly changed authorized binding is required for a subsequent decision.

Native Actions artifacts carry the non-secret continuation journal and the
existing live progress schema. Unrelated commits or observation timestamps do
not reset a failed attempt. This source change becomes a live event consumer
only after its ordinary protected Main integration and native admission; a
candidate commit or passing fixture test does not activate it. Firefox 158
default-policy acceptance, protected production image/profile admission,
runtime health, exact-domain forwarding removal and fresh public readback
remain independent open obligations.

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

## Immediate execution — Owner principle of 2026-10-13

> Was du heute kannst besorgen, das verschiebe nicht auf morgen, sondern erledige es unmittelbar, denn alles andere war, ist und wird inakzeptabel sein.
>
> q.e.d.
> Ingolf Lohmann

Execute every safe, deterministic, authorized and actually callable next action
in the current work ring, through its tests, persistence and fresh readback.
Do not postpone executable work to another day, chat or run merely to return
an intermediate status. Reuse `tools/ai_handoff.py --client-receipt`: it already
rejects a terminal handoff with an executable successor. Its consistency
result is separate from live execution evidence. A genuine external or
protected-authority blocker keeps the task open with its exact retry condition;
other executable work continues. Preserve causal NOOP for unchanged failed
effects, existing authorization and review boundaries. The machine binding
extends `self_application_working_rule.immediate_execution_principle` in the
existing recursive policy, with no parallel controller or trigger.

## Recursive self-application — Owner rule of 2026-10-13

The Owner's 2026-10-15 transition instruction also applies to the client's
preparation before a later effect becomes available. Use `transition_plan` in
the existing `tools/ai_handoff.py --client-receipt` contract documented in
`docs/HUMAN_MACHINE_PROGRESS_PROTOCOL.md`: bind current task inputs, retain
activation conditions and alternatives, and execute admitted preparation now.
Consume the emitted ready actions through the existing executor, reassess after
human corrections, and retain causal NOOP and every existing effect boundary.
This source-level capability is not proof of a deployed autonomous consumer or
a measured speedup.

Apply the working method to its own results, errors, omissions and open
obligations across every applicable layer. Consume the exact preceding run's
results as successor inputs. Keep task identity, source, affected subject,
acceptance criterion and the smallest authorized causal repair. Execute an
admitted repair, test the changed subject, read back its effect and continue.
An unreadable or vanished subject remains an unreobserved obligation.

The existing `tools/ai_handoff.py --client-receipt` gate rejects dropped
predecessor duties, premature completion, uninspected existing routes,
unchanged failed retries and missing effect readbacks. Reuse that gate.
The existing Site evidence collector now carries current and unreobserved
duties in each persisted snapshot, with the previous verified snapshot's ID
and SHA-256. Its original-byte readback covers the duties as part of the same
record. The observer dispatches no native effects, DNS writes or permission
changes. Recording a task does not establish an available executor.

An unchanged failed effect is NOOP until its causal prerequisites or genuinely
available execution capability change. Observation clocks and unrelated node
lifecycle commits do not authorize another attempt. Other admitted work
continues. Each changed subject needs fresh dependent gates; predecessors
remain historical evidence, and their PASS does not transfer.

Preserve “Quod erat demonstrandum ingenium” as Ingolf Lohmann's formulation.
A scientific proof, novelty or improvement claim needs a concrete verified
delta in a stated scope. Iteration count, new bytes and the attributed phrase
alone do not establish that claim. This is an operational working rule.

The product-delivery target is `https://raumzeitterminal.de/`. DNS, TLS, useful
application delivery and authenticated native execution are separate
obligations. A different hostname, a successful observer, repository tests or
an HTTP-200-only observation does not establish product acceptance. Persist
and read back each layer through its supported authorized path; mark unknown
propagation rather than claiming adoption on Main, the Mirror or other clients.

The existing draft integration candidate #523 is reused for this request.
No parallel controller, new trigger or review bypass is created.
