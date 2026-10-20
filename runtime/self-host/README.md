<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# S1 standalone node package, version 1.12.0

Every current and future repository node, including Authority and Mirror, must
implement and run both the universal Transputer and the universal Terminal.
The normative bus obligations are in `MESH_ACTIVATION.json#/required_node_runtime`.
There are no role exemptions. A reference-only diagnostic profile does not admit
a node to the productive Mesh.

`python3 -B tools/qikvrt_self_host.py mesh-contract` checks the role-independent
contract and the exact packaged source carriers. The existing `pack` and `verify`
paths invoke the same gate and bind its contract digest in the package manifest.
Missing either component, weakened effect invariants, unsafe partition behavior,
or an incomplete fault model blocks package admission. This source gate does
not assert that a node is deployed or that failover has executed.

Fault acceptance must exercise process crash, node loss, network partition,
provider loss, lost Effect-Ack, simultaneous takeover, stale writer and rejoin on
the real public workload. It must retain the same session/Work Unit, original
event bytes and confirmed effects, with zero acknowledged-effect loss and zero
duplicate irreversible effects. A takeover needs authenticated journal catch-up
and a fence that the effect carrier enforces against the previous writer; an
unknown outcome permits readback only. One provider hosting multiple repositories
does not establish independence from provider loss.

Ordinarily unnoticed recovery is a measured acceptance objective. Declare the
failure bound, topology, workload and numerical RTO/interruption SLO first;
record p50/p95/p99/maximum interruption, failed requests, retries and queue age.
If a safe quorum is absent, preserve confirmed reads and hold writes visibly.
Do not hide an unverified effect behind a successful response. Necessary
authorized operations require documented REST/API adapters.

The existing monitor replica protects a confirmed observation prefix. It does
not replicate the native TEMDD effect ledger or implement writer takeover. The
current S1 native terminal/Transputer remains a single-node carrier; live
multi-node effect replication, write fencing and transparent recovery are open
implementation/host-acceptance work. The neuronal description is an architecture
analogy governed by the existing evidence/adaptation policy.

## Existing S1 host and stopped-container recovery

The same protected `container_deploy` job now preserves a read-only host
preflight when image/signing production fails after the full source test.
It reuses `container-host-preflight`, the original binding validator,
production governance and mutually authenticated Engine. It records credential
presence and the first admission boundary without credential or private origin
values; an admitted host receives exactly one `GET /v1.45/info`. The daemon ID
must match the independently pinned binding. No image, container, DNS, key or
volume is changed. Missing admission is persisted as HOLD, not deployment.
The job retains its existing enable flag and protected production environment.
The deployment step still requires successful container and publication jobs;
public acceptance also requires successful publication. Read-only diagnosis
does not waive signing, exact-source, review, protection or deployment gates.

The existing `container-deploy` consumer in `qikvrt_ci.yml` supports initial
create-only delivery and recovery of the exact same stopped S1 container. It
continues to require protected exact Main, independent merged-PR review, the
protected `qikvrt-production` environment and the admitted signed Firefox
image. A source test or a Railway service inventory establishes none of those
production predicates.

The private connection is `vars.QIKVRT_LINUX_HOST_BINDING_JSON`, independently
pinned by `vars.QIKVRT_LINUX_HOST_BINDING_SHA256`, and the existing protected
`QIKVRT_LINUX_HOST_CA`, `QIKVRT_LINUX_HOST_CERT`, `QIKVRT_LINUX_HOST_KEY` secrets.
`vars.QIKVRT_CONTAINER_DEPLOY_ENABLED` admits this existing consumer. The binding
must supply the real mTLS Docker API origin, daemon ID, container name, existing
state volume, private configuration directory and digest, node ID, manifest
digest, loopback routing port, exact source HEAD/TREE and image digest. The
checked-in `LINUX_HOST_BINDING.example.json` remains a template; do not fill its
unknown fields with invented host values or export credentials into Git.

Recovery first checks the authenticated daemon and owner volume, the same
container/image/binding labels, runtime user/command, security and loopback
settings, `unless-stopped` policy, and exactly the existing writable state
volume plus read-only configuration mount. It verifies the pinned image,
configuration and package-manifest bytes, then reobserves the container before
one `POST /v1.45/containers/{id}/start`. A concurrent successful start is NOOP.
An ambiguous response is resolved by GET, with no second start. There is no
container replacement, mount update, profile export, profile initialization or
credential operation in this recovery consumer. Drift remains HOLD and requires
the existing separately admitted migration path. In particular, Railway's
older `/var/lib/qikvrt` profile layout is not silently reinterpreted as the S1
`/var/lib/qikvrt/node` layout.

`EXACT_EXISTING_CONTAINER_RESUMED_PENDING_PUBLIC_ACCEPTANCE` establishes only
the observed container start and health in that invocation. Independent public
Effect-Acknowledgement and Firefox readback, actual private session acceptance,
profile persistence and automatic restart remain distinct host obligations.
A running Firefox window is not an authenticated provider session. Local Engine
fixtures verify these branches without claiming any real host or login effect.

## Irreversible Authority succession

Ingolf Lohmann's requirement of 2026-10-16 is normative in
`policy/CANONICAL_UPSTREAM_REMOTE_V1.json#/authority_succession`.
An Authority whose contact-dependent mandate has expired or has been
authoritatively revoked loses it irreversibly. A qualified successor Mirror
becomes Authority and retains that role when the predecessor returns. The
predecessor cannot regain Authority through reconnection, an old configured
role, or another role projection; it may rejoin only as a fenced, authenticated,
caught-up Mirror. The same loss rule applies if the successor later fails.
Goldkelch/qik-vrt is retained as the retired Authority identity; the current
Owner-bound Authority remains ingolf-lohmann/qik-vrt.

A single failed HTTP GET or an observer's loss of visibility is insufficient
revocation evidence. Live takeover must bind the qualified contact-loss/lease
event, a safe quorum, original journal catch-up and a strictly newer fencing
epoch. The effect carrier must reject the old writer before successor effects;
absence of a safe quorum holds writes and preserves confirmed reads. Test
simultaneous takeover and predecessor rejoin without failback on the real
workload. Do not turn an observer's uncertainty into two competing writers.

`deployment-roles`, `mesh-contract`, `pack` and `verify` now reject a policy
that restores automatic failback, omits the retired identity, permits unsafe
promotion, or promotes a retired Authority. These are source/package admission
checks. They neither execute a live election nor establish native fencing,
cross-node effect replication, measured availability or a universal survival
theorem; the existing live-acceptance gaps remain open.

### Reproducible succession assurance (2026-10-16)

The existing `tools/qikvrt_self_host.py` now also contains
`AuthoritySuccessionModel`. It is an explicitly local reference model, using
SQLite FULL-synchronous transactions for modeled votes, an epoch/owner fence,
irreversible retirement and an original-byte effect journal. No product
command invokes it. It installs no election service or production writer.
The existing `make workflow-executor-mesh-contract` runs its dedicated tests;
the ordinary S1 test target also discovers them.

```
python3 -B -m unittest -v tests.test_self_host.AuthoritySuccessionModelTests
```

Seven separately named tests cover the seven normative acceptance cases:

| Policy case | Test suffix | Checked model transition |
| --- | --- | --- |
| CONTACT_LOSS_REVOCATION | contact_loss_revocation | A's quorum-bound lease expires; A is permanently retired before any later write |
| FENCED_MIRROR_TAKEOVER | fenced_mirror_takeover_preserves_originals_and_lost_ack | caught-up B, quorum and expected-epoch CAS install epoch 2; A's token is rejected; original bytes and one effect survive replay |
| FORMER_AUTHORITY_REJOIN_WITHOUT_FAILBACK | former_authority_rejoin_without_failback | authenticated exact-head catch-up admits A as Mirror; B remains Authority |
| CONCURRENT_TAKEOVER | concurrent_takeover_persistent_votes_intersect | persistent per-voter single choice rejects two certificates for one epoch |
| NO_QUORUM_HOLD | no_quorum_hold_preserves_confirmed_reads | all singleton partitions reject writes; confirmed local prefix remains readable |
| RETIRED_AUTHORITY_REPROMOTION_REJECTION | retired_authority_repromotion_rejected_at_every_new_epoch | retired A stays ineligible even with a higher epoch |
| SUCCESSOR_CONTACT_LOSS | successor_contact_loss_applies_same_rule | B also retires on expiry; qualified C takes epoch 3; A and B stay fenced |

Additional controls exercise two concurrent local processes sharing the same
atomic carrier, process exit during an uncommitted SQLite transaction, restart,
stale journals, higher ballot promises, duplicate/unknown voters, unverified
revocation, lease renewal and clock regression. These are simulated faults and
local process/storage tests, never independent network-node acceptance.

