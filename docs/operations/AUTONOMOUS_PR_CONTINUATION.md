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

### Exact tested subject after integrity re-entry — 2026-10-17

The existing CI test job publishes its accepted committed HEAD and TREE only
after the terminal full-test/fixpoint gate succeeds. Offline-browser and S1
container source checks consume that subject through `needs.test`, then verify
both identities independently after checkout. They must not silently check out
the original event HEAD after the admitted integrity writer advances the PR.
The handoff rejects uncommitted changes, a changed remote ref, unrelated ancestry
and successor changes outside the three existing integrity files. Other source
changes require fresh admission and their own exact-subject tests.

This fixes the downstream materialization handoff; it does not approve a
workflow or publish a synthetic commit status. GitHub-token PR synchronization
still creates approval-required workflow runs under the provider contract:
https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
The existing REST admission, independent review, signing and publication
boundaries remain separate. No new trigger, credential, permission or executor
is introduced. A successful upstream test job does not accept another job's
execution, the whole workflow, a publication or exact-host delivery.

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

Credential diagnostics are scoped to the current job's secret context. Both
the CI `ACCESS_PREFLIGHT.json` and the coordinator's intent/HOLD receipt retain
`credential_delivery`, including when native protection blocks admission.
`PAIR_NOT_DELIVERED` and `PARTIAL_PAIR_DELIVERED` do not establish that a key is
absent from repository, organization, environment or private credential storage.
`configuration_status=NOT_INSPECTED` and unverified AMO authentication stay
explicit. A non-requested CI invocation reports `AMO_SIGNING_NOT_REQUESTED`,
independently of credential delivery. None of these observations admit signing.

The existing two AMO jobs reference repository/organization secret contexts;
neither names a GitHub environment. Environment-scoped secrets require their
actual, separately admitted job/environment binding and any native approvals.
An unreadable secret inventory cannot supply that binding. Do not guess an
environment name, copy secrets, expand permissions or relocate credentials to
make a preflight pass. Reobserve the existing protected binding through an
authorized secret-metadata operation first. The unchanged package, required
Main protection, independent review and original intent remain mandatory.

The first activation has an exact source boundary: the independently observed
pre-activation Main commit and original contract blob are pinned in the Owner
request. Its original bytes must prove that this signing producer did not yet
exist. Reaching that source bounds historical discovery without scanning years
of older jobs or spending the repository token's request budget on them. Later
old-source runs with any other head cannot erase an admitted producer's journal.
This is a source-lineage boundary, with no deadline or age-based abort rule.

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

## Direct Owner Firefox signing REST client — 2026-10-17

Ingolf Lohmann explicitly renewed `APPROVED` / Product Owner authorization
for Firefox admission repair and PR523 integration on 2026-10-17 at
11:19:29 Europe/Istanbul. The exact instruction and its scope are retained at
https://github.com/ingolf-lohmann/qik-vrt/pull/523#issuecomment-6231678308.
This is an Owner instruction, not an independent native GitHub review.

Reuse `scripts/qikvrt_api_client.py` with an already authorized GitHub token
securely supplied as `QIKVRT_API_TOKEN`. A local adapter token is not a GitHub
credential. No token value belongs in arguments, source, logs or receipts.

`--operation firefox_amo_access` performs GETs for the two fixed repository
secret names `AMO_JWT_ISSUER` and `AMO_JWT_SECRET`. It reports only the name and
creation/update times. It neither retrieves values nor changes their binding.
Denials retain `NOT_INSPECTED`; configured metadata does not establish job
delivery or Mozilla authentication. Environment/organization/vault scopes
remain uninspected. This read is not a prerequisite for an otherwise admitted
signing dispatch: Actions-write and Secrets-read are separate permissions.

The existing direct Owner signing branch does not depend on a Main merge.
Use `--operation firefox_amo_dispatch --dry-run false --accept-effect`, the
current PR523 `--ref`, independently reviewed `--amo-expected-head`,
`--amo-expected-tree` and `--amo-workflow-blob`, and a stable `--request-id`.
An optional `--amo-previous-run-id` binds the prior native producer; the
existing workflow resolves and recovers its original signing journal.
The client verifies the six-component package against the existing Owner
request, reads current PR523 HEAD/TREE and immutable workflow bytes, then
reobserves source admission under the existing durable client journal lock.
It dispatches only `qikvrt_ci.yml`, with `amo_executor_run_id=0`; the actual
consumer must enforce `GITHUB_ACTOR=ingolf-lohmann` before any signing effect.
No generic workflow dispatch, new server, proxy, trigger or permission grant
is added. The existing Ruleset writer route remains unchanged.

