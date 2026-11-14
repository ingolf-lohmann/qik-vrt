# Repository-native DevOps autonomy (Issue #748)

## Authority and roles

The Product Owner / Principal authorizes objectives and acceptance criteria, not individual debugging, testing, CI, or GitHub maintenance operations. The existing repository writers, watchdogs, CI and admitted host executors perform these operations. ChatGPT is optional and must never be a liveness dependency, approval proxy, sole scheduler, or owner of a required continuation receipt.

Principal authorization is **not** GitHub's own workflow approval. Never manufacture platform admission or bypass branch protection, review, writer fencing, host access, or effect-acknowledgement gates.

## Synchronous bounded execution contract

For each admitted work unit, the repository-native executor must:

1. Read current authority HEAD/TREE and durable work queue; acquire or validate its exclusive writer fence.
2. Select the highest-priority **executable** unit. A blocked lane remains queued with its specific blocker; it does not globally stop unrelated admitted lanes.
3. Reproduce the first causal failure (TEMDD RED), apply the smallest reversible repair with existing generators/IaC, and execute positive, negative, restart/replay and fencing regressions (GREEN).
4. Regenerate deterministic manifests and integrity artifacts **after** source changes and before the final exact-HEAD test; do not race a second writer or rebase evidence from another HEAD.
5. Run unchanged native exact-HEAD CI and reviews; on new HEAD or failed check, invalidate old success evidence and continue the same unit or queue a bounded successor.
6. Independently read back repository/host/UI state and require a distinct EMP execution receipt and EAP effect acknowledgement before marking a productive effect DONE.
7. Persist a machine-readable continuation receipt before yielding or crossing any process, host, agent or chat boundary. Re-entry validates HEAD, writer lease/fence and receipt, then resumes the next idempotent step. Missing receipt is a recovery work unit, not DONE.

No client timer, competing controller, parallel app, or Vercel workaround. Existing GitHub Actions triggers and repository-owned execution paths provide wakeup/re-entry; any external automation is only a fallback, never the source of truth.

## Fail-closed states

- `DONE`: all acceptance criteria and independent effect readbacks match the exact admitted artifact and execution.
- `REPAIR_REQUIRED`: a technically executable local or independent lane remains; perform it, not merely report it.
- `EXTERNAL_ADMISSION_REQUIRED`: only the lane requiring platform authorization is blocked. Continue all independent authorized lanes; preserve the admission request without escalating debugging to the Principal.
- `CONTEXT_HANDOFF_BLOCKED`: continuation receipt missing or stale; restore it and revalidate before any write.
- `CAPABILITY_BLOCKED`: an unavailable adapter prevents that specific effect, not unrelated work.

Every receipt must bind work-unit ID, authority, exact HEAD/TREE, writer lease/fence, attempted action, outcome, evidence digest/URL, blocked lane, next idempotent step and acceptance criteria. A commit, passing unit test, handoff, D1 snapshot, or Principal declaration alone is never an EAP effect.

## Regression invariant

`scripts/check_digital_twin_stall.py --self-test` includes a regression ensuring GitHub `action_required` does not erase independently repairable Sites/receipt work. This classifier is **not** itself an executor. Its successor decisions must be consumed by the existing fenced repository-native writer. Until that integration and independent productive readback are proven, the overall Definition of Done remains OPEN.
