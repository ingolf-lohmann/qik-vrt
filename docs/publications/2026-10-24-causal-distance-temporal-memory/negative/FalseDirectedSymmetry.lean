import QIKVRTEffectAck.CausalDistanceBoundaryChecks
open QIKVRT.CausalDistance.V1 QIKVRT.CausalDistance.BoundaryChecks.V1
example : distance oneWay false true = distance oneWay true false := by
  rw [forward_distance_two, backward_distance_infinite]
  rfl
