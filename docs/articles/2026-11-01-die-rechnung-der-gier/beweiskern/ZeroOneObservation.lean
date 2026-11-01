/-
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann.
-/

import QIKVRTUniversalOntology.Core
import QIKVRTFormalization.Decision.ObservationSufficiency

/-!
# Zero, one, distinction, observation and effect recovery

This conservative companion reuses the existing ontology's `Distinction` and
the existing observation-sufficiency theorem. It does not modify either source.

The algebraic assumptions are explicit. Identity laws alone do not imply
nontriviality. A mathematical selector obtained using classical choice need
not be an executable algorithm or an available physical measurement.

No proposition here derives physical spacetime, a direction of physical time,
backwards signalling, universal self-knowledge or prevention of societal harm.
-/

namespace QIKVRT.ZeroOneObservation

open QIKVRT.UniversalOntology
open QIKVRT.V2.DecisionSufficiency

universe u v w z

/-- Only the arithmetic laws needed below; all hold in a unital ring.
No claim is made that these fields alone are a complete ring definition. -/
structure NeutralArithmetic (α : Type u) where
  zero : α
  one : α
  add : α → α → α
  mul : α → α → α
  zero_add : ∀ x, add zero x = x
  add_zero : ∀ x, add x zero = x
  one_mul : ∀ x, mul one x = x
  mul_one : ∀ x, mul x one = x
  add_left_cancel : ∀ a b c, add a b = add a c → b = c
  add_mul : ∀ a b c, mul (add a b) c = add (mul a c) (mul b c)

/-- Absorption follows from distributivity, cancellation and additive identity. -/
theorem zero_mul {α : Type u} (A : NeutralArithmetic α) (x : α) :
    A.mul A.zero x = A.zero := by
  apply A.add_left_cancel (A.mul A.zero x)
  calc
    A.add (A.mul A.zero x) (A.mul A.zero x) =
        A.mul (A.add A.zero A.zero) x := (A.add_mul A.zero A.zero x).symm
    _ = A.mul A.zero x := congrArg (fun t => A.mul t x) (A.add_zero A.zero)
    _ = A.add (A.mul A.zero x) A.zero := (A.add_zero _).symm

/-- If the two neutral elements coincide, every value is the additive identity. -/
theorem zero_eq_one_collapses {α : Type u} (A : NeutralArithmetic α)
    (equalIdentities : A.zero = A.one) (x : α) : x = A.zero := by
  calc
    x = A.mul A.one x := (A.one_mul x).symm
    _ = A.mul A.zero x := congrArg (fun t => A.mul t x) equalIdentities.symm
    _ = A.zero := zero_mul A x

/-- Identity collapse eliminates every distinction in the carrier. -/
theorem collapse_eliminates_difference {α : Type u} (A : NeutralArithmetic α)
    (equalIdentities : A.zero = A.one) (x y : α) : x = y := by
  exact (zero_eq_one_collapses A equalIdentities x).trans
    (zero_eq_one_collapses A equalIdentities y).symm

/-- Under the explicit arithmetic laws, nontriviality is equivalent to a distinction. -/
theorem zero_ne_one_iff_distinction {α : Type u} (A : NeutralArithmetic α) :
    A.zero ≠ A.one ↔ Nonempty (Distinction α) := by
  constructor
  · intro different
    exact ⟨⟨A.zero, A.one, different⟩⟩
  · rintro ⟨difference⟩ equalIdentities
    exact difference.different
      (collapse_eliminates_difference A equalIdentities difference.left difference.right)

/-- A one-element arithmetic satisfies the laws, so nontriviality is not automatic. -/
def trivialArithmetic : NeutralArithmetic Unit where
  zero := ()
  one := ()
  add := fun _ _ => ()
  mul := fun _ _ => ()
  zero_add := by intro x; cases x; rfl
  add_zero := by intro x; cases x; rfl
  one_mul := by intro x; cases x; rfl
  mul_one := by intro x; cases x; rfl
  add_left_cancel := by intro a b c _; cases b; cases c; rfl
  add_mul := by intro a b c; rfl

