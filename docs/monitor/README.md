# Repository-native Mesh monitor

The existing `docs/monitor` carrier now owns the public observation UI, Node 24
server, verified client replicas, signed webhook receiver and durable replay.
The UI and GitHub observation contract reuse the dashboard implemented for
Ingolf Lohmann; no ChatGPT process or schedule is required to serve this carrier.

`npm start` runs the monitor. `npm test` executes the clock/source regression
checks and the HTTP, storage, replay and concurrent-client acceptance tests.
The root `make test` includes these tests. No third-party Node package is needed.

Every node can deploy this same carrier with a distinct
`QIKVRT_MONITOR_NODE_ID`, `QIKVRT_MONITOR_SOURCE_REPOSITORY` and JSON
`QIKVRT_MONITOR_REPOSITORIES` list of public repositories. The list is an explicit
scope; a missing Authority cannot erase the independently observed Mirror.
Set `QIKVRT_MONITOR_STATE_DIR` to a persistent volume. One writer/replica owns a
state directory. The bounded two-node replication/read-failover path below is
implemented in this same server. Independent deployed-node failover remains an
open acceptance gate; local process tests do not assert it.

The configured host exposes `/mesh` for the whole configured Mesh, `/node` for
its local repository and `/client` for a client instance. Each browser tab has
its own identifier, read-only snapshot and ordered event replica. The client
checks node identity, implementation version, epoch, sequence and SHA-256 before
adopting data. `/api/node` exposes the binding; `/api/events?after=0` exposes the
ordered public-event journal. Resource-constrained clients can use these data
interfaces without running the UI. Native clients can reuse `client-replica.js`;
the same acceptance tests instantiate it in independent client contexts.

GitHub REST is used only for an initial/explicit observation or in response to
a received event. There is no periodic source polling and no browser-to-GitHub
fallback. `/api/stream` sends state and ordered deliveries over SSE. A 20-second
transport heartbeat does not renew GitHub observation timestamps. Ages advance
locally every second; stale source counters become unknown. Connection, source
freshness, client equality and workflow success remain distinct states.

Configure `QIKVRT_GITHUB_WEBHOOK_SECRET` and register the GitHub webhook endpoint
`/api/webhooks/github` for the configured public repositories. Signatures are
validated over the exact request bytes, and private repository payloads are
rejected. Repository-hook registration requires a GitHub capability that is
not exposed by the available connector. An installed secret, a published page,
or a connected SSE stream never substitutes for a real provider delivery.

## Losslessness acceptance boundary

For each accepted signed public webhook, the exact original bytes are stored
as base64, with their SHA-256, original delivery ID, consecutive event number
and chained record digest. This public event retention is specifically required
by the owner's 4 October 2026 no-data-loss instruction. Credentials and private
events are not stored. The journal is not truncated. The state file is written,
fsynced, atomically renamed and its directory fsynced before a positive durable
receipt or stream publication. A duplicate ID with different bytes is rejected.
Storage failure produces a failure response and preserves the previous state.

On disconnect/restart, `Last-Event-ID` or an explicit verified cursor causes
replay of every subsequent event. Clients independently verify original bytes,
consecutive numbering and the digest chain. A missing event is detected and
replayed; corruption or an unexplained epoch change is held visibly. A current
snapshot cannot substitute for the complete accepted event history.

The reproducible tests cover 32 accepted events delivered to four simultaneous
clients, restart/replay, duplicate/conflicting delivery, altered bytes,
signature rejection and storage failure. This is bounded software evidence.
It is not proof of infinite storage, physical hardware behavior, acceptance by
every product, independently deployed multi-node failover or GitHub-provider delivery. The complete
Mesh acceptance additionally requires provider registration, a fresh external
delivery, all required node/client/product deployments and fault injection on
those deployed instances. `TRANSPORT_ACK` is never `EFFECT_ACK_DONE`.

## Deterministic two-node replication and read failover

