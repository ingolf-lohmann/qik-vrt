import QIKVRTSpacetimeBridge.SpacetimeBridge

/-!
# Exact discrete volume-scaling lemma

For a d-dimensional conformal rescaling g' = Ω² g with Ω > 0,
the continuum volume density scales by Ω^d. The determinant identity
is recorded in the scientific dossier. This module proves the
injectivity step in an exact natural-number-valued scale model.

This is intentionally NOT a formalization over positive real-valued
functions or smooth Lorentzian metrics. The natural-valued model is
an exact arithmetic proxy; the continuum determinant and
measure-theoretic steps remain analytic obligations.
-/

namespace QIKVRT.SpacetimeBridge.V1.VolumeLaw

/-- The d-dimensional volume multiplier associated with scale Ω. -/
def conformalVolumeFactor (omega dimension : Nat) : Nat :=
  omega ^ dimension

/-- Multiplicativity of the volume multiplier under composition
of positive integer-valued scale changes. -/
theorem conformalVolumeFactor_mul
    (omega1 omega2 dimension : Nat) :
    conformalVolumeFactor (omega1 * omega2) dimension =
      conformalVolumeFactor omega1 dimension *
      conformalVolumeFactor omega2 dimension := by
  simp [conformalVolumeFactor, Nat.mul_pow]

/-- In positive dimension, the exact integer volume multiplier
identifies its positive integer scale uniquely. -/
theorem scale_eq_of_same_volume_factor
    (dimension omega1 omega2 : Nat)
    (hd : dimension ≠ 0)
    (_h1 : 0 < omega1) (_h2 : 0 < omega2)
    (hvolume :
      conformalVolumeFactor omega1 dimension =
      conformalVolumeFactor omega2 dimension) :
    omega1 = omega2 := by
  exact (Nat.pow_left_inj hd).mp (by simpa [conformalVolumeFactor] using hvolume)

/-- Unit volume multiplier forces unit positive integer scale. -/
theorem scale_eq_one_of_unit_volume_factor
    (dimension omega : Nat)
    (hd : dimension ≠ 0)
    (_hω : 0 < omega)
    (hvolume : conformalVolumeFactor omega dimension = 1) :
    omega = 1 := by
  have hpow : omega ^ dimension = 1 ^ dimension := by
    simpa [conformalVolumeFactor] using hvolume
  exact (Nat.pow_left_inj hd).mp hpow

/-- A calibrated integer count proportional to the volume multiplier. -/
def calibratedCount (baseDensity omega dimension : Nat) : Nat :=
  baseDensity * conformalVolumeFactor omega dimension

theorem scale_eq_of_same_calibrated_count
    (baseDensity dimension omega1 omega2 : Nat)
    (hbase : 0 < baseDensity)
    (hd : dimension ≠ 0)
    (h1 : 0 < omega1) (h2 : 0 < omega2)
    (hcount :
      calibratedCount baseDensity omega1 dimension =
      calibratedCount baseDensity omega2 dimension) :
    omega1 = omega2 := by
  apply scale_eq_of_same_volume_factor dimension omega1 omega2 hd h1 h2
  exact Nat.mul_left_cancel hbase hcount

end QIKVRT.SpacetimeBridge.V1.VolumeLaw
