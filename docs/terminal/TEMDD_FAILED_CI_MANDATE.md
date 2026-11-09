<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# QIK-VRT Trusted Mesh — mandatory TEMDD after failed continuous development/integration

**Decision:** 2026-11-09, Owner statement by Ingolf Lohmann.
**Declared authorization:** Principal, Code Owner, Product Owner (same person).
**Authority:** `ingolf-lohmann/qik-vrt` only.
**Scope:** All failed continuous development / continuous integration runs and
their dependent release/admission decisions. This rule is fail-closed and does
not turn Owner approval into technical test evidence or independent review.

## Normative rule

When a CI/CD run fails, times out, is cancelled or is blocked as
`action_required`, the responsible development path **MUST** apply
Tested Event Model Driven Development (TEMDD) before marking the
failure resolved, accepting a successor or authorizing a dependent effect.

The required TEMDD sequence is:

1. **OBSERVE** the original failed workflow, immutable run ID and attempt,
   actual source repository, exact commit HEAD/tree when independently available,
   failing jobs, timestamps, tool version and raw diagnostic evidence.
2. **CLASSIFY** the failure as source, test, integrity, infrastructure,
   governance, protected-host or unknown; unknown and unobserved remain `HOLD`.
3. **MODEL** the failed behavior as a falsifiable event/invariant with
   expected negative and positive behavior; preserve preceding evidence.
4. **TEST** a bounded reproducer at the exact failing source. If the failed
   step cannot be reproduced, say so explicitly. A pre-existing TEMDD suite
   passing does not count as reproduction of that step.
5. **REPAIR** only the smallest causal and reversible change, separately
   review the change, and add the failure-specific regression before merging.
6. **RETEST** the complete relevant gates at the exact successor HEAD/TREE,
   verify repository manifest and SHA-256, and reobserve the failed function.
7. **READBACK** independently the required effect/receipt, writer fence,
   authorization, durable ledger and host only when relevant and authorized.

A missing original job log, blocked workflow, unknown exact source, failed
regression, missing reviewer, unknown host or missing independent effect
readback MUST remain `HOLD`. Neither a green unrelated CI job nor the
workflow-run observer is a release, production, merge, approval or
`EFFECT_ACK_DONE` authority. No reset, event renumbering, evidence rewrite,
unauthenticated replay, or retry of an irreversible effect is permitted.

## Executable bounded response

`.github/workflows/qikvrt_temdd_failure_response.yml` observes completed
failures of the listed principal development/CI workflows on the **default
branch** after this change is admitted. It reads job metadata, isolates
a same-repository failed source at its exact SHA without checkout credentials,
runs existing TEMDD regression suites and writes an observation JSON plus
test log as CI artifacts. `tools/qikvrt_temdd_failure_response.py` always
emits `HOLD`, even when those generic TEMDD regressions pass; it cannot
mistake generic tests for a successful failed-step reproducer.

The observer has `contents: read` and `actions: read` only. It does not
mutate Main, journals, pull requests, releases, secrets or the original host.
Its own failure is not subscribed as an event source; therefore it cannot
recursively heal its own failing workflow.

**Coverage boundary:** GitHub `workflow_run` subscriptions explicitly name
workflow producers; other workflows are still subject to this normative rule,
but are not automatically observed until added to the subscription. Failed
jobs from pull requests with a different head repository are classified
`HOLD` without executing untrusted fork code. A disabled or unapproved
Actions workflow also remains `HOLD`. This candidate is not active for
workflow-run failure events until merged into the default branch and enabled.

## DoD for this rule

- [ ] Owner-approved normative TEMDD rule committed to Authority Main.
- [ ] Exact source and independent reviewer admission passed (no self-approval).
- [ ] Trigger coverage validated for failing development/CI producers.
- [ ] Demonstrated failure yields bound `OBSERVE/CLASSIFY/ACTION/READBACK/HOLD`
      receipt with original failed job metadata and SHA-256 test-log digest.
- [ ] Negative tests prove wrong HEAD, missing jobs, blocked workflow and
      passing unrelated TEMDD tests cannot yield `PASS` or `EFFECT_ACK_DONE`.
- [ ] Failed-step reproduction, smallest reversible correction, exact-successor
      retest and independent readback have been demonstrated on an actual case.
- [ ] Original production, governance and EAP acceptance gates remain distinct;
      the global QIK-VRT DoD remains blocked until independently satisfied.

**Current candidate status:** NOT ADMITTED; no production effect claimed.
