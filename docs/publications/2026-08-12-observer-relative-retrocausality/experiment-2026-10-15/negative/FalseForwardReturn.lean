import QIKVRTFormalization
open QIKVRT.V2.ThreeObserverProtocol
-- Must fail: a declared past-directed return is not a forward transport.
example : ForwardTransport assumedPastDirectedTrace := by
  unfold ForwardTransport assumedPastDirectedTrace
  decide
