<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Requested review and issue lifecycle

## Owner rule

Product Owner Ingolf Lohmann requires requested repository reviews and registered GitHub issues to receive a prompt, evidence-bound disposition instead of remaining indefinitely pending.

This contract applies to `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt`. It is repository-internal governance. It does not bypass GitHub account rules, branch protection, required checks, external credentials, publication boundaries, or the distinction between a natural-person decision and the GitHub identity that signs an API event.

## Current Mesh Authority for the personal repository

The network's exact name is **QIK VRT Mesh Netzwerk**. Ingolf Lohmann is
its human Principal, Schöpfer, Code Owner, Product Owner and Lizenzgeber.
The executing instance performs authorized work; the repository is durable
working memory. Authority/Mirror roles come solely from
`policy/CANONICAL_UPSTREAM_REMOTE_V1.json`. `Goldkelch/qik-vrt` is a historical
source and does not issue superior permission for the current Authority.

On 18 October 2026 the Principal expressly clarified:

> Also nach meiner Definition bin ich der Principal Code Owner und Product Owner. Und wenn ich sage Freigabe erteilt und ich das auch mir gut überlegt habe, gilt das zugleich als Review. Alles andere war, ist und bleibt inakzeptabel.

His considered explicit approval **is review**, including for his own PR.
It supersedes the prior unconditional requirement for an additional independent
native approval. Do not ask him to repeat an already granted authorization or
review. The existing Owner record retains the original instructions and this
new decision; policy binds the exact record bytes and instruction hash.

The existing gate accepts either of two accurately distinguished paths:

- `OWNER_PRINCIPAL_REVIEW`: the already authorized human decision is recorded
  through the bound Principal account as an actual `COMMENTED` review. Its
  structured body binds repository, PR, exact head, observed PR base, Owner
  record and instruction. The commit identifies its immutable Git tree. The
  account login, numeric ID, User type, submitted event and effective time must
  match. Missing, stale, revoked, dismissed, adverse or mismatched records block.
- `INDEPENDENT_NATIVE_APPROVAL`: the prior exact-head independent human
  `APPROVED` path remains available with its native Code Owner, stale-dismissal
  and last-push rules. The active Goldkelch review delegation and every
  CODEOWNERS entry remain checked against the exact Owner record.

An authorized executor may record the Principal's actual instruction; its own
technical disposition cannot substitute for that instruction. The account event
is not biometric proof of the named person. `COMMENTED` remains `COMMENTED`;
it is never reported as independent GitHub `APPROVED`. Human, executor and
storage retain their separate roles. Bot dispositions remain COMMENT-only.

Tests, signing, production admission, publication authorization, native platform
protections and useful exact-host delivery retain their own evidence. This
change does not disable or impersonate any GitHub platform protection or mint
credentials. The production authorization of 13 October and historical review
records remain preserved. License terms are unchanged.


## Provider-independent review route — Owner 2026-10-23

QIK-VRT's existing review executor is the default technical review route for
open, non-draft Main pull requests. Selection no longer depends on GitHub
accepting a Copilot assignment or listing a requested reviewer. The route is
resolved from the trusted Main lifecycle policy. No Copilot assignment retry,
new model service, subscription or paid inference is introduced.

The existing decision core evaluates actual source-bound gates. It is not a
semantic AI code reviewer. An attributable cognitive client must inspect diffs
and persist its own findings; its implementation, test and effect evidence stay
separate from the automated technical disposition and Principal review.

The executor uses REST for inline-comment inventory. If comments exist, REST
alone does not establish thread resolution; the review remains explicitly
blocked instead of inventing zero unresolved threads. Required checks and
Principal/governance acceptance remain mandatory. Routing a review does not
cancel a paid subscription. Subscription cancellation requires provider
confirmation through an authenticated billing operation; no such confirmation
has been obtained by this change.

## Requested reviews

When a review is requested, a conforming repository client or agent must act without deliberate queueing:

