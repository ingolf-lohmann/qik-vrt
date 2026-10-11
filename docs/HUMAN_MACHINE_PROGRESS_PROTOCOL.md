# QIK-VRT Human–Machine Progress Protocol

## Purpose

During repository, build, verification, publication, deployment, or GitHub Actions work, every artificial-cognitive client MUST behave like a visible engineering client rather than a conversational black box.

## Mandatory live format

Before and after every discrete GitHub action, and between every observed workflow, job, or step transition, the client MUST emit a fresh compact progress frame:

```text
Repository: <owner/repo>
Branch: <branch-or-ref>
Commit: <sha-or-pending>

[██████░░░░] 60%

✓ completed step
⟳ current step
□ pending step

BLOCKER:
<none or concrete blocker>

NEXT:
<next executable action>
```

A GitHub action includes every connector/API mutation or read that advances the task: branch creation, file read, file write, commit, PR creation, workflow observation, job inspection, log inspection, review, merge, ref update, release, publication, and verification. Silence between such actions is prohibited. A later summary does not compensate for a missing intermediate frame.

## Rules

1. Work first; explain only what is necessary for execution or a concrete blocker.
2. Show repository, branch/ref, and commit SHA whenever known.
3. Show one progress bar with an integer percentage from 0 through 100.
4. Distinguish completed (`✓`), running (`⟳`), pending (`□`), failed (`✗`), and blocked (`!`) steps.
5. Report only verified facts. Never convert transport success, an exit code, or a model assertion into `PASS`, `DONE`, publication, deployment, merge, or symmetric canonicality.
6. Emit a new progress frame before and after every discrete GitHub action and at every workflow/job/step state transition. No batching, omission, or replacement by prose is permitted.
7. On completion, show the final commit/merge/release identifiers and all decisive checks.
8. On failure, name the exact failing workflow, job, step, ref, SHA, error, and next remediation action.
9. Machine-readable state MUST be written to `AI_PROGRESS.json`; the human-readable projection MUST be written to `AI_STATUS.md` whenever a persistent repository workflow owns the operation.
10. All AI-specific adapter files MUST point to this protocol and may not redefine it inconsistently.
11. `REUSE_BEFORE_CREATE` applies to status handling: existing status emitters, observers, workflows, and projections MUST be extended before a parallel mechanism is introduced.
12. **Observation is not a snapshot or terminal handoff while a follow-up action exists.** Any observation that yields an executable, expected, or causally required successor action keeps the owning operation in `RUNNING` (or `WAITING` only while an external effect is genuinely pending). The client MUST execute or continue that successor within the same round trip, then observe its effect and verify readback. It MUST NOT freeze, summarize, hand off, or present the intermediate observation as completion merely because a read succeeded.
13. **Continuation is the default after a non-terminal observation.** The round trip is `OBSERVE -> DIAGNOSE -> ACT -> OBSERVE EFFECT -> VERIFY READBACK -> CONTINUE` until a scope-bound terminal state is actually established. A snapshot is admissible only when no executable successor remains for the owned scope, a concrete blocker requires external authority/input, or an explicitly bounded observation window has ended.
14. Observation frequency MUST be event- and workload-sensitive rather than a fixed polling ritual. New input, active effects, unresolved causal defects, expected receipts, or successor-carrier movement increase observation pressure; unchanged stable state is deduplicated. Monitoring activity alone is not progress.

## Binding client continuation procedure

Owner instruction: Ingolf Lohmann, 2026-10-11. This procedure is mandatory for
all repository clients. Preserve the existing authorized repair, integration
and exact-host delivery goal after handoffs, compaction or status questions.
Do not ask for the same authorization again. Inspect applicable existing
repository, connector, CLI and Mesh routes before declaring execution absent;
retain operation, HTTP method, target/account binding and exact denial evidence.
A locally absent CLI or empty project filter alone is insufficient.

Continue each safe, deterministic, authorized successor, including useful
preparation and persistence while an external effect is blocked. Keep GitHub
REST-only routing, secure credentials and protected governance. Never create a
proxy executor or synthetic trigger to manufacture capability. Preserve issue
evidence, perform NOOP for unchanged causal failures, and read back ambiguous
effects before another effectful attempt.

Before a terminal handoff, run the existing read-only validator:
`python3 -B tools/ai_handoff.py --client-receipt <receipt.json>`.
Its `qikvrt-client-continuation/1` receipt contains:

- `subject`: exact `repository`, `head` and `tree`; `authorization`: `granted`
  and its non-secret `source`; `requested_authorization_again: false`.
- `inventory`: non-empty evidence locators or concrete absence/denial receipts
  for `repository`, `connector`, `cli` and `mesh`. Inspect only relevant existing
  routes; do not enumerate unrelated credentials or disclose secret values.
- `next_actions`: each exact-subject action's `route` (`connector`, `cli`,
  `mesh`), `service`, `operation`, HTTP `method`, `transport`, capability
  `evidence`, callable binding `observed_method`, `observed_operation`,
  `observed_repository`, and boolean `authorized`, `safe`, `deterministic`, `callable`,
  `authenticated`, `permitted`, `admitted`. Any action satisfying all predicates
  requires `state: CONTINUE`. Governance failure keeps `admitted: false`.
