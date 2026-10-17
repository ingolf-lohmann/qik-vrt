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

## Immediate execution — Owner principle of 2026-10-13

> Was du heute kannst besorgen, das verschiebe nicht auf morgen, sondern erledige es unmittelbar, denn alles andere war, ist und wird inakzeptabel sein.
>
> q.e.d.
> Ingolf Lohmann

Apply this principle now: execute each safe, deterministic, already authorized
and actually callable successor within the current work ring. Complete its
applicable tests, persistence and fresh effect readback before a handoff.
The existing client gate rejects terminal return while an executable successor
remains; reuse it. A concrete external or protected-authority blocker retains
the open task, causal evidence and retry condition. Independent executable
work continues, and unchanged failed effects remain NOOP. The principle adds
no permission scope and proves no unattended runner or other-client adoption.
Its normative source is the existing recursive policy's
`self_application_working_rule.immediate_execution_principle`.

## Binding client continuation procedure

### Knowledge and correction continuity — Owner correction of 2026-10-16

Knowledge loss itself is the defect, regardless of when a handoff happens.
Apply `policy/QIKVRT_EPISTEMIC_CONNECTABILITY_CONTINUITY_V1.json` through the
existing client receipt and validator. Carry established results and their
source identities, granted authorization, unknowns, scope limits, failures and
corrections as well as open tasks. Reuse unchanged exact-source evidence;
reobserve mutable state when the task requires it.

`knowledge` is a list of records with unique `id`, nonempty `epistemic_class`,
`scope` and `statement`, a nonempty `subject` object and `evidence` locator list,
optional `supersedes` record IDs, and `record_sha256`. The digest is SHA-256 of
the entire record without `record_sha256`, encoded as UTF-8 JSON with sorted
keys, compact separators, `ensure_ascii=false` and finite JSON values. Every
declared predecessor record must remain byte-equivalent under this encoding.
Do not silently edit, drop or promote its epistemic class, scope or statement.
Corrections append a new record referencing the retained original; orphan and
cyclic correction references are rejected. Record hashes bind declared bytes;
they do not authenticate evidence or establish that a statement is true.

Historical writer-encoding repair uses the explicit versioned contract
qikvrt-knowledge-historical-encoding-migration/v1 in the existing policy's
knowledge_continuity.historical_encoding_migration. It is opt-in through the
receipt's knowledge_encoding_migration, bound to the exact SHA-256-verified
immediate predecessor. Each of at most 128 listed records declares the codec
json-sorted-spaced-utf8/v1, its original digest and its canonical compact digest.
That historical codec is finite UTF-8 JSON with sorted keys, ensure_ascii=false
and separators comma-space and colon-space. No other historical codec is tried.

Every listed record must occur exactly once in the pinned predecessor and the
successor with identical fields and stored digest. Both declared digests are
independently recomputed. Only the in-memory reader view uses the recomputed
compact digest for the existing schema, correction-graph and continuity checks;
the original receipt and all stored records remain unchanged. New records must
use the ordinary compact encoding and cannot enter the historical mapping.
An unpinned migration, an undeclared or malformed codec, a different payload,
duplicate mapping, missing record or unlisted invalid digest remains BLOCK.
An old receipt without this declaration remains rejected under the strict gate.
Successful compatibility checking does not change any recorded epistemic class,
grant a permission, transfer predecessor PASS or prove runtime/delivery success.

When a durable predecessor is available, pin its exact repository-relative
`receipt_path` and `receipt_sha256` under `previous_run`. Its `execution_id`
must match. The existing provenance Work Unit may carry `execution_id`,
`knowledge` and `work` directly; no separate memory service is required. The
validator reads only that explicit file (at most 2 MiB), rejects changed bytes and
paths outside the repository, and derives inherited knowledge and open work
from it. Omitting those from the caller's `previous_run` summary cannot erase
them. Keep this pin across handoffs and resolve a missing predecessor before
claiming that reconstruction succeeded. Historical receipts without knowledge
remain readable; their absence of a snapshot is not evidence of full retention.

Keep observations local to their measured scope. For example, absent process
environment variables establish only absence in that process, not absence of
an existing GitHub Actions secret or a provider credential. The current IONOS
Cloud-v6 inventory consumer's GET-only scope does not determine the token's
other rights. IONOS Cloud DNS documents `IONOS_TOKEN` bearer authentication:
https://docs.ionos.com/sdk-go-bundle/sdks/dns . Actual token rights and admitted
execution remain separately unverified until observed. A generic failure must
not overwrite this distinction as a global access-absence claim.

These are continuity checks on supplied records. They do not prove that an
initial snapshot contains all human/model knowledge, that another client used
the gate, that historical PASS applies to a changed subject, or that the product
was delivered. Retain the exact-host and live-effect gates below.

### Anticipated transitions — Owner instruction of 2026-10-15

Clients observing an emerging transition MUST use the existing client receipt
to retain its indication, activation conditions, available preparation and
independent alternatives. Execute admitted preparation in the current work
ring even while the later effect is blocked. Reassess on relevant new evidence
or human corrections; keep original task identity and open obligations.

