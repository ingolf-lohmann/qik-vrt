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

## Standalone S1 packaging

This successor imports this carrier from PR #456, exact donor commit
`14fc43ec8263d7d278c54975ac0338130e0de716`. The unrelated native-cache,
Digital Twin model restoration and Railway deployment executor from that PR
are outside this selective import. Their historical checks are not transferred.

The current package, source/runtime pins, volume/OS-lock contract, local source
adapter, authentication boundaries and independent readback are documented in
[`runtime/self-host/README.md`](../../runtime/self-host/README.md).
`self-host.mjs` configures this same `createMonitor` and listener. With adapter
`none` the activity source is the immutable exported repository; GitHub ingress
and live detail routes are disabled and Railway transport is rejected. Existing
server behavior is retained for its original entrypoint and explicit adapters.
The package's public terminal is read-only. The historical native TEMDD and
Firefox/noVNC sources are now recovered with original blob provenance; see
`runtime/self-host/RECOVERED_TERMINAL.md`. Independent host/storage/HTTPS
admission remains a separate HOLD condition.
No public deployment, complete S1, native terminal actuation or EFFECT_ACK_DONE
is claimed.

## RaumzeitTerminal: personal entry in the existing React client

The self-host listener serves the same `index-react.html` at `/`, `/index.html`
and `/client`. The first view explains a personal browser assistant for
resuming research/development work with sources, decisions and authorizations
across sessions. `/mesh` and `/node` retain the monitor, its errors and fresh
readback boundaries. This is an implementation-side root route; it establishes
no domain control or public deployment of `raumzeitterminal.de`.

The primary action opens the existing read-only SQLite export panel. File
opening does not authenticate its owner or resume a runtime. The explicitly
opened setup form uses the three existing Personal-Origin questions: attribution
identifier, personal-origin configuration and evidence retention. Defaults are
local-only and metadata-only. Editing invalidates the preview; credential URLs,
queries and fragments are refused. Fields stay in React memory; no API write,
account, remote origin, transcript or durable personal store is created. Reload
clears the preview. Existing monitor instance metadata retains its behavior.
Returning file readers are not automatically asked the onboarding questions.
Authenticated binding, reuse of established answers and actual personal task
resumption remain product targets.

Dueck's six questions form the editorial acceptance checklist inside the same
React terminal:

| Question | Visible answer and evidence limit |
| --- | --- |
| Concrete use case | Continue an interrupted research/development task; persistent sources, decisions and permissions are a product target. |
| Actual users/buyers | Target groups are named; a customer or buyer base is not established by available evidence. |
| Updates | Ingolf Lohmann holds Product/Code responsibility; OpenAI Codex contributes implementation. Changes are versioned and checked; no interval or support SLA is promised. |
| Later costs | No binding price list; commercial use requires a separate written license; operating/model/support costs remain unpriced. |
| Exact capability | Local export reading, technical readbacks and a transient setup preview; component evidence does not establish the complete browser assistant. |
| Measurable advantage | No measured customer advantage; proposed equal-task comparison records resumption time, repeated context and confirmed effects without duplication. |

The component link resolves historical native run `37444676087` on #474 HEAD
`a3a19ed041900fbffb2aa38bb4c51fdffb0f7751`, TREE
`1b96726a258cd5efdf8cc0512013d245328167e5`. This exact-source SQLite/Owner-REST
and desktop-origin evidence never supplies a transferred check for new UI bytes.
Public HTTPS, actual Android/iOS, per-user authentication, automatic context
resumption, customer benefit and EFFECT_ACK_DONE remain open.

The existing desktop Origin harness adds actual React interaction controls with
unavailable telemetry: primary file opening without onboarding, three-question
preview, credential-URL refusal, no added storage or personal transport, six
bounded product answers, preview clearing on reload, monitor/error navigation
and narrow/desktop layout. The existing S1 lane retains original persistence
controls and adds a separate exact-source UI witness and screenshots to its
artifact. A narrow desktop viewport is not actual mobile-device acceptance.
Editorial and automated checks are not an independent usability study.
# React Authority-404 source successor

`mesh-react.js` renders repository-source and terminal REST failures with state,
impact, observed status and uncertainty, responsible actor, next REST step and
evidenced repair progress. Original diagnostics remain selectable JSON in native
details. The exact #468 observation is a replay input; its test results and the
Storage/Origin stack are not evidence for this successor. Reproduce with
`node --test docs/monitor/react-feedback.test.mjs`; the existing
`repository-monitor-test` target includes it. See
[`evidence/monitor-feedback/react/README.md`](../../evidence/monitor-feedback/react/README.md)
for the preserved #476 baseline and fresh comparison. Human comprehension is
`NOT_MEASURED`; main integration and public delivery remain separate.
