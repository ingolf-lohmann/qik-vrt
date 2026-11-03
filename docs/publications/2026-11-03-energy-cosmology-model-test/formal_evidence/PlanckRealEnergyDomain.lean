import Mathlib.Data.Real.Sqrt

/-!
# Ordered-real Planck-energy domain candidate

This additive module instantiates the scalar energy layer in `ℝ`.  It assumes
strictly positive input constants and defines the Planck mass, time and energy.
It also represents an admissible energy gap by the ordered interval
`0 ≤ ΔE < E_P`.

No numerical value, SI calibration, empirical correspondence, natural-law
claim, host effect or publication effect is established by these definitions.
-/

namespace QIKVRT
namespace V2
namespace Physics
namespace PlanckRealEnergy

/-- Positive real inputs for the algebraic Planck-energy construction. -/
structure PositivePlanckInputs where
  hbar : ℝ
  G : ℝ
  c : ℝ
  hbar_pos : 0 < hbar
  G_pos : 0 < G
  c_pos : 0 < c

/-- Planck mass over the ordered real numbers. -/
noncomputable def planckMass (i : PositivePlanckInputs) : ℝ :=
  Real.sqrt (i.hbar * i.c / i.G)

/-- Planck time over the ordered real numbers. -/
noncomputable def planckTime (i : PositivePlanckInputs) : ℝ :=
  Real.sqrt (i.hbar * i.G / i.c ^ 5)

/-- Planck energy `E_P = m_P c²`. -/
noncomputable def planckEnergy (i : PositivePlanckInputs) : ℝ :=
  planckMass i * i.c ^ 2

/-- [PRE-T01] The instantiated Planck mass is strictly positive. -/
theorem PRE_T01_planckMass_pos (i : PositivePlanckInputs) :
    0 < planckMass i := by
  exact Real.sqrt_pos.2 (div_pos (mul_pos i.hbar_pos i.c_pos) i.G_pos)

/-- [PRE-T02] The instantiated Planck time is strictly positive. -/
theorem PRE_T02_planckTime_pos (i : PositivePlanckInputs) :
    0 < planckTime i := by
  exact Real.sqrt_pos.2
    (div_pos (mul_pos i.hbar_pos i.G_pos) (pow_pos i.c_pos 5))

/-- [PRE-T03] The instantiated Planck energy is strictly positive. -/
theorem PRE_T03_planckEnergy_pos (i : PositivePlanckInputs) :
    0 < planckEnergy i := by
  exact mul_pos (PRE_T01_planckMass_pos i) (pow_pos i.c_pos 2)

/-- [PRE-T04] Planck time times Planck energy equals reduced Planck action. -/
theorem PRE_T04_planckTime_mul_planckEnergy (i : PositivePlanckInputs) :
    planckTime i * planckEnergy i = i.hbar := by
  have hG : i.G ≠ 0 := ne_of_gt i.G_pos
  have hc : i.c ≠ 0 := ne_of_gt i.c_pos
  have hm_sq : planckMass i ^ 2 = i.hbar * i.c / i.G := by
    exact Real.sq_sqrt
      (div_nonneg (mul_nonneg i.hbar_pos.le i.c_pos.le) i.G_pos.le)
  have ht_sq : planckTime i ^ 2 = i.hbar * i.G / i.c ^ 5 := by
    exact Real.sq_sqrt
      (div_nonneg (mul_nonneg i.hbar_pos.le i.G_pos.le)
        (pow_nonneg i.c_pos.le 5))
  have hsq :
      (planckTime i * (planckMass i * i.c ^ 2)) ^ 2 = i.hbar ^ 2 := by
    rw [mul_pow, mul_pow, ht_sq, hm_sq]
    field_simp [hG, hc]
    <;> ring
  have hlhs_pos : 0 < planckTime i * (planckMass i * i.c ^ 2) :=
    mul_pos (PRE_T02_planckTime_pos i)
      (mul_pos (PRE_T01_planckMass_pos i) (pow_pos i.c_pos 2))
  rw [planckEnergy]
  nlinarith [hsq, i.hbar_pos]

/-- [PRE-T05] Equivalent energy form `E_P = ℏ / t_P`. -/
theorem PRE_T05_planckEnergy_eq_hbar_div_planckTime
    (i : PositivePlanckInputs) :
    planckEnergy i = i.hbar / planckTime i := by
  apply (eq_div_iff (ne_of_gt (PRE_T02_planckTime_pos i))).2
  rw [mul_comm]
  exact PRE_T04_planckTime_mul_planckEnergy i

/-- Ordered-real admissibility contract for a sub-Planckian energy gap. -/
structure PlanckEnergyGap (i : PositivePlanckInputs) where
  deltaE : ℝ
  nonnegative : 0 ≤ deltaE
  belowPlanck : deltaE < planckEnergy i

end PlanckRealEnergy
end Physics
end V2
end QIKVRT
