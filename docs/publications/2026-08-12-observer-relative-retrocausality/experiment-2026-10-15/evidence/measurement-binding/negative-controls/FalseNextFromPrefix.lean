import QIKVRTFormalization.Physics.MeasurementTransfer
open QIKVRT.V2.Physics.MeasurementTransfer

-- Expected rejection: the finite-prefix premise cannot be used at its cut.
example : False := by
  rcases finite_calibration_does_not_force_next_prediction 8 with
    ⟨model, observed, agreement, disagreement⟩
  have outside : model 8 = observed 8 := agreement 8 (by decide)
  exact disagreement outside
