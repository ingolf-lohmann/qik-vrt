import QIKVRTEffectAck.CausalDistance
open QIKVRT.CausalDistance.V1
example : Graph Bool := { edge := fun _ _ n => n = 0, positive := by intro a b n h; subst n; decide }
