import QIKVRTFormalization.Physics.MeasurementTransfer
open QIKVRT.V2.Physics.MeasurementTransfer

-- Expected rejection: equal coordinate duration does not identify proper time.
example : (⟨5, 0, 5⟩ : InertialSegment).properDuration =
    (⟨5, 3, 4⟩ : InertialSegment).properDuration := by
  decide
