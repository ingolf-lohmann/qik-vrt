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
are only known after an actual import; V1 does not claim an unimplemented
platform event hook or uninterrupted bidirectional synchronization.

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