The existing private journal is keyed by official add-on/version rather than
request ID, ref or unrelated HEAD/TREE changes. A pending or ambiguous dispatch
survives restart and remains readback-only. HTTP200/204 means transport
acceptance only. Retrieve the original native run, job logs, signing journal,
receipt and signed XPI through the existing GitHub readback operations. Verify
the exact source binding, Mozilla signature, default-policy Firefox activation
and persistent restart. Never infer these effects from metadata or a dispatch
response, and never edit/delete a journal to force a new submission.

Each operation reuses the existing repository/exact-host closing readback.
The OpenAPI source describes the bounded GitHub operations; changing it does
not register them with ChatGPT. A securely credentialed, callable runtime and
the active connector's actual operation exposure remain independent activation
conditions. A repository commit or fixture PASS cannot close that live gap.
Independent native approval and effective Main protection remain separate
merge gates after successful Firefox admission.

## Close a missing REST capability through the original source — Owner 2026-10-25

Use REST first. If an operation is absent or insufficient, inspect the existing
connector and its actual method/target/principal binding, read the exact original
repository implementation and extend that existing REST path. The final source
fallback is the original Authority `ingolf-lohmann/qik-vrt` on GitHub. Reproduce
the failure, test the corrected component and complete package, persist the exact
source and continuation and independently read them back. Then use REST when its
actual runtime and protected credential bindings are admitted. Do not request
the existing Owner authorization again, create a parallel executor or substitute
a timer. A callable source repair belongs in the existing transition's
`preparation` and `blocking_repairs`; it prevents a premature terminal BLOCK.

The original fixed Ruleset controller existed, but its direct POST bypassed the
existing durable attempt journal and rejected current HTTP200 run details. The
own REST adapter also did not expose that fixed operation. The shared controller
now persists exact-source intent before transport and accepts validated HTTP200
run identity as well as legacy empty HTTP204. Its journal key is independent of
request ID, Main SHA and writer version, so none can replay an unresolved POST.
The current provider contract is documented at:
https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event

The existing `src/qikvrt_github_api_shim.py` now offers exactly:

`POST /repos/ingolf-lohmann/qik-vrt/qikvrt/ruleset-authority`

`GET /repos/ingolf-lohmann/qik-vrt/qikvrt/ruleset-authority`

These are QIK-VRT routes, not additional GitHub endpoints. The service is
disabled for this purpose unless `QIKVRT_RULESET_AUTHORITY_ENABLED=1` is installed
through its protected configuration. Admission also requires the existing
expiring REST credential, exact Authority repository and configured Owner login
`ingolf-lohmann`. The server reuses the protected Authority credential resolver;
it excludes generic `GITHUB_TOKEN`, rejects reuse of the caller credential and
never returns a credential value. Enabling source code does not configure a
credential or grant provider permissions. The evidence-read MCP credential and
catalog retain their existing scope.

The server needs the original source/policy files, declared Python runtime and
its protected configuration. It does not need an already running productive S1
or protected Main to request repair of Main protection. The existing Ruleset
writer and its exact-source checks still own the actual administration effect.
No generic URL, workflow, branch, source override, native review, ready transition
or merge operation is exposed.

POST uses this exact bounded request shape; replace only the explicitly bound
request identity, fresh Main SHA and selected reviewed writer version:

```json
{"schema":"qikvrt-ruleset-authority-rest/v1","request_id":"owner-ruleset-20261025","expected_main_sha":"080c05f1cba7b1638477da78613b87252ffe1a12","writer_version":"principal-review-v4","effect_accepted":true}
```

The existing repository client can select the admitted Mesh origin explicitly
with `--ruleset-via-mesh --base-url <actual-admitted-Mesh-origin>` and the existing
`--operation ruleset_authority_dispatch`, `--expected-main-sha`,
`--ruleset-writer-version`, stable `--request-id`, `--dry-run false` and
`--accept-effect`. Its `QIKVRT_API_TOKEN` remains the REST caller credential and
is never forwarded to GitHub. Omitting the Mesh flag preserves the existing
canonical direct-GitHub default and its separate provider credential requirement.
The private server and caller reuse the original journal implementation in
separate owned metadata directories, not another native ledger.

