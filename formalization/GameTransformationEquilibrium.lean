/- Copyright 2026 Ingolf Lohmann.
   SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
   Abstract game-transform model. No physical retrocausality claim. -/
namespace QIKVRT.GameTransformation

structure TwoActionGame where
  left : Nat
  right : Nat

inductive Action where
  | left | right
  deriving DecidableEq, Repr

def utility (g : TwoActionGame) : Action → Nat
  | .left => g.left
  | .right => g.right

def equilibrium (g : TwoActionGame) (a : Action) : Prop :=
  ∀ b : Action, utility g b ≤ utility g a

def initial : TwoActionGame := ⟨1, 0⟩
def transformed : TwoActionGame := ⟨1, 2⟩

theorem initial_left_equilibrium : equilibrium initial .left := by
  intro b
  cases b <;> decide

theorem transformed_left_not_equilibrium :
    ¬ equilibrium transformed .left := by
  intro h
  have hright := h .right
  decide at hright

theorem transformed_right_equilibrium : equilibrium transformed .right := by
  intro b
  cases b <;> decide

theorem admissible_transform_exits_initial_equilibrium :
    equilibrium initial .left ∧
    ¬ equilibrium transformed .left ∧
    equilibrium transformed .right :=
  ⟨initial_left_equilibrium, transformed_left_not_equilibrium,
   transformed_right_equilibrium⟩

-- Double-negative guards: invalid equilibrium claims cannot be admitted.
theorem reject_false_initial_right :
    ¬ equilibrium initial .right := by
  intro h
  have hleft := h .left
  decide at hleft

theorem reject_false_transformed_left :
    ¬ equilibrium transformed .left :=
  transformed_left_not_equilibrium

-- Boundary consistency is explicit: changing the model does not assert
-- that a later physical event caused an earlier physical event.
structure BoundaryClaim where
  modelConsistent : Bool
  evidencePresent : Bool

def admitted (c : BoundaryClaim) : Prop :=
  c.modelConsistent = true ∧ c.evidencePresent = true

theorem reject_inconsistent_boundary (e : Bool) :
    ¬ admitted ⟨false, e⟩ := by
  intro h
  cases h.1

theorem reject_unproven_effect (c : Bool) :
    ¬ admitted ⟨c, false⟩ := by
  intro h
  cases h.2

end QIKVRT.GameTransformation
