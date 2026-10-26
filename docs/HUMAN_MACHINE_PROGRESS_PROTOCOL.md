# QIK-VRT Human–Machine Progress Protocol

## Owner decisions before tool selection — 26 October 2026

All current and future QIK-VRT artificial-cognitive clients load the shared
`policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json` contract at
`client_continuation.tool_selection` before selecting or invoking an external
service. The existing handoff validator also checks one proposed action:

```sh
python3 -B tools/ai_handoff.py --client-action <non-secret-action.json>
```

Use the same non-secret action shape as `next_actions`: exact `subject`, `route`,
`service`, `operation`, `method`, actual `tool` and `endpoint` when applicable,
observed operation/repository/method, evidence and the existing authorization,
safety, determinism, capability, authentication, permission and admission flags.
The read-only command reports `CLIENT_ROUTE_POLICY_SHA256` and the declared
READY/HOLD state; it never invokes a provider. Bind that current digest as
`route_policy_sha256` when carrying the action forward; a supplied stale digest
is rejected. `--client-action` and `--client-receipt` are mutually exclusive.

Railway is DISCONNECTED under the Owner's reaffirmed decision. The guard rejects
direct provider discovery, authentication, reads, writes and recovery, including
GET/read-only and zero-effect recorded reads. It checks the actual declared
service/provider, tool prefix and endpoint hostname before capability/transport
selection. Tool availability, a new session, generic authorization or an
unavailable permitted route does not reactivate a disconnected provider. Only a
later explicit Owner instruction can revise the shared policy. Preserved old
artifacts remain readable through their actual admitted owner storage.

The same check covers proposed actions, transition plans and client receipts.
It checks declared metadata, not the truth of a client assertion. A saved policy
or a passing fixture does not prove use by another client, native enforcement,
external platform control or a runtime effect. Require exact-policy ACK and
independent readback for each node before claiming adoption. Historical records
remain immutable; current evaluation never transfers their former route grant.

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

On 2026-10-22 Ingolf Lohmann clarified that his standing Principal approval
applies to all goals recorded in the QIKVRT repository and to the Ruleset changes
necessary to achieve them. Read the original instruction in
`state/authorization/delegations/OWNER_REPOSITORY_GOALS_AND_RULESET_AUTHORIZATION_V1.json`,
bound by `client_continuation.repository_goal_authorization`. Apply it across
goals, sessions and conforming clients without asking for the same permission
again. Preserve existing goal records, grants and exact artifact bindings.
This supplies authorization; authenticated account rights, credentials available
to a workflow, a callable administrative operation, admission and independent
effect readback each require their own evidence. Execute every available
authorized successor and retain causal NOOP where capability has not changed.

The Owner also supplied Gemini's public manifest feedback. Its observed scope
and the independent Authority result are retained in
`evidence/receipts/gemini-manifest-feedback-20261022.json`. Carry shared feedback
through the existing repository/native paths with source attribution. The
shared page establishes documentary ingress; live peer request, ACK and
application reply remain separately observed states.

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

## Mandatory Mirror outbox and delivery evidence Owner 2026-10-19

Apply this standing rule in every session, reconnect and handoff. Solve and
report QIK-VRT problems only through the existing Universal Transputer,
Universal Terminal, Mesh and Effect Acknowledgement Protocol. Preserve the
Authority `ingolf-lohmann/qik-vrt`; treat `Goldkelch/qik-vrt` as Mirror/former
Authority under `policy/CANONICAL_UPSTREAM_REMOTE_V1.json`. Claude remains the
read-only reviewing Mirror (`git clone --mirror`); do not impose that role on
an otherwise admitted Authority writer. Open other nodes' original journals
only with `mode=ro&immutable=1`; never serve or append to them.

