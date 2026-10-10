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
available and verified. The existing merge transport is retained as inactive
code, not certified as CAS.

Candidate files, PR comments, cached evidence and an agent's assertion cannot
enable the capability. A later adapter must bind its verified operation and
evidence digest to the exact repository, target ref, expected old Main and
reviewed candidate head; it must retain review, ruleset and permission gates.
The pure decision core validates a trusted producer's binding; it cannot
independently certify that producer or the underlying server. A populated
digest is not a proof by itself. Tests using a simulated VERIFIED adapter are
model-relative unit tests, not live GitHub assurance.

## Publication closure

After an admitted effect, the existing core performs GET-only reads in order:

1. Exact `refs/heads/main` object.
2. Immutable commit named by the merge response: its SHA, TREE and ordered
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
