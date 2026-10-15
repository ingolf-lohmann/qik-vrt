import QIKVRTFormalization.Physics.EmpiricalBridge
import QIKVRTFormalization.Retrocausality.ObserverRelative

/-!
# Scoped measurement and prediction transfer

Research question and requested closure: Ingolf Lohmann, 2026-10-15.
Successor formalization: OpenAI Codex, on his instruction.

This extends the existing empirical bridge and reuses the existing `run`.
Referenced states are mathematical representations. Instantiating a map does
not certify its correspondence to an apparatus. One-step correspondence,
initial/input binding, calibration and domain admission are explicit premises.
Integer quantities denote declared common resolution units, not arbitrary real
proper times. The squared-interval examples concern straight inertial timelike
segments in flat 1+1 spacetime with c=1, not curved or accelerated worldlines.
-/

namespace QIKVRT.V2.Physics.MeasurementTransfer

/-- An absolute-error enclosure in a declared common integer unit. -/
def Within (actual center budget : Int) : Prop :=
  0 ≤ budget ∧ center - budget ≤ actual ∧ actual ≤ center + budget

theorem exact_readout_is_within (value : Int) : Within value value 0 := by
  unfold Within
  omega

/-- Independent error budgets compose; neither input premise is manufactured. -/
theorem error_budgets_compose {actual middle forecast e₁ e₂ : Int}
    (h₁ : Within actual middle e₁) (h₂ : Within middle forecast e₂) :
    Within actual forecast (e₁ + e₂) := by
  unfold Within at *
  omega

/-- Reuse the existing interval-order theorem with explicit measurement errors. -/
theorem separated_readback_enclosures_establish_order
    {actualEarly actualLate estimateEarly estimateLate e₁ e₂ : Int}
    (h₁ : Within actualEarly estimateEarly e₁)
    (h₂ : Within actualLate estimateLate e₂)
    (separated : estimateEarly + e₁ < estimateLate - e₂) :
    actualEarly < actualLate :=
  ObserverRelative.separated_time_intervals_establish_actual_order
    actualEarly actualLate (estimateEarly + e₁) (estimateLate - e₂)
    h₁.2.2 h₂.2.1 separated

/-- Local correspondence, restricted to a declared invariant domain. -/
structure ScopedDynamicsBinding
    (ModelState ReferencedState ModelInput ReferencedInput : Type) where
  modelStep : ModelState → ModelInput → ModelState
  referenceStep : ReferencedState → ReferencedInput → ReferencedState
  stateMap : ModelState → ReferencedState
  inputMap : ModelInput → ReferencedInput
  admitted : ModelState → Prop
  permitted : ModelInput → Prop
  closed : ∀ m i, admitted m → permitted i → admitted (modelStep m i)
  commutes : ∀ m i, admitted m → permitted i →
    stateMap (modelStep m i) = referenceStep (stateMap m) (inputMap i)

variable {M P I J : Type}

theorem admitted_run (B : ScopedDynamicsBinding M P I J)
    (initial : M) (inputs : Nat → I)
    (hInitial : B.admitted initial) (hInputs : ∀ n, B.permitted (inputs n)) :
    ∀ n, B.admitted (run B.modelStep initial inputs n) := by
  intro n
  induction n with
  | zero => exact hInitial
  | succ n ih => exact B.closed _ _ ih (hInputs n)

/-- A local commuting diagram lifts to every admitted step of the trajectory. -/
theorem bound_runs_correspond (B : ScopedDynamicsBinding M P I J)
    (modelInitial : M) (referenceInitial : P)
    (modelInputs : Nat → I) (referenceInputs : Nat → J)
    (hAdmitted : B.admitted modelInitial)
    (hPermitted : ∀ n, B.permitted (modelInputs n))
    (hInitial : B.stateMap modelInitial = referenceInitial)
    (hInputs : ∀ n, B.inputMap (modelInputs n) = referenceInputs n) :
    ∀ n, B.stateMap (run B.modelStep modelInitial modelInputs n) =
      run B.referenceStep referenceInitial referenceInputs n := by
  intro n
  induction n with
  | zero => exact hInitial
  | succ n ih =>
      simp only [run]
      rw [B.commutes _ _
        (admitted_run B modelInitial modelInputs hAdmitted hPermitted n)
        (hPermitted n), ih, hInputs n]