Use the same `server.mjs` on both nodes with separate durable state directories.
There is one observation/writer controller. The `replica` role never calls
GitHub, accepts webhooks or creates local observations; it imports the writer's
original journal records and serves the confirmed prefix through the existing
activity/events/SSE interfaces. The logical `node_id` and epoch remain those of
the writer. `serving_node_id` identifies the actual serving instance. A client
can reconnect to the replica URL with its existing verified epoch/cursor and
continue byte-exact replay without resetting its identity or digest chain.

| Setting | Writer (`primary`) | Read-only `replica` |
| --- | --- | --- |
| `QIKVRT_MONITOR_ROLE` | `primary` (default) | `replica` |
| `QIKVRT_MONITOR_NODE_ID` | Unique writer identity | Distinct replica identity |
| `QIKVRT_MONITOR_STATE_DIR` | Writer's own durable volume | Replica's own durable volume |
| `QIKVRT_MONITOR_REPLICA_URL` | Replica origin URL | Unset |
| `QIKVRT_MONITOR_REPLICA_NODE_ID` | Exact replica identity | Unset |
| `QIKVRT_MONITOR_PRIMARY_NODE_ID` | Unset | Exact writer identity |
| `QIKVRT_MONITOR_REPLICATION_SECRET` | Configured shared peer secret | Same peer secret |

Both nodes must use this protocol version and the same explicit public
repository scope. Use an authenticated private transport or HTTPS between
deployed nodes. Secrets remain environment configuration and are never
persisted in the journal. Each peer HMAC binds the method, path and exact body;
responses are independently HMAC-verified and bound to the expected node,
writer, epoch, cursor, snapshot digest and journal head. This authenticates
configured peers; it is not a consensus protocol or proof of Byzantine honesty.

The writer serializes updates in the existing controller, stores locally, reads
the signed replica head and sends the missing suffix in bounded batches. The
replica verifies every original payload SHA-256, consecutive event number,
previous digest, record digest, public scope and overlapping record before any
mutation. No event is renumbered, reserialized into a replacement record,
truncated or overwritten. The final snapshot checkpoint becomes visible only
when its complete event prefix is durably stored. Each batch uses the existing
fsync/file-rename/directory-fsync persistence path before returning its signed
head. The writer verifies the exact readback and fsyncs its confirmation before
the positive webhook receipt or event publication. Such a receipt has
`cross_node_durable=true`; the legacy unconfigured mode explicitly has `false`.

The protocol is carried by authenticated `GET /api/replication/head`, replica
`POST /api/replication/append`, and writer `POST /api/replication/sync` (empty
body). The exported `replicationSignature` defines their request signature;
the response uses method `RESPONSE` with the same path. Synchronization is
event-driven, at primary startup or explicitly requested, with no polling
controller. A lost response may leave a durably stored but unacknowledged event;
duplicate webhook retry or explicit sync reobserves the peer and preserves the
original record. Batches resume from the verified stored prefix after restart.
Until confirmation, the writer's public interfaces retain its last confirmed
prefix. An incomplete replica batch does not replace its last confirmed
snapshot. Conflicting history, epoch, unknown source or missing events fail
closed. A filesystem failure freezes further writes until restart revalidates
the disk state; it produces no positive durable receipt.

Failover here means **read/replay continuity of the verified checkpoint**.
The replica rejects writer promotion and webhook ingress. A client or existing
trusted routing layer can select its URL; this change does not add a second
controller, leader election or automatic write takeover. Write failover needs a
separate fencing/authority contract that prevents simultaneous writers. While
the replica is unavailable, the configured writer retains pending records and
withholds positive acceptance rather than silently degrading to one-node ACK.
The old unconfigured one-node mode remains available with its original scope.

