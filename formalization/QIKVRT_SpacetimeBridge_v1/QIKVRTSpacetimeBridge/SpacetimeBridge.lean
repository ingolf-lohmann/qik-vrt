import QIKVRTCausalGeometry.CausalGeometry

/-!
# Conditional causal + volume reconstruction interface

This module formalizes the *composition* of the standard continuum
causal-reconstruction result with an independent volume-scale
identifiability premise. It does not prove the HKM/Malament theorem
from graph data: the theorem's Lorentzian-manifold and distinguishing
hypotheses, and its continuum causal-isomorphism premise, are explicit.

The volume premise concerns equality of the full volume signature on
the relevant measurable regions, not one global scalar. The final
extensionality premise states that conformal class plus calibrated
scale identifies the metric.
-/

namespace QIKVRT.SpacetimeBridge.V1

universe u

/-- A typed statement of the hypotheses and conclusions needed to
compose causal conformal reconstruction with volume-scale recovery. -/
structure CausalVolumeReconstruction
    (Metric ConformalClass VolumeScale : Type u) where
  causallyEquivalent : Metric → Metric → Prop
  isLorentzian : Metric → Prop
  dimension : Metric → Nat
  futureDistinguishing : Metric → Prop
  pastDistinguishing : Metric → Prop
  conformalClass : Metric → ConformalClass
  volumeScale : Metric → VolumeScale
  sameVolumeSignature : Metric → Metric → Prop

  /-- HKM/Malament-type input. This is a named external mathematical
  obligation, not a theorem derived from a finite graph. -/
  causalDeterminesConformal :
    ∀ {g h}, isLorentzian g → isLorentzian h →
      dimension g > 2 → dimension h > 2 →
      futureDistinguishing g → pastDistinguishing g →
      futureDistinguishing h → pastDistinguishing h →
      causallyEquivalent g h →
      conformalClass g = conformalClass h

  /-- Volume calibration removes the conformal-scale ambiguity.
  Equality must cover the full region-volume signature. -/
  volumeDeterminesScale :
    ∀ {g h}, conformalClass g = conformalClass h →
      sameVolumeSignature g h →
      volumeScale g = volumeScale h

  /-- In a fixed model class, conformal class and calibrated scale
  jointly identify the metric. -/
  metricExtensional :
    ∀ {g h}, conformalClass g = conformalClass h →
      volumeScale g = volumeScale h → g = h

/-- Conditional reconstruction theorem: once the continuum causal
isomorphism theorem, volume calibration, and metric extensionality
are supplied with their hypotheses, the metric is unique. -/
theorem causal_volume_reconstruct
    {Metric ConformalClass VolumeScale : Type u}
    (R : CausalVolumeReconstruction Metric ConformalClass VolumeScale)
    {g h : Metric}
    (hgL : R.isLorentzian g) (hhL : R.isLorentzian h)
    (hgd : R.dimension g > 2) (hhd : R.dimension h > 2)
    (hgf : R.futureDistinguishing g) (hgp : R.pastDistinguishing g)
    (hhf : R.futureDistinguishing h) (hhp : R.pastDistinguishing h)
    (hcausal : R.causallyEquivalent g h)
    (hvolume : R.sameVolumeSignature g h) :
    g = h := by
  have hconformal : R.conformalClass g = R.conformalClass h :=
    R.causalDeterminesConformal hgL hhL hgd hhd hgf hgp hhf hhp hcausal
  have hscale : R.volumeScale g = R.volumeScale h :=
    R.volumeDeterminesScale hconformal hvolume
  exact R.metricExtensional hconformal hscale

/-- A falsifiable empirical bridge: predictions, observations and a
pre-registered discrepancy threshold. The strict inequality is the
rejection rule; it is deliberately separate from mathematical
reconstruction. -/
structure EmpiricalTest (Model Observation : Type u) where
  predict : Model → Observation
  discrepancy : Observation → Observation → Nat
  tolerance : Nat

def Rejects {Model Observation : Type u}
    (T : EmpiricalTest Model Observation)
    (m : Model) (observed : Observation) : Prop :=
  T.tolerance < T.discrepancy (T.predict m) observed

theorem rejection_exceeds_tolerance
    {Model Observation : Type u}
    (T : EmpiricalTest Model Observation)
    (m : Model) (observed : Observation)
    (h : Rejects T m observed) :
    T.tolerance < T.discrepancy (T.predict m) observed := h

end QIKVRT.SpacetimeBridge.V1
