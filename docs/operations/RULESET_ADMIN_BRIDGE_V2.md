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

The successor binds sole parent `59dc49b16c8ff43c229809aa9245c72cfbc44b2a` and
its own live PR/ref/head/tree. It runs on one genuine non-force owner push, not a
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
before calling the pinned reconciler and afterwards. The read credential used
for the final ruleset readback is not the administrative credential. The
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
