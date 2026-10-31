/- SPDX-License-Identifier: CC-BY-NC-ND-4.0
   Copyright (c) 2026 Ingolf Lohmann.
   Candidate source: kernel verification is required, not claimed.
-/
namespace QikVrtAlgebraicRoot
structure TwoIdentities (α : Type) where
  add : α → α → α
  mul : α → α → α
  zero : α
  one : α
  add_zero : ∀ a, add a zero = a
  zero_add : ∀ a, add zero a = a
  mul_one : ∀ a, mul a one = a
  one_mul : ∀ a, mul one a = a

def boolCountermodel : TwoIdentities Bool where
  add := Bool.and
  mul := Bool.xor
  zero := true
  one := false
  add_zero := by intro a; cases a <;> rfl
  zero_add := by intro a; cases a <;> rfl
  mul_one := by intro a; cases a <;> rfl
  one_mul := by intro a; cases a <;> rfl

theorem zero_ne_one : boolCountermodel.zero ≠ boolCountermodel.one := by decide

theorem distributivity_not_forced :
    boolCountermodel.mul true (boolCountermodel.add false true) ≠
      boolCountermodel.add
        (boolCountermodel.mul true false)
        (boolCountermodel.mul true true) := by decide

#print axioms QikVrtAlgebraicRoot.zero_ne_one
#print axioms QikVrtAlgebraicRoot.distributivity_not_forced
end QikVrtAlgebraicRoot
