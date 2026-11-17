<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Expected-HEAD ref publication and bounded continuation

Owner decision applied on 2026-10-10: one authoritative target-ref commit point;
an atomic comparison against the expected old HEAD; fresh published HEAD/TREE
readback before CONTINUE. This extends the existing promotion decision core
and executor, not a second writer, release mechanism or policy authority.

## Current adapter boundary

GitHub's normal merge REST `sha` predicate compares the pull request head. It
does not compare the previous Main ref. The Git reference PATCH API documents
`sha` and `force`, but no expected-old-SHA predicate. A client GET followed by
PATCH, a successful transport acknowledgement, or a workflow concurrency group
does not establish server-side CAS for every competing writer.

Sources checked 2026-10-10:

- https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request
- https://docs.github.com/en/rest/git/refs#update-a-reference
- https://github.blog/engineering/architecture-optimization/building-git-infrastructure-for-agent-scale-development/

The trusted default-branch workflow therefore declares target-ref CAS
`UNAVAILABLE`. Even terminal green gates cannot turn that adapter into
`PROMOTABLE`. The decision is `HOLD / ATOMIC_TARGET_REF_CAS_UNVERIFIED`, before
either ready-state change or merge. This intentionally stops automatic
promotion by this executor until a reviewed server-side operation is actually
available and verified. The 2026-10-12 integration removes the REST merge fallback. The automatic
Main phase remains explicitly disabled, even with a populated qualification.

Candidate files, PR comments, cached evidence and an agent's assertion cannot
enable the capability. The GraphQL adapter must bind its independently qualified operation and
evidence digest to the exact repository, target ref, expected old Main and
reviewed candidate head; it must retain review, ruleset and permission gates.
The pure decision core validates a trusted producer's binding; it cannot
independently certify that producer or the underlying server. A populated
digest is not a proof by itself. Tests using a simulated VERIFIED adapter are
model-relative unit tests, not live GitHub assurance.

## Publication closure

After an admitted effect, the existing core performs GET-only reads in order:

1. Exact `refs/heads/main` object.
2. Immutable commit M named by the recorded updateRefs intent (or historical
   REST merge response): its SHA, TREE and ordered
   parents must match the declared result, verified candidate tree, old Main
   and reviewed head.
3. Exact `refs/heads/main` object again, still pointing at that returned commit.

Any unavailable, malformed or mismatched observation yields HOLD. Preserve
the recorded merge SHA and reconcile the effect before another write; a
failed readback never authorizes a blind retry. A matching later HEAD with a
different tree, or merely a HEAD different from the old Main, is insufficient.
CONTINUE is limited to this ref-publication closure. It establishes neither
independent Code Owner approval nor deployment, provider-wide serialisation,
Authority/Mirror equality, PASS, FINAL_PASS or EFFECT_ACK_DONE.

The wrapper retains the candidate, pre-effect snapshot, decision, transport
response and readback as one workflow artifact bound to run ID and attempt.
These artifacts remain subject to GitHub retention. They do not provide a
permanent external archive.

## Acceptance and scope

Run the existing decision and contract tests. Inject missing/non-atomic CAS,
wrong repository/ref/base/head, an unrelated Main update, wrong TREE/parents,
and lost readback. No such input may authorize promotion or CONTINUE. Inspect
the source of a future capability receipt independently before enabling it.

This patch is prepared in ingolf-lohmann/qik-vrt, the Owner-designated
Authority since 2026-10-07. Goldkelch/qik-vrt is the separately observed Mirror
and remained inaccessible through the connected REST route at preparation.
Native role-policy activation on Main remains unverified; the role-repair
carrier is https://github.com/ingolf-lohmann/qik-vrt/pull/491 . Neither the
Owner's reassignment nor this draft establishes native activation, and no
predecessor Goldkelch Authority evidence is transferred.
Other repository writers are outside this bounded change; consolidating their
actual write operations requires separate exact-source verification. Native
workflow admission, independent review, integrity materialization and Main
integration remain separate acceptance evidence.


## GraphQL CAS integration — 2026-10-12

The existing core now provides `qualify-cas`, `prepare-graphql`,
`publish-graphql` and `reconcile-graphql`; no second promotion writer or
workflow is introduced. The API call is exactly one `updateRefs` mutation:

```graphql
mutation QikvrtPromote($input: UpdateRefsInput!) {
  updateRefs(input: $input) { clientMutationId }
}
```

Its structured input contains one reference update: `name=refs/heads/main`,
`beforeOid=B`, `afterOid=M`, `force=false`. The opaque `repositoryId` is checked
against an authenticated REST repository observation and the qualification.
B is the reviewed old Main, H the reviewed PR head, and T the independently
reviewed expected result TREE. M must be GitHub's currently recorded test merge
for the same PR, obtained through both the PR metadata and `refs/pull/N/merge`.
Its immutable object must have exactly ordered parents `[B,H]` and TREE T.
The adapter does not manufacture a merge object, calculate a new TREE, or
silently accept a new test merge. A different result requires fresh review.

