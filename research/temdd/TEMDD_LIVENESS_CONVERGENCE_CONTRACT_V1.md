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

## Liveness

Liveness is a separate obligation:

For every reachable non-goal state that satisfies the declared environment assumptions, an admissible productive successor must eventually be available and executed, or the system must expose an explicit external dependency rather than pretending to progress.

```text
∀ S ∈ Reachable:
  ¬Goal(S) ∧ EnvironmentAssumptions(S)
  ⇒ ◇(ProductiveSuccessor(S) ∨ ExplicitExternalHold(S))
```

An external hold is not goal reachability.

## Well-founded progress

To prove convergence, define a ranking/progress function

```text
V : ReachableStates → W
```

where `W` is well-founded. Every internally productive successor must strictly decrease the rank:

```text
¬Goal(S) ∧ InternalProductiveStep(S,S')
⇒ V(S') < V(S)
```

A transition that merely repeats the same semantic state, refreshes timestamps, retries transport, or produces new receipts without reducing the declared rank does **not** count as convergence progress.

## Conditional convergence theorem obligation

The target theorem is:

```text
Safety
∧ Liveness
∧ WellFounded(V)
∧ StrictDecreaseOnEveryInternalProductiveStep(V)
∧ FairExecution
∧ StableRequiredEnvironmentAssumptions
⇒ GoalReachability
```

This is a theorem obligation, not a theorem claimed as proved by this file.

## Counterexample obligations

Any implementation claiming convergence MUST test at least:

1. **Deadlock:** non-goal state with no admissible internal successor.
2. **Livelock:** transitions continue but the semantic rank never decreases.
3. **Cycle:** a previously bound semantic state recurs without a strictly smaller rank.
4. **Evidence churn:** receipts/HEADs change while the goal-relevant semantic state does not improve.
5. **External dependency:** required human/platform/physical effect is unavailable; system must HOLD rather than synthesize success.
6. **Moving environment:** an external prerequisite changes faster than it can be bound; convergence requires an explicit stability/fairness assumption.
7. **Successor mutation:** evidence from a predecessor is not accepted for the mutated successor.

## Meaning of “inevitable”

Within TEMDD, “inevitable” may be used as a technical conclusion only for a declared transition system for which the convergence obligations above have been discharged.

The intended meaning is therefore:

> Given the stated environment assumptions, fair execution, and a proved well-founded ranking that strictly decreases on every internally productive non-goal step, the system cannot remain forever outside the goal set.

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
- executable deadlock/livelock/cycle/evidence-churn tests exist,
- at least one concrete QIK-VRT subsystem supplies an explicit ranking `V`,
- the ranking is checked on its productive transitions,
- the stated environment assumptions are explicit,
- an independent fresh readback confirms the exact published subject.

Until then:

```text
TEMDD_LIVENESS_CONVERGENCE_THEOREM = UNPROVED
EFFECT_ACK_DONE = FALSE
```

— Ingolf Lohmann / QIK-VRT research programme