- `attempts`: `effect_count` (zero or one per causal attempt), `current` and
  optional `previous` causal evidence, `ambiguous_effect` and
  `readback_before_effect`. An effectful attempt also binds its admitted `action`
  using the same predicates and observed operation binding as `next_actions`.
  A causal attempt cannot execute twice. Each causal evidence object binds SHA256 digests for
  relevant `subject`, `error`, `cause` and `capability`. Observation timestamps
  and unrelated lifecycle commits are excluded. Identical failure evidence
  requires zero effects. Materially changed evidence alone does not authorize
  an effect; all action predicates must still hold.
- `readback.repository`: current `repository`, `ref`, `head`, `tree`, `source`;
  `readback.delivery`: exact `hostname: raumzeitterminal.de`, `source` and
  `state` (`UNKNOWN`, `PENDING`, `VERIFIED`). Missing access stays explicit.
- `state`: `CONTINUE`, `BLOCK`, `DONE` or `OWNER_CHOICE`. An externally pending
  execution can retain `CONTINUE` with its `pending_execution` evidence. BLOCK
  requires a concrete `blocker` with `operation`, `reason`, `evidence`,
  `retry_condition` and `next_action`, after exhausting safe authorized work.
  OWNER_CHOICE requires at least two distinct `owner_choices`. DONE requires
  current Main and exact-host independent working-software/TLS readbacks bound
  to the same subject; no open executable successor may remain.

The validator checks receipt consistency only. Evidence locators and predicates
must come from actual observations; a fabricated or stale receipt is forbidden.
Exit zero, `CLIENT_HANDOFF_CONSISTENCY=VALID`, local fixtures and green candidate
tests do not establish a live effect. Independently read back the relevant
provider results and exact HEAD/TREE. Persisting the rule does not establish
Main integration, adoption by another client or deployment. Regression cases
run in the existing `make ai-runtime-contract` gate without network or secrets.

## Repository runtime objective

The repository is the durable runtime authority. Chat sessions are disposable transport surfaces. Required tools, exact versions, checksums, bootstrap logic, cache contracts, provenance, tests, and recovery procedures MUST accumulate in the repository so that a new authorized client can reconstruct the runtime without depending on prior conversation memory.

The repository runtime MUST improve cumulatively by reusing and refining existing components. Tool caches accelerate execution, while committed locks, manifests, provenance, and bootstrap code preserve reproducibility. Credentials, mutable authentication state, and unverified binaries MUST never be persisted as runtime cache content.

## State semantics

- `IDLE`: no live operation owns the durable root handoff snapshot.
- `RUNNING`: work is actively progressing, including continuation after any non-terminal observation with an available successor.
- `WAITING`: an external system is running or a review/approval is pending and there is no immediately executable local successor.
- `PASS`: all declared gates for the stated scope are verified.
- `BLOCK`: a concrete blocker prevents continuation.
- `FAIL`: an executed gate failed.
- `TIMEOUT`: observation ended because its declared time bound expired.
- `CANCELLED`: the operation was explicitly stopped.

`PASS` is scope-bound. It MUST identify the verified repository, ref, source SHA, checks, and evidence.

## Durable multi-scope handoff

`AI_PROGRESS.json` uses the durable `qikvrt-ai-progress/3.1` variant of
`schemas/human_machine_progress.schema.json` when several repository scopes
must be represented together. The root snapshot MUST be `IDLE` when no live
operation owns it and MUST label its ref and SHA as projection-input
provenance, not as current remote state.

The projection input MUST be bound by a committed
`portable-git-object-closure`. Its capsule contains the exact source commit
payload, every Git tree object needed to traverse the selected paths, and the
selected blob payloads. Validators MUST recompute every Git SHA-1 using the
canonical object header, recompute every payload SHA-256, traverse each path
from the commit's root tree, reject missing or surplus objects, and verify the
capsule file's own byte, SHA-256, and Git-blob binding. When the declared
source commit exists locally, all embedded objects MUST additionally be
byte-identical to local Git. The proof remains bounded: it does not establish
complete history, a current remote ref, repository synchronization, merge,
publication, deployment, or repository-wide `PASS`.

Every scope has its own evidence, boundary, percentage and effect state. A
scope-specific `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE` MUST remain nested
under that scope and MUST NOT promote an incomplete sibling scope or the
top-level repository effect state. When the top-level effect state is
`EFFECT_ACK_CONTINUE` or `EFFECT_ACK_BLOCK`, all top-level release claims MUST
be false. Every nested `EFFECT_ACK_DONE` scope MUST bind its own repository,
ref, source SHA, checks and evidence; it cannot borrow the root projection
input SHA.

The durable projection MUST name a checkable `projection_owner`. A later
workflow MAY supersede that owner only by materializing a conforming snapshot
that preserves all still-authoritative bounded scopes. A historical workflow
MUST NOT key ownership solely to the continued existence of one receipt.

The tracked snapshot MUST not freeze transient claims such as a pull request
being open, checks running, a merge pending, or repositories synchronized
unless a durable repository receipt binds that exact assertion. A live watcher
is telemetry, not exact-head proof: current PR, check, merge, promotion, or
synchronization claims require current commit/run/check evidence. In
particular, a live observation with a known successor MUST remain live state
and MUST NOT be projected as a terminal snapshot.

## Communication boundary

The client MUST not answer with long explanations when it can perform the next executable action. Explanations are subordinate to execution, evidence, progress, and recovery.
