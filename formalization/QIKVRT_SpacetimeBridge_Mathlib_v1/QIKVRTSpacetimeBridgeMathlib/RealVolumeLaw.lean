import Mathlib.Analysis.SpecialFunctions.Pow.Real

/-!
# Positive real conformal volume scaling

This package is intentionally separate from QIKVRT_SpacetimeBridge_v1.
For a positive real scale Ω and positive real dimension d, the scalar
volume multiplier Ω^d is injective in Ω. This file formalizes that
order-theoretic step over ℝ. It does not formalize a smooth metric,
the determinant identity, or Radon–Nikodym uniqueness.
-/

namespace QIKVRT.SpacetimeBridge.MathlibV1

/-- The scalar real-valued volume-density multiplier for scale Ω
and positive real dimension d. -/
def realVolumeDensity (omega dimension : ℝ) : ℝ :=
  omega ^ dimension

/-- Equal positive-real volume multipliers identify the positive
real scale when the dimension is positive. -/
theorem scale_eq_of_same_real_volume_density
    (dimension omega1 omega2 : ℝ)
    (hd : 0 < dimension)
    (h1 : 0 < omega1)
    (h2 : 0 < omega2)
    (hvolume :
      realVolumeDensity omega1 dimension =
      realVolumeDensity omega2 dimension) :
    omega1 = omega2 := by
  by_contra hne
  rcases lt_or_gt_of_ne hne with hlt | hgt
  · have hpow := Real.rpow_lt_rpow (le_of_lt h1) hlt hd
    exact (ne_of_lt hpow) hvolume
  · have hpow := Real.rpow_lt_rpow (le_of_lt h2) hgt hd
    exact (ne_of_gt hpow) hvolume

/-- The real-valued density multiplier is positive for a positive
scale, independently of the positive exponent. -/
theorem realVolumeDensity_pos
    (omega dimension : ℝ)
    (homega : 0 < omega) :
    0 < realVolumeDensity omega dimension := by
  exact Real.rpow_pos_of_pos homega dimension

/-- Density equality implies scale equality; this is a named
interface for subsequent local-measure formalization. -/
theorem scale_eq_of_same_local_density
    (dimension omega1 omega2 : ℝ)
    (hd : 0 < dimension)
    (h1 : 0 < omega1)
    (h2 : 0 < omega2)
    (hdensity :
      realVolumeDensity omega1 dimension =
      realVolumeDensity omega2 dimension) :
    omega1 = omega2 :=
  scale_eq_of_same_real_volume_density dimension omega1 omega2 hd h1 h2 hdensity

end QIKVRT.SpacetimeBridge.MathlibV1
