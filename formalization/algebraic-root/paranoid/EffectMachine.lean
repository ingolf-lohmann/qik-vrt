import SerializationCascade

namespace QikVrtAlgebraicRoot

/-- Acknowledgement is a state transition, never an unconstrained Boolean input. -/
inductive EffectEvent (Payload : Type) where
  | propose (value : Payload)
  | observe (value : Payload)
  | acknowledge

structure EffectState (Payload : Type) where
  proposed : Option Payload := none
  observed : Option Payload := none
  acknowledged : Bool := false

/-- An observation is retained only when it matches the current proposal.
    A new proposal invalidates previous observations and acknowledgements. -/
def effectStep {Payload : Type} [DecidableEq Payload]
    (s : EffectState Payload) (event : EffectEvent Payload) :
    EffectState Payload :=
  match event with
  | .propose p => { proposed := some p }
  | .observe p =>
      if s.proposed = some p then
        { s with observed := some p, acknowledged := false }
      else
        s
  | .acknowledge =>
      if s.proposed.isSome && s.proposed == s.observed then
        { s with acknowledged := true }
      else
        s

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
      · rename_i hguard
        intro _
        simp only [Bool.and_eq_true, Bool.isSome_eq_true, beq_iff_eq] at hguard
        obtain ⟨hSome, hEq⟩ := hguard
        cases hp : s.proposed with
        | none => simp [hp] at hSome
        | some p =>
            refine ⟨p, hp, ?_⟩
            exact hEq ▸ hp
      · exact safe

def effectRun {Payload : Type} [DecidableEq Payload]
    (events : List (EffectEvent Payload)) : EffectState Payload :=
  events.foldl effectStep {}

theorem effectRun_safe {Payload : Type} [DecidableEq Payload]
    (events : List (EffectEvent Payload)) :
    effectSafe (effectRun events) := by
  unfold effectRun
  apply List.foldlRecOn events
  · intro h
    exact h
  · exact effectStep_preserves_safety
  · intro h
    simp [effectSafe] at h

end QikVrtAlgebraicRoot