theorem identity_laws_allow_zero_eq_one :
    trivialArithmetic.zero = trivialArithmetic.one := by
  rfl

theorem trivial_arithmetic_has_no_distinction : ¬ Nonempty (Distinction Unit) := by
  rintro ⟨difference⟩
  exact difference.different (Subsingleton.elim _ _)

/-- Logical existence of a binary question; this does not supply a physical sensor. -/
theorem distinction_admits_binary_question {α : Type u} (difference : Distinction α) :
    ∃ question : α → Nat, question difference.left = 0 ∧ question difference.right = 1 := by
  classical
  refine ⟨fun x => if x = difference.left then 0 else 1, ?_, ?_⟩
  · simp
  · simp [Ne.symm difference.different]

/-- A detected difference entails different inputs; the converse requires more. -/
theorem detected_difference_requires_source_difference
    {State : Type u} {Observation : Type v}
    (observe : State → Observation) (x y : State)
    (detected : observe x ≠ observe y) : x ≠ y := by
  intro same
  exact detected (congrArg observe same)

/-- The existing impossibility theorem applies to any effect that is hidden by observation. -/
theorem hidden_effect_has_no_correct_decoder
    {State : Type u} {Observation : Type v} {Effect : Type w}
    (observe : State → Observation) (effect : State → Effect) (x y : State)
    (sameObservation : observe x = observe y) (differentEffect : effect x ≠ effect y) :
    ¬ ∃ decoder : Observation → Effect, ∀ state, decoder (observe state) = effect state := by
  exact impossibility_of_mixed_fiber observe effect x y sameObservation differentEffect

/-- Pair the old observation with a new witness. -/
def refine {State : Type u} {Observation : Type v} {Witness : Type w}
    (observe : State → Observation) (witness : State → Witness) :
    State → Observation × Witness := fun state => (observe state, witness state)

theorem refinement_preserves_old_information
    {State : Type u} {Observation : Type v} {Witness : Type w}
    (observe : State → Observation) (witness : State → Witness) (x y : State)
    (same : refine observe witness x = refine observe witness y) : observe x = observe y := by
  exact congrArg Prod.fst same

theorem witness_can_separate_an_old_collision
    {State : Type u} {Observation : Type v} {Witness : Type w}
    (observe : State → Observation) (witness : State → Witness) (x y : State)
    (differentWitness : witness x ≠ witness y) :
    refine observe witness x ≠ refine observe witness y := by
  intro same
  exact differentWitness (congrArg Prod.snd same)

/-- The new witness is sufficient exactly to the extent it separates relevant effects. -/
theorem sufficient_joint_observation
    {State : Type u} {Observation : Type v} {Witness : Type w} {Effect : Type z}
    (observe : State → Observation) (witness : State → Witness) (effect : State → Effect)
    (separates : ∀ x y, observe x = observe y → witness x = witness y → effect x = effect y) :
    ObservationSufficient (refine observe witness) effect := by
  intro x y same
  exact separates x y (congrArg Prod.fst same) (congrArg Prod.snd same)

/-- Exact criterion on reachable observations. Existence alone is not computability. -/
theorem recoverable_iff_observation_sufficient
    {State : Type u} {Observation : Type v} {Effect : Type w}
    (observe : State → Observation) (effect : State → Effect) :
    (∃ decoder : ObservationImage observe → Effect,
      ∀ state, decoder (observedImage observe state) = effect state) ↔
    ObservationSufficient observe effect := by
  constructor
  · rintro ⟨decoder, correct⟩ x y same
    have imagesEqual : observedImage observe x = observedImage observe y := by
      apply Subtype.ext
      exact same
    calc
      effect x = decoder (observedImage observe x) := (correct x).symm
      _ = decoder (observedImage observe y) := congrArg decoder imagesEqual
      _ = effect y := correct y
  · intro sufficient
    exact refinedObservation_enables_recovery observe effect sufficient

