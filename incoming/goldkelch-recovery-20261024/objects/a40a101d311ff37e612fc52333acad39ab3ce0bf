# Why TEMDD Liveness Matters

TEMDD separates two questions that software systems often mix together:

1. **Safety:** Did the system avoid claiming success without evidence?
2. **Liveness:** If the goal has not been reached, is there a justified way to keep making real progress?

A system can be perfectly safe and still be useless: it can refuse every unsafe action forever. Conversely, a system can keep doing things forever without getting closer to its goal. That is livelock.

The stronger TEMDD research objective is therefore **conditional convergence**.

## The idea

Every accepted transition is evidence-bound:

```text
BOUND INPUT
→ EXECUTE
→ OBSERVE
→ FRESH READBACK
→ IDENTITY / PROVENANCE BIND
→ NEXT BOUND INPUT
```

The observed successor is not trusted merely because a workflow says it succeeded. It becomes the next input only after fresh readback and binding.

That gives safety, but convergence needs more.

Define a progress measure `V(S)` over reachable states. Its values must belong to a well-founded order: there must be no infinite strictly descending chain.

The goal, subject and ranking stay fixed for the execution under examination.
Every transition outside the goal must satisfy `V(S_next) ≤ V(S_current)`;
for every internally productive step it must additionally satisfy:

```text
V(S_next) < V(S_current)
```

If those properties hold, the machine cannot perform infinitely many internally
productive steps while remaining outside the goal. To infer eventual goal
reachability, we must additionally establish that every non-goal execution
eventually performs a productive step or reaches the goal. Availability or
scheduler fairness alone does not supply a missing external prerequisite.

That is the precise technical content behind the word **inevitable**.

## What does not count as progress

TEMDD must not count any of these as convergence merely because activity occurred:

- retrying the same failed transport;
- refreshing a timestamp;
- generating another receipt for the same semantic state;
- moving HEAD while the goal-relevant state does not improve;
- transferring predecessor evidence to a mutated successor;
- waiting on a human, platform, network, or physical effect while pretending that the dependency was satisfied.

These cases must become either a smaller-ranked successor or an explicit `HOLD`.

Exposing a HOLD is useful diagnostic behavior, but a permanently absorbing
non-goal HOLD cannot prove goal reachability. The chosen contract requires
eventual HOLD release as a separate theorem premise and productive execution
after release. A finite observation ending in HOLD leaves the future unknown.
Repeated releases must not reset the rank; otherwise productive steps can cycle
forever despite each individual decrease.

## What must be tested

A convergence claim must survive counterexamples for:

- deadlock;
- livelock;
- cycles;
- evidence churn;
- unavailable external dependencies;
- permanently absorbing external HOLDs;
- repeated HOLD release with a rank reset;
- moving environments;
- successor mutation.

## What is proved today?

This document does **not** claim that global TEMDD convergence has already been proved.

The current status is:

```text
TEMDD_LIVENESS_CONVERGENCE_THEOREM = UNPROVED
EFFECT_ACK_DONE = FALSE
PREDECESSOR_EVIDENCE_TRANSFER = FALSE
```

The repository now contains the theorem obligation in a form that can be implemented, tested, falsified, refined, and eventually proved for concrete subsystems.

## The target theorem

```text
Safety
AND ProductiveLiveness
AND ExternalHoldRelease
AND WellFounded(V)
AND NonIncreaseOnEveryNonGoalStep(V)
AND StrictDecreaseOnEveryInternalProductiveStep(V)
AND FairExecution
AND StableRequiredEnvironmentAssumptions
IMPLIES GoalReachability
```

This is stronger than saying “the system keeps trying.”

Here `ProductiveLiveness = G(¬Goal → F(Goal ∨ ProductiveStep))` and
`ExternalHoldRelease = G((¬Goal ∧ ExplicitExternalHold) → F(Goal ∨ ¬ExplicitExternalHold))`.
The HOLD-inclusive response property is diagnostic only. A permanent HOLD
violates these premises; it does not weaken the meaning of `GoalReachability`.
The conclusion means eventual goal reachability on every maximal admissible
execution under the stated assumptions. Finite stopped runs are completed by
stuttering, so stopping outside the goal cannot satisfy liveness vacuously.
It supplies no universal completion deadline.

Executable finite-lasso regressions run in the existing Effect Ack conformance
gate. They reject permanent HOLD and rank-reset cycles and retain the global
theorem status `UNPROVED`.

It asks us to prove when **continued, evidence-bound operation cannot avoid eventually reaching the declared goal**.

That is the research programme.

— Ingolf Lohmann / QIK-VRT
