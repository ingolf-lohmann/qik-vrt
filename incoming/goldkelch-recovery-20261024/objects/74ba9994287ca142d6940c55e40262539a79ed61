<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Digital Twin scheduling

Ingolf Lohmann requires every scheduled task to exist in the Digital Twin and
remain synchronized with its executing scheduler. V1 adds a durable private
registry and bounded calendar planner to the existing authenticated API shim.
It does not start a second timer or silently reproduce private task prompts in
public Git. The existing ChatGPT automation remains the sole executor for the
initial regulatory watch.

The registry uses the executor's stable task ID and binds the exact prompt,
title, VEVENT, IANA timezone, timing mode and enabled state by SHA-256. Source
update and run timestamps are observation metadata. A calculated next slot is
planning evidence, not proof that the hosted scheduler has run. Flexible and
condition-watch timing remains controlled by the hosted executor.

## Synchronization transaction

1. Read the actual executor task through its authorized connector.
2. Import that snapshot with `expected_revision` and a fresh observation time.
3. Prepare the intended change against the exact local revision.
4. Apply the returned `automations.update` arguments to that same task ID.
5. Read the executor again; a transport acknowledgement is insufficient.
6. Reconcile the exact desired configuration and read the local registry again.

Prepared changes remain `AWAIT_EXECUTOR_READBACK` until matching source bytes
arrive. Concurrent or stale updates, source timestamp rollback, same-version
configuration collisions and mismatched prepared readbacks fail closed. A
failed or ambiguous external update requires source reobservation before any
retry. There is no background polling loop. Changes made outside this adapter
are only known after an actual import or authenticated bridge event. Provider
event delivery and uninterrupted bidirectional synchronization require fresh
runtime evidence; implementing the ingress does not establish that wiring.

The incoming snapshot's remote authenticity remains the caller/authorized
connector's responsibility. The server authenticates its caller with the
existing scoped, expiring bearer credential; it does not turn arbitrary JSON
or a caller-supplied timestamp into authenticated platform evidence.

## Existing transport

Use `make run-api` and its existing repository/principal/credential configuration.
Scheduling lives on the local QIKVRT shim, not on GitHub's dispatch API:

| Method | Path | Operation |
|---|---|---|
| GET | `/api/digital-twin/v1/schedules` | Private registry readback |
| GET | `/api/digital-twin/v1/schedules/{task_id}` | Exact task readback |
| POST | `/api/digital-twin/v1/schedules/reconcile` | Import fresh source snapshot with CAS |
| POST | `/api/digital-twin/v1/schedules/prepare` | Prepare a change; no executor mutation |
| POST | `/api/digital-twin/v1/schedules/plan` | Calculate next slots; no dispatch |
| POST | `/api/digital-twin/v1/schedules/bridge` | Source read, CAS existing task, fresh source readback, reconcile, independent local read |

All scheduling requests require the existing authenticated principal and
repository scope. GETs also require authentication. Runtime database files
are mode 0600, excluded from Git, isolated by repository/principal and checked
against unsafe symlinks. The CLI reuses the same registry implementation:

```sh
python3 -B -m src.qikvrt_digital_twin_scheduling \
  --root /path/to/private/node --repository owner/repo --principal operator read
```

`reconcile`, `prepare` and `plan` consume one bounded closed-schema JSON object
on stdin. The machine-readable policy specifies the supported VEVENT subset.
Unsupported schedules hold without approximation. Daily/weekly local time
survives DST; nonexistent slots are skipped and repeated slots use the first
fold. An explicit `Z` DTSTART keeps its UTC clock across DST, independent of
the executor's default timezone. Native execution of scheduled tasks is outside
this registry's authority.

## Initial binding and acceptance

`state/digital_twin/QIKVRT_EU_REGULATORY_WATCH_SCHEDULE_BINDING_V1.json` binds the
real watch's metadata and configuration digest without its private full prompt.
Local import/readback is separate from Main integration, the public Universal
Terminal carrier and continuous bridge activation. That runtime must expose an
authenticated ingress before productive synchronization can be claimed.
The existing missing Digital Twin reference-model import remains owned by PR
#422; this implementation reuses the executable API shim and does not duplicate
or silently substitute that separate model repair.