/-- Prediction is a question about a future effect under a specified evolution. -/
def futureEffect {State : Type u} {Effect : Type v}
    (advance : State → State) (effect : State → Effect) : State → Effect :=
  fun state => effect (advance state)

/-- Even with specified evolution, exact prediction needs sufficient present observation. -/
theorem exact_prediction_iff_observation_sufficient
    {State : Type u} {Observation : Type v} {Effect : Type w}
    (observe : State → Observation) (advance : State → State) (effect : State → Effect) :
    (∃ predictor : ObservationImage observe → Effect,
      ∀ state, predictor (observedImage observe state) = effect (advance state)) ↔
    ObservationSufficient observe (futureEffect advance effect) := by
  exact recoverable_iff_observation_sufficient observe (futureEffect advance effect)

/-- Finite counterexample: a constant observation hides an actual 0/1 distinction. -/
theorem constant_observation_cannot_recover_a_bit :
    ¬ ∃ decoder : Unit → Bool, ∀ bit : Bool, decoder () = bit := by
  exact hidden_effect_has_no_correct_decoder (fun _ : Bool => ()) id
    false true rfl (by decide)

/-- A witness that actually carries the missing bit permits constructive recovery. -/
theorem actual_bit_witness_restores_recovery :
    ∃ decoder : Unit × Bool → Bool, ∀ bit : Bool, decoder ((), bit) = bit := by
  exact ⟨Prod.snd, by intro bit; rfl⟩

/-- Duplicating the same uninformative observation does not close the gap. -/
theorem duplicate_blind_witness_does_not_restore_recovery :
    ¬ ∃ decoder : Unit × Unit → Bool, ∀ bit : Bool, decoder ((), ()) = bit := by
  exact hidden_effect_has_no_correct_decoder (fun _ : Bool => ((), ())) id
    false true rfl (by decide)

/-- Specifying deterministic dynamics alone does not repair hidden input. -/
theorem known_identity_dynamics_do_not_restore_prediction :
    ¬ ∃ predictor : Unit → Bool,
      ∀ bit : Bool, predictor () = futureEffect id id bit := by
  exact constant_observation_cannot_recover_a_bit

/-- A finite countermodel, not an empirical economic claim.
The fields are deliberately independent; any proposed link needs its own premise. -/
structure EconomicOutcome where
  profitReported : Bool
  damageOccurred : Bool

/-- A private success signal alone need not determine an external consequence. -/
theorem profit_alone_does_not_determine_damage :
    ¬ ∃ decoder : Bool → Bool,
      ∀ outcome : EconomicOutcome,
        decoder outcome.profitReported = outcome.damageOccurred := by
  exact hidden_effect_has_no_correct_decoder EconomicOutcome.profitReported
    EconomicOutcome.damageOccurred ⟨true, false⟩ ⟨true, true⟩ rfl (by decide)

/-- Accurate damage readback adds exactly the missing distinction in this example. -/
theorem damage_readback_restores_recovery :
    ∃ decoder : Bool × Bool → Bool,
      ∀ outcome : EconomicOutcome,
        decoder (outcome.profitReported, outcome.damageOccurred) = outcome.damageOccurred := by
  exact ⟨Prod.snd, by intro outcome; rfl⟩

/-- Missing observation, observed failure and observed success remain three states. -/
theorem unknown_differs_from_observed_failure :
    (none : Option Bool) ≠ some false := by decide

theorem unknown_differs_from_observed_success :
    (none : Option Bool) ≠ some true := by decide

theorem observed_failure_differs_from_observed_success :
    (some false : Option Bool) ≠ some true := by decide

end QIKVRT.ZeroOneObservation
