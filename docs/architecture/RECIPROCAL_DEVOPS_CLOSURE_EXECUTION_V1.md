<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Reciprocal DevOps closure: one executable step

`tools/qikvrt_pr_closure_engine.py` reuses the role-local decision core from
Mirror PR #396 at `1819da9bf08478a7052312d24819a8c25c1533a3`. Its stricter
execution boundary composes the pure `evaluate-closure` acceptance evaluator
from PR #433. Acceptance readiness never grants execution permission.

The #433/#434 consolidation also composes `evaluate` and `verify-readback` in
the same strict-JSON core. The closure controller's merge admission calls that
shared promotion evaluator after its existing check/status and native protection
checks. It observes repository/PR/HEAD/TREE, the native independent review, the
latest workflow run and attempt, and the actual jobs and executed steps. The four
required promotion workflows match the trusted-main promotion workflow; all
observed applicable executions and current checks/statuses remain mandatory.
Other open PR file overlaps block merge admission. The final fence repeats the
complete observation; acceptance-ready closure JSON cannot override a blocker
or create a second executor. Positive single-step fixtures remain CONTINUE.

The authenticated host supplies the same repository-scoped transport interface
for either role: read, fresh capability probe, and one attempted mutation. The
GitHub transport reads its actual principal and repository permission; a host
connector must derive these from its signed-in connector and its callable
operations. An arbitrary JSON snapshot, token name, secret declaration, or
Mirror capability cannot authenticate the Authority. Missing access blocks.

One invocation performs the following bounded sequence:

1. Probe principal, role-local write permission and callable operations.
2. Exhaust all pages of open PRs and branches, bind Main HEAD/TREE, and repeat
   the census unchanged. Duplicates, truncation and drift block.
3. Walk PRs in `(created_at, number)` order using the reused decision core.
   Review requests additionally require a positive exact-handle membership
   and permission probe; a permission summary alone is insufficient.
   Select exactly one supported, currently admitted action, or retain the
   first exact blocker and every scanned decision.
4. Repeat the whole inventory, capability and exact-head gate observations;
   fence the same selection. Record and fsync a create-only intent before I/O.
5. Attempt exactly one review request, SHA-bound native branch update, or native
   merge. Merges additionally require current independent exact-head approval,
   all applicable successful gates, and enforced native Code Owner, last-push,
   strict check and no-force rules. Both roles use `merge_method=merge`.
6. Read fresh state after success **or uncertain I/O**, repeat the complete
   census, verify the selected effect and preservation of all original PR heads
   and branch tips. Changed/deleted refs require observed Git ancestry; a native
   merge additionally requires a two-parent merge object containing the exact
   original PR head, reachable from the resulting Main.
7. Bind intent, before/after census, actual principal, effect and readback in a
   hash-linked, verified Effect-ACK CONTINUE chain and a receipt. Return to the
   host for another fresh step; this code creates no second scheduled executor.

No ref deletion, force update, squash/rebase merge, approval, comment, release,
IETF or Zenodo mutation is available. Legacy `FAST_FORWARD_CAS` remains a
readable policy label from #396; this successor never writes Main refs. Closing
an equal-tree/unmerged PR does not satisfy native lossless closure and is blocked.
Unknown mergeability is never permission to update a branch.

The journal must be retained by the host across invocations. Unresolved intents
block later effects. Recovery is read-only, binds the recorded intent and
original protocol, and never retries a mutation. A host connector may execute
one supported action after the same fresh preflight and persist its own
readback receipt; observation replay cannot perform that action.

```sh
python3 -B tools/qikvrt_pr_closure_engine.py validate-policy
python3 -B tools/qikvrt_pr_closure_engine.py run --repository ingolf-lohmann/qik-vrt
# GH_TOKEN comes only from the authenticated host, never a repository file.
python3 -B tools/qikvrt_pr_closure_engine.py run --repository ingolf-lohmann/qik-vrt \
  --apply --journal-dir <durable-private-host-journal> --output <receipt.json>
python3 -B tools/qikvrt_pr_closure_engine.py recover --repository ingolf-lohmann/qik-vrt \
  --intent <durable-private-host-journal>/<intent-id>.intent.json --output <receipt.json>
make reciprocal-devops-closure-test
```

The existing policy has no enforced Mirror ruleset binding. Therefore this
successor cannot merge Mirror PRs until the actual required native protection
is bound and freshly verified; repository `push=true` does not close that gap.
A successful review request establishes only that request, never independent
approval, technical-review success, Main integration, reciprocal execution,
object-closure completeness or public byte equality. Both directions and public
repository/IETF/Zenodo bytes remain separate acceptance evidence.
`TARGET_REACHED`, `EFFECT_ACK_DONE` and Authority/Mirror equality remain false.