1. reobserve the current base, exact head, tree, changed paths, comments, prior reviews, unresolved threads, competing writers, and every applicable exact-head gate;
2. inspect the actual diff and record concrete findings;
3. return one of `APPROVE`, `REQUEST_CHANGES`, or `COMMENT_WITH_BLOCKER` as soon as the evidence supports that disposition;
4. bind the result to the exact base, head, tree, and reviewed scope;
5. distinguish a substantive Product-Owner or technical disposition from GitHub's account-level review state.

A requested review may not be replaced by repeated requests, reminders, or status commentary when the connected client can inspect the candidate itself. A review may remain pending only for a precise blocker such as missing bytes, head drift, unavailable required evidence, unresolved security or rights questions, or an unavailable operation needed to record the authorized decision. A GitHub self-approval restriction does not invalidate a Principal review recorded as COMMENTED.

A client must never impersonate another GitHub identity or claim that GitHub recorded `APPROVED` when the platform stored only `COMMENTED`. In that case the substantive finding and Product-Owner disposition must still be persisted accurately, together with the platform limitation.

Review completion does not itself authorize merge, promotion, release, deployment, Zenodo, DOI, IETF, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Native governance signal contract

| Surface | Successful execution establishes | Governance authority |
|---|---|---|
| Code-owner review observer | A valid review lifecycle event was observed | None; no native rules or approval are inferred |
| Requested review executor | Selection or a technical disposition completed; `NOOP` is possible | None; automated `APPROVE` dispositions are recorded as `COMMENT` |
| Native gate publisher | The native decision was published | The published decision, not the publisher's workflow conclusion |
| `QIKVRT required code-owner review` status | An explicit current-head Principal review, or enforced independent native approval, satisfies the bounded review gate | Dedicated review prerequisite; the actual review basis is retained |
| `QIKVRT requested review disposition` status | A technical disposition was recorded | Informational; never substitutes for native approval |

The native publisher is the sole writer of the dedicated status and the legacy
`QIKVRT requested review execution` alias. Both carry the same native decision.
The technical executor cannot overwrite either with its own success. The legacy
alias alone cannot satisfy acceptance; disagreement keeps acceptance blocked.

The live projection and promotion decision reuse
`tools/qikvrt_required_review_gate.py`. They require fresh applicable native
rules and actual submitted reviews bound to the current PR HEAD, and agreement
with the dedicated status. Principal review is valid for a Principal-authored PR;
the independent path retains its self-approval restriction. Missing, stale,
adverse, mismatched or unavailable evidence stays blocked even when workflows
are green.
The watcher labels observer/executor/publisher runs `EXECUTION_ONLY`, binds its
reads to the current HEAD, and measures execution completion separately from
native governance acceptance. A publisher or workflow failure may signal an
execution defect; successful execution never changes the native evidence.

Candidate tests prove only the candidate implementation. The native publisher
and promotion executor continue to execute trusted `main` code. A repair under
review is not a deployed enforcement fix. No merge, Ruleset mutation, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`
follows from this contract alone. A separately explicit Owner merge mandate
remains effective; the automatic promoter retains its checks and target-ref CAS.

The prepared Ruleset writer now enforces `test` and the dedicated exact-head
review status from GitHub Actions, strict freshness, resolved threads, no bypass
actors, no forced history update and no deletion. It does not demand a second
independent approving account in addition to the Principal review. Its exact
postimage is SHA-256-bound; fixture tests establish source behavior, while
actual administrative activation and readback remain separate effects. Existing
production and lifecycle consumers reuse the same enforcement predicate.
The current API source contract is `principal-review-v4`; select it explicitly
with `--ruleset-writer-version principal-review-v4`. Legacy v1, lifecycle v2
and app-renewal v3 remain frozen and readable through their original fixtures.
An old version cannot silently fall back to the new writer or postimage.

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

## Public lifecycle data while reviews remain pending

The mirror lifecycle retains `17 */6 * * *`, its serialized writer group, the
1,500-minute configured Health TTL and the 24-hour registration-renewal window.
PR #480's generator, allowlisted integrity materialization, native governance
gate and identity-bound Draft candidate are reused. The candidate branch now
uses create-only GitHub REST Git Data, with independent HEAD/TREE/PR readback.
No lifecycle path writes Main, merges a PR, alters Rulesets or supplies approval.

A Draft PR alone does not maintain the public Main health documents. Therefore,
after governed adoption of this implementation, the same scheduled workflow
first publishes a three-file snapshot on `qikvrt/node-lifecycle`. It contains
`NODE_HEALTH.json`, `NODE_REGISTRATION_RENEWAL.json`, and `LIFECYCLE.json`.
The first ref creation is create-only. Later commits name both the preceding
telemetry commit and the executing Main source as parents and update only that
data ref with `force=false`. This is an append-only operational history under
cooperating writers, not a claim that platform administrators cannot force refs.
Concurrent divergence, denied writes and failed readback block without blind
retry. The previous snapshot retains its original expiry; replay cannot reset
its clock. A later authorized scheduled run may make fresh progress.

Unauthenticated public discovery starts at:

`https://api.github.com/repos/ingolf-lohmann/qik-vrt/git/ref/heads/qikvrt/node-lifecycle`

