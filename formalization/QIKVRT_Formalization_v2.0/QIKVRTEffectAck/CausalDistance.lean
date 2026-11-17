-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann.

import Std

/-!
# Positive weighted, evidence-selected path distance

`Graph.edge` is the selected relation, not a discovery oracle. Its external
source/evidence binding is a separate obligation. `none` denotes infinity in
THIS graph only. Reversing a relation is retrospective traversal, not a claim
that a physical effect travels into the past. No symmetry of the original
directed distance is assumed. All costs are strictly positive natural numbers.
-/

namespace QIKVRT.CausalDistance.V1

universe u

structure Graph (V : Type u) where
  edge : V → V → Nat → Prop
  positive : ∀ {a b n}, edge a b n → 0 < n

inductive Path {V : Type u} (g : Graph V) : V → V → Nat → Prop where
  | refl (a) : Path g a a 0
  | snoc {a b c n w} : Path g a b n → g.edge b c w → Path g a c (n + w)

theorem path_append {V : Type u} {g : Graph V} {a b c n m}
    (p : Path g a b n) (q : Path g b c m) : Path g a c (n + m) := by
  induction q with
  | refl => simpa using p
  | snoc q e ih => simpa [Nat.add_assoc] using Path.snoc ih e

theorem zero_path_endpoints {V : Type u} {g : Graph V} {a b n}
    (p : Path g a b n) (h : n = 0) : a = b := by
  cases p with
  | refl => rfl
  | snoc p e => have := g.positive e; omega

theorem exists_least_cost (P : Nat → Prop) (h : ∃ n, P n) :
    ∃ n, P n ∧ ∀ m, P m → n ≤ m := by
  classical
  obtain ⟨n, hn⟩ := h
  induction n using Nat.strongRecOn with
  | ind n ih =>
    by_cases smaller : ∃ m, m < n ∧ P m
    · obtain ⟨m, hmn, hm⟩ := smaller
      exact ih m hmn hm
    · exact ⟨n, hn, by
        intro m hm
        by_cases h : n ≤ m
        · exact h
        · exact False.elim (smaller ⟨m, by omega, hm⟩)⟩

noncomputable def minimum (P : Nat → Prop) (h : ∃ n, P n) : Nat :=
  Classical.choose (exists_least_cost P h)

theorem minimum_spec (P : Nat → Prop) (h : ∃ n, P n) :
    P (minimum P h) ∧ ∀ m, P m → minimum P h ≤ m :=
  Classical.choose_spec (exists_least_cost P h)

/-- `none` is infinite/unreachable within the selected relation. -/
noncomputable def distance {V : Type u} (g : Graph V) (a b : V) : Option Nat := by
  classical
  exact if h : ∃ n, Path g a b n then some (minimum (Path g a b) h) else none

theorem distance_some_iff {V : Type u} (g : Graph V) (a b : V) (n : Nat) :
    distance g a b = some n ↔ Path g a b n ∧ ∀ m, Path g a b m → n ≤ m := by
  classical
  unfold distance
  split
  next h =>
    have spec := minimum_spec (Path g a b) h
    constructor
    · intro he; cases Option.some.inj he; exact spec
    · intro hn
      have eq : minimum (Path g a b) h = n := Nat.le_antisymm (spec.2 n hn.1) (hn.2 _ spec.1)
      exact congrArg some eq
  next h =>
    constructor
    · intro he; contradiction
    · intro hn; exact False.elim (h ⟨n, hn.1⟩)

theorem distance_none_iff {V : Type u} (g : Graph V) (a b : V) :
    distance g a b = none ↔ ¬ ∃ n, Path g a b n := by
  classical
  simp only [distance]
  split <;> simp_all

theorem distance_zero_iff {V : Type u} (g : Graph V) (a b : V) :
    distance g a b = some 0 ↔ a = b := by
  constructor
  · intro h; exact zero_path_endpoints ((distance_some_iff g a b 0).mp h).1 rfl
  · intro h; subst b; exact (distance_some_iff g a a 0).mpr ⟨Path.refl a, by intro m _; omega⟩

def extendedLE : Option Nat → Option Nat → Prop
  | _, none => True
  | some a, some b => a ≤ b
  | none, some _ => False

def extendedAdd : Option Nat → Option Nat → Option Nat
  | some a, some b => some (a + b)
  | _, _ => none

theorem distance_le_path {V : Type u} {g : Graph V} {a b n}
    (p : Path g a b n) : extendedLE (distance g a b) (some n) := by
  classical
  have h : ∃ n, Path g a b n := ⟨n, p⟩
  simp only [distance, dif_pos h, extendedLE]
  exact (minimum_spec (Path g a b) h).2 n p

