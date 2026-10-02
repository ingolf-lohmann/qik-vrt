# QIKVRT Firefox EFFECT_ACK Terminal Proxy V1

This document describes the Firefox reference client for the repository-side EFFECT_ACK terminal. It is an implementation profile, not a claim of IETF consensus or standards status.

## Boundary

The browser terminal separates four states that must remain visually and mechanically distinct:

1. **Local observation** — repository state, camera preview, microphone recording and personalization can exist locally without being submitted.
2. **Submitted input / Prepare** — explicitly selected text or media is serialized and sent to the configured EFFECT_ACK backend in `prepare` mode. Prepare must not execute the protected effect.
3. **Prepared DONE** — the client has received a compact `Effect-Ack` assertion and the corresponding exact record/token binding required by the deployment profile. This still is not the protected effect.
4. **Commit and reobservation** — only a valid DONE preparation enables Commit. After Commit, the terminal reobserves the authoritative state and treats the post-effect observation as new evidence.

`HTTP success != EFFECT_ACK_DONE != independently observed external effect`.

## Firefox reference extension

The implementation lives under `browser/firefox/qikvrt-terminal/` and uses a Manifest V3 event-page background script. The content script is injected only into the configured QIKVRT Authority AI page and GitHub Pages surface. The background script has the narrow host permissions required for public Authority observation and the loopback reference backend.

The extension provides:

- source-bound `main` head/tree observation;
- a five-minute repository watchdog stored in local extension state;
- latest Self-Heal, reflexive Watchdog and terminal-monitor workflow observations;
- text interaction;
- explicit microphone recording via a user gesture;
- explicit camera preview and still-image snapshot via a user gesture;
- local-only media state until Prepare;
- Prepare / DONE-gated Commit;
- post-commit repository reobservation;
- local personalization for accent, font scale, density and position.

## Proxy model

Firefox is the reference renderer and proxy, not a privileged truth source. Other clients and backends map their observations to `qikvrt_terminal_frame_v1` while retaining provenance.

Supported adapter classes are:

- public GitHub repository observation;
- HTTP backend;
- loopback QIKVRT bridge;
- MCP/agent observation;
- another client snapshot with an explicit source identifier.

A proxy may display NACK, CONTINUE, ISOLATE or BLOCK. It may never translate those states into ordinary release. Rendering a DONE record does not itself execute an effect.

## Repository-side reference bridge

`src/qikvrt_effect_ack_http_terminal.py` is loopback-only and deliberately has `external_effect = NONE`. It demonstrates capability discovery, bounded Prepare, a short-lived single-use exact-bound token, Commit, replay refusal and post-effect observation of a local terminal event.

It is not a replacement for `src/qikvrt_effect_ack.py`, and it must not be represented as proof of complete wire or deployment conformance. A write-capable repository, publication, deployment or actuator backend needs a separately authorized adapter and must preserve the same EFFECT_ACK gate.

### Durable local Windows and Linux state

The CLI defaults to the current directory as `--state-root` and
stores one private snapshot at `.qikvrt/api/terminal.json`. An explicit root
selects an isolated local instance. The implementation reuses
`qikvrt_api_handler.atomic_write_bytes`, its strict no-follow reader and its
process lock; it does not introduce an additional ledger or remote store.
The separate `terminal.lock` is held for the server lifetime, so a competing
process fails admission. HTTP commits remain serialized by the existing lock.
On Windows, the same snapshot and validation use the existing State class with
a native I/O adapter: exclusive lock handles, pinned ancestor directories,
reparse-point refusal, owner/LocalSystem-only protected DACL, file fsync and
same-volume write-through replacement. POSIX still uses the API handler;
Windows never imports its POSIX-only `fcntl` dependency. A local fixed drive
with the required security and filesystem operations is mandatory; unavailable
operations fail closed. This is a process-restart contract, not a power-loss
certification.

