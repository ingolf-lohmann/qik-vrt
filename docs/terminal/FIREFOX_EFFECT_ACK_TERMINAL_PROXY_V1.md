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

### Durable local Linux state

On POSIX, the CLI defaults to the current directory as `--state-root` and
stores one private snapshot at `.qikvrt/api/terminal.json`. An explicit root
selects an isolated local instance. The implementation reuses
`qikvrt_api_handler.atomic_write_bytes`, its strict no-follow reader and its
process lock; it does not introduce an additional ledger or remote store.
The separate `terminal.lock` is held for the server lifetime, so a competing
process fails admission. HTTP commits remain serialized by the existing lock.

The snapshot contains records, ordered events, prepared tokens and their
consumption state together. Prepare and Commit replace it atomically and fsync
both file and directory before a positive HTTP reply. Tokens and key material
remain in the mode-0600 local file and must never enter uploaded evidence.
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

The existing Linux Firefox witness retains its real browser effect, adds
bounded HTTP concurrency, then kills and restarts actual terminal processes
and compares every retained event and referenced record. This establishes only
the bounded local snapshot on a filesystem honoring atomic rename and fsync.
It does not test power removal, media destruction, network loss, productive
Authority/Mirror nodes or unbounded scalability. The unseeded Windows/in-memory
reference profile continues to declare `PROCESS_LIFETIME_ONLY`.

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
