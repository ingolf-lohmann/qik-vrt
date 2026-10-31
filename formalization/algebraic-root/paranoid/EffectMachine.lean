import SerializationCascade

namespace QikVrtAlgebraicRoot

inductive EffectEvent (Payload : Type) where
  | propose (value : Payload)
  | observe (value : Payload)
  | acknowledge

structure EffectState (Payload : Type) where
  proposed : Option Payload := none
  observed : Option Payload := none
  acknowledged : Bool := false

def effectStep {Payload : Type} [DecidableEq Payload]
    (s : EffectState Payload) (event : EffectEvent Payload) :
    EffectState Payload :=
  match event with
  | .propose p => { proposed := some p }
  | .observe p =>
      if s.proposed = some p then
        { s with observed := some p, acknowledged := false }
      else s
  | .acknowledge =>
      if h : s.proposed.isSome = true ∧ s.proposed = s.observed then
        { s with acknowledged := true }
      else s

def effectSafe {Payload : Type} (s : EffectState Payload) : Prop :=
  s.acknowledged = true → ∃ p, s.proposed = some p ∧ s.observed = some p

theorem effectStep_preserves_safety {Payload : Type} [DecidableEq Payload]
    (s : EffectState Payload) (e : EffectEvent Payload)
    (safe : effectSafe s) : effectSafe (effectStep s e) := by
  cases e with
  | propose p =>
      intro h
      simp [effectStep] at h
  | observe p =>
      unfold effectStep
      split
      · intro h
        simp at h
      · exact safe
  | acknowledge =>
      unfold effectStep
      split
      · rename_i h
        intro _
        rcases h with ⟨hsome, heq⟩
        cases hp : s.proposed with
        | none => simp [hp] at hsome
        | some p =>
            refine ⟨p, hp, ?_⟩
            rw [← heq]
            exact hp
      · exact safe

def effectRunFrom {Payload : Type} [DecidableEq Payload]
    (s : EffectState Payload) : List (EffectEvent Payload) → EffectState Payload
  | [] => s
  | e :: es => effectRunFrom (effectStep s e) es

theorem effectRunFrom_safe {Payload : Type} [DecidableEq Payload]
    (events : List (EffectEvent Payload)) (s : EffectState Payload)
    (hs : effectSafe s) : effectSafe (effectRunFrom s events) := by
  induction events generalizing s with
  | nil => simpa [effectRunFrom] using hs
  | cons e es ih =>
      exact ih (effectStep s e) (effectStep_preserves_safety s e hs)

theorem effectRun_safe {Payload : Type} [DecidableEq Payload]
    (events : List (EffectEvent Payload)) :
    effectSafe (effectRunFrom ({} : EffectState Payload) events) := by
  apply effectRunFrom_safe
  intro h
  simp at h

#print axioms QikVrtAlgebraicRoot.effectStep_preserves_safety
#print axioms QikVrtAlgebraicRoot.effectRunFrom_safe
#print axioms QikVrtAlgebraicRoot.effectRun_safe

end QikVrtAlgebraicRoot
