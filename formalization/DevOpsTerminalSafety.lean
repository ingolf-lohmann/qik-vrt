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


/- Release gating is a pure model. Executable release packaging must be
   checked independently against this specification in native CI. -/
structure ClientReleaseEvidence where
  artifactDigestVerified : Bool
  exactHeadCiPassed : Bool
  governanceApproved : Bool
  originAdmitted : Bool
  immutableAssetAvailable : Bool
  deriving DecidableEq, Repr

def releasePermitted (e : ClientReleaseEvidence) : Prop :=
  e.artifactDigestVerified = true ∧
  e.exactHeadCiPassed = true ∧
  e.governanceApproved = true ∧
  e.originAdmitted = true ∧
  e.immutableAssetAvailable = true

theorem release_requires_digest (e : ClientReleaseEvidence)
    (h : releasePermitted e) : e.artifactDigestVerified = true := h.1

theorem release_requires_exact_ci (e : ClientReleaseEvidence)
    (h : releasePermitted e) : e.exactHeadCiPassed = true := h.2.1

theorem release_requires_governance (e : ClientReleaseEvidence)
    (h : releasePermitted e) : e.governanceApproved = true := h.2.2.1

theorem release_requires_origin (e : ClientReleaseEvidence)
    (h : releasePermitted e) : e.originAdmitted = true := h.2.2.2.1

theorem release_requires_immutable_asset (e : ClientReleaseEvidence)
    (h : releasePermitted e) : e.immutableAssetAvailable = true := h.2.2.2.2

theorem failed_digest_blocks_release (e : ClientReleaseEvidence)
    (h : e.artifactDigestVerified = false) : ¬ releasePermitted e := by
  intro hp
  have hd := release_requires_digest e hp
  rw [h] at hd
  cases hd

theorem unverified_ci_blocks_release (e : ClientReleaseEvidence)
    (h : e.exactHeadCiPassed = false) : ¬ releasePermitted e := by
  intro hp
  have hc := release_requires_exact_ci e hp
  rw [h] at hc
  cases hc

end QIKVRT.DevOps
