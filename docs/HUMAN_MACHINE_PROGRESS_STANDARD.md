# QIK-VRT Human–Machine Progress Standard

Status: normative repository standard  
Version: 2.0

## Purpose

Every externally meaningful repository operation MUST remain visible to the human operator. The client MUST emit a complete progress frame immediately before and immediately after every discrete GitHub action, and whenever an observed workflow, job, or step changes state.

A later summary does not compensate for a missing frame. Prose does not replace execution telemetry.

## Non-recursive telemetry boundary

The GitHub reads and writes used solely to observe or persist a progress frame form one atomic telemetry cycle. They do not recursively require progress frames of their own; otherwise no finite implementation could persist the first frame. All task-advancing GitHub operations outside that atomic telemetry cycle remain subject to the before-and-after frame rule.

## Required frame

```text
Repository: <owner/name>
Branch: <branch-or-ref>
Commit: <sha-or-pending>
Operation: <precise operation>
Frame: <monotonic sequence> — <transition kind>

[██████████░░░░░░░░░░] 50%

✓ completed gate or action
⟳ running gate or action
□ pending gate or action
✗ failed gate or action
! blocked gate or action

BLOCKER: <none or exact blocker>
NEXT: <next executable action>
STATUS = IDLE | RUNNING | WAITING | PASS | BLOCK | FAIL | TIMEOUT | CANCELLED
```

The percentage is relative progress over declared gates or observed steps, not an elapsed-time prediction. A visual percentage never proves correctness.

## Discrete GitHub actions

The frame boundary applies to every client operation that advances or verifies the task, including:

1. branch or ref creation/update;
2. file create/read/update/delete used for the task;
3. commit, pull-request, review, merge, tag, release, or publication operations;
4. workflow/run/job/step observation and log or artifact inspection;
5. status, check, integrity, provenance, proof, and deployment verification; and
6. retry, repair, synchronization, or mirror operations.

Multiple task-advancing GitHub actions MUST NOT be batched behind one progress frame.

## Workflow observation contract

A persistent watcher MUST:

1. use a repository/PR-scoped concurrency group so watchers never overlap;
2. complete one observation cycle before starting another;
3. observe the newest relevant run per workflow and every exposed job and step;
4. persist a fresh full frame whenever the workflow/job/step state signature changes;
5. suppress unchanged duplicate frames;
6. wait five seconds only after the prior frame has been persisted and only while work remains active; and
7. finish with a terminal frame containing decisive run, job, check, and evidence identifiers.

The human projection MUST be available in the repository-native client surface, at minimum a persistent pull-request comment and the GitHub Actions step summary. Machine state MUST conform to `schemas/human_machine_progress.schema.json`.

That schema preserves `qikvrt_human_machine_progress_v1` for live workflow
frames and defines `qikvrt-ai-progress/3.1` for durable root handoff snapshots.
A durable snapshot may carry several explicitly bounded scopes; a nested
scope-specific `PASS` never promotes an incomplete sibling scope or the
top-level repository effect state.

Version 3.1 makes projection-input evidence portable between canonical
repositories with different commit histories. The committed capsule is an
exact selected-path Git-object closure, not a worktree copy or a network
fallback. Its commit, tree, path, mode, blob, size, SHA-256 and capsule-file
bindings are verified offline; available local Git objects are a mandatory
second check. This proves only the declared historical projection inputs.

## Tracked status artifacts

`AI_PROGRESS.json` and `AI_STATUS.md` are durable handoff snapshots. When no repository operation owns them, they MUST be `IDLE` or terminal. A tracked root snapshot MUST NOT remain falsely `RUNNING`, `WAITING`, or `PENDING` after its owner has ended.

Live workflow frames may be persisted by `QIKVRT live status watch`, but a
branch-level watcher is telemetry only. Exact PR, check, merge, promotion, or
synchronization claims require evidence bound to the current commit and run.
The tracked root snapshots identify the last stable handoff state without
promoting watcher output into exact-head proof.

## Repository runtime authority

The repository is the durable runtime authority. Chat sessions and individual artificial-cognitive clients are disposable transport surfaces. The repository MUST accumulate and version:

- exact tool and dependency locks;
- checksums, provenance, and licenses;
- bootstrap and recovery logic;
- positive, negative, integrity, and security tests;
- runtime-cache contracts and receipts;
- progress and failure diagnostics; and
- verified improvements to ordering, reuse, throughput, and recovery.

Existing components MUST be reused, extended, parameterized, generalized, or refactored before parallel machinery is created.

## Cache semantics

Verified tool archives, wheelhouses, package stores, and build products MAY be reused through exact-key caches. Cache hits accelerate execution but never replace current-tree proof, integrity, provenance, security, review, or release gates. Credentials and mutable authentication state MUST never enter a cache.

A cold cache and a warm cache MUST preserve the same correctness semantics. Missing cache content may reduce throughput; it must not remove reproducible capability while the locked upstream material remains available.

## Terminal semantics

`PASS` is scope-bound and requires referenced evidence. Terminal `PASS` is forbidden while any required gate remains pending, running, failed, blocked, or unverified. A concrete repairable failure remains an active persistence run; the client continues repair rather than returning explanatory prose as a substitute for execution.

## Continuous human-readable feedback

Product Owner Ingolf Lohmann establishes
`HUMAN_READABLE_FEEDBACK_CONTINUOUS_IMPROVEMENT` as a continuous optimization
objective for errors and all visible feedback. The machine contract is
[HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json](../policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json);
the work unit is [HUMAN_READABLE_FEEDBACK_OPTIMIZATION_20261006_V1.json](../state/work_units/HUMAN_READABLE_FEEDBACK_OPTIMIZATION_20261006_V1.json).
It applies to the Universales Raumzeit-Terminal, React/HTML monitors, Firefox,
CLI and human-facing API projections on all current and future nodes/clients.
Historical snapshots remain immutable; node adoption needs its own readback.

Every message MUST first explain in plain, localizable language what happened
and its impact. State the established cause, or explicitly mark it unknown.
Name the smallest available next action and its responsible actor. For repair
or continuation, distinguish planned, started, completed and blocked using
actual execution evidence. A queued repair is not started; a green observer
is not native approval; an unchanged blocker is not new progress.

Keep technical error codes, machine states, exact repository/HEAD/TREE/run and
receipt bindings available in accessible, copyable details. Visual surfaces
use progressive disclosure with keyboard and screenreader semantics; text
surfaces retain a concise explanation followed by diagnostic details. Redact
secrets and private content. Deduplicate unchanged feedback without hiding
failures. Localization must preserve the technical meaning and uncertainty.

Example: “Die Veröffentlichung wartet auf die GitHub-Freigabe. Das Paket ist
geprüft; veröffentlicht wurde es noch nicht.” This wording is valid only when
those three scoped facts are observed. If repair is active, name its evidenced
step. If it is blocked, state what is missing and what can proceed.

Use OBSERVE → MEASURE → DIAGNOSE → ADAPT → VALIDATE → COMPARE → LEARN with
existing emitters and review paths. Evaluate equivalent real before/after
error and status cases: can the human identify state, impact and next action?
Record language, sample, review method, comprehension/clarification measures,
repair-state accuracy and retained diagnostics in the existing interface
evaluation matrix. Automated wording checks do not establish comprehension.
No quality, accessibility, privacy, evidence or mandatory-gate regression is
allowed. Policy persistence alone does not prove implementation, rollout or
measured improvement. Machine states and `PREDECESSOR_EVIDENCE_TRANSFER=false`
remain unchanged.