Run `make digital-twin-scheduling-test`. It covers restart persistence, exact
configuration identity, concurrent writers, pause/readback, freshness and
version conflicts, principal isolation, unsafe paths, DST and real HTTP ingress.

## Event-driven continuous bridge adapter

The existing scheduler remains the sole executor. Its authorized provider sends
one `/bridge` request on a configuration/source event, resume or process restart.
The body contains `task_id`, a stable `event_id`, `expected_revision` and
`changes` (empty for observation). An event ID binds those exact request bytes;
reordering fails against the current local revision. The same event may be
replayed with the original request; replay still reads the source freshly and
checks local state. A changed source requires a new event and current revision.
No timer, polling thread, job execution, create endpoint or second scheduler is
introduced. The integration operator must connect the existing source's event
delivery/restart lifecycle to this ingress, preserving one active binding per
repository/principal/task. This delivery is not established by the tests.

The shim builds `HttpScheduleExecutor` from private server configuration:

- `QIKVRT_SCHEDULE_EXECUTOR_URL`: trusted HTTPS existing-task collection URL
  (HTTP on `127.0.0.1` only for local integration).
- `QIKVRT_SCHEDULE_EXECUTOR_TOKEN`: canonical `b64url:` scoped gateway credential.
- `QIKVRT_SCHEDULE_EXECUTOR_TOKEN_EXPIRES_UTC`: expiry, checked before every call.

URLs and credentials cannot be supplied in the bridge request. Redirects and
unbounded/malformed responses are rejected. Each request carries the exact
`X-QIKVRT-Repository` and `X-QIKVRT-Principal` scope. `GET {URL}/{task_id}` returns
a closed envelope with `repository`, `principal`, `executor` (exactly
`chatgpt_automations`) and `observation`. The observation has exactly `task`
(the existing `ScheduleSourceTask`), `version` (opaque, 1–256 ASCII characters
from `[A-Za-z0-9_.:-]`), `observed_at` and `conditional_update` (boolean).
The timestamp must be sampled during the actual read, after the bridge
initiated it. Configuration and `updated_at` bind the opaque version; rollback
and contradictory bindings hold. Last/next-run metadata can change
independently of configuration.

For a change, `PATCH {URL}/{task_id}` sends `{"changes":{...}}`,
`If-Match: "opaque-version"` and `Idempotency-Key: event_id`. The gateway must
atomically reject a version mismatch (412) in the executing scheduler's own
authority domain, update only that existing ID and return the same envelope.
It must authenticate the provider and enforce scope. A lock held only in the
Twin or a last-moment read followed by an unconditional update is insufficient.
The ordinary ChatGPT `automations.update` tool has no exposed conditional
version parameter; a gateway backed solely by that tool must advertise
`conditional_update:false`, permitting observation but blocking mutation.
This contract does not invent an installed provider gateway or platform CAS.

The private SQLite journal persists `PREPARED` before the effect and
`ATTEMPTED` before the outbound call. Concurrent bridge/manual writers are
excluded. A restarted `PREPARED` transaction freshly validates its original
source before claiming the effect. An `ATTEMPTED` transaction never sends
another update; matching fresh source bytes can complete reconcile. If the
effect remains ambiguous or drifted, the task holds pending explicit provider
recovery evidence. A matching configuration establishes observed state, not
causality of an ambiguous write. Journal revision advances atomically with
reconcile so a crash before `VERIFIED` can resume safely.

Every success returns `CONFIGURATION_READBACK_VERIFIED` for one authenticated
transaction, with event, task, source version, local revision and configuration
digest. `executor_mutation_acknowledged` records only a successful update
response; it is not the effect witness. An independent connection reads the
persisted task and observation again. `local_dispatch_authorized`,
`continuous_bridge_verified` and `effect_ack_done` remain false. Productive
continuous verification additionally requires the actual authenticated source
event carrier, restart/redelivery, real executor CAS, source/local readback and
drift witnesses for the deployed exact subject. The committed test gateway
proves the adapter flow only; the earlier regulatory-watch roundtrip remains
historical evidence and is not promoted into productive bridge verification.
