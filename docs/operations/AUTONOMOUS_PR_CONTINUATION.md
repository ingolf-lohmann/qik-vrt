<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Autonomous PR continuation

## Purpose

The repository may independently continue deterministic, repository-internal
repairs on an explicitly opted-in same-repository draft pull request. The
continuation is bounded by the active owner delegation and never substitutes
an external scientific review or a separately authorized publication effect.

## Opt-in

A draft pull request is eligible only when its body contains the exact marker:

```text
<!-- qikvrt-autonomous-self-heal:enabled -->
```

The scheduled worker processes at most one eligible pull request per run. The
head repository must equal the executing repository, the head must still equal
the immediately reobserved SHA, and history rewriting is forbidden.

## Deterministic sequence

```text
REOBSERVE_MAIN_AND_PR_HEAD
→ MERGE_CURRENT_MAIN_HISTORY_PRESERVING
→ RUN_ALLOWLISTED_SELF_HEAL_HANDLERS
→ VERIFY_PUBLICATION_OVERVIEW
→ VERIFY_REPOSITORY_NATIVE_INTEGRITY
→ RUN_CONTROLLER_TESTS
→ RUN_FULL_REPOSITORY_SUITE
→ PUSH_FAST_FORWARD_SUCCESSOR
→ REPOSITORY_DISPATCH_EXACT_HEAD_REVERIFICATION
→ PERSIST_COMMIT_STATUS_AND_PR_COMMENT
```

The first added repair class is `PUBLICATION_OVERVIEW_DRIFT`. It detects a
local `docs/publications/*/README.md` that is absent from either
`docs/publications/index.json` or `docs/publications/index.html`, adds only the
missing index entries, and then lets repository-native integrity regeneration
bind the changed bytes.

## Trigger semantics

A push performed with the workflow-provided `GITHUB_TOKEN` does not recursively
start ordinary push or pull-request workflows. The worker therefore emits the
explicit repository-dispatch event
`qikvrt_autonomous_exact_head_verify`. The receiving workflow checks out the
exact candidate SHA, runs the full repository suite, re-executes the QCE finite
formal package when present, and writes a distinct status to the candidate
commit.

This mechanism does not impersonate pre-existing workflow contexts and does
not alter branch protection.

## External boundaries

The following gates cannot be manufactured by repository automation:

- an identified independent Human Physics Review when the candidate requires
  one;
- a natural-person decision authorizing a concrete Zenodo payload;
- credentials and authorization for a cross-repository Mirror mutation.

The worker stops before these gates. A future cross-repository continuation may
use a separately configured GitHub App installation credential with access to
both repositories, but no such credential value is stored in the repository
and no Mirror or Zenodo effect is authorized by this contract.

## Prohibited effects

- force push or history rewrite;
- direct mutation of `main` by the proposal worker;
- unconditional automatic merge;
- branch-protection change;
- release or tag creation;
- deployment;
- Zenodo or IETF mutation;
- repository-wide `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` claims.

## Immediate execution — Owner principle of 2026-10-13

> Was du heute kannst besorgen, das verschiebe nicht auf morgen, sondern erledige es unmittelbar, denn alles andere war, ist und wird inakzeptabel sein.
>
> q.e.d.
> Ingolf Lohmann

Execute every safe, deterministic, authorized and actually callable next action
in the current work ring, through its tests, persistence and fresh readback.
Do not postpone executable work to another day, chat or run merely to return
an intermediate status. Reuse `tools/ai_handoff.py --client-receipt`: it already
rejects a terminal handoff with an executable successor. Its consistency
result is separate from live execution evidence. A genuine external or
protected-authority blocker keeps the task open with its exact retry condition;
other executable work continues. Preserve causal NOOP for unchanged failed
effects, existing authorization and review boundaries. The machine binding
extends `self_application_working_rule.immediate_execution_principle` in the
existing recursive policy, with no parallel controller or trigger.

## Recursive self-application — Owner rule of 2026-10-13

Apply the working method to its own results, errors, omissions and open
obligations across every applicable layer. Consume the exact preceding run's
results as successor inputs. Keep task identity, source, affected subject,
acceptance criterion and the smallest authorized causal repair. Execute an
admitted repair, test the changed subject, read back its effect and continue.
An unreadable or vanished subject remains an unreobserved obligation.

The existing `tools/ai_handoff.py --client-receipt` gate rejects dropped
predecessor duties, premature completion, uninspected existing routes,
unchanged failed retries and missing effect readbacks. Reuse that gate.
The existing Site evidence collector now carries current and unreobserved
duties in each persisted snapshot, with the previous verified snapshot's ID
and SHA-256. Its original-byte readback covers the duties as part of the same
record. The observer dispatches no native effects, DNS writes or permission
changes. Recording a task does not establish an available executor.

An unchanged failed effect is NOOP until its causal prerequisites or genuinely
available execution capability change. Observation clocks and unrelated node
lifecycle commits do not authorize another attempt. Other admitted work
continues. Each changed subject needs fresh dependent gates; predecessors
remain historical evidence, and their PASS does not transfer.

Preserve “Quod erat demonstrandum ingenium” as Ingolf Lohmann's formulation.
A scientific proof, novelty or improvement claim needs a concrete verified
delta in a stated scope. Iteration count, new bytes and the attributed phrase
alone do not establish that claim. This is an operational working rule.

The product-delivery target is `https://raumzeitterminal.de/`. DNS, TLS, useful
application delivery and authenticated native execution are separate
obligations. A different hostname, a successful observer, repository tests or
an HTTP-200-only observation does not establish product acceptance. Persist
and read back each layer through its supported authorized path; mark unknown
propagation rather than claiming adoption on Main, the Mirror or other clients.

The existing draft integration candidate #523 is reused for this request.
No parallel controller, new trigger or review bypass is created.
