<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Requested review and issue lifecycle

## Owner rule

Product Owner Ingolf Lohmann requires requested repository reviews and registered GitHub issues to receive a prompt, evidence-bound disposition instead of remaining indefinitely pending.

This contract applies to `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt`. It is repository-internal governance. It does not bypass GitHub account rules, branch protection, required checks, external credentials, publication boundaries, or the distinction between a natural-person decision and the GitHub identity that signs an API event.

## Current Mesh Authority for the personal repository

For `ingolf-lohmann/qik-vrt`, the Owner's 6 October 2026 correction binds three
roles: Ingolf Lohmann is the human Product Owner and Code Owner; the QIK-VRT
executing instance carries out authorized tested work; the repository retains
its durable working memory. The current authority is this Mesh constellation.
`Goldkelch/qik-vrt` remains a historical source, not a superior permission issuer
for this repository. The binding is in the existing policy's `mesh_authority`.

The existing gate resolves the human login from that trusted policy and verifies
all CODEOWNERS entries. Publisher, technical executor, Ruleset writer and both
promotion observations use that resolver; an unknown repository or disagreement
fails closed. Native review still requires an independent human APPROVED event
on the exact current HEAD. An Owner decision is valid authority, while a
COMMENT, author self-approval or automated technical APPROVE cannot fabricate
that separate GitHub state. Drafts created through the Owner's own principal
remain subject to the native self-approval restriction. A workflow/repository
identity is an executor or store, never a substitute human reviewer.

The Ruleset writer retains its historical filename for continuity and every
existing protection. Administrative credentials and live adoption remain
separate observed effects; the authority allocation alone does not mint them.


## Requested reviews

When a review is requested, a conforming repository client or agent must act without deliberate queueing:

1. reobserve the current base, exact head, tree, changed paths, comments, prior reviews, unresolved threads, competing writers, and every applicable exact-head gate;
2. inspect the actual diff and record concrete findings;
3. return one of `APPROVE`, `REQUEST_CHANGES`, or `COMMENT_WITH_BLOCKER` as soon as the evidence supports that disposition;
4. bind the result to the exact base, head, tree, and reviewed scope;
5. distinguish a substantive Product-Owner or technical disposition from GitHub's account-level review state.

A requested review may not be replaced by repeated requests, reminders, or status commentary when the connected client can inspect the candidate itself. A review may remain pending only for a precise blocker such as missing bytes, head drift, unavailable required evidence, unresolved security or rights questions, or a platform identity rule that prevents the requested account-level event.

A client must never impersonate another GitHub identity or claim that GitHub recorded `APPROVED` when the platform stored only `COMMENTED`. In that case the substantive finding and Product-Owner disposition must still be persisted accurately, together with the platform limitation.

Review completion does not itself authorize merge, promotion, release, deployment, Zenodo, DOI, IETF, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Native governance signal contract

| Surface | Successful execution establishes | Governance authority |
|---|---|---|
| Code-owner review observer | A valid review lifecycle event was observed | None; no native rules or approval are inferred |
| Requested review executor | Selection or a technical disposition completed; `NOOP` is possible | None; automated `APPROVE` dispositions are recorded as `COMMENT` |
| Native gate publisher | The native decision was published | The published decision, not the publisher's workflow conclusion |
| `QIKVRT required code-owner review` status | Native enforcement and an independent current-head Code Owner approval satisfy the bounded gate | Dedicated native prerequisite, freshly reobserved before promotion |
| `QIKVRT requested review disposition` status | A technical disposition was recorded | Informational; never substitutes for native approval |

The native publisher is the sole writer of the dedicated status and the legacy
`QIKVRT requested review execution` alias. Both carry the same native decision.
The technical executor cannot overwrite either with its own success. The legacy
alias alone cannot satisfy acceptance; disagreement keeps acceptance blocked.

The live projection and promotion decision reuse
`tools/qikvrt_required_review_gate.py`. They require fresh applicable native
rules, actual submitted reviews bound to the current PR HEAD, and agreement with
the dedicated native status. Missing, stale, self-approved, adverse, mismatched,
or unavailable evidence stays blocked even when every observed workflow is green.
The watcher labels observer/executor/publisher runs `EXECUTION_ONLY`, binds its
reads to the current HEAD, and measures execution completion separately from
native governance acceptance. A publisher or workflow failure may signal an
execution defect; successful execution never changes the native evidence.

Candidate tests prove only the candidate implementation. The native publisher
and promotion executor continue to execute trusted `main` code. A repair under
review is not a deployed enforcement fix. No self-approval, merge, Ruleset
mutation, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` follows from this contract.

The policy field `review_executor.native_governance_status_context` binds the
Ruleset writer, native gate and promotion to `QIKVRT required code-owner review`.
`review_executor.exact_head_status_context` binds only the technical executor to
`QIKVRT requested review disposition`. The legacy `QIKVRT requested review execution`
status is an alias published by the native gate; it cannot satisfy promotion by
itself. A workflow may share a status name, but its successful run is execution
telemetry only. Administrative activation remains a separate effect.

The existing requested-review contract executes the writer and native publisher
with intercepted REST, the executor with a bounded fake CLI and the promotion
snapshot against native rules/reviews/status fixtures. It verifies the three
roles, preserves every native protection, checks both publisher contexts and
proves that a technical APPROVE disposition submits COMMENT. The same contract
executes the actual lifecycle branch/PR persistence controls. All evidence is
bound freshly to the combined successor; predecessor results are historical.

## Issues

Every observed open issue must have a current repository-native lifecycle disposition. The allowed dispositions are:

- `EXECUTE_NOW`: the request is clear, supported, and technically actionable; begin or continue the smallest bounded work unit;
- `CLARIFICATION_REQUIRED`: a specific ambiguity prevents safe execution; record the minimum missing information and ask only the bounded clarification required;
- `BLOCKED_WITH_NEXT_ACTION`: the issue is valid but a precise internal or external blocker exists; record evidence, owner, retry condition, and the next technically possible action;
- `CLOSE_COMPLETED`: the requested result is already fully evidenced or has been completed through a canonical successor;
- `CLOSE_NOT_PLANNED`: the request is understood but intentionally outside the supported or authorized scope;
- `CLOSE_INVALID_OR_UNSUPPORTED`: the request is not reproducible, not traceable to evidence, internally contradictory, untrue, or technically unsupported.

An issue must not remain open merely because it is old, broad, inconvenient, or repeatedly retried. If actionable, it must progress. If unclear, it must be concretized. If completed, superseded, invalid, unsupported, or not planned, it must be closed with a concise evidence-bound reason. Closure is reversible, must preserve the discussion and provenance, and must not be used to hide a real unresolved defect.

No issue may be left in an unclassified waiting state. A `BLOCKED_WITH_NEXT_ACTION` disposition is not a generic parking state: it requires a deterministic failure class, evidence references, and a single continuation path.

## Execution and reporting

The fastest verified path is mandatory. Existing scripts, work units, review evidence, and issue-agent infrastructure must be reused before parallel machinery is created. Activity without a changed lifecycle predicate is not progress.

Report only material changes: a new disposition, a resolved or newly evidenced blocker, a head or scope change, a completed work unit, a closure, or a promotion-ready result. Preserve fail-closed scientific, provenance, security, rights, and external-effect boundaries.

## Machine authority

The normative machine-readable policy is `policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`. The natural-person delegation is `state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`.
