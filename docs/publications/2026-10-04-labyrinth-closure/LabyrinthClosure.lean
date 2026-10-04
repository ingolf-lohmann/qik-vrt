/- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
   Copyright 2026 Ingolf Lohmann.
   Model closure lemmas; not a proof of the Python implementation or live mesh. -/
import Std

namespace QIKVRT.Labyrinth

variable {V : Type} (edge : V → V → Prop) (side : V → Bool)

def Portal (u v : V) : Prop := edge u v ∧ side u ≠ side v

theorem reverse_is_same_portal
    (symmetric : ∀ u v, edge u v → edge v u) (u v : V) :
    Portal edge side u v ↔ Portal edge side v u := by
  constructor
  · intro h
    exact ⟨symmetric u v h.1, Ne.symm h.2⟩
  · intro h
    exact ⟨symmetric v u h.1, Ne.symm h.2⟩

variable {I : Type}

def Sound (known actual : I → Prop) : Prop := ∀ x, known x → actual x

def Grow (known : I → Prop) (found : I) : I → Prop :=
  fun x => known x ∨ x = found

theorem grow_preserves_soundness (known actual : I → Prop) (found : I)
    (sound : Sound known actual) (valid_found : actual found) :
    Sound (Grow known found) actual := by
  intro x hx
  cases hx with
  | inl old => exact sound x old
  | inr same =>
      cases same
      exact valid_found

theorem grow_is_monotone (known : I → Prop) (found x : I) :
    known x → Grow known found x := by
  intro h
  exact Or.inl h

theorem two_witnesses_are_sound (known actual : I → Prop)
    (sound : Sound known actual) (x y : I)
    (hx : known x) (hy : known y) (distinct : x ≠ y) :
    actual x ∧ actual y ∧ x ≠ y := by
  exact ⟨sound x hx, sound y hy, distinct⟩

inductive Reachable (edge : V → V → Prop) (s : V) : V → Prop where
  | root : Reachable edge s s
  | step {u v : V} : Reachable edge s u → edge u v → Reachable edge s v

theorem closed_set_covers_reachable (s : V) (processed : V → Prop)
    (root_processed : processed s)
    (closed : ∀ u v, processed u → edge u v → processed v) :
    ∀ v, Reachable edge s v → processed v := by
  intro v reached
  induction reached with
  | root => exact root_processed
  | step _ relation induction_hypothesis =>
      exact closed _ _ induction_hypothesis relation

theorem connected_closed_set_covers_all (s : V) (processed : V → Prop)
    (root_processed : processed s)
    (closed : ∀ u v, processed u → edge u v → processed v)
    (connected : ∀ v, Reachable edge s v) :
    ∀ v, processed v := by
  intro v
  exact closed_set_covers_reachable edge s processed root_processed closed v (connected v)

theorem no_infinite_strict_rank_descent (rank : Nat → Nat)
    (decreases : ∀ k, rank (k + 1) < rank k) : False := by
  have bound : ∀ k, rank k + k ≤ rank 0 := by
    intro k
    induction k with
    | zero => simp
    | succ k previous =>
        have step := decreases k
        omega
  have impossible := bound (rank 0 + 1)
  omega

def Complete (known actual : I → Prop) : Prop :=
  ∀ x, known x ↔ actual x

theorem complete_empty_is_zero (known actual : I → Prop)
    (complete : Complete known actual) (empty : ∀ x, ¬ known x) :
    ∀ x, ¬ actual x := by
  intro x exists_actual
  exact empty x ((complete x).mpr exists_actual)

theorem complete_singleton_is_unique (known actual : I → Prop) (only : I)
    (complete : Complete known actual)
    (singleton : ∀ x, known x ↔ x = only) :
    ∀ x, actual x ↔ x = only := by
  intro x
  exact (complete x).symm.trans (singleton x)

theorem partial_empty_does_not_imply_zero :
    ∃ known actual : Bool → Prop,
      Sound known actual ∧ (∀ x, ¬ known x) ∧ (∃ x, actual x) := by
  refine ⟨(fun _ => False), (fun x => x = true), ?_, ?_, ?_⟩
  · intro x impossible
    exact False.elim impossible
  · intro x impossible
    exact impossible
  · exact ⟨true, rfl⟩

end QIKVRT.Labyrinth

#print axioms QIKVRT.Labyrinth.reverse_is_same_portal
#print axioms QIKVRT.Labyrinth.grow_preserves_soundness
#print axioms QIKVRT.Labyrinth.grow_is_monotone
#print axioms QIKVRT.Labyrinth.two_witnesses_are_sound
#print axioms QIKVRT.Labyrinth.closed_set_covers_reachable
#print axioms QIKVRT.Labyrinth.connected_closed_set_covers_all
#print axioms QIKVRT.Labyrinth.no_infinite_strict_rank_descent
#print axioms QIKVRT.Labyrinth.complete_empty_is_zero
#print axioms QIKVRT.Labyrinth.complete_singleton_is_unique
#print axioms QIKVRT.Labyrinth.partial_empty_does_not_imply_zero