The live v2 `Hardware/AuthorityMirrorWitness.lean` extends the existing witness
with a separate `AuthoritySuccession` namespace; its top-level import already
builds this module. The existing hardware axiom audit and ordinary manuscript
audit include the extension. Frozen published sources and historical theorem
statements are unchanged. The formal model proves majority intersection and
same-epoch certificate uniqueness for a fixed three-voter electorate,
monotone fencing epochs, invariant preservation over finite transition runs,
persistent retirement, and conditional one-step successor progress. Python
uses an arbitrary fixed finite electorate; no formal Python/SQLite refinement
or dynamic-membership proof is claimed.

The safety statement is **at most one effective writer per shared serialized
effect carrier**, not at most one process believing itself leader. Every effect
must atomically check exact owner, current epoch, an unexpired mandate and a
safe distinct-member quorum in the same serialization domain as its commit.
Fencing must cover every irreversible sink; a check before an unfenced later
effect has a race. Authenticated voters must retain one choice per epoch across
restarts, the complete retirement set and a non-rollback epoch high-water mark.
A successor must bind the original confirmed journal before admission.

Both Lean and Python contain a constructive split-brain counterexample for two
independent, unsynchronized effect carriers. Increasing a token at only one
carrier, GitHub ref CAS, local SQLite exclusivity or observing a missing peer
cannot close this global coverage obligation. The model's supplied voters,
authenticated-certificate booleans and logical time are assumptions, not real
signatures or calibrated independent clocks. SQLite tests cover process crash;
they do not qualify power loss, disk rollback or adversarial snapshot restore.

Safety deliberately permits no progress. Progress additionally needs an
available non-equivocating majority, an eligible caught-up successor, reachable
enforced carriers, valid authenticated identity and eventually adequate message
delivery/scheduling. A two-voter electorate cannot write safely after losing
one voter. Irreversible retirement can exhaust a finite set of eligible nodes;
ongoing survival then requires separately authorized safe membership expansion.
No guaranteed RTO, asynchronous failure-detector completeness, Byzantine
tolerance, consensus termination or indefinite availability is proved.

The seven **live** cases remain OPEN until original independent execution
receipts bind the real node identities, fixed/joint membership, quorum rules,
lease clock/error bounds, persistent ballots/epochs/retirement, every effect
carrier, workload and original replicated journal. No current HTTP observer
establishes these facts. Native deployment, production takeover, public-domain
delivery and EFFECT_ACK_DONE remain separate unfulfilled acceptances.

Primary algorithmic context (not evidence of QIK-VRT deployment):
Diego Ongaro and John Ousterhout, *In Search of an Understandable Consensus
Algorithm*, https://raft.github.io/raft.pdf . The existing research entry point
remains Ingolf Lohmann, *Das Universum als Round Trip*,
https://zenodo.org/records/21888130 (DOI 10.5281/zenodo.21888130).
This operational candidate is not a new archived scientific publication.

## Local repository copy, cache and stable-idle work batch

Every node has the same local cache obligations in
`MESH_ACTIVATION.json#/required_node_runtime/local_repository_cache`.
The existing launcher now provides a content-addressed private copy of explicitly
selected, regular, committed repository files and original exportable work
instructions. Work Unit IDs, source HEAD/TREE and instruction bytes are retained.
Local candidate updates are consolidated into one final file inventory; no
native effect event or effect acknowledgement enters this deferred path.

This reuses the existing private snapshot/fsync/OS-lock helpers and the existing
MonitorStore/listener. `snapshot-state` requires stopped native writers and copies
whole private runtime stores; it cannot stage exportable work proposals during
local development. The added cache/outbox is therefore a bounded extension, not
another native ledger, scheduler or executor. It does not create Git commits.

Create a private 0600 work request outside the selected checkout, with:

```json
{"schema":"qikvrt-repository-work-request/v1","scope":"OWNER_SELECTED_EXPORTABLE_PROPOSAL_BYTES",
 "repository":"ingolf-lohmann/qik-vrt","node_id":"local:admitted-node",
 "paths":["AI","README.md"],"work_unit_id":"owner-work:unique-id",
 "instructions_file":"/private/owner/exportable-instructions.txt"}
```

The cache parent is owner-only 0700 and separate from the checkout. The instruction
file must be explicitly exportable and 0600. Run `stage` for each distinct local
Work Unit, then validate the final exact local state; no cloud request occurs
during staging:

```sh
python3 -B tools/qikvrt_self_host.py mesh-cache-stage --root /private/local-repo \
  --mesh-cache /private/cache/local-work --work-request /private/owner/work.json
python3 -B tools/qikvrt_self_host.py mesh-cache-idle \
  --mesh-cache /private/cache/local-work --work-request /private/owner/work.json \
  --validation-command python3 -B -m unittest tests.test_self_host
python3 -B tools/qikvrt_self_host.py mesh-cache-send \
  --mesh-cache /private/cache/local-work --work-request /private/owner/work.json \
  --peer /private/owner/cloud-peer.json
python3 -B tools/qikvrt_self_host.py mesh-cache-check \
  --mesh-cache /private/cache/local-work --work-request /private/owner/work.json \
  --peer /private/owner/cloud-peer.json
```

### Commission the original host and retain operating evidence

Source tests and a running listener do not establish a working Mirror return
path. No peer is admitted by default. Start the existing admitted S1 service on
the original owner-controlled host with an explicitly provisioned private peer
entry; preserve its existing state, supervisor and protected credential binding.
Railway or another managed replacement is not a prerequisite.

The receiver's private config uses `mesh_work_peers` entries with `node_id`,
`repository` and `secret_file`. The sender's private `--peer` document declares
the receiver's `url`, `node_id`, `source_head`, `source_tree` and `secret_file`.
Both protected key files must contain the same admitted key. Do not put these
files or keys in Git, work instructions, publication archives or chat. Verify
the actual node identities and source pins independently before admitting them.

Stage an actual, explicitly exportable committed Work Unit, execute its real
validation, send the frozen batch, then run `mesh-cache-check` on the sender.
`send` atomically retains the authenticated GET receipt, its original response
bytes and response signature in the existing private `CACHE_STATE.json`, alongside
`last_ack`; a successful acknowledgement is therefore auditable after restart.
No second ledger or scheduler is created. Existing cache states remain readable.
An older acknowledged batch can be checked remotely, but absence of its retained
sender response is reported as `sender_receipt_durable=false`, never fabricated.

`check` sends only one authenticated GET with a fresh unpredictable challenge to
`/api/mesh-work/readback/<batch_id>/<challenge>`. The existing receiver reloads
and validates its durable original inbox, compares it with the running state,
and returns the challenge, current source identity and exact stored receipt.
The sender verifies the signature, challenge, current receiver pins, batch and
receipt digest, and any retained original sender witness. It never POSTs,
executes proposals, changes the cache or repairs a lost receiver inbox.

Restart the same admitted receiver service and reopen the same sender cache;
repeat `mesh-cache-check` and retain both results with the host acceptance.
Recheck after changes to source, peer admission, keys or storage. Missing peers,
missing receipts, stale source pins, disk divergence, replayed readbacks and
unavailable routes remain HOLD; resolve them causally before another send.
A changed key needs its protected historical-verification/rotation procedure;
an old witness is not silently relabeled with the new key.

`/api/node` exposes only aggregate proposal readiness: `NO_PEERS_ADMITTED`,
`PEER_BATCH_REQUIRED`, `PEER_BATCHES_DURABLE` or a readback HOLD. Credentials and
proposal bodies remain private. The existing independent public verifier refuses
acceptance of standalone `raumzeitterminal.de` when any admitted peer lacks a
durable batch for the current receiver source, or no peer is admitted. This gate
does not prevent local startup needed for commissioning. Private challenged
readback, actual host restart and public HTTPS acceptance are separate duties.
These checks cover proposal continuity; native-effect replication, quorum/fencing,
zero duplicate irreversible effects and numerical recovery SLO remain separate.

The explicit validation command has a 60-second bound; a timeout/failure holds
the batch. The finite idle proof means: cache writer lock held; clean local
commit; selected file bytes match its Git blobs; unchanged HEAD/TREE/inventory
before and after an executed zero-exit validation. `IDLE_STABLE_VALIDATED` is the
same state predicate for every batch. It does not prove that unregistered jobs,
the native runtime or every node are idle. Whole-node admission requires a
complete work/executor inventory and an independent workload-bound proof.

The private peer declaration contains `url`, `node_id`, `source_head`,
`source_tree` and `secret_file`; source pins identify the admitted receiver
package, and the 0600 key is a distinct 32–256 byte ASCII peer key. Only HTTPS
or loopback HTTP is permitted, with no redirects. Receiver S1 configuration may
declare `mesh_work_peers`, each containing `node_id`, `repository`, `secret_file`.
No peer is admitted by default. Credentials never enter cached objects or the
wire batch. Selection grants no publication right for personal/private state.

