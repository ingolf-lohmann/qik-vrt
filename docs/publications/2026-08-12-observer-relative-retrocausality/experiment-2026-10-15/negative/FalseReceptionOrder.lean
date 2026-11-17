import QIKVRTFormalization
open QIKVRT.V2.BacksignalingBoundary
-- Must fail: changing the declared event ordering is detectable.
example : ¬ ReversedReception publishedOrder := by
  unfold ReversedReception publishedOrder
  decide
