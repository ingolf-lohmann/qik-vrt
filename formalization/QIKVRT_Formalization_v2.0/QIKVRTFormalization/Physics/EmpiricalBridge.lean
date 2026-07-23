import Std

/-!
# Empirical bridge for mathematical and physical claims

This module formalizes the boundary between a kernel-checked mathematical
model and a statement about measured physical reality.

Lean can check the internal mathematics of a model and the logical consequence
of explicitly supplied bridge assumptions.  It does not manufacture empirical
premises.  Therefore every promoted physical claim must expose:

* a mathematical model predicate,
* an observation/evidence predicate,
* a bridge from model plus evidence to a physical conclusion,
* and the exact assumptions used by that bridge.
-/

namespace QIKVRT.V2.Physics

/-- A typed separation of model states, observations, and physical claims. -/
structure EmpiricalContext where
  ModelState : Type
  Observation : Type
  PhysicalClaim : Type

/--
A physical bridge is auditable because the model condition, evidence condition,
and conclusion relation are separate first-class predicates.
-/
structure EmpiricalBridge (C : EmpiricalContext) where
  modelHolds : C.ModelState → Prop
  evidenceSupports : C.Observation → Prop
  concludes : C.ModelState → C.Observation → C.PhysicalClaim → Prop
  sound : ∀ m o p, modelHolds m → evidenceSupports o → concludes m o p

/-- A physical claim is discharged only relative to explicit model and evidence witnesses. -/
def PhysicallySupported {C : EmpiricalContext} (B : EmpiricalBridge C)
    (m : C.ModelState) (o : C.Observation) (p : C.PhysicalClaim) : Prop :=
  B.modelHolds m ∧ B.evidenceSupports o ∧ B.concludes m o p

/-- The bridge theorem: explicit model and evidence premises yield support. -/
theorem physicallySupported_of_bridge {C : EmpiricalContext}
    (B : EmpiricalBridge C) (m : C.ModelState) (o : C.Observation)
    (p : C.PhysicalClaim) (hm : B.modelHolds m)
    (ho : B.evidenceSupports o) : PhysicallySupported B m o p := by
  exact ⟨hm, ho, B.sound m o p hm ho⟩

/-- Removing either empirical premise prevents construction by this theorem. -/
theorem physicallySupported_has_model_evidence {C : EmpiricalContext}
    (B : EmpiricalBridge C) (m : C.ModelState) (o : C.Observation)
    (p : C.PhysicalClaim) (h : PhysicallySupported B m o p) :
    B.modelHolds m ∧ B.evidenceSupports o := by
  exact ⟨h.1, h.2.1⟩

/--
A deterministic forward model: every admissible transition strictly advances
an abstract time coordinate.  This captures the mathematical content needed to
exclude backward state propagation inside that model.
-/
structure ForwardModel where
  State : Type
  time : State → Nat
  Step : State → State → Prop
  advances : ∀ {a b}, Step a b → time a < time b

/-- No single admissible transition can propagate a state to an earlier or equal time. -/
theorem no_backward_step (M : ForwardModel) {a b : M.State}
    (h : M.Step a b) : ¬ M.time b ≤ M.time a := by
  exact Nat.not_le_of_lt (M.advances h)

/-- A finite chain of forward transitions preserves strict temporal order. -/
inductive Reachable (M : ForwardModel) : M.State → M.State → Prop
  | refl (a : M.State) : Reachable M a a
  | tail {a b c : M.State} : Reachable M a b → M.Step b c → Reachable M a c

/-- Every nontrivial reachable path ends no earlier than it starts. -/
theorem reachable_time_monotone (M : ForwardModel) {a b : M.State}
    (h : Reachable M a b) : M.time a ≤ M.time b := by
  induction h with
  | refl a => exact Nat.le_refl _
  | tail hab hbc ih =>
      exact Nat.le_trans ih (Nat.le_of_lt (M.advances hbc))

/--
A backward-looking classification can depend on a later observation without
changing the already-completed forward state path.
-/
structure RetrospectiveClassifier (M : ForwardModel) where
  Label : Type
  classify : M.State → M.State → Label

/-- Reclassification is a semantic map and does not itself assert a reverse transition. -/
def ReclassificationWithoutBackwardStep (M : ForwardModel)
    (R : RetrospectiveClassifier M) (past future : M.State) : Prop :=
  M.time past ≤ M.time future ∧
  ¬ M.Step future past ∧
  ∃ label, R.classify past future = label

/-- Forward reachability plus strict-step semantics yields non-retrocausal reclassification. -/
theorem reclassification_without_backward_step (M : ForwardModel)
    (R : RetrospectiveClassifier M) {past future : M.State}
    (hReach : Reachable M past future)
    (hDistinct : M.time past < M.time future) :
    ReclassificationWithoutBackwardStep M R past future := by
  refine ⟨reachable_time_monotone M hReach, ?_, ?_⟩
  · intro hBack
    have hAdvance := M.advances hBack
    exact (Nat.not_lt_of_ge (Nat.le_of_lt hDistinct)) hAdvance
  · exact ⟨R.classify past future, rfl⟩

#print axioms physicallySupported_of_bridge
#print axioms physicallySupported_has_model_evidence
#print axioms no_backward_step
#print axioms reachable_time_monotone
#print axioms reclassification_without_backward_step

end QIKVRT.V2.Physics
