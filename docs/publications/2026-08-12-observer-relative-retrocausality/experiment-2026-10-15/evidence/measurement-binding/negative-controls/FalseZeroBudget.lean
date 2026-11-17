import QIKVRTFormalization.Physics.MeasurementTransfer
open QIKVRT.V2.Physics.MeasurementTransfer

-- Expected rejection: two nonzero error budgets cannot be erased.
example : Within 4 0 0 := by
  exact error_budgets_compose
    (show Within 4 2 2 by unfold Within; decide)
    (show Within 2 0 2 by unfold Within; decide)
