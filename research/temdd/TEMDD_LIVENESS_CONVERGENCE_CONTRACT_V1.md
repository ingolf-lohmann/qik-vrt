# TEMDD Liveness and Convergence Contract v1

Status: **research contract / theorem obligation — not yet a proved global theorem**

## Purpose

TEMDD already distinguishes a successful transport or workflow execution from an observed effect. This contract states the stronger research question: under which explicit assumptions does repeated evidence-bound continuation necessarily reach an accepted goal rather than deadlock, livelock, or cycle forever?

The claim is deliberately conditional. “Inevitable” is not asserted from observation alone. It becomes machine-verifiable only after the assumptions, progress order, and proof obligations below are discharged for the claimed transition system.

## State progression

For every transition:

```text
BOUND_INPUT(S_n)
→ EXECUTE(E_n)
→ OBSERVE(S_{n+1})
→ FRESH_READBACK(S_{n+1})
→ IDENTITY_AND_PROVENANCE_BIND(S_{n+1})
→ NEXT_BOUND_INPUT(S_{n+1})
```

Thus the observed successor becomes the next input **only after fresh identity and provenance binding**.

```text
PREDECESSOR_EVIDENCE_TRANSFER = FALSE
TRANSPORT_ACK != EFFECT_ACK
EFFECT_ACK_DONE(n) != GLOBAL_DONE
```

## Safety

Safety means that no transition may be accepted without satisfying its bound invariants and acceptance predicate.

```text
ACCEPT(S_n,E_n,S_{n+1})
⇒ BOUND(S_n)
 ∧ ADMISSIBLE(E_n)
 ∧ FRESH_READBACK(S_{n+1})
 ∧ BOUND(S_{n+1})
 ∧ INVARIANTS_HOLD(S_{n+1})
```

## Execution and temporal semantics

Fix one exact subject, transition relation, goal predicate and ranking function.
Quantify over **every maximal admissible execution** under the declared
environment assumptions, not only over a selected successful run. Complete a
finite stopped execution by stuttering at its final state; a non-goal deadlock
therefore cannot satisfy liveness vacuously. `G` means always and `F` means
eventually on that execution. `GoalReachability` means `F Goal` on every such
execution; it asserts neither a uniform deadline nor termination of the global
state machine.

`ProductiveStep` at position `n` denotes an actually executed, admissible,
freshly bound `InternalProductiveStep(S_n,S_{n+1})`, not just an available action,
receipt or intention. `ExplicitExternalHold` is a state predicate exposing an
unresolved external dependency. It is neither `Goal` nor `ProductiveStep`.

## Diagnostic response and productive liveness

The previous disjunction is retained **only as a diagnostic response property**:

```text
DiagnosticResponse = G(¬Goal → F(Goal ∨ ProductiveStep ∨ ExplicitExternalHold))
```

It can hold on an absorbing non-goal HOLD forever and is not a convergence
premise. The goal-reachability obligation instead requires:

```text
ProductiveLiveness = G(¬Goal → F(Goal ∨ ProductiveStep))
ExternalHoldRelease = G((¬Goal ∧ ExplicitExternalHold) → F(Goal ∨ ¬ExplicitExternalHold))
```

Every HOLD in an execution satisfying the theorem premises must eventually be
released or reach the goal. Release alone is insufficient: subsequent productive
execution must also satisfy `ProductiveLiveness`. Scheduler fairness does not
create a missing human, platform or physical effect and does not imply external
release. These are separate obligations to establish for the concrete subsystem.
A permanently absorbing non-goal HOLD violates both obligations. Its honest
disposition is `THEOREM_PREMISES_NOT_SATISFIED`, not `GoalReachability`.

A finite observation ending in HOLD leaves its future **UNKNOWN**. Elapsed time,
a timeout or a bounded trial cannot establish eventual release or permanence;
the permanent-HOLD counterexample below uses an explicitly declared self-loop.

## Well-founded progress

To prove convergence, define a ranking/progress function

```text
V : ReachableStates → W
```

where the strict order `<` on `W` is well-founded. Write `a ≤ b` for
`a = b` or `a < b`. Every transition out of a non-goal state, including an
external release, retry or stutter, must be non-increasing. Every internally
productive successor must strictly decrease the rank:

```text
¬Goal(S) ∧ Step(S,S') ⇒ V(S') ≤ V(S)
¬Goal(S) ∧ InternalProductiveStep(S,S') ⇒ V(S') < V(S)
```

