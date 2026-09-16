# Existing Mesh administrative carrier: credential adapter repair

This increment continues Mirror PR #381 on `ops/ruleset-admin-bridge-20260915`.
It is not a product promotion, a native reviewer, a branch cleaner, or an assertion
that repository autonomy is operating. The only authorized external mutation is
the already-canonical Authority ruleset #19344903, through the unchanged pinned
`tools/qikvrt_ruleset_reconcile.py` on Authority Main.

## Cause and executable repair

The previous native run 35027652358 reached the pinned Authority tool but passed
an empty static `QIKVRT_GITHUB_ADMIN_TOKEN`. A declared credential name was being
treated as an available credential. The earlier event guard also still required
the bootstrap parent, rather than the actual materialized predecessor.

The current adapter binds the actual sole parent returned for its exact head,
the native push before/after pair, and its own live PR/ref/head/tree. It runs on one genuine non-force owner push, not a
rerun or a timer. Every subsequent mutation requires a new, explicitly bound
successor; receipts cannot be transferred to a child, even with identical files.

`tools/qikvrt_ruleset_admin_bridge.py` reads only the already-documented App
configuration names: variable `QIKVRT_RULESET_APP_CLIENT_ID` (issue #1072), or
variable `QIKVRT_RULESET_APP_ID` (the existing #1071 implementation), and secret
`QIKVRT_RULESET_APP_PRIVATE_KEY`. If both identifiers exist, both must match the
same authenticated App. Their availability is checked in the actual Actions
step, not inferred from source or from owner authorization. Missing fields yield
`RULESET_APP_CONFIGURATION_MISSING` and non-secret presence booleans. No PAT,
secret-name guessing, secret enumeration or new credential is introduced.

The adapter signs an RS256 App JWT using OpenSSL. Only PUBLIC unsigned claims
are temporarily written; the private key travels through process stdin. It
verifies App identity, the Goldkelch installation and Administration:write
before requesting a token restricted to repository ID 1271407206. It checks the
returned permissions, single-repository grant and expiry, then independently
checks the token's accessible repositories. It reobserves the exact subjects
before calling the pinned reconciler and afterwards. A separate GET first uses
the read credential. When GitHub hides the bypass list, a further complete GET
uses the already-scoped App token through the adapter's GET-only ruleset path.
This is HTTP-response independence, not independent-principal evidence. The
installation token remains process-local and is revoked in `finally`.

No private key, JWT, installation token, raw API exception or unrestricted
response enters logs, artifacts, repository files or step outputs. The adapter
itself allows no ruleset PUT, PR review, merge, source write or branch deletion;
only the pinned reconciler can apply its unchanged ETag-bound policy.

The unrelated existing `admit` job is preserved; this increment does not claim
to repair or execute that legacy workflow-admission route.

## Validation and limits

`make ruleset-admin-bridge-test` is a dependency of normal `make test` and is
also run by the existing administrative workflow before it receives App secrets.
Regressions exercise missing configuration, wrong App/installation/repository,
insufficient or excessive permission, expiry, pre/post-effect subject drift,
transport without independent readback, secret redaction and token revocation.

A `RULESET_CURRENT` receipt certifies only exact ruleset equality. If no PUT was
needed, `effect_observed` remains false. An exception after entering the pinned
reconciler leaves `mutation=UNKNOWN`, never a fabricated `NONE`. Native P3,
post-review reobservation, legitimate Main integration, fresh Main validation
and operational repository-wide completion remain separate obligations.

The source successor initially needs the existing canonical integrity
materializer. Its generated delta must be checked independently against the
three-file integrity allowlist and validated on its own literal successor.
No generated worktree result, predecessor test or administrative receipt may be
used as successor-local P2 evidence. This administrative job always executes the
pinned Authority Main implementation, not a new product implementation.

## Scope correction after native execution on 2026-09-16

Native run `35076597819`, job `104730374372`, executed the 22 adapter
regressions and seven pinned Authority-reconciler tests successfully on source
`277c25f2cde3b996939e24373b11ba2368ff8ad5`. It then held with
`PRODUCT_PR_DRIFT`: the copied product #1104 binding was already stale. Its
non-secret receipt independently exposed all three documented App fields as
empty in that particular Actions step. No token was minted and no PUT occurred.
This result belongs only to that source head, not to any successor.

The existing materializer produced child
`3cf103828efe7b5087b7b61f406557454b0bffb2`, tree
`b1e99fe5d23dd7b559e81681f88622bb3d071dd7`, with exactly the three
canonical integrity paths changed. The next source increment preserves it as
its sole parent. No tests or administrative receipt are transferred from it.

Ruleset #19344903 is an independent administrative subject. Binding its repair
to the head of unrelated product PR #1104 caused unrelated development to stop
an otherwise unchanged administrative work unit. The corrected adapter binds
only the live #381 carrier/ref/head/tree/parent and exact Authority Main, pinned
reconciler bytes, canonical policy, installation and ruleset. It never submits
or authorizes a product review, merge or deployment. Product heads retain their
own separate P2-P7 obligations; none is certified by this receipt.

Two additional permanent regressions reproduce the unwanted product dependency
and require an actionable missing-configuration result that retains the exact
Main and carrier bindings. Missing App configuration now explicitly requests
`BIND_EXISTING_RULESET_APP_CONFIGURATION_IN_CARRIER_ACTIONS`, rather than another
unspecified source repair or an unproductive rerun. The previously observed
empty configuration does not prove that an App or a credential is absent from
all repository Environments or from the owner's account.

## Complete readback, not a redacted projection (2026-09-16)

GitHub documents that GET `/repos/{owner}/{repo}/rulesets/{ruleset_id}` returns
`bypass_actors` only to callers with ruleset write access:
https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset

The pinned reconciler normalizes an omitted bypass list to an empty list. The
adapter must therefore not infer `bypass_actors=[]` from the ordinary read
credential's redacted response. The pinned writer and canonical policy remain
unchanged; the bridge now requires an explicitly present list before accepting
full equality. No new credential, permission, scheduler or writer is introduced.

When the first public projection lacks a list, the existing scoped token must
obtain a complete pre-operation snapshot before the writer is called. This also
handles an apparently CURRENT public projection whose hidden bypass list still
differs. Missing, null or malformed full visibility is a fail-closed
`RULESET_BYPASS_VISIBILITY_MISSING`, before PUT. A truly current full snapshot
needs no PUT even if token creation was necessary just for visibility.

After any operation, the bridge performs a new public GET and, when redacted,
a new complete GET using the same scoped App token. Neither the PUT response
nor the pre-operation snapshot is reused. Both the visible projection and full
policy evaluation must agree, the normalized observed and desired digests must
be equal, and the carrier/Main bindings must still match. Only then does receipt
schema `qikvrt_ruleset_admin_bridge_v5` record `ruleset_comparison=MATCH` and
`full_readback=true`. It names its readback credential class, never its value,
and declares `SEPARATE_GET_NOT_SEPARATE_PRINCIPAL`. Review, source promotion,
deployment, predecessor evidence transfer and `effect_ack_done` remain false.

Eight permanent regressions cover redacted false-current responses, complete
GET selection, already-current visibility without PUT, hidden nonempty bypass
repair, nonempty post-PUT bypass, malformed or missing full visibility, visibility
loss after PUT, and missing configuration despite a matching visible projection.
They extend the existing test module and normal Makefile/workflow admission.

This source change does not provision or prove delivery of App configuration.
Exact source `36829a18b79fcb3ce4a72c5d49d508b57183a04e`, native run
`35085096153`, returned all three configuration-presence booleans false and
`mutation=NONE`. That is historical evidence of non-delivery to that specific
Actions job, not proof of absence from the owner's account and not evidence for
any successor. Current-head execution and full repository P2 remain mandatory.
