<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Digital Twin scheduling

Ingolf Lohmann requires every scheduled task to exist in the Digital Twin and
remain synchronized with its executing scheduler. V1 adds a durable private
registry and bounded calendar planner to the existing authenticated API shim.
Private task prompts remain outside public Git. The executor projection can
import an existing ChatGPT automation through its authorized adapter. This code
does not create an automation, call a calendar or start a background dispatcher.

## Native event contract

`policy/QIKVRT_DIGITAL_TWIN_SCHEDULE_EVENTS_CONTRACT_V1.json` and
`schemas/qikvrt_schedule_events_v1.schema.json` define the native versioned
contract. `src/qikvrt_digital_twin_schedule_events.py` adds the native semantics
to the existing private SQLite storage and uses the same authenticated API shim.
The projection alone cannot implement native create/delete/tombstone, selectable
DST folds, role-bound connector-neutral receipts or append-only replay.

Event, operation and receipt identities are domain-separated SHA-256 identities
over a stable namespace/key. Configuration changes preserve the event identity.
An exact integer `expected_version` is mandatory. Create accepts only unused
identities at version 0; update replaces a live event's complete configuration;
delete stores a versioned tombstone with `value=null`. Tombstones cannot be
resurrected or reused. An identical operation ID and byte-identical request are
idempotent. Different bytes under that ID fail closed, including boolean/integer
aliases that Python might otherwise compare equal.

Each accepted operation writes both the event and a contiguous ledger record
in one `BEGIN IMMEDIATE` transaction. An independent post-commit read must match
the exact successor. If another writer advanced it, the request returns HOLD;
the original operation remains reconstructible and can be queried/retried by its
same ID. A historical retry returns its original subject and fresh current state,
and cannot promote historical success into current-subject evidence.

Time binds canonical UTC seconds, a canonical local timestamp, the supplied IANA
key, explicit fold 0/1 and the exact TZif SHA-256. Invalid civil times, naive UTC
timestamps, offsets/subseconds, noncanonical folds and TZif drift fail closed.
Daily/weekly recurrence follows the civil clock; hourly recurrence uses elapsed
UTC intervals. Recurring gaps are skipped and ambiguous times use the declared
FIRST or SECOND fold exactly once. Only the explicit bounded subset is supported.
The planner returns future slots without executing them.

Python documents both the fold behavior and the lack of cross-version timezone
reproducibility when only a key is serialized. Here `ZoneInfo.from_file` uses the
same bytes that are hashed, and drift is rejected:
https://docs.python.org/3.12/library/zoneinfo.html

Snapshots use compact UTF-8 JSON with sorted keys, no BOM/newline, integer-only
numbers, closed structural fields and bounded depth/size. Events sort by UTC
start then ID, followed by tombstones sorted by ID; planned slots sort by slot
then ID; ledger records use contiguous sequence; receipts sort by ID. Replay
reconstructs every CAS successor and predecessor hash before writing an empty
same-subject native store, then requires byte-identical export. Replay is local
history reconstruction and does not execute historical jobs.

Sync receipts bind the exact event version/hash, source repository/role/head/tree
and either an opaque connector/resource or an independently bound repository
target. An optional observation contains time, target revision and the complete
readback. Contradictory bytes under the same receipt ID or immutable target
revision fail closed. Transport-only receipts never establish an effect. Matching
observations establish consistency of supplied data; the authorized adapter owns
their remote authenticity. The implementation always leaves external effect,
connector authenticity, pole equality and general EFFECT_ACK_DONE unverified.

Events survive a code-head change as data. Active evidence requires the current
head/tree and current event version/hash. Old receipts remain historical.
Authority and Mirror have separate storage namespaces, even for the same
repository name. Reconstruction across repository/role subjects is rejected.
`TRANSPORT_ACK != EFFECT_ACK` and `PREDECESSOR_EVIDENCE_TRANSFER=false` apply.

Native runtime bindings are explicit:
`QIKVRT_SCHEDULE_ROLE`, `QIKVRT_SCHEDULE_HEAD`, `QIKVRT_SCHEDULE_TREE`, together
with the existing allowed repository, authenticated principal and private root.
These supplied bindings do not attest a deployed binary or independently observed
repository head. A deployment adapter must establish that evidence separately.

| Method | Native suffix after `/api/digital-twin/v1/schedule-events` | Purpose |
|---|---|---|
| GET | `/contract` | Versioned machine contract |
| GET | empty or `/{event_id}` | Current private event/tombstone and active receipts |
| POST | `/operations` | Create/update/delete with operation ID and exact CAS |
| POST | `/sync-receipts` | Import connector-neutral consistency evidence |
| GET | `/snapshot` | Canonical snapshot as a string |
| POST | `/replay` | Restore `{"snapshot":"..."}` into an empty exact-subject store |
| POST | `/plan` | Next slots after `{"after_utc":"...Z"}` |

Run `make digital-twin-schedule-events-test` for native roundtrip, timezone/DST,
idempotency, competing connections, post-commit races, deterministic ordering,
tombstones, replay tampering, conflicting receipts and authenticated HTTP.

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

## Separate repair and runtime acceptance

Local import/readback is separate from Main integration, a public Universal
Terminal carrier and continuous bridge activation. A deployed runtime must expose
authenticated ingress before productive synchronization can be claimed. This
candidate creates no real user event or external-calendar success receipt.
The existing missing Digital Twin reference-model import remains owned by PR
#422; this implementation reuses the executable API shim and does not duplicate
or silently substitute that separate model repair.

Run `make digital-twin-scheduling-test`. It covers restart persistence, exact
configuration identity, concurrent writers, pause/readback, freshness and
version conflicts, principal isolation, unsafe paths, DST and real HTTP ingress.
