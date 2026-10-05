<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Private personal transitions on the native CAS carrier

This PR453 review candidate integrates the exact PR429 carrier
`e02529936bdeed3e3d2c71097c3b9dde4f206467`. It adds a semantic adapter to its
existing `ScheduleEventStore`, private SQLite file, expected-version operations,
append-only ledger, scoped expiring bearer authentication and HTTP shim. There
is no second Twin, database, scheduler, worker, polling loop or dispatch service.
Personal goals are typed native event payloads. Their native scheduling flag is
always disabled and recurrence is null; priority is an effect-free projection
for an existing admitted executor. Preparing an action grants no execution right.

The actual Owner profile, private runtime connection, live restart observation
and actual QIK-VRT human delivery are unverified. This implementation remains
`REVIEW_CANDIDATE_NOT_ACTIVE`; `EFFECT_ACK_DONE=false`. Local synthetic tests
cannot activate that profile or establish deployment, human understanding,
usefulness, acceptance of generated code or unlimited context coverage.

All endpoints below use the existing authentication and rate limiter. Repository,
role, head, tree and principal come from existing server configuration, never
from an input-selected storage scope. `QIKVRT_PERSONAL_CHANNELS_JSON` configures
channel IDs with an exact principal and supported `languages` and `modalities`.
An empty configuration means no admitted human channel. An authorized alternative
is reported only when it exists in this configuration.

| Method | Path after `/api/digital-twin/v1/personal` | Result |
|---|---|---|
| GET | `/contract` | Executable requirement fields and configured readback capability |
| GET | empty or `/{requirement_id}` | Private goals, readiness, feedback and current action boundary |
| POST | `/inputs` | One closed input/goal/feedback transition with exact expected version |
| POST | `/prioritize` | Deterministic priority reasons at the supplied canonical UTC instant |

Input envelopes have exactly `schema=qikvrt_personal_input_v1`, `input_id`,
`requirement_id`, `expected_version`, `transition` and `data`. IDs are SHA-256
identities. `src/qikvrt_digital_twin_personal.py` is the executable semantic
validator; `/contract` lists the 17 mandatory requirement fields from PR453.
Explicit null/incomplete dispositions remain OPEN. Empty unresolved decisions
do not manufacture an Owner question. A typed proposal does not become an
accepted requirement. Routine refinement precedes an explicitly necessary
unresolved Owner choice. Structural completeness is not proof that a human's
natural-language predicate is adequate; reviewed source semantics remain the
authorized caller's responsibility.

| Transition | Exact `data` fields | Scoped behavior |
|---|---|---|
| `input` | strand_id, requirement, priority, context, input | Initial revision, independent stable identities, private persistence |
| `correct` | requirement, priority, context, input | Revision +1 and hash of superseded requirement; invalidate pending action/feedback |
| `cancel` | reason | Persist terminal cancelled state, disable goal, reject later reactivation |
| `observe` | blocker, retry_condition, procedure_sha256, context | Reobserve criteria/context; material change queues feedback; unchanged state is NOOP |
| `prepare_action` | action_id | Bound proposal for the existing executor, never execution/admission |
| `feedback_attempt` | feedback_id, attempt_id, channel_id, transport_ack | Exactly one current configured delivery attempt; DELIVERY_PENDING |
| `feedback_readback` | feedback_id, attempt_id | Invoke independently configured channel reader; input contains no delivery assertion |
| `human_feedback` | feedback_id, response, scope_acceptance | Preserve actual supplied feedback; scope acceptance does not imply delivery or global DONE |

The priority object has `main_goal`, `continuing_goal`, `deadline_utc`, `impact`
(0–5) and `reason`. A declared deadline within 24 hours takes precedence, then
declared impact, the main goal and stable identity. The context object has
`channel_id`, `language` and `modality`. Unknown channels, languages and modalities
remain explicit coverage gaps; other strands are neither cancelled nor replaced.

Corrections and observations preserve historical inputs and receipts in the
same native ledger. Competing versions fail CAS; repeated identical committed
inputs return historical replay, never a new effect receipt. Reobserving an
unchanged blocker does not append a ledger entry or recreate a notification.
A changed code subject cannot inherit a pending action or active delivery state.
Requirements for an unobserved Authority subject remain HOLD in a Mirror runtime.
Native operations cannot overwrite the reserved personal payload through the
generic HTTP writer. HTTP snapshot replay containing personal records requires
a trusted backup path; offline native replay rejects a different principal.

A delivery integration must explicitly install the callable
`server.qikvrt_personal_channel_readback(binding)` on the existing shim server.
This candidate installs no production channel reader and performs no outbound
delivery. The callable must perform bounded independent readback through the
configured authorized channel, authenticate that channel, and return exactly
`principal`, `channel_id`, `attempt_id`, `message_sha256`, `delivered`,
`observed_at_utc` and `receipt_id`. Bindings must match the pending attempt;
observations must be fresh and no earlier than the recorded attempt. Missing,
negative or unconfigured readback keeps delivery pending. Contradictory, stale
or cross-principal readback is rejected without changing the ledger. The
backend's authenticity is an integration/admission responsibility, not proved
by accepting a matching dictionary. A request cannot inject a callable or assert
delivery. A correction/cancellation that wins CAS during a readback prevents
that observation from becoming a new current goal version.

`make digital-twin-personal-test` executes all 12 PR453 scenarios plus negative
controls. The HTTP shim is authenticated, the service process really restarts,
and a separate local HTTP fixture distinguishes accepted transport from channel
delivery. Fixture inputs contain no real correspondence, credentials or personal
payloads. These are candidate tests, not an Owner's private restart/delivery
receipt. The proposal and Work Unit retain the live-runtime HOLD until those
actual evidence predicates are established under separate admission. Merge and
deployment are outside this task.