A transition that merely repeats the same semantic state, refreshes timestamps, retries transport, or produces new receipts without reducing the declared rank does **not** count as convergence progress.

Non-increase prevents an external transition from resetting the rank between
productive decreases. If the environment changes the bound subject, goal or
ranking, restart verification for that successor; do not transfer the previous
convergence premises or evidence.

## Conditional convergence theorem obligation

The target theorem is:

```text
Safety
∧ ProductiveLiveness
∧ ExternalHoldRelease
∧ WellFounded(V)
∧ NonIncreaseOnEveryNonGoalStep(V)
∧ StrictDecreaseOnEveryInternalProductiveStep(V)
∧ FairExecution
∧ StableRequiredEnvironmentAssumptions
⇒ GoalReachability
```

This is a theorem obligation, not a theorem claimed as proved by this file.

The conditional argument is: an infinite execution avoiding `Goal` must, by
`ProductiveLiveness`, execute infinitely many productive steps. Non-increase
between their strict decreases would produce an infinite descending chain in
`W`, contradicting well-foundedness. A finite non-goal stop is excluded by its
stuttering completion. `ExternalHoldRelease` makes the external obligation
explicit; `DiagnosticResponse` cannot substitute for productive liveness.
The abstract argument does not discharge these premises for QIK-VRT or supply
a kernel-checked proof.

## Counterexample obligations

Any implementation claiming convergence MUST test at least:

1. **Deadlock:** non-goal state with no admissible internal successor.
2. **Livelock:** transitions continue but the semantic rank never decreases.
3. **Cycle:** a previously bound semantic state recurs without a strictly smaller rank.
4. **Evidence churn:** receipts/HEADs change while the goal-relevant semantic state does not improve.
5. **External dependency:** required human/platform/physical effect is unavailable; system must HOLD rather than synthesize success.
6. **Moving environment:** an external prerequisite changes faster than it can be bound; convergence requires an explicit stability/fairness assumption.
7. **Successor mutation:** evidence from a predecessor is not accepted for the mutated successor.
8. **Permanent external HOLD:** an absorbing non-goal HOLD satisfies diagnostic response but violates productive liveness and hold release; it is not a goal-reachability witness.
9. **Released HOLD with rank reset:** repeated release and productive decrease can still cycle if release increases the rank; reject the non-increase premise.

The existing conformance gate includes `tests/test_temdd_liveness_convergence.py`
with executable
finite-lasso regressions. A lasso is a finite prefix followed by a declared
repeating cycle, so its temporal checks cover that whole infinite model, not
an arbitrary observation timeout. The tests evaluate the companion JSON's
temporal formulas and theorem premises. They are bounded model regressions,
not a proof of the theorem or of a concrete QIK-VRT subsystem's convergence.
The original Effect Ack conformance source remains byte-identical because its
bytes are bound by an existing publication source manifest.

```sh
python3 -B -m unittest -v tests.test_temdd_liveness_convergence.TemddLivenessConvergenceTests
```

## Meaning of “inevitable”

Within TEMDD, “inevitable” may be used as a technical conclusion only for a declared transition system for which the convergence obligations above have been discharged.

The intended meaning is therefore:

> Given productive liveness, eventual external-hold release, the stated environment and fairness assumptions, and a well-founded ranking that never increases outside the goal and strictly decreases on every internally productive non-goal step, the system cannot remain forever outside the goal set.

Without those premises, inevitability remains a hypothesis.

## Relationship to Effect Ack

`EFFECT_ACK_DONE` is local to one bound effect. It closes a transition; it does not terminate the global state machine.

```text
S_n --E_n--> S_{n+1}
OBSERVE → READBACK → BIND
EFFECT_ACK_DONE(E_n)
S_{n+1} becomes the next bound input
```

This permits an epistemic spiral: each verified effect closes one proof obligation while its verified successor opens the next.

## Acceptance for this research contract

This contract reaches its own EFFECT_ACK_DONE only after:

- a machine-readable companion contract exists,
- executable deadlock/livelock/cycle/evidence-churn and permanent-HOLD/rank-reset tests exist,
- at least one concrete QIK-VRT subsystem supplies an explicit ranking `V`,
- the ranking is checked for strict decrease on productive transitions and non-increase on all non-goal transitions,
- the stated environment assumptions are explicit,
- an independent fresh readback confirms the exact published subject.

Until then:

```text
TEMDD_LIVENESS_CONVERGENCE_THEOREM = UNPROVED
EFFECT_ACK_DONE = FALSE
```

— Ingolf Lohmann / QIK-VRT research programme