The existing listener accepts HMAC-bound `POST /api/mesh-work/batch` and a
separate authenticated `GET /api/mesh-work/receipt/<batch_id>`. Original bytes,
the idle/validation binding, epoch, prior accepted batch, revision and file
inventory are checked before one fsync/rename transaction. Received instruction
bytes remain proposals and are not executed. This is a configured-peer
attestation and exact-byte delivery receipt, not an independent rerun of the
sender's validation or a native Effect-Ack.

Only not-yet-acknowledged content objects cross the network; repeated bytes are
deduplicated without dropping Work Units. A lost response retains the exact
outbox; retry queries the authoritative receipt before a further POST. A stale
parallel copy, changed idle input, invalid signature/digest, full store or
unavailable receiver holds work. A pending batch blocks additional cache
staging until readback resolves it. Source files and cached/outbox originals
are retained. Protocol bounds are 16 MiB per batch, 1024 Work Units and 8192
selected files; the receiver holds at 64 MiB of proposal state rather than
silently evicting an accepted receipt. There is no autonomous garbage collector.

Tests compare actual loopback payload requests and bytes for individually sent
updates and a single batch, and cover cache reuse, restart, lost responses,
partitions, corrupt bytes/receipts and competing copies. Fewer transferred
bytes/requests do not establish a numerical user-latency speedup, optimal global
scheduling, public independent-node deployment or live Mesh transparency.
The existing native ledger replication-before-Effect-Ack requirement is unchanged.

The same S1 listener now serves the static React document at `/mesh`, `/node`
and `/client`. Node selection is `/node?repository=<declared-repository>`.
It consumes the existing hash-checked client replica and event stream, refreshes
on opening, visibility/online recovery and explicit readback, and displays the
original observation timestamp even after disconnection. React, React DOM and
Scheduler are frozen with complete MIT notices in `REACT_LOCK.json`; no CDN,
npm installation or framework server is needed. The source document is preserved
byte-for-byte at `/scheibenhard-original.html`. This adds no new monitor, ledger,
executor or public mutation route.

The complete public acceptance order is [MESH_ACTIVATION.json](MESH_ACTIVATION.json).
Candidate CI builds/verifies this document inside the existing S1 lane. Actual
hosting-platform CI is not instantiated: its own-host principal/executor is
unavailable. The contract requires a current complete node/terminal inventory,
one fresh native Transputer ping and authenticated receipt at every terminal,
with shared logical identity, measured receive window and clock uncertainty.
An HTTP health response, SSE connection or local React test cannot close it.
Own-host public deployment, all-node delivery and the first all-terminal round
trip remain OPEN. They are not replaced by the separately hosted observer Site.

This package reuses the existing Node monitor and reference terminal. It now
also includes the recovered original productive TEMDD ledger/Unix daemon and
Firefox/noVNC deployment sources from snapshot
`c6a53e200c4835a4f871d8496feb81d953610831`. Exact source provenance and the new
portable S1 adapter are described in [RECOVERED_TERMINAL.md](RECOVERED_TERMINAL.md).
The recovered originals remain byte-identical. No second ledger or executor is
introduced. Select `temdd` (the example default), `firefox`, or the compatibility
`reference` profile explicitly. Missing profile retains the existing reference
behavior for prior private configurations.
Linux x86-64/ARM64 operators provision Node 24.x and Python 3.12.x. The builder
freezes their actual patch versions, architectures and executable SHA-256;
startup rejects any substitution. Python's renderer pin remains unchanged.

`tools/bootstrap-runtime.sh --check-only --profile self-host` performs no
GitHub CLI check or installation. Its default adapter is `none`. Selecting
`--adapter github` retains the locked GitHub CLI bootstrap. Every pre-existing
profile still requires that bootstrap and refuses `--adapter none`.
The PowerShell checker carries the same adapter selection; the actual service
launcher is Linux-only. The profile checker is readiness, not deployment proof.

## Bounded transfer of an existing dependency image

The existing Firefox-158 dependency ZIP can exceed the connector's 512-MiB
artifact limit even though native Actions can read it. The existing CI exporter
therefore also preserves up to four separate 256-MiB payloads and a small
`DELIVERY.json`/`PARTS.json` artifact. Each part has its own native artifact ID,
ZIP digest and original-byte digest. The workflow independently downloads the
parts and restores the original pinned archive before publishing the delivery
receipt. Existing single-artifact consumers remain compatible.

Once that exact delivery is pinned in the work unit, unchanged dependency and
transport code reuse the small metadata plus fresh GET-only artifact-availability
checks. They download no large archive and publish no duplicate parts. Expired,
changed or denied metadata holds reuse; it never grants another signing attempt.

The existing S1 entrypoint exposes the same bounded file operations:

```sh
python3 -B tools/qikvrt_self_host.py container-artifact-split \
  --carrier-archive /private/image.docker.tar.gz \
  --transport-sha256 <original-archive-pin> --output /private/parts \
  --receipt /private/split.json
python3 -B tools/qikvrt_self_host.py container-artifact-join \
  --root /private/delivered-parts --output /private/restored-image.docker.tar.gz \
  --manifest-sha256 <PARTS.json-pin> --transport-sha256 <original-archive-pin> \
  --receipt /private/restore.json
```

Download and verify each ZIP against `DELIVERY.json`, place only its declared
part beside the pinned `PARTS.json`, then reassemble. The join refuses missing,
corrupt, reordered, symlinked or path-changing parts and never overwrites an
existing destination. The restored file is independently read back. Neither
operation imports or runs an image, signs or activates an extension, authorizes
a deployment, migrates a private profile, or transfers predecessor acceptance.
The original image source and the transport-exporter source remain separate.
The existing signing, governance, private host and exact-domain gates remain.

## Authenticated Owner REST input

The native `temdd` and `firefox` profiles now provide direct HTTP input through
the original TEMDD ledger, including when `unix_ingress` is `false`. No Unix
socket, browser proxy, remote desktop, Git installation or provider credential
is required by this path. The separate Unix adapter defaults to enabled for
existing configurations and retains its original mode/UID boundary.

Provision a distinct private 0600 ASCII bearer key (32–256 characters) for each
explicit principal, outside the package and monolith. The read-only terminal key
cannot authorize Owner REST. Add the following to the private, source-bound
configuration; permission names grant only the stated local storage operation:

```json
{"unix_ingress":false,"owner_rest_grants":[
 {"principal":"owner:ingolf-lohmann","token_file":"/etc/qikvrt/owner-rest.token",
  "permissions":["prepare","commit","readback"]}
]}
```

No grants means the REST writer is disabled. Each request revalidates secret
file ownership/mode and current bearer bytes. Rotation revokes the previous key
immediately. A changed configuration/source/volume binding holds the runtime;
it never widens a live grant. Principal authentication is a provisioned capability
binding, not biometric proof of a natural person. TLS/public ingress and mobile
acceptance require their own deployment evidence. The existing terminal-port
listener stays at `127.0.0.1`; the public monitor exposes no owner input route.

Send `Authorization: Bearer <private-key>` and `QIKVRT-Owner: <principal>`.
Write requests use `Content-Type: application/json` and this exact envelope:

```json
{"schema":"qikvrt_owner_rest_input_v1","request_id":"owner:unique-work-unit",
 "subject":{"repository":"ingolf-lohmann/qik-vrt","pr":469,
            "head":"EXACT_HEAD","tree":"EXACT_TREE"},
 "input":{"schema":"qikvrt_terminal_input_v1","text":"Exact owner input"}}
```

The subject must match the running package/configuration, including its PR.
`input` uses the existing bounded text contract (4096 characters); audio/video
remain explicitly unadmitted. Request bodies are at most 32768 UTF-8 bytes.
Every request ID is bound to principal, subject and exact canonical input.

| Operation on the configured terminal port | Binding and result |
|---|---|
| `POST /api/owner/prepare` | `Effect-Ack-Request: v=1, mode=prepare`; persists the preparation in the existing SQLite `meta` table, inserts no input event, returns `record_hash` and `commit_token`. |
| `POST /api/owner/commit` | Same envelope; `Effect-Ack-Request: v=1, mode=commit, token=:BASE64_ASCII_TOKEN:, hash=:BASE64_32_HASH_BYTES:`; calls the original ledger append and verifies its result through a new read-only SQLite connection. |
| `GET /api/owner/receipts/<request_id>` | Same authorization/identity headers plus `QIKVRT-Subject: <exact subject JSON>`; independent read-only SQLite observation without resubmission or a preparation ticket. |

