import PlanckRealEnergyDomain

namespace QIKVRT.V2.Physics.PlanckRealEnergy

/-- The original erasure-budget inference, now instantiated over the reals.
    The thermodynamic lower bound and the available work are premises. -/
theorem REB_T01_real_bit_bound (cost information work available : ℝ)
    (cost_pos : 0 < cost)
    (landauer : cost * information ≤ work)
    (supply : work ≤ available) :
    information ≤ available / cost := by
  apply (le_div_iff₀ cost_pos).2
  calc
    information * cost = cost * information := mul_comm _ _
    _ ≤ work := landauer
    _ ≤ available := supply

/-- Sub-Planckian gap normalization preserves the closed/open interval. -/
theorem REB_T02_gap_normalized (i : PositivePlanckInputs)
    (gap : PlanckEnergyGap i) :
    0 ≤ gap.deltaE / planckEnergy i ∧
      gap.deltaE / planckEnergy i < 1 := by
  exact ⟨div_nonneg gap.nonnegative (PRE_T03_planckEnergy_pos i).le,
    (div_lt_one (PRE_T03_planckEnergy_pos i)).2 gap.belowPlanck⟩

/-- A Planck-energy work budget gives a conditional real information bound.
    This is an algebraic specialization, not a claim of an operational limit. -/
theorem REB_T03_planck_budget (i : PositivePlanckInputs)
    (cost information work : ℝ) (cost_pos : 0 < cost)
    (landauer : cost * information ≤ work)
    (supply : work ≤ planckEnergy i) :
    information ≤ planckEnergy i / cost :=
  REB_T01_real_bit_bound cost information work (planckEnergy i)
    cost_pos landauer supply

end QIKVRT.V2.Physics.PlanckRealEnergy

