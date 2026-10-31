import QIKVRTEffectAck.SeedArchitecture
open QIKVRT.SeedArchitecture.V1
-- Deliberately false: determinism does not make distinct input traces identical.
theorem false_prediction : execute (fun (_ : Bool) input => input) false [false] = execute (fun (_ : Bool) input => input) false [true] := by decide