Fresh admission reuses `tools/qikvrt_required_review_gate.py` and observes
applied Main rules, their full native rulesets without bypass actors, exact-H
independent Code Owner approval, stale-review dismissal, last-push approval,
non-fast-forward prohibition, and all native Required Checks on H AND M.
`test` and `QIKVRT required code-owner review` are mandatory minimum checks.
App-bound checks must match the configured App id. Missing, adverse, wrongly
bound or incomplete check inventories hold. Policy drift invalidates the
qualification. The GraphQL viewer must equal the independently qualified
executor identity; the Code Owner reviewer must differ from that executor.
Admission is reobserved after viewer identification and immediately before CAS.
Native protection, not preceding GETs, must reject a review/check withdrawal
between admission and mutation. This behaviour needs actual live qualification.

The only qualification source in the workflow is the fixed default-branch file
`state/autonomy/TARGET_REF_CAS_QUALIFICATION_V1.json`. It is intentionally
`UNAVAILABLE`. A candidate file, comment, cached artifact, digest alone or unit
test cannot activate it. Qualified evidence must bind the adapter bytes,
repository/node id, endpoint, equivalent protected test-reference policy,
current effective Main policy, bypass-free executor and independent verifier.
All ten named cases in `CAS_QUALIFICATION_CASES` need live, source-bound receipts:
wrong B, NFF, absent/stale/withdrawn review, failed/absent checks, changed H,
approved exact merge, and ambiguous response without replay. Negative server
cases require unchanged refs. Receipt locators/digests are attestations consumed
from the separately reviewed trusted file; the pure gate does not fetch them or
prove the independence of an identity string. Unit fixtures are explicitly
simulation and are not qualification artifacts.

`CAS_AUTOMATIC_MAIN_PROMOTION` is a literal false in the existing workflow and
`automatic_main_promotion_enabled` remains false in the existing contract.
Enabling it is a separate protected review after the server and governance
qualifications. It also requires an admitted durable cross-run attempt store
and recovery integration. The disabled workflow's run-scoped `/tmp` journal
and retained Action artifact do not by themselves prove cross-run crash safety.
This patch does not activate automation or modify native protections.

## Intent, ambiguity and recovery

Before the write, `publish-graphql` creates and fsyncs an exclusive intent file
and its directory. It records the request, its SHA-256, B/H/T/M, the qualified
capability and live admission. Failure to persist the intent prevents the write.
The caller must keep the same journal across restarts and invocations; an
existing journal prevents another mutation. `clientMutationId` correlates the
request; it is not an idempotency key. The transport uses the existing scoped
`gh` authentication, with JSON on stdin, a pinned github.com GraphQL POST and
no credential copying, retry, REST fallback or permission expansion.

The clean GraphQL payload contains only the matching `clientMutationId`.
The code never invents `merged:true` from it. After every attempted write,
including a timeout, an HTTP/GraphQL error, partial data or malformed JSON,
independent ref → M/TREE/ordered parents → ref readback runs. Errors and raw
responses are retained. Ambiguous/rejected responses remain HOLD even if M is
observed. A separate GET-only reconciliation may establish exact publication,
with original intent/digest validation and no repeat mutation. PR merge state,
Code Owner approval, CAS causality and broader completion are separate claims.

Use an exact snapshot already produced by the existing executor:

```sh
python3 -B tools/qikvrt_expected_head_promotion.py prepare-graphql --input snapshot.json
# Only with independently qualified transport/protection and durable journal:
python3 -B tools/qikvrt_expected_head_promotion.py publish-graphql \
  --input snapshot.json --attempt-file /durable/qikvrt/attempt.json
# Recovery is GET-only. Never invoke publish again with a different journal.
python3 -B tools/qikvrt_expected_head_promotion.py reconcile-graphql \
  --input /durable/qikvrt/attempt.json
```

The default qualification yields HOLD without a GraphQL request. Missing live
capabilities on 2026-10-12: no generic authenticated GraphQL POST/updateRefs
operation exposed to this client, no GraphQL credential delivered to its CLI,
Main unprotected with no rulesets or reviews, and no qualified equivalent
protected test reference. Existing authenticated REST reads and branch writes
do not establish these operation-specific capabilities. No protected-ref
mutation, workflow dispatch/rerun, review approval or Main promotion was made.

Current primary API and policy sources checked 2026-10-12:

- https://docs.github.com/en/graphql/reference/git
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

The GraphQL atomicity guarantee covers reference updates in one mutation;
review/check GETs and later readback are outside that transaction. GitHub's
native protection semantics for manually pushed merges, stale reviews and
last-push approval must be tested with the actual executor identity. A documented
primitive and passing simulations are not the live server qualification.
