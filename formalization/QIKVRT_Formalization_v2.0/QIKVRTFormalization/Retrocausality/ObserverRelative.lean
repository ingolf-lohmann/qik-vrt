import QIKVRTFormalization.Retrocausality.ThreeObserverProtocol

/-!
Source-order inversion, its latency threshold, and measurement-order bounds.
Research question: Ingolf Lohmann. Successor formalization: OpenAI Codex.
Integer labels are model quantities. No physical clock or channel is assumed.
The ordinal sign is established here; a calibrated metric gradient is not.
-/
namespace QIKVRT.V2.ObserverRelative

def InverseOrientation (firstLocal secondLocal firstSource secondSource : Int) : Prop :=
  firstLocal < secondLocal ∧ secondSource < firstSource

theorem inverse_orientation_has_signed_differences
    (a b x y : Int) (h : InverseOrientation a b x y) :
    0 < b - a ∧ y - x < 0 := by
  unfold InverseOrientation at h
  omega

theorem increasing_reparameterizations_preserve_orientation
    (a b x y : Int) (localMap sourceMap : Int → Int)
    (hl : ∀ u v, u < v → localMap u < localMap v)
    (hs : ∀ u v, u < v → sourceMap u < sourceMap v)
    (h : InverseOrientation a b x y) :
    InverseOrientation (localMap a) (localMap b) (sourceMap x) (sourceMap y) :=
  ⟨hl a b h.1, hs y x h.2⟩

theorem overtaking_iff_delay_difference_exceeds_emission_gap
    (old new oldDelay newDelay : Int) :
    new + newDelay < old + oldDelay ↔ new - old < oldDelay - newDelay := by
  omega

theorem equal_delays_preserve_source_order
    (old new delay : Int) (h : old < new) :
    old + delay < new + delay := by omega

theorem every_positive_emission_gap_allows_positive_delay_overtaking
    (old new : Int) (h : old < new) :
    ∃ oldDelay newDelay : Int, 0 < oldDelay ∧ 0 < newDelay ∧
      new + newDelay < old + oldDelay := by
  refine ⟨new - old + 2, 1, ?_⟩
  omega

theorem separated_time_intervals_establish_actual_order
    (actualEarly actualLate upperEarly lowerLate : Int)
    (he : actualEarly ≤ upperEarly) (hl : lowerLate ≤ actualLate)
    (gap : upperEarly < lowerLate) : actualEarly < actualLate := by
  omega

-- Arithmetic form of a complementary-mixture identity, not a general
-- theorem about all physical quantum operations or detector efficiencies.
theorem complementary_numerators_have_constant_sum (total component : Int) :
    component + (total - component) = total := by omega

theorem published_mark_orientation : InverseOrientation 100 101 20 10 := by
  unfold InverseOrientation
  decide

end QIKVRT.V2.ObserverRelative