theorem triangle {V : Type u} (g : Graph V) (a b c : V) :
    extendedLE (distance g a c) (extendedAdd (distance g a b) (distance g b c)) := by
  cases hab : distance g a b with
  | none => simp [extendedAdd, extendedLE]
  | some n =>
    cases hbc : distance g b c with
    | none => simp [extendedAdd, extendedLE]
    | some m =>
      exact distance_le_path (path_append
        ((distance_some_iff g a b n).mp hab).1
        ((distance_some_iff g b c m).mp hbc).1)

def reverse {V : Type u} (g : Graph V) : Graph V where
  edge a b n := g.edge b a n
  positive h := g.positive h

theorem reverse_path {V : Type u} {g : Graph V} {a b n}
    (p : Path g a b n) : Path (reverse g) b a n := by
  induction p with
  | refl => exact Path.refl _
  | snoc p e ih =>
    have one : Path (reverse g) _ _ _ := Path.snoc (Path.refl _) e
    simpa [Nat.add_comm] using path_append one ih

theorem reverse_path_iff {V : Type u} (g : Graph V) (a b : V) (n : Nat) :
    Path (reverse g) a b n ↔ Path g b a n := by
  constructor
  · intro p; exact reverse_path p
  · exact reverse_path

theorem distance_ext {V : Type u} {g h : Graph V} (a b c d : V)
    (eqPaths : ∀ n, Path g a b n ↔ Path h c d n) : distance g a b = distance h c d := by
  cases hg : distance g a b with
  | none =>
    have noG := (distance_none_iff g a b).mp hg
    have noH : ¬ ∃ n, Path h c d n := by
      intro ⟨n, hn⟩; exact noG ⟨n, (eqPaths n).mpr hn⟩
    exact ((distance_none_iff h c d).mpr noH).symm
  | some n =>
    have spec := (distance_some_iff g a b n).mp hg
    exact ((distance_some_iff h c d n).mpr
      ⟨(eqPaths n).mp spec.1, by intro m hm; exact spec.2 m ((eqPaths m).mpr hm)⟩).symm

theorem reverse_distance {V : Type u} (g : Graph V) (a b : V) :
    distance (reverse g) a b = distance g b a :=
  distance_ext a b b a (reverse_path_iff g a b)

def undirected {V : Type u} (g : Graph V) : Graph V where
  edge a b n := g.edge a b n ∨ g.edge b a n
  positive h := h.elim g.positive g.positive

theorem undirected_path_symm {V : Type u} {g : Graph V} {a b n}
    (p : Path (undirected g) a b n) : Path (undirected g) b a n := by
  induction p with
  | refl => exact Path.refl _
  | snoc p e ih =>
    have one : Path (undirected g) _ _ _ := Path.snoc (Path.refl _) e.symm
    simpa [Nat.add_comm] using path_append one ih

theorem undirected_distance_symmetric {V : Type u} (g : Graph V) (a b : V) :
    distance (undirected g) a b = distance (undirected g) b a :=
  distance_ext a b b a (by intro n; exact ⟨undirected_path_symm, undirected_path_symm⟩)

theorem selected_edges_only {V : Type u} {g : Graph V} {a b n}
    (h : distance g a b = some n) : Path g a b n :=
  ((distance_some_iff g a b n).mp h).1

theorem path_inclusion {V : Type u} {g h : Graph V}
    (included : ∀ a b n, g.edge a b n → h.edge a b n) {a b n}
    (p : Path g a b n) : Path h a b n := by
  induction p with
  | refl => exact Path.refl _
  | snoc p e ih => exact Path.snoc ih (included _ _ _ e)

theorem edge_addition_cannot_increase_distance {V : Type u} {g h : Graph V}
    (included : ∀ a b n, g.edge a b n → h.edge a b n) (a b : V) :
    extendedLE (distance h a b) (distance g a b) := by
  cases hg : distance g a b with
  | none => simp [extendedLE]
  | some n => exact distance_le_path (path_inclusion included
      ((distance_some_iff g a b n).mp hg).1)

/-- A component is restricted by a PRESENT path, never by an invented edge. -/
theorem weak_component_distance_finite {V : Type u} (g : Graph V) (a b : V)
    (connected : ∃ n, Path (undirected g) a b n) :
    ∃ n, distance (undirected g) a b = some n := by
  cases hd : distance (undirected g) a b with
  | none => exact False.elim ((distance_none_iff _ _ _).mp hd connected)
  | some n => exact ⟨n, rfl⟩

/-- A producer can export a path and a lower-bound proof as a checked certificate.
This is a refinement INTERFACE, not a proof of a Python shortest-path program. -/
structure DistanceCertificate {V : Type u} (g : Graph V) (a b : V) where
  cost : Nat
  witness : Path g a b cost
  lowerBound : ∀ n, Path g a b n → cost ≤ n

theorem certificate_exact {V : Type u} {g : Graph V} {a b : V}
    (certificate : DistanceCertificate g a b) :
    distance g a b = some certificate.cost :=
  (distance_some_iff _ _ _ _).mpr ⟨certificate.witness, certificate.lowerBound⟩

end QIKVRT.CausalDistance.V1