GET requires `request_id`, `expected_main_sha` and `writer_version`, with an
optional positive `run_id`. An omitted run ID recovers the exact original
request's saved GitHub run identity without changing its journal. The controller
then independently verifies the original run/event/ref/head, jobs, canonical
Ruleset digest and protected Main. If the provider returned no run identity or
the result remains ambiguous, GET retains the original intent and remains
unverified; it never retries POST. Wrong original request/source bindings and
duplicate parameters fail closed. A supplied independently identified run ID
uses the original GET-only postcondition path. The repository client uses
`--operation ruleset_authority_readback` with read-only defaults; the same Mesh
flag permits recovery without `--ruleset-run-id`.

HTTP202 proves transport continuation only. A GET-verified Ruleset postcondition
still proves neither mutation attribution nor Main integration, original-host
start, exact-domain delivery or global EFFECT_ACK_DONE. A source commit,
OpenAPI change or wire fixture does not register a hosted ChatGPT connector or
deploy this REST service. Preserve those exact activation gaps until observed.
Do not relabel a provider's unavailable REST ready/CAS operation as implemented
by this bounded Ruleset route.

## Direct Owner handoff to the existing Linux CI job — 2026-10-17

Ingolf Lohmann explicitly authorized the Linux CI/CD pipeline to take over
this operation at 12:33:35 Europe/Istanbul. The exact instruction is retained
in `WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json#/owner_ci_handoff`. This extends
the existing direct Owner signing path; the protected Main delegation and
its native protection requirements retain their separate admission rules.

The existing `amo_unlisted` job now depends on the successful `test` job and
checks out its exact committed HEAD/TREE output. An Owner push to the existing
PR523 integration branch can request signing without a separate dispatch.
The preflight and the signing consumer independently validate the fixed
repository, workflow source SHA, branch, original and triggering Owner actor,
first run attempt, successful tested subject, freshly read current open PR523,
and the already authorized deterministic six-component XPI digest. Bot pushes,
PR events, forks, other refs, stale subjects and changed packages cannot use
this handoff. It does not create an independent review or authorize Main
promotion. Workflow triggers, token permissions and Firefox signature policy
are unchanged.

The existing add-on/version concurrency group remains the upload writer fence.
Before an effect, the existing journal resolver inspects both actual manual
dispatch producers and Owner-push producers since this grant. Only a started
official signing step counts; a successful presence-only preflight does not.
The newest actual producer's original journal must be recovered before the
existing signing consumer runs. An incomplete inventory, lost original
journal or source drift holds the effect; reruns cannot replace fresh admitted
readback. The existing consumer persists upload intent before PUT and never
resubmits an unresolved upload, even if the repository HEAD changes.

`ACCESS_PREFLIGHT.json` records `DIRECT_OWNER_TESTED_PUSH`, its exact source
and authorization binding, and the job-scoped credential delivery state.
Missing credential delivery keeps `submit=false` and reports
`AMO_CREDENTIAL_PAIR_NOT_DELIVERED_TO_THIS_JOB`. This proves neither remote
secret-store absence nor Mozilla authentication. Original native receipts and
the signed XPI, followed by actual default-policy Firefox activation and
persistent restart, remain required before effect completion.

## Exclusive blocking-repair priority — Owner 2026-10-25

Ingolf Lohmann authorized the errors that prevent further work to take highest
and exclusive priority. This is completion/repair work; it does not wait for
idle or the optimization backlog gate. Defer unrelated work, performance and
throughput tuning until the blocking defects have their own verified repair.

Reuse the current client transition plan: `blocking_repairs` names its open
repair transition IDs. Every reference must resolve exactly once. The planner
retains unrelated ready actions under `deferred` and exposes only admitted
repair preparation/execution as `ready`. A flat `next_actions` entry cannot
bypass that scope. An unavailable repair stays open with its exact capability
or authority prerequisite; unrelated executable work does not replace it.
Remove a repaired transition from this list only after exact-subject effect
readback. An empty list restores the preserved ordinary work. Historical plans
without this field retain their reader contract. This gate validates declared
consistency, not the truth of a repair classification or actual execution.

The existing native-only IONOS S1 path remains first. Firefox signing and its
activation/restart acceptance remain separate. Main protection, native review,
protected host/storage/configuration, mTLS and exact-domain acceptance remain
required; a ready plan grants none of them and creates no timer or executor.

## Owner conditional REST merge and continuation — 28 October 2026

