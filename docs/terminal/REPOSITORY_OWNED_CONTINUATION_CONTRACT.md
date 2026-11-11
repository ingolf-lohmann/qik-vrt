# QIK-VRT: Repository-owned continuation and recovery contract

Status: normative candidate, pending exact-HEAD CI and independent review.

## Authority and direction
The authority repository `ingolf-lohmann/qik-vrt` owns work-unit identity,
writer identity, persisted progress, next action, recovery and effect evidence.
A ChatGPT session is a replaceable adapter, **not** the scheduler, owner of
state, or evidence of completion. A client/context boundary must never
implicitly close a repository work unit.

## Error transition (TEMDD, fail-closed)
For a parse, syntax, schema, type, workflow, transport or runtime error:

1. Record the exact writer/work-unit/head identity and the failing input,
   operation, error class, evidence reference and time when available.
2. Forbid the unsafe effect; never manufacture an EAP acknowledgement.
3. Classify the cause: internally diagnosable, external authorization, or
   unknown. Unknown remains unknown; it is not success.
4. For internally diagnosable faults, persist a bounded diagnostic/recovery
   work unit, select the smallest reversible repair, and re-enter the **same
   writer's successor** after a verified mutation/readback.
5. For external authorization, retain a resumable pending work unit, expose
   the required external gate and avoid unauthorized action.
6. After every repair, perform exact-HEAD tests, integrity verification,
   independent readback and evidence linkage. A changed HEAD invalidates
   prior exact-HEAD claims.
7. Repeat until independent effect acknowledgement or an explicitly typed
   external gate. A chat response, timeout, context switch or missing
   permission is not an EAP DONE transition.

## Non-negotiable invariants
- No unverified DONE or `effect_ack_done=true`.
- No `next_action` that executes a protected effect while externally blocked.
- A malformed receipt returns diagnostic classification, not a fabricated
  successful action.
- Never spin or commit indefinitely on the same failing fingerprint:
  bounded retry, causal evidence and escalation must remain visible.
- Never bypass GitHub workflow approval, reviews, integrity, host identity,
  writer fencing, or the independent EAP verifier.
- The repository's existing watchdog, EMP, EKM, TEMDD and EAP paths are the
  integration targets. No parallel client-owned scheduler.

## Acceptance
A qualifying proof needs native exact-HEAD CI including negative tests,
a demonstrated error-to-repair-to-successor repository mutation, integrity
trio verification, independent review, and independent EAP/host readback
for productive claims. Until then the status is OPEN, not DONE.
