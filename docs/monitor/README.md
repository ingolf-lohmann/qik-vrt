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
state directory. Independent node deployment and cross-node journal replication
are separate acceptance gates; this implementation does not assert them.

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
every product, multi-node replication or GitHub-provider delivery. The complete
Mesh acceptance additionally requires provider registration, a fresh external
delivery, all required node/client/product deployments and fault injection on
those deployed instances. `TRANSPORT_ACK` is never `EFFECT_ACK_DONE`.

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
