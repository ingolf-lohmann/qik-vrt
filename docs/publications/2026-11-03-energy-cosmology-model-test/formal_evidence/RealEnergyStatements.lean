import RealErasureBudget

/-! Explicit statement/checked bindings for the eight original real-energy claims.
These are claim bindings, not eight additional independent mathematical results. -/
namespace QIKVRT.V2.Physics.PlanckRealEnergy

def PRE_T01_Statement : Prop := ∀ i : PositivePlanckInputs, 0 < planckMass i
theorem PRE_T01_checked : PRE_T01_Statement := PRE_T01_planckMass_pos

def PRE_T02_Statement : Prop := ∀ i : PositivePlanckInputs, 0 < planckTime i
theorem PRE_T02_checked : PRE_T02_Statement := PRE_T02_planckTime_pos

def PRE_T03_Statement : Prop := ∀ i : PositivePlanckInputs, 0 < planckEnergy i
theorem PRE_T03_checked : PRE_T03_Statement := PRE_T03_planckEnergy_pos

def PRE_T04_Statement : Prop :=
  ∀ i : PositivePlanckInputs, planckTime i * planckEnergy i = i.hbar
theorem PRE_T04_checked : PRE_T04_Statement := PRE_T04_planckTime_mul_planckEnergy

def PRE_T05_Statement : Prop :=
  ∀ i : PositivePlanckInputs, planckEnergy i = i.hbar / planckTime i
theorem PRE_T05_checked : PRE_T05_Statement := PRE_T05_planckEnergy_eq_hbar_div_planckTime

def REB_T01_Statement : Prop :=
  ∀ cost information work available : ℝ, 0 < cost →
    cost * information ≤ work → work ≤ available → information ≤ available / cost
theorem REB_T01_checked : REB_T01_Statement := REB_T01_real_bit_bound

def REB_T02_Statement : Prop :=
  ∀ (i : PositivePlanckInputs) (gap : PlanckEnergyGap i),
    0 ≤ gap.deltaE / planckEnergy i ∧ gap.deltaE / planckEnergy i < 1
theorem REB_T02_checked : REB_T02_Statement := REB_T02_gap_normalized

def REB_T03_Statement : Prop :=
  ∀ (i : PositivePlanckInputs) (cost information work : ℝ), 0 < cost →
    cost * information ≤ work → work ≤ planckEnergy i →
    information ≤ planckEnergy i / cost
theorem REB_T03_checked : REB_T03_Statement := REB_T03_planck_budget

end QIKVRT.V2.Physics.PlanckRealEnergy