Executable regressions include two separate local Node processes, writer
`SIGKILL`, 32 events replayed to four independent clients, interruption before
and after peer durability, timeout, duplicate retry, both-node restart, bounded
partial-batch recovery, gaps, valid conflicting replicas, invalid signatures,
private payloads, corrupt confirmations and source/replica storage failures.
These processes share the test host; they are not independent deployments or
failure domains. Storage capacity is finite, and the complete journal is still
held in memory and atomically rewritten. No global losslessness or
`EFFECT_ACK_DONE` follows. Actual separated deployments, fault injection and
fresh failover readback remain required and have not been performed here.

The existing Universal Terminal `/AI/` and Firefox/noVNC carrier remain the
integration path. Its shared operator session is not declared a per-user
isolated browser. This monitor does not change that session or its durable
TEMDD ledger.

## Immediate system health

Every instance displays the shared `health-projection.js` result above activity.
The same projection appears in `/api/node.health`: repository read failures,
stale observations, suspicious workflows, missing provider delivery, actual
runtime health, native compilation and client phase remain distinct checks.
Causes precede details. Failed checks produce `DEGRADED`; missing or expired
evidence produces `UNKNOWN`. Successful CI alone can never produce whole-system
`HEALTHY`. A received heartbeat updates transport evidence only. An event gap
cannot be cleared by receiving a newer snapshot.

`QIKVRT_NATIVE_STATE_FILE` can bind the existing local native-cache status to a
monitor. A missing/broken configured receipt is visible. A valid core cache is
not asserted to prove the complete live Transputer. Actual terminal runtime
health requires that carrier's current authenticated self-observation; until
that integration is present, the runtime check stays unknown.

## Native runtime and remaining carriers

The existing `tools/qikvrt_tool_cache.py native-prepare` path now compiles and
statically links the available C90 Effect-Ack conformance executable once for
each exact source/compiler/target binding. Root tests reuse this artifact and
rerun its 7,864,387 checks. `native-record`, `native-plan` and `native-optimize`
provide source-bound usage, measured amortization and bounded compilation of
registered hot layers. No higher terminal layer is reported compiled merely
because its planner or the JavaScript engine exists.

The missing Digital Twin Python reference model was restored byte-for-byte from
Mirror commit `04e5ee0f06ae33965b4041a7f4175ac3764e688b` (blob
`816d55781e53e0801390a96e8032c9fa2b327ae2`). Its REST tests now start from
independent states and are part of `make test`. This closes a concrete missing
dependency; it is still the existing reference simulation, not a Siemens tenant
connection, human Digital Twin, physical actuation or full C90 REST port.

`policy/QIKVRT_UNIVERSAL_TERMINAL_IMPLEMENTATION_GAPS_20261004.json` records the
owner's expanded scope and the actual unclosed carrier/acceptance dependencies.

## Exact repository-native deployment of the existing Railway service

`tools/qikvrt_mesh_monitor_deploy.py` and
`.github/workflows/qikvrt_mesh_monitor_deploy.yml` close the missing executor
path. They deploy only the existing `mesh-monitor` service
`dc3773e0-d057-4779-b9c1-9ca0f2074f69` in the existing production environment.
The immutable runtime subject is **674aa35ec0659119a19cda66b88f32050e34f105**,
tree **5100b66a299ded9ecb64622d2d36a5a77ef1f85d**, root `/docs/monitor`.
The executor successor is a separate subject: updating its branch never changes
that runtime pin or transfers predecessor checks to the executor.

The fixed contract is
`state/deployments/MESH_MONITOR_RAILWAY_EXACT_674aa35.json`. It retains `npm test`,
`npm start`, `/health`, the 60-second healthcheck, restart **ALWAYS** with the
existing max-retries value 3, one `iad` replica and no sleeping. Only the already
staged `mirror-monitor-events` volume is used at `/var/lib/qikvrt/monitor`.
There is no new service, alternative server implementation, upload of a mutable
working directory, or change to CODEOWNERS/review/rulesets.

The owner authorized this bounded deployment. The push event on the existing
candidate branch starts the executor without a ChatGPT client, schedule or
interactive Railway confirmation. Future protected-branch integration remains
a separate governed effect. This change does not merge itself or assert native
review success. The workflow is not installed on `main` merely by existing in
a draft candidate.