The Structured Field token is Base64 of the returned ASCII `commit_token`;
the hash is Base64 of the 32 decoded bytes of the hexadecimal `record_hash`.
Both wire fields reuse the existing Effect-Ack parser. Initial commit expires
after 120 seconds. A stored preparation survives restart; an already committed
request can be read back and replayed after expiry. Exact Prepare replay returns
the same binding; exact Commit replay returns the original event with
`replayed=true`, including concurrent requests and single-file restore. Same ID
with different input is HTTP 409, without a second event. A lost response permits
authenticated receipt readback before a retry. Key rotation invalidates old
commit tickets, while the newly authenticated same principal can recover receipts.

Bearer keys are not stored in the SQLite carrier, events, preparation metadata
or receipts. Preparation and original event bytes occupy the same monolithic
database as the pinned carrier. Commit success means verified local persistence:
`EFFECT_ACK_CONTINUE`, `ordinary_release=false`, `EFFECT_ACK_DONE=false`. It grants
no repository, publication, deployment or other downstream effect. Failed
authentication is 401; identity, origin or permission refusal is 403; subject,
ticket, expiry or replay conflict is 409; absent authority or unavailable storage
holds at 503. The public `/api/terminal` readback advertises the private REST URL
and adapter availability without exposing personal event bodies or credentials.

`tests.test_self_host_temdd.OwnerRESTMonolithTests` executes the exported native
process with Unix ingress disabled, real authenticated REST, independent SQLite
readback, concurrent idempotent commits, SIGKILL/restart, monolith-only restore
and the negative identity/subject/conflict/authorization controls. The original
Unix ingress and historical source identity tests remain mandatory separately.

## Freeze, transfer and start

### App-Store-free secure Origin adapter

`monolith-origin-export` extends the same stopped-writer checkpoint. It emits
a static HTTPS bootstrap for both Node and Client roles from the independently
pinned carrier. The browser explicitly imports the **unchanged SQLite main
file** into one origin-private IndexedDB record. It does not create another
ledger or epoch. A Web Worker uses pinned sql.js 1.14.2 solely for fixed,
read-only SQLite integrity, carrier-byte and native-ledger readback queries.
The embedded Python source remains retained source and is not executed by the
browser. The React Terminal is passive: no native commands, inferred effects,
automatic file execution, background task scheduler or cloud writer is added.

After stopping both existing writers, use the same private configuration and
manifest pin as the native monolith:

```sh
python3 -B tools/qikvrt_self_host.py monolith-origin-export \
  --root /absolute/private-state/temdd/events.sqlite3 \
  --manifest-sha256 <independently supplied carrier-manifest-sha256> \
  --config /absolute/private/config.json \
  --output /absolute/private/new-origin-shell
```

The output includes the exact image SHA-256, native `meta.epoch`, source subject,
React/SQLite licenses and an individually hash-pinned Service Worker shell.
**It contains no private SQLite image, event bodies or credentials.** Publishing
that shell and obtaining an authenticated public HTTPS readback remain separate
effects. Serve it under a dedicated trusted HTTPS origin or subpath with normal
JavaScript and `application/wasm` MIME types. Loopback HTTP is admitted only for
development. Arbitrary HTTP, opaque origins and `file:` starts fail closed.
Use the HTTPS URL once online; the fully verified shell then works offline.
Installing a Home Screen shortcut is optional; no App Store or Git is required.

Choose the checkpointed SQLite file through the browser's explicit file picker.
This is user-mediated import, **not unrestricted filesystem access on iOS or
Android**. The browser checks the independent image digest, SQLite format and
integrity, every embedded carrier file, the original manifest pin, native epoch
and original event-body digests before committing. Transaction completion is
followed by fresh byte and SQL readback. Reload, browser restart and offline
opening reuse that record; they do not reset identity. An explicit download
exports the identical original SQLite bytes for native restoration. A new
independently bound checkpoint can replace the image only if all prior record
identities and digests remain an unchanged prefix. Capacity is explicitly
bounded to 64 MiB and 10,000 original ledger records; unsupported images are
refused without truncation.

IndexedDB and the shell cache belong to the browser origin and profile. They
are not freely visible filesystem elements. `navigator.storage.persist()` is
requested and its actual result is reported. Denial, quota exhaustion,
browser-data deletion and storage eviction are not turned into native fsync
or unlimited retention claims. A corrupt image is retained but not presented
as valid; automatic recreation or epoch replacement is forbidden. The adapter
does not implement native Python execution, native-effect replication or Mesh
write takeover in the mobile browser.

`make origin-adapter-test` exercises the original native SQLite fixture and
negative controls. `make origin-adapter-browser-test` additionally uses locked
Playwright/Chromium for actual IndexedDB transactions, corrupt import, offline
Service Worker/WASM/React loading, byte-identical export, reload and a complete
browser-process close/relaunch. It is desktop Linux evidence only. The existing
S1 CI lane executes these tests on its exact candidate head. A device-emulated
viewport or desktop WebKit must never be reported as an Android/iOS witness.
Actual Android/iOS offline, storage, restart and reconnection acceptance remains
`NOT_EXECUTED` until corresponding devices or executable runner routes exist;
`mobile_runtime_verified=false` and `effect_ack_done=false` remain explicit.

