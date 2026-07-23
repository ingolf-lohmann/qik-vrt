import Std

/-!
# Empirical bridge for mathematical and physical claims

This module formalizes the boundary between a kernel-checked mathematical
model and a statement about measured physical reality.

Lean can check the internal mathematics of a model and the logical consequence
of explicitly supplied bridge assumptions. It does not manufacture empirical
premises. Every promoted physical claim must expose a mathematical model,
observational evidence, and the bridge assumptions relating both.
-/

namespace QIKVRT.V2.Physics

structure EmpiricalContext where
  ModelState : Type
  Observation : Type
  PhysicalClaim : Type

structure EmpiricalBridge (C : EmpiricalContext) where
  modelHolds : C.ModelState → Prop
  evidenceSupports : C.Observation → Prop
  concludes : C.ModelState → C.Observation → C.PhysicalClaim → Prop
  bridgeRule : ∀ m o p, modelHolds m → evidenceSupports o → concludes m o p

def PhysicallySupported {C : EmpiricalContext} (B : EmpiricalBridge C)
    (m : C.ModelState) (o : C.Observation) (p : C.PhysicalClaim) : Prop :=
  B.modelHolds m ∧ B.evidenceSupports o ∧ B.concludes m o p

theorem physicallySupported_of_bridge {C : EmpiricalContext}
    (B : EmpiricalBridge C) (m : C.ModelState) (o : C.Observation)
    (p : C.PhysicalClaim) (hm : B.modelHolds m)
    (ho : B.evidenceSupports o) : PhysicallySupported B m o p := by
  exact ⟨hm, ho, B.bridgeRule m o p hm ho⟩

theorem physicallySupported_has_model_evidence {C : EmpiricalContext}
    (B : EmpiricalBridge C) (m : C.ModelState) (o : C.Observation)
    (p : C.PhysicalClaim) (h : PhysicallySupported B m o p) :
    B.modelHolds m ∧ B.evidenceSupports o := by
  exact ⟨h.1, h.2.1⟩

structure ForwardModel where
  State : Type
  time : State → Nat
  Step : State → State → Prop
  advances : ∀ {a b}, Step a b → time a < time b

theorem no_backward_step (M : ForwardModel) {a b : M.State}
    (h : M.Step a b) : ¬ M.time b ≤ M.time a := by
  have hAdvance : M.time a < M.time b := M.advances h
  omega

inductive Reachable (M : ForwardModel) : M.State → M.State → Prop
  | refl (a : M.State) : Reachable M a a
  | tail {a b c : M.State} : Reachable M a b → M.Step b c → Reachable M a c

theorem reachable_time_monotone (M : ForwardModel) {a b : M.State}
    (h : Reachable M a b) : M.time a ≤ M.time b := by
  induction h with
  | refl a => exact Nat.le_refl _
  | tail hReach hStep ih =>
      have hAdvance : M.time _ < M.time _ := M.advances hStep
      omega

structure RetrospectiveClassifier (M : ForwardModel) where
  Label : Type
  classify : M.State → M.State → Label

def ReclassificationWithoutBackwardStep (M : ForwardModel)
    (R : RetrospectiveClassifier M) (past future : M.State) : Prop :=
  M.time past ≤ M.time future ∧
  ¬ M.Step future past ∧
  ∃ label, R.classify past future = label

theorem reclassification_without_backward_step (M : ForwardModel)
    (R : RetrospectiveClassifier M) {past future : M.State}
    (hReach : Reachable M past future)
    (hDistinct : M.time past < M.time future) :
    ReclassificationWithoutBackwardStep M R past future := by
  refine ⟨reachable_time_monotone M hReach, ?_, ?_⟩
  · intro hBack
    have hAdvance : M.time future < M.time past := M.advances hBack
    omega
  · exact ⟨R.classify past future, rfl⟩

#print axioms physicallySupported_of_bridge
#print axioms physicallySupported_has_model_evidence
#print axioms no_backward_step
#print axioms reachable_time_monotone
#print axioms reclassification_without_backward_step

end QIKVRT.V2.Physics