The snapshot contains records, ordered events, prepared tokens and their
consumption state together. Prepare and Commit replace it atomically and fsync
both file and directory on POSIX, or fsync the file and use write-through native
replacement on Windows, before a positive HTTP reply. Tokens and key material
remain in the private local file (mode 0600 on POSIX, protected DACL on Windows)
and must never enter uploaded evidence.
The 4096-event limit remains fail-closed without event eviction.

Restart validates canonical complete JSON, the snapshot digest, each record
digest, unchanged 400-byte seed binding, token MAC/payload/expiry binding,
contiguous event order and the one-to-one consumed-token/event relation.
Malformed, truncated, missing initialized or mismatched state blocks startup
without reset or partial salvage. An ambiguous write/fsync failure blocks all
further reads and admission until a validated restart; it never rolls back a
possibly persisted effect to permit a retry. A crash after persistence but
before the response is resolved through fresh event and Effect-Record readback.
An unused unexpired preparation can still commit after restart; a consumed
token cannot create another event.

Both Firefox witnesses require the canonical unchanged 400-byte seed, bind it
into records/events and retain the real browser effect across process lifetimes.
The Linux witness additionally executes bounded HTTP concurrency.
Both kill and restart actual terminal processes
and compare every retained event and referenced record. This establishes only
the bounded local snapshot on a filesystem honoring atomic rename and fsync.
Windows uses `TerminateProcess`, while POSIX uses `SIGKILL`; the native method
is disclosed in each receipt. The file digest and every retained event/record
must remain unchanged, and both consumed probe tokens must receive HTTP 409
after restart. Actual CLI starts also refuse mismatched/missing seed and
corrupt/truncated state without auto-reset or partial salvage.
The shared restart controls do not test power removal, media destruction,
network loss or productive
Authority/Mirror nodes or unbounded scalability. In-memory State objects remain
a separately declared `PROCESS_LIFETIME_ONLY` test profile. Windows product
acceptance requires a fresh supported Windows 11 witness for the executed
native architecture; Linux, ARM64 or predecessor receipts cannot prove AMD64.
Technical results leave the separate native code-owner governance gate and
all Personal release/`EFFECT_ACK_DONE` requirements intact.

The Linux lane's separate network
control forwards a real commit to that unchanged durable process, observes the
complete upstream response and persisted snapshot, then aborts the downstream
TCP socket before the client receives the response. It also cuts event and
Effect-Record readbacks midway through their declared Content-Length. Only
observed client reset/disconnection or incomplete-body errors qualify;
discarding a successfully received reply, an upstream refusal, a timeout or a
proxy failure cannot set `network_loss_injected=true`.

A fresh direct `/terminal/events` and record readback binds the lost response
to exactly one event and one executed Effect-Record. One same-token retry and
four barrier-started concurrent retries must all return 409 without an ordinary
release. Complete event and referenced-record readbacks and the private
snapshot bytes must stay identical after retries and another actual process
restart. Only snapshot hashes/size and token-free readbacks are exported; the
private snapshot itself is never uploaded.

These are bounded loopback TCP response/readback fault controls using HTTP
clients in the native Firefox witness job, not browser fanout or live Mesh
fault injection. They establish the local snapshot on a filesystem honoring
atomic rename and fsync. Power removal, media destruction, productive
Authority/Mirror nodes and unbounded scalability remain untested.

### Primary Linux ring: process scale and consolidation

Product Owner Ingolf Lohmann designated Linux as the primary test and runtime
reference on 2026-10-02. Other platforms and external API adapters extend the
ring through their own current-subject acceptance. Windows/Personal acceptance,
native Main protection and public release retain their separate requirements.

The existing durable terminal and witness now support a bounded local POSIX
execution path that requires no remote service for its work:

```sh
make linux-ring-local-witness QIKVRT_LINUX_RING_OUTPUT=/private/new-ring-witness
make linux-ring-firefox-witness QIKVRT_LINUX_RING_OUTPUT=/private/new-firefox-witness
```