Add `input_sha256` to the receipt, recomputed from the actual task inputs and
human corrections. Its `transition_plan` contains the same `input_sha256`, the
exact current `subject`, and `transitions`. Each transition has a unique `id`,
nonempty indication `evidence`, an `activation` list of unique condition `id`,
strict boolean `satisfied` and nonempty `evidence`, a target `action`, and a
`preparation` list. Target and preparation actions use the existing
`next_actions` admission fields and exact operation binding. Conditions needed
for preparation completion belong in the target's activation list. A transition
condition never supplies authorization, credentials, callable capability or
governance admission.

For a previously failed planned action, supply its `retry.current` and
`retry.previous` using the existing subject/error/cause/capability digests.
Unchanged causal evidence suppresses that action; observation clocks or a new
input digest do not admit a retry. Actual effects still require the ordinary
`attempts` gate and fresh per-action readback.

`tools/ai_handoff.py --client-receipt` emits `CLIENT_TRANSITION_PLAN` JSON with
admitted `ready` actions (stage `PREPARE` or `EXECUTE`) and `waiting` transitions
with their missing condition IDs. The client consumes the ready actions through
the existing authorized executor. Available preparation prevents terminal
handoff; unresolved transitions prevent DONE. Recompute the plan after each
relevant input, subject or capability change, retaining independent alternatives.
No parallel worker, trigger or credential store is introduced.

Historical v1 receipts without a plan remain readable. Validation checks the
declared bindings and predicates, not their live authenticity or completeness.
The plan neither executes actions nor proves a latency improvement, unattended
runtime, Main integration, other-client adoption or domain delivery. Measure
latency, correction recovery and verified useful progress separately before
claiming such gains.

Owner instruction: Ingolf Lohmann, 2026-10-11. This procedure is mandatory for
all repository clients. Preserve the existing authorized repair, integration
and exact-host delivery goal after handoffs, compaction or status questions.
Do not ask for the same authorization again. Inspect applicable existing
repository, connector, CLI and Mesh routes before declaring execution absent;
retain operation, HTTP method, target/account binding and exact denial evidence.
A locally absent CLI or empty project filter alone is insufficient.

Continue each safe, deterministic, authorized successor, including useful
preparation and persistence while an external effect is blocked. Keep GitHub
and IONOS REST-only routing, secure credentials and protected governance. Never create a
proxy executor or synthetic trigger to manufacture capability. Preserve issue
evidence, perform NOOP for unchanged causal failures, and read back ambiguous
effects before another effectful attempt.

On 2026-10-13 Ingolf Lohmann explicitly selected **“REST-only beibehalten”**
for IONOS. Reuse this decision across reconnects; do not reopen the browser-login
choice. The existing client gate enforces `client_continuation.ionos_route` for
planned and effectful actions, including blocked actions. This route constraint
does not establish an authenticated Hosting API key, a domain operation or a
delivery effect. The existing Cloud-v6 GET-only inventory binding is a separate
product and cannot serve as a Hosting domain/DNS writer. DNS, TLS and application
delivery still require independent evidence for `raumzeitterminal.de`.

Before a terminal handoff, run the existing read-only validator:
`python3 -B tools/ai_handoff.py --client-receipt <receipt.json>`.
Its `qikvrt-client-continuation/1` receipt contains:

- `subject`: exact `repository`, bound `ref`, `head` and `tree`; `authorization`: `granted`
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
- `action_window`: nonempty `id`, timezone-aware `completed_at` and `closed_at`.
  Both closing observations must bind this `action_id` and an `observed_at`
  strictly after completion and no later than closure. Earlier session reads
  and another action's observations cannot close this work unit. Every
  effectful `attempt` requires its own window and repository/delivery readback;
  a fresh final receipt cannot conceal an unchecked earlier action.
- `readback.repository`: current `repository`, `ref`, `head`, `tree`, `source`,
  `action_id`, `observed_at`. All subject fields must match the acting branch's
  newly bound subject. If a new HEAD/TREE is observed, follow it and update the
  subject and applicable checks before attempting closure.
  `readback.delivery`: exact `hostname: raumzeitterminal.de`, `source` and
  `state` (`UNKNOWN`, `PENDING`, `VERIFIED`), `action_id`, `observed_at`, public
  HTTPS `url` and read-only `method: GET`. VERIFIED additionally needs an
  integer `http_status: 200`, exact-origin `final_url` and the observed body
  `response_sha256`. A redirect to another origin is not delivery on this host.
  Missing access stays UNKNOWN; observed absence can stay PENDING. Neither is
  a delivery proof or a negative conclusion about DNS/registry state.
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

The existing policy binds the unchanged Owner rule from PR #507 at
`state/authorization/delegations/OWNER_END_OF_ACTION_VERIFICATION_GRUNDREGEL_V1.json`.
The read-only handoff validator derives its delivery domain from that contract
and verifies the bound bytes. This adds behavioral coverage to the existing
client gate; it creates no second governance implementation or remote writer.
The original 30 regressions remain, with action-time, HEAD/TREE, per-attempt and
HTTP-proof negative controls added. The shared CLI is exercised for connector,
CLI and Mesh route receipts. Registered AI adapter shims reuse AI/AGENTS;
their presence is not an executed Claude/Codex/Copilot session witness. The
HTTP transport client, read-only web terminal, personal terminal and Firefox
remain separately scoped clients whose existing tests do not prove automatic
use of this gate. Actual adoption requires their own emitted receipts and an
independent live readback. No successful fixture substitutes for those witnesses.

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
