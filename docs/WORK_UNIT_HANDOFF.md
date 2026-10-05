<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Existing Mesh API work-unit handoff

PR #445 extends `src/qikvrt_api_handler.py`, the existing HTTP shim and
`scripts/qikvrt_api_client.py`. It adds no workflow or parallel scheduler.
The admitted service thread outlives its HTTP request and client process.
The bounded productive operation is **ingest the exact existing work-unit
snapshot into the existing authenticated inbox**. It cannot execute arbitrary
commands, repair another PR, publish, promote Main or deploy a service.

The GitHub workflow's original four operations remain unchanged. The following
operations require an installed Mesh HTTP adapter. GitHub `workflow_dispatch`
and a green CI run do not expose this productive handoff automatically.

| Operation | Contract |
| --- | --- |
| `work_unit_handoff` | Queue one existing work-unit ID with its exact local ref, HEAD, TREE, source-byte SHA-256, authenticated principal and retained scoped authorization. Queue receipt is not executor admission. |
| `work_unit_status` | Read the current checkpoint, actual executor identity/fence, hash-linked journal and independently revalidate any completed effect receipt and bytes. |
| `work_unit_event` | Append one idempotent `QUESTION_ANSWERED`, `CLIENT_DISCONNECT_REPORTED` or `EXPLICIT_CANCEL` event with its evidence digest. |

Use the existing authenticated dispatch-shaped endpoint and client. `artifact_id`
is the unchanged work-unit ID. For handoff, `expected_sha256` is the SHA-256 of
`state/work_units/<ID>.json`, and `payload_b64` encodes:

```json
{
  "schema": "qikvrt_work_unit_handoff_v1",
  "work_unit_id": "QIKVRT_CHAT_INTERRUPTION_CONTINUITY_20261002_V1",
  "subject": {"ref": "refs/heads/<current-local-branch>", "head": "<exact-40-hex-head>", "tree": "<exact-40-hex-tree>"}
}
```

An event envelope is `{"kind":"QUESTION_ANSWERED","evidence_sha256":"<64-hex>"}`.
The client/event adapter must retain the exact trace bytes behind the digest.
The event's name or digest is a **caller-reported observation**, not independent
proof that ChatGPT, iOS or a natural person performed it. Only an admitted
executor accepts question/disconnection events, and the answered question must
precede the disconnection report. Cancellation stops the remaining bounded
effect and cannot be undone by a replay.

The thread waits for the two client events. On wakeup it reobserves the local
HEAD, TREE, full local branch ref, tracked cleanliness, exact work-unit bytes,
loaded executor sources, current credential validity and journal checkpoint.
Its work-unit fence prevents duplicate admission; the existing handler fence
serializes actual effects across work units. A blocked work unit does not block
independent work units. These fences protect cooperating local API executors;
they do not establish a GitHub-wide writer lock or remote-ref observation.

The existing `ingest` transaction, responsibility protocol, immutable receipt,
provenance, inbox and audit chain implement the effect. The deterministic child
request ID is derived from the immutable handoff. After an ambiguous response,
read `work_unit_status` before any replay. Adapter startup restores unresolved
checkpoints with current credentials, a real new process/run identity and a
fresh subject check. A committed child effect is reconciled by the existing
receipt; its bytes are not rewritten. A journaled state transition whose
checkpoint is missing or corrupt is isolated rather than guessed.

## Verification and remaining product gate

`python3 -B -m unittest -v tests.test_work_unit_handoff` runs separate HTTP client,
server and competing-writer processes. It covers question/answer, actual client
SIGKILL, unchanged executor continuation, Explicit-Cancel, HEAD/dirty-byte drift,
competing writer, independent scope, conflicting replay, response loss, server
restart, committed-effect/checkpoint loss and fresh-readback tampering.
`make test` includes these controls in the existing end-to-end target.

Those controls establish their local adapter scope. The original #445 product
acceptance still requires the actual ChatGPT-client task/event trace, an
installed admitted productive handoff for the intended user task, and fresh
independent post-disconnection readback. A loopback adapter is not an iOS
deployment or a general authenticated chat-task executor. Scratch-host lifetime
does not establish a persistent production host.

`productive_continuity_verified=false`, `client_behavior_changed=false` and
top-level `EFFECT_ACK_DONE=false` remain explicit until that witness exists.
`owner_manual_restart_count` and `duplicate_effect_count` remain `null`; the
controls report actual process IDs, receipt bytes and journal write/replay
records instead of inventing product counters.
