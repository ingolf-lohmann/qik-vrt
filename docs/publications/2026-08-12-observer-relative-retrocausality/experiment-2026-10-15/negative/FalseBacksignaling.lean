import QIKVRTFormalization
open QIKVRT.V2.BacksignalingBoundary
-- Must fail: the concrete witness does not receive before its own emission.
example : ReceiveBeforeOwnEmission publishedOrder := by
  unfold ReceiveBeforeOwnEmission publishedOrder
  decide