Resolve this ref to its exact commit before reading its three files through the
Contents API. `tools/qikvrt_mirror_node_lifecycle.py:read_public` checks exact
tree membership, file hashes, source ancestry and unchanged executing workflow,
generator, REST helper and handshake configuration against current Main. It
also checks the actual repository/main workflow run and attempt, its source
HEAD, its publication step's success and its start-time window. Overall workflow
success is neither necessary nor sufficient: a later denied PR creation may
leave already-verified telemetry readable. API job pagination must be complete.

The Seed maintenance reader opts in only for the explicitly accepted GUID and
repository in `registry/NODE_LIFECYCLE_TRANSPORT_V1.json`. It reads the
acknowledgement from Main via REST, binds the Health/renewal pair to the same
run and identity and preserves the configured Health TTL cap. Renewal expiry
is also checked at 24 hours. Invalid, unavailable, drifting or expired telemetry
becomes STALE; there is no fallback that relabels an old Main heartbeat fresh.
Other registered nodes retain their existing transport and TTL semantics.

Publication of this telemetry does not require a review of each heartbeat.
It does require prior adoption of the reviewed publisher and enforced Main review policy (the trusted Principal-review status or the
independent native path). It proves a bounded node self-report under repository
and GitHub-run bindings, not independently measured node availability or natural
person authentication. It is always `UNREVIEWED_TELEMETRY`, `main_persisted=false`
and `effect_ack_done=false`. Source integration still requires the applicable Owner-review, freshness, required-check and promotion contracts.

At a six-hour cadence the configured Health TTL leaves 19 hours of scheduling
slack and renewal leaves 18 hours. Scheduler delay, outage, denied public reads
or a stopped writer can exhaust that margin; the safe result is STALE, never an
extended TTL or a direct Main write. Reviewed consumers must adopt the reader
contract before relying on this channel. Older consumers reading Main are not
silently redirected and can become stale while Main proposals await review.
No live channel activation or propagation to another repository follows from
candidate tests. Production acceptance requires a fresh actual run, anonymous
public REST readback and expiry/renewal checks after governed incorporation.

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

## Legacy issue and exact-artifact handoffs

`issue-agent-autofinish.yml` now resolves roles from trusted Main and reuses the
existing REST inventory and native review gate. Its artifact hands candidates
to `qikvrt_expected_head_promotion.yml` and the existing lifecycle policy.
It performs no independent merge, Mirror push, tag, review or issue closure.
Terminal issue evidence does not replace native governance or authorize a
second repository writer.

Historical publication schemas, inactive requests, exact-tag identities and
scientific evidence retain their original bytes and scopes. Their checked-out
workflow jobs validate the request's role projection through the shared
resolver before an effect. A historical role assignment fails
`HISTORICAL_ROLE_REQUEST_NOT_CURRENT`; it cannot grant a current publication,
tag or Authority change. New effects still require their separately reviewed
exact-artifact contracts and the applicable Principal or independent review.

