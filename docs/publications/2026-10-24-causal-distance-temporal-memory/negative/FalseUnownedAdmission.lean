import QIKVRTEffectAck.CausalDistanceBoundaryChecks
open QIKVRT.CausalDistance.BoundaryChecks.V1 QIKVRT.EffectAck.V1
example : authorizeOrdinaryRelease fullyValidConsumerChecks
    { admittedSnapshot with responsibilityAssigned := false } .done true = true := by decide
