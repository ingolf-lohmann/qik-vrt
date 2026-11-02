import QIKVRTEffectAck.EvidenceRecovery
open QIKVRT.EvidenceRecovery.V1
example : collect (fun _ : Nat => (none : Option Nat)) [1] = some [7] := by decide
