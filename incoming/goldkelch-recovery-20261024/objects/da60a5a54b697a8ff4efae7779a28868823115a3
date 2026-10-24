<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Lessons learned: components must form an executable, evidenced path

Owner: Ingolf Lohmann. Permanent application authorized in
`state/authorization/delegations/OWNER_CAPABILITY_PATH_LEARNING_20261004_V1.json`.
Implementation carrier: existing PR #441, not a replacement controller.
Machine policy: `policy/QIKVRT_RECURSIVE_HALTPOINT_V1.json#/capability_path_learning`.
Durable incident, path index and validation:
`state/work_units/CAPABILITY_PATH_LEARNING_20261004_V1.json`.

## Incident and epistemic status

The Owner reports approximately two or three days spent finding a usable
composition of already existing repository components. This is an attributed
estimate, not an instrumented duration or a measured speedup baseline. The
failure was not just a missing script: discovery, compatible interfaces,
actual integration permission, runtime credential delivery and effect readback
were not resolved as one path early enough. Source presence and a user admin
role were repeatedly mistaken for stronger operational predicates.

Historical anchors (never successor gate authority): PR447 comments
5981620880 (native administration job reached, credential inputs empty) and
PR441 comment 5981768732 (early capability preflight lesson). Admin run
36847427445, attempt 4, job 111468119495 reached the runner but not the ruleset
writer. PR435 comment 5981417380 is a CORRECTED record; its original incorrect
TREE/time/count assertions must not be reused. No global node absence or global
credential absence follows from one 403, 404 or empty job input.

## Permanent procedure: reuse the path, not just the pieces

Resolve the requested operation and exact subject first. Use the existing
path index and receipts before another broad repository/tool/plugin search.
For each candidate composition record source blob, input/output contracts,
owner authorization, callable tool, effective integration permission, runtime
credential delivery, exact target scope, node liveness, role/writer fencing,
idempotency and readback capability. User-role metadata remains separate.
Check the first missing predicate before attempting the effect. A REST adapter
can supply a missing method; it cannot manufacture authentication or elevate
the calling integration. Do not repeat generic Owner consent when already held.

The existing `tools/qikvrt_recursive_haltpoint.py` now exposes
`resolve_capability_routes(request)` and accepts `capability_routes` through its
existing `classify`/JSON CLI. It selects among at most 32 existing ordered
compositions of at most 16 steps, checks every interface join including initial
input and final output, and orders eligible paths by supplied measured latency
then stable ID. It performs NO network access, mutation, secret loading, job
start, review, merge or publication. It returns only `PLAN_CANDIDATE` and the
first reobservation/admission action. Proposed later steps have not run.
Existing observer calls without route evidence explicitly return
`UNOBSERVED_NOT_EXECUTION_AUTHORITY`, an `effect_permission=false` boundary and
the durable contract reference. Presence is not readiness.

The request context binds repository/HEAD/TREE, operation, semantic intent,
input/output contracts, principal and integration IDs, and credential/tool/role/
authorization configuration epochs. Epochs are non-secret change identifiers,
NOT token values, token hashes or credential fingerprints. Route evidence binds
the context, component source blobs, contracts and current policy digest.
Observations older than 60 seconds, future-dated observations and mismatched
bindings cannot select a route. The age bound is not a liveness guarantee.

Trusted read adapters must supply fresh non-secret receipts. The planner checks
bindings, not cryptographic truth of assertions or execution rights. Do not turn
an issue, comment, model output or arbitrary JSON into executable authority.
Every selected step still requires the existing executor's live admission,
review where applicable, final writer fence and fresh effect readback. Reobserve
and replan after EACH step; do not assume a proposed capability was produced.

Return negative observations to the existing durable ledger, keyed to the exact
context. Never cache effect authority. Within the unchanged observation window,
a known denial suppresses a duplicate attempt. Expiry requires observation, not
an automatic retry. Identity, tool, source, policy, role, authorization or
configuration change invalidates the old key and requires new evidence. Ledger
storage, single-writer CAS and notification de-duplication belong to the existing
carrier, not this pure function. The new function does not itself implement or
prove that live durable integration.

Preserve the same semantic message/intent ID on failover. An unknown effect or
already acknowledged intent is READBACK_ONLY, never a fresh upload/merge/replay.
A lost response is not proof that the write failed. Single-use publication
consumption and source-bound authorizations remain unchanged. A failed node
must not stop independent eligible lanes; selecting a surviving carrier is not
an unreviewed Authority-role takeover. If all supplied routes are blocked,
report the first concrete missing capability and its administrative owner once.
Do not infer that every possible route or every node is unavailable.

## Reuse index, not an invented deployment

- Mirror administrative effect: existing
  `.github/workflows/qikvrt_goldkelch_ruleset_authority_effect.yml` on Main.
  It targets its executing repository. Its observed attempt reached credential
  resolution only; it is not marked ready. Existing App/Token binding must be
  supplied through its protected administration channel.
- Authority-specific credential adapter: existing PR381,
  `tools/qikvrt_ruleset_admin_bridge.py`. Its pinned target is Authority, not
  automatically the Mirror. Reobserve its actual source and admission contract.
- Source recovery: existing PR444 fixed-target read carrier; installation
  enumeration does not substitute for a credential-attested source read.
- Promotion/reentry: existing PR435 and its native integrity materializer/tests.
  Branch continuation is distinct from independent review and Main integration.
- The returned `QIKVRT_Admin_REST_Adapter_Kandidat.zip` is an unattached local
  candidate recorded by digest, NOT a registered or credentialed live connector.
  Do not silently duplicate it or promote its local tests to a GitHub effect.

## Failure compensation acceptance (mandatory, not already proven)

Use the stable application endpoint and existing Universal Terminal/ledger
carrier. Specify the tolerated failure model, minimum surviving capabilities,
application timeout, recovery-time budget and data-loss budget BEFORE claiming
availability. Time detection, route selection, credential/admission, state replay
and end-to-end readback separately. The local selection target is <=1 second;
the application's end-to-end recovery deadline must be supplied per workload.
A fast planner is not a fast platform recovery, and no universal guarantee follows.

Fault-inject node/process loss, network partition, revoked permission, absent or
expired credential, stale routing cache, concurrent role takeover and lost ACK.
Verify no acknowledged state lost, no duplicated non-idempotent effect, single
fenced writer, correct session/identity continuity and fresh application-visible
readback. Test warm and cold paths, recovery after restart, and restored-node
rejoin. Reject split brain and stale role epochs even if a second node is live.
Record actual request failure rate, p50/p95/p99/max interruption, retries, queue
age, RTO and RPO against the declared workload budget. Do not suppress a real
outage merely to make the application appear healthy. Graceful degradation must
be truthful and scope-limited.

No ChatGPT task, client button, new timer or duplicate scheduler is introduced.
Use existing native events/continuation and store resume/negative-cache/intent
receipts in the existing durable carrier. Current code supplies bounded planning
and regression protection; native end-to-end failover remains an acceptance gate.

## Persistence and propagation

AGENTS -> this contract -> existing machine policy -> existing classifier ->
existing test module/CI -> owner/work-unit receipts -> reviewed node adoption.
Keep raw historical evidence and corrections attributable. A node adopts only a
reviewed exact source subject, validates locally, registers its capability/role
receipt, and passes its own fault-injection acceptance. A Mirror commit is not
proof of Authority synchronization, global rollout or invisibility to users.
Use the existing branch and integration gates; do not self-approve or weaken
protection to deploy this lesson. Failure of one independent publication lane
is not a global stop. Functional evidence does not prove phenomenal experience.