Ingolf Lohmann explicitly authorizes automatic repository merges when the current
PR is conflict-free and its existing applicable tests are green, followed by
immediate autonomous continuation. Read the later decision at
state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json
#/conditional_merge_decision; AI_CONTEXT.json pins the exact source bytes.
This later Owner decision admits the existing direct REST merge with its expected
PR-head precondition. Do not repeat the earlier CAS-based authorization hold for
this separately authorized route or ask the Owner for the same permission again.
Reobserve Main, head, tree, tests and competing writers immediately before each
merge; preserve platform protections and independently verify the actual merge,
Main tree and ordered parents. Resolve an ambiguous result by readback.
The legacy atomic old-Main CAS qualifier and disabled CAS workflow retain their
own technical status. This decision does not qualify them, admit an unavailable
Draft transition or prove an unattended executor. Merge acceptance is separate
from runtime, host, domain and productive EFFECT_ACK_DONE acceptance.



## Later Owner GraphQL fallback decision — 29 October 2026

GraphQL remains the standing admitted fallback when the required GitHub REST
operation does not exist. REST is the primary interface, including the existing
`/repos/ingolf-lohmann/qik-vrt/qikvrt/continuation` facade. Read the later decision
in `state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json`
under `graphql_fallback_decision`; the shared client policy pins its exact bytes.
This later Owner instruction supersedes the unconditional GraphQL prohibition
for the bounded admitted fallback; do not ask for the same authorization again.
Keep the fallback during adaptation. Successful original CI/CD/CO run/job
observations may reorder independent verification branches; they cannot remove
gates, rewrite source, expand credentials or transfer acceptance to another HEAD.
The first fixed operation is `markPullRequestReadyForReview`, followed by an
independent REST readback. Unknown effects prohibit another mutation. Merge,
protected service activation, native host and exact-domain acceptance remain
separate. No new timer, trigger service or replacement executor is introduced.

The existing workflow completion receiver now includes original CI, the native
TEMDD carrier and the operation watchdog. Its immutable per-run feedback artifact
retains job durations and skipped jobs. `continuation_graph` uses successful
job durations to order independent CI siblings by longest observed duration
first; missing timings remain unknown. Failure, an incomplete inventory or
stale/foreign source provides no learning or admission. This is an adaptive
QIK-VRT continuation plan, not a modification of GitHub's GraphQL schema.

The existing protected REST service exposes GET (plan/readback) and POST (one
fixed readiness mutation) at `/repos/ingolf-lohmann/qik-vrt/qikvrt/continuation`.
`QIKVRT_CONTINUATION_ENABLED=1` admits that route using the existing expiring
caller token, Owner binding and separate protected Authority credential resolver.
Required fields are `request_id`, `pull_request`, `expected_main_sha`,
`expected_head`, `expected_tree`, and `ci_run_id`; POST additionally requires
`schema=qikvrt-continuation-rest/v1` and literal `effect_accepted=true`. No query,
credential, provider URL, merge command or source patch is accepted from clients.
The original attempt journal persists intent before the GraphQL POST and keeps
unresolved effects fenced across request IDs and source changes. Native service
activation and end-to-end acceptance require their own readback; source tests
do not establish a deployed endpoint or guaranteed progress.

Fresh evidence advances the retained graph's execution frontier: verified
source/review/CI branches remain recorded, Draft selects the GraphQL fallback,
and independently verified readiness selects a fresh REST merge recheck. That
frontier drives the fixed readiness controller. Successful timings reorder only
the explicitly independent children after the mandatory test root. The sealed
REST package carries both the original Owner decision and artifact transport;
a cold `python -S` export test checks this closure without checkout or credentials.

Provider contract: https://docs.github.com/en/graphql/reference/pulls#markpullrequestreadyforreview
and https://docs.github.com/en/graphql/guides/forming-calls-with-graphql.

The existing CI producer now preserves `TESTED_SUBJECT.json` only after its
terminal full-test/fixpoint disposition. The small immutable Actions artifact
binds the original run/attempt and actual accepted HEAD/TREE. Consumers verify
its original metadata, archive size/digest and sole bounded JSON member. A run's
event HEAD is retained separately; a green event alone cannot accept either
that predecessor or another candidate. Historical runs without this artifact
remain useful timing observations but cannot authorize the new REST mutation.

If the original readiness ACK was lost, GET independently reports the current
exact readiness. An accepted POST on that same bound already-ready subject may
close the original journal using the independent readback, with zero new
GraphQL mutations. Its original response remains unchanged or explicitly absent;
the closing digest is labeled as readback and claims no mutation attribution.