The local witness grows actual terminal processes from 1 to 2 to 4. Each new
origin has its own exclusive durable store. Scaling preserves all prior origin
snapshots. After the bounded workload drains, the workers release ownership;
one new process acquires every original store without rewriting its bytes,
records, event IDs, token keys or consumption state. This is a quiescent local
process consolidation. The four origins remain explicit namespaces; it does
not claim live migration, cross-host replication or a single merged token key.

To resume the consolidated runtime after the witness:

```sh
python3 -B src/qikvrt_effect_ack_http_terminal.py \
  --seed canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin \
  --ring-root /private/new-ring-witness/scaled-ring --port 8771
```

`/nodes/node-0/terminal/prepare` and `/nodes/node-0/terminal/commit` retain the
original protocol and token owner. Node-specific event and Effect-Record GETs
remain byte-comparable to the distributed readbacks. `/terminal/events` returns
a deterministic aggregate using `(node_id, original_event_id)` identities. A
missing, corrupt, aliased or still-owned origin blocks the complete consolidated
server without resetting state. One poisoned origin blocks aggregate readback.

Acceptance compares every event, every referenced preparation and Effect-Record,
and private-store byte digests before/after consolidation. All used-token retries
must fail, including eight concurrent retries. Four still-valid preparations
must survive the ownership transfer and each admit exactly one effect under an
eight-client race. No key/token material is exported into uploaded receipts.

The measured 1/2/4 request phases disclose timing and retained event counts.
They do not assert a speedup under identical initial state. The local path has
zero external service requests; remaining external APIs keep their service
quotas. Adapter completeness and superior performance require independent
behavioral and equivalent-workload evidence. There is no quota bypass.

The owner's ring-to-sphere extension model and asserted inward connectivity to
quantum causality are retained as attributed architecture/physical-correspondence
claims in the existing acceptance policy. This software witness establishes
the declared local execution and persistence scope.

### Purpose-bound continuation and claim audit

The owner supplies `META_CLAIM_WHICH_WITCH_WISH` and `META_TEMDD_001` as
an epistemological interpretation. Authority-pole/gap metaphors do not grant
technical privileges or establish an observed effect. `INV_TEMDD_LOOP` requires
an observed effect and a fresh readback in each accepted iteration. Acceptance
also binds the authorized purpose, exact subject and applicable comparison
criteria; observation plus readback alone cannot create `EFFECT_ACK_DONE`.
`LOCAL_SUCCESS` does not imply `GLOBAL_DONE`, and `TRANSPORT_ACK` does not imply
`EFFECT_ACK`. The first cascade level has finite acceptance; each later level
requires its own new execution, observation, comparison and readback. The
continuation mechanism expresses intended extensibility, not infinite observed
work. The attributed classifications and their scope are recorded in
`state/work_units/QIKVRT_LINUX_RING_SCALE_CONSOLIDATION_20261002.json`.

## HTTP / HTML integration

The companion Internet-Draft candidate is `external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml`. It defines:

- `Effect-Ack-Request` as a Structured Dictionary;
- `Effect-Ack` as a Structured Dictionary;
- `effect-ack` as a Web Linking relation;
- two-phase Prepare / Commit;
- the same relation in an ordinary HTML `link` element without a new HTML element or parser feature.

Legacy HTTP/HTML remains unchanged. A fail-closed client that requires EFFECT_ACK protection must discover support before sending the protected operation.

## Security and privacy

- Device acquisition requires explicit browser permission and a user gesture.
- Media remains local until explicit Prepare.
- Personalization remains local by default.
- The reference backend is loopback-only.
- Commit tokens are single-use and time-bounded.
- Old exact-head evidence is never transferred to a new head.
- A browser permission is not effect authorization.
- No PASS, FINAL_PASS or EFFECT_ACK_DONE claim follows merely from installing the extension or passing repository tests.