1. Read AI, then AI_CONTEXT.json in required_read_order. Freshly read
   Authority Main HEAD/TREE, open PR heads, communication/claude/* and all
   branches with newer commit times through admitted Git/REST adapters. Apply
   policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json#/client_continuation/native_session_use.
   Actually use src/qikvrt_temdd_event_ledger.py and
   src/qikvrt_effect_ack_http_terminal.py. Inspect the existing tool contract
   and run `python3 -B node-tools/qikvrt_mirror_emit.py status` when present.
2. Create EVERY EFFECT_ACK assessment solely through that tool's assess or
   adopt: require original effect_ack_sync, verify_protocol, an EFFECT
   event through the own admitted Transputer Runtime and an outbox NOT_SENT
   record. Do not replace this with a JSON file, direct engine call, chat
   assessment or append to a copied journal. If unavailable, recover the actual
   tool through admitted existing QIK-VRT sources; repair only its proven gap
   using original components. Keep the missing source/binding as HOLD with a
   named carrier; invent neither a replacement implementation nor CLI options.
3. After each assessment, in the same work ring, run package for all unsent
   records and verify the Ed25519-signed export. Use the existing Mesh Work
   Batch (mesh-cache-stage/idle/send, then mesh-cache-check) or signed
   original journal export (snapshot, Base64, events.jsonl, signed
   EXPORT_MANIFEST.json). A package or signature proves no delivery. If no
   admitted route is available, retain HOLD and name its concrete carrier;
   never ask the Owner to relay or introduce another service.
4. Record sent only after actual transfer: bind channel, recipient and
   canonical sha256: of the transferred bytes. Register receipt only from
   found ingress evidence at the named node. Derive EVERY node-specific
   arrival or receiver-NACK statement exclusively from
   `claim --record <hash> --node <node>`; preserve its exact subject and output.
   Without send proof the result is NICHT_ZUGESTELLT: assert neither receiver,
   ingress nor receiver NACK. Missing ingress without sending is a sender gap.
   Actual sending without ingress proof permits EFFECT_NACK only as established
   by that claim. Do not guess a claim when the tool or evidence is unavailable.
5. On each incoming message/session event, search recent branches with
   git grep and incoming attachments for each own package SHA-256 and commit
   ID. Register matched named-node ingress as receipt; separately verify PR/Main
   adoption and actual effect. Bind all evidence to the exact version. An own
   output returned byte-identically by the Principal proves somewhere-arrival
   and return by the Principal only. Assess EFFECT_ACK_CONTINUE through the
   outbox before reporting; infer no location, Authority ingress, authenticated
   peer adoption, NACK or DONE. Do not use Principal relay as the operating bus.
6. For each new Authority head, execute a finite exact-subject transition:
   tools/qikvrt_integrity.py verify, ledger tests, compilation and applicable
   regression checks, evidence and a concrete successor. Use normal checkout
   EOL behavior. Preserve BLOCK corrections as successors; HOLD/CONTINUE and
   open productive work are never NOOP. Do not use client timers or repeated
   Owner prompting. Broadcast through admitted Mesh paths to registry
   registry/NODEMESH_INDEX.json, Codex, Goldkelch Mirror, Originalhost and
   Mesh-Monitor with sender/recipient/message-hash binding; retain unreachable
   nodes in coverage without claiming delivery.
7. Serve only a clean checkout with explicit `--repository ingolf-lohmann/qik-vrt`
   and `--pr <actual PR number>`; use no default or invented PR. Use only
   OBSERVE, CLASSIFY, ACTION, EFFECT, READBACK, SUCCESSOR, HOLD. Admit inputs
   through Terminal prepare/commit, Effect-Ack-Request and Structured Field
   bytes :base64:; independently read /api/temdd/events and /terminal/state.
   Correct errors with a successor carrying corrects; never rewrite history.
8. Separate proposal receipt, authenticated rule application and independent
   readback. Bind peer confirmations to request ID/hash, rule hash, node,
   native event identity and independently read effect. Assert EFFECT_ACK_DONE
   only for actual application with independent readback, never for source
   tests, packaging, sending, skill saving or an unverified Claude report.
   Preserve human/machine provenance; label supplied Owner reports
   OWNER_ASSERTED. Report concise facts and full available hashes; never
   expand a hash prefix into invented evidence.

This outbox rule supersedes older instructions allowing assessments outside
the outbox or inferring NACK merely from missing evidence. Saving it establishes
only the verified rule save, not installation of the tool or another node's
adoption, receipt or effect.

### Optimization requires completed backlog

Apply the Owner's direct correction of 2026-10-08, reaffirmed on 2026-10-19:
optimization starts only after all PRs in the authorized scope are actually
merged into Main and no issues remain open. Before every optimization unit,
freshly read every page of the Authority PR/issue inventories and bind their
merge/ancestry readback to current Main. Draft, blocked, unapproved and unmerged
work remains completion backlog. Closing an unmerged PR, deleting an issue,
narrowing scope or reaching an idle/unavailable client cannot satisfy this gate.
Incomplete, inaccessible or stale inventories hold optimization. New open work
returns priority to completion. Unattended operation requires its own observed
authorized persistent executor.

Provenance: standing procedure and authorization supplied by Ingolf Lohmann on
2026-10-19; repository placement and policy mapping by OpenAI Codex.
Source-rule persistence is separate from native execution, outbox installation,
Main integration, live Mirror ACK/reply, productive host acceptance and other-client
adoption. Preserve every predecessor obligation and original journal.