The server-side runner supplies **one** already authorized credential:
`RAILWAY_TOKEN` (project token, `Project-Access-Token` header) or
`RAILWAY_API_TOKEN` (account/workspace token, bearer header). No token is created,
extracted from the connector, put in an argument/cache/repository, or printed.
An absent credential produces `HOLD_RAILWAY_SERVER_CREDENTIAL_UNAVAILABLE`
before a network request. Permission, schema, state and drift failures remain
HOLD; API bodies and variable values never become logs or receipts.

The controller freshly validates the project, environment, service, source,
runtime settings, variables and volume. It accepts only reviewed patch
`9d4860c4-5003-48ef-a07f-d383f303b539`, limited to that service and volume;
unrelated or destructive staged fields stop it. It acquires the create-only
Git-Data ref `refs/tags/qikvrt-monitor-deploy/674aa35ec0659119a19cda66b88f32050e34f105`
using the runner's `GITHUB_TOKEN`, reobserves immediately and makes at most one
Railway mutation. The claim is retained on timeout, API failure or runner loss.
Subsequent runners can observe an in-flight deploy or verify the exact live
result; they cannot blindly repeat the mutation. A failed/ambiguous claim needs
authoritative provider reobservation and a separately governed recovery, not
deletion or force-update by this controller.

`environmentPatchCommitStaged` has no expected-patch-ID/CAS argument in the
primary API schema. The double read, strict patch allowlist, one-shot claim and
workflow concurrency protect cooperating runners. They cannot exclude a
privileged external writer changing staging after the last observation. That
remaining platform concurrency limit is explicit; no stronger atomicity is
claimed. The existing patch commit performs the deployment; it is never
followed by an extra redeploy. If settings are already live and no patch remains,
the only allowed deploy request is `serviceInstanceDeployV2` with the explicit
runtime commit, after the same one-shot claim.

`tools/qikvrt_mesh_monitor_readback.mjs` runs in a separate process without the
deployment credentials. It fetches `/health`, `/api/node`, both client assets,
the snapshot and the complete bounded journal, checks exact head/tree/version
and artifact hashes, and applies the original snapshot/event bytes through the
existing `client-replica.js`. A final node read must match its epoch, sequence,
digest and journal head. Drift, altered bytes, missing health structure or the
old public carrier fail closed. Application health `UNKNOWN`/`DEGRADED` is
retained rather than becoming whole-system `HEALTHY` through deployment success.

After one admitted dispatch the workflow uses `--wait-readback`: up to 36
read-only observations started within a 180-second window, with at most five
seconds between them. The final request/client check keeps its existing 30/90
second bounds and may finish after that window; the job has a ten-minute bound.
It verifies the public runtime and independent client in the same server-side
execution, without depending on another platform event. Permission, target and
configuration drift stop observation immediately; timeout retains the dispatch
receipt and claim as HOLD. There is no mutation retry. A later
`deployment_status` success event is also readback-only. The workflow
persists a safe receipt, `AI_PROGRESS.json` and `AI_STATUS.md` as Action artifacts
and a human step summary. `PUBLIC_RUNTIME_READBACK_VERIFIED` is bounded to this
carrier/client check; provider webhook registration/delivery, live restart fault
injection and cross-node failover remain independent gates. `EFFECT_ACK_DONE`
and general Mesh completion remain false.

Local checks use the existing Python/Node toolchain, no Railway CLI:

```sh
python3 -B -m unittest -v tests.test_mesh_monitor_deploy
node --test tests/mesh_monitor_readback.test.mjs
make repository-monitor-test
```

The exact remaining capability is recorded in
`runtime/capabilities/MESH_MONITOR_RAILWAY_SERVER_DEPLOYMENT_20261004.json` and
the provenance work unit
`state/work_units/MESH_MONITOR_REPOSITORY_DEPLOYMENT_20261004.json`.