Platform sources: [Service Workers](https://www.w3.org/TR/service-workers/),
[secure contexts](https://www.w3.org/TR/secure-contexts/),
[WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/),
[sql.js source](https://github.com/sql-js/sql.js/tree/v1.14.2).

In a clean reviewed checkout run:

```sh
python3 -B tools/qikvrt_self_host.py pack --root . \
  --expected-head <exact-commit> --expected-tree <exact-tree> \
  --output /absolute/new/package-directory
```

The output is a directory and deterministic uncompressed `.tar` of explicitly
allowlisted **committed** blobs with exact sizes, hashes and Git source binding.
It contains neither credentials nor `.git` nor private state. An independent
receiver must obtain the printed manifest pin through a trusted channel, verify
the archive bytes, and safely extract regular files. No online installer, gh,
Railway, npm install or mutable remote checkout is used to start the export.
The declared tools are operator-provisioned, not included binary payloads.

Copy `CONFIG.example.json` outside the package, replace all placeholders and
bind an authorized node identity, absolute volume path, ports and source pair.
Config and secret files must belong to the runtime UID and be mode 0600; the
volume must be mode 0700. Supply a private 32–256-character ASCII terminal token
from the host's existing secret provisioner. Never put a token in argv, source,
the package, caches or receipts. Default listener is loopback. Bind `0.0.0.0`
only behind the host's existing authorized HTTPS routing. No DNS, account,
firewall, billing or routing changes are made by this package.

```sh
python3 -B tools/qikvrt_self_host.py verify --root <package-directory> \
  --manifest-sha256 <independently-obtained-pin>
python3 -B tools/qikvrt_self_host.py run --root <package-directory> \
  --manifest-sha256 <same-pin> --config <absolute-private-config>
```

The launcher and monitor share an OS file lock for the entire service lifetime,
starts the selected original native or reference terminal on loopback and the
existing Node monitor, and shuts both down on termination. A failed bind never becomes a
ready receipt. Configure restart in the host's existing supervisor, using this
exact command and unchanged private config. No second supervision/execution
system or platform service is created. An isolated launcher crash leaves the
surviving monitor holding the lock; restart is refused until it also stops.
Kernel lock release after all holders exit permits crash restart.

The separately mounted volume layout is:

| Path relative to configured volume | Contract |
| --- | --- |
| `binding.json` | fsynced node/package/config/source binding; drift refuses startup |
| `node.lock` | owner-only OS lock; a second live writer is refused |
| `monitor/node.json` | existing exact journal and checkpoint; fsync/rename semantics unchanged |
| `temdd/` | existing owner-only SQLite ledger/Unix ingress location; no substitute ledger is created |
| `receipts/` | reserved private operator receipts; not a cache or public document route |

A different package/config against an existing volume requires separately
reviewed migration. Do not delete or relabel acknowledged data to defeat the
binding. A real persistent mount/device identity, capacity and power-loss
guarantees remain host admission evidence; an ordinary local directory is not
proof of host persistence. The runtime binds only its configured filesystem.

The [Railway → Own-Host migration contract](MIGRATION.md) now provides
`migration-inventory`, `migration-verify-source`, `migration-export`,
`migration-verify-export`, `migration-import --dry-run`, `migration-import`,
`migration-verify-import` and `migration-rollback` in this same tool. It binds
all source/target paths, sizes and digests, preserves original DB/WAL/journals
and historical event subjects, and checks the explicit new `binding.json` in
separate verifier processes. Failed or rolled-back imports remain quarantined;
the launcher refuses them. These offline operations start no service and mutate
no Railway state or route. Actual snapshot capture, host admission and external
cutover readback remain independently evidence-bound.

The additive [one-shot Railway capture path](CAPTURE.md) now supplies
`migration-capture-supervisor`, `migration-capture-arm` and `migration-capture`.
The supervisor composer is unstarted and preserves all original recovered
source bytes. Its private, pinned hook fences startup before requesting bounded
writer shutdown, refuses unknown processes and drift, records complete private
metadata/acknowledgement evidence and fills `SOURCE.json`. Actual privileged
execution and private transfer remain a separate capability HOLD; no source
snapshot or production export is inferred from this adapter or its tests.

## Private durable-state snapshot and exact restoration

The existing launcher now provides `snapshot-state` and `restore-state`.
The immutable code export excludes state. These separate operations preserve
the **existing** native SQLite database, any WAL/SHM files, original monitor
journal and exact volume binding. They create neither a replacement ledger
nor synthetic production events. Tokens, credentials, Firefox profiles, caches
and private operator receipts are deliberately outside this snapshot.

On the source, stop the admitted service and its path unit through the existing
supervisor. Keep automatic activation and every original writer fenced while
transferring ownership; acquiring locks for a snapshot does not permanently
stop a source service. Do not allow an old and a restored writer to operate
the same node identity on different hosts.

```sh
sudo systemctl stop <authorized-name>.path <authorized-name>.service
sudo systemctl show <authorized-name>.service --property=ActiveState,MainPID
python3 -B tools/qikvrt_self_host.py snapshot-state \
  --root <absolute-verified-package-directory> \
  --manifest-sha256 <independent-package-pin> \
  --config <absolute-unchanged-private-config> \
  --output <absolute-new-private-snapshot-directory>
```

Run the snapshot as the original runtime UID. The command holds both existing
OS writer locks, checks the exact package/config/node/source binding and
streams a bounded 2 GiB inventory. It refuses a live writer before creating
output. The new directory is mode 0700 and its files are mode 0600; file and
directory sync plus independent digest readback precede a successful receipt.
`STATE_MANIFEST.json` binds every file's size and SHA-256. An incomplete output
is a failed operation and is never overwritten or automatically cleaned up.

Treat the complete snapshot as private durable application data. Transfer it
over the operator's existing authorized secure channel; keep the manifest pin
in an independent trusted channel. Never put this directory in Git, an Actions
artifact/cache, a public route or an email to another project participant.
Provision credentials separately through the intended host's secret facility.

On the independently authorized target, the configured state path must be
**absent** beneath a pre-existing owner-only parent. Keep the exact configured
absolute path, package pin, config bytes and node identity unchanged. The
restoration is create-only; an existing state path, wrong manifest, changed
binding, symlink, unlisted file, unsafe mode or changed file bytes returns HOLD.

```sh
python3 -B tools/qikvrt_self_host.py restore-state \
  --root <absolute-verified-package-directory> \
  --manifest-sha256 <same-independent-package-pin> \
  --config <absolute-unchanged-private-config> \
  --state-snapshot <absolute-private-snapshot-directory> \
  --state-manifest-sha256 <independently-obtained-state-pin>
```

This copies and rechecks the acknowledged bytes before runtime use. It neither
starts a process nor changes host admission. Bind a new host declaration to the
actual target, validate its persistent mount, install the pinned supervisor
units, then start through the existing `run-admitted` guard. Independently
compare the original ledger epoch, exact native event rows/digest chain and
monitor journal before and after a deployed restart, and repeat the external
HTTPS readback. Snapshot/restore success alone leaves all host, runtime,
Railway-cutover and EFFECT_ACK_DONE assertions false.

A new package head or changed config requires separately reviewed migration;
these operations cannot relabel old data for a new version. They also do not
export a legacy Railway volume. The observed live Railway terminal has a
different source/runtime layout whose exact data binding and export capability
remain to be verified; do not apply this S1 binding to it by editing metadata.
The [Railway SSH documentation](https://docs.railway.com/cli/ssh), freshly
read on 5 October 2026, describes registered-key SSH and SCP/SFTP access to
mounted-volume files. That is an operator transfer path, not a callable
authenticated export capability in this task. Do not register a new key, expose
a public data endpoint or copy a live SQLite file alone to bypass this gap.

### Railway retirement boundary

The fresh configuration inventory covers all five existing production services.
It distinguishes applied configuration from staged changes; no staged patch was
applied and no service, volume, route, variable value or account was changed.
The precise observation is in
`evidence/self_host/RAILWAY_EXIT_PREPARATION_20261005.json`.

| Existing service | Observed dependency | Required retirement evidence |
| --- | --- | --- |
| `universal-terminal` | Goldkelch source `2fdcf8d`; GitHub/tool installation at boot; Railway domain, deployment identity and live `/var/lib/qikvrt` volume | Exact legacy source/data export; source-writer fence; admitted target; independent original-event/epoch and public-use/restart readback |
| `mesh-monitor` | Applied Goldkelch `/docs/monitor` configuration; separate staged mirror source/volume changes | Actual current journal/source/route readback and safe export; independently accepted own-host monitor; no assumption that staged storage is live |
| `mesh-monitor-exact` | Applied Goldkelch `/deploy/mesh-monitor`, managed Python startup | Bound replacement of its actual role/data and independently checked consumers/routes |
| `mesh-monitor-live` | Applied Goldkelch `/deploy/mesh-monitor`, managed Python startup | Bound replacement of its actual role/data and independently checked consumers/routes |
| `mesh-monitor-bootstrap` | Applied Python 3.13 Alpine image and Railway domain | Verify remaining bootstrap consumers and replace their actual endpoint before retirement |

Before retiring each service, retain its recoverable original data and establish
the replacement's exact role, ownership and route with independent acceptance.
Keep the original writer fenced if rollback becomes necessary; reverse a
cutover only after diagnosing which side owns the acknowledged state.
Traffic/DNS switching, volume deletion, account cancellation and decommission
are separate operations after this evidence. No spend, DNS change, account
cancellation, staged deployment, legacy-state rebinding or Railway shutdown is
performed by this preparation.

## Network, authentication and readback

Adapter `none` observes its local packaged source, never GitHub. GitHub ingress
and live-run routes are refused. The outbound provider wrapper rejects Railway
and every external provider before transport; only loopback is allowed.
With the explicitly selected GitHub adapter, HTTPS `api.github.com` is permitted
and its webhook requires the existing HMAC boundary. Startup requires an
owner-only `github_webhook_secret_file` containing a 32–256-byte secret.
The host must apply its
own OS egress policy; the application wrapper is not a process sandbox.

Public GET/HEAD routes reuse monitor activity/events/SSE and the read-only
terminal at `/AI/` or `/terminal/`. Terminal repository reads resolve only
allowlisted public exported files; the immutable package commit is explicitly
distinguished from a current remote `main`. No public terminal effect or owner
Unix operation is exposed. `/api/terminal` returns sanitized runtime metadata,
not private input, record bodies, tokens or secret-file paths. Reference HTTP endpoints require the configured bearer token. Native subject
and SSE reads retain the recovered loopback/Host/same-Origin boundary. Private
native events are never proxied through the public monitor. Owner durable
Prepare/Commit remain the existing Unix peer-UID/socket/SQLite client contract.

Run the **existing independent monitor client** in a separate process:

```sh
node tools/qikvrt_mesh_monitor_readback.mjs --self-host <package-directory> \
  <exact-origin-url> <manifest-pin> <config-sha256> <expected-node-id> none
```

It verifies runtime/config/source pins, terminal binding, exact client assets,
snapshot, original journal bytes/digest chain and a final fresh node readback.
It uses the exported original client bytes, with no Git or provider dependency.
The original Railway plan path remains compatible when its existing contract
is installed; self-host selects an explicit separate plan. No credentials are
needed in the readback process. A local URL proves only local HTTP readback.

## Executable S1 validation

### Own-host admission and existing launcher binding

The same entrypoint now includes provider-neutral inventory/admission for
DigitalOcean, IONOS/1and1 Cloud and Hetzner. Start with `provider-inventory` and
`provider-classify`; contradictory or incomplete account/inventory observations
hold creation. See [PROVIDER_ADMISSION.md](PROVIDER_ADMISSION.md) for exact
region/size/cost/key binding, separate create authorization, durable idempotent
receipts and the existing independent public readback. These provider stages
do not replace the native own-host admission below.

`admit` extends this same tool. It makes no network call, starts no service,
creates no supervisor, modifies no state and grants no deployment authority.
Without a private host declaration and private configuration it returns
`HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE` (exit 2).

Copy `HOST_ADMISSION.example.json` outside the package, mode 0600. All nulls
mean missing evidence; they are deliberately not a fabricated host or URL.
Bind exact package Head/Tree/manifest, config digest and node ID. The host
operator supplies the SHA-256 of the exact `/etc/machine-id` bytes and the
selected persistent mount fields from `/proc/self/mountinfo`: `mount_point`,
`mount_root`, `device_major_minor`, `filesystem`, `mount_source`. The command
selects the longest mount containing the configured private `state_dir` and
compares these fields locally. Overlay, tmpfs and other ephemeral filesystems
are refused. A matching mount is not a power-loss or capacity guarantee.

The declaration also identifies the actually callable, authorized host
execution operation, existing supervisor/service, authorized public HTTPS
origin and digests of independently validated ownership/authorization,
persistence and HTTPS-routing evidence. Evidence digests alone do not validate
those records. Obtain the declaration pin through an independent trusted
channel; do not infer it from an untrusted self-report. Do not put secrets or
credential values in the declaration, arguments, launcher plan or repository.

```sh
python3 -B tools/qikvrt_self_host.py admit --root <absolute-package-directory> \
  --manifest-sha256 <independent-package-pin> --config <absolute-private-config> \
  --admission <absolute-private-host-declaration> \
  --admission-sha256 <independent-host-declaration-pin>
```

The result is `HOST_LAUNCHER_BOUND_PENDING_EXTERNAL_ACCEPTANCE`, with argv arrays
for the **existing** exported `verify`, `run` and independent monitor-readback
commands. No declaration-supplied command is executed. An independently
reviewed successor tool can prepare this plan for the unchanged exact #457
export `3bf52747bc94de847d390ffacabecae183aee588` / Tree
`96c7bb691675dcd15bb5045871201adb400074f0`; the plan runs that export's original
launcher. A newly packed successor binds its own fresh source pair instead.

After independently validating the named host/control-plane and evidence,
use the existing supervisor with the emitted verify/run argv. From a separate
external client execute the emitted readback against the exact HTTPS origin.
Record acknowledged native SQLite events through the existing owner Unix
ingress and the existing monitor journal, restart the actual deployed service
via the same supervisor, then repeat public readback and compare the exact
acknowledged event bytes and digest chain. Neither an empty ledger nor a
local restart substitutes for this witness. Record supervisor restart identity,
before/after process identities, mount binding and independent observations.

This plan leaves `host_admission_verified`, `public_readback_verified`,
`restart_verified`, `review_governance_satisfied` and `effect_ack_done` false.
Current host capability/HOLD evidence is in
`runtime/capabilities/S1_OWN_HOST_ADMISSION_20261005.json`; tests of synthetic
declarations are explicitly local controls and are not host acceptance.

### Durable supervisor binding and event-based restoration

The same reviewed tool now provides `supervisor` and `run-admitted`. No new
executor, ledger, provider adapter or supervision daemon is created. On a
validated own host with its already provisioned **systemd >=252**, set
`supervisor_id` in the private admission to `systemd:<authorized-name>.service`.
The private config/token/state must be owned by the intended service UID;
generate as that UID. Validate the guard's SHA-256 independently from the
reviewed source, even when it launches the unchanged original #457 export.

```sh
sh tools/bootstrap-runtime.sh --check-only --profile self-host-systemd --adapter none
python3 -B tools/qikvrt_self_host.py supervisor \
  --root <absolute-package-directory> --manifest-sha256 <independent-package-pin> \
  --config <absolute-private-config> --admission <absolute-private-host-declaration> \
  --admission-sha256 <independent-host-declaration-pin> \
  --admission-tool-sha256 <independently-reviewed-guard-pin> \
  --output <absolute-new-supervisor-output-directory>
```

The create-only directory contains `<authorized-name>.service`,
`<authorized-name>.path` and `BINDING.json` with exact unit/guard/package/config
pins. It is `SYSTEMD_BINDING_PREPARED_NOT_INSTALLED`. Validate both units with
`systemd-analyze verify`. On the independently authorized host, install those
exact unit bytes as root-owned mode 0644 files under `/etc/systemd/system/`,
compare their digests with `BINDING.json`, then use the **existing** supervisor:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now <authorized-name>.service <authorized-name>.path
sudo systemctl show <authorized-name>.service \
  --property=MainPID,InvocationID,NRestarts,ExecMainStatus,ActiveState,UnitFileState
```

The root-owned installed units and independently verified guard/runtime paths
are part of host admission. Do not install unreviewed generated bytes or infer
deployment permission from a declaration digest. Unit generation installs
nothing and performs no host or routing effect.

Every service start, including automatic recovery, rechecks the guard, exact
package/runtime/config/host/mount/admission pins. The original exported
`verify` runs in a separate process; its original `run` replaces the guard
with `exec`, preserving systemd's MainPID and cgroup. The existing kernel lock
and persistent volume binding remain authoritative. The guard requires an
active systemd PID1/version and compares MainPID/InvocationID with the actual
manager; an environment variable alone cannot establish this binding.
Identity drift returns
HOLD **78**, which suppresses unattended restart. State is never deleted,
recreated, relabeled or silently migrated by recovery.

`Restart=always` recovers an unexpected exit; an intentional `systemctl stop`
does not restart. `KillMode=control-group` removes surviving children before
another writer can start. Boot and the admitted mount's activation pull in the
enabled service; `RequiresMountsFor`/`BindsTo` prevent a missing mount from being
replaced by an ordinary directory. Five starts per 300 seconds bound a crash
storm. Restoring the **same pinned** config, admission, manifest, guard or
machine-ID bytes triggers the `.path` unit to retry admission. The retry is a
filesystem event, not an HTTP probe or a periodic loop. Restoring a package
directory atomically must include its manifest event. A changed head, revoked
authorization, changed identity/device, corruption or exhausted rate limit
requires a separately validated repair (`systemctl reset-failed` and a fresh
start after diagnosis); recovery cannot grant itself a new pin or credential.

The existing terminal workflow now requires a real native systemd test on its
disposable runner: kill only the launcher MainPID, observe a new invocation
and cgroup cleanup, preserve acknowledged native SQLite rows and monitor
journal bytes, force admission drift into HOLD 78, then restore the exact
admission bytes and observe automatic event-based recovery. Its receipt and
systemd version are retained as an exact-head artifact. This is a CI fixture,
not an owned public deployment. External HTTPS/readback, the actual deployed
restart witness and review governance stay mandatory and separate.

The same mandatory native lane also exercises snapshot/restore with a real
owner-Unix Prepare/Commit, SIGKILL, exact SQLite/WAL and monitor-journal bytes,
and fresh original-daemon readback after restoration. Additional original
SQLite-backend controls cover abrupt WAL retention and each actual OS writer
lock. They supplement the owner-Unix controls. Sanitized exact-head test
receipts contain only synthetic-fixture digests/counts and explicit unfulfilled
deployment assertions; the private state directories themselves are never
uploaded.

On the declared Linux runtime run `make test repository-monitor-test self-host-test`.
The existing full repository suite stays intact; the two explicit S1 targets add
the original monitor controls and standalone package controls. CI, repository
evidence, global completion, collective review and Batch-003 remaining subject
disposition require all three targets
after provisioning the S1 runtime. The existing terminal workflow additionally
requires all 31 HTTP/owner-Unix controls and freezes the actual source package.
A profile-specific Linux test is not imposed on unrelated portable callers.


## Verbindliche Nachweisoberfläche je Repository-Knoten

Product Owner Ingolf Lohmann verlangt seit dem 5. Oktober 2026, 23:47 Uhr
Europe/Paris, die Oberfläche
<https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site/>
für **jeden gegenwärtigen und künftigen QIK-VRT-Repository-Knoten** und für das
Mesh insgesamt. Produktname: **Universales Raumzeit-Terminal**.

Jeder Knoten stellt eine eigene, öffentlich über HTTPS erreichbare,
repositorygebundene Instanz bereit. Er zeigt seine Identität, Rolle, exakt
ausgelieferten HEAD/TREE und Paketbytes sowie getrennt davon den frisch
beobachteten Remote-Stand. Bekannte unerreichbare Knoten bleiben sichtbar.
Ein gemeinsamer Host ist zulässig, sofern Identität, Quelle, Speicher und
Readback jeder Instanz einzeln prüfbar sind.

Zum Mindestumfang gehören automatische Aktualisierung beim Öffnen und
Fortsetzen, der vorhandene Replica-/SSE-Pfad, explizite Aktualisierung,
zeitgebundene HTTP-Befunde, persistierte unveränderte Beobachtungsbytes mit
SHA-256, ein separater bytegenauer Readback, sichtbare Historie und
JSON-Downloads. Quellen, Bootstrap-/Runtime-Paket, Manifest, Downloadprüfung
und Lizenzhinweise bleiben nachvollziehbar. Ein Hintergrundlauf muss über das
Repository oder die zugelassene Hosting-CI ohne geöffneten Client arbeiten.

Die Referenz aktualisiert offene Clients und wiederverwendbare Serverbefunde
im 60-Sekunden-Fenster, markiert Befunde nach 120 Sekunden als veraltet und
hält 200 Beobachtungen vor. Jede Instanz erklärt und prüft ihre Frische und
Aufbewahrung; geschützte native Wirkungsbelege behalten ihre eigenen Regeln.
Bei Fehlern bleibt der ursprüngliche Beobachtungszeitpunkt erhalten.
Standard-Knoten übernehmen ausschließlich freigegebene öffentliche Metadaten
und lizenzierte Paketbytes, keine persönlichen Inhalte oder Geheimnisse.

Der maschinenlesbare Vertrag und die exakt gebundene Referenzquelle stehen in
[`MESH_ACTIVATION.json#/required_repository_surface`](MESH_ACTIVATION.json).
Bestehender Monitor, S1-Listener, Replica und Paketpfad werden weiterverwendet.
Die vollständige Funktionsdeckung und öffentliche Bereitstellung je Knoten
sind weiterhin **ungeprüft**. Der aktuelle Referenzstand ist kein neuer
öffentlicher HTTP-, Hosting-CI- oder nativer Transputer-Wirkungsnachweis.
Alle bisherigen Erst-Ping-, vollständigen Terminal-Empfangs- und
Restart-Abnahmestufen bleiben erforderlich.

## Precise remaining acceptance

The former productive source gap is resolved for the exact recovered historical
snapshot. The original Goldkelch commit declared by that snapshot could not be
retrieved directly, and equality with a later Railway production build remains
unverified. The selected native daemon runs its original SQLite/WAL and Unix
implementation through the new sealed-source adapter. Reference HTTP remains
process-local and does not supply durable native evidence.

The native suite exercises actual owner Prepare/Commit, fresh SQLite/SSE,
wrong subject, drift, duplicate commit and crash restart. The terminal workflow
also builds the declared Linux Firefox carrier and runs the actual candidate
export with only loopback networking, no Git/gh in its runtime PATH, real X11
window and VNC WebSocket readbacks, plus native/browser crash restart. These
checks establish only the execution recorded by the immutable workflow head.

No callable own-host deployment operation, verified host identity, durable mount
or public route is available in this task. The deployment work unit records
`HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE` and references the historical source recovery separately. Container and local
restart tests do not close the host admission condition.
S1 remains OPEN until host admission, exact deployment,
fresh public use/readback and deployed restart acceptance are established.
No public URL, S1 DONE or EFFECT_ACK_DONE is asserted.

## Same monolithic store for a Node and a Client

The Owner's deployment instruction of 6 October 2026 is bound in
`MESH_ACTIVATION.json#/deployment_contract`. A Node and a Client use the same
store format and starter. Their role does not select a different distribution.
The Terminal remains passive input/output and is opened on demand.

The native candidate extends the existing S1 builder. It puts the sealed package
files, pinned React runtime and package manifest into a `carrier` table in the
same SQLite file used by the original native TEMDD ledger. The ledger's
`meta` and `events` tables, owner ingress, preparation, commit, replay and
independent SQLite readback are reused unchanged. No second effect kernel or
Git service is required at runtime. The SQLite file is a normal filesystem file.

The current native ABI places that object at
`<private-state>/temdd/events.sqlite3`. The code extracted from its pinned
carrier is a disposable cache, not another authoritative repository. Host
configuration, credentials, operating-system locks and sockets are runtime
bindings. They are not part of a public distribution or copied as private state.
The separate monitor journal remains a read projection; its history is not
included in a single-file native-ledger relocation.

After making a reviewed exact S1 export with the existing `pack` operation:

```sh
python3 tools/qikvrt_self_host.py monolith-pack \
  --root /private/sealed-package --manifest-sha256 <independent-manifest-pin> \
  --output /private/state/temdd/events.sqlite3
python3 tools/qikvrt_self_host.py monolith-run \
  --root /private/state/temdd/events.sqlite3 \
  --manifest-sha256 <independent-manifest-pin> --config /private/config.json
```

The parent directories must already be owner-only directories. Creation is
exclusive. The configuration retains the existing exact head/tree, runtime,
token and volume binding; `terminal_profile` must be `temdd`. The outer starter
must itself have the same bytes as the starter embedded in the sealed carrier.
The ready response and `/api/runtime` give the local React URL
`http://127.0.0.1:<port>/client`. `/node` and `/client` serve the same React
carrier. No browser or Firefox/noVNC process is opened by `monolith-run`.
The authenticated Owner REST Prepare/Commit/readback path is preserved, with
private Unix ingress as a separate optional local adapter.

Opening or reading the Terminal does not append an input or start a workflow.
An explicitly committed owner input is persisted by the existing ledger in
the same monolithic file and read back independently. This is a local native
ledger effect, not cloud synchronization, public deployment or Mesh acceptance.

### Transfer only a stable complete image

SQLite can need WAL/SHM companions while the runtime is active. A main-file-only
copy of an active runtime is not a complete snapshot. Stop the runtime, then:

```sh
python3 tools/qikvrt_self_host.py monolith-checkpoint \
  --root /private/state/temdd/events.sqlite3 \
  --manifest-sha256 <independent-manifest-pin> --config /private/config.json
```

This operation must hold both existing writer locks, verify the volume binding,
checkpoint the WAL, return to the single-main-file journal mode, reject remaining
transaction companions, fsync the file and directory, and return its fresh hash.
It does not admit a live competing writer or copy private tokens. Only after this
cut may the object be transferred alone. The recipient independently verifies
the carrier pin and provisions its own private runtime binding. Old prepared
inputs retain their old route binding and are not automatically reauthorized.
Automatic replication, fence/quorum takeover, power-loss and mobile evidence
remain separate acceptance obligations.

### Mobile runtime remains an open implementation and witness

The same logical object contract applies to mobile clients. This candidate's
adapter is still Linux/Python/Node. A filesystem file does not execute without
a suitable runtime, and a mobile browser cannot be assumed to run this native
starter. The secure-Origin SQLite adapter described above preserves the same
original image; actual iOS/Android and public HTTPS acceptance remain open.

WebKit supports Home Screen web apps without an App Store; it requires an
executable initial web entry. Service Worker registration requires the permitted
HTTP(S) origin and secure-context conditions, rather than an arbitrary embedded
blob worker script. Browser-owned persistent storage is origin-bound, may not
map to a user-visible file, and is subject to quota and eviction. These platform
contracts must be checked by the adapter and exercised on actual devices.

Primary source locators:

- https://www.w3.org/TR/service-workers/
- https://webkit.org/blog/12257/the-file-system-access-api-with-origin-private-file-system/
- https://webkit.org/blog/14403/updates-to-storage-policy/
- https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/

`mobile_runtime_verified=false`, `all_manufacturers_verified=false`, and
`EFFECT_ACK_DONE=false` remain explicit. Neither a source gate nor a native Linux
test supplies mobile, public URL or cloud synchronization acceptance.

## One canonical persistent representation

`MESH_ACTIVATION.json#/storage_contract` is the storage authority. SQLite
remains the common Node/Client product file. `repository.qmesh` is only a
read-only, byte-exact export of a checkpointed SQLite image. It is never a
second native ledger, writer, replay authority or Effect-Ack source. See
`MESH_FILE.md` for the exact transport/import and full-tree contract. The
legacy source-only QIKMESH1 file cannot be promoted to a product store.

`portable --root <exact-checkout> --expected-head <HEAD> --expected-tree <TREE>
--output <new-private-directory>` creates `repository.sqlite3` containing the
sealed S1 carrier, original empty native ledger and every original committed
blob in `repository_files`. It additionally emits the derived
`repository.qmesh` and a self-contained, read-only React export viewer. The
viewer can select and copy files through normal browser file access. The
secure-Origin adapter, native Owner REST and passive native Terminal retain
their existing independent permission and acceptance boundaries.

The default portable image contains the complete **current Git tree**, not
ancestor commits, other branches/tags, Git configuration, LFS payloads or
submodule repositories. Its receipt reports this boundary as `git_history`.
Add `--include-git-history` to preserve every commit and Git object reachable
from the exact HEAD in `repository.bundle`. This option refuses shallow or
incomplete object stores, performs strict Git checks, disables network/lazy
fetch, and records bundle size, SHA-256 and commit count. Historical format
defects remain failures; no original object is rewritten. Other refs and their
unreachable history are outside this explicitly bounded bundle.

`portable-restore --root <absolute-repository.sqlite3>
--manifest-sha256 <independent-carrier-pin> --image-sha256 <independent-image-pin>
--expected-head <HEAD> --expected-tree <TREE> --output <absent-private-directory>`
validates and restores every source blob and executable mode using Python
alone. The destination must be absent. Unsafe Git administrative paths and
escaping symlinks are refused before writing. Every restored file and the
complete original tree identity are read back. This does not execute the
restored application or restore Git history. A separately pinned complete
bundle can be cloned into an empty directory with Git protocols restricted
to the local file; verify its HEAD, TREE, commit count and `git fsck --strict`.
The raw-blob restore preserves committed bytes. A normal Git checkout then
applies the original `.gitattributes`, including CMD/PowerShell CRLF endings.
The repository inventory checks that checkout representation; retain both
the byte-exact blob witness and the subsequent attribute-aware checkout check.
Private runtime state, credentials and bootable Linux distribution acceptance
remain separate obligations.

For an activated native object use `monolith-transport-export` with the same
`--root`, `--manifest-sha256`, `--config` and a create-only `--output`. Import
with `monolith-transport-import --root <transport> --manifest-sha256 <pin>
--image-sha256 <independent-image-pin> --transport-sha256 <independent-wire-pin>
--output <absent-private-SQLite-path>`. Import performs no native effect;
private configuration and credentials are provisioned separately before
`monolith-run`. No predecessor test or approval accepts a successor HEAD.
<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->

## Current Authority roles and Linux Docker delivery — 2026-10-13

The successor in PR #523 reuses the complete runtime delivery from PR #494.
Its original artifact is 11521962723, SHA-256
`5a912ccde96253bdba5f5e82cd0a36a4ff89de58dabbe57977bc1acf298d9695`.
The seven-layer image is an immutable **dependency carrier**, without QIKVRT
implementation code. Reuse that image and reseal the current source package;
an old source package does not establish execution of the current candidate.
The frozen baseline, source comparison and original byte receipt are bound in
`evidence/receipts/QIKVRT_LINUX_DOCKER_ROLE_DEPLOYMENT_20261013_V1/`.

Resolve Authority `ingolf-lohmann/qik-vrt` and Mirror `Goldkelch/qik-vrt` from
`policy/CANONICAL_UPSTREAM_REMOTE_V1.json`, with the Owner projection in
`policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`. Both policies are now
included in the sealed package. Compose, the mirror bootstrap and monitor
defaults agree; conflicting environment overrides are refused. The legacy
mirror Git transport is held under REST-only routing. It is not the S1 Docker
deployment executor and is not silently substituted for a REST capability.

The existing `.github/workflows/qikvrt_effect_ack_http_terminal.yml` retrieves
the exact SHA-256-bound baseline, loads it, adds only its existing test carrier's
Git/Make provisioning, and exports the matching current-source package. The
runtime target remains the original dependency image. Actual CI checks include
Docker start, role/health readback, private durable input, profile persistence,
container restart and exact native-event readback. Those tests do not attest
production, public HTTPS or an independent persistent host.

The existing launcher exposes `runtime-delivery-verify`,
`runtime-delivery-load`, `deployment-roles` and `docker-admit`. Its existing
`supervisor` and `run-admitted` operations accept `--delivery` and an
independent `--delivery-sha256` pin. Docker admission first verifies the image,
current package, exact runtime executable bindings inside that image, host
machine/mount identity and private config/admission pins. It requires
`public_origin=https://raumzeitterminal.de` and
`execution_operation=docker run --network host`. Only a local Unix-socket
Docker engine is allowed. All application listeners remain loopback-bound and
use the existing admitted HTTPS reverse proxy. Package/config/secrets are
read-only mounts; the separately admitted host state directory is persistent.

Keep the same existing systemd service. The container has `--restart no`; the
existing supervisor owns restart, mount/admission guards and HOLD exit 78.
Every guarded restart checks the exact subject and preserves its volume
binding. A changed source cannot silently rebind an old volume: use the
existing snapshot/migration contracts where migration is required.

The same workflow's production job is available only on trusted Authority Main,
after its delivery lane succeeds, and only through `deploy_existing_host=true`.
It consumes an **existing** runner/environment and these protected, non-secret
bindings: `QIKVRT_S1_EXISTING_HOST_RUNNER` (JSON runner labels),
`QIKVRT_S1_EXISTING_ENVIRONMENT`, `QIKVRT_S1_CONFIG_PATH`,
`QIKVRT_S1_ADMISSION_PATH`, `QIKVRT_S1_ADMISSION_SHA256`,
`QIKVRT_S1_PACKAGE_PATH`, `QIKVRT_S1_GUARD_PATH` and
`QIKVRT_S1_DELIVERY_PATH`. This implementation creates none of those external
resources and does not invent their availability. The installed guard and
systemd unit must already match the reviewed binding; missing or mismatched
bindings fail closed. The exact delivered bytes are retained at the admitted
durable delivery path. The job restarts only that existing unit. A separate
hosted Linux job independently verifies the real application, roles, exact
HEAD/TREE and ledger/source bytes at `https://raumzeitterminal.de/`.

Production remains unverified until those host and independent HTTP operations
actually succeed. Native Main governance and review remain separate gates.
No provider purchase, DNS write, second website, new controller or automatic
Main promotion is included.

## Native peer rule receipt and activation

`mesh-cache-send`/`mesh-cache-check` keep their proposal-only contract. A work
batch or its receipt never activates a rule. The original native Terminal has
an additional, separately admitted rule path on its existing loopback listener:

| Operation | Evidence / effect |
| --- | --- |
| `POST /api/mesh-work/rule/receive` | Original `OBSERVE` event; receipt only |
| `POST /api/mesh-work/rule/apply` | Install the exact native writer guard and append a separate original `EFFECT` event |
| `GET /api/mesh-work/rule/readback/<request_id>/<32-hex-challenge>` | Fresh read-only SQLite connections verify request, both events and active guard |

Use the existing `mesh_work_peers` private keys and HMAC method/path/body
contract. The sender pins the peer identity and source HEAD/TREE. Configure
its peer `url` to the **existing native Terminal** listener, reached through
the admitted host transport; the monitor proposal listener remains unchanged.
No new listener, service, credential provider or message relay is added.
The native listener remains loopback-only and refuses browser-origin requests.
Original native and copied-journal writer fences still apply.

The receiver additionally requires `mesh_rule_grants` in its existing private,
source/volume-bound S1 configuration. Each entry has exactly these fields:
`peer_node_id` (authenticated sender), `request_id`, canonical `request_sha256`,
`rule_sha256`, `rule_path` (a sealed `policy/` JSON file), and `rule_pointer`
(an array of JSON object keys selecting the approved rule). Hash references
use `sha256:<64 lowercase hex>`. There is no default grant. Incoming rule bytes
must equal the already reviewed local rule; a message cannot change the rule
file or authorize itself. Grant/configuration changes require the existing
configuration/volume admission procedure.

The bounded canonical JSON request uses schema `qikvrt-peer-rule-request/v1`
and exactly `request_id`, `work_unit_id`, `sender_node_id`, `sender_repository`,
`peer_node_id`, `subject` (`repository`, positive `pr`, `head`, `tree`),
`rule_id`, `rule` (the selected JSON object), and `rule_sha256`. The request
digest covers the complete canonical request; the rule digest covers canonical
rule bytes. Receiver receipts bind both hashes, sender/recipient, Work Unit,
exact subject, original native provenance, event ID/epoch, native digest,
payload digest and ledger-body digest. Every read also revalidates the local
rule bytes, grant and sealed source. Original request bytes and frozen native
event plans live in the original ledger's `meta` table, not a second journal.

Activation means **native peer rule admission guard installation**. S1 consumes
that binding before every subsequent native append. A removed/corrupt active
guard, revoked grant or changed source holds unrelated native writes. A crash
between guard installation and event append allows only the original exact
application event to finish the activation. This is not a general policy
interpreter: receipt/activation does not execute prose, arbitrary instructions,
repository proposals or a model session. It cannot prove future Claude
behaviour, other-node adoption, or a safety/physical effect.

The existing S1 CLI performs one finite synchronous exchange:

```sh
python3 -B tools/qikvrt_self_host.py mesh-rule-confirm \
  --mesh-cache /private/existing-node-cache \
  --work-request /private/exact-rule-request.json \
  --peer /private/existing-terminal-peer.json --apply-rule
```

Omit `--apply-rule` for receipt only. The sender retains its request and
authenticated receipts in the existing cache. It performs fresh challenged
GET before any POST and after every native effect. Lost responses are resolved
by readback; an unavailable read never admits a retry, and an acknowledged
receipt disappearing holds the exchange. Receipt/event identities cannot be
replaced after restart. The existing EAP engine may return nested
`rule_effect.state = EFFECT_ACK_DONE` only for verified native guard activation.
The outer `effect_ack_done` and `all_peer_adoption_verified` remain false.
No global completion, public-host delivery or actual Claude ACK is inferred.

Reproduce the real loopback/native-journal conformance tests with:

```sh
python3 -B -m unittest -v tests.test_self_host_temdd.NativePeerRuleTests
make test repository-monitor-test self-host-test
```

The fixtures use synthetic peer identities and private test keys. They exercise
receipt/application separation, original writer-guard enforcement, full binding
substitution controls, HMAC/challenge replay rejection, restart, lost ACK,
revocation, native identity replacement and refusal without independent readback.
Productive acceptance still needs the actual admitted peer's private channel,
its original writable Transputer and independently challenged Terminal readback.

