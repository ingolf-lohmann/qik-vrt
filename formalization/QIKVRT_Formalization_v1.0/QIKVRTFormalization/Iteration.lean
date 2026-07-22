import QIKVRTFormalization.Foundations

/-!
# Iteration, escape certificates, and the autonomous quadratic process

The analytic escape-radius lemma for `ℂ` belongs to the standard library of
complex dynamics.  Here the process-independent logical content is checked:
finite escape certificates are monotone, their union is exactly eventual
escape, and a deterministic forward recursion has no later-gate input.
-/

namespace QIKVRT

universe u v

def iterate (step : α → α) (x₀ : α) : Nat → α
  | 0 => x₀
  | n + 1 => step (iterate step x₀ n)

@[simp] theorem iterate_zero (step : α → α) (x₀ : α) :
    iterate step x₀ 0 = x₀ := rfl

@[simp] theorem iterate_succ (step : α → α) (x₀ : α) (n : Nat) :
    iterate step x₀ (n + 1) = step (iterate step x₀ n) := rfl

def EscapesBy (escaped : α → Prop) (orbit : Nat → α) (N : Nat) : Prop :=
  ∃ k, k ≤ N ∧ escaped (orbit k)

def EventuallyEscapes (escaped : α → Prop) (orbit : Nat → α) : Prop :=
  ∃ k, escaped (orbit k)

theorem escapesBy_mono {escaped : α → Prop} {orbit : Nat → α} {N M : Nat}
    (hNM : N ≤ M) (h : EscapesBy escaped orbit N) :
    EscapesBy escaped orbit M := by
  rcases h with ⟨k, hkN, hk⟩
  exact ⟨k, Nat.le_trans hkN hNM, hk⟩

theorem eventuallyEscapes_iff_exists_escapeBy (escaped : α → Prop)
    (orbit : Nat → α) :
    EventuallyEscapes escaped orbit ↔ ∃ N, EscapesBy escaped orbit N := by
  constructor
  · rintro ⟨k, hk⟩
    exact ⟨k, k, Nat.le_refl k, hk⟩
  · rintro ⟨N, k, _, hk⟩
    exact ⟨k, hk⟩

theorem escape_exhaustion (escaped : α → Prop) (orbit : Nat → α) :
    (fun _ : Unit => EventuallyEscapes escaped orbit) =ₚ
    (fun _ : Unit => ∃ N, EscapesBy escaped orbit N) := by
  intro _
  exact eventuallyEscapes_iff_exists_escapeBy escaped orbit

section Quadratic

variable [OfNat α 0] [Mul α] [Add α]

def quadraticStep (c z : α) : α := z * z + c

def mandelbrotOrbit (c : α) : Nat → α := iterate (quadraticStep c) 0

@[simp] theorem mandelbrotOrbit_zero (c : α) : mandelbrotOrbit c 0 = 0 := rfl

@[simp] theorem mandelbrotOrbit_succ (c : α) (n : Nat) :
    mandelbrotOrbit c (n + 1) =
      mandelbrotOrbit c n * mandelbrotOrbit c n + c := rfl

structure TaggedState (P : Type u) (S : Type v) where
  parameter : P
  state : S

def taggedQuadraticStep [Mul α] [Add α]
    (x : TaggedState α α) : TaggedState α α :=
  ⟨x.parameter, x.state * x.state + x.parameter⟩

theorem tagged_parameter_preserved [Mul α] [Add α]
    (x : TaggedState α α) :
    (taggedQuadraticStep x).parameter = x.parameter := rfl

end Quadratic

structure EscapeSpecification (P : Type u) (S : Type v) where
  orbit : P → Nat → S
  outside : P → Prop
  escaped : S → Prop
  soundComplete : ∀ c, outside c ↔ EventuallyEscapes escaped (orbit c)

theorem escapeSpecification_exhaustion
    (spec : EscapeSpecification α β) (c : α) :
    spec.outside c ↔ ∃ N, EscapesBy spec.escaped (spec.orbit c) N := by
  rw [spec.soundComplete c]
  exact eventuallyEscapes_iff_exists_escapeBy spec.escaped (spec.orbit c)

end QIKVRT