/--
An admitted dynamics binding plus bounded readout and numerical/model errors
gives a bounded prediction of the referenced observable at each admitted step.
The premises quantify over the claimed domain; finite calibration does not
silently discharge them for unmeasured cases.
-/
theorem bounded_prediction_transfers (B : ScopedDynamicsBinding M P I J)
    (modelInitial : M) (referenceInitial : P)
    (modelInputs : Nat → I) (referenceInputs : Nat → J)
    (hAdmitted : B.admitted modelInitial)
    (hPermitted : ∀ n, B.permitted (modelInputs n))
    (hInitial : B.stateMap modelInitial = referenceInitial)
    (hInputs : ∀ n, B.inputMap (modelInputs n) = referenceInputs n)
    (modelReadout : M → Int) (referenceReadout : P → Int)
    (forecast : Nat → Int) (measurementBudget modelBudget : Int)
    (hReadout : ∀ m, B.admitted m →
      Within (referenceReadout (B.stateMap m)) (modelReadout m) measurementBudget)
    (hForecast : ∀ n,
      Within (modelReadout (run B.modelStep modelInitial modelInputs n))
        (forecast n) modelBudget) :
    ∀ n, Within (referenceReadout
      (run B.referenceStep referenceInitial referenceInputs n))
      (forecast n) (measurementBudget + modelBudget) := by
  intro n
  rw [← bound_runs_correspond B modelInitial referenceInitial
    modelInputs referenceInputs hAdmitted hPermitted hInitial hInputs n]
  exact error_budgets_compose
    (hReadout _ (admitted_run B modelInitial modelInputs hAdmitted hPermitted n))
    (hForecast n)

/-- Ordinally indistinguishable clocks can have different metric calibration. -/
theorem order_alone_does_not_identify_clock_scale :
    ∃ first second : Int → Int,
      (∀ a b, a < b → first a < first b) ∧
      (∀ a b, a < b → second a < second b) ∧
      first 1 - first 0 ≠ second 1 - second 0 := by
  refine ⟨(fun x => x), (fun x => 2 * x), ?_, ?_, ?_⟩
  · intro a b h
    exact h
  · intro a b h
    change 2 * a < 2 * b
    omega
  · decide

/-- Exact common-unit samples of an inertial segment, not measured data. -/
structure InertialSegment where
  coordinateDuration : Int
  spatialDisplacement : Int
  properDuration : Int

def InertialProperTimeLaw (s : InertialSegment) : Prop :=
  0 < s.coordinateDuration ∧ 0 < s.properDuration ∧
    s.properDuration * s.properDuration =
      s.coordinateDuration * s.coordinateDuration -
        s.spatialDisplacement * s.spatialDisplacement

theorem exact_inertial_segment_example :
    InertialProperTimeLaw ⟨5, 3, 4⟩ := by
  unfold InertialProperTimeLaw
  decide

/-- Equal coordinate duration and forward order do not identify proper time. -/
theorem same_coordinate_duration_allows_different_proper_durations :
    ∃ first second : InertialSegment,
      InertialProperTimeLaw first ∧ InertialProperTimeLaw second ∧
      first.coordinateDuration = second.coordinateDuration ∧
      first.properDuration ≠ second.properDuration := by
  refine ⟨⟨5, 0, 5⟩, ⟨5, 3, 4⟩, ?_⟩
  unfold InertialProperTimeLaw
  decide

/-- Agreement on every member of any finite prefix does not force its successor. -/
theorem finite_calibration_does_not_force_next_prediction (cut : Nat) :
    ∃ model observed : Nat → Int,
      (∀ n, n < cut → model n = observed n) ∧ model cut ≠ observed cut := by
  refine ⟨(fun _ => 0), (fun n => if n < cut then 0 else 1), ?_, ?_⟩
  · intro n hn
    simp [hn]
  · simp

end QIKVRT.V2.Physics.MeasurementTransfer
