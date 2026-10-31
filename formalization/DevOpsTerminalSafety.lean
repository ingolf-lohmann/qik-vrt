/- QIK-VRT DevOps terminal: pure safety model.
   This file proves properties of the abstract transition system only.
   It does not assert that the deployed HTTP bridge implements this model. -/
namespace QIKVRT.DevOps

inductive Stage where
  | ingress | admission | processing | handoff | ci | review | merge | effect
  deriving DecidableEq, Repr

inductive Status where
  | unknown | blocked | running | success
  deriving DecidableEq, Repr

structure Evidence where
  terminalReadback : Bool
  transputerReadback : Bool
  nativeCiPassed : Bool
  governancePassed : Bool
  mainReadback : Bool
  productiveEffectReadback : Bool
  deriving DecidableEq, Repr

def admitted (e : Evidence) : Prop :=
  e.terminalReadback = true ∧ e.transputerReadback = true

def mergePermitted (e : Evidence) : Prop :=
  e.nativeCiPassed = true ∧ e.governancePassed = true

def effectPermitted (e : Evidence) : Prop :=
  admitted e ∧ mergePermitted e ∧
  e.mainReadback = true ∧ e.productiveEffectReadback = true

theorem effect_requires_terminal (e : Evidence)
    (h : effectPermitted e) : e.terminalReadback = true := h.1.1

theorem effect_requires_transputer (e : Evidence)
    (h : effectPermitted e) : e.transputerReadback = true := h.1.2

theorem effect_requires_ci (e : Evidence)
    (h : effectPermitted e) : e.nativeCiPassed = true := h.2.1.1

theorem effect_requires_governance (e : Evidence)
    (h : effectPermitted e) : e.governancePassed = true := h.2.1.2

theorem effect_requires_main_readback (e : Evidence)
    (h : effectPermitted e) : e.mainReadback = true := h.2.2.1

theorem effect_requires_productive_readback (e : Evidence)
    (h : effectPermitted e) : e.productiveEffectReadback = true := h.2.2.2

theorem ci_alone_cannot_establish_effect
    (e : Evidence) (h : e.productiveEffectReadback = false) :
    ¬ effectPermitted e := by
  intro he
  have hp := effect_requires_productive_readback e he
  rw [h] at hp
  cases hp

end QIKVRT.DevOps
